#!/usr/bin/env python3
"""
OLS / limma-style linear model on the TOIL log matrix: y ~ tumor + GTEx subregion dummies.

Tumor coefficient: tumor vs reference GTEx detailed_category, adjusting for other normal
subregions. Coefficients via stable least squares (numpy.linalg.lstsq). Per-gene residual
variance; t-tests on the tumor coefficient (homoskedastic OLS; limma without eBayes).

See docs/DEA_METHODOLOGY.md
"""

from __future__ import annotations

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
    write_dea_provenance,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "dea_tumor_normal.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def build_design(
    sample_ids: list[str],
    meta: pd.DataFrame,
    ref_region: str,
) -> tuple[np.ndarray, list[str], int]:
    """
    Columns: intercept, is_tumor, then one dummy per non-reference normal detailed_category
    (1 if that normal sample's category matches, else 0; tumor rows are 0 on dummies).
    """
    m = meta.set_index("sample_id", drop=False)
    missing = [s for s in sample_ids if s not in m.index]
    if missing:
        raise ValueError(f"Samples missing from manifest (first 5): {missing[:5]}")

    normals = meta.loc[meta["group"] == "normal"]
    cats_present = sorted(normals["detailed_category"].dropna().astype(str).unique())
    if ref_region not in cats_present:
        raise ValueError(
            f"reference_normal_subregion {ref_region!r} not among normals: {cats_present}"
        )
    dummy_cats = [c for c in cats_present if c != ref_region]
    col_names = ["intercept", "is_tumor"] + [f"normal_region::{c}" for c in dummy_cats]

    n = len(sample_ids)
    p = 2 + len(dummy_cats)
    X = np.zeros((n, p), dtype=np.float64)
    X[:, 0] = 1.0
    for i, sid in enumerate(sample_ids):
        row = m.loc[sid]
        if row["group"] == "tumor":
            X[i, 1] = 1.0
        elif row["group"] == "normal":
            cat = str(row["detailed_category"])
            if cat in dummy_cats:
                j = dummy_cats.index(cat)
                X[i, 2 + j] = 1.0
        else:
            raise ValueError(f"Unknown group for {sid}: {row['group']}")

    return X, col_names, p


