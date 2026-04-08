#!/usr/bin/env python3
"""
Write minimal omics/multi_omics_mae/*.tsv.gz under a synthetic data_root for CI or local smoke tests.

Layout matches fetch_movics_staging_data / m2_movics_intnmf_depmap_mae.R expectations:
  rows = genes, columns = ModelID (ACH-*), gzip TSV.

Usage:
  python scripts/write_min_movics_mae_fixtures.py /path/to/synthetic_data_root
Then:
  GLIOMA_TARGET_DATA_ROOT=/path/to/synthetic_data_root snakemake -c1 m2_movics_intnmf_depmap_mae
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("data_root", type=Path, help="Directory to create (omics/multi_omics_mae under it)")
    args = ap.parse_args()
    dr = args.data_root.resolve()
    mae = dr / "omics" / "multi_omics_mae"
    mae.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(42)
    n_genes = 60
    n_samp = 8
    genes = [f"GENE{i:04d}" for i in range(n_genes)]
    samples = [f"ACH-{i:06d}" for i in range(n_samp)]

    expr = pd.DataFrame(
        rng.lognormal(mean=1.0, sigma=0.4, size=(n_genes, n_samp)),
        index=genes,
        columns=samples,
    )
    cn = pd.DataFrame(
        rng.normal(loc=0.0, scale=0.3, size=(n_genes, n_samp)),
        index=genes,
        columns=samples,
    )
    mut = pd.DataFrame(0, index=genes, columns=samples, dtype=int)
    for i, g in enumerate(genes):
        flip = rng.random(n_samp) < (0.2 + 0.6 * (i / max(n_genes - 1, 1)))
        mut.loc[g] = flip.astype(int)
    mut.loc[genes[0]] = 0
    mut.loc[genes[1]] = 1
    mut.loc[genes[2], samples[0]] = 1
    mut.loc[genes[2], samples[1]] = 0

    expr.to_csv(mae / "depmap_gbm_expression_logtpm.tsv.gz", sep="\t", compression="gzip")
    cn.to_csv(mae / "depmap_gbm_cnv_log2.tsv.gz", sep="\t", compression="gzip")
    mut.to_csv(mae / "depmap_gbm_mutation_binary.tsv.gz", sep="\t", compression="gzip")
    pd.DataFrame({"ModelID": samples, "cohort": "synthetic_fixture"}).to_csv(
        mae / "depmap_gbm_sample_manifest.tsv", sep="\t", index=False
    )

    # Prefix 000_ so this sorts before real DepMap folders; latest_depmap_dir() still picks e.g. depmap_public_* when present.
    rel = dr / "depmap" / "000_synthetic_mae_fixture"
    rel.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "ModelID": samples,
            "CellLineName": [f"SynthLine_{i}" for i in range(n_samp)],
            "OncotreePrimaryDisease": ["Glioma"] * n_samp,
            "OncotreeSubtype": ["Glioblastoma" if i % 2 == 0 else "Astrocytoma" for i in range(n_samp)],
            "OncotreeLineage": ["CNS/Brain"] * n_samp,
            "ModelType": ["Cell Line"] * n_samp,
        }
    ).to_csv(rel / "Model.csv", index=False)

    gene_cols = ["TP53 (7157)", "EGFR (1956)", "PTEN (5728)", "ATRX (84148)", "TERT (7015)"]
    crispr = pd.DataFrame(
        rng.normal(0.0, 0.15, size=(n_samp, len(gene_cols))),
        index=samples,
        columns=gene_cols,
    )
    crispr.index.name = "ModelID"
    crispr.to_csv(rel / "CRISPRGeneEffect.csv")

    print(f"Wrote minimal MAE under {mae}; Model.csv + CRISPRGeneEffect stub under {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
