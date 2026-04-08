#!/usr/bin/env python3
"""Stage minimal reference + spatial h5ad under GLIOMA_TARGET_DATA_ROOT for M3 Cell2location smoke tests.

Paths match config/m3_deconvolution_cell2location_inputs.yaml defaults. Genes are aligned across both objects.

Usage:
  python scripts/m3_ci_stage_minimal_h5ad.py --data-root /path/to/staging
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import yaml


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="Write minimal Cell2location staging h5ad files.")
    ap.add_argument(
        "--data-root",
        type=Path,
        required=True,
        help="GLIOMA_TARGET_DATA_ROOT (absolute or cwd-relative).",
    )
    args = ap.parse_args()
    dr = args.data_root.resolve()
    rr = _repo_root()
    cfg_p = rr / "config" / "m3_deconvolution_cell2location_inputs.yaml"
    doc = yaml.safe_load(cfg_p.read_text(encoding="utf-8"))
    blk = doc.get("m3_deconvolution_cell2location") or {}
    ref_rel = blk.get("reference_h5ad", "m3_spatial_deconv/cell2location/reference_scRNA.h5ad")
    spat_rel = blk.get("spatial_h5ad", "m3_spatial_deconv/cell2location/spatial_visium.h5ad")

    try:
        import anndata as ad
    except ImportError as e:
        raise SystemExit(f"anndata required: {e}") from e

    rng = np.random.default_rng(42)
    genes = [f"GENE{i:03d}" for i in range(1, 121)]
    n_ref = 24
    n_spat = 16
    x_ref = rng.poisson(lam=12.0, size=(n_ref, len(genes))).astype(np.float32)
    x_spat = rng.poisson(lam=10.0, size=(n_spat, len(genes))).astype(np.float32)
    ref = ad.AnnData(X=x_ref)
    ref.var_names = genes
    ref.obs_names = [f"cell_{i:03d}" for i in range(n_ref)]
    ct = np.array(["Astro"] * 8 + ["Oligo"] * 8 + ["Tcell"] * 8, dtype=object)
    ref.obs["cell_type"] = ct

    spat = ad.AnnData(X=x_spat)
    spat.var_names = genes
    spat.obs_names = [f"spot_{i:03d}" for i in range(n_spat)]

    ref_p = dr / str(ref_rel).replace("/", os.sep)
    spat_p = dr / str(spat_rel).replace("/", os.sep)
    ref_p.parent.mkdir(parents=True, exist_ok=True)
    spat_p.parent.mkdir(parents=True, exist_ok=True)
    ref.write_h5ad(ref_p)
    spat.write_h5ad(spat_p)
    print(f"Wrote {ref_p} and {spat_p} ({len(genes)} shared genes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
