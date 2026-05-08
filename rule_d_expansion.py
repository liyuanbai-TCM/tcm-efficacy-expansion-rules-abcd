import pandas as pd
from pathlib import Path

# =========================
# 1. 文件路径
# =========================
# 这两个 CSV 文件要和 runD.py 放在同一个文件夹里

herb_file = Path("herb_relations.csv")
background_file = Path("background_kg_node_edges.csv")

output_ruleD_file = "herb_relations_Rule_D_expanded_nodes.csv"
output_evidence_file = "Rule_D_evidence_paths.csv"

# 是否去掉当前中药原来已经有的功效，只保留新增扩展功效
REMOVE_ORIGINAL_EFFECTS = True


# =========================
# 2. Rule D 严格节点类型
# =========================
# 注意：这里只允许 Pattern name 和 Disease name
# 不能加入 Pattern (pattern)、Symptom (pattern)、证候（证候）等

seed_labels = [
    "Pattern name",
    "Disease name"
]


# =========================
# 3. 读取 CSV
# =========================

def read_csv_auto(path):
    """
    自动尝试几种常见编码，避免中文 CSV 乱码或打不开。
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
# 4. 检查必要列
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
# 6. 准备结果容器
# =========================

all_ruleD_rows = []
all_evidence_rows = []


# =========================
# 7. 按每味中药分别执行 Rule D
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
    # 7.1 Rule D 第一步：
    #     当前中药原始功效 ← treated_by ← Pattern name / Disease name
    # =========================

    step1 = bg[
        (bg["target_id"].isin(original_effect_ids)) &
        (bg["TYPE"] == "treated_by") &
        (bg["source_LABEL"].isin(seed_labels))
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
    # 7.2 Rule D 第二步：
    #     Pattern name / Disease name -- transforms_to --> Pattern name / Disease name
    # =========================
    # 重点：
    # transforms_to 推导后的 target_LABEL 也必须严格限制为：
    # Pattern name / Disease name

    step2 = bg[
        (bg["source_id"].isin(seed_node_ids)) &
        (bg["TYPE"] == "transforms_to") &
        (bg["target_LABEL"].isin(seed_labels))
    ].copy()

    if step2.empty:
        continue

    step2 = step2.rename(columns={
        "source_id": "seed_node_id",
        "source_ENGLISHNAME": "seed_node_ENGLISHNAME_2",
        "source_LABEL": "seed_node_LABEL_2",
        "target_id": "transformed_node_id",
        "target_ENGLISHNAME": "transformed_node_ENGLISHNAME",
        "target_LABEL": "transformed_node_LABEL"
    })

    transformed_node_ids = set(step2["transformed_node_id"])

    if not transformed_node_ids:
        continue


    # =========================
    # 7.3 Rule D 第三步：
    #     推导后的 Pattern name / Disease name -- treated_by --> 扩展功效D
    # =========================

    step3 = bg[
        (bg["source_id"].isin(transformed_node_ids)) &
        (bg["TYPE"] == "treated_by")
    ].copy()

    if step3.empty:
        continue

    step3 = step3.rename(columns={
        "source_id": "transformed_node_id",
        "source_ENGLISHNAME": "transformed_node_ENGLISHNAME_2",
        "source_LABEL": "transformed_node_LABEL_2",
        "target_id": "expanded_effect_id",
        "target_ENGLISHNAME": "expanded_effect_ENGLISHNAME",
        "target_LABEL": "expanded_effect_LABEL"
    })

    # 和当前中药自己的原始功效比对，去掉原来已经有的功效
    if REMOVE_ORIGINAL_EFFECTS:
        step3 = step3[~step3["expanded_effect_id"].isin(original_effect_ids)].copy()

    if step3.empty:
        continue


    # =========================
    # 7.4 生成当前中药的 Rule D 证据路径表
    # =========================
    # 路径：
    # 当前中药原始功效 → 原始 Pattern/Disease → transforms_to 后 Pattern/Disease → 扩展功效D

    evidence = (
        step1[
            [
                "original_effect_id",
                "original_effect_ENGLISHNAME",
                "original_effect_LABEL",
                "seed_node_id",
                "seed_node_ENGLISHNAME",
                "seed_node_LABEL"
            ]
        ]
        .merge(
            step2[
                [
                    "seed_node_id",
                    "transformed_node_id",
                    "transformed_node_ENGLISHNAME",
                    "transformed_node_LABEL"
                ]
            ],
            on="seed_node_id",
            how="inner"
        )
        .merge(
            step3[
                [
                    "transformed_node_id",
                    "expanded_effect_id",
                    "expanded_effect_ENGLISHNAME",
                    "expanded_effect_LABEL"
                ]
            ],
            on="transformed_node_id",
            how="inner"
        )
    )

    evidence = evidence.drop_duplicates()

    # 加上当前中药信息，方便核查
    evidence.insert(0, "herb_id", herb_id)
    evidence.insert(1, "herb_ENGLISHNAME", herb_name)
    evidence.insert(2, "herb_LABEL", herb_label)

    evidence["备注"] = "扩展功效D"
    evidence["NOTE"] = "Rule D expanded nodes"

    all_evidence_rows.append(evidence)


    # =========================
    # 7.5 生成当前中药的正式扩展结果
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

        # 替换为扩展功效D
        new_row["target_id"] = r["expanded_effect_id"]
        new_row["target_ENGLISHNAME"] = r["expanded_effect_ENGLISHNAME"]
        new_row["target_LABEL"] = r["expanded_effect_LABEL"]

        # 中药到功效的关系仍然是 has_effect
        new_row["TYPE"] = "has_effect"

        if "中文关系类型" in new_row.index:
            new_row["中文关系类型"] = "包含功效"

        new_row["备注"] = "扩展功效D"
        new_row["NOTE"] = "Rule D expanded nodes"

        all_ruleD_rows.append(new_row)


# =========================
# 8. 汇总并导出扩展D正式结果表
# =========================

if all_ruleD_rows:
    ruleD = pd.DataFrame(all_ruleD_rows)

    # 正式结果表去重：
    # 同一味中药 + 同一个扩展功效 + has_effect，只保留一条
    ruleD = ruleD.drop_duplicates(subset=["source_id", "target_id", "TYPE"])

    # 如果原表有 LID，则重新编号
    if "LID" in ruleD.columns:
        numeric_lid = pd.to_numeric(herb["LID"], errors="coerce")
        if numeric_lid.notna().any():
            max_lid = int(numeric_lid.max())
            ruleD["LID"] = range(max_lid + 1, max_lid + 1 + len(ruleD))
        else:
            ruleD["LID"] = [f"RuleD_{i+1}" for i in range(len(ruleD))]

else:
    ruleD = pd.DataFrame(columns=list(herb.columns) + ["备注", "NOTE"])

ruleD.to_csv(output_ruleD_file, index=False, encoding="utf-8-sig")


# =========================
# 9. 汇总并导出证据路径表
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
        "transformed_node_id",
        "transformed_node_ENGLISHNAME",
        "transformed_node_LABEL",
        "expanded_effect_id",
        "expanded_effect_ENGLISHNAME",
        "expanded_effect_LABEL",
        "备注",
        "NOTE"
    ])

evidence_all.to_csv(output_evidence_file, index=False, encoding="utf-8-sig")


# =========================
# 10. 打印结果
# =========================

print("完成！")
print("输入原始中药功效关系数量：", len(herb_effects))
print("输入中药数量：", herb_effects["source_id"].nunique())
print("扩展功效D结果行数：", len(ruleD))
print("涉及扩展结果的中药数量：", ruleD["source_id"].nunique() if not ruleD.empty else 0)

print("已导出：")
print(output_ruleD_file)
print(output_evidence_file)