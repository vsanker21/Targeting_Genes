# GLIOMA-TARGET

Computational pipeline for integrative therapeutic target discovery in high-grade gliomas.

**Project specification:** `Project_Outline.docx` (text extract in-repo: **`Project_Outline_extracted.txt`**). The outline defines **seven modules** (harmonization → DEA/mutation/subtype → scRNA/spatial → GRN → modality prioritization → structure/toxicity → integrated GTS scoring). **`docs/PIPELINE_ALIGNMENT.md`** maps each module to **implemented vs planned** artifacts here; machine-readable status: **`config/pipeline_outline.yaml`**.

## Local data (shared with GBM Detection)

This repository references **existing downloads** under:

`G:\GBM Detection\data`

To use another location, set:

```text
GLIOMA_TARGET_DATA_ROOT
```

Paths are declared in `config/data_sources.yaml`.

| Area | Role |
|------|------|
| `tcga/TCGA-GBM` | TCGA-GBM case folders (~2800 UUID directories); pair with GDC metadata from your companion workflow |
| `geo/epigenetic` | GSE100351, GSE139136 |
| `geo/external_validation` | GSE154795 |
| `geo/scrna_seq` | GSE131928, GSE141946, GSE57872 |
| `geo/spatial` | GSE287631 |
| `sra/GSE57872` | FASTQ + STAR/count outputs for GSE57872 |
| `dryad/spatial_gbm` | Ravi et al. Dryad bundle: Visium, tumor/env scRNA, methylation, IMC, MALDI ([DOI 10.5061/dryad.h70rxwdmj](https://doi.org/10.5061/dryad.h70rxwdmj)) |
| `geo/bulk_microarray/GSE*` | Outline microarray cohorts (GSE4290, GSE7696, GSE50161, GSE68848) |
| `gtex/xena_toil/` | TOIL hub gene TPM + phenotype for TCGA+GTEx |
| `depmap/` | DepMap release bundle (API → signed GCS URLs) |
| `gdc/tcga_gbm_open_star_counts/` | 391 open TCGA-GBM STAR gene-count TSVs + manifest |
| `references/` | GENCODE v44 GTF, HGNC complete set, hg38 blacklist (GitHub) |
| `pipelines/` | Shallow `git` clones: nf-core/rnaseq, scrnaseq, fetchngs; cmap/cmapPy |
| `lincs/clue_api_subset/` | CLUE REST JSON snapshots (only if `CLUE_API_KEY` or `CLUE_API_TOKEN_FILE` is set) |

**Download everything public (orchestrator)**

```powershell
pip install -r requirements.txt
python scripts\verify_python_environment.py
python scripts\download_all_required.py
```

Methods used: **NCBI GEO FTP**, **TOIL Xena HTTPS**, **EBI FTP / HGNC GCS**, **DepMap API + GCS**, **GDC REST**, **GitHub raw**, **shallow `git clone`**, **CLUE `api.clue.io` (optional token)**, **WSL `curl` fallback**, optional **`--probe-aws`** and **`--with-string`**.

Flags: `--skip-depmap`, `--skip-gdc`, `--skip-geo`, `--skip-gtex`, `--skip-references`, `--skip-git`, `--skip-clue`, `--no-gtex-tpm`, `--gdc-workers N`.

Legacy script (GEO bulk + TOIL only): `scripts/download_external_datasets.py`.

### LINCS / CLUE token (store outside the repo)

Request a free academic **user_key** at [clue.io](https://clue.io/). Do **not** commit it. Either:

```powershell
$env:CLUE_API_KEY = "your_user_key"
```

or point to a file whose **first line** is the key:

```powershell
$env:CLUE_API_TOKEN_FILE = "C:\Users\YOU\.secrets\clue_user_key.txt"
```

Then run the orchestrator without `--skip-clue`. Snapshots (landmark genes, temozolomide-related signatures, etc.) are written under `lincs/clue_api_subset/`.

**Not automated:** CGGA, controlled CPTAC/PDC, Synapse-protected cohorts, full MSigDB, full L1000 GCTX matrices — add locally or extend `config/data_sources.yaml`.

More detail: `docs/DATA_MANIFEST.md`.

## Quick checks

```powershell
cd "G:\Targeting Genes"
pip install -r requirements.txt
python scripts\verify_python_environment.py
python scripts\verify_data_layout.py
```

Optional Snakemake **`rule all`** environment flags (**`GLIOMA_TARGET_INCLUDE_*`**): [docs/OPTIONAL_SLICES.md](docs/OPTIONAL_SLICES.md).

### Windows: full environment + outline DAG gate

One command runs **pip** (`requirements.txt` + `requirements-optional.txt` + `requirements-dev.txt`), **core env verify**, **optional cmapPy stack** (pytest + GCT functional test; GNINA/10x reported but not required on Windows), **third-party status JSON**, **pytest**, and **`snakemake all`** (default **`rule all`** inputs only: optional **`GLIOMA_TARGET_INCLUDE_*`** flags are **not** forwarded to that Snakemake step — see **`scripts/snakemake_subprocess_env.py`**). Implements the **partial** M1–M7 scaffolding in **`config/pipeline_outline.yaml`** when data exist under **`GLIOMA_TARGET_DATA_ROOT`**.

```powershell
python scripts\run_windows_outline_gate.py
python scripts\run_windows_outline_gate.py -c 4
python scripts\run_windows_outline_gate.py --no-snakemake --skip-pip
```

Vendor tools (**Cell Ranger**, **Space Ranger**, **GNINA**) are still **not** installed by this script; add them separately if you need strict binary checks (`--strict-binaries` / `GLIOMA_TARGET_GNINA_EXE`, etc.).

**Outline “planned” scope (not the same as `snakemake all`):** Large items from **`Project_Outline.docx`** (full FASTQ reprocessing, ComBat/Harmony, CGGA/CPTAC/CBTTC, DESeq2/MOVICS/SCENIC+/sRGES/full GTS, etc.) are **not** implemented as end-to-end steps here. See **`config/pipeline_planned_extensions.yaml`** and **`results/pipeline_planned_extensions_report.json`** (Snakemake **`pipeline_planned_extensions_report`**; included in **`rule all`**). **Partial automation:** **`m4_string_api_network`** calls the STRING-DB HTTP API for DEA M21 gene lists (needs internet); run manually with `snakemake results/module4/string_api/string_api_fetch_provenance.json -c1` if you did not build those outputs yet.

With Snakemake installed:

```powershell
snakemake verify_python_environment -c 1
snakemake -n
snakemake -c 1
```

This builds verified layout flags, GDC expression matrices (where data exist), TOIL subset, **Module 2 §2.1 DEA tables**, and QC JSONs.

### Third-party tooling (Cell Ranger, GNINA, cmapPy)

These are **not** in the core `requirements.txt`. The repo can still **install and verify** what is possible from PyPI/conda and **report** the rest.

| Tool | How to install | In-repo verification |
|------|----------------|------------------------|
| **cmapPy** (LINCS `.gct` / `.gctx`) | `pip install -r requirements-optional.txt` or `python scripts\install_optional_third_party.py` | **`python scripts\ensure_optional_third_party_functional.py`** (pip + **GCT write/parse round-trip**); `verify_optional_third_party_tooling.py --strict` (import-only) |
| **Snakemake** | | **`optional_third_party_python_stack`** — full `ensure` with env overrides (GNINA bootstrap, 10x, etc.; see Snakefile). **`optional_stack_ci`** — same as GitHub Actions: `run_optional_stack_ci.py` (pytest + ensure with CI flags). Env for CI rule: **`GLIOMA_TARGET_OPTIONAL_STACK_CI_STRICT=1`**, **`GLIOMA_TARGET_OPTIONAL_STACK_SKIP_PIP=1`**. |
| **GNINA** (docking) | PATH / **`GLIOMA_TARGET_GNINA_EXE`**, or let `ensure_optional_third_party_functional.py` bootstrap into **`.conda_envs\gnina`** (unless `--no-bootstrap-gnina`). Alternatively: `conda activate …`, then `install_optional_third_party.py --conda-gnina` or `conda install -c conda-forge gnina -y` | `gnina --help`; `verify_optional_third_party_tooling.py` checks PATH and `conda list` when `CONDA_PREFIX` is set |
| **Cell Ranger / Space Ranger** | Download from [10x Genomics](https://www.10xgenomics.com/support/software/cell-ranger); unpack and add the `cellranger-x.y.z` folder to **PATH** or set **`GLIOMA_TARGET_CELLRANGER_EXE`** / **`GLIOMA_TARGET_SPACERANGER_EXE`** (see `config\third_party_tooling.yaml`) | `ensure` / `verify` report status; use `--require-10x-tools` or **`GLIOMA_TARGET_REQUIRE_10X_OPTIONAL_STACK=1`** to fail the run if missing. Optional tree: `{data_root}\tools\cellranger` |

If `conda` reports **no default base** or **not a conda environment**, create/activate an environment first (`conda create -n glioma-target python=3.11`, `conda activate glioma-target`), then re-run pip and optional installs inside that env.

```powershell
pip install -r requirements.txt -r requirements-optional.txt -r requirements-dev.txt
python scripts\run_optional_stack_ci.py
python scripts\install_optional_third_party.py
python scripts\ensure_optional_third_party_functional.py --no-bootstrap-gnina
pytest tests -q
python scripts\verify_optional_third_party_tooling.py
snakemake verify_optional_third_party_tooling -c 1
```

GitHub Actions runs the same idea on Ubuntu: **`.github/workflows/optional-stack.yml`** (`pytest` + `ensure_optional_third_party_functional.py --no-bootstrap-gnina --no-gnina-required` so the default Linux “GNINA required” policy does not fail a runner without docking binaries).

Use `--strict-binaries` on the verify script only on machines where Cell Ranger and GNINA are supposed to be on PATH (CI images, shared lab nodes).

---

## Implementation vs outline (short)

| Outline | This repo (representative paths) |
|---------|----------------------------------|
| **M1** Harmonization & cohorts | `config/data_sources.yaml`, `scripts/download_all_required.py`, `results/module2/tcga_gbm_star_*.parquet` |
| **M2 §2.1** Tumor vs normal DEA | `results/module3/dea_gbm_vs_gtex_brain*.tsv` + `outline_m21_*` columns per outline FDR and absolute log2 fold-change gates (`config/dea_tumor_normal.yaml`) |
| **M2 §2.2** Mutation / dependency layer | **CRISPR** + **DepMap somatic** + optional **TCGA MAF** + **`join_dea_mutsig.py`** on MutSig gene tables (`config/mutsig_merge.yaml`). MutSig2CV itself is not executed in-repo. |
| **M2 §2.3** Subtype + stratified DEA | **MSigDB** / **centroid** in `module2_integration.yaml`. **Stratified** Welch + OLS (`stratified_dea.yaml`). **`join_stratified_dea_integration.py`** adds DepMap/MAF/MutSig to `*/integrated/*.tsv`. **MOVICS** still external. |
| **M2+** Mutations, full MOVICS | Partial / planned — see `config/pipeline_outline.yaml` |
| **M3–M7** scRNA/spatial, GRN, prioritization, structure, GTS | **Mixed (per outline):** M3–M6 **partial** scaffolding; **M7** — **GTS v1.1** (E+M+D+N), tier-1 slice, stratified tables, optional **UHD figures + Word report** (`m7_glioma_target_deliverables`); outline **S/T** and full validation still **planned**. See `config/pipeline_outline.yaml` and `data_sources.yaml` |

**Primary DEA** uses the **TOIL RSEM hub** only (tumor + GTEx normals), avoiding GDC-vs-TOIL batch mixing. **DESeq2/edgeR** on the outline is **planned** for harmonized integer counts. **Normal panel:** default GTEx sites are **cortex / frontal / cingulate** (cerebellum excluded by default; outline also mentions cerebellum — see **`docs/PIPELINE_ALIGNMENT.md`**).

---

## Artifacts (outline-oriented)

**Toward M1 + M2 inputs**

- `results/module2/tcga_gbm_star_tpm_matrix.parquet` — protein-coding genes × TCGA-GBM (`tpm_unstranded`)
- `results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet` — integer `unstranded` STAR counts (future DESeq2 / within-TCGA DE)
- `results/module2/tcga_gbm_sample_meta.tsv`, `results/module1/gdc_file_case_metadata.json`
- `results/module2/gdc_counts_matrix_qc.json`
- `results/module2/gdc_counts_cohort_summary.json` — counts matrix vs sample meta overlap, sparsity (after counts matrix is built)
- `results/module1/combat_seq_tcga_gbm_primary/combat_seq_adjusted_counts.parquet` — **ComBat-Seq** (`sva::ComBat_seq`) on **Primary Tumor** subset of STAR counts; batch = **TCGA TSS** (barcode token); read `combat_seq_provenance.json` caveats (`m1_combat_seq_tcga_gbm_primary`; R package **`sva`**: `python scripts/install_r_combat_dependencies.py`)
- `results/module3/deseq2_tcga_gbm/primary_vs_recurrent/deseq2_results.tsv` — **PyDESeq2** Recurrent vs Primary on GDC STAR counts (`m2_deseq2_tcga_primary_recurrent`; install **pydeseq2** from `requirements-optional.txt`)
- `results/module3/deseq2_tcga_gbm/primary_vs_solid_tissue_normal/deseq2_results.tsv` — **PyDESeq2** Primary vs TCGA Solid Tissue Normal (n=5; low power — read `deseq2_provenance.json` caveats; `m2_deseq2_tcga_primary_vs_solid_normal`)
- `results/module3/edger_tcga_gbm/primary_vs_recurrent/edger_qlf_results.tsv` — **edgeR** glmQLF, same aggregation and contrasts as PyDESeq2 (`m2_edger_tcga_primary_recurrent`; R + **edgeR** / **limma**, **yaml**, **jsonlite**, **arrow** — see **`Typical Windows setup for edgeR`** below and `requirements-optional.txt`). Overrides for `Rscript`: **`R_HOME`**, **`RSCRIPT`**, **`rscript:`** in `config/config.yaml`, or **`config/rscript_local.yaml`**.
- `results/module3/edger_tcga_gbm/primary_vs_solid_tissue_normal/edger_qlf_results.tsv` — **edgeR** glmQLF Primary vs Solid Tissue Normal (`m2_edger_tcga_primary_vs_solid_normal`; same caveats as PyDESeq2 stub)

**Typical Windows setup for edgeR (`m2_edger_*`)**

1. *(Optional, Administrator PowerShell)* Upgrade or install R: `python scripts/install_r_for_snakemake.py --upgrade`
2. If Snakemake still cannot find Rscript: `python scripts/configure_r_for_snakemake.py` (writes gitignored `config/rscript_local.yaml`)
3. Install CRAN + Bioconductor dependencies: `python scripts/install_r_edger_dependencies.py` (runs `scripts/install_edger_pkgs.R` with the discovered `Rscript`)

**Supplementary pathway enrichment (fgsea + clusterProfiler on WikiPathways / PathwayCommons GMTs):** `python scripts/install_r_supplementary_dependencies.py` (runs `scripts/install_r_supplementary_enrichment.R`). Smoke test: `python scripts/run_supplementary_enrichment_smoke.py` (keeps your real **`results/`** DEA; use **`--copy-demo-results`** only on a clean clone or CI). ARCHS4 matrices: `python scripts/download_supplementary_reference_resources.py` (omit **`--skip-archs4-h5`** for full HDF5). CLUE: **`.env.example`**, then `fetch_clue_api_subset.py`. See **`docs/SNAKEMAKE_HPC.md`** (cluster execution; optional **`requirements-hpc.txt`** for SLURM).

Manual equivalent for step 3:

```text
Rscript -e "install.packages(c('yaml','jsonlite','arrow','BiocManager'), repos='https://cloud.r-project.org'); BiocManager::install(c('edgeR','limma'))"
```

**Outline M2 §2.1 (TOIL-coherent DEA)**

- `results/module3/toil_gbm_vs_brain_tpm.parquet`, `toil_gbm_vs_brain_samples.tsv`
- `results/module3/cohort_design_summary.json` — cohort QC + **`methods_traceability`** (outline ↔ implementation mapping from `config/methods_traceability.yaml`)
- `results/module3/dea_gbm_vs_gtex_brain.tsv` — Welch vs pooled normals; **`padj_bh`**; **`outline_m21_*`** flags (outline §2.1 FDR and absolute log2 fold-change on hub-scale contrast)
- `results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv` — OLS tumor vs reference cortex + region covariates; same outline flags on **β_tumor**
- `dea_*_outline_drivers.tsv` — **`outline_m22_known_gbm_driver`** on primary + DepMap/MAF/MutSig DEA tables (`references/gbm_known_drivers_outline.yaml`; not somatic calls)
- `stratified_dea/integrated/*_outline_drivers.tsv`, `stratified_ols_dea/integrated/*_outline_drivers.tsv` — same driver flag on integrated subtype DEA (after `stratified_dea_integration.flag`; touch `stratified_integrated_outline_drivers.flag`)
- `stratified_dea/integrated/`, `stratified_ols_dea/integrated/` — stratified DEA + integration columns (`join_stratified_dea_integration.py`)
- `mean_log_tpm_by_verhaak_subtype.tsv` — per-subtype mean hub log expression (`subtype_mean_expression` in `module2_integration.yaml`)
- **GLIOMA-TARGET score v1.1** — `results/module7/gts_candidate_table_*_stub.tsv` (`glioma_target_score`, `glioma_target_tier`, sub-norms `gts_sub_*`); high-confidence slice **`results/module7/glioma_target_tier1_welch.tsv`** (tier 1 only). **`docs/GLIOMA_TARGET_SCORE.md`**; **`config/pipeline_inventory.yaml`** → **`primary_deliverables`**. Rule **`m7_gts_candidate_stub`** / `scripts/export_gts_candidate_table.py`. **UHD figures:** `scripts/visualize_glioma_target_results.py` or Snakemake **`m7_visualize_gts_results`** (matplotlib in **`requirements-dev.txt`**). Optional **`rule all`:** set **`GLIOMA_TARGET_INCLUDE_M7_DELIVERABLES=1`** to require figures + Word report + **`glioma_target_deliverables.flag`** in one go (**matplotlib** + **python-docx** from **`requirements-dev.txt`**; do not also set **`GLIOMA_TARGET_INCLUDE_M7_VIZ`** / **`GLIOMA_TARGET_INCLUDE_M7_DOCX`**). Alternatively set **`GLIOMA_TARGET_INCLUDE_M7_VIZ=1`** and/or **`GLIOMA_TARGET_INCLUDE_M7_DOCX=1`** separately for only PNG/PDF/panels/flag or only **`.docx`**.
- **`dea_string_export` jobs** — HGNC lists for **STRING**: `dea_welch_fdr05_symbols_for_string.txt` (FDR), `dea_welch_string_m21_high_confidence.txt`, `dea_welch_string_fdr_lfc_ge_1p5.txt`, `dea_ols_string_m21_high_confidence.txt`, plus DepMap-aware lists `dea_*_string_m21_depmap_crispr_median_lte_minus0p5.txt` (M2.1 screen + median CRISPR ≤ −0.5 on GBM lines); provenance `dea_string_export_provenance.json`
- **`wgcna_hub_subset`** — `results/module4/wgcna_hub_expr_subset.parquet` (genes × TCGA tumor samples, TOIL RSEM TPM) and optional **`wgcna_hub_expr_subset_long.tsv`** (tidy `gene_id`, `sample_id`, `toil_rsem_tpm`); see `wgcna_hub_expr_subset_provenance.json`
- **`wgcna_sample_traits`** — `results/module4/wgcna_hub_sample_traits.tsv` (manifest + Verhaak scores + optional **`verhaak_is_*`** one-hot columns for WGCNA; rows aligned to the WGCNA subset columns by default); provenance `wgcna_hub_sample_traits_provenance.json`
- **`stratified_string_export`** — per-subtype HGNC lists under `results/module4/stratified_string/` (M2.1 screen only: `welch_integrated_m21`, `ols_integrated_m21`; plus DepMap median CRISPR gate: `welch_integrated_m21_depmap`, `ols_integrated_m21_depmap`); provenance `stratified_string_export_provenance.json` (`scripts/export_stratified_dea_string_lists.py`)
- **`gsea_prerank_export`** — `results/module4/gsea/*.rnk` (global Welch/OLS) and **`results/module4/gsea/stratified/{welch_integrated,ols_integrated}/`** (integrated subtype DEA); tab, no header, signed **-log10(p)** rank metric for **GSEA/fgsea**; provenance `gsea_prerank_export_provenance.json` (keys **`jobs`**, **`stratified_jobs`**); touch `gsea_stratified_prerank.flag` (`scripts/export_dea_gsea_prerank_rnk.py`)
- **`module4_export_manifest`** — `results/module4/module4_export_manifest.json` inventories STRING/WGCNA/subtype-mean/stratified-string/GSEA paths and file sizes (`scripts/write_module4_export_manifest.py`)
- `*_provenance.json` sidecars next to each DEA TSV

**Outline M3 (inputs)**

- `results/module3/module3_public_inputs_status.json` — which GEO/Dryad/SRA paths exist under `data_root` (`config/module3_inputs.yaml`)
- `results/module3/module3_sc_workflow_paths_status.json` — optional **Scanpy / Seurat / Visium** working directories under `data_root` (presence only; `module3_inputs.yaml` → `sc_workflow_path_checks`, `scripts/module3_sc_workflow_paths_status.py`, rule **`m3_sc_workflow_paths_status`**)

**Outline M5 (inputs)**

- `results/module5/module5_data_paths_status.json` — LINCS CLUE subset and cmapPy paths under `data_root` (`config/module5_inputs.yaml`)
- `results/module5/cmap_tooling_scan.json` — whether **`cmapPy`** resolves via `importlib.util.find_spec`, plus path-check booleans and optional LINCS signature job counts; if **`results/optional_third_party_functional_report.json`** exists (from **`ensure_optional_third_party_functional`** / **`optional_stack_ci`**), a slim **`optional_third_party_functional`** block (GCT round-trip + binary checks) is merged in (`config/module5_inputs.yaml` → `cmap_tooling_scan.optional_functional_report_json`; **`m5_cmap_tooling_scan`** after **`m5_lincs_disease_signature`**)
- `results/module5/lincs_connectivity_readiness.json` — merged **readiness tier** (signatures on disk + cmap path/import), blockers, and suggested next steps (`module5_inputs.yaml` → `lincs_connectivity_readiness`, `scripts/module5_lincs_connectivity_readiness.py`, rule **`m5_lincs_connectivity_readiness`**)
- `results/module5/lincs_signature_pack.json` — **machine-oriented** list of global + stratified Entrez signature paths with on-disk stats and provenance fields (`lincs_signature_pack`, `scripts/export_module5_lincs_signature_pack.py`, rule **`m5_lincs_signature_pack`**; optional **`defaults_for_connectivity`** in YAML)
- `results/module5/lincs_disease_signature_welch_entrez.tsv`, `lincs_disease_signature_ols_entrez.tsv` — **Entrez × signed −log₁₀(p)** from global DEA (header row; LINCS/cmapPy input side); **stratified** integrated subtype tables under `results/module5/lincs_disease_signature/stratified/{welch_integrated,ols_integrated}/`; `lincs_disease_signature_provenance.json` (`jobs` + `stratified_jobs`), `lincs_stratified_signature.flag`, `scripts/export_module5_lincs_disease_signature.py`, `module5_inputs.yaml` → `lincs_disease_signature`
- `results/module5/module5_export_manifest.json` — sizes / paths for M5 artifacts (`scripts/write_module5_export_manifest.py`, `module5_inputs.yaml` → `module5_export_manifest`)

**Outline M6 (stub)**

- `results/module6/structure_druggability_bridge_welch.tsv`, `structure_druggability_bridge_ols.tsv` — top **GTS tiers** (≤2 by default) capped at **800** rows/job, plus HGNC **Entrez**, **UniProt**, gene name, and **AlphaFold EBI entry URL**; **stratified** mirrors under `results/module6/structure_druggability_bridge_stratified/{welch_integrated,ols_integrated}/` (`*_structure_bridge.tsv`); `structure_druggability_bridge_provenance.json` (`jobs` + **`stratified_jobs`**), `structure_druggability_bridge_stratified.flag` (`config/module6_inputs.yaml`, `scripts/export_module6_structure_druggability_bridge.py`). No pocket or ADMET scoring.

**Outline M7 (GTS v1.1 + reporting)**

- `results/module7/gts_candidate_table_welch_stub.tsv`, `gts_candidate_table_ols_stub.tsv` — HGNC-level candidates with **evidence tiers** (1–4), **v1.1 composite** `glioma_target_score` / `glioma_target_tier` (**E+M+D+N**; see `config/glioma_target_score.yaml`), `signed_neglog10_p`, DepMap CRISPR median, outline M21/M22 flags; **stratified** integrated subtype tables under `results/module7/gts_candidate_stratified/{welch_integrated,ols_integrated}/` (includes **`stratify_subtype`**); `gts_candidate_stub_provenance.json` (`jobs` + **`stratified_jobs`**), `gts_stratified_candidate_stub.flag`; `config/module7_inputs.yaml`, `scripts/export_gts_candidate_table.py`. Outline **S/T/TGTS** modality arms and automated external validation remain **planned** (`config/pipeline_outline.yaml`).
- **Figures + Word in one go:** `snakemake m7_glioma_target_deliverables -c1` or **`GLIOMA_TARGET_INCLUDE_M7_DELIVERABLES=1`** with **`snakemake all`** (after **`requirements-dev.txt`**: matplotlib + python-docx) → UHD PNG/PDF/panels + **`glioma_target_results_report.docx`** + **`glioma_target_deliverables.flag`**.

**Outline M2 §2.2–2.3**

- `results/module3/dea_*_depmap_crispr.tsv` — **DepMap CRISPR** medians; `depmap_crispr_join_provenance.json`
- `results/module3/depmap_gbm_somatic_by_gene.tsv`, `dea_*_depmap_somatic.tsv` — **DepMap somatic** (VEP HIGH/MODERATE); `depmap_somatic_join_provenance.json`
- `results/module3/tcga_gbm_maf_gene_summary.tsv`, `dea_*_tcga_maf.tsv` — optional **TCGA MAF** (`config/tcga_mutation_layer.yaml`)
- `results/module3/dea_*_mutsig.tsv` — optional **MutSig** columns (`config/mutsig_merge.yaml`); `mutsig_join_provenance.json`
- `results/module3/tcga_gbm_verhaak_subtype_scores.tsv` — Verhaak labels (`module2_integration.yaml` / MSigDB or centroid)
- `results/module3/stratified_dea/summary.tsv`, `stratified_dea/dea_welch_subtype_*.tsv` — **subtype-stratified** Welch vs pooled normals
- `results/module3/stratified_ols_dea/summary.tsv`, `stratified_ols_dea/dea_ols_subtype_*.tsv` — **subtype-stratified** OLS vs ref GTEx region + dummies (`config/stratified_dea.yaml`)

Rationale for scale, filters, and OLS vs Welch: **`docs/DEA_METHODOLOGY.md`**. M2 knobs: **`config/module2_integration.yaml`**, **`config/stratified_dea.yaml`**, **`config/tcga_mutation_layer.yaml`**, **`config/mutsig_merge.yaml`**.

## Layout

- `requirements.txt` — core Python + Snakemake
- `requirements-optional.txt` — **cmapPy** (LINCS); **pydeseq2** (count-based DE milestone); functional check via `scripts/ensure_optional_third_party_functional.py`
- `requirements-dev.txt` — **pytest** (optional; for `tests/test_optional_cmap_py_gct_roundtrip.py`)
- `pytest.ini` — test discovery + filters noisy **cmapPy** `FutureWarning`s from `parse_gct`
- `config/third_party_tooling.yaml` — Cell Ranger / Space Ranger / GNINA discovery + `data_root` markers
- `config/config.yaml` — run defaults
- `config/data_sources.yaml` — dataset paths relative to `data_root`
- `config/pipeline_outline.yaml` — seven-module implementation status
- `config/pipeline_planned_extensions.yaml` — outline items beyond current DAG (registry for `pipeline_planned_extensions_report`)
- `config/pipeline_inventory.yaml` — cross-module **`results/pipeline_results_index.json`** (M3–**M7** export manifests + job-list provenance harvest, optional `optional_path_posix`, summary `n_missing_required` / `n_missing_optional`; `scripts/write_pipeline_results_index.py`)
- `config/required_downloads.yaml` — DepMap filenames, reference URLs, GDC toggles
- `config/dea_tumor_normal.yaml` — cohorts, filters, OLS, **outline §2.1 reporting**
- `scripts/download_all_required.py` — full public download orchestrator
- `scripts/build_gdc_gbm_expression_matrix.py` — GDC STAR TPM + counts matrices
- `scripts/extract_toil_gbm_brain_tpm.py`, `scripts/dea_tumor_vs_normal.py`, `scripts/dea_ols_gtex_region_covariate.py`
- `scripts/summarize_expression_cohort.py`, `scripts/validate_gdc_counts_matrix.py`, `scripts/summarize_gdc_counts_cohort.py`, `scripts/dea_deseq2_tcga_primary_recurrent.py`, `scripts/dea_deseq2_tcga_primary_vs_solid_normal.py`, `scripts/tcga_gbm_deseq2_two_group.py`, `scripts/configure_r_for_snakemake.py`, `scripts/install_r_for_snakemake.py`, `scripts/install_r_edger_dependencies.py`, `scripts/install_edger_pkgs.R`, `scripts/install_r_combat_dependencies.py`, `scripts/install_combat_pkgs.R`, `scripts/combat_seq_tcga_gbm_subset.R`, `scripts/edger_tcga_gbm_two_group.R`, `scripts/module3_public_inputs_status.py`, `scripts/module3_sc_workflow_paths_status.py`, `scripts/module5_data_paths_status.py`, `scripts/module5_cmap_tooling_scan.py`, `scripts/module5_lincs_connectivity_readiness.py`, `scripts/export_module5_lincs_disease_signature.py`, `scripts/export_module5_lincs_signature_pack.py`, `scripts/write_module5_export_manifest.py`, `scripts/join_dea_outline_driver_flags.py`
- `scripts/depmap_shared.py`, `scripts/join_dea_depmap_crispr.py`, `scripts/join_dea_depmap_somatic.py`, `scripts/tcga_maf_gene_cohort_summary.py`, `scripts/join_dea_tcga_maf.py`, `scripts/join_dea_mutsig.py`, `scripts/join_stratified_dea_integration.py`, `scripts/mean_expression_by_verhaak_subtype.py`, `scripts/dea_string_filters.py`, `scripts/export_dea_string_gene_list.py`, `scripts/export_stratified_dea_string_lists.py`, `scripts/export_dea_gsea_prerank_rnk.py`, `scripts/export_wgcna_hub_subset.py`, `scripts/export_wgcna_sample_traits.py`, `scripts/write_module4_export_manifest.py`, `scripts/export_gts_candidate_table.py`, `scripts/write_module7_export_manifest.py`, `scripts/module6_structure_tooling_paths_status.py`, `scripts/export_module6_structure_druggability_bridge.py`, `scripts/write_module6_export_manifest.py`, `scripts/score_gbm_verhaak_subtypes.py`, `scripts/dea_stratified_by_subtype.py`, `scripts/dea_stratified_ols_by_subtype.py`
- `config/module2_integration.yaml`, `config/stratified_dea.yaml`, `config/tcga_mutation_layer.yaml`, `config/mutsig_merge.yaml`, `config/module3_inputs.yaml`, `config/module5_inputs.yaml`, `config/module6_inputs.yaml`, `config/module7_inputs.yaml`, `config/gbm_verhaak_signatures.yaml`
- `references/gbm_known_drivers_outline.yaml`
- `docs/PIPELINE_ALIGNMENT.md`, `docs/DEA_METHODOLOGY.md`, `docs/OPTIONAL_SLICES.md`
- `scripts/write_pipeline_results_index.py` — merge M4–M7 export manifests + selected provenance paths; fresh `exists` / size / mtime
- `scripts/verify_python_environment.py`, `scripts/install_optional_third_party.py`, `scripts/ensure_optional_third_party_functional.py`, `scripts/run_optional_stack_ci.py`, `scripts/run_windows_outline_gate.py`, `scripts/run_supplementary_enrichment_smoke.py`, `scripts/verify_optional_third_party_tooling.py`, `scripts/snakemake_subprocess_env.py` — env + optional cmapPy / tooling checks; gate + supplementary smoke call Snakemake with **`snakemake_subprocess_env`** (drops optional **`GLIOMA_TARGET_INCLUDE_*`** for those runs)
- `Snakefile` — Snakemake DAG (`verify_python_environment`, `optional_third_party_python_stack`, `optional_stack_ci`, `verify_optional_third_party_tooling`, …)
