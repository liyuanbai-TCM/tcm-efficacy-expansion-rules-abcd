import pandas as pd
from pathlib import Path

# =========================
# 1. File paths
# =========================
# Place these two CSV files in the same folder as rule_c_expansion.py.

herb_file = Path("herb_relations.csv")
background_file = Path("background_kg_node_edges.csv")

output_ruleC_file = "herb_relations_Rule_C_expanded_nodes.csv"
output_evidence_file = "Rule_C_evidence_paths.csv"

# Remove efficacy relations that are already explicitly recorded for the herb.
REMOVE_ORIGINAL_EFFECTS = True


# =========================
# 2. Strict Rule C node types
# =========================
# Rule C only allows reverse reasoning from contextualized symptoms that
# explicitly encode a disease or pattern context.
#
# Valid example:
#   Treat headache (liver deficiency)
#   <-treated_by- Headache (liver deficiency) [Symptom (pattern)]
#   <-manifests_as- Liver deficiency [Pattern name]
#   -treated_by-> Treat liver deficiency
#
# Invalid example:
#   Treat headache -> Treat liver deficiency
#
# General symptom nodes such as "Symptom name" are excluded because one
# general symptom may be associated with multiple diseases or patterns.

SYMPTOM_LABELS = {
    "Symptom (disease)",
    "Symptom (pattern)",

    # Chinese-label compatibility
    "症状(疾病)",
    "症状(证候)",
}

UPPER_LABELS = {
    "Disease name",
    "Pattern name",

    # Chinese-label compatibility
    "疾病名称",
    "证候名称",
}

EFFECT_LABELS = {
    "effect",

    # Chinese-label compatibility
    "功效",
}


# =========================
# 3. CSV reader
# =========================

def read_csv_auto(path: Path) -> pd.DataFrame:
    """
    Read a CSV file by trying several common encodings.
    All values are loaded as strings and missing values are replaced with "".
    """
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return pd.read_csv(path, encoding=encoding, dtype=str).fillna("")
        except UnicodeDecodeError:
            continue

    return pd.read_csv(path, dtype=str).fillna("")


herb = read_csv_auto(herb_file)
bg = read_csv_auto(background_file)

# Remove surrounding spaces from column names and cell values.
herb.columns = herb.columns.str.strip()
bg.columns = bg.columns.str.strip()

for column in herb.columns:
    herb[column] = herb[column].astype(str).str.strip()

for column in bg.columns:
    bg[column] = bg[column].astype(str).str.strip()


# =========================
# 4. Validate required columns
# =========================

REQUIRED_COLUMNS = [
    "source_id",
    "source_ENGLISHNAME",
    "source_LABEL",
    "target_id",
    "target_ENGLISHNAME",
    "target_LABEL",
    "TYPE",
]

for column in REQUIRED_COLUMNS:
    if column not in herb.columns:
        raise ValueError(f"herb_relations.csv is missing required column: {column}")

for column in REQUIRED_COLUMNS:
    if column not in bg.columns:
        raise ValueError(
            f"background_kg_node_edges.csv is missing required column: {column}"
        )


# =========================
# 5. Select explicit herb-effect relations
# =========================

herb_effects = herb[
    (herb["TYPE"] == "has_effect")
    & (herb["source_LABEL"].isin(["Chinese herb name", "中药名称"]))
].copy()

if herb_effects.empty:
    raise ValueError(
        "No original herb has_effect relations were found. Check whether TYPE "
        "is 'has_effect' and source_LABEL is 'Chinese herb name'."
    )

print("Number of input explicit herb-effect relations:", len(herb_effects))
print("Number of input herbs:", herb_effects["source_id"].nunique())


# =========================
# 6. Result containers
# =========================

all_ruleC_rows = []
all_evidence_rows = []


# =========================
# 7. Apply Rule C herb by herb
# =========================

