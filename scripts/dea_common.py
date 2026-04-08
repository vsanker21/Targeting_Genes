"""
Shared utilities for TOIL-based DEA: hub scale, linear TPM, expression filters, provenance.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


def hub_to_linear(hub: np.ndarray, pseudo: float) -> np.ndarray:
    """Invert UCSC TOIL log2(TPM + pseudo) to non-negative linear TPM."""
    h = np.asarray(hub, dtype=np.float64)
    return np.maximum(np.power(2.0, h) - pseudo, 0.0)


def filter_mask_pooled_normal(
    x_lin_tumor: np.ndarray,
    x_lin_normal: np.ndarray,
    min_tpm: float,
    min_frac: float,
) -> np.ndarray:
    """
    Per gene (row): keep if tumor passes (mean + fraction) OR pooled normal passes.
    Independent filtering on abundance; test statistics computed only on kept genes.
    """
    mean_t = x_lin_tumor.mean(axis=1)
    mean_n = x_lin_normal.mean(axis=1)
    frac_t = (x_lin_tumor >= min_tpm).mean(axis=1)
    frac_n = (x_lin_normal >= min_tpm).mean(axis=1)
    return ((mean_t >= min_tpm) & (frac_t >= min_frac)) | ((mean_n >= min_tpm) & (frac_n >= min_frac))


def filter_mask_tumor_or_reference_normal(
    x_lin_tumor: np.ndarray,
    x_lin_ref_normal: np.ndarray,
    min_tpm: float,
    min_frac: float,
) -> np.ndarray:
    """
    Contrast-aligned filter for tumor vs reference normal: keep if tumor passes OR
    reference-normal subgroup passes (avoids keeping genes driven only by non-reference GTEx sites).
    """
    if x_lin_ref_normal.size == 0:
        raise ValueError("reference normal expression matrix has no columns")
    mean_t = x_lin_tumor.mean(axis=1)
    mean_r = x_lin_ref_normal.mean(axis=1)
    frac_t = (x_lin_tumor >= min_tpm).mean(axis=1)
    frac_r = (x_lin_ref_normal >= min_tpm).mean(axis=1)
    return ((mean_t >= min_tpm) & (frac_t >= min_frac)) | ((mean_r >= min_tpm) & (frac_r >= min_frac))


def invert_xt_x(XtX: np.ndarray) -> tuple[np.ndarray, float]:
    """(X'X)^{-1} via solve(I); returns (inverse, condition number estimate)."""
    p = XtX.shape[0]
    cond = float(np.linalg.cond(XtX))
    inv_xtx = np.linalg.solve(XtX, np.eye(p, dtype=np.float64))
    return inv_xtx, cond


def write_dea_provenance(
    path: Path,
    *,
    script: str,
    method: str,
    extra: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "script": script,
        "method": method,
        "utc_timestamp": datetime.now(timezone.utc).isoformat(),
        **extra,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def config_fingerprint(cfg: dict[str, Any]) -> str:
    """Stable short hash of YAML-relevant DEA settings for reproducibility."""
    blob = yaml.safe_dump(cfg, sort_keys=True, default_flow_style=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def apply_outline_m21_columns(
    out: pd.DataFrame,
    cfg: dict[str, Any],
    *,
    effect_col: str,
    padj_col: str = "padj_bh",
) -> pd.DataFrame:
    """
    Project outline §2.1 reporting gates: FDR < alpha and |log2FC| > threshold.
    On TOIL hub data, effect_col is a log2(TPM+pseudo) contrast surrogate, not DESeq2 LFC.
    """
    block = (cfg.get("outline_module2") or {}).get("dea_reporting") or {}
    if not block.get("enabled", True):
        return out
    alpha = float(block.get("fdr_alpha", 0.05))
    thr = float(block.get("min_abs_log2_fold_change", 1.5))
    pc = np.asarray(out[padj_col], dtype=np.float64)
    eff = np.asarray(out[effect_col], dtype=np.float64)
    padj_ok = np.nan_to_num(pc, nan=1.0) < alpha
    fc_ok = np.abs(np.nan_to_num(eff, nan=0.0)) >= thr
    o2 = out.copy()
    o2["outline_m21_padj_below_alpha"] = padj_ok
    o2["outline_m21_abs_log2fc_ge_threshold"] = fc_ok
    o2["outline_m21_high_confidence_screen"] = padj_ok & fc_ok
    return o2
