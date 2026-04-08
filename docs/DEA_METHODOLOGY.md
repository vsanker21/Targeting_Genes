# Tumor vs normal differential expression (methodology)

How this step fits the **seven-module project outline** (especially **Module 2 §2.1**) is documented in **`docs/PIPELINE_ALIGNMENT.md`** and **`config/pipeline_outline.yaml`**.

## Why TOIL-only for primary DEA

TCGA–GTEx comparisons are **invalid** if tumor expression is quantified with **GDC STAR** outputs while normals come from **TOIL RSEM** (or vice versa): the contrast is confounded by **pipeline, reference transcriptome, and normalization**.

The harmonized **TOIL RNA-seq hub** (`TcgaTargetGtex_rsem_gene_tpm.gz`) provides **RSEM gene TPM** for both **TCGA** and **GTEx** on a **shared processing path**. We therefore perform **primary** tumor vs normal discovery on this matrix only.

The **GDC STAR count / TPM matrix** under `results/module2/` remains the reference for **TCGA-internal** analyses (e.g. molecular subtypes, survival, pseudotime inputs) and for **count-based** methods when matched normal counts are available. Run `scripts/validate_gdc_counts_matrix.py` after building counts; results go to `results/module2/gdc_counts_matrix_qc.json`.

## Cohort definitions

- **Tumor:** TCGA, primary site Brain, `detailed_category` contains “Glioblastoma”, `_sample_type` = Primary Tumor (per `TcgaTargetGTEX_phenotype.txt.gz`).
- **Normal:** GTEx cerebral cortex panel: **Frontal Cortex (Ba9), Cortex, Anterior Cingulate (Ba24)**. Cerebellar samples are **excluded** from the default normal pool because mixing cortex and cerebellum in one control group drives massive, region-driven false signal relative to hemispheric GBM. Add cerebellum categories in `config/dea_tumor_normal.yaml` if you explicitly want a cerebellum-matched contrast (or run a separate contrast).

**Reproducibility:** `extract_toil_gbm_brain_tpm.py` writes matrix columns in **sorted** order (all tumor sample IDs ascending, then all normal IDs ascending) and the sample manifest rows in the **same** order. Cohort counts and duplicate-ID checks are summarized in `results/module3/cohort_design_summary.json` (`summarize_expression_cohort.py`).

## Scale and filtering (both DEA paths)

1. **Scale of TOIL values:** The UCSC TOIL file stores **log₂(TPM + 0.001)** per gene (not linear TPM; entries can be negative). We **do not** apply a second log. Optional `linear_tpm` mode exists in config for hypothetical linear matrices.
2. **Linear TPM for filtering/reporting:** `TPM ≈ max(2^E − pseudo, 0)` with `pseudo = 0.001` (matches the hub encoding when `expression_scale: log2_tpm_plus_pseudo`).
3. **Thresholds:** `min_tpm` and `min_fraction_expressing` in `config/dea_tumor_normal.yaml` (`filters`).
4. **Multiple testing:** Configurable via `multiple_testing.method` (default **Benjamini–Hochberg** `fdr_bh` via `statsmodels.stats.multitest.multipletests`). Tables report `padj_bh` and `multiple_testing_method`.

Each DEA run writes a sidecar **provenance JSON** next to the TSV (`*_provenance.json`): config fingerprint, sample sizes, filter mode, and method-specific diagnostics.

## Path A — Welch t-test (pooled normals)

**Use case:** Fast screen, tumor vs **pooled** GTEx normals (ignores subregion structure).

1. **Filter:** A gene is tested if **either** the tumor group **or** the **pooled normal** group passes the linear-TPM mean + fraction thresholds (standard independent filtering on abundance).
2. **Test:** **Welch’s t-test** (`scipy.stats.ttest_ind`, `equal_var=False`) on hub **log₂(TPM+pseudo)** values. This uses **Satterthwaite’s approximate degrees of freedom** per gene (appropriate when variances differ).
3. **Effect size:** `delta_log2_expression` = mean log hub tumor − mean log hub pooled normal (approximate log-fold-change for moderate effects).