for herb_id, herb_group in herb_effects.groupby("source_id", sort=False):

    base = herb_group.iloc[0].copy()

    herb_name = base["source_ENGLISHNAME"]
    herb_label = base["source_LABEL"]
    original_effect_ids = set(herb_group["target_id"])

    print(
        "Processing:",
        herb_id,
        herb_name,
        "original effects:",
        len(original_effect_ids),
    )

    # ---------------------------------------------------------
    # Step 1
    # Explicit effect <-treated_by- contextualized symptom
    # ---------------------------------------------------------

    step1 = bg[
        (bg["target_id"].isin(original_effect_ids))
        & (bg["TYPE"] == "treated_by")
        & (bg["source_LABEL"].isin(SYMPTOM_LABELS))
        & (bg["target_LABEL"].isin(EFFECT_LABELS))
    ].copy()

    if step1.empty:
        continue

    step1 = step1.rename(
        columns={
            "source_id": "symptom_node_id",
            "source_ENGLISHNAME": "symptom_node_ENGLISHNAME",
            "source_LABEL": "symptom_node_LABEL",
            "target_id": "original_effect_id",
            "target_ENGLISHNAME": "original_effect_ENGLISHNAME",
            "target_LABEL": "original_effect_LABEL",
        }
    )

    symptom_node_ids = set(step1["symptom_node_id"])
    if not symptom_node_ids:
        continue

    # ---------------------------------------------------------
    # Step 2
    # Disease/Pattern --manifests_as--> contextualized symptom
    # Reverse lookup is performed by matching the symptom as target_id.
    # ---------------------------------------------------------

    step2 = bg[
        (bg["target_id"].isin(symptom_node_ids))
        & (bg["TYPE"] == "manifests_as")
        & (bg["source_LABEL"].isin(UPPER_LABELS))
        & (bg["target_LABEL"].isin(SYMPTOM_LABELS))
    ].copy()

    if step2.empty:
        continue

    step2 = step2.rename(
        columns={
            "source_id": "upper_node_id",
            "source_ENGLISHNAME": "upper_node_ENGLISHNAME",
            "source_LABEL": "upper_node_LABEL",
            "target_id": "symptom_node_id",
            "target_ENGLISHNAME": "symptom_node_ENGLISHNAME_2",
            "target_LABEL": "symptom_node_LABEL_2",
        }
    )

    upper_node_ids = set(step2["upper_node_id"])
    if not upper_node_ids:
        continue

    # ---------------------------------------------------------
    # Step 3
    # Disease/Pattern --treated_by--> Rule C expanded effect
    # ---------------------------------------------------------

    step3 = bg[
        (bg["source_id"].isin(upper_node_ids))
        & (bg["TYPE"] == "treated_by")
        & (bg["source_LABEL"].isin(UPPER_LABELS))
        & (bg["target_LABEL"].isin(EFFECT_LABELS))
    ].copy()

    if step3.empty:
        continue

    step3 = step3.rename(
        columns={
            "source_id": "upper_node_id",
            "source_ENGLISHNAME": "upper_node_ENGLISHNAME_2",
            "source_LABEL": "upper_node_LABEL_2",
            "target_id": "expanded_effect_id",
            "target_ENGLISHNAME": "expanded_effect_ENGLISHNAME",
            "target_LABEL": "expanded_effect_LABEL",
        }
    )

    if REMOVE_ORIGINAL_EFFECTS:
        step3 = step3[
            ~step3["expanded_effect_id"].isin(original_effect_ids)
        ].copy()

    if step3.empty:
        continue

    # ---------------------------------------------------------
    # Build complete evidence paths
    # ---------------------------------------------------------

    evidence = (
        step1[
            [
                "original_effect_id",
                "original_effect_ENGLISHNAME",
                "original_effect_LABEL",
                "symptom_node_id",
                "symptom_node_ENGLISHNAME",
                "symptom_node_LABEL",
            ]
        ]
        .merge(
            step2[
                [
                    "symptom_node_id",
                    "upper_node_id",
                    "upper_node_ENGLISHNAME",
                    "upper_node_LABEL",
                ]
            ],
            on="symptom_node_id",
            how="inner",
        )
        .merge(
            step3[
                [
                    "upper_node_id",
                    "expanded_effect_id",
                    "expanded_effect_ENGLISHNAME",
                    "expanded_effect_LABEL",
                ]
            ],
            on="upper_node_id",
            how="inner",
        )
        .drop_duplicates()
    )

    if evidence.empty:
        continue

    evidence.insert(0, "herb_id", herb_id)
    evidence.insert(1, "herb_ENGLISHNAME", herb_name)
    evidence.insert(2, "herb_LABEL", herb_label)
    evidence["Efficacy_Node_Type"] = "Rule C expanded nodes"

    all_evidence_rows.append(evidence)

    # ---------------------------------------------------------
    # Build final herb-to-expanded-effect relations
    # Only effects supported by complete evidence paths are exported.
    # ---------------------------------------------------------

    expanded_effects = evidence[
        [
            "expanded_effect_id",
            "expanded_effect_ENGLISHNAME",
            "expanded_effect_LABEL",
        ]
    ].drop_duplicates(subset=["expanded_effect_id"])

    for _, row in expanded_effects.iterrows():
        new_row = base.copy()

        new_row["source_id"] = herb_id
        new_row["source_ENGLISHNAME"] = herb_name
        new_row["source_LABEL"] = herb_label

        new_row["target_id"] = row["expanded_effect_id"]
        new_row["target_ENGLISHNAME"] = row["expanded_effect_ENGLISHNAME"]
        new_row["target_LABEL"] = row["expanded_effect_LABEL"]

        new_row["TYPE"] = "has_effect"
        new_row["Efficacy_Node_Type"] = "Rule C expanded nodes"

        # Remove temporary fields if they exist in the input template.
        new_row = new_row.drop(labels=["备注", "NOTE"], errors="ignore")

        all_ruleC_rows.append(new_row)


