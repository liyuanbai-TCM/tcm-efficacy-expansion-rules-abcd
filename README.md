# TCM Efficacy Expansion Rules A-D

This repository provides Python scripts for rule-based semantic expansion of Chinese herbal efficacy relations. The scripts implement Rules A-D to infer expanded herb-efficacy relations from explicit herb efficacy relations and a Traditional Chinese Medicine (TCM) knowledge graph.

## 1. Overview

Traditional Chinese herbal efficacy descriptions are often expressed in natural language. This makes them difficult to use directly in computational analysis, knowledge graph reasoning, and formula efficacy prediction.

This repository provides reproducible Python code for expanding explicit herb-efficacy relations into rule-based expanded efficacy relations. The expansion process uses semantic relations in a TCM knowledge graph, including `treated_by`, `manifests_as`, `includes`, and `transforms_to`.

The generated results follow the same relation structure as the input herb-efficacy file:

```text
Chinese herb name --has_effect--> expanded effect
```

Each rule script generates two output files:

1. an expanded herb-efficacy relation file
2. a rule-specific evidence path file

The evidence path files are used to record the reasoning paths that support the expanded herb-efficacy relations.

## 2. Repository Contents

```text
tcm-efficacy-expansion-rules-abcd/
│
├── rule_a_expansion.py
├── rule_b_expansion.py
├── rule_c_expansion.py
├── rule_d_expansion.py
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

## 3. Expansion Rules

### 3.1 Rule A: Symptom manifestation-based expansion

Rule A expands herbal efficacy nodes through disease or pattern manifestations.

Logical path:

```text
Chinese herb name --has_effect--> original effect
original effect <--treated_by-- Pattern name / Disease name
Pattern name / Disease name --manifests_as--> Symptom (disease) / Symptom (pattern)
Symptom (disease) / Symptom (pattern) --treated_by--> Rule A expanded effect
```

In Rule A, the first reverse lookup retains only nodes whose `source_LABEL` is:

```text
Pattern name
Disease name
```

The `manifests_as` step retains only manifestation nodes whose `target_LABEL` is:

```text
Symptom (disease)
Symptom (pattern)
```

### 3.2 Rule B: Hierarchical inclusion-based expansion

Rule B expands herbal efficacy nodes through hierarchical inclusion relations of disease or pattern nodes.

Logical path:

```text
Chinese herb name --has_effect--> original effect
original effect <--treated_by-- Pattern name / Disease name
Pattern name / Disease name --includes--> descendant nodes
descendant nodes --treated_by--> Rule B expanded effect
```

Rule B recursively follows `includes` relations from disease or pattern seed nodes until no further descendant nodes can be found. All reachable descendant nodes are then used to infer expanded efficacy nodes through `treated_by` relations.

### 3.3 Rule C: Reverse manifestation-based expansion

Rule C expands herbal efficacy nodes through reverse manifestation reasoning from symptom-related nodes to their upstream disease, pattern, symptom, or etiology contexts.

Logical path:

```text
Chinese herb name --has_effect--> original effect
original effect <--treated_by-- symptom-related contextual nodes
upstream nodes --manifests_as--> symptom-related contextual nodes
upstream nodes --treated_by--> Rule C expanded effect
```

Rule C retains symptom-related contextual nodes. The allowed `source_LABEL` values include:

```text
Symptom (disease)
Symptom (disease) (pattern)
Symptom (etiology)
Symptom (symptom)
Symptom (symptom) (pattern)
Symptom (pattern)
Symptom name
```

Chinese label variants are also supported in the script.

### 3.4 Rule D: Pathogenesis transformation-based expansion

Rule D expands herbal efficacy nodes through transformation relations between disease or pattern nodes.

Logical path:

```text
Chinese herb name --has_effect--> original effect
original effect <--treated_by-- Pattern name / Disease name
Pattern name / Disease name --transforms_to--> Pattern name / Disease name
Pattern name / Disease name --treated_by--> Rule D expanded effect
```

In Rule D, both the source and target nodes of the `transforms_to` relation are strictly limited to:

```text
Pattern name
Disease name
```

Nodes such as `Pattern (pattern)`, `Symptom (pattern)`, or other contextualized symptom or pattern nodes are not included in Rule D.

## 4. Requirements

Python 3.9 or later is recommended.

Install the required Python package:

```bash
pip install -r requirements.txt
```

The required package is:

```text
pandas>=1.5
```

## 5. Input Files

Before running the scripts, users need to prepare two CSV files:

```text
herb_relations.csv
background_kg_node_edges.csv
```

These two files should be placed in the same folder as the Python scripts.

The input files can be prepared in either of the following ways:

1. Users may create their own CSV input files, as long as the required column structure and relation labels are preserved.
2. Users may prepare the input files based on their own TCM knowledge graph or structured efficacy resources.


This GitHub repository provides the Python implementation only. The input files required by the scripts can be prepared by users according to the required column structure, or derived from the deposited Zenodo dataset. In particular, the explicit herb-efficacy relation table can be used as the input `herb_relations.csv`, and the background node-annotated edge table should be prepared as `background_kg_node_edges.csv`.

```text
Structured Dataset of Traditional Efficacies for Chinese Herbal Medicines, Version 2.0
https://doi.org/10.5281/zenodo.20066842
```

### 5.1 `herb_relations.csv`

This file contains the original explicit herb-efficacy relations. Each row should follow the structure:

```text
Chinese herb name --has_effect--> effect
```

Required columns:

```text
source_id
source_ENGLISHNAME
source_LABEL
target_id
target_ENGLISHNAME
target_LABEL
TYPE
```

The `TYPE` value for herb-efficacy relations should be:

```text
has_effect
```

The `source_LABEL` value should usually be:

```text
Chinese herb name
```

The `target_LABEL` value should usually be:

```text
effect
```

The file may contain one herb, multiple herbs, or all herbs. The scripts process herbs by `source_id`.

### 5.2 `background_kg_node_edges.csv`

This file contains the background TCM knowledge graph relations with node IDs, node names, node labels, and relation types.

Required columns:

```text
source_id
source_ENGLISHNAME
source_LABEL
target_id
target_ENGLISHNAME
target_LABEL
TYPE
```

The background graph should include semantic relations among diseases, patterns, symptoms, etiologies, and efficacy nodes. The scripts use semantic relations such as:

```text
treated_by
manifests_as
includes
transforms_to
```

Note: The scripts require a node-annotated edge table named `background_kg_node_edges.csv`. This means that both source and target nodes should contain IDs, English names, semantic labels, and relation types.

### 5.3 Important note on file names

The input file names are fixed in the scripts. Please either:

1. rename your input files as:

```text
herb_relations.csv
background_kg_node_edges.csv
```

or

2. modify the following lines in each Python script before running:

```python
herb_file = Path("herb_relations.csv")
background_file = Path("background_kg_node_edges.csv")
```

## 6. How to Run

Run Rule A:

```bash
python rule_a_expansion.py
```

Run Rule B:

```bash
python rule_b_expansion.py
```

Run Rule C:

```bash
python rule_c_expansion.py
```

Run Rule D:

```bash
python rule_d_expansion.py
```

## 7. Output Files

Each rule script generates two output files: an expanded relation file and an evidence path file.

### 7.1 Rule A outputs

```text
herb_relations_Rule_A_expanded_nodes.csv
Rule_A_evidence_paths.csv
```

### 7.2 Rule B outputs

```text
herb_relations_Rule_B_expanded_nodes.csv
Rule_B_evidence_paths.csv
```

### 7.3 Rule C outputs

```text
herb_relations_Rule_C_expanded_nodes.csv
Rule_C_evidence_paths.csv
```

### 7.4 Rule D outputs

```text
herb_relations_Rule_D_expanded_nodes.csv
Rule_D_evidence_paths.csv
```

The expanded relation files contain the final herb-to-expanded-efficacy relations. The evidence path files record the rule-specific reasoning paths supporting these expanded relations.

The released expanded relation files and rule-specific evidence path files generated using these scripts are deposited in:

```text
Structured Dataset of Traditional Efficacies for Chinese Herbal Medicines, Version 2.0
https://doi.org/10.5281/zenodo.20066842
```

## 8. Deduplication Strategy

For each rule, expanded efficacy nodes are compared with the original efficacy nodes of the herb. If an expanded `target_id` already exists in the original `herb_relations.csv`, it is removed and not exported as a newly expanded node.

Within each rule output, duplicated expanded efficacy relations are also removed. The final exported relation table keeps only one record for the same:

```text
source_id + target_id + TYPE
```

The evidence path tables may contain repeated expanded efficacy nodes because the same expanded efficacy relation may be supported by multiple reasoning paths. These repeated evidence paths are retained for traceability.

## 9. Related Dataset

The released expanded herb-efficacy relation files and the corresponding rule-specific evidence path files are deposited in Zenodo:

```text
Structured Dataset of Traditional Efficacies for Chinese Herbal Medicines, Version 2.0
https://doi.org/10.5281/zenodo.20066842
```

## 10. Related Publication

Please consider citing the following publication if you refer to our specific methodologies, construction logic, or prediction models:

```text
Yuanbai L, Fangzhou L, Yihao L, Yu D, Meng L, Qin Q, Yang Y, Hongming M.
A Knowledge Graph-Driven Hypergeometric Efficacy Prediction Model for Classical Traditional Chinese Herbal Formulas.
Methods Inf Med. 2026 Apr 7. doi: 10.1055/a-2841-4549. Epub ahead of print. PMID: 41895302.
```

## 11. License

This repository is released under the MIT License.

## 12. Contact

For questions, please contact:

```text
LI Yuanbai: liyuanbai126@126.com
```