**Limit:** If normals mix subregions with different baseline expression, the pooled mean is a **marginal** normal baseline; prefer Path B for inference on a clear estimand.

## Path B — OLS with GTEx subregion covariate (preferred estimand)

**Use case:** **Tumor vs a reference GTEx subregion**, while **adjusting** for other included normal subregions (same hub log scale as Path A).

`scripts/dea_ols_gtex_region_covariate.py` fits, per gene:

**E[Y] = β₀ + β₁·tumor + Σ γ_k·I(normal in subregion k)**

- **Y** = hub log₂(TPM + pseudo).
- **Reference** normal tissue type: `ols_region_covariate.reference_normal_subregion` (default **Brain - Cortex**). Reference normals have all subregion dummies = 0.
- **β₁** = contrast **tumor vs reference normals**, holding other normal subregions fixed (when present).

**Inference:** **Homoskedastic OLS** per gene. Coefficients from **`numpy.linalg.lstsq`** (numerically stable vs raw normal equations). **Var(β̂)** uses **(X′X)⁻¹** computed with **`np.linalg.solve(X′X, I)`**. Residual **σ²** per gene; **t = β̂₁ / SE(β̂₁)** with **df = n − p**; two-sided **p** and the configured FDR method.

This matches the **least-squares + per-gene residual variance** part of **limma** on a fixed design. It does **not** apply **limma’s empirical Bayes** variance moderation (use R/limma for **eBayes**).

### OLS filtering modes (`ols_region_covariate.filter_mode`)

- **`contrast_aligned` (default):** A gene is tested if **either** the tumor arm **or** the **reference-normal-only** subgroup passes the linear-TPM thresholds. This aligns the gene set with the **tumor vs reference** estimand and avoids keeping genes driven solely by signal in non-reference GTEx sites.
- **`pooled_normal`:** Same filter as the Welch path (tumor **or** any pooled normal). Use when you want **identical** filtering to Path A for comparing ranks/gene lists.

## Which table to cite

- For **biological interpretation** of tumor vs cortex with frontal/cingulate heterogeneity in controls: prefer **OLS (Path B)** with default **`contrast_aligned`** filtering.
- For **simple exploratory** tumor vs pooled normal: **Welch (Path A)**.

## Traceability to the project outline (Module 2)

The narrative outline (**`Project_Outline_extracted.txt`**) specifies **DESeq2/edgeR**, **GTEx frontal/cerebellum** controls, **MutSig2CV**, **MOVICS** consensus subtyping, etc. This repository’s **primary** bulk screen deliberately differs where mixing data sources would reduce validity:

| Outline topic | Repository choice (why) |
|---------------|-------------------------|
| Module 2.1 DESeq2 / edgeR | **Primary screen:** TOIL hub Welch + OLS on **log₂(TPM+pseudo)** (tumor vs GTEx brain, one path). **Count-based DE (implemented):** PyDESeq2 + edgeR on **GDC STAR** integer counts for **within-TCGA-GBM** contrasts (`config/deseq2_tcga_gbm.yaml`, rules `m2_deseq2_tcga_*` / `m2_edger_tcga_*`); and on **recount3 GENCODE G029** integer counts for **TCGA-GBM tumor vs GTEx brain normal** on the **recount3 pipeline for both arms** (`config/deseq2_recount3_tcga_gtex.yaml`, `m2_deseq2_recount3_tcga_gbm_vs_gtex_brain`, `m2_edger_recount3_tcga_gbm_vs_gtex_brain`). See **`config/m2_1_harmonized_count_dea.yaml`** — do not mix GDC STAR tumors with TOIL TPM normals. `outline_m21_*` gates apply to the **hub-scale** table unless you re-map them for count-based outputs. |
| Module 2.1 GTEx cerebellum | Default **excludes cerebellum** from the pooled normal (see **Cohort definitions**); add categories in YAML to match outline wording explicitly. |
| Module 2.2 MutSig / variant priors | **DepMap** + optional **TCGA MAF** + **MutSig table join**—complementary to, not a full replacement for, MutSig2CV + CADD in the outline. |
| Module 4 STRING + DepMap context | **`dea_string_export`** and **`stratified_string_export`** support **`numeric_filters`** on joined columns such as **`depmap_crispr_median_gbm`** (integrated stratified tables carry the same DepMap fields as global DEA). DepMap gene-effect scores are **Chronos-style** summaries across lines: **more negative** values indicate **stronger dependency** in the aggregated GBM panel. Thresholds (e.g. median ≤ −0.5) are **heuristic screens** for PPI / synthetic-lethality workflows, not standalone claims. |
| Module 2.3 MOVICS | **MSigDB Verhaak** ranks or **centroid cosine**; outputs include **assignment_score_margin** and **verhaak_subtype_runner_up** to flag ambiguous calls. **Stratified** DE provenance JSON documents **non-independence** of subtype partitions. |

