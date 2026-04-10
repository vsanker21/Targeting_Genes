#!/usr/bin/env python3
"""
Two-group Welch t-test + Benjamini–Hochberg FDR on log-transformed expression (holdout staging).

Outputs TSV columns: gene_id, log2FoldChange, pvalue, padj

--kind geo: GEO series_matrix (probes as gene_id). --kind cgga: CGGA gene_name counts (symbols as gene_id).

This is a frozen holdout statistic for permutation decoys; recount3 vs STAR arm-specific re-quantification
is not applied here — the same table is copied to each preregistered arm path by the suite driver.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from statsmodels.stats.multitest import multipletests

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from holdout_geo_expression import load_cgga_gene_counts, load_geo_series_matrix


def _welch_t_pvalues(log_m: np.ndarray, mask_a: np.ndarray, mask_b: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """log_m: (n_genes, n_samples). Returns log2fc (mean B - mean A), t, p (two-sided)."""
    a = log_m[:, mask_a]
    b = log_m[:, mask_b]
    na = int(mask_a.sum())
    nb = int(mask_b.sum())
    if na < 2 or nb < 2:
        raise ValueError("each group needs >= 2 samples")
    ma = np.nanmean(a, axis=1)
    mb = np.nanmean(b, axis=1)
    va = np.nanvar(a, axis=1, ddof=1)
    vb = np.nanvar(b, axis=1, ddof=1)
    log2fc = mb - ma
    se2 = va / na + vb / nb
    se = np.sqrt(np.maximum(se2, 1e-20))
    t = (mb - ma) / se
    df_num = se2**2
    df_den = (va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1)
    df = df_num / np.maximum(df_den, 1e-20)
    p = 2 * scipy_stats.t.sf(np.abs(t), df=np.clip(df, 1e-6, 1e9))
    p = np.clip(p, 0, 1)
    return log2fc, t, p


def run_de(
    *,
    kind: str,
    expression_path: Path,
    manifest: pd.DataFrame,
    group_column: str,
    log_pseudo: float,
    min_mean_log: float,
) -> pd.DataFrame:
    df = manifest.copy()
    if group_column not in df.columns:
        raise ValueError(f"missing column {group_column}")
    sid = df["sample_id"].astype(str)
    grp = df[group_column].astype(str)
    labels = sorted(grp.unique())
    if len(labels) != 2:
        raise ValueError(f"expected 2 groups in {group_column}, got {labels}")
    g0, g1 = labels[0], labels[1]
    mask_a = grp.eq(g0).to_numpy()
    mask_b = grp.eq(g1).to_numpy()

    samples = sid.tolist()
    if kind == "geo":
        feat, mat, _cols = load_geo_series_matrix(expression_path, samples)
    elif kind == "cgga":
        feat, mat, _cols = load_cgga_gene_counts(expression_path, samples)
    else:
        raise ValueError(kind)

    log_m = np.log2(np.maximum(mat, 0.0) + log_pseudo)
    keep = (np.nanmean(log_m[:, mask_a], axis=1) >= min_mean_log) | (
        np.nanmean(log_m[:, mask_b], axis=1) >= min_mean_log
    )
    log_m = log_m[keep]
    feat = feat[keep]

    log2fc, _t, p = _welch_t_pvalues(log_m, mask_a, mask_b)
    _ok, padj, _a, _b = multipletests(p, method="fdr_bh")
    out = pd.DataFrame(
        {
            "gene_id": feat.astype(str),
            "log2FoldChange": log2fc.astype(np.float64),
            "pvalue": p.astype(np.float64),
            "padj": padj.astype(np.float64),
        }
    )
    meta0, meta1 = int(mask_a.sum()), int(mask_b.sum())
    out.attrs["group_order"] = [g0, g1]
    out.attrs["n_g0"] = meta0
    out.attrs["n_g1"] = meta1
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kind", choices=("geo", "cgga"), required=True)
    ap.add_argument("--expression", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--group-column", type=str, default="group")
    ap.add_argument("--log-pseudo", type=float, default=-1, help="default: 0.01 geo, 1 cgga")
    ap.add_argument("--min-mean-log", type=float, default=0.0, help="min mean log2 expr in either group")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    log_pseudo = args.log_pseudo
    if log_pseudo < 0:
        log_pseudo = 1.0 if args.kind == "cgga" else 0.01

    sep = "," if args.manifest.suffix.lower() == ".csv" else "\t"
    man = pd.read_csv(args.manifest, sep=sep)
    try:
        res = run_de(
            kind=args.kind,
            expression_path=args.expression,
            manifest=man,
            group_column=args.group_column,
            log_pseudo=log_pseudo,
            min_mean_log=args.min_mean_log,
        )
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(args.output, sep="\t", index=False)
    g0, g1 = res.attrs.get("group_order", ("?", "?"))
    print(
        f"Wrote {args.output} (genes={len(res)}; {g0} n={res.attrs.get('n_g0')} vs {g1} n={res.attrs.get('n_g1')})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
