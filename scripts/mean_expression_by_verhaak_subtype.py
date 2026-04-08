#!/usr/bin/env python3
"""
Per-subtype column means on the TOIL hub matrix (log2 TPM + pseudo) for primary tumors only.

Uses verhaak_subtype_call from subtype scores; excludes Unassigned and subtypes with
< min_samples_per_subtype. One row per gene_id; columns are subtype labels + optional n_samples row in JSON.

See config/module2_integration.yaml — subtype_mean_expression
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


def ensg_base(gene_id: str) -> str:
    s = str(gene_id).strip()
    if "." in s and s.startswith("ENSG"):
        return s.split(".", 1)[0]
    return s


def load_integration_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module2_integration.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def main() -> int:
    rr = repo_root()
    cfg = load_integration_cfg()
    block = cfg.get("subtype_mean_expression") or {}
    expr_path = rr / block.get("expression_parquet", "results/module3/toil_gbm_vs_brain_tpm.parquet")
    score_path = rr / block.get("subtype_scores_tsv", "results/module3/tcga_gbm_verhaak_subtype_scores.tsv")
    out_tsv = rr / block.get("output_tsv", "results/module3/mean_log_tpm_by_verhaak_subtype.tsv")
    out_js = rr / block.get("provenance_json", "results/module3/mean_log_tpm_by_verhaak_subtype_provenance.json")
    min_n = int(block.get("min_samples_per_subtype", 3))

    if not expr_path.is_file() or not score_path.is_file():
        print("Missing expression parquet or subtype scores.", file=sys.stderr)
        return 1

    st = pd.read_csv(score_path, sep="\t")
    st["sample_id"] = st["sample_id"].astype(str)
    if "verhaak_subtype_call" not in st.columns:
        print("subtype scores missing verhaak_subtype_call", file=sys.stderr)
        return 2

    df = pd.read_parquet(expr_path)
    df.index = df.index.map(lambda x: ensg_base(str(x)))
    df = df.groupby(df.index).median()

    col_blocks: dict[str, list[str]] = {}
    counts: dict[str, int] = {}
    for sub, grp in st.groupby("verhaak_subtype_call"):
        lab = str(sub)
        if lab in ("Unassigned", "nan") or pd.isna(sub):
            continue
        sids = [s for s in grp["sample_id"].tolist() if s in df.columns]
        if len(sids) < min_n:
            continue
        col_blocks[lab] = sids
        counts[lab] = len(sids)

    if not col_blocks:
        print("No subtypes met min_samples_per_subtype", file=sys.stderr)
        return 3

    sub_order = sorted(col_blocks.keys())
    parts = []
    for lab in sub_order:
        cols = col_blocks[lab]
        sub_df = df[cols].to_numpy(dtype=np.float64)
        parts.append(pd.Series(np.nanmean(sub_df, axis=1), name=lab, index=df.index.astype(str)))
    out = pd.concat(parts, axis=1)
    out.index.name = "gene_id"
    out = out.reset_index()
    out_tsv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_tsv, sep="\t", index=False)

    prov = {
        "scale": "TOIL hub log2(TPM+pseudo); column = mean across tumor samples in subtype",
        "subtypes_included": sub_order,
        "n_tumor_samples_per_subtype": counts,
        "min_samples_per_subtype": min_n,
        "n_genes": int(len(out)),
        "expression_parquet": str(expr_path),
        "subtype_scores_tsv": str(score_path),
    }
    out_js.write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(f"Wrote {out_tsv} and {out_js}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
