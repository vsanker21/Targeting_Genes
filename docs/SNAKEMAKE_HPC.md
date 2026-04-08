# Snakemake on workstations and HPC clusters

This pipeline is developed on Windows and Linux. On clusters, run Snakemake from a **login or submit node** with network access to your **`GLIOMA_TARGET_DATA_ROOT`** (shared filesystem recommended).

## Minimal proof run (no full TCGA/GTEx mirrors)

Committed demo files under **`references/demo_supplementary/`** provide tiny pathway GMTs, HGNC rows, DEA, and prerank so **fgsea** and **clusterProfiler** can run end-to-end:

1. Install R, then Bioconductor stack:

   ```bash
   python scripts/install_r_supplementary_dependencies.py
   ```

2. Run the isolated smoke workflow (does **not** pull stratified DEA / prerank export):

   ```bash
   # Default: leave results/ unchanged — require real Welch DEA + prerank already present.
   python scripts/run_supplementary_enrichment_smoke.py

   # Clean clone / CI: copy tiny demo DEA + prerank from references/demo_supplementary/repo_results/
   python scripts/run_supplementary_enrichment_smoke.py --copy-demo-results
   ```

   Options: **`--dry-run`**, **`--incremental`** (omit **`--forcerun`**). **`--copy-demo-results`** will **not** overwrite an existing large **`dea_gbm_vs_gtex_brain.tsv`** (≥200 lines) unless **`--force-demo-copy`**. Deprecated: **`--skip-copy-results`** (same as default).

   The smoke driver sets **`GLIOMA_TARGET_DATA_ROOT`** to the demo tree unless you already exported that variable.

   The smoke driver passes Snakemake a subprocess environment that **drops optional `rule all` gates** (`GLIOMA_TARGET_INCLUDE_*`; see **`scripts/snakemake_subprocess_env.py`**) so **`--dry-run`** does not inherit e.g. M7 figure/docx flags from your shell.

   The demo prerank **`.rnk`** (under **`references/demo_supplementary/repo_results/`**, used only with **`--copy-demo-results`**) mixes **positive and negative** signed −log10(p)–style statistics so **fgsea** does not warn that all ranked values are on one side of zero.

3. **ARCHS4 HDF5** (accurate **`m4_join_dea_archs4_expression`**): ensure **`{data_root}/references/archs4_recount/gtex_matrix.h5`** and **`tcga_matrix.h5`**. Download (large; existing files are skipped):

   ```bash
   python scripts/download_supplementary_reference_resources.py
   ```

   Use **`download_all_required.py --with-supplementary-reference-resources`** without **`--skip-supplementary-archs4`** for the same matrices.

4. **LINCS / CLUE** snapshots under **`data_root/lincs/`**: set **`CLUE_API_KEY`** or **`CLUE_API_TOKEN_FILE`** (see **`.env.example`**), then **`python scripts/fetch_clue_api_subset.py`**, or run **`download_all_required.py`** with a key present.

## Windows notes

- Set **`PYTHONUTF8=1`** so Snakemake and Python agree on UTF-8 in logs and paths.
- If the workflow was interrupted: **`snakemake --unlock`**.
- Stale outputs: **`snakemake --rerun-incomplete`**.

## HPC / cluster execution

**Option A — SLURM (recommended when the plugin is available)**

Install the executor plugin next to the main stack. A **pinned** combo lives in **`requirements-hpc.txt`** (currently **`snakemake-executor-plugin-slurm==2.6.0`**, tested with Snakemake 8.x from **`requirements.txt`**):

```bash
pip install -r requirements.txt -r requirements-hpc.txt
```

To install the SLURM plugin alone without the pin:

```bash
pip install "snakemake-executor-plugin-slurm"
```

Then submit many jobs to SLURM (example):

```bash
snakemake --executor slurm --jobs 50 \
  --default-resources mem_mb=8192 runtime=1440 \
  --set-resources infer_strandedness:mem_mb=16384
```

Tune **`--jobs`**, partitions, and **`--default-resources`** to your site policy. Use **`--dry-run`** first.

**Option B — Generic batch wrapper (`cluster-generic`)**

Install **`snakemake-executor-plugin-cluster-generic`**, then use a profile similar to:

```yaml
executor: cluster-generic
cluster-generic-submit-cmd: >
  mkdir -p slurm_logs &&
  sbatch --parsable
  --cpus-per-task={threads}
  --mem={resources.mem_mb}
  -J smk-{rule}
  -o slurm_logs/{rule}-%j.out
  -e slurm_logs/{rule}-%j.err
  --wrap={exec_job:q}
default-resources:
  - mem_mb=8192
```

Save as e.g. **`profiles/my_site/config.yaml`** and run **`snakemake --workflow-profile profiles/my_site --jobs 30`**. Adjust **`--wrap`**, partitions, and account flags for your scheduler.

The checked-in **`profiles/example_slurm/config.yaml`** only sets **cores** / **default-resources** for local or login-node runs (no extra plugins required).

**Option C — Job array / single-node parallel**

On a single large node, keep **`snakemake -c $SLURM_CPUS_PER_TASK`** (or **`-j`** matching allocated cores) without a cluster executor.

## R on clusters

- Load an **R module** or use a **conda** environment with **`r-base`** before **`python scripts/install_r_supplementary_dependencies.py`** (or **`install_r_edger_dependencies.py`**, **`install_r_movics_dependencies.py`**).
- Non-interactive installs: Bioconductor respects **`CI=true`** or **`GLIOMA_TARGET_R_VERBOSE=1`** for verbose **`install_r_supplementary_enrichment.R`** logs.
- Optional mirror: **`GLIOMA_TARGET_R_BIOC_MIRROR`** (passed through to R **`options(BioC_mirror)`**).

## Related docs

- **`docs/GBM_DETECTION_AND_OPEN_DATA.md`** — data layout and supplementary downloads.
- **`README.md`** — **`Rscript`** resolution on Windows (**`configure_r_for_snakemake.py`**).
