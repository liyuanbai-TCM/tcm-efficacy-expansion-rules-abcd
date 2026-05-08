import pandas as pd
from pathlib import Path
from collections import defaultdict

# =========================
# 1. 文件路径
# =========================
# 这两个 CSV 文件要和 runB.py 放在同一个文件夹里

herb_file = Path("herb_relations.csv")
background_file = Path("background_kg_node_edges.csv")

output_ruleB_file = "herb_relations_Rule_B_expanded_nodes.csv"
output_evidence_file = "Rule_B_evidence_paths.csv"

# 是否去掉当前中药原来已经有的功效，只保留新增扩展功效
REMOVE_ORIGINAL_EFFECTS = True


# =========================
# 2. 读取 CSV
# =========================

def read_csv_auto(path):
    """
    自动尝试几种常见编码，避免中文CSV乱码或打不开。
    """
    for enc in ["utf-8-sig", "utf-8", "gb18030", "gbk"]:
        try:
            return pd.read_csv(path, encoding=enc, dtype=str).fillna("")
        except UnicodeDecodeError:
            continue

    return pd.read_csv(path, dtype=str).fillna("")


herb = read_csv_auto(herb_file)
bg = read_csv_auto(background_file)

# 清理列名和内容前后空格
herb.columns = herb.columns.str.strip()
bg.columns = bg.columns.str.strip()

for col in herb.columns:
    herb[col] = herb[col].astype(str).str.strip()

for col in bg.columns:
    bg[col] = bg[col].astype(str).str.strip()


# =========================
# 3. 检查必要列
# =========================

required_cols = [
    "source_id",
    "source_ENGLISHNAME",
    "source_LABEL",
    "target_id",
    "target_ENGLISHNAME",
    "target_LABEL",
    "TYPE"
]

for col in required_cols:
    if col not in herb.columns:
        raise ValueError(f"herb_relations.csv 缺少列：{col}")

for col in required_cols:
    if col not in bg.columns:
        raise ValueError(f"background_kg_node_edges.csv 缺少列：{col}")


# =========================
# 4. 建立节点名称查询表
# =========================

node_source = bg[["source_id", "source_ENGLISHNAME", "source_LABEL"]].copy()
node_source.columns = ["node_id", "node_ENGLISHNAME", "node_LABEL"]

node_target = bg[["target_id", "target_ENGLISHNAME", "target_LABEL"]].copy()
node_target.columns = ["node_id", "node_ENGLISHNAME", "node_LABEL"]

herb_source = herb[["source_id", "source_ENGLISHNAME", "source_LABEL"]].copy()
herb_source.columns = ["node_id", "node_ENGLISHNAME", "node_LABEL"]

herb_target = herb[["target_id", "target_ENGLISHNAME", "target_LABEL"]].copy()
herb_target.columns = ["node_id", "node_ENGLISHNAME", "node_LABEL"]

nodes = pd.concat(
    [node_source, node_target, herb_source, herb_target],
    ignore_index=True
).drop_duplicates(subset=["node_id"])

node_info = nodes.set_index("node_id").to_dict(orient="index")


def get_node_name(node_id):
    return node_info.get(node_id, {}).get("node_ENGLISHNAME", node_id)


def get_node_label(node_id):
    return node_info.get(node_id, {}).get("node_LABEL", "")


# =========================
# 5. 筛出中药原始功效关系
# =========================
# 这里保证一味药、多味药、全部中药都可以跑

herb_effects = herb[
    (herb["TYPE"] == "has_effect") &
    (herb["source_LABEL"].isin(["Chinese herb name", "中药名称"]))
].copy()

if herb_effects.empty:
    raise ValueError(
        "没有筛到中药 has_effect 原始关系。请检查 herb_relations.csv 中的 TYPE 是否为 has_effect，source_LABEL 是否为 Chinese herb name。"
    )

print("输入原始中药功效关系数量：", len(herb_effects))
print("输入中药数量：", herb_effects["source_id"].nunique())


# =========================
# 6. 预先建立 includes 查询表
# =========================

include_edges = bg[bg["TYPE"] == "includes"].copy()

include_lookup = defaultdict(list)

for _, r in include_edges.iterrows():
    include_lookup[r["source_id"]].append(r)


# =========================
# 7. 准备结果容器
# =========================

all_ruleB_rows = []
all_evidence_rows = []


# =========================
# 8. 按每味中药分别执行 Rule B
# =========================

