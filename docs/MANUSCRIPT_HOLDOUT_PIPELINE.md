# Holdout pipelines & permutations

## 1. Harmonize staging (done programmatically)
```bash
snakemake -c1 m7_harmonize_holdout_staging
```
Produces `validation/.../holdout_source_inventory.json` and unpacks CGGA zips.

## 2. Build sample manifests (programmatic)
```bash
python scripts/build_holdout_sample_manifests_from_staging.py
```
Writes under `$GLIOMA_TARGET_DATA_ROOT/validation/external_cohort_sample_meta/`:
- `cgga_gbm_holdout_samples.tsv` — primary GBM (WHO IV), MGMT methylated vs un-methylated
- `gse4290_holdout_samples.tsv` — GBM grade 4 vs epilepsy controls (series_matrix metadata)
- `gse7696_holdout_samples.tsv` — GBM vs non-tumoral (Sample_title)

Freeze row sets in the same commit as the preregistration tag.

## 3. Permutation label tables (programmatic)
```bash
python scripts/generate_holdout_permutation_labels.py \
  --input-tsv "$DATA_ROOT/validation/external_cohort_sample_meta/cgga_gbm_holdout_samples.tsv" \
  --prefix cgga --n-replicates 50 --base-seed 42
```
Repeat with `--prefix gse4290` / `gse7696` (must match `config/holdout_preregistered_outputs.yaml` globs).

Outputs: `validation/holdout_permutation/{prefix}_perm_r*.csv`

## 4. DEA per arm (orchestrated suite)
One-shot (after manifests + GEO/CGGA staging exist):
```bash
python scripts/run_holdout_preregistered_de_suite.py --build-manifests --perm-replicates 50
```
Options: `--skip-permutations`, `--skip-de`, `--only-cohort geo_gse4290` (repeatable).

For each cohort × arm (`recount3_only`, `gdc_star_only`, `integrated`):
- **Real labels:** `real_labels_de.tsv` per `config/holdout_preregistered_outputs.yaml`.
- **Permuted:** for each `perm_r{k}.csv`, DE with **`permuted_group`** → `perm_r{k}_de.tsv` in each arm folder.

The suite currently duplicates the **same** native-matrix Welch + BH-FDR table across arms until recount3/STAR/integrated re-quantification exists for each holdout (see `README_holdout_de_arms.txt` under each cohort).

Required columns for decoy plumbing: `gene_id`, `padj` (GEO uses Affymetrix probe IDs as `gene_id`; CGGA uses gene symbols — map to Ensembl if you need cross-cohort keys).

## 5. Aggregate external DE for validation report (optional)
Copy or symlink the primary holdout contrast DE to:
`validation/external_holdout/dea_tumor_vs_control.tsv`  
Then set `external_holdout_dea.strict_require_file: true` when ready for hard gates.

## 6. Decoy metrics JSON
```bash
snakemake -c1 m7_holdout_decoy_metrics
```
Point `m7_holdout_decoy_inputs.yaml` at the correct real vs permuted tables for each analysis story.
