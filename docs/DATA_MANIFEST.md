# Data manifest (GLIOMA-TARGET ↔ GBM Detection)

Root directory: `G:\GBM Detection\data` (override with `GLIOMA_TARGET_DATA_ROOT`). **Same tree as the GBM Detection project** — see **`docs/GBM_DETECTION_AND_OPEN_DATA.md`** for orchestration and optional open-source extensions (MSigDB, MCP-counter, etc.).

For how each dataset supports the **seven-module project outline**, see **`docs/PIPELINE_ALIGNMENT.md`** and **`config/pipeline_outline.yaml`**.

## TCGA

- **Path:** `tcga/TCGA-GBM/`
- **Contents:** Many UUID-named case directories (thousands of folders), consistent with a GDC-style mirror.
- **Pipeline use:** Module 1 (harmonization), Module 2 (bulk expression, mutation, CNV when matched to file types inside each case). You will need the companion project’s sample ↔ file map or GDC metadata to select RNA-seq, WXS, etc.

## GEO — epigenetic

| Series | Path |
|--------|------|
| GSE100351 | `geo/epigenetic/GSE100351/` (series matrices, SOFT, RAW tar, extracted) |
| GSE139136 | `geo/epigenetic/GSE139136/` |

**Use:** Methylation / epigenetic layers; Module 1–2 filters (e.g. promoter hypermethylation exclusion).

## GEO — external validation

| Series | Path |
|--------|------|
| GSE154795 | `geo/external_validation/GSE154795/` (processed matrix) |

**Use:** Independent bulk or processed validation cohort for expression signatures.

## GEO — single-cell RNA-seq

| Series | Path | Notes |
|--------|------|--------|
| GSE131928 | `geo/scrna_seq/GSE131928/` | RAW tar, series matrix, cell metadata xlsx |
| GSE141946 | `geo/scrna_seq/GSE141946/` | counts + metadata gz |
| GSE57872 | `geo/scrna_seq/GSE57872/` | GBM matrix + series matrix |

**Use:** Module 3 (cell states, pseudotime), Module 5C (surface / state coverage).

## GEO — spatial

| Series | Path |
|--------|------|
| GSE287631 | `geo/spatial/GSE287631/` | Excel-based spatial / WTA exports |

**Use:** Spatial niche analysis (Module 3.2); format-specific parsers TBD.

## SRA workflow output (GSE57872)

- **Path:** `sra/GSE57872/`
- **Subdirs:** `fastq/` (per-SRR folders), `counts/` (e.g. `GSE57872_counts_matrix.csv.gz`, STAR outputs)

**Use:** Reuse quantified expression without re-downloading; align with GEO metadata for sample labels.

## Dryad — spatial multi-omics (Freiburg)

