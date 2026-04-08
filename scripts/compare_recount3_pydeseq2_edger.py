#!/usr/bin/env python3
"""
Concordance between PyDESeq2 and edgeR results on the same recount3 count matrix.

Merges on Ensembl gene_id (base); reports Spearman correlation and overlap of FDR-significant sets.
Output: results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_vs_edger_concordance.json
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

try:
    from scipy.stats import spearmanr
except ImportError:
    spearmanr = None  # type: ignore[misc, assignment]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensg_base(g: str) -> str:
    s = str(g).strip()
    if s.startswith("ENSG") and "." in s:
        return s.split(".", 1)[0]
    return s


def main() -> int:
    if spearmanr is None:
        print("Install scipy for Spearman correlation: pip install scipy", file=sys.stderr)
        return 1

    rr = repo_root()
    cfg = yaml.safe_load((rr / "config" / "deseq2_recount3_tcga_gtex.yaml").read_text(encoding="utf-8"))
    block = cfg.get("deseq2_recount3_tcga_gbm_vs_gtex_brain") or {}
    out_dir = rr / str(block.get("output_dir", "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain"))

    p_path = out_dir / str(block.get("output_results", "deseq2_results.tsv"))
    e_path = out_dir / str(block.get("edger", {}).get("output_results", "edger_qlf_results.tsv"))
    if not p_path.is_file():
        print(f"Missing PyDESeq2 results: {p_path}", file=sys.stderr)
        return 2
    if not e_path.is_file():
        print(f"Missing edgeR results: {e_path}", file=sys.stderr)
        return 3

    pydf = pd.read_csv(p_path, sep="\t")
    edf = pd.read_csv(e_path, sep="\t")
    pydf["_k"] = pydf["gene_id"].map(ensg_base)
    edf["_k"] = edf["gene_id"].map(ensg_base)
    m = pydf.merge(edf, on="_k", suffixes=("_py", "_ed"), how="inner")
    if len(m) < 100:
        print(f"Too few merged genes: {len(m)}", file=sys.stderr)
        return 4

    lfc_py = pd.to_numeric(m["log2FoldChange"], errors="coerce")
    lfc_ed = pd.to_numeric(m["logFC"], errors="coerce")
    padj_py = pd.to_numeric(m["padj"], errors="coerce")
    fdr_ed = pd.to_numeric(m["FDR"], errors="coerce")

    mask = lfc_py.notna() & lfc_ed.notna()
    rho_lfc, _ = spearmanr(lfc_py[mask], lfc_ed[mask])

    mask_p = padj_py.notna() & fdr_ed.notna()
    rho_p, _ = spearmanr(
        -np.log10(padj_py.clip(lower=1e-300)[mask_p].to_numpy()),
        -np.log10(fdr_ed.clip(lower=1e-300)[mask_p].to_numpy()),
    )

    fdr_cut = 0.05
    sig_py = set(m.loc[padj_py < fdr_cut, "_k"])
    sig_ed = set(m.loc[fdr_ed < fdr_cut, "_k"])
    inter = len(sig_py & sig_ed)
    prov: dict[str, Any] = {
        "n_genes_merged": int(len(m)),
        "spearman_log2fc_vs_logfc": float(rho_lfc),
        "spearman_neg_log10_fdr": float(rho_p),
        "fdr_cutoff": fdr_cut,
        "n_sig_pydeseq2": len(sig_py),
        "n_sig_edger": len(sig_ed),
        "n_sig_both": inter,
        "pydeseq2_tsv": str(p_path.relative_to(rr)).replace("\\", "/"),
        "edger_tsv": str(e_path.relative_to(rr)).replace("\\", "/"),
    }
    out_json = out_dir / "deseq2_vs_edger_concordance.json"
    out_json.write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(f"Wrote {out_json}")
    print(json.dumps(prov, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