def main() -> int:
    cfg = load_cfg()
    ols_cfg = cfg.get("ols_region_covariate") or {}
    ref_region = str(ols_cfg.get("reference_normal_subregion", "Brain - Cortex"))
    filter_mode = str(ols_cfg.get("filter_mode", "contrast_aligned")).lower()
    out_rel = ols_cfg.get(
        "output_dea",
        "results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv",
    )
    expr_path = repo_root() / cfg["output"]["expression_parquet"]
    sample_path = repo_root() / cfg["output"]["sample_table"]
    out_path = repo_root() / out_rel
    prov_path = out_path.with_suffix("").with_name(out_path.stem + "_provenance.json")
    if not expr_path.is_file() or not sample_path.is_file():
        print("Run extract_toil_gbm_brain_tpm.py first.", file=sys.stderr)
        return 1

    filt = cfg.get("filters", {})
    min_tpm = float(filt.get("min_tpm", 1.0))
    min_frac = float(filt.get("min_fraction_expressing", 0.1))
    mt = cfg.get("multiple_testing", {}) or {}
    fdr_method = str(mt.get("method", "fdr_bh"))

    df = pd.read_parquet(expr_path)
    meta = pd.read_csv(sample_path, sep="\t")
    sample_ids = [str(c) for c in df.columns]
    meta["sample_id"] = meta["sample_id"].astype(str)

    tumor_cols = meta.loc[meta["group"] == "tumor", "sample_id"].astype(str).tolist()
    normal_cols = meta.loc[meta["group"] == "normal", "sample_id"].astype(str).tolist()
    ref_normal_cols = meta.loc[
        (meta["group"] == "normal") & (meta["detailed_category"].astype(str) == ref_region),
        "sample_id",
    ].astype(str).tolist()

    missing_t = [c for c in tumor_cols if c not in df.columns]
    missing_n = [c for c in normal_cols if c not in df.columns]
    if missing_t or missing_n:
        print(f"Manifest/column mismatch tumor {missing_t[:3]} normal {missing_n[:3]}", file=sys.stderr)
        return 2

    X, design_names, p = build_design(sample_ids, meta, ref_region)
    n = X.shape[0]
    if np.linalg.matrix_rank(X) < p:
        print(
            f"Design matrix rank-deficient: rank={np.linalg.matrix_rank(X)} < p={p}. Columns: {design_names}",
            file=sys.stderr,
        )
        return 3

    XtX = X.T @ X
    XtX_inv, cond_xtx = invert_xt_x(XtX)
    coef_tumor_idx = 1

    toil = cfg.get("toil") or {}
    scale = toil.get("expression_scale", "log2_tpm_plus_pseudo")
    pseudo = float(toil.get("log_pseudo", 0.001))

    X_tum = df[tumor_cols].to_numpy(dtype=np.float64)
    X_norm = df[normal_cols].to_numpy(dtype=np.float64)
    if scale == "linear_tpm":
        raise NotImplementedError("ols_region_covariate requires log2_tpm_plus_pseudo TOIL scale")
    lt_full = df.to_numpy(dtype=np.float64)
    x_lin_t = hub_to_linear(X_tum, pseudo)
    x_lin_n = hub_to_linear(X_norm, pseudo)
    mean_t = x_lin_t.mean(axis=1)
    mean_n = x_lin_n.mean(axis=1)

    if filter_mode == "pooled_normal":
        keep = filter_mask_pooled_normal(x_lin_t, x_lin_n, min_tpm, min_frac)
    elif filter_mode == "contrast_aligned":
        if not ref_normal_cols:
            print("contrast_aligned filter requires ≥1 reference-normal sample.", file=sys.stderr)
            return 4
        miss_r = [c for c in ref_normal_cols if c not in df.columns]
        if miss_r:
            print(f"Reference normal columns missing in matrix: {miss_r[:3]}", file=sys.stderr)
            return 5
        x_lin_ref = df[ref_normal_cols].to_numpy(dtype=np.float64)
        x_lin_ref = hub_to_linear(x_lin_ref, pseudo)
        keep = filter_mask_tumor_or_reference_normal(x_lin_t, x_lin_ref, min_tpm, min_frac)
    else:
        print(f"Unknown ols_region_covariate.filter_mode: {filter_mode}", file=sys.stderr)
        return 6

    Y = lt_full[keep, :].T
    genes = df.index[keep]
    df_resid = n - p

    Beta, _, rank_ls, _ = np.linalg.lstsq(X, Y, rcond=None)
    if rank_ls < p:
        print(f"lstsq rank {rank_ls} < p={p}", file=sys.stderr)
        return 7

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
            "reference_normal_subregion": ref_region,
            "filter_mode": filter_mode,
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
        }
    )
    out = apply_outline_m21_columns(out, cfg, effect_col="beta_tumor_vs_ref_normal", padj_col="padj_bh")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.sort_values("padj_bh").to_csv(out_path, sep="\t", index=False)
    sig = (out["padj_bh"] < 0.05).sum()
    print(f"Wrote {out_path} rows={len(out)} FDR<0.05: {sig}")

    write_dea_provenance(
        prov_path,
        script="dea_ols_gtex_region_covariate.py",
        method="ols_lstsq_homoskedastic_tumor_coef",
        extra={
            "config_sha256_prefix": config_fingerprint(cfg),
            "expression_parquet": str(expr_path),
            "sample_table": str(sample_path),
            "n_genes_input": int(df.shape[0]),
            "n_genes_tested": int(keep.sum()),
            "filter_min_tpm": min_tpm,
            "filter_min_fraction_expressing": min_frac,
            "filter_mode": filter_mode,
            "reference_normal_subregion": ref_region,
            "n_reference_normal_samples": len(ref_normal_cols),
            "design_column_names": design_names,
            "condition_number_XtX": cond_xtx,
            "lstsq_rank": int(rank_ls),
            "toil_expression_scale": scale,
            "toil_log_pseudo": pseudo,
            "outline_module2_dea_reporting": (cfg.get("outline_module2") or {}).get("dea_reporting"),
        },
    )
    print(f"Wrote {prov_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
