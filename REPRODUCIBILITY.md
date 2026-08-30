# Reproducibility Guide

## Knowledge Graph–Based Structuring and Explicitation of Therapeutic-Effect Knowledge in Traditional Chinese Medicine

This document links the public source data, Python scripts, generated outputs, and manuscript results used to reproduce the rule-based herb-efficacy expansion described in the manuscript.

## 1. Public resources

### 1.1 Upstream TCM knowledge graph

The semantic expansion rules use Version 2.0 of the related TCM knowledge graph:

- **Dataset:** *A Semantic Knowledge Graph Linking Diseases, Patterns, Symptoms, and Herbs for Traditional Chinese Medicine (Version 2.0)*
- **Zenodo DOI:** https://doi.org/10.5281/zenodo.20061549
- Relevant source files:
  - `node-v2-eng260502.csv`
  - `edge-v2-eng260502.csv`

### 1.2 Herb-efficacy dataset used for the revised manuscript

The corrected rule-expansion outputs are deposited in:

- **Dataset:** *Structured Dataset of Traditional Efficacies for Chinese Herbal Medicines (Version 2.1)*
- **Zenodo DOI:** https://doi.org/10.5281/zenodo.22168291

Version 2.1 corrects the implementation and output of Rule C. The explicit herb-efficacy relations and the Rule A, Rule B, and Rule D results are unchanged from Version 2.0.

## 2. GitHub scripts

Repository:

https://github.com/liyuanbai-TCM/tcm-efficacy-expansion-rules-abcd

The repository contains four rule-specific Python scripts:

- `rule_a_expansion.py`
- `rule_b_expansion.py`
- `rule_c_expansion.py`
- `rule_d_expansion.py`

Each script implements one semantic expansion rule described in the manuscript.

## 3. Input preparation

The rule scripts use two principal input resources:

1. **Explicit herb-efficacy relations**
   - Zenodo file: `explicit_herb_efficacy_relations_v2.csv`
   - The scripts use this information as the starting herb-efficacy relation table.
   - Where required by the local script configuration, the working input may be named:
     - `herb_relations.csv`

2. **Background TCM knowledge graph**
   - Derived from the Version 2.0 knowledge graph files:
     - `node-v2-eng260502.csv`
     - `edge-v2-eng260502.csv`
   - Where required by the local script configuration, the prepared working input may be named:
     - `background_kg_node_edges.csv`

The intermediate working filenames above are script-side input names; the authoritative deposited source files remain those listed in the Zenodo records.

## 4. Rule definitions and scripts

### Rule A

- Script: `rule_a_expansion.py`
- Function: symptom-manifestation-based expansion.
- Published relation output:
  - `expanded_herb_efficacy_relations_ruleA_v2.csv`
- Published evidence output:
  - `herb_efficacy_expansion_evidence_ruleA_v2.csv`

### Rule B

- Script: `rule_b_expansion.py`
- Function: hierarchical inheritance-based expansion.
- Published relation output:
  - `expanded_herb_efficacy_relations_ruleB_v2.csv`
- Published evidence output:
  - `herb_efficacy_expansion_evidence_ruleB_v2.csv`

### Rule C

- Script: `rule_c_expansion.py`
- Function: reverse contextualized reasoning from contextualized symptom nodes to explicitly linked upstream disease or pattern nodes.
- The corrected implementation allows only:
  - `Symptom (pattern)`
  - `Symptom (disease)`
- Their explicitly linked upstream nodes must be:
  - `Pattern name`
  - `Disease name`
- Published corrected relation output:
  - `expanded_herb_efficacy_relations_ruleC_v2.1.csv`
- Published corrected evidence output:
  - `herb_efficacy_expansion_evidence_ruleC_v2.1.csv`

The earlier Rule C implementation used an overly broad set of symptom-related node types and could therefore generate unsupported reverse inferences. The corrected `rule_c_expansion.py` in the GitHub repository should be used to reproduce the revised manuscript results.

### Rule D

- Script: `rule_d_expansion.py`
- Function: pathogenesis-transformation-based expansion.
- Published relation output:
  - `expanded_herb_efficacy_relations_ruleD_v2.csv`
- Published evidence output:
  - `herb_efficacy_expansion_evidence_ruleD_v2.csv`

## 5. Expected reproduction results

