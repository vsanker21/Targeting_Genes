#!/usr/bin/env python3
"""
Build a sample × metadata table for external WGCNA traits (outline Module 4.1).

Left-joins Verhaak subtype scores onto the TOIL sample manifest, then restricts rows
to sample IDs present in the hub expression matrix and/or the WGCNA subset parquet
so traits align with exported expression slices.

Config: config/module2_integration.yaml — wgcna_sample_traits (default) or wgcna_sample_traits_recount3_only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq
import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_integration_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module2_integration.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def parquet_hub_sample_columns(path: Path) -> set[str]:
    """Column names in TOIL hub parquet excluding gene index column."""
    names = pq.read_schema(path).names
    return {n for n in names if n != "gene_id"}


def subset_parquet_sample_columns(path: Path) -> list[str]:
    df = pd.read_parquet(path)
    return [str(c) for c in df.columns]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build sample × metadata traits for WGCNA.")
    p.add_argument(
        "--config-block",
        default="wgcna_sample_traits",
        help="YAML block in config/module2_integration.yaml (default: wgcna_sample_traits)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    rr = repo_root()
    block = (load_integration_cfg().get(args.config_block) or {})
    if not block.get("enabled", True):
        print(f"{args.config_block} disabled")
        return 0

    sample_path = rr / str(block.get("sample_table", "results/module3/toil_gbm_vs_brain_samples.tsv"))
    score_path = rr / str(
        block.get("subtype_scores_tsv", "results/module3/tcga_gbm_verhaak_subtype_scores.tsv")
    )
    expr_path = rr / str(block.get("expression_parquet", "results/module3/toil_gbm_vs_brain_tpm.parquet"))
    align_rel = block.get("align_with_wgcna_subset_parquet")
    align_path = (rr / str(align_rel)) if align_rel else None
    restrict_matrix = bool(block.get("restrict_to_matrix_columns", True))
    sample_filter = str(block.get("sample_filter", "all")).strip().lower()
    out_tsv = rr / str(block.get("output_tsv", "results/module4/wgcna_hub_sample_traits.tsv"))
    out_js = rr / str(block.get("provenance_json", "results/module4/wgcna_hub_sample_traits_provenance.json"))

    if not sample_path.is_file():
        print(f"Missing {sample_path}", file=sys.stderr)
        return 1
    if not score_path.is_file():
        print(f"Missing {score_path}", file=sys.stderr)
        return 2

    samples = pd.read_csv(sample_path, sep="\t", dtype=str, low_memory=False)
    if "sample_id" not in samples.columns:
        print("sample_table must contain sample_id", file=sys.stderr)
        return 3

    samples["sample_id"] = samples["sample_id"].astype(str)

    if sample_filter == "tumor_only":
        samples = samples.loc[samples["group"].str.lower() == "tumor"].copy()
    elif sample_filter != "all":
        print(f"Unknown sample_filter: {sample_filter}", file=sys.stderr)
        return 4

    align_mode = "none"
    want_ids: set[str] | None = None
    if align_path is not None and align_path.is_file():
        want_ids = set(subset_parquet_sample_columns(align_path))
        align_mode = "wgcna_subset_parquet"
    elif restrict_matrix:
        if not expr_path.is_file():
            print(f"Missing expression parquet {expr_path}", file=sys.stderr)
            return 5
        want_ids = parquet_hub_sample_columns(expr_path)
        align_mode = "full_hub_columns"

    if want_ids is not None:
        sid = samples["sample_id"].astype(str)
        samples = samples.loc[sid.isin(want_ids)].copy()

    scores = pd.read_csv(score_path, sep="\t", low_memory=False)
    if "sample_id" not in scores.columns:
        print("subtype scores TSV must contain sample_id", file=sys.stderr)
        return 6

    scores["sample_id"] = scores["sample_id"].astype(str)
    score_cols = [c for c in scores.columns if c != "sample_id"]
    merged = samples.merge(scores[["sample_id"] + score_cols], on="sample_id", how="left")

    one_hot = bool(block.get("verhaak_one_hot_columns", False))
    oh_labels: list[str] = list(
        block.get("verhaak_one_hot_labels") or ["Classical", "Mesenchymal", "Neural", "Proneural"]
    )
    if one_hot and "verhaak_subtype_call" in merged.columns:
        vc = merged["verhaak_subtype_call"].astype(str).str.strip()
        for lab in oh_labels:
            safe = lab.replace(" ", "_")
            merged[f"verhaak_is_{safe}"] = (vc == lab).astype(int)

    first = ["sample_id", "group", "study", "detailed_category", "sample_type"]
    head = [c for c in first if c in merged.columns]
    rest = [c for c in merged.columns if c not in head]
    merged = merged[head + rest]

    out_tsv.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_tsv, sep="\t", index=False)

    n_subtype = int(merged["verhaak_subtype_call"].notna().sum()) if "verhaak_subtype_call" in merged.columns else 0
    prov = {
        "status": "ok",
        "config_block": args.config_block,
        "n_rows": int(len(merged)),
        "n_with_verhaak_subtype_call": n_subtype,
        "verhaak_one_hot_columns": one_hot,
        "verhaak_one_hot_labels": oh_labels if one_hot else None,
        "sample_filter": sample_filter,
        "align_mode": align_mode,
        "align_with_wgcna_subset_parquet": str(align_rel) if align_rel else None,
        "restrict_to_matrix_columns": restrict_matrix and align_mode != "wgcna_subset_parquet",
        "output_columns": list(merged.columns),
    }
    out_js.write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(f"Wrote {out_tsv} rows={len(merged)}")
    print(f"Wrote {out_js}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
