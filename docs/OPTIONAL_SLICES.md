# Optional pipeline slices (ClinVar, M3 scRNA, M3 deconv, MOVICS, M5 sRGES)

These targets are **not** required for the default `snakemake` build unless you set the env vars below (they extend `rule all`).

## Environment flags (`rule all`)

| Variable | Effect |
|----------|--------|
| `GLIOMA_TARGET_INCLUDE_CLINVAR=1` | Adds ClinVar-annotated MAF gene table (`m2_maf_genes_clinvar_annotate`). |
| `GLIOMA_TARGET_INCLUDE_M3_SCANPY=1` | Adds GSE57872 Scanpy outputs (`m3_gse57872_scanpy_qc_cluster`). |
| `GLIOMA_TARGET_INCLUDE_M3_DECONV_S2=1` | Adds **`m3_deconvolution_s2_nnls`** outputs (scipy **NNLS** on **real** wide TSVs under **`data_root`** per **`config/m3_deconvolution_s2_nnls.yaml`**). **Not** stripped by **`snakemake_subprocess_env`**. |
| `GLIOMA_TARGET_INCLUDE_M3_RCTD_RUN=1` | Adds **`m3_deconvolution_rctd_run`** (R **spacexr** hook; **`snakemake --use-conda`**). **Not** stripped by **`snakemake_subprocess_env`**. |
| `GLIOMA_TARGET_INCLUDE_M3_CELL2LOCATION_RUN=1` | Adds **`m3_deconvolution_cell2location_run`** (Python hook; **`snakemake --use-conda`**). **Not** stripped by **`snakemake_subprocess_env`**. |
| `GLIOMA_TARGET_INCLUDE_M5_SRGES_RUN=1` | Adds **`m5_srges_run`** (compound ranks from real **`perturbation_tsv`**). **Not** stripped by **`snakemake_subprocess_env`**. |
| `GLIOMA_TARGET_INCLUDE_MOVICS=1` | Adds MOVICS IntNMF clusters (`m2_movics_intnmf_tcga_gbm`, TCGA TPM + counts). |
| `GLIOMA_TARGET_INCLUDE_MOVICS_DEPMAP_MAE=1` | Adds three-view IntNMF (`m2_movics_intnmf_depmap_mae`) plus cluster interpretation (`m2_movics_depmap_intnmf_characterize` → `cluster_model_annotations.tsv`, `cluster_summary.json`). Requires DepMap staging + `depmap/<release>/Model.csv`. |
| `GLIOMA_TARGET_INCLUDE_SUPPLEMENTARY_WIRING=1` | Adds supplementary pathway wiring (WikiPathways URL sync, PathwayCommons GMT, fgsea/clusterProfiler R stubs, ARCHS4 join, etc. — see `Snakefile` / `docs/GBM_DETECTION_AND_OPEN_DATA.md`). |
| `GLIOMA_TARGET_INCLUDE_M7_DELIVERABLES=1` | Adds **`m7_glioma_target_deliverables`** (UHD figures + Word report + sentinel flag). Requires **`requirements-dev.txt`** (matplotlib + python-docx). **Do not** also set **`GLIOMA_TARGET_INCLUDE_M7_VIZ`** or **`GLIOMA_TARGET_INCLUDE_M7_DOCX`** (duplicate `rule all` inputs). |
| `GLIOMA_TARGET_INCLUDE_M7_VIZ=1` | Adds matplotlib UHD composite + panels + PDF + **`glioma_target_visualization.flag`**. Ignored when **`GLIOMA_TARGET_INCLUDE_M7_DELIVERABLES=1`** is set. |
| `GLIOMA_TARGET_INCLUDE_M7_DOCX=1` | Adds **`glioma_target_results_report.docx`**. Ignored when **`GLIOMA_TARGET_INCLUDE_M7_DELIVERABLES=1`** is set. |

**Both MOVICS paths:** set `GLIOMA_TARGET_INCLUDE_MOVICS=1` and `GLIOMA_TARGET_INCLUDE_MOVICS_DEPMAP_MAE=1` only when R/MOVICS and both data layouts (GDC matrices + DepMap MAE) are available — TCGA and DepMap clusters are **not** comparable cohorts.

