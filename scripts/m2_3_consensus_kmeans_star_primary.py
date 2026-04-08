#!/usr/bin/env python3
"""
M2.3: Monti-style consensus clustering on log1p GDC STAR counts (Primary Tumor samples only).
Co-association matrix from repeated k-means on PCA space; hierarchical clustering chooses k (max silhouette).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def load_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "m2_3_consensus_clustering.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))["consensus_star_primary"]


def main() -> int:
    rr = repo_root()
    cfg = load_cfg()
    out_dir = rr / cfg["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    counts_path = rr / cfg["counts_matrix"]
    meta_path = rr / cfg["sample_meta"]
    if not counts_path.is_file() or not meta_path.is_file():
        print(f"Missing counts or meta: {counts_path} / {meta_path}", file=sys.stderr)
        return 2

    meta = pd.read_csv(meta_path, sep="\t", dtype=str, low_memory=False)
    col_key = cfg["meta_column_matrix"]
    st_col = cfg["sample_type_col"]
    allowed = {str(x).strip() for x in cfg["filter_sample_types"]}
    meta_sub = meta[meta[st_col].isin(allowed)].copy()
    keep_cols = [c for c in meta_sub[col_key].astype(str).tolist() if c]

    counts = pd.read_parquet(counts_path)
    if "gene_id" in counts.columns:
        counts = counts.set_index("gene_id")
    # columns = sample IDs
    use_cols = [c for c in keep_cols if c in counts.columns]
    if len(use_cols) < cfg["k_max"] + 2:
        prov = {
            "status": "skipped",
            "reason": "too few primary tumor samples in count matrix after meta join",
            "n_samples_requested": len(keep_cols),
            "n_samples_in_matrix": len(use_cols),
        }
        (out_dir / "consensus_provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
        pd.DataFrame(columns=["sample_id", "cluster", "k_chosen"]).to_csv(
            out_dir / "consensus_sample_clusters.tsv", sep="\t", index=False
        )
        print(prov["reason"])
        return 0

    X = counts[use_cols].astype(np.float64)
    X = np.log1p(X.values.T)  # samples x genes
    var = X.var(axis=0)
    n_top = min(int(cfg["n_top_variable_genes"]), X.shape[1])
    top_idx = np.argsort(-var)[:n_top]
    X = X[:, top_idx]

    n_comp = min(int(cfg["pca_components"]), X.shape[0] - 1, X.shape[1])
    if n_comp < 2:
        print("Not enough dimensions for PCA", file=sys.stderr)
        return 2
    pca = PCA(n_components=n_comp, random_state=int(cfg["random_seed_base"]))
    Z = pca.fit_transform(X)

    n_runs = int(cfg["n_kmeans_runs"])
    k_hi = int(cfg["k_max"])
    base_seed = int(cfg["random_seed_base"])
    co = np.zeros((Z.shape[0], Z.shape[0]), dtype=np.float64)
    for r in range(n_runs):
        km = KMeans(
            n_clusters=k_hi,
            n_init=int(cfg["kmeans_n_init"]),
            random_state=base_seed + r,
        )
        lab = km.fit_predict(Z)
        for i in range(Z.shape[0]):
            same = lab == lab[i]
            co[i, same] += 1.0
    co /= float(n_runs)
    dist = 1.0 - co
    np.fill_diagonal(dist, 0.0)
    condensed = squareform(dist, checks=False)
    link = linkage(condensed, method="average")

    k_min, k_max = int(cfg["k_min"]), int(cfg["k_max"])
    best_k, best_sil = k_min, -1.0
    for k in range(k_min, k_max + 1):
        labels = fcluster(link, k, criterion="maxclust")
        if len(set(labels)) < 2:
            continue
        sil = float(silhouette_score(Z, labels, metric="euclidean"))
        if sil > best_sil:
            best_sil, best_k = sil, k

    labels_final = fcluster(link, best_k, criterion="maxclust")
    out_df = pd.DataFrame(
        {"sample_id": use_cols, "cluster": labels_final.astype(int), "k_chosen": best_k},
    )
    out_df.to_csv(out_dir / "consensus_sample_clusters.tsv", sep="\t", index=False)

    prov = {
        "status": "ok",
        "method": cfg.get("method_name", ""),
        "n_samples": int(len(use_cols)),
        "n_genes_used": int(n_top),
        "pca_components": int(n_comp),
        "n_kmeans_runs": n_runs,
        "kmeans_upper_for_coassociation": k_hi,
        "k_chosen": int(best_k),
        "silhouette_euclidean_pca": float(best_sil),
        "counts_matrix": str(counts_path),
    }
    (out_dir / "consensus_provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(f"Wrote {out_dir / 'consensus_sample_clusters.tsv'} k={best_k} sil={best_sil:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
