#!/usr/bin/env python3
"""
ARCHS4/recount HDF5: mean log1p expression per outline GBM driver symbol (GTEx + TCGA matrices).

Requires h5py. Gene symbols must match meta/genes in the HDF5 (Maayan matrices: typically samples × genes
in data/expression; genes × samples is detected when the first axis length matches len(meta/genes)).
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import yaml

_REPO = Path(__file__).resolve().parents[1]


def _data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((_REPO / "config/data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def _driver_symbols() -> list[str]:
    p = _REPO / "references" / "gbm_known_drivers_outline.yaml"
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    syms = doc.get("gene_symbols") or []
    return [str(s).strip() for s in syms if str(s).strip()]


def _summarize_matrix(h5_path: Path, symbols: list[str]) -> dict[str, Any]:
    try:
        import h5py
        import numpy as np
    except ImportError:
        return {"error": "h5py_or_numpy_missing", "path": str(h5_path)}

    if not h5_path.is_file():
        return {"error": "missing_file", "path": str(h5_path)}

    out: dict[str, Any] = {"path": str(h5_path), "genes": {}}
    try:
        with h5py.File(h5_path, "r") as h5:
            if "meta/genes" not in h5 or "data/expression" not in h5:
                out["error"] = "missing_meta_genes_or_data_expression"
                return out
            genes_raw = h5["meta/genes"][:]
            genes = [g.decode("utf-8", "replace") if isinstance(g, (bytes, bytearray)) else str(g) for g in genes_raw]
            g2i = {g: i for i, g in enumerate(genes)}
            expr = h5["data/expression"]
            if len(expr.shape) != 2:
                out["error"] = f"unexpected_expression_shape_{expr.shape}"
                return out
            n0, n1 = expr.shape
            # Maayan ARCHS4/recount matrices use samples × genes; some exports use genes × samples.
            if n1 == len(genes):
                gene_axis = "columns"
                n_samples, n_genes = n0, n1
                take_gene_vec = lambda i: expr[:, i]  # noqa: E731
            elif n0 == len(genes):
                gene_axis = "rows"
                n_genes, n_samples = n0, n1
                take_gene_vec = lambda i: expr[i, :]  # noqa: E731
            else:
                out["error"] = (
                    f"cannot_align_genes shape={expr.shape} meta_genes={len(genes)} "
                    "(expected genes along rows or columns)"
                )
                return out
            out["expression_layout"] = {
                "gene_axis": gene_axis,
                "n_samples": int(n_samples),
                "n_genes": int(n_genes),
            }
            for sym in symbols:
                idx = g2i.get(sym)
                if idx is None:
                    out["genes"][sym] = {"error": "symbol_not_in_matrix"}
                    continue
                col = expr[:, idx] if gene_axis == "columns" else expr[idx, :]
                arr = np.asarray(col, dtype=np.float64)
                arr = arr[np.isfinite(arr)]
                if arr.size == 0:
                    out["genes"][sym] = {"error": "empty_column"}
                    continue
                log1p = np.log1p(np.maximum(arr, 0.0))
                out["genes"][sym] = {
                    "n_samples": int(arr.size),
                    "mean_raw": float(np.mean(arr)),
                    "mean_log1p": float(np.mean(log1p)),
                    "sd_log1p": float(np.std(log1p, ddof=1)) if arr.size > 1 else 0.0,
                }
    except OSError as e:
        out["error"] = str(e)
    return out


def main() -> int:
    dr = _data_root()
    doc = yaml.safe_load((_REPO / "config/data_sources.yaml").read_text(encoding="utf-8"))
    ad = (doc.get("references") or {}).get("archs4_recount_dir")
    if not isinstance(ad, str):
        print("Missing references.archs4_recount_dir", file=sys.stderr)
        return 1
    base = Path(ad.replace("{data_root}", str(dr)).replace("/", os.sep))
    symbols = _driver_symbols()
    payload = {
        "data_root": str(dr.resolve()),
        "driver_symbols": symbols,
        "note": (
            "Mean log1p of ARCHS4/recount gene-level counts across all samples in data/expression "
            "(GTEx or TCGA cohort mix per file). Gene axis vs meta/genes is inferred (samples×genes or genes×samples)."
        ),
        "gtex_matrix": _summarize_matrix(base / "gtex_matrix.h5", symbols),
        "tcga_matrix": _summarize_matrix(base / "tcga_matrix.h5", symbols),
    }
    out = _REPO / "results/module4/archs4_outline_driver_expression_context.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
