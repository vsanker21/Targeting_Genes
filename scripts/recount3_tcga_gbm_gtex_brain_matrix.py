#!/usr/bin/env python3
"""
Build TCGA-GBM (recount3) + GTEx brain integer count matrix and sample table for DE (PyDESeq2 / edgeR).

Shared by dea_deseq2_recount3_tcga_gbm_vs_gtex_brain.py. Not GDC STAR — recount3 GENCODE G029.
"""

from __future__ import annotations

import gzip
import os
import random
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(str(cfg["data_root"]).replace("/", os.sep))


def base_ensg(gid: str) -> str:
    g = str(gid)
    if g.startswith("ENSG") and "." in g:
        return g.rsplit(".", 1)[0]
    return g


def star_gene_bases(star_parquet: Path) -> set[str]:
    genes_only = pd.read_parquet(star_parquet, columns=[])
    if genes_only.index.name == "gene_id":
        ids = genes_only.index.astype(str)
    else:
        ids = pd.read_parquet(star_parquet, columns=["gene_id"])["gene_id"].astype(str)
    return {base_ensg(x) for x in ids}


def load_tcga_recount3(path: Path, star_bases: set[str]) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        sep="\t",
        compression="gzip",
        comment="#",
        low_memory=False,
        index_col=0,
    )
    df.index = [base_ensg(x) for x in df.index.astype(str)]
    df = df[df.index.isin(star_bases)]
    df = df[~df.index.duplicated(keep="first")]
    return df.astype(int)


def parse_max_gtex_brain_samples(raw: Any) -> int | None:
    """
    None / 'all' / negative / 0 => use all GTEx brain columns.
    Positive int => subsample that many columns (random_seed).
    """
    if raw is None:
        return None
    if isinstance(raw, str) and raw.strip().lower() in ("all", ""):
        return None
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    return n


def stream_gtex_subset(
    path: Path,
    star_bases: set[str],
    max_normals: int | None,
    seed: int,
) -> tuple[dict[str, list[int]], list[str]]:
    """Return {gene_base: counts per picked column} and picked sample column names."""
    out: dict[str, list[int]] = {}
    picked_names: list[str] = []
    rng = random.Random(seed)
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("gene_id"):
                header = line.strip().split("\t")
                samples = header[1:]
                n_s = len(samples)
                if max_normals is None or max_normals >= n_s:
                    pick = list(range(n_s))
                else:
                    pick = sorted(rng.sample(range(n_s), k=max_normals))
                picked_names = [samples[i] for i in pick]
                break
        else:
            raise ValueError(f"No header in {path}")
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            b = base_ensg(parts[0])
            if b not in star_bases or b in out:
                continue
            try:
                vals = [int(float(parts[1 + i])) for i in pick]
            except (ValueError, IndexError):
                continue
            out[b] = vals
    return out, picked_names


def ensure_recount3_gz(rr: Path, tcga_gz: Path, gtex_gz: Path) -> int:
    if tcga_gz.is_file() and gtex_gz.is_file():
        return 0
    print("recount3 G029 files missing; running download_recount3_harmonized_g029.py …")
    r = subprocess.run(
        [sys.executable, str(rr / "scripts" / "download_recount3_harmonized_g029.py")],
        cwd=str(rr),
        check=False,
    )
    return r.returncode


def load_recount3_block(rr: Path) -> dict[str, Any]:
    cfg_path = rr / "config" / "deseq2_recount3_tcga_gtex.yaml"
    doc = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    block = doc.get("deseq2_recount3_tcga_gbm_vs_gtex_brain") or {}
    return block


def resolve_cache(block: dict[str, Any]) -> Path:
    sub = block.get("local_cache_subdir", "recount3/harmonized_g029").replace("/", os.sep)
    dr = data_root()
    env_cache = os.environ.get("RECOUNT3_CACHE_DIR", "").strip()
    return Path(env_cache).resolve() if env_cache else (dr / sub)


def build_counts_and_coldata(
    block: dict[str, Any],
    rr: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """
    Full gene x sample counts (tumor TCGA columns + GTEx brain columns) and coldata (index=sample_id).
    aux has paths and streaming metadata for provenance.
    """
    star_path = rr / str(block["star_counts_matrix"]).replace("/", os.sep)
    if not star_path.is_file():
        raise FileNotFoundError(f"Missing STAR matrix (gene universe): {star_path}")

    cache = resolve_cache(block)
    tcga_gz = cache / Path(block["tcga_gbm_g029_relpath"]).name
    gtex_gz = cache / Path(block["gtex_brain_g029_relpath"]).name

    code = ensure_recount3_gz(rr, tcga_gz, gtex_gz)
    if code != 0:
        raise RuntimeError(f"recount3 download failed with exit code {code}")
    if not tcga_gz.is_file() or not gtex_gz.is_file():
        raise FileNotFoundError(f"Missing after download:\n  {tcga_gz}\n  {gtex_gz}")

    star_bases = star_gene_bases(star_path)
    max_n = parse_max_gtex_brain_samples(block.get("max_gtex_brain_samples"))
    seed = int(block.get("random_seed") or 42)

    tcga = load_tcga_recount3(tcga_gz, star_bases)
    gtex_dict, gtex_ids = stream_gtex_subset(gtex_gz, star_bases, max_n, seed)

    common = sorted(tcga.index.intersection(gtex_dict.keys()))
    if len(common) < 100:
        raise ValueError(f"Too few shared genes ({len(common)}); check inputs.")

    tcga_c = tcga.loc[common]
    norm_mat = pd.DataFrame(
        {gtex_ids[j]: [gtex_dict[b][j] for b in common] for j in range(len(gtex_ids))},
        index=common,
        dtype="int64",
    )
    counts = pd.concat([tcga_c, norm_mat], axis=1)
    counts.index.name = "gene_id"

    rows = []
    for c in tcga_c.columns:
        rows.append({"sample_id": str(c), "condition": "Tumor"})
    for sid in gtex_ids:
        rows.append({"sample_id": str(sid), "condition": "Normal"})
    coldata = pd.DataFrame(rows).set_index("sample_id")

    aux = {
        "tcga_gz": tcga_gz,
        "gtex_gz": gtex_gz,
        "max_gtex_brain_samples_resolved": max_n,
        "random_seed": seed,
        "gtex_brain_sample_columns": gtex_ids,
        "n_gtex_columns": len(gtex_ids),
    }
    return counts, coldata, aux


def write_de_matrix_assets(out_dir: Path, counts: pd.DataFrame, coldata: pd.DataFrame, block: dict[str, Any]) -> tuple[Path, Path]:
    """Wide counts parquet (gene_id column) + sample meta TSV for R edgeR."""
    out_dir.mkdir(parents=True, exist_ok=True)
    matrix_name = str(block.get("prepared_counts_matrix", "recount3_de_counts_matrix.parquet"))
    meta_name = str(block.get("prepared_sample_meta", "recount3_de_sample_meta.tsv"))
    matrix_path = out_dir / matrix_name.replace("/", os.sep)
    meta_path = out_dir / meta_name.replace("/", os.sep)

    wide = counts.reset_index()
    if wide.columns[0] != "gene_id":
        wide = wide.rename(columns={wide.columns[0]: "gene_id"})
    wide.to_parquet(matrix_path, index=False)
    coldata.reset_index().to_csv(meta_path, sep="\t", index=False)
    return matrix_path, meta_path
