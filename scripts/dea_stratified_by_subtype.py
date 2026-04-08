#!/usr/bin/env python3
"""
Outline Module 2 §2.3: Welch DEA (tumor vs pooled GTEx normals) stratified by Verhaak subtype call.

Each subtype with ≥ min_tumor_samples primary tumors is tested against the same normal pool
as the global DEA (TOIL hub scale). See config/stratified_dea.yaml
"""

from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy.stats import ttest_ind
from statsmodels.stats.multitest import multipletests

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from dea_common import apply_outline_m21_columns, config_fingerprint, filter_mask_pooled_normal, hub_to_linear

STATISTICAL_CAVEATS = [
    "Subtype labels partition one primary tumor cohort; stratified results are not statistically independent across subtypes.",
    "Each subtype arm uses the same pooled GTEx normal samples as the global Welch DEA (overlapping normal data across subtype contrasts).",
    "Small subtype sample sizes can produce near-constant expression arms; Welch p-values may be numerically unreliable (RuntimeWarnings suppressed in this script).",
    "Outline Module 2 section 2.3 references MOVICS consensus; this pipeline uses MSigDB Verhaak gene-set ranks (or user centroids), not multi-algorithm consensus posteriors.",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_dea_cfg() -> dict[str, Any]:
    return yaml.safe_load((repo_root() / "config" / "dea_tumor_normal.yaml").read_text(encoding="utf-8"))


def load_stratified_cfg() -> dict[str, Any]:
    return yaml.safe_load((repo_root() / "config" / "stratified_dea.yaml").read_text(encoding="utf-8"))


def slug_subtype(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(name).strip())


def run_one_subtype(
    df: pd.DataFrame,
    tumor_cols: list[str],
    normal_cols: list[str],
    cfg: dict[str, Any],
    subtype_label: str,
) -> pd.DataFrame | None:
    if len(tumor_cols) < 2:
        return None
    X = df[tumor_cols].to_numpy(dtype=np.float64)
    Y = df[normal_cols].to_numpy(dtype=np.float64)
    toil = cfg.get("toil") or {}
    scale = toil.get("expression_scale", "log2_tpm_plus_pseudo")
    pseudo = float(toil.get("log_pseudo", 0.001))
    filt = cfg.get("filters", {})
    min_tpm = float(filt.get("min_tpm", 1.0))
    min_frac = float(filt.get("min_fraction_expressing", 0.1))
    mt = cfg.get("multiple_testing", {}) or {}
    fdr_method = str(mt.get("method", "fdr_bh"))

    if scale == "linear_tpm":
        x_lin = np.maximum(X, 0.0)
        y_lin = np.maximum(Y, 0.0)
        lt = np.log2(x_lin + 1.0)
        ln = np.log2(y_lin + 1.0)
    else:
        lt = X
        ln = Y
        x_lin = hub_to_linear(X, pseudo)
        y_lin = hub_to_linear(Y, pseudo)

    mean_t = x_lin.mean(axis=1)
    mean_n = y_lin.mean(axis=1)
    keep = filter_mask_pooled_normal(x_lin, y_lin, min_tpm, min_frac)
    lt_sub = lt[keep]
    ln_sub = ln[keep]
    genes = df.index[keep]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        t_stat, p_two = ttest_ind(lt_sub, ln_sub, axis=1, equal_var=False, nan_policy="omit")
    log2fc = lt_sub.mean(axis=1) - ln_sub.mean(axis=1)
    _, padj, _, _ = multipletests(np.nan_to_num(p_two, nan=1.0), method=fdr_method)

    out = pd.DataFrame(
        {
            "gene_id": genes.astype(str),
            "stratify_subtype": subtype_label,
            "n_tumor_samples": len(tumor_cols),
            "n_normal_samples": len(normal_cols),
            "mean_linear_tpm_tumor": mean_t[keep],
            "mean_linear_tpm_normal": mean_n[keep],
            "mean_log2_tpm_plus_pseudo_tumor": lt_sub.mean(axis=1),
            "mean_log2_tpm_plus_pseudo_normal": ln_sub.mean(axis=1),
            "delta_log2_expression": log2fc,
            "welch_t": t_stat,
            "pvalue": p_two,
            "padj_bh": padj,
            "multiple_testing_method": fdr_method,
        }
    )
    return apply_outline_m21_columns(out, cfg, effect_col="delta_log2_expression", padj_col="padj_bh")


def main() -> int:
    st_cfg = load_stratified_cfg()
    cfg = load_dea_cfg()
    rr = repo_root()

    expr_path = rr / st_cfg.get("expression_parquet", cfg["output"]["expression_parquet"])
    sample_path = rr / st_cfg.get("sample_table", cfg["output"]["sample_table"])
    subtype_path = rr / st_cfg["subtype_scores_tsv"]
    out_dir = rr / st_cfg.get("output_dir", "results/module3/stratified_dea")
    summary_path = rr / st_cfg.get("summary_tsv", "results/module3/stratified_dea/summary.tsv")
    min_n = int(st_cfg.get("min_tumor_samples", 8))

    if not expr_path.is_file() or not sample_path.is_file() or not subtype_path.is_file():
        print("Missing expression, sample table, or subtype scores.", file=sys.stderr)
        return 1

    meta = pd.read_csv(sample_path, sep="\t")
    meta["sample_id"] = meta["sample_id"].astype(str)
    normal_cols = meta.loc[meta["group"] == "normal", "sample_id"].tolist()

    st = pd.read_csv(subtype_path, sep="\t")
    st["sample_id"] = st["sample_id"].astype(str)
    if "verhaak_subtype_call" not in st.columns:
        print("subtype_scores_tsv missing verhaak_subtype_call", file=sys.stderr)
        return 2

    df = pd.read_parquet(expr_path)
    missing_n = [c for c in normal_cols if c not in df.columns]
    if missing_n:
        print(f"Normal columns missing in matrix: {missing_n[:3]}", file=sys.stderr)
        return 3

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_rows: list[dict[str, Any]] = []

    for subtype, grp in st.groupby("verhaak_subtype_call"):
        if str(subtype) in ("Unassigned", "nan") or pd.isna(subtype):
            continue
        tumor_cols = grp["sample_id"].tolist()
        tumor_cols = [c for c in tumor_cols if c in df.columns]
        if len(tumor_cols) < min_n:
            summary_rows.append(
                {
                    "subtype": subtype,
                    "n_tumor_samples": len(tumor_cols),
                    "skipped": True,
                    "reason": f"n<{min_n}",
                    "output_tsv": "",
                    "n_genes_tested": 0,
                    "n_sig_fdr_0.05": 0,
                }
            )
            continue
        out_df = run_one_subtype(df, tumor_cols, normal_cols, cfg, str(subtype))
        if out_df is None:
            continue
        slug = slug_subtype(subtype)
        out_file = out_dir / f"dea_welch_subtype_{slug}.tsv"
        out_df.sort_values("padj_bh").to_csv(out_file, sep="\t", index=False)
        n_sig = int((out_df["padj_bh"] < 0.05).sum())
        summary_rows.append(
            {
                "subtype": subtype,
                "n_tumor_samples": len(tumor_cols),
                "skipped": False,
                "reason": "",
                "output_tsv": str(out_file.relative_to(rr)).replace("\\", "/"),
                "n_genes_tested": len(out_df),
                "n_sig_fdr_0.05": n_sig,
            }
        )
        print(f"Wrote {out_file} subtype={subtype} n_tumor={len(tumor_cols)} FDR<0.05: {n_sig}")

    pd.DataFrame(summary_rows).to_csv(summary_path, sep="\t", index=False)
    prov = {
        "stratified_dea": st_cfg,
        "config_sha256_prefix": config_fingerprint(cfg),
        "expression_parquet": str(expr_path),
        "subtype_scores": str(subtype_path),
        "statistical_caveats": STATISTICAL_CAVEATS,
        "outline_reference": "Project_Outline_extracted.txt Module 2",
    }
    (out_dir / "stratified_dea_provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(f"Wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
