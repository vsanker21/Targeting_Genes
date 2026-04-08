# GLIOMA-TARGET score (v1.1)

This pipeline implements **composite v1.1** of the outline Module 7.1 score in `config/glioma_target_score.yaml`, written by `scripts/export_gts_candidate_table.py` into the Module 7 candidate TSVs. **v1.1** adds non-zero weights for **D** (HGNC primary UniProt present — tractability proxy, consistent with the Module 6 structure bridge) and **N** (membership in the DepMap-gated STRING export list for the same DEA engine). **S** (spatial/scRNA) and **T** (toxicity) remain reserved at weight **0** until integrated.

## Tier definitions (`glioma_target_tier`)

Tiers are assigned from **`glioma_target_score`** (0–1) using bands aligned with the outline §7.2 narrative (applied to signals implemented in v1.1):

| Tier | Score range | Meaning (v1.1) |
|------|----------------|----------------|
| **1** | ≥ 0.75 | Highest composite rank on **E**, **M**, **D**, **N** (see YAML weights). |
| **2** | ≥ 0.50 and < 0.75 | Moderate composite. |
| **3** | ≥ 0.25 and < 0.50 | Exploratory composite. |
| **4** | < 0.25 | Lower composite on implemented signals. |

**Primary deliverable (high-confidence list):** dedicated slice **`results/module7/glioma_target_tier1_welch.tsv`** (same columns as the Welch table; every row has **`glioma_target_tier == 1`**). Written with the global Welch job in **`export_gts_candidate_table.py`** / **`m7_gts_candidate_stub`**. The full ranked table remains **`results/module7/gts_candidate_table_welch_stub.tsv`**. **`config/pipeline_inventory.yaml`** → **`primary_deliverables`** and **`results/pipeline_results_index.json`** → **`summary.primary_deliverables`** point at the tier-1 file.

Thresholds are configurable under `tier_thresholds` in `config/glioma_target_score.yaml`.

## Column glossary (candidate TSVs)

Columns below are typical for **`gts_candidate_table_*_stub.tsv`** after a successful `m7_gts_candidate_stub` / `export_gts_candidate_table.py` run.

| Column | Description |
|--------|-------------|
| `hgnc_symbol` | HGNC gene symbol (from `data_root` HGNC complete set). |
| `gene_id` | Ensembl gene id (often versioned `ENSG…`). |
| `glioma_target_score` | Composite **v1.1** score in **[0, 1]** = weighted blend of E/M/D/N percentile ranks (see YAML weights). |
| `glioma_target_tier` | Integer **1–4** from score bands above. |
| `gts_sub_E_norm` | Per-gene **E** sub-score in [0, 1] (expression evidence). |
| `gts_sub_M_norm` | Per-gene **M** sub-score (DepMap + known-driver). |
| `gts_sub_D_norm` | Per-gene **D** sub-score (HGNC UniProt proxy). |
| `gts_sub_N_norm` | Per-gene **N** sub-score (STRING list for this engine; neutral 0.5 if list missing). |
| `gts_evidence_tier` | Discrete **evidence screen** (1 = strong DE + DepMap dependency threshold; 2–4 = weaker gates). Independent of `glioma_target_tier`; both are useful. |
| `gts_stub_sort_metric` | Legacy sort helper (signed −log10 *p* magnitude + small bonuses); kept for traceability. |
| `signed_neglog10_p` | Sign of effect × −log10(raw *p*). |
| `padj_bh` | Benjamini–Hochberg FDR when present in the parent DEA (column name kept for compatibility). |
| `delta_log2_expression` | Welch: tumor vs normal log2 fold change (OLS/recount3 jobs use their effect column name instead). |
| `depmap_crispr_median_gbm` | Median DepMap CRISPR gene effect across GBM-related models (more negative ⇒ stronger dependency signal). |
| `outline_m21_high_confidence_screen` | Outline high-confidence DE screen flag from Module 2. |
| `outline_m22_known_gbm_driver` | True if gene is in the outline “known driver” list. |
| `stratify_subtype` | Present only in **`gts_candidate_stratified/**`** tables (Verhaak subtype context). |

**Tier-1-only file:** **`glioma_target_tier1_welch.tsv`** — subset of the Welch candidate table; path configurable as **`gts_candidate_stub.welch_tier1_output_tsv`** in `config/module7_inputs.yaml`.

For engine-specific effect column names (e.g. `beta_tumor_vs_ref_normal`, `log2FoldChange`, `logFC`), see `config/module7_inputs.yaml` → `gts_candidate_stub.jobs`.

**Word report:** after `pip install -r requirements-dev.txt` (includes **python-docx**), run **`python scripts/export_glioma_target_results_docx.py`** → **`results/module7/glioma_target_results_report.docx`** (summary + table of top genes; full list remains in the TSV).

**High-resolution figures:** after `pip install -r requirements-dev.txt` (includes **matplotlib**), run **`python scripts/visualize_glioma_target_results.py`**. This writes a **six-panel composite** (text summary panel removed) to **`results/module7/glioma_target_results_uhd.png`**, optional **PDF** via **`--output-pdf`**, and by default **six separate UHD PNGs** under **`results/module7/glioma_target_panels/`**. Use **`--no-split-panels`** for composite only; **`--no-composite`** for panels only; **`--dpi`** / per-panel sizes in the script (`PANEL_FIGSIZE`) for 4K/print.

**Snakemake:** rule **`m7_visualize_gts_results`** runs the matplotlib script (PNG + PDF + panels + **`glioma_target_visualization.flag`**). Rule **`m7_export_glioma_results_docx`** builds **`glioma_target_results_report.docx`** from the tier-1 TSV (pipeline index section included when **`results/pipeline_results_index.json`** is already on disk). Rule **`m7_glioma_target_deliverables`** depends on both and writes **`glioma_target_deliverables.flag`** — use **`snakemake m7_glioma_target_deliverables -c1`** for a single human-facing M7 build. Optional **`rule all`:** **`GLIOMA_TARGET_INCLUDE_M7_DELIVERABLES=1`** requests the bundle flag (pulls viz + docx; do not combine with **`GLIOMA_TARGET_INCLUDE_M7_VIZ`** / **`GLIOMA_TARGET_INCLUDE_M7_DOCX`**); or set **`GLIOMA_TARGET_INCLUDE_M7_VIZ=1`** and/or **`GLIOMA_TARGET_INCLUDE_M7_DOCX=1`** individually. Full **`GLIOMA_TARGET_INCLUDE_*`** table: **[OPTIONAL_SLICES.md](OPTIONAL_SLICES.md)**.

**Conceptual art (non-data):** optional illustration for slides/posters — **`results/module7/glioma_target_concept_brain_network.png`** (stylized brain + network motif; regenerate externally if needed).
