#!/usr/bin/env python3
"""
Cross-assay concordance: TOIL bulk DEA (Welch + OLS with region covariate) vs recount3 count-based DE.

Merges on Ensembl gene_id (base). Reports Spearman/Pearson between:
  • Welch delta_log2_expression vs PyDESeq2 log2FoldChange / edgeR logFC
  • OLS beta_tumor_vs_ref_normal vs the same recount3 LFCs
  • Welch delta_log2_expression vs OLS beta_tumor_vs_ref_normal (same TOIL TPM cohort)
  • −log10(raw p-value) agreement between each TOIL model and recount3 (same merged genes as LFC)

Interpretation: tumor vs brain-normal contrast across TPM (Welch or OLS) and G029 counts;
high rho indicates directional agreement, not numerical identity. Welch–OLS agreement
summarizes robustness of the TPM-based contrast to modeling choice. P-value correlations
complement LFC correlations (rank similarity of evidence strength).

Output: results/module3/toil_welch_vs_recount3_bulk_effect_correlation.json
(legacy filename; contains both Welch and OLS blocks.)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from scipy.stats import pearsonr, spearmanr
except ImportError:
    pearsonr = None  # type: ignore[misc, assignment]
    spearmanr = None  # type: ignore[misc, assignment]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensg_base(g: str) -> str:
    s = str(g).strip()
    if s.startswith("ENSG") and "." in s:
        return s.split(".", 1)[0]
    return s


def neglog10_pvalues(series: pd.Series) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce")
    x = x.where(x > 0, np.nan).clip(lower=1e-300)
    return -np.log10(x)


def corr_block(
    x: pd.Series,
    y: pd.Series,
    *,
    min_pairs: int = 50,
    sign_agreement: bool = True,
) -> dict[str, Any] | None:
    a = pd.to_numeric(x, errors="coerce").to_numpy(dtype=float)
    b = pd.to_numeric(y, errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(a) & np.isfinite(b)
    n = int(mask.sum())
    if n < min_pairs or spearmanr is None or pearsonr is None:
        return None
    rho, _ = spearmanr(a[mask], b[mask])
    r, _ = pearsonr(a[mask], b[mask])
    out: dict[str, Any] = {
        "n_pairs": n,
        "spearman_rho": float(rho),
        "pearson_r": float(r),
    }
    if sign_agreement:
        same = np.sign(a[mask]) == np.sign(b[mask])
        out["fraction_sign_agreement"] = float(np.mean(same))
    return out


def _one_bulk(
    bulk: pd.DataFrame,
    effect_col: str,
    py: pd.DataFrame,
    ed: pd.DataFrame,
) -> dict[str, Any]:
    bulk = bulk.copy()
    bulk["_k"] = bulk["gene_id"].map(ensg_base)
    m_py = bulk.merge(py, on="_k", suffixes=("_bulk", "_r3py"), how="inner")
    m_ed = bulk.merge(ed, on="_k", suffixes=("_bulk", "_r3ed"), how="inner")
    eff_py = m_py[effect_col]
    eff_ed = m_ed[effect_col]
    return {
        "n_genes_bulk": int(bulk["_k"].nunique()),
        "n_overlap_pydeseq2": int(len(m_py)),
        "n_overlap_edger": int(len(m_ed)),
        "vs_pydeseq2": corr_block(eff_py, m_py["log2FoldChange"]),
        "vs_edger": corr_block(eff_ed, m_ed["logFC"]),
    }


def main() -> int:
    if spearmanr is None:
        print("Install scipy for correlations: pip install scipy", file=sys.stderr)
        return 1

    rr = repo_root()
    welch_p = rr / "results/module3/dea_gbm_vs_gtex_brain.tsv"
    ols_p = rr / "results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv"
    py_p = rr / "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_results.tsv"
    ed_p = rr / "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_qlf_results.tsv"
    out_p = rr / "results/module3/toil_welch_vs_recount3_bulk_effect_correlation.json"

    for p in (welch_p, ols_p, py_p, ed_p):
        if not p.is_file():
            print(f"Missing {p}", file=sys.stderr)
            return 2

    w = pd.read_csv(welch_p, sep="\t", low_memory=False)
    o = pd.read_csv(ols_p, sep="\t", low_memory=False)
    py = pd.read_csv(py_p, sep="\t", low_memory=False)
    ed = pd.read_csv(ed_p, sep="\t", low_memory=False)

    py = py.copy()
    ed = ed.copy()
    py["_k"] = py["gene_id"].map(ensg_base)
    ed["_k"] = ed["gene_id"].map(ensg_base)

    welch_stats = _one_bulk(w, "delta_log2_expression", py, ed)
    ols_stats = _one_bulk(o, "beta_tumor_vs_ref_normal", py, ed)

    wc = w[["gene_id", "delta_log2_expression"]].copy()
    wc["_k"] = wc["gene_id"].map(ensg_base)
    oc = o[["gene_id", "beta_tumor_vs_ref_normal"]].copy()
    oc["_k"] = oc["gene_id"].map(ensg_base)
    m_wo = wc.merge(oc, on="_k", how="inner", suffixes=("_welch", "_ols"))
    welch_vs_ols_tpm = corr_block(
        m_wo["delta_log2_expression"],
        m_wo["beta_tumor_vs_ref_normal"],
    )

    w2 = w.copy()
    w2["_k"] = w2["gene_id"].map(ensg_base)
    o2 = o.copy()
    o2["_k"] = o2["gene_id"].map(ensg_base)
    m_w_py = w2.merge(py, on="_k", how="inner", suffixes=("_welch", "_r3py"))
    m_w_ed = w2.merge(ed, on="_k", how="inner", suffixes=("_welch", "_r3ed"))
    m_o_py = o2.merge(py, on="_k", how="inner", suffixes=("_ols", "_r3py"))
    m_o_ed = o2.merge(ed, on="_k", how="inner", suffixes=("_ols", "_r3ed"))

    welch_vs_py_neglog10p = corr_block(
        neglog10_pvalues(m_w_py["pvalue_welch"]),
        neglog10_pvalues(m_w_py["pvalue_r3py"]),
        sign_agreement=False,
    )
    welch_vs_ed_neglog10p = corr_block(
        neglog10_pvalues(m_w_ed["pvalue"]),
        neglog10_pvalues(m_w_ed["PValue"]),
        sign_agreement=False,
    )
    ols_vs_py_neglog10p = corr_block(
        neglog10_pvalues(m_o_py["pvalue_ols"]),
        neglog10_pvalues(m_o_py["pvalue_r3py"]),
        sign_agreement=False,
    )
    ols_vs_ed_neglog10p = corr_block(
        neglog10_pvalues(m_o_ed["pvalue"]),
        neglog10_pvalues(m_o_ed["PValue"]),
        sign_agreement=False,
    )

    prov: dict[str, Any] = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "note": "Welch: TOIL RSEM TPM mean log2 tumor vs normal (Welch). OLS: TPM with GTEx region dummies (beta_tumor_vs_ref_normal). Recount3: PyDESeq2/edgeR on G029 counts vs GTEx brain. welch_vs_ols_tpm_effects: same cohort, two TPM DE models.",
        "welch_tsv": str(welch_p.relative_to(rr)).replace("\\", "/"),
        "ols_tsv": str(ols_p.relative_to(rr)).replace("\\", "/"),
        "recount3_pydeseq2_tsv": str(py_p.relative_to(rr)).replace("\\", "/"),
        "recount3_edger_tsv": str(ed_p.relative_to(rr)).replace("\\", "/"),
        "n_genes_welch": welch_stats["n_genes_bulk"],
        "n_genes_ols": ols_stats["n_genes_bulk"],
        "n_genes_recount3_pydeseq2": int(py["_k"].nunique()),
        "n_genes_recount3_edger": int(ed["_k"].nunique()),
        "n_overlap_welch_pydeseq2": welch_stats["n_overlap_pydeseq2"],
        "n_overlap_welch_edger": welch_stats["n_overlap_edger"],
        "welch_vs_pydeseq2": welch_stats["vs_pydeseq2"],
        "welch_vs_edger": welch_stats["vs_edger"],
        "n_overlap_ols_pydeseq2": ols_stats["n_overlap_pydeseq2"],
        "n_overlap_ols_edger": ols_stats["n_overlap_edger"],
        "ols_vs_pydeseq2": ols_stats["vs_pydeseq2"],
        "ols_vs_edger": ols_stats["vs_edger"],
        "n_overlap_welch_ols_tpm": int(len(m_wo)),
        "welch_vs_ols_tpm_effects": welch_vs_ols_tpm,
        "welch_vs_pydeseq2_neglog10_pvalue": welch_vs_py_neglog10p,
        "welch_vs_edger_neglog10_pvalue": welch_vs_ed_neglog10p,
        "ols_vs_pydeseq2_neglog10_pvalue": ols_vs_py_neglog10p,
        "ols_vs_edger_neglog10_pvalue": ols_vs_ed_neglog10p,
    }

    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(f"Wrote {out_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
