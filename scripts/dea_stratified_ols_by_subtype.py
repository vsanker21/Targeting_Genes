#!/usr/bin/env python3
"""
Outline Module 2 §2.3: OLS tumor coefficient (subtype tumors vs reference GTEx region + region dummies)
stratified by verhaak_subtype_call. Same pooled normals and design as global OLS, but is_tumor=1 only
for tumors in the current subtype.

See config/stratified_dea.yaml and config/dea_tumor_normal.yaml (ols_region_covariate).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy import stats
from statsmodels.stats.multitest import multipletests

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from dea_common import (
    apply_outline_m21_columns,
    config_fingerprint,
    filter_mask_pooled_normal,
    filter_mask_tumor_or_reference_normal,
    hub_to_linear,
    invert_xt_x,
)
from dea_ols_gtex_region_covariate import build_design

STATISTICAL_CAVEATS = [
    "Subtype labels partition one primary tumor cohort; stratified OLS tables are not statistically independent across subtypes.",
    "Each subtype arm reuses the same pooled GTEx normals and the same reference-normal estimand as global OLS (Path B); is_tumor=1 only for tumors in that subtype.",
    "Homoskedastic OLS per gene without limma eBayes variance moderation (see docs/DEA_METHODOLOGY.md).",
    "Outline Module 2 section 2.3 references MOVICS; labels here are MSigDB Verhaak ranks or user centroids.",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_dea_cfg() -> dict[str, Any]:
    return yaml.safe_load((repo_root() / "config" / "dea_tumor_normal.yaml").read_text(encoding="utf-8"))


def load_stratified_cfg() -> dict[str, Any]:
    return yaml.safe_load((repo_root() / "config" / "stratified_dea.yaml").read_text(encoding="utf-8"))


def slug_subtype(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(name).strip())


def run_one_subtype_ols(
    df_sub: pd.DataFrame,
    sample_ids: list[str],
    meta: pd.DataFrame,
    tumor_cols: list[str],
    normal_cols: list[str],
    ref_normal_cols: list[str],
    cfg: dict[str, Any],
    ols_cfg: dict[str, Any],
    subtype_label: str,
) -> pd.DataFrame | None:
    ref_region = str(ols_cfg.get("reference_normal_subregion", "Brain - Cortex"))
    filter_mode = str(ols_cfg.get("filter_mode", "contrast_aligned")).lower()
    filt = cfg.get("filters", {})
    min_tpm = float(filt.get("min_tpm", 1.0))
    min_frac = float(filt.get("min_fraction_expressing", 0.1))
    mt = cfg.get("multiple_testing", {}) or {}
    fdr_method = str(mt.get("method", "fdr_bh"))
    toil = cfg.get("toil") or {}
    scale = toil.get("expression_scale", "log2_tpm_plus_pseudo")
    pseudo = float(toil.get("log_pseudo", 0.001))

    if scale == "linear_tpm":
        raise NotImplementedError("stratified OLS requires log2_tpm_plus_pseudo TOIL scale")

    if len(tumor_cols) < 2:
        return None

    try:
        X, design_names, p = build_design(sample_ids, meta, ref_region)
    except ValueError as e:
        print(f"Design error subtype={subtype_label}: {e}", file=sys.stderr)
        return None

    n = X.shape[0]
    if np.linalg.matrix_rank(X) < p:
        print(
            f"Rank-deficient design subtype={subtype_label} rank={np.linalg.matrix_rank(X)} < p={p}",
            file=sys.stderr,
        )
        return None

    XtX = X.T @ X
    XtX_inv, cond_xtx = invert_xt_x(XtX)
    coef_tumor_idx = 1

    lt_full = df_sub.to_numpy(dtype=np.float64)
    X_tum = df_sub[tumor_cols].to_numpy(dtype=np.float64)
    X_norm = df_sub[normal_cols].to_numpy(dtype=np.float64)
    x_lin_t = hub_to_linear(X_tum, pseudo)
    x_lin_n = hub_to_linear(X_norm, pseudo)
    mean_t = x_lin_t.mean(axis=1)
    mean_n = x_lin_n.mean(axis=1)

    if filter_mode == "pooled_normal":
        keep = filter_mask_pooled_normal(x_lin_t, x_lin_n, min_tpm, min_frac)
    elif filter_mode == "contrast_aligned":
        if not ref_normal_cols:
            return None
        miss_r = [c for c in ref_normal_cols if c not in df_sub.columns]
        if miss_r:
            return None
        x_lin_ref = df_sub[ref_normal_cols].to_numpy(dtype=np.float64)
        x_lin_ref = hub_to_linear(x_lin_ref, pseudo)
        keep = filter_mask_tumor_or_reference_normal(x_lin_t, x_lin_ref, min_tpm, min_frac)
    else:
        print(f"Unknown filter_mode: {filter_mode}", file=sys.stderr)
        return None

    Y = lt_full[keep, :].T
    genes = df_sub.index[keep]
    df_resid = n - p

    Beta, _, rank_ls, _ = np.linalg.lstsq(X, Y, rcond=None)
    if rank_ls < p:
        print(f"lstsq rank {rank_ls} < p={p} subtype={subtype_label}", file=sys.stderr)
        return None

    fitted = X @ Beta
    resid = Y - fitted
    rss = np.sum(resid * resid, axis=0)
    sigma2 = rss / max(df_resid, 1)
    v_tumor = float(XtX_inv[coef_tumor_idx, coef_tumor_idx])
    se = np.sqrt(np.maximum(sigma2 * v_tumor, 0.0))
    beta_t = Beta[coef_tumor_idx, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        t_stat = np.where(se > 0, beta_t / se, np.nan)
    p_two = 2.0 * stats.t.sf(np.abs(t_stat), df=df_resid)
    _, padj, _, _ = multipletests(np.nan_to_num(p_two, nan=1.0), method=fdr_method)

    tum_idx = [sample_ids.index(s) for s in tumor_cols]
    n_idx = [sample_ids.index(s) for s in normal_cols]
    mean_log_t = lt_full[keep, :][:, tum_idx].mean(axis=1)
    mean_log_n = lt_full[keep, :][:, n_idx].mean(axis=1)

    out = pd.DataFrame(
        {
            "gene_id": genes.astype(str),
            "stratify_subtype": subtype_label,
            "reference_normal_subregion": ref_region,
            "filter_mode": filter_mode,
            "n_tumor_samples": len(tumor_cols),
            "n_normal_samples": len(normal_cols),
            "mean_linear_tpm_tumor": mean_t[keep],
            "mean_linear_tpm_normal": mean_n[keep],
            "mean_log2_tpm_plus_pseudo_tumor": mean_log_t,
            "mean_log2_tpm_plus_pseudo_normal": mean_log_n,
            "beta_tumor_vs_ref_normal": beta_t,
            "se_tumor": se,
            "t_stat": t_stat,
            "df_residual": df_resid,
            "pvalue": p_two,
            "padj_bh": padj,
            "multiple_testing_method": fdr_method,
            "design_n_samples": n,
            "design_p_params": p,
            "design_columns": ",".join(design_names),
            "condition_number_XtX": cond_xtx,
        }
    )
    return apply_outline_m21_columns(out, cfg, effect_col="beta_tumor_vs_ref_normal", padj_col="padj_bh")


def main() -> int:
    st_cfg = load_stratified_cfg()
    cfg = load_dea_cfg()
    ols_cfg = cfg.get("ols_region_covariate") or {}
    rr = repo_root()

    expr_path = rr / st_cfg.get("expression_parquet", cfg["output"]["expression_parquet"])
    sample_path = rr / st_cfg.get("sample_table", cfg["output"]["sample_table"])
    subtype_path = rr / st_cfg["subtype_scores_tsv"]
    out_dir = rr / st_cfg.get("ols_stratified_output_dir", "results/module3/stratified_ols_dea")
    summary_path = rr / st_cfg.get(
        "ols_stratified_summary_tsv",
        "results/module3/stratified_ols_dea/summary.tsv",
    )
    min_n = int(st_cfg.get("min_tumor_samples", 8))
    ref_region = str(ols_cfg.get("reference_normal_subregion", "Brain - Cortex"))

    if not expr_path.is_file() or not sample_path.is_file() or not subtype_path.is_file():
        print("Missing expression, sample table, or subtype scores.", file=sys.stderr)
        return 1

    meta = pd.read_csv(sample_path, sep="\t")
    meta["sample_id"] = meta["sample_id"].astype(str)
    normal_cols = meta.loc[meta["group"] == "normal", "sample_id"].tolist()
    ref_normal_cols = meta.loc[
        (meta["group"] == "normal") & (meta["detailed_category"].astype(str) == ref_region),
        "sample_id",
    ].astype(str).tolist()

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

        sample_ids = [str(c) for c in normal_cols + tumor_cols]
        df_sub = df[sample_ids]

        out_df = run_one_subtype_ols(
            df_sub,
            sample_ids,
            meta,
            tumor_cols,
            normal_cols,
            ref_normal_cols,
            cfg,
            ols_cfg,
            str(subtype),
        )
        if out_df is None:
            summary_rows.append(
                {
                    "subtype": subtype,
                    "n_tumor_samples": len(tumor_cols),
                    "skipped": True,
                    "reason": "design_or_lstsq_failed",
                    "output_tsv": "",
                    "n_genes_tested": 0,
                    "n_sig_fdr_0.05": 0,
                }
            )
            continue

        slug = slug_subtype(subtype)
        out_file = out_dir / f"dea_ols_subtype_{slug}.tsv"
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
        "stratified_ols_dea": {
            "ols_stratified_output_dir": str(out_dir.relative_to(rr)).replace("\\", "/"),
            "ols_stratified_summary_tsv": str(summary_path.relative_to(rr)).replace("\\", "/"),
            **{k: st_cfg[k] for k in st_cfg if k in ("min_tumor_samples", "subtype_scores_tsv", "expression_parquet", "sample_table")},
        },
        "dea_config_sha256_prefix": config_fingerprint(cfg),
        "reference_normal_subregion": ref_region,
        "ols_filter_mode": str(ols_cfg.get("filter_mode", "contrast_aligned")),
        "statistical_caveats": STATISTICAL_CAVEATS,
        "outline_reference": "Project_Outline_extracted.txt Module 2",
    }
    (out_dir / "stratified_ols_dea_provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(f"Wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
