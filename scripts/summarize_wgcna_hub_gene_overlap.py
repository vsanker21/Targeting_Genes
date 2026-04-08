#!/usr/bin/env python3
"""
Compare gene_id sets between integrated WGCNA TPM hub and recount3-only hub (TOIL matrix rows).

Writes JSON for quick QC and downstream reporting (driver+M2.1+recount3 vs recount3 DepMap consensus only).

Inputs: results/module4/wgcna_hub_expr_subset.parquet,
        results/module4/wgcna_hub_expr_subset_recount3_only.parquet
Output: results/module4/wgcna_hub_gene_overlap_summary.json (configurable via argv).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensg_base(gene_id: str) -> str:
    s = str(gene_id).strip()
    if "." in s and s.startswith("ENSG"):
        return s.split(".", 1)[0]
    return s


def gene_set_from_parquet(path: Path) -> set[str]:
    df = pd.read_parquet(path)
    if df.index.name != "gene_id" and "gene_id" in df.columns:
        return {ensg_base(x) for x in df["gene_id"].astype(str)}
    return {ensg_base(x) for x in df.index.astype(str)}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Summarize overlap between WGCNA hub parquets.")
    p.add_argument(
        "--integrated-parquet",
        default="results/module4/wgcna_hub_expr_subset.parquet",
        help="Path under repo root",
    )
    p.add_argument(
        "--recount3-only-parquet",
        default="results/module4/wgcna_hub_expr_subset_recount3_only.parquet",
    )
    p.add_argument(
        "--output-json",
        default="results/module4/wgcna_hub_gene_overlap_summary.json",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    rr = repo_root()
    p_int = rr / args.integrated_parquet.replace("/", os.sep)
    p_r3 = rr / args.recount3_only_parquet.replace("/", os.sep)
    out_p = rr / args.output_json.replace("/", os.sep)

    if not p_int.is_file():
        print(f"Missing {p_int}", file=sys.stderr)
        return 1
    if not p_r3.is_file():
        print(f"Missing {p_r3}", file=sys.stderr)
        return 2

    gi = gene_set_from_parquet(p_int)
    gr = gene_set_from_parquet(p_r3)
    inter = gi & gr
    only_i = gi - gr
    only_r = gr - gi

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "integrated_parquet": str(p_int.relative_to(rr)).replace("\\", "/"),
        "recount3_only_parquet": str(p_r3.relative_to(rr)).replace("\\", "/"),
        "n_genes_integrated_hub": len(gi),
        "n_genes_recount3_only_hub": len(gr),
        "n_intersection": len(inter),
        "n_integrated_not_in_recount3_hub": len(only_i),
        "n_recount3_hub_not_in_integrated": len(only_r),
        "fraction_recount3_genes_in_integrated": round(len(inter) / len(gr), 6) if gr else None,
        "note": "Integrated hub = Welch M21 ∪ OLS M21 ∪ recount3 DepMap consensus; recount3-only = consensus alone.",
    }
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