Using the Version 2.0 upstream knowledge graph, the explicit herb-efficacy relations, and the current GitHub scripts, the expected rule-specific outputs are:

| Rule | Expanded herb-efficacy relations | Evidence records |
|---|---:|---:|
| Rule A | 15,223 | 15,223 |
| Rule B | 4,229 | 4,327 |
| Rule C | 274 | 509 |
| Rule D | 1,182 | 1,209 |
| **Total** | **20,908** | **21,268** |

The Version 2.1 Zenodo release contains five herb-efficacy relation files in total, including the explicit relations:

- Total relation records across the five relation files: **28,820**
- Unique herbs: **483**
- Unique target efficacy nodes: **2,519**
- Unique herb-efficacy pairs after deduplication by `source_id` and `target_id`: **28,792**

Rule-specific files are intentionally retained separately. If the same herb-efficacy relation is inferred by more than one rule, it may appear in multiple rule-specific files so that the provenance of each reasoning pathway is preserved.

## 6. Version correspondence

### Dataset Version 2.0

Version 2.0 introduced the revised dataset structure and recalculated Rule A-D results using Version 2.0 of the upstream knowledge graph.

### Dataset Version 2.1

Version 2.1 changes only Rule C:

- explicit relations: unchanged from Version 2.0
- Rule A: unchanged from Version 2.0
- Rule B: unchanged from Version 2.0
- Rule C: corrected and replaced in Version 2.1
- Rule D: unchanged from Version 2.0

For this reason, the unchanged files retain the `_v2.csv` suffix, while the corrected Rule C files use the `_v2.1.csv` suffix.

Earlier Rule C outputs retained in the Zenodo version history are provided for traceability and should **not** be used to reproduce the revised manuscript results.

## 7. Data-code-output mapping

| Manuscript component | Code | Public output |
|---|---|---|
| Rule A | `rule_a_expansion.py` | `expanded_herb_efficacy_relations_ruleA_v2.csv`; `herb_efficacy_expansion_evidence_ruleA_v2.csv` |
| Rule B | `rule_b_expansion.py` | `expanded_herb_efficacy_relations_ruleB_v2.csv`; `herb_efficacy_expansion_evidence_ruleB_v2.csv` |
| Rule C | `rule_c_expansion.py` | `expanded_herb_efficacy_relations_ruleC_v2.1.csv`; `herb_efficacy_expansion_evidence_ruleC_v2.1.csv` |
| Rule D | `rule_d_expansion.py` | `expanded_herb_efficacy_relations_ruleD_v2.csv`; `herb_efficacy_expansion_evidence_ruleD_v2.csv` |

The rule definitions correspond to the manuscript Methods section describing semantic expansion (Section 2.4.2) and Figure 2. The resulting expansion counts correspond to the revised results reported in Section 3.3. The public data and code links should also be cited in the manuscript Data Availability statement.

## 8. Minimal reproduction workflow

1. Download the Version 2.0 TCM knowledge graph from Zenodo.
2. Download `explicit_herb_efficacy_relations_v2.csv` from the Version 2.1 herb-efficacy dataset.
3. Prepare the script-side working inputs required by the repository scripts (`herb_relations.csv` and `background_kg_node_edges.csv`, where applicable).
4. Run `rule_a_expansion.py`, `rule_b_expansion.py`, `rule_c_expansion.py`, and `rule_d_expansion.py`.
5. Compare the generated rule-specific relation and evidence files with the corresponding public files in the Version 2.1 Zenodo release.
6. Confirm the expected record counts listed in Section 5 of this document.

## 9. Reproducibility scope

The purpose of this repository is to reproduce the deterministic rule-based semantic expansion reported in the manuscript. Large source and output data files are maintained on Zenodo rather than duplicated in GitHub. GitHub provides the executable rule implementations and this data-code-output mapping; Zenodo provides the versioned source data and released outputs.

## 10. Citation

### Herb-efficacy dataset

LI Yuanbai, YANG Yang. (2026). *Structured Dataset of Traditional Efficacies for Chinese Herbal Medicines (Version 2.1)* [Data set]. Zenodo. https://doi.org/10.5281/zenodo.22168291

### Upstream TCM knowledge graph

*A Semantic Knowledge Graph Linking Diseases, Patterns, Symptoms, and Herbs for Traditional Chinese Medicine (Version 2.0).* Zenodo. https://doi.org/10.5281/zenodo.20061549
