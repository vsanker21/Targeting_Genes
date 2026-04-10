"""Parse GEO series_matrix.txt.gz into a feature x sample float matrix (in-memory)."""

from __future__ import annotations

import gzip
from pathlib import Path

import numpy as np
import pandas as pd


def load_geo_series_matrix(matrix_gz: Path, sample_ids: list[str]) -> tuple[pd.Index, np.ndarray, list[str]]:
    """
    Returns (feature_index, values float64 [n_features, n_samples], columns_present).
    feature_index: probe / ID_REF labels.
    """
    want = list(sample_ids)
    with gzip.open(matrix_gz, "rt", errors="replace") as f:
        for line in f:
            if line.lower().startswith("!series_matrix_table_begin"):
                break
        else:
            raise ValueError(f"no matrix table in {matrix_gz}")
        header_line = f.readline()
        if not header_line:
            raise ValueError("empty matrix header")
        names = [p.strip().strip('"') for p in header_line.rstrip("\n").split("\t")]
        if names[0].upper() != "ID_REF":
            raise ValueError(f"unexpected first column {names[0]!r}")
        col_index = {n: i for i, n in enumerate(names)}
        miss = [s for s in want if s not in col_index]
        if miss:
            raise ValueError(f"sample IDs not in matrix columns (showing up to 10): {miss[:10]}")
        idx_cols = [col_index[s] for s in want]

        rows: list[str] = []
        chunks: list[list[float]] = []
        for raw in f:
            if raw.startswith("!") or raw.lower().startswith("!series_matrix_table_end"):
                break
            parts = raw.rstrip("\n").split("\t")
            if len(parts) < len(names):
                continue
            probe = parts[0].strip('"')
            rows.append(probe)
            try:
                vals = [float(parts[j]) for j in idx_cols]
            except ValueError:
                vals = [float("nan")] * len(idx_cols)
            chunks.append(vals)

    mat = np.asarray(chunks, dtype=np.float64)
    return pd.Index(rows), mat, want


def load_cgga_gene_counts(counts_tsv: Path, sample_ids: list[str]) -> tuple[pd.Index, np.ndarray, list[str]]:
    """gene_name x samples integer counts -> float matrix."""
    want = list(sample_ids)
    head = pd.read_csv(counts_tsv, sep="\t", nrows=0)
    missing = [s for s in want if s not in head.columns]
    if missing:
        raise ValueError(f"sample columns missing from counts (up to 10): {missing[:10]}")
    usecols = ["gene_name"] + want
    df = pd.read_csv(counts_tsv, sep="\t", usecols=usecols)
    genes = df["gene_name"].astype(str)
    mat = df[want].to_numpy(dtype=np.float64)
    return pd.Index(genes), mat, want
