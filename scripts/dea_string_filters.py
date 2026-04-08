"""
Shared DEA row filters for STRING / symbol export scripts (padj, outline M2.1, effect, numeric joins).
"""

from __future__ import annotations

import sys
from typing import Any

import numpy as np
import pandas as pd


def resolve_fdr_column(dea: pd.DataFrame) -> str | None:
    """Welch/OLS use padj_bh; PyDESeq2 padj; edgeR FDR."""
    for c in ("padj_bh", "padj", "FDR"):
        if c in dea.columns:
            return c
    return None


def normalize_bool_series(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower().isin(("true", "1", "yes"))


def filter_dea(dea: pd.DataFrame, job: dict[str, Any]) -> pd.DataFrame:
    padj_max = float(job.get("padj_max", 0.05))
    fdr_col = str(job.get("fdr_column", "") or "").strip()
    if not fdr_col:
        fdr_col = resolve_fdr_column(dea) or ""
    if not fdr_col or fdr_col not in dea.columns:
        return dea.iloc[0:0].copy()
    sub = dea.loc[pd.to_numeric(dea[fdr_col], errors="coerce") <= padj_max].copy()

    if job.get("require_outline_m21_high_confidence_screen", False):
        col = "outline_m21_high_confidence_screen"
        if col not in sub.columns:
            print(f"WARNING: job {job.get('job_name')} missing {col}; skipping that filter", file=sys.stderr)
        else:
            sub = sub.loc[normalize_bool_series(sub[col])]

    eff_col = job.get("effect_column")
    min_abs = job.get("min_abs_effect")
    if eff_col and min_abs is not None:
        if eff_col not in sub.columns:
            print(f"WARNING: job {job.get('job_name')} missing effect column {eff_col}", file=sys.stderr)
        else:
            eff = pd.to_numeric(sub[eff_col], errors="coerce")
            sub = sub.loc[np.abs(eff) >= float(min_abs)]

    jname = str(job.get("job_name", "unnamed"))
    for f in job.get("numeric_filters") or []:
        if not isinstance(f, dict):
            print(f"WARNING: job {jname} numeric_filters entry not a dict: {f}", file=sys.stderr)
            continue
        col = str(f.get("column", "")).strip()
        op = str(f.get("op", "")).strip().lower()
        val = f.get("value")
        if not col or op not in ("lte", "gte") or val is None:
            print(f"WARNING: job {jname} bad numeric_filters entry {f}", file=sys.stderr)
            continue
        if col not in sub.columns:
            print(f"WARNING: job {jname} missing column {col}; skipping that numeric filter", file=sys.stderr)
            continue
        x = pd.to_numeric(sub[col], errors="coerce")
        mask = x.notna()
        v = float(val)
        if op == "lte":
            mask &= x <= v
        else:
            mask &= x >= v
        sub = sub.loc[mask].copy()
    return sub