Machine-readable mapping: **`config/methods_traceability.yaml`**, copied into **`results/module3/cohort_design_summary.json`** under **`methods_traceability`** when you run **`summarize_expression_cohort.py`**.

## Pathway enrichment inputs (GSEA / fgsea)

**`gsea_prerank_export`** writes two-column `.rnk` files (HGNC symbol, metric) with **metric = sign(hub-scale effect) × (−log₁₀ p)** from the primary Welch or OLS table, and optionally the same metric from **integrated stratified** Welch/OLS DEA tables (one `.rnk` per subtype file under `results/module4/gsea/stratified/`). This is a **ranking screen** for preranked methods; it is **not** a full GSEA implementation and does not substitute for gene-set size or correlation structure checks in the target tool. Subtype `.rnk` files inherit the same **non-independence caveats** as stratified DEA.

## Count-based DE (M2.1) — implemented

**Spec:** **`config/m2_1_harmonized_count_dea.yaml`** (which matrix + which Snakemake rules).

1. **GDC STAR same pipeline:** `results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet` + `tcga_gbm_sample_meta.tsv` — **PyDESeq2** (`pydeseq2`) and **edgeR** (R) for **Primary vs Recurrent** and **Primary vs Solid Tissue Normal** (`m2_deseq2_tcga_*`, `m2_edger_tcga_*`). See **`config/deseq2_tcga_gbm.yaml`**.

2. **recount3 G029 harmonized counts:** TCGA-GBM + GTEx brain normals from **JHU recount3** mirrors, restricted to the ENSG universe overlapping the STAR matrix — **tumor vs normal** PyDESeq2 + edgeR (`m2_deseq2_recount3_tcga_gbm_vs_gtex_brain`, `m2_edger_recount3_tcga_gbm_vs_gtex_brain`). Downloads: **`scripts/download_recount3_harmonized_g029.py`** / `download_all_required.py --with-recount3-de-counts`. **Not** GDC STAR alignments for the GTEx arm.

**vs TOIL primary DEA:** The TOIL **Welch / OLS** tables (`dea_gbm_vs_gtex_brain*.tsv`) remain the default **log-TPM** cross-cohort screen. Count-based recount3 DE is the appropriate **DESeq2/edgeR analogue** for tumor vs GTEx on **harmonized integer counts**. Compare effect sizes cautiously (`m2_toil_welch_vs_recount3_bulk_effect_correlation`).

**Still optional / not in-repo:** Subtype-stratified **count-based** DE per Verhaak group; DESeq2 on **ComBat-adjusted** pseudo-counts (exploratory only).

## Optional: R / limma with moderation

For **voom** weights and **eBayes**, export the same **log matrix** and **design matrix** (see provenance JSON column names) into R and run **limma**; the Python OLS table is the unmoderated analogue.