for herb_id, herb_group in herb_effects.groupby("source_id", sort=False):

    # 当前中药自己的模板行
    base = herb_group.iloc[0].copy()

    herb_name = base["source_ENGLISHNAME"]
    herb_label = base["source_LABEL"]

    # 当前中药自己的原始功效
    original_effect_ids = set(herb_group["target_id"])

    print("正在处理：", herb_id, herb_name, "原始功效数量：", len(original_effect_ids))


    # =========================
    # 8.1 第一步：
    #     当前中药原始功效 ← treated_by ← 证候/疾病
    # =========================

    step1 = bg[
        (bg["target_id"].isin(original_effect_ids)) &
        (bg["TYPE"] == "treated_by") &
        (bg["source_LABEL"].isin(["Pattern name", "Disease name"]))
    ].copy()

    if step1.empty:
        continue

    step1 = step1.rename(columns={
        "source_id": "seed_node_id",
        "source_ENGLISHNAME": "seed_node_ENGLISHNAME",
        "source_LABEL": "seed_node_LABEL",
        "target_id": "original_effect_id",
        "target_ENGLISHNAME": "original_effect_ENGLISHNAME",
        "target_LABEL": "original_effect_LABEL"
    })

    seed_node_ids = set(step1["seed_node_id"])

    if not seed_node_ids:
        continue


    # =========================
    # 8.2 第二步：
    #     从这些疾病/证候出发，
    #     沿 includes 关系多轮向下找所有子孙节点
    # =========================

    descendant_records = []

    seed_rows = step1[
        [
            "original_effect_id",
            "original_effect_ENGLISHNAME",
            "original_effect_LABEL",
            "seed_node_id",
            "seed_node_ENGLISHNAME",
            "seed_node_LABEL"
        ]
    ].drop_duplicates()

    for _, seed in seed_rows.iterrows():
        original_effect_id = seed["original_effect_id"]
        original_effect_name = seed["original_effect_ENGLISHNAME"]
        original_effect_label = seed["original_effect_LABEL"]

        seed_id = seed["seed_node_id"]
        seed_name = seed["seed_node_ENGLISHNAME"]
        seed_label = seed["seed_node_LABEL"]

        # 每个起点单独记录，避免 includes 形成环导致死循环
        visited = set([seed_id])

        # frontier 中每一项是：
        # 当前节点ID、当前路径ID列表、当前层级
        frontier = [(seed_id, [seed_id], 0)]

        while frontier:
            parent_id, path_ids, level = frontier.pop(0)

            for edge in include_lookup.get(parent_id, []):
                child_id = edge["target_id"]

                if child_id == "":
                    continue

                # 防止循环
                if child_id in visited:
                    continue

                visited.add(child_id)

                child_name = edge["target_ENGLISHNAME"]
                child_label = edge["target_LABEL"]

                child_path_ids = path_ids + [child_id]
                child_level = level + 1

                descendant_records.append({
                    "original_effect_id": original_effect_id,
                    "original_effect_ENGLISHNAME": original_effect_name,
                    "original_effect_LABEL": original_effect_label,

                    "seed_node_id": seed_id,
                    "seed_node_ENGLISHNAME": seed_name,
                    "seed_node_LABEL": seed_label,

                    "include_parent_id": parent_id,
                    "include_parent_ENGLISHNAME": get_node_name(parent_id),
                    "include_parent_LABEL": get_node_label(parent_id),

                    "included_node_id": child_id,
                    "included_node_ENGLISHNAME": child_name,
                    "included_node_LABEL": child_label,

                    "include_level": child_level,
                    "include_path_ids": " -> ".join(child_path_ids),
                    "include_path_names": " -> ".join([get_node_name(x) for x in child_path_ids])
                })

                frontier.append((child_id, child_path_ids, child_level))


    descendants = pd.DataFrame(descendant_records)

    if descendants.empty:
        continue

    descendants = descendants.drop_duplicates()
    descendant_ids = set(descendants["included_node_id"])

    if not descendant_ids:
        continue


    # =========================
    # 8.3 第三步：
    #     子孙节点 -- treated_by --> 扩展功效B
    # =========================

    step3 = bg[
        (bg["source_id"].isin(descendant_ids)) &
        (bg["TYPE"] == "treated_by")
    ].copy()

    if step3.empty:
        continue

    step3 = step3.rename(columns={
        "source_id": "included_node_id",
        "source_ENGLISHNAME": "included_node_ENGLISHNAME_2",
        "source_LABEL": "included_node_LABEL_2",
        "target_id": "expanded_effect_id",
        "target_ENGLISHNAME": "expanded_effect_ENGLISHNAME",
        "target_LABEL": "expanded_effect_LABEL"
    })

    # 去掉当前中药原来已经有的功效，只保留新增扩展功效
    if REMOVE_ORIGINAL_EFFECTS:
        step3 = step3[~step3["expanded_effect_id"].isin(original_effect_ids)].copy()

    if step3.empty:
        continue


    # =========================
    # 8.4 生成当前中药的证据路径表
    # =========================

    evidence = descendants.merge(
        step3[
            [
                "included_node_id",
                "expanded_effect_id",
                "expanded_effect_ENGLISHNAME",
                "expanded_effect_LABEL"
            ]
        ],
        on="included_node_id",
        how="inner"
    )

    evidence = evidence.drop_duplicates()

    # 加上当前中药信息，方便核查
    evidence.insert(0, "herb_id", herb_id)
    evidence.insert(1, "herb_ENGLISHNAME", herb_name)
    evidence.insert(2, "herb_LABEL", herb_label)

    evidence["备注"] = "扩展功效B"
    evidence["NOTE"] = "Rule B expanded nodes"

    all_evidence_rows.append(evidence)


    # =========================
    # 8.5 生成当前中药的正式扩展结果
    # =========================

    expanded_effects = step3[
        [
            "expanded_effect_id",
            "expanded_effect_ENGLISHNAME",
            "expanded_effect_LABEL"
        ]
    ].drop_duplicates(subset=["expanded_effect_id"])

    for _, r in expanded_effects.iterrows():
        new_row = base.copy()

        # 保留当前中药作为 source
        new_row["source_id"] = herb_id
        new_row["source_ENGLISHNAME"] = herb_name
        new_row["source_LABEL"] = herb_label

        # 替换为扩展功效B
        new_row["target_id"] = r["expanded_effect_id"]
        new_row["target_ENGLISHNAME"] = r["expanded_effect_ENGLISHNAME"]
        new_row["target_LABEL"] = r["expanded_effect_LABEL"]

        # 中药到功效的关系仍然是 has_effect
        new_row["TYPE"] = "has_effect"

        if "中文关系类型" in new_row.index:
            new_row["中文关系类型"] = "包含功效"

        new_row["备注"] = "扩展功效B"
        new_row["NOTE"] = "Rule B expanded nodes"

        all_ruleB_rows.append(new_row)


