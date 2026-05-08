import pandas as pd
from pathlib import Path

# =========================
# 1. 文件路径
# =========================
# 这两个 CSV 文件要和 runA.py 放在同一个文件夹里

herb_file = Path("herb_relations.csv")
background_file = Path("background_kg_node_edges.csv")

output_ruleA_file = "herb_relations_Rule_A_expanded_nodes.csv"
output_evidence_file = "Rule_A_evidence_paths.csv"

# 是否去掉当前中药原来已经有的功效，只保留新增扩展功效
REMOVE_ORIGINAL_EFFECTS = True


# =========================
# 2. Rule A 严格节点类型
# =========================

# 第一步：原始功效反查时，只允许疾病名、证候名
seed_labels = [
    "Pattern name",
    "Disease name"
]

# 第二步：manifests_as 得到的下级节点，只允许这两类
symptom_labels = [
    "Symptom (disease)",
    "Symptom (pattern)"
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
# 这里是为了让程序既可以跑单味药，也可以跑全部中药。
# 如果 herb_relations.csv 里只有黄芪，就只跑黄芪；
# 如果里面是全部中药，就按 source_id 每味药分别跑。

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

all_ruleA_rows = []
all_evidence_rows = []


# =========================
# 7. 按每味中药分别执行 Rule A
# =========================

for herb_id, herb_group in herb_effects.groupby("source_id", sort=False):

    # 当前中药自己的模板行
    base = herb_group.iloc[0].copy()

    herb_name = base["source_ENGLISHNAME"]
    herb_label = base["source_LABEL"]

    # 当前中药自己的原始功效 target_id
    original_effect_ids = set(herb_group["target_id"])

    print("正在处理：", herb_id, herb_name, "原始功效数量：", len(original_effect_ids))


    # =========================
    # 7.1 Rule A 第一步：
    #     原始功效 ← treated_by ← Pattern name / Disease name
    # =========================

    step1 = bg[
        (bg["target_id"].isin(original_effect_ids)) &
        (bg["TYPE"] == "treated_by") &
        (bg["source_LABEL"].isin(seed_labels))
    ].copy()

    if step1.empty:
        continue

    step1 = step1.rename(columns={
        "source_id": "pattern_disease_id",
        "source_ENGLISHNAME": "pattern_disease_ENGLISHNAME",
        "source_LABEL": "pattern_disease_LABEL",
        "target_id": "original_effect_id",
        "target_ENGLISHNAME": "original_effect_ENGLISHNAME",
        "target_LABEL": "original_effect_LABEL"
    })

    pattern_disease_ids = set(step1["pattern_disease_id"])


    # =========================
    # 7.2 Rule A 第二步：
    #     Pattern name / Disease name -- manifests_as --> Symptom (disease) / Symptom (pattern)
    # =========================

    step2 = bg[
        (bg["source_id"].isin(pattern_disease_ids)) &
        (bg["TYPE"] == "manifests_as") &
        (bg["target_LABEL"].isin(symptom_labels))
    ].copy()

    if step2.empty:
        continue

    step2 = step2.rename(columns={
        "source_id": "pattern_disease_id",
        "source_ENGLISHNAME": "pattern_disease_ENGLISHNAME_2",
        "source_LABEL": "pattern_disease_LABEL_2",
        "target_id": "symptom_id",
        "target_ENGLISHNAME": "symptom_ENGLISHNAME",
        "target_LABEL": "symptom_LABEL"
    })

    symptom_ids = set(step2["symptom_id"])


    # =========================
    # 7.3 Rule A 第三步：
    #     症状节点 -- treated_by --> 扩展功效A
    # =========================

    step3 = bg[
        (bg["source_id"].isin(symptom_ids)) &
        (bg["TYPE"] == "treated_by")
    ].copy()

    if step3.empty:
        continue

    step3 = step3.rename(columns={
        "source_id": "symptom_id",
        "source_ENGLISHNAME": "symptom_ENGLISHNAME_2",
        "source_LABEL": "symptom_LABEL_2",
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
    # 7.4 生成当前中药的 Rule A 证据路径表
    # =========================

    evidence = (
        step1[
            [
                "original_effect_id",
                "original_effect_ENGLISHNAME",
                "original_effect_LABEL",
                "pattern_disease_id",
                "pattern_disease_ENGLISHNAME",
                "pattern_disease_LABEL"
            ]
        ]
        .merge(
            step2[
                [
                    "pattern_disease_id",
                    "symptom_id",
                    "symptom_ENGLISHNAME",
                    "symptom_LABEL"
                ]
            ],
            on="pattern_disease_id",
            how="inner"
        )
        .merge(
            step3[
                [
                    "symptom_id",
                    "expanded_effect_id",
                    "expanded_effect_ENGLISHNAME",
                    "expanded_effect_LABEL"
                ]
            ],
            on="symptom_id",
            how="inner"
        )
    )

    evidence = evidence.drop_duplicates()

    # 加上当前中药信息，方便后面核查
    evidence.insert(0, "herb_id", herb_id)
    evidence.insert(1, "herb_ENGLISHNAME", herb_name)
    evidence.insert(2, "herb_LABEL", herb_label)

    evidence["备注"] = "扩展功效A"
    evidence["NOTE"] = "Rule A expanded nodes"

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

        # 替换为扩展功效A
        new_row["target_id"] = r["expanded_effect_id"]
        new_row["target_ENGLISHNAME"] = r["expanded_effect_ENGLISHNAME"]
        new_row["target_LABEL"] = r["expanded_effect_LABEL"]

        # 中药到功效的关系仍然是 has_effect
        new_row["TYPE"] = "has_effect"

        if "中文关系类型" in new_row.index:
            new_row["中文关系类型"] = "包含功效"

        new_row["备注"] = "扩展功效A"
        new_row["NOTE"] = "Rule A expanded nodes"

        all_ruleA_rows.append(new_row)


# =========================
# 8. 汇总并导出 Rule A 正式结果表
# =========================

if all_ruleA_rows:
    ruleA = pd.DataFrame(all_ruleA_rows)

    # 正式结果表去重：
    # 同一味中药 + 同一个扩展功效 + has_effect，只保留一条
    ruleA = ruleA.drop_duplicates(subset=["source_id", "target_id", "TYPE"])

    # 如果原表有 LID，则重新编号
    if "LID" in ruleA.columns:
        numeric_lid = pd.to_numeric(herb["LID"], errors="coerce")
        if numeric_lid.notna().any():
            max_lid = int(numeric_lid.max())
            ruleA["LID"] = range(max_lid + 1, max_lid + 1 + len(ruleA))
        else:
            ruleA["LID"] = [f"RuleA_{i+1}" for i in range(len(ruleA))]

else:
    ruleA = pd.DataFrame(columns=list(herb.columns) + ["备注", "NOTE"])

ruleA.to_csv(output_ruleA_file, index=False, encoding="utf-8-sig")


# =========================
# 9. 汇总并导出 Rule A 证据路径表
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
        "pattern_disease_id",
        "pattern_disease_ENGLISHNAME",
        "pattern_disease_LABEL",
        "symptom_id",
        "symptom_ENGLISHNAME",
        "symptom_LABEL",
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
print("扩展功效A结果行数：", len(ruleA))
print("涉及扩展结果的中药数量：", ruleA["source_id"].nunique() if not ruleA.empty else 0)

print("已导出：")
print(output_ruleA_file)
print(output_evidence_file)