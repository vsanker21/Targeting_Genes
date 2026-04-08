#!/usr/bin/env python3
"""
M3: GSE57872-oriented Scanpy pipeline — QC (genes/counts/mito) + HVG + neighbors + Leiden.
Resolves input under data_root from config globs or input_override_relative.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from glob import glob
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def load_full_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "m3_gse57872_scanpy.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def resolve_input_path(dr: Path, cfg: dict[str, Any]) -> Path | None:
    override = cfg.get("input_override_relative")
    if override:
        p = dr / str(override).replace("/", os.sep)
        return p if p.is_file() else None
    for pat in cfg.get("input_search_globs", []):
        full = str(dr / pat.replace("/", os.sep))
        hits = sorted({Path(x) for x in glob(full) if Path(x).is_file()})
        if hits:
            return hits[0]
    return None


def run_scanpy(ad, cfg: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    import scanpy as sc

    qc = cfg["qc"]
    proc = cfg["processing"]
    sc.settings.verbosity = 1
    ad.var_names_make_unique()
    ad.obs["n_counts"] = np.asarray(ad.X.sum(axis=1)).ravel()
    ad.obs["n_genes"] = np.asarray((ad.X > 0).sum(axis=1)).ravel()
    mito_prefix = str(qc.get("mito_prefix", "MT-"))
    ad.var["mito"] = ad.var_names.str.startswith(mito_prefix)
    ad.obs["pct_mito"] = (
        np.asarray(ad[:, ad.var["mito"].values].X.sum(axis=1)).ravel()
        / np.clip(ad.obs["n_counts"].values, 1e-9, None)
        * 100.0
    )
    sc.pp.filter_cells(ad, min_genes=int(qc["min_genes"]))
    sc.pp.filter_cells(ad, min_counts=float(qc["min_counts"]))
    ad = ad[ad.obs["pct_mito"] < float(qc["max_pct_mito"])].copy()
    sc.pp.normalize_total(ad, target_sum=1e4)
    sc.pp.log1p(ad)
    sc.pp.highly_variable_genes(ad, n_top_genes=int(proc["n_top_genes_hvg"]), subset=True)
    sc.tl.pca(ad, n_comps=min(int(proc["n_pcs"]), ad.shape[0] - 1, ad.shape[1] - 1))
    sc.pp.neighbors(ad, n_neighbors=int(proc["n_neighbors"]), n_pcs=int(proc["n_pcs"]))
    sc.tl.leiden(
        ad,
        resolution=float(proc["leiden_resolution"]),
        random_state=int(proc["random_seed"]),
        flavor="igraph",
        n_iterations=2,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    obs_out = ad.obs[["n_counts", "n_genes", "pct_mito", "leiden"]].copy()
    obs_out.insert(0, "cell_id", obs_out.index.astype(str))
    obs_out.to_csv(out_dir / "obs_qc_leiden.tsv", sep="\t")

    metrics = {
        "n_cells_after_qc": int(ad.n_obs),
        "n_genes_after_hvg": int(ad.n_vars),
        "n_leiden_clusters": int(ad.obs["leiden"].nunique()),
        "leiden_resolution": float(proc["leiden_resolution"]),
        "random_seed": int(proc["random_seed"]),
    }
    (out_dir / "qc_cluster_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out-dir",
        type=str,
        default="",
        help="Override output directory (default: from config m3_gse57872_scanpy.yaml).",
    )
    args = ap.parse_args()

    rr = repo_root()
    full = load_full_cfg()
    cfg_ds = full["dataset"]
    out_dir = Path(args.out_dir) if args.out_dir else rr / full["output_dir"]

    try:
        import scanpy  # noqa: F401
    except ImportError:
        print("Install scanpy (see requirements-optional.txt) for m3_scrna_scanpy_qc_cluster.py", file=sys.stderr)
        return 2

    prov: dict[str, Any] = {"dataset_geo": cfg_ds.get("geo_accession"), "output_dir": str(out_dir)}

    dr = data_root()
    inp = resolve_input_path(dr, full)
    if inp is None:
        prov["status"] = "missing_input"
        prov["searched_under_data_root"] = str(dr)
        prov["globs"] = list(full.get("input_search_globs", []))
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "run_provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
        print(
            "No GSE57872 input found under data_root; stage .h5ad or counts or set "
            "input_override_relative in config/m3_gse57872_scanpy.yaml.",
            file=sys.stderr,
        )
        return 3

    prov["input_path"] = str(inp)
    prov["input_mode"] = "file"

    import anndata as ad
    import scanpy as sc

    if inp.suffix.lower() == ".h5ad":
        adata = sc.read_h5ad(inp)
    else:
        df = pd.read_csv(inp, index_col=0)
        # Expect cells × genes (rows = cells); transpose if clearly genes × cells
        if df.shape[0] < df.shape[1] and df.shape[0] < 500:
            df = df.T
        adata = ad.AnnData(
            X=df.values.astype(np.float32),
            obs=pd.DataFrame(index=df.index.astype(str)),
            var=pd.DataFrame(index=df.columns.astype(str)),
        )

    metrics = run_scanpy(adata, full, out_dir)
    prov["status"] = "ok"
    prov["metrics"] = metrics
    (out_dir / "run_provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
