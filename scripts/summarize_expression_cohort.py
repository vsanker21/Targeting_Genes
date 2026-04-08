#!/usr/bin/env python3
"""
Cohort / design QC for TOIL GBM vs GTEx brain extract: sample counts, region breakdown,
duplicate IDs. Writes JSON for methods supplements and pipeline checks.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "dea_tumor_normal.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def main() -> int:
    cfg = load_cfg()
    sample_path = repo_root() / cfg["output"]["sample_table"]
    expr_path = repo_root() / cfg["output"]["expression_parquet"]
    out_path = repo_root() / "results" / "module3" / "cohort_design_summary.json"
    if not sample_path.is_file():
        print(f"Missing {sample_path}", file=sys.stderr)
        return 1

    meta = pd.read_csv(sample_path, sep="\t")
    meta["sample_id"] = meta["sample_id"].astype(str)
    dup = meta["sample_id"].duplicated().sum()
    if dup:
        print(f"WARNING: {dup} duplicate sample_id rows in manifest", file=sys.stderr)

    by_group = meta.groupby("group").size().to_dict()
    region_counts = Counter()
    for _, row in meta.iterrows():
        if row["group"] == "normal":
            region_counts[str(row.get("detailed_category", ""))] += 1
        else:
            region_counts[f"tumor::{row.get('detailed_category', '')}"] += 1

    summary: dict[str, Any] = {
        "n_manifest_rows": int(len(meta)),
        "n_tumor": int(by_group.get("tumor", 0)),
        "n_normal": int(by_group.get("normal", 0)),
        "duplicate_sample_id_rows": int(dup),
        "normal_detailed_category_counts": dict(sorted(region_counts.items())),
        "config_gtex_brain_detailed_categories": cfg.get("gtex_brain_detailed_categories"),
        "ols_reference_normal_subregion": (cfg.get("ols_region_covariate") or {}).get(
            "reference_normal_subregion"
        ),
    }
    trace_path = repo_root() / "config" / "methods_traceability.yaml"
    if trace_path.is_file():
        summary["methods_traceability"] = yaml.safe_load(trace_path.read_text(encoding="utf-8"))
    if expr_path.is_file():
        try:
            import pyarrow.parquet as pq

            names = list(pq.ParquetFile(expr_path).schema.names)
            want = set(meta["sample_id"].astype(str))
            present = want.intersection(names)
            summary["parquet_schema_column_names_n"] = len(names)
            summary["manifest_samples_found_in_parquet_columns"] = len(present)
            missing = sorted(want - set(names))
            if missing:
                summary["manifest_samples_missing_in_parquet_first10"] = missing[:10]
        except Exception as e:
            summary["parquet_schema_read_error"] = str(e)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
