# GBM Detection data root + programmatic open data

## Shared tree with GBM Detection

`config/data_sources.yaml` sets **`data_root`** to the same base directory as the **GBM Detection** project (default `G:/GBM Detection/data`). **`GLIOMA_TARGET_DATA_ROOT`** overrides it when set.

**Use one tree** so that:

- Legacy **TCGA-GBM** UUID-style folders, **GEO**, **SRA**, **Dryad**, and any companion-project mirrors stay in predictable paths (`data_sources.yaml` documents each).
- This repo’s **`scripts/download_all_required.py`** adds **DepMap**, **GDC open STAR counts**, **TOIL Xena**, **references**, **recount3** (optional), **git pipeline clones**, **LINCS CLUE** (optional token), **MOVICS staging**, optional **supplementary references** (Expression Atlas gene slices, ARCHS4/recount matrices, pathway GMTs, ChEMBL + DGIdb, ClinVar + gnomAD), and optional **high-value public layers** (pharmacogenomics, methylation betas, scRNA reference mirrors) without duplicating large cohorts.

## Core orchestrator

```text
python scripts/download_all_required.py
```

Common flags:

| Flag | Purpose |
|------|---------|
| `--with-recount3-de-counts` | recount3 G029 TCGA-GBM + GTEx brain gene sums (count-based DE). |
| `--with-movics-staging` | DepMap MAE `.tsv.gz` + optional CGGA HTTP + CBTTC readme. |
| `--with-open-extensions` | Extra open files from **`config/open_source_data_extensions.yaml`** (below). |
| `--with-high-value-datasets` | **GDSC**, **PRISM** (DepMap file index), **Open Targets** targets JSON shard, **GDC** open TCGA-GBM **methylation beta** TXT, **CELLxGENE Census** h5ad on public S3, **CGGA** via **`fetch_movics_staging_data`** if URLs are set — see **`config/high_value_public_datasets.yaml`**. |
| `--skip-high-value-gdc-methylation` | With **`--with-high-value-datasets`**, skips the large GDC methylation phase (smoke tests). |
| `--with-supplementary-reference-resources` | **Expression Atlas** per-gene TSVs, **ARCHS4/recount** GTEx + TCGA HDF5 matrices (~1.3 GB), **WikiPathways** + **PathwayCommons** GMTs, **ChEMBL** UniProt map + **DGIdb** tables, **ClinVar** gene summary, **gnomAD** LOF-by-gene — see **`config/supplementary_reference_resources.yaml`**. |
| `--skip-supplementary-archs4` | With the flag above, skips **`gtex_matrix.h5`** / **`tcga_matrix.h5`** (CI / smoke). |
| `--with-string` | STRING protein links (large). |
| `--skip-clue` | Skip LINCS / CLUE even if a key is set (default: run CLUE when `CLUE_API_KEY` or `CLUE_API_TOKEN_FILE` is set). |

Report: **`results/download_all_report.json`**.

### LINCS / CLUE (API key)

