"""Shared DepMap release discovery and GBM model selection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def extend_dea_pairs_paths(repo_root: Path, block: dict[str, Any]) -> list[tuple[Path, Path]]:
    """Base Welch + OLS DEA paths plus optional recount3 (or other) pairs from YAML extra_dea_pairs."""
    paths: list[tuple[Path, Path]] = [
        (repo_root / str(block["dea_ols_tsv"]), repo_root / str(block["output_ols"])),
        (repo_root / str(block["dea_welch_tsv"]), repo_root / str(block["output_welch"])),
    ]
    for pair in block.get("extra_dea_pairs") or []:
        if not isinstance(pair, dict):
            continue
        inp = pair.get("input") or pair.get("dea_tsv")
        outp = pair.get("output")
        if inp and outp:
            paths.append((repo_root / str(inp), repo_root / str(outp)))
    return paths


def latest_depmap_dir(data_root: Path) -> Path:
    d = data_root / "depmap"
    if not d.is_dir():
        raise FileNotFoundError(f"No depmap directory: {d}")
    subs = sorted([p for p in d.iterdir() if p.is_dir()], key=lambda p: p.name.lower())
    if not subs:
        raise FileNotFoundError(f"No DepMap release subfolders under {d}")
    return subs[-1]


def detect_gbm_models(
    model_path: Path,
    primary_substr: str,
    lineage_fallback: str | None,
) -> list[str]:
    mdf = pd.read_csv(model_path, low_memory=False)
    col_id = next(
        (c for c in ("ModelID", "model_id", "ModelId") if c in mdf.columns),
        mdf.columns[0],
    )
    prim = mdf.get("OncotreePrimaryDisease", pd.Series([""] * len(mdf)))
    mask = prim.astype(str).str.contains(primary_substr, case=False, na=False)
    gbm = mdf.loc[mask, col_id].astype(str).tolist()
    if not gbm and lineage_fallback and "OncotreeLineage" in mdf.columns:
        lin = mdf["OncotreeLineage"].astype(str)
        mask2 = lin.str.contains(lineage_fallback, case=False, na=False)
        gbm = mdf.loc[mask2, col_id].astype(str).tolist()
    return sorted(set(gbm))