# =========================
# 9. 汇总并导出扩展B正式结果表
# =========================

if all_ruleB_rows:
    ruleB = pd.DataFrame(all_ruleB_rows)

    # 去重：同一味中药 + 同一个扩展功效 + has_effect，只保留一条
    ruleB = ruleB.drop_duplicates(subset=["source_id", "target_id", "TYPE"])

    # 如果原表有 LID，则重新编号
    if "LID" in ruleB.columns:
        numeric_lid = pd.to_numeric(herb["LID"], errors="coerce")
        if numeric_lid.notna().any():
            max_lid = int(numeric_lid.max())
            ruleB["LID"] = range(max_lid + 1, max_lid + 1 + len(ruleB))
        else:
            ruleB["LID"] = [f"RuleB_{i+1}" for i in range(len(ruleB))]

else:
    ruleB = pd.DataFrame(columns=list(herb.columns) + ["备注", "NOTE"])

ruleB.to_csv(output_ruleB_file, index=False, encoding="utf-8-sig")


# =========================
# 10. 汇总并导出证据路径表
# =========================

if all_evidence_rows:
    evidence_all = pd.concat(all_evidence_rows, ignore_index=True)
    evidence_all = evidence_all.drop_duplicates()
else:
    evidence_all = pd.DataFrame(columns=[
        "herb_id",
        "herb_ENGLISHNAME",
        "herb_LABEL",
        "original_effect_id",
        "original_effect_ENGLISHNAME",
        "original_effect_LABEL",
        "seed_node_id",
        "seed_node_ENGLISHNAME",
        "seed_node_LABEL",
        "include_parent_id",
        "include_parent_ENGLISHNAME",
        "include_parent_LABEL",
        "included_node_id",
        "included_node_ENGLISHNAME",
        "included_node_LABEL",
        "include_level",
        "include_path_ids",
        "include_path_names",
        "expanded_effect_id",
        "expanded_effect_ENGLISHNAME",
        "expanded_effect_LABEL",
        "备注",
        "NOTE"
    ])

evidence_all.to_csv(output_evidence_file, index=False, encoding="utf-8-sig")


# =========================
# 11. 打印结果
# =========================

print("完成！")
print("输入原始中药功效关系数量：", len(herb_effects))
print("输入中药数量：", herb_effects["source_id"].nunique())
print("扩展功效B结果行数：", len(ruleB))
print("涉及扩展结果的中药数量：", ruleB["source_id"].nunique() if not ruleB.empty else 0)

print("已导出：")
print(output_ruleB_file)
print(output_evidence_file)