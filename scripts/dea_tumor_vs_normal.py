#!/usr/bin/env python3
"""
Welch t-test on hub log₂(TPM+pseudo) for tumor vs pooled normal (TOIL single pipeline).

Welch uses unequal variances and Satterthwaite approximate degrees of freedom per gene
(scipy.stats.ttest_ind, equal_var=False). Multiple testing: Benjamini–Hochberg FDR.

See docs/DEA_METHODOLOGY.md
"""

from __future__ import annotations

import sys
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
from dea_common import (
    apply_outline_m21_columns,
    config_fingerprint,
    filter_mask_pooled_normal,
    hub_to_linear,
    write_dea_provenance,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "dea_tumor_normal.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def main() -> int:
    cfg = load_cfg()
    expr_path = repo_root() / cfg["output"]["expression_parquet"]
    sample_path = repo_root() / cfg["output"]["sample_table"]
    out_path = repo_root() / cfg["output"]["dea_table"]
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
    tumor_cols = meta.loc[meta["group"] == "tumor", "sample_id"].astype(str).tolist()
    normal_cols = meta.loc[meta["group"] == "normal", "sample_id"].astype(str).tolist()

    missing_t = [c for c in tumor_cols if c not in df.columns]
    missing_n = [c for c in normal_cols if c not in df.columns]
    if missing_t or missing_n:
        print(f"Manifest/column mismatch tumor {missing_t[:3]} normal {missing_n[:3]}", file=sys.stderr)
        return 2

    X = df[tumor_cols].to_numpy(dtype=np.float64)
    Y = df[normal_cols].to_numpy(dtype=np.float64)

    toil = cfg.get("toil") or {}
    scale = toil.get("expression_scale", "log2_tpm_plus_pseudo")
    pseudo = float(toil.get("log_pseudo", 0.001))

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

    t_stat, p_two = ttest_ind(lt_sub, ln_sub, axis=1, equal_var=False, nan_policy="omit")
    log2fc = lt_sub.mean(axis=1) - ln_sub.mean(axis=1)
    _, padj, _, _ = multipletests(np.nan_to_num(p_two, nan=1.0), method=fdr_method)

    out = pd.DataFrame(
        {
            "gene_id": genes.astype(str),
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
    out = apply_outline_m21_columns(out, cfg, effect_col="delta_log2_expression", padj_col="padj_bh")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.sort_values("padj_bh").to_csv(out_path, sep="\t", index=False)
    sig = (out["padj_bh"] < 0.05).sum()
    print(f"Wrote {out_path} rows={len(out)} FDR<0.05: {sig}")

    write_dea_provenance(
        prov_path,
        script="dea_tumor_vs_normal.py",
        method="welch_ttest_ind_hub_log2_tpm_plus_pseudo",
        extra={
            "config_sha256_prefix": config_fingerprint(cfg),
            "expression_parquet": str(expr_path),
            "sample_table": str(sample_path),
            "n_genes_input": int(df.shape[0]),
            "n_genes_tested": int(keep.sum()),
            "filter_min_tpm": min_tpm,
            "filter_min_fraction_expressing": min_frac,
            "welch_equal_var": False,
            "toil_expression_scale": scale,
            "toil_log_pseudo": pseudo,
            "outline_module2_dea_reporting": (cfg.get("outline_module2") or {}).get("dea_reporting"),
        },
    )
    print(f"Wrote {prov_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
