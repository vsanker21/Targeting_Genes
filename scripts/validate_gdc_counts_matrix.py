#!/usr/bin/env python3
"""
Sanity checks for GDC STAR unstranded counts matrix (integer, non-negative, Ensembl gene IDs).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_sources_counts_path() -> Path:
    cfg = yaml.safe_load(
        (repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8")
    )
    rel = (cfg.get("gdc") or {}).get(
        "repo_unstranded_counts_matrix",
        "results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet",
    )
    return repo_root() / rel.replace("/", os.sep)


def main() -> int:
    path = data_sources_counts_path()
    if not path.is_file():
        print(f"Missing counts matrix: {path}", file=sys.stderr)
        return 1

    df = pd.read_parquet(path)
    genes = df.index.astype(str)
    ens_frac = float(genes.str.startswith("ENSG").mean())
    arr = df.to_numpy()
    if not np.issubdtype(arr.dtype, np.integer):
        arr_int = np.asarray(arr, dtype=np.int64)
        if not np.allclose(arr, arr_int):
            print(f"WARNING: non-integer values present; dtype={df.dtypes.iloc[0]}", file=sys.stderr)
    neg = int((arr < 0).sum())
    na = int(np.isnan(arr.astype(float)).sum()) if arr.dtype.kind == "f" else 0

    col_sums = arr.sum(axis=0)
    report = {
        "path": str(path.resolve()),
        "n_genes": int(df.shape[0]),
        "n_samples": int(df.shape[1]),
        "dtype": str(df.dtypes.iloc[0]) if df.shape[1] else "",
        "fraction_gene_ids_ensg_prefix": round(ens_frac, 6),
        "n_negative_entries": neg,
        "n_nan_entries": na,
        "per_sample_total_counts_median": float(np.median(col_sums)),
        "per_sample_total_counts_min": float(col_sums.min()),
        "per_sample_total_counts_max": float(col_sums.max()),
    }
    ok = ens_frac > 0.99 and neg == 0 and na == 0
    report["qc_pass"] = ok
    out = repo_root() / "results" / "module2" / "gdc_counts_matrix_qc.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not ok:
        return 2
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
