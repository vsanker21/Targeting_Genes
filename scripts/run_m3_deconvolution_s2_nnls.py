#!/usr/bin/env python3
"""
M3 S2: spot-level deconvolution with non-negative least squares (NNLS).

Uses scipy.optimize.nnls per spot: min ||y - R @ w||_2 with w >= 0, then L1-normalize w
to obtain cell-type fraction estimates. Baseline only; not RCTD or Cell2location.

Requires real wide TSVs under data_root (see config/m3_deconvolution_s2_nnls.yaml).
Rule m3_deconvolution_s2_nnls is optional in rule all (GLIOMA_TARGET_INCLUDE_M3_DECONV_S2=1).

TSV formats:
  reference_profile_tsv: column 0 = gene_id, remaining columns = cell-type mean profiles (>= 0).
  spatial_counts_tsv: column 0 = spot_id, remaining columns = gene counts (same gene order as header).
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import scipy
import yaml
from scipy.optimize import nnls


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def deconvolve_nnls(r: np.ndarray, y: np.ndarray) -> np.ndarray:
    """R: (G,K), y: (G,S) -> fractions (S,K)."""
    _, k = r.shape
    _, s = y.shape
    out = np.zeros((s, k))
    for j in range(s):
        w, _ = nnls(r, y[:, j])
        tot = w.sum()
        if tot > 1e-12:
            out[j, :] = w / tot
        else:
            out[j, :] = 1.0 / k
    return out


def load_reference_wide(path: Path) -> tuple[np.ndarray, list[str], list[str]]:
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.reader(f, delimiter="\t")
        header = next(r)
        if len(header) < 2:
            raise SystemExit(f"Reference needs gene_id + type columns: {path}")
        genes: list[str] = []
        cols = header[1:]
        rows: list[list[float]] = []
        for row in r:
            if not row:
                continue
            genes.append(str(row[0]).strip())
            vals = [float(x) for x in row[1 : 1 + len(cols)]]
            rows.append(vals)
    mat = np.array(rows, dtype=float)
    mat = np.clip(mat, 0.0, None)
    return mat, genes, cols


def load_spatial_wide(path: Path) -> tuple[np.ndarray, list[str]]:
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.reader(f, delimiter="\t")
        header = next(r)
        if len(header) < 2:
            raise SystemExit(f"Spatial needs spot_id + gene columns: {path}")
        genes = header[1:]
        spots: list[str] = []
        rows: list[list[float]] = []
        for row in r:
            if not row:
                continue
            spots.append(str(row[0]).strip())
            rows.append([float(x) for x in row[1 : 1 + len(genes)]])
    mat = np.array(rows, dtype=float).T  # (G, S)
    mat = np.clip(mat, 0.0, None)
    return mat, spots


def main() -> int:
    rr = repo_root()
    cfg_path = rr / "config" / "m3_deconvolution_s2_nnls.yaml"
    if not cfg_path.is_file():
        print(f"Missing {cfg_path}", file=sys.stderr)
        return 1
    doc = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    block = doc.get("m3_deconvolution_s2_nnls") or {}
    if not block.get("enabled", True):
        print("m3_deconvolution_s2_nnls disabled")
        return 0

    ref_rel = block.get("reference_profile_tsv")
    spat_rel = block.get("spatial_counts_tsv")
    if not ref_rel or not spat_rel:
        print(
            "config/m3_deconvolution_s2_nnls.yaml: reference_profile_tsv and spatial_counts_tsv required "
            "(paths relative to data_root)",
            file=sys.stderr,
        )
        return 1

    dr = data_root()
    ref_p = dr / str(ref_rel).replace("/", os.sep)
    spat_p = dr / str(spat_rel).replace("/", os.sep)
    if not ref_p.is_file():
        print(f"Missing reference TSV under data_root: {ref_p}", file=sys.stderr)
        return 1
    if not spat_p.is_file():
        print(f"Missing spatial TSV under data_root: {spat_p}", file=sys.stderr)
        return 1

    r_mat, genes_r, type_names = load_reference_wide(ref_p)
    y_mat, spot_ids = load_spatial_wide(spat_p)
    with spat_p.open(encoding="utf-8", newline="") as f:
        g_order = next(csv.reader(f, delimiter="\t"))[1:]
    gi = {g: i for i, g in enumerate(genes_r)}
    idx = [gi[g] for g in g_order if g in gi]
    if len(idx) != len(g_order):
        missing = [g for g in g_order if g not in gi]
        print(f"Reference missing genes (first 8): {missing[:8]}", file=sys.stderr)
        return 1
    r_mat = r_mat[idx, :]
    y_mat = y_mat[idx, :]

    out_dir_rel = str(block.get("output_dir", "results/module3/m3_deconvolution_s2"))
    out_dir = rr / out_dir_rel.replace("/", os.sep)
    out_dir.mkdir(parents=True, exist_ok=True)

    fractions = deconvolve_nnls(r_mat, y_mat)
    frac_path = out_dir / "spot_celltype_fractions.tsv"
    with frac_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["spot_id", *type_names])
        for i, sid in enumerate(spot_ids):
            w.writerow([sid, *[f"{fractions[i, j]:.6f}" for j in range(fractions.shape[1])]])

    prov: dict[str, Any] = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "status": "ok",
        "artifact_kind": "m3_deconvolution_s2_nnls",
        "method": "scipy.optimize.nnls + L1_normalize",
        "scipy_version": getattr(scipy, "__version__", "unknown"),
        "n_genes": int(r_mat.shape[0]),
        "n_cell_types": int(r_mat.shape[1]),
        "n_spots": int(y_mat.shape[1]),
        "reference_profile_tsv": str(ref_p),
        "spatial_counts_tsv": str(spat_p),
        "output_dir": out_dir_rel.replace(os.sep, "/"),
        "spot_celltype_fractions_tsv": str(frac_path.relative_to(rr)).replace(os.sep, "/"),
        "note": "NNLS baseline. For RCTD use rule m3_deconvolution_rctd_run; for Cell2location use m3_deconvolution_cell2location_run.",
    }
    (out_dir / "deconvolution_s2_provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
    (out_dir / "deconvolution_s2.flag").write_text("ok\n", encoding="utf-8")
    print(f"Wrote {frac_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
