#!/usr/bin/env python3
"""
Subset the TOIL hub TPM matrix (genes × samples) for WGCNA / co-expression prep (outline Module 4.1).

Resolves HGNC symbols from one or more line-delimited lists (dea_string_export outputs, optional
recount3 PyDESeq2∩edgeR DepMap consensus from intersect_symbol_lists.py), maps symbols to Ensembl
via HGNC, intersects the expression matrix index, optionally restricts to tumor samples.
Writes Parquet plus optional long TSV (gene_id, sample_id, toil_rsem_tpm) for tidyverse/R workflows.

Config: config/module2_integration.yaml — wgcna_hub_subset (default) or wgcna_hub_subset_recount3_only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

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


def ensg_base(gene_id: str) -> str:
    s = str(gene_id).strip()
    if "." in s and s.startswith("ENSG"):
        return s.split(".", 1)[0]
    return s


def load_integration_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module2_integration.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def load_symbol_to_ensg(hgnc_path: Path) -> dict[str, str]:
    df = pd.read_csv(hgnc_path, sep="\t", dtype=str, low_memory=False)
    out: dict[str, str] = {}
    for _, row in df.iterrows():
        sym = str(row.get("symbol", "") or "").strip().upper()
        eid = str(row.get("ensembl_gene_id", "") or "").strip()
        if sym and eid.startswith("ENSG") and sym not in out:
            out[sym] = ensg_base(eid)
    return out


def load_symbols_from_txts(paths: list[Path]) -> tuple[set[str], list[str]]:
    """Return (uppercase symbols, ordered list of missing paths)."""
    syms: set[str] = set()
    missing: list[str] = []
    for p in paths:
        if not p.is_file():
            missing.append(str(p))
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip().upper()
            if s and not s.startswith("#"):
                syms.add(s)
    return syms, missing


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Subset TOIL TPM matrix for WGCNA (config-driven gene lists).")
    p.add_argument(
        "--config-block",
        default="wgcna_hub_subset",
        help="YAML block name in config/module2_integration.yaml (default: wgcna_hub_subset)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    rr = repo_root()
    block = (load_integration_cfg().get(args.config_block) or {})
    if not block.get("enabled", True):
        print(f"{args.config_block} disabled")
        return 0

    expr_path = rr / str(block.get("expression_parquet", "results/module3/toil_gbm_vs_brain_tpm.parquet"))
    sample_path = rr / str(block.get("sample_table", "results/module3/toil_gbm_vs_brain_samples.tsv"))
    hg_rel = str(block.get("hgnc_tsv", "{data_root}/references/hgnc_complete_set.txt")).replace(
        "{data_root}", str(data_root())
    ).replace("/", os.sep)
    hgnc_path = Path(hg_rel)
    list_rels = list(block.get("symbol_list_paths") or [])
    out_pq = rr / str(block.get("output_parquet", "results/module4/wgcna_hub_expr_subset.parquet"))
    out_long_rel = block.get("output_long_tsv")
    out_long = rr / str(out_long_rel) if out_long_rel else None
    out_js = rr / str(block.get("provenance_json", "results/module4/wgcna_hub_expr_subset_provenance.json"))
    sample_filter = str(block.get("sample_filter", "tumor_only")).strip().lower()

    if not list_rels:
        print(f"{args.config_block}.symbol_list_paths is empty", file=sys.stderr)
        return 1
    if not expr_path.is_file():
        print(f"Missing expression matrix {expr_path}", file=sys.stderr)
        return 2
    if not sample_path.is_file():
        print(f"Missing sample table {sample_path}", file=sys.stderr)
        return 3
    if not hgnc_path.is_file():
        print(f"Missing HGNC {hgnc_path}", file=sys.stderr)
        return 4

    list_paths = [rr / rel.replace("/", os.sep) for rel in list_rels]
    raw_symbols, missing_lists = load_symbols_from_txts(list_paths)
    if missing_lists:
        for m in missing_lists:
            print(f"WARNING: missing gene list {m}", file=sys.stderr)
    if not raw_symbols:
        print("No symbols loaded from gene lists", file=sys.stderr)
        return 5

    sym_to_e = load_symbol_to_ensg(hgnc_path)
    wanted_base: set[str] = set()
    unknown_symbol: list[str] = []
    for sym in sorted(raw_symbols):
        e = sym_to_e.get(sym)
        if e:
            wanted_base.add(e)
        else:
            unknown_symbol.append(sym)

    expr = pd.read_parquet(expr_path)
    idx_base = expr.index.map(ensg_base)
    mask = idx_base.isin(wanted_base)
    sub = expr.loc[mask].copy()
    n_matched = int(len(sub))
    if n_matched == 0:
        print("No genes from lists overlap the expression matrix index", file=sys.stderr)
        return 6

    meta = pd.read_csv(sample_path, sep="\t", dtype=str, low_memory=False)
    if "sample_id" not in meta.columns or "group" not in meta.columns:
        print("sample_table must have sample_id and group", file=sys.stderr)
        return 7
    if sample_filter == "tumor_only":
        keep_ids = set(meta.loc[meta["group"].str.lower() == "tumor", "sample_id"].astype(str))
    elif sample_filter == "all":
        keep_ids = set(meta["sample_id"].astype(str))
    else:
        print(f"Unknown sample_filter: {sample_filter}", file=sys.stderr)
        return 8

    avail_cols = [c for c in expr.columns if str(c) in keep_ids]
    if not avail_cols:
        print("No sample columns left after filter", file=sys.stderr)
        return 9
    sub = sub[avail_cols]

    out_pq.parent.mkdir(parents=True, exist_ok=True)
    sub.to_parquet(out_pq, index=True)

    n_long = 0
    if out_long is not None:
        long_df = sub.reset_index().melt(
            id_vars=["gene_id"],
            var_name="sample_id",
            value_name="toil_rsem_tpm",
        )
        n_long = int(len(long_df))
        out_long.parent.mkdir(parents=True, exist_ok=True)
        long_df.to_csv(out_long, sep="\t", index=False, float_format="%.7g")
        print(f"Wrote {out_long} rows={n_long}")

    prov = {
        "status": "ok",
        "config_block": args.config_block,
        "expression_parquet": str(expr_path.relative_to(rr)).replace("\\", "/"),
        "sample_table": str(sample_path.relative_to(rr)).replace("\\", "/"),
        "sample_filter": sample_filter,
        "n_samples_in_subset": len(sub.columns),
        "n_genes_in_subset": len(sub),
        "output_long_tsv": str(out_long.relative_to(rr)).replace("\\", "/") if out_long else None,
        "n_long_tsv_rows": n_long if out_long else None,
        "long_tsv_value_column": "toil_rsem_tpm",
        "symbol_list_paths": [str(Path(p).as_posix()) for p in list_rels],
        "n_symbols_in_lists": len(raw_symbols),
        "n_symbols_resolved_to_ensembl": len(wanted_base),
        "n_symbols_not_in_hgnc": len(unknown_symbol),
        "n_genes_matched_in_matrix": n_matched,
        "unknown_symbols_sample": unknown_symbol[:50],
        "missing_list_files": missing_lists,
    }
    out_js.write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(f"Wrote {out_pq} shape={sub.shape}")
    print(f"Wrote {out_js}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
