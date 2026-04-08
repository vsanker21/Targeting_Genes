#!/usr/bin/env python3
"""
Cohort-level summary of GDC STAR unstranded counts matrix vs TCGA-GBM sample metadata.

Supports future count-based DE (DESeq2/edgeR) outlined in Module 2.1: documents sample overlap,
library scale, and sparsity. Does not run DE.

Outputs: results/module2/gdc_counts_cohort_summary.json
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def main() -> int:
    rr = repo_root()
    ds = yaml.safe_load((rr / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    rel = (ds.get("gdc") or {}).get(
        "repo_unstranded_counts_matrix",
        "results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet",
    )
    counts_path = rr / rel.replace("/", os.sep)
    meta_path = rr / "results" / "module2" / "tcga_gbm_sample_meta.tsv"

    if not counts_path.is_file():
        print(f"Missing counts matrix {counts_path}", file=sys.stderr)
        return 1
    if not meta_path.is_file():
        print(f"Missing {meta_path}", file=sys.stderr)
        return 2

    meta = pd.read_csv(meta_path, sep="\t", dtype=str)
    meta_ids = set(meta["column_name"].astype(str))

    df = pd.read_parquet(counts_path)
    mat_cols = [str(c) for c in df.columns]
    overlap = sorted(meta_ids.intersection(mat_cols))
    only_meta = sorted(meta_ids - set(mat_cols))
    only_mat = sorted(set(mat_cols) - meta_ids)

    arr = df.to_numpy()
    zero_frac = float((arr == 0).mean()) if arr.size else 0.0
    col_sums = arr.sum(axis=0).astype(np.float64)

    report: dict[str, Any] = {
        "counts_matrix_path": str(counts_path.resolve()),
        "sample_meta_path": str(meta_path.resolve()),
        "n_genes_matrix": int(df.shape[0]),
        "n_samples_matrix_columns": int(df.shape[1]),
        "n_rows_sample_meta": int(len(meta)),
        "n_samples_in_both_meta_and_matrix": len(overlap),
        "n_sample_ids_only_in_meta_first20": only_meta[:20],
        "n_sample_ids_only_in_matrix_first20": only_mat[:20],
        "matrix_sparsity_zero_fraction": round(zero_frac, 6),
        "per_sample_total_counts_median": float(np.median(col_sums)) if col_sums.size else None,
        "per_sample_total_counts_mean": float(np.mean(col_sums)) if col_sums.size else None,
        "count_based_de_prerequisite_note": "DESeq2/edgeR tumor vs GTEx require integer counts on a shared pipeline for both arms; this matrix is TCGA-GBM GDC STAR only until harmonized normal counts are added.",
    }
    out = rr / "results" / "module2" / "gdc_counts_cohort_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