1. Request a free academic **`user_key`** from [CLUE / clue.io](https://clue.io/) (API base: `https://api.clue.io`).
2. Export **`CLUE_API_KEY`** or put the key in a file outside the repo and set **`CLUE_API_TOKEN_FILE`** to that path (first line = key). See **`.env.example`**.
3. Refresh snapshots only: **`python scripts/fetch_clue_api_subset.py`** (writes under **`lincs/clue_api_subset/`** per **`config/required_downloads.yaml`** `clue_api.snapshots`), or run the full orchestrator without **`--skip-clue`**.

Never commit keys; **`.env`**, **`.clue_key`**, and similar patterns are in **`.gitignore`**.

## Open-source extensions catalog

**`config/open_source_data_extensions.yaml`** lists additional **HTTPS** (and optional **GEO**) downloads useful for enrichment, immune context, and drug–gene priors:

- **MSigDB** Hallmark + C6 oncogenic GMTs (symbols) — optional rows include **Reactome** (`c2.cp.reactome`), **KEGG legacy** (`c2.cp.kegg_legacy`), and more (see Broad release listing for exact filenames).
- **MCP-counter** `Signatures/genes.txt` (GitHub raw) — cell-type deconvolution context; saved under `references/cell_deconvolution/mcpcounter/genes.txt`.
- **CTD** chemical–gene (`CTD_chem_gene_ixns.tsv.gz`, ~**42 MB** compressed on the wire; expands to a very large TSV) and **gene–pathway** (`CTD_genes_pathways.tsv.gz`).
- **GEO** under **`geo_series`** — GSE list in **`config/open_source_data_extensions.yaml`**; pulls **matrix** + **soft** `.gz` from NCBI FTP into **`geo/bulk_microarray/<GSE>/`** (same helper as **`geo_bulk_series`** in **`required_downloads.yaml`**).

Standalone:

```text
python scripts/download_open_source_extensions.py
python scripts/download_open_source_extensions.py --dry-run
python scripts/download_open_source_extensions.py --only msigdb_hallmark_hs_symbols
```

Report: **`results/open_source_extensions_download_report.json`**.

**MSigDB license:** academic/non-commercial terms apply — [GSEA MSigDB license](https://www.gsea-msigdb.org/gsea/msigdb/license.jsp).

## High-value public datasets (pharmacogenomics, methylation, scRNA reference)

**`config/high_value_public_datasets.yaml`** drives **`scripts/download_high_value_public_datasets.py`**:

| Layer | Source | Layout under `data_root` |
|--------|--------|---------------------------|
| **GDSC** fitted dose–response | Sanger **cog.sanger.ac.uk** release 8.5 CSVs | `pharmacogenomics/gdsc/` |
| **PRISM** primary + secondary | **DepMap** public files CSV → Figshare URLs | `pharmacogenomics/prism_depmap/primary`, `.../secondary` |
| **Open Targets** targets (one JSON part) | **EBI FTP** platform release | `pharmacogenomics/open_targets/` |
| **GDC** methylation beta | **GDC API** open TCGA-GBM TXT (sesame level 3 betas) | `gdc/tcga_gbm_open_methylation_beta/` |
| **CELLxGENE Census** h5ad | **AWS S3** `cellxgene-data-public` census path | `references/scrna_cellxgene_census/` |
| **CGGA** | Portal HTTPS URLs in **`m2_movics_data_fetch.yaml`** | `cohorts/cgga_expression/` |

Standalone:

```text
python scripts/download_high_value_public_datasets.py
python scripts/download_high_value_public_datasets.py --dry-run
python scripts/download_high_value_public_datasets.py --skip-gdc-methylation
```

Report: **`results/high_value_public_datasets_report.json`**.

**CGGA** has no fixed open bulk URL: copy fresh **HTTPS** links from the [CGGA download page](http://www.cgga.org.cn/download.jsp) into **`cgga_http`** in **`config/m2_movics_data_fetch.yaml`**, then run the high-value script (or **`fetch_movics_staging_data.py`**) so files land under **`cohorts/cgga_expression/`**.

## Supplementary reference resources (pathways, drug–target, variant context, bulk RNA context)

**`config/supplementary_reference_resources.yaml`** drives **`scripts/download_supplementary_reference_resources.py`**: ARCHS4/recount GTEx + TCGA HDF5, Expression Atlas gene TSVs, WikiPathways + PathwayCommons GMTs, ChEMBL UniProt map + DGIdb, ClinVar gene summary, gnomAD LOF-by-gene; **DrugCentral** dump is optional (`--with-drugcentral` on the script).

Standalone:

```text
python scripts/download_supplementary_reference_resources.py
python scripts/download_supplementary_reference_resources.py --dry-run
python scripts/download_supplementary_reference_resources.py --skip-archs4-h5
python scripts/download_supplementary_reference_resources.py --with-drugcentral
```

Report: **`results/supplementary_reference_resources_report.json`**. After a successful run, confirm **`errors`** is **`[]`**.

**Snakemake:** rule **`supplementary_reference_resources_paths_status`** writes **`results/module3/supplementary_reference_resources_paths_status.json`** (paths from **`config/data_sources.yaml`**). Rule **`m4_pathway_database_mirror_paths_status`** includes group **`supplementary_open_pathway_gmts`** for the two GMT files.

**WikiPathways** GMT URLs are date-pinned; if a download 404s, pick the current **`wikipathways-*-gmt-Homo_sapiens.gmt`** from [WikiPathways GMT downloads](https://wikipathways-data.wmcloud.org/current/gmt/) and update the YAML.

**PathwayCommons** PC12 “All hgnc” gene sets are stored as **`PathwayCommons12.All.hgnc.gmt.gz`** (gzip) from [Bader Lab PathwayCommons mirrors](https://download.baderlab.org/PathwayCommons/PC2/v12/) — the old **`pathwaycommons.org/archives/...`** link redirects to an HTML index, not the GMT bytes.

**Snakemake wiring (optional):** full table of **`GLIOMA_TARGET_INCLUDE_*`** flags (supplementary, ClinVar, MOVICS, M7, etc.) and subprocess-env behavior: **[OPTIONAL_SLICES.md](OPTIONAL_SLICES.md)**. Set **`GLIOMA_TARGET_INCLUDE_SUPPLEMENTARY_WIRING=1`** so **`rule all`** also builds:

- **`install_r_supplementary_enrichment`** (Bioconductor **fgsea**, **clusterProfiler**, **enrichplot**, **org.Hs.eg.db**, **data.table**) — requires **R** + **`Rscript`** on **`PATH`** (or **`config/config.yaml`** **`rscript`**). Programmatic install: **`python scripts/install_r_supplementary_dependencies.py`**. Supplementary smoke: **`python scripts/run_supplementary_enrichment_smoke.py`** — by default **does not** copy demo files into **`results/`** (avoids overwriting real TOIL DEA); use **`--copy-demo-results`** on a clean clone or in CI only. Uses **`snakemake --allowed-rules`** so the demo path does not schedule stratified DEA. **ARCHS4** accuracy: **`python scripts/download_supplementary_reference_resources.py`** without **`--skip-archs4-h5`** (or **`download_all_required.py --with-supplementary-reference-resources`** without **`--skip-supplementary-archs4`**) for **`gtex_matrix.h5`** / **`tcga_matrix.h5`**. **CLUE / LINCS**: **`CLUE_API_KEY`** or **`CLUE_API_TOKEN_FILE`** (see **`.env.example`**), then **`python scripts/fetch_clue_api_subset.py`** or **`download_all_required.py`**. Cluster notes: **`docs/SNAKEMAKE_HPC.md`**.
- **`sync_wikipathways_gmt_url_report`** (writes **`results/reports/wikipathways_gmt_url_sync.json`**; use **`python scripts/sync_wikipathways_gmt_url.py --write-yaml`** with **`GLIOMA_TARGET_WIKIPATHWAYS_SYNC_YAML=1`** to patch the YAML when the index moves).
- **`check_wikipathways_gmt_url`**, **`pathwaycommons_hgnc_gmt_plain`**, **`m4_supplementary_open_enrichment_plan`**, **`m4_clusterprofiler_supplementary_plan`**, **`m4_run_fgsea_supplementary_pathways`** → **`results/module4/gsea/fgsea_supplementary_pathways_results.tsv`**, **`m4_run_clusterprofiler_supplementary_pathways`** → **`results/module4/gsea/clusterprofiler_supplementary_enricher.tsv`**, **`archs4_recount_h5_summary`** (HDF5 inventory) and **`archs4_outline_driver_expression_context`** (driver-level summary), **`m4_join_dea_archs4_expression`** (joins cohort marginals onto Welch/OLS + recount3 DEA tables; **`results/module3/dea_archs4_join_provenance.json`**), **`drugcentral_postgres_load_status`** (skipped unless **`GLIOMA_TARGET_DRUGCENTRAL_LOAD=1`**).

**Windows:** set **`PYTHONUTF8=1`** or use **`scripts/run_snakemake_all_windows.ps1`** for long **`snakemake all`** runs. If a run dies mid-file, **`snakemake --unlock`** then **`snakemake --rerun-incomplete`**.

**DrugCentral → PostgreSQL:** with **`GLIOMA_TARGET_DRUGCENTRAL_LOAD=1`**, the **`drugcentral_postgres_load_status`** rule runs **`load_drugcentral_postgres.py`** ( **`psql`** + **`PG*`** ). Manual: **`python scripts/load_drugcentral_postgres.py --database drugcentral --create-db`**.

## Adding more data

1. **GEO:** add GSE IDs under **`geo_series`** in `open_source_data_extensions.yaml` and set **`enabled: true`**, or extend **`geo_bulk_series`** in **`config/required_downloads.yaml`** for the main orchestrator.
2. **CGGA / controlled cohorts:** add **`cgga_http`** rows in **`config/m2_movics_data_fetch.yaml`**, then use **`--with-high-value-datasets`** or **`fetch_movics_staging_data.py`**; respect CGGA terms of use.
3. **New HTTPS files:** append a **`downloads`** row with `url`, `dest` (relative to `data_root`), and `enabled: true` in **`open_source_data_extensions.yaml`**, or extend **`high_value_public_datasets.yaml`** / **`supplementary_reference_resources.yaml`**.