Truthy values: `1`, `true`, `yes`, `on` (case-insensitive).

## When optional flags are *not* passed to Snakemake

These entry points call Snakemake with a subprocess environment built by **`scripts/snakemake_subprocess_env.py`**, which **removes** all **`GLIOMA_TARGET_INCLUDE_*`** variables so resolution matches the **default** `rule all` (even if your interactive shell still has them set):

- **`python scripts/run_windows_outline_gate.py`** — only the final **`snakemake all`** step; earlier steps see your full environment.
- **`python scripts/run_supplementary_enrichment_smoke.py`**
- Pytest **`@pytest.mark.snakemake`** dry-run tests

**Still uses your shell as-is:** typing **`snakemake`** directly, **`scripts/run_snakemake_all_windows.ps1`**, and GitHub Actions jobs that set env in the workflow step.

## ClinVar (M2.2)

- Set **`maf_glob`** in `config/tcga_mutation_layer.yaml` if you want a non-empty MAF gene summary; otherwise the join still runs but matches zero genes.
- Example (PowerShell):

```powershell
$env:GLIOMA_TARGET_INCLUDE_CLINVAR = "1"
snakemake -c1
```

Or build only: `snakemake -c1 m2_maf_genes_clinvar_annotate`

## M3 scRNA (GSE57872)

- Stage `.h5ad` or counts under `data_root` per **`config/m3_gse57872_scanpy.yaml`** (`geo/scrna_seq/GSE57872/...` or `sra/GSE57872/counts/...`).
- This slice does **not** use in-repo synthetic expression matrices; the Scanpy rule expects real staged inputs.

```powershell
$env:GLIOMA_TARGET_INCLUDE_M3_SCANPY = "1"
snakemake -c1 m3_gse57872_scanpy_qc_cluster
```

Install Scanpy stack: `pip install -r requirements-optional.txt`

## M3 deconvolution S2 (NNLS; real TSVs under `data_root`)

**`m3_deconvolution_s2_nnls`** reads **wide TSVs** from **`config/m3_deconvolution_s2_nnls.yaml`** (paths relative to **`GLIOMA_TARGET_DATA_ROOT`**) and writes **`results/module3/m3_deconvolution_s2/`**. There is **no** in-repo synthetic or placeholder path: missing files fail the rule. Add these outputs to **`rule all`** with **`GLIOMA_TARGET_INCLUDE_M3_DECONV_S2=1`**.

```powershell
snakemake -c1 m3_deconvolution_s2_nnls
```

## M3 RCTD / Cell2location (optional conda rules)