# =========================
# 8. Export Rule C relation file
# =========================

if all_ruleC_rows:
    ruleC = pd.DataFrame(all_ruleC_rows)
    ruleC = ruleC.drop_duplicates(subset=["source_id", "target_id", "TYPE"])

    if "LID" in ruleC.columns:
        numeric_lid = pd.to_numeric(herb["LID"], errors="coerce")
        if numeric_lid.notna().any():
            max_lid = int(numeric_lid.max())
            ruleC["LID"] = range(max_lid + 1, max_lid + 1 + len(ruleC))
        else:
            ruleC["LID"] = [f"RuleC_{index + 1}" for index in range(len(ruleC))]
else:
    output_columns = list(herb.columns)
    for column in ("Efficacy_Node_Type",):
        if column not in output_columns:
            output_columns.append(column)

    output_columns = [
        column for column in output_columns if column not in {"备注", "NOTE"}
    ]
    ruleC = pd.DataFrame(columns=output_columns)

ruleC.to_csv(output_ruleC_file, index=False, encoding="utf-8-sig")


# =========================
# 9. Export Rule C evidence file
# =========================

if all_evidence_rows:
    evidence_all = pd.concat(all_evidence_rows, ignore_index=True)
    evidence_all = evidence_all.drop_duplicates()
else:
    evidence_all = pd.DataFrame(
        columns=[
            "herb_id",
            "herb_ENGLISHNAME",
            "herb_LABEL",
            "original_effect_id",
            "original_effect_ENGLISHNAME",
            "original_effect_LABEL",
            "symptom_node_id",
            "symptom_node_ENGLISHNAME",
            "symptom_node_LABEL",
            "upper_node_id",
            "upper_node_ENGLISHNAME",
            "upper_node_LABEL",
            "expanded_effect_id",
            "expanded_effect_ENGLISHNAME",
            "expanded_effect_LABEL",
            "Efficacy_Node_Type",
        ]
    )

evidence_all.to_csv(output_evidence_file, index=False, encoding="utf-8-sig")


# =========================
# 10. Safety checks and summary
# =========================

if not evidence_all.empty:
    invalid_symptom_labels = set(evidence_all["symptom_node_LABEL"]) - SYMPTOM_LABELS
    invalid_upper_labels = set(evidence_all["upper_node_LABEL"]) - UPPER_LABELS
    invalid_effect_labels = set(evidence_all["expanded_effect_LABEL"]) - EFFECT_LABELS

    if invalid_symptom_labels:
        raise RuntimeError(
            f"Unexpected symptom node labels in Rule C evidence: "
            f"{sorted(invalid_symptom_labels)}"
        )

    if invalid_upper_labels:
        raise RuntimeError(
            f"Unexpected upper node labels in Rule C evidence: "
            f"{sorted(invalid_upper_labels)}"
        )

    if invalid_effect_labels:
        raise RuntimeError(
            f"Unexpected expanded effect labels in Rule C evidence: "
            f"{sorted(invalid_effect_labels)}"
        )

print("Completed.")
print("Input explicit herb-effect relations:", len(herb_effects))
print("Input herbs:", herb_effects["source_id"].nunique())
print("Rule C expanded relations:", len(ruleC))
print(
    "Herbs with Rule C expansions:",
    ruleC["source_id"].nunique() if not ruleC.empty else 0,
)
print("Rule C evidence paths:", len(evidence_all))

if not evidence_all.empty:
    print("Symptom node types in Rule C evidence:")
    print(evidence_all["symptom_node_LABEL"].value_counts().to_string())

print("Exported:")
print(output_ruleC_file)
print(output_evidence_file)