- **Path:** `dryad/spatial_gbm/`
- **Citation:** Ravi et al., *Spatially resolved multi-omics deciphers bidirectional tumor-host interdependence in glioblastoma*, Dryad, [10.5061/dryad.h70rxwdmj](https://doi.org/10.5061/dryad.h70rxwdmj)

| Subfolder | Modality |
|-----------|----------|
| `10XVisium 2/` | Visium Space Ranger outputs per sample (`#UKF*_ST`) |
| `scTumor_Tissue/` | Tumor scRNA (`#UKF*_T_SCRNA`) |
| `scSlices_Environment/` | Environment / slice scRNA |
| `Methylation/` | Methylation (`raw/`, `Meta.csv`) |
| `IMC_1/` | Imaging mass cytometry (`raw/`) |
| `MALDI_1/` | MALDI (`raw/`) |

**Use:** Module 3 (spatial + sc integration, niche programs), Module 4 (SCENIC+ if ATAC matched elsewhere), high-value **matched** multi-omics within one study.

## GEO — bulk microarray (outline cohorts)

Downloaded under `geo/bulk_microarray/<GSE>/` (matrix + soft) via `scripts/download_external_datasets.py`.

| Series | Path |
|--------|------|
| GSE4290 | `geo/bulk_microarray/GSE4290/` |
| GSE7696 | `geo/bulk_microarray/GSE7696/` |
| GSE50161 | `geo/bulk_microarray/GSE50161/` |
| GSE68848 | `geo/bulk_microarray/GSE68848/` |

**Use:** Module 2 bulk DEA / validation alongside TCGA; harmonize probesets across platforms before meta-analysis.

## GTEx / TCGA reference expression (TOIL Xena)

| File | Path |
|------|------|
| Sample phenotype | `gtex/xena_toil/TcgaTargetGTEX_phenotype.txt.gz` |
| Gene TPM (TCGA + GTEx) | `gtex/xena_toil/TcgaTargetGtex_rsem_gene_tpm.gz` (~1.23 GB decompressed stream; gz ~1.3 GB) |

**Source:** [UCSC Xena TOIL RNA-seq hub](https://xenabrowser.net/) — `toil.xenahubs.net`.

**Use:** Module 2 tumor vs normal brain controls (filter phenotype to CNS / frontal cortex as needed); cross-cohort normalization required when mixing with array data.

## DepMap (Broad Institute)

Fetched via `GET https://depmap.org/portal/api/download/files` (CSV of filenames, MD5, and **time-limited** Google Cloud HTTPS links). The orchestrator picks the newest `DepMap Public YYQq` release unless `config/required_downloads.yaml` sets `depmap.prefer_release`.

Typical layout:

`depmap/depmap_public_25q3/Model.csv`, `CRISPRGeneEffect.csv`, `CRISPRGeneDependency.csv`, `OmicsExpressionTPMLogp1HumanProteinCodingGenes.csv`, `OmicsSomaticMutations.csv`, `PortalOmicsCNGeneLog2.csv`, plus `download_manifest.json`.

**Use:** Module 4–5 synthetic lethality, expression, mutation context for cell-line–grounded priors.

## DepMap-derived multi-omics MAE (MOVICS staging)

Built under **`{data_root}/omics/multi_omics_mae/`** by **`scripts/fetch_movics_staging_data.py`** (or **`snakemake fetch_movics_staging_data`**) after DepMap CSVs are present — see **`config/m2_movics_data_fetch.yaml`**.

| File | Description |
|------|-------------|
| `depmap_gbm_expression_logtpm.tsv.gz` | Genes × ModelID; log1p TPM (protein-coding subset from DepMap expression file) |
| `depmap_gbm_cnv_log2.tsv.gz` | Same gene × model grid; log₂ copy-ratio style values from `PortalOmicsCNGeneLog2.csv` |
| `depmap_gbm_mutation_binary.tsv.gz` | Binary mutation presence (0/1) per gene × model from `OmicsSomaticMutations.csv` |
| `depmap_gbm_sample_manifest.tsv` | ModelID list + cohort label |
| `depmap_mae_provenance.json` | Row counts, release path, `mutation_matrix_filter`, optional `outline_drivers_in_expr_cn_universe` |

Gene selection (see **`config/m2_movics_data_fetch.yaml`**): **GBM outline drivers** from **`references/gbm_known_drivers_outline.yaml`** are **prioritized** in the expr∩CN universe, then high-variance genes fill to **`max_genes`**; mutation rows are optionally restricted to **variable** binaries across models for a cleaner MOVICS binomial layer.

**Use:** Module 2.3 three-view **`MOVICS::getIntNMF`** via Snakemake rule **`m2_movics_intnmf_depmap_mae`** (config **`config/m2_movics_depmap_mae_run.yaml`**; optional **`GLIOMA_TARGET_INCLUDE_MOVICS_DEPMAP_MAE=1`**). These are **cell-line** models, not TCGA tumors — **do not treat cluster IDs as comparable** to **`m2_movics_intnmf_tcga_gbm`** (TPM + counts on GDC STAR).

After IntNMF, **`snakemake m2_movics_depmap_intnmf_characterize`** writes **`results/module3/m2_movics_intnmf_depmap_mae/cluster_model_annotations.tsv`** (clusters × `Model.csv` fields) and **`cluster_summary.json`** (lineage mix, mutation burden, optional CRISPR means).

## GDC (NCI) — open TCGA-GBM RNA quantification

`gdc/tcga_gbm_open_star_counts/` contains **391** `*.rna_seq.augmented_star_gene_counts.tsv` files and `gdc_files_manifest.json` (full `file_id` / `md5sum` / size metadata from `POST https://api.gdc.cancer.gov/files`).

**Use:** Harmonized gene counts aligned with GDC pipelines (complement legacy UUID-folder mirrors under `tcga/TCGA-GBM`).

`gdc/tcga_gbm_open_methylation_beta/` (optional) holds **open** TCGA-GBM **methylation beta** TXT files (Illumina arrays; GDC `data_type` = Methylation Beta Value) plus `gdc_methylation_files_manifest.json`, staged by **`scripts/download_high_value_public_datasets.py`** or **`download_all_required.py --with-high-value-datasets`**.

Under **`pharmacogenomics/`** (same orchestrator): **GDSC** fitted dose-response CSVs, **PRISM** primary/secondary repurposing tables (URLs from the DepMap files API), and an **Open Targets** targets JSON shard. **`references/scrna_cellxgene_census/`** holds CELLxGENE Census **h5ad** mirrors from public S3. See **`config/high_value_public_datasets.yaml`**.

**Supplementary references** (optional **`scripts/download_supplementary_reference_resources.py`** or **`download_all_required.py --with-supplementary-reference-resources`**): **`references/archs4_recount/`** (GTEx + TCGA HDF5), **`references/expression_atlas_genes/`**, **`references/pathways/`** (WikiPathways GMT + PathwayCommons **`PathwayCommons12.All.hgnc.gmt.gz`** from Bader Lab), **`references/drug_target/`** (ChEMBL UniProt map), **`references/dgidb/`**, **`references/clinvar/`**, **`references/gnomad/`**, optional **`references/drugcentral/`**. Paths are listed in **`config/data_sources.yaml`** under **`references.*`** and driven by **`config/supplementary_reference_resources.yaml`**.

## Derived matrices (this repo, `results/`)

Built by `scripts/build_gdc_gbm_expression_matrix.py` (or Snakemake rule `tcga_gbm_tpm_matrix`):

| Output | Description |
|--------|-------------|
| `results/module2/tcga_gbm_star_tpm_matrix.parquet` | Protein-coding genes × samples; values = `tpm_unstranded` |
| `results/module2/tcga_gbm_sample_meta.tsv` | Column names ↔ GDC `file_id`, TCGA case/sample barcodes |
| `results/module1/gdc_file_case_metadata.json` | Cache of per-file GDC case/sample metadata |

## Module 3 — TOIL-based tumor vs normal DEA

| Output | Description |
|--------|-------------|
| `results/module3/toil_gbm_vs_brain_tpm.parquet` | TOIL hub values (log₂(TPM+0.001)) for GBM primary + GTEx cortex normals |
| `results/module3/toil_gbm_vs_brain_samples.tsv` | Sample ↔ group |
| `results/module3/dea_gbm_vs_gtex_brain.tsv` | Welch t-test + BH-FDR; see `docs/DEA_METHODOLOGY.md` |

## Reference files

| File | Source |
|------|--------|
| `references/gencode.v44.annotation.gtf.gz` | [GENCODE v44](https://www.gencodegenes.org/) via EBI FTP |
| `references/hgnc_complete_set.txt` | [HGNC](https://www.genenames.org/download/) public Google Cloud Storage |
| `references/hg38-blacklist.v2.bed.gz` | [Boyle-Lab/Blacklist](https://github.com/Boyle-Lab/Blacklist) (GitHub raw) |

## Public pipelines (`git clone --depth 1`)

Populated by `scripts/download_all_required.py` when `git` is on PATH (see `config/required_downloads.yaml` → `git_pipelines`).

| Path | Upstream |
|------|----------|
| `pipelines/nf-core-rnaseq` | [nf-core/rnaseq](https://github.com/nf-core/rnaseq) |
| `pipelines/nf-core-scrnaseq` | [nf-core/scrnaseq](https://github.com/nf-core/scrnaseq) |
| `pipelines/nf-core-fetchngs` | [nf-core/fetchngs](https://github.com/nf-core/fetchngs) |
| `pipelines/cmapPy` | [cmap/cmapPy](https://github.com/cmap/cmapPy) (LINCS GCT/GCTX I/O) |

## LINCS / CLUE API subset

When `CLUE_API_KEY` or `CLUE_API_TOKEN_FILE` (first line = key; file **outside** the git repo) is set, JSON snapshots are saved under `lincs/clue_api_subset/` via `GET https://api.clue.io/...` with the `user_key` header. This is a **small** metadata/signature slice (e.g. L1000 landmark genes, temozolomide-related `sigs` / `perts`), not the full expression matrix.

## Not automated (access / registration)

- **CGGA** — apply at [CGGA portal](http://www.cgga.org.cn/); add `cgga/` under `data_root` and extend `config/data_sources.yaml`.
- **CPTAC-GBM** — GDC with controlled-access acknowledgment; use `gdc-client` with a manifest.
- **Bulk L1000 GCTX / full signature matrices** — use [CLUE Data Library](https://clue.io/data/GCTX), BigQuery (`cmapBQ`), or controlled exports; not mirrored by the JSON subset step.

Add entries to `config/data_sources.yaml` when these are available locally.

## In-repo scaffolding (not under `data_root`)

- **`results/module3/m3_deconvolution_s2/`** — S2 **scipy NNLS** spot fractions + provenance from **`m3_deconvolution_s2_nnls`** (**`config/m3_deconvolution_s2_nnls.yaml`**, **`scripts/run_m3_deconvolution_s2_nnls.py`**). Requires **real** wide TSVs under **`data_root`** (see YAML). Optional **`rule all`:** **`GLIOMA_TARGET_INCLUDE_M3_DECONV_S2=1`**. **`m3_deconvolution_integration_stub`** echoes a successful run in **`m3_deconvolution_s2_nnls_echo`**.
- **`results/module3/m3_deconvolution_rctd/`** — RCTD hook from **`m3_deconvolution_rctd_run`** (**`--use-conda`**, **`workflow/envs/m3_rctd.yaml`**); RDS inputs under **`data_root`** per **`config/m3_deconvolution_rctd_inputs.yaml`**. **`rctd_run_provenance.json`** always records **`artifact_kind`**, **`status`** (`ok` \| `rds_load_failed` \| `spacexr_missing` \| `create_failed`), and load / **`spacexr`** / **`create.RCTD`** fields from **`scripts/run_m3_rctd_wrapper.R`**. **`rctd_run.flag`** is written only when **`status`** is **`ok`**; the wrapper removes any prior flag at startup and exits **1** when **`status`** is not **`ok`**, so Snakemake does not treat a failed RCTD attempt as a successful rule (same idea as **`cell2location_run.flag`**). Optional **`rule all`:** **`GLIOMA_TARGET_INCLUDE_M3_RCTD_RUN=1`**.
- **`results/module3/m3_deconvolution_cell2location/`** — Provenance + flag from **`m3_deconvolution_cell2location_run`**; inputs under **`data_root`** per **`config/m3_deconvolution_cell2location_inputs.yaml`**. **`cell2location_run_provenance.json`** uses **`status`**: **`inputs_ok`** (validate-only), **`trained_ok`**, or **`training_failed`** (import failure, exception, or non-zero training exit). **`cell2location_run.flag`** is written only on exit **0**; **`training_failed`** paths remove any existing flag so Snakemake is not fooled by a prior success. On training path failures after **`RegressionModel.export_posterior`**, provenance may include **`signature_extract_diagnostic`** (AnnData layout snapshot) and **`signature_extract_error`**, or **`gene_intersection_diagnostic`** (spatial vs signature gene counts) when intersection falls below **`min_shared_genes`**. When **`training.enabled`** is true, also **`spatial_cell2location.h5ad`** and **`spot_cell_abundance_means.tsv`** (paths configurable in YAML); the Snakefile declares those paths as rule outputs only when **`training.enabled`** is true at workflow parse time. Optional **`rule all`:** **`GLIOMA_TARGET_INCLUDE_M3_CELL2LOCATION_RUN=1`**.
- **`results/module3/module3_export_manifest.json`** — Curated inventory ( **`scripts/write_module3_export_manifest.py`** ); includes RCTD + Cell2location run paths as **optional** manifest rows (**`module3_inputs.yaml`** → **`module3_export_manifest.optional_tags`**). Those rows are **not** named inputs on Snakemake **`m3_export_manifest`** (see **`_ARTIFACTS_EXEMPT_FROM_SNAKEFILE_MANIFEST_INPUTS`** in the writer) so **`snakemake --dry-run`** for **`pipeline_results_index`** does not schedule optional conda deconv rules when RDS/h5ad are absent.
- **`results/module3/m3_deconvolution_integration_stub.json`** — **`scripts/module3_deconvolution_integration_stub.py`** checklist includes RCTD flags (**`rctd_provenance_present`**, **`rctd_rds_loaded`**, **`rctd_create_ok`**, **`rctd_run_status`**) and Cell2location (**`cell2location_run_status`**, **`in_repo_cell2location_trained`**, **`cell2location_training_outputs_in_provenance`**, **`cell2location_has_signature_extract_diagnostic`**, **`cell2location_has_gene_intersection_diagnostic`**); **`recommended_next_steps`** adds RCTD / Cell2location hints from **`rctd_followup_messages`** and **`cell2location_followup_messages`** (including summaries when **`cell2location_run_provenance.json`** records layout / intersection diagnostics).
- **`results/module3/m3_repo_scrna_spatial_integration_stub.json`** — **`scripts/m3_repo_scrna_spatial_integration_stub.py`**; **`m3_deconvolution_integration_stub_echo`** carries **`readiness_tier`**, **`artifact_kind`**, and checklist-derived **`in_repo_cell2location_or_rctd`**, **`cell2location_run_status`**, **`cell2location_has_signature_extract_diagnostic`**, **`cell2location_has_gene_intersection_diagnostic`**, and **`rctd_run_status`** from **`m3_deconvolution_integration_stub.json`** when that file exists.
- **`results/module3/m3_repo_deconvolution_integration_stub.json`** — **`scripts/m3_repo_deconvolution_integration_stub.py`** (after **`m3_deconvolution_integration_stub`** + **`m3_repo_scrna_spatial_integration_stub`**) includes **`m3_deconvolution_integration_stub_echo`**: **`readiness_tier`**, **`artifact_kind`**, full **`checklist`**, and **`n_recommended_next_steps`** from the main deconvolution stub JSON for manifest / cross-slice consumers.
- **`results/module5/m5_srges_compound_ranks.tsv`** — compound ranking from **`m5_srges_run`** (**`config/m5_srges.yaml`**, **`scripts/run_m5_srges.py`**) using **real** long-format **`perturbation_tsv`** under **`data_root`**. Optional **`rule all`:** **`GLIOMA_TARGET_INCLUDE_M5_SRGES_RUN=1`**. Stage cmapPy/CLUE mirror exports under **`{data_root}/lincs/srges_rank_score_exports`** for **`m5_srges_output_paths_status`**.