- **`m3_deconvolution_rctd_run`** — use **`snakemake --use-conda -c1 m3_deconvolution_rctd_run`**. Conda env **`workflow/envs/m3_rctd.yaml`**; RDS paths under **`data_root`** in **`config/m3_deconvolution_rctd_inputs.yaml`**. **`scripts/run_m3_rctd_orchestrate.py`** resolves **`Rscript`** via **`rscript_resolve`** (registry / **`config/rscript_local.yaml`** / **`R_HOME`**, then PATH). Install **spacexr** in that env if needed (see env comments). **`rctd_run_provenance.json`** records **`artifact_kind`**, **`status`** (`ok`, **`rds_load_failed`**, **`spacexr_missing`**, **`create_failed`**), and load / **`create.RCTD`** diagnostics. **`rctd_run.flag`** is written only when **`status`** is **`ok`**; otherwise the R wrapper exits **1** (Snakemake marks the rule failed; matches **`cell2location_run.flag`** behavior). Optional **`rule all`:** **`GLIOMA_TARGET_INCLUDE_M3_RCTD_RUN=1`**.
- **`m3_deconvolution_cell2location_run`** — **`snakemake --use-conda -c1 m3_deconvolution_cell2location_run`**. Env **`workflow/envs/m3_cell2location.yaml`**; h5ad paths in **`config/m3_deconvolution_cell2location_inputs.yaml`**. **`cell2location_run_provenance.json`** includes **`artifact_kind`**, **`status`** (`inputs_ok`, **`trained_ok`**, **`training_failed`**), **`training_enabled`**, and optional **`training_error`** / import fields. **`cell2location_run.flag`** is written only when the script exits **0**; **`training_failed`** removes any existing flag so a failed re-run does not leave a stale success marker. With **`training.enabled: true`**, **`scripts/run_m3_cell2location_orchestrate.py`** runs **`RegressionModel`** (reference signatures) then **`Cell2location`** (spatial mapping), using **`reference_labels_key`**, optional **`reference_batch_key`** / **`reference_counts_layer`** / **`spatial_counts_layer`**, **`signature_summary`** (`means` vs **`q05`**), **`min_shared_genes`** (intersection of spatial **`var_names`** with signature rows), and **`cell2location_max_epochs`** (see YAML comments). Optional **`rule all`:** **`GLIOMA_TARGET_INCLUDE_M3_CELL2LOCATION_RUN=1`**. When **`training.enabled`** is **true**, the Snakefile also lists **`output_result_h5ad`** and **`output_abundance_tsv`** as rule outputs (same paths as the YAML) so Snakemake invalidates the run when those artifacts are removed or when you toggle training on after a validate-only build—**re-run `snakemake` after changing `training.enabled`** so the DAG matches the new output set. On training failures after **`export_posterior`**, provenance may include **`signature_extract_diagnostic`** (AnnData layout snapshot) and **`gene_intersection_diagnostic`** (gene overlap counts); **`m3_deconvolution_integration_stub.json`** checklist flags and **`recommended_next_steps`** surface those for planning.

Conda validation: **`.github/workflows/m3-deconv-external-tools.yml`** (**`workflow_dispatch`**). Default run does a **full** micromamba install for **`m3_rctd`** (plus R `jsonlite`/`remotes` smoke) and a **`micromamba create --dry-run`** for **`m3_cell2location`** (avoids multi-GB torch/cell2location downloads). Enable workflow input **`cell2location_full_install`** to run a separate job that performs a **full** **`m3_cell2location`** create and a Python smoke import (**`cell2location`**, **`scvi`**, **`scanpy`**, **`anndata`**).

**`module3_export_manifest.json`** lists RCTD + Cell2location run files for **`pipeline_results_index`**; those paths use **`module3_inputs.yaml`** → **`module3_export_manifest.optional_tags`** and are **not** Snakemake inputs on **`m3_export_manifest`** (see **`_ARTIFACTS_EXEMPT_FROM_SNAKEFILE_MANIFEST_INPUTS`** in **`scripts/write_module3_export_manifest.py`**) so **`snakemake --dry-run`** for the merged index does not pull optional conda deconv rules when **`data_root`** lacks RDS/h5ad.

## M5 compound ranking (optional `rule all`)

**`m5_srges_run`** ranks compounds from **real** **`perturbation_tsv`** under **`data_root`** (**`config/m5_srges.yaml`**). It is **not** in default **`rule all`**; set **`GLIOMA_TARGET_INCLUDE_M5_SRGES_RUN=1`** to include it. Rebuild: **`snakemake -c1 m5_srges_run`**. Stage cmapPy/CLUE mirror exports under **`{data_root}/lincs/srges_rank_score_exports`** for **`m5_srges_output_paths_status`**.

## Programmatic multi-omics staging (`m2_movics_inputs.yaml` paths)

After **`python scripts/download_all_required.py`** has populated **`data_root/depmap/<release>/`**, run:

```text
python scripts/fetch_movics_staging_data.py
```

or **`snakemake -c1 fetch_movics_staging_data`**.

This writes:

- **`{data_root}/omics/multi_omics_mae/`** — DepMap **Glioma**-related models: expression (log TPM), CN (log2), binary mutation matrix (rows = gene symbols), plus `depmap_mae_provenance.json`.
- **`{data_root}/cohorts/cgga_expression/`** — files for each URL you add under **`cgga_http`** in **`config/m2_movics_data_fetch.yaml`** (copy links from the [CGGA download page](https://cgga.org.cn/download.jsp); portal URLs can change).
- **`{data_root}/cohorts/cbttc/ACCESS_NOTES.md`** — controlled-access notes (no open bulk API here).

Hook: **`python scripts/download_all_required.py --with-movics-staging`** runs the fetcher after the main phases (still needs DepMap present in that run or a prior one).

**Three-view IntNMF (DepMap cell lines):** after the `.tsv.gz` trio exists under `{data_root}/omics/multi_omics_mae/`, run **`snakemake -c1 m2_movics_intnmf_depmap_mae`** (R + MOVICS; same install as TCGA rule). Matrix paths are read from **`config/m2_movics_data_fetch.yaml`** (`depmap_gbm_mae`); hyperparameters in **`config/m2_movics_depmap_mae_run.yaml`**. The MAE gene list **prioritizes GBM outline drivers** (`prioritize_outline_drivers_in_gene_universe` + **`references/gbm_known_drivers_outline.yaml`**) before high-variance expression fill, then **`mutation_require_variable`** trims non-informative binary rows for MOVICS.

**TCGA vs DepMap MOVICS:** cluster IDs from **`m2_movics_intnmf_tcga_gbm`** (tumors) and **`m2_movics_intnmf_depmap_mae`** (lines) are **not** comparable; use separate panels or explicit “methods comparison” labeling — see **`m2_3_movics_vs_consensus_method_contrast.json`** field **`tcga_vs_depmap_intnmf_interpretation`**.

**Interpret clusters:** with DepMap **`Model.csv`** under `{data_root}/depmap/<release>/`, run **`snakemake -c1 m2_movics_depmap_intnmf_characterize`** after the IntNMF rule. Writes **`cluster_model_annotations.tsv`** and **`cluster_summary.json`** (lineage mix, mutation burden, optional **`CRISPRGeneEffect.csv`** means).

**R + MOVICS CI (manual trigger):** workflow **`movics-depmap-r-smoke.yml`** builds tiny MAE fixtures and runs **`m2_movics_intnmf_depmap_mae`** on Ubuntu (`workflow_dispatch`).

**CGGA / CBTTC:** add HTTPS rows under **`cgga_http`** in **`config/m2_movics_data_fetch.yaml`** when you have current portal links; place controlled-access files under **`cohorts/cbttc/`** when obtained — no extra Snakemake rules until a second cohort matrix is wired.

## MOVICS (M2.3 IntNMF)

- **Baseline (tumors):** TPM + log2(counts+1) from in-repo STAR matrices (`config/m2_movics_run.yaml`). Reproducible GDC-aligned baseline.
- **Three-view (cell lines):** expression + CN + mutation from DepMap staging above (`m2_movics_intnmf_depmap_mae`).
- **Extend:** stage additional matrices under paths checked in `config/m2_movics_inputs.yaml` when you have other cohort data.

```powershell
python scripts/install_r_movics_dependencies.py
$env:GLIOMA_TARGET_INCLUDE_MOVICS = "1"
snakemake -c1
```

Or: `snakemake -c1 m2_movics_intnmf_tcga_gbm`

R does not need to be on PATH if `python scripts/configure_r_for_snakemake.py` has been run (writes `config/rscript_local.yaml`, gitignored) or R is registered in Windows. Ad-hoc: `powershell -File scripts/run_rscript.ps1 ...`

If **`heatmap.plus`** fails to build from source on Windows, install **Rtools** matching your R version: https://cran.r-project.org/bin/windows/Rtools/

## MOVICS vs consensus report

After changing MOVICS wiring or copy in `scripts/m2_3_movics_vs_consensus_report.py`:

```text
snakemake -c1 m2_3_movics_vs_consensus_report
```

Output: `results/module3/m2_3_movics_vs_consensus_method_contrast.json` — includes **`programmatic_multi_omic_staging`** (fetch config, rule name, MAE path under `data_root`).

## CI

GitHub Actions workflow **Optional slices** (`.github/workflows/optional-slices-ci.yml`) runs M3 synthetic via Snakemake, **`fetch_movics_staging_data`** with an empty `GLIOMA_TARGET_DATA_ROOT` (DepMap skipped; report JSON still produced), and regenerates the contrast JSON on Ubuntu (no ClinVar download, no R/MOVICS).

