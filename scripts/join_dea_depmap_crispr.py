#!/usr/bin/env python3
"""
Outline Module 2 §2.2 / Module 4: join DEA genes with DepMap CRISPR gene effect (median across GBM models).

DepMap Public 25Q3+ CRISPRGeneEffect.csv: rows = ModelID (ACH-*), columns = genes as `SYMBOL (entrez)`.
Earlier releases with genes-as-rows are not auto-detected here — use a matching DepMap bundle.

Requires: data_root/depmap/<release>/ from download_all_required.py, plus HGNC for Ensembl→Entrez.
See config/module2_integration.yaml
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from depmap_shared import detect_gbm_models, extend_dea_pairs_paths, latest_depmap_dir


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def load_integration_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module2_integration.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def ensg_base(gene_id: str) -> str:
    s = str(gene_id).strip()
    if "." in s and s.startswith("ENSG"):
        return s.split(".", 1)[0]
    return s


def entrez_from_crispr_gene_col(name: str) -> int | None:
    m = re.search(r"\((\d+)\)\s*$", str(name).strip())
    return int(m.group(1)) if m else None


def load_ensg_to_entrez(hgnc_path: Path, wanted_ensg: set[str]) -> dict[str, int]:
    hg = pd.read_csv(hgnc_path, sep="\t", dtype=str, low_memory=False)
    if "ensembl_gene_id" not in hg.columns or "entrez_id" not in hg.columns:
        raise ValueError(f"HGNC missing ensembl_gene_id or entrez_id: {hgnc_path}")
    out: dict[str, int] = {}
    for _, row in hg.iterrows():
        eid = str(row.get("ensembl_gene_id", "") or "").strip()
        ez = str(row.get("entrez_id", "") or "").strip()
        if not eid or not ez or not ez.isdigit():
            continue
        base = ensg_base(eid)
        if base in wanted_ensg:
            out[base] = int(ez)
    return out


def read_crispr_gbm_gene_aggregates(
    crispr_path: Path,
    gbm_models: list[str],
    ensg_to_entrez: dict[str, int],
) -> tuple[pd.DataFrame, int]:
    """
    CRISPRGeneEffect: index = ModelID, columns = `SYMBOL (entrez)`.
    Returns DataFrame indexed by Ensembl (no version) with columns median, min, max over GBM lines.
    """
    hdr = pd.read_csv(crispr_path, nrows=0)
    idx_name = hdr.columns[0]
    entrez_to_col: dict[int, str] = {}
    for c in hdr.columns[1:]:
        ez = entrez_from_crispr_gene_col(c)
        if ez is not None:
            entrez_to_col[ez] = c
    wanted_cols: list[str] = []
    col_to_ensg: dict[str, str] = {}
    for ensg, ez in ensg_to_entrez.items():
        col = entrez_to_col.get(ez)
        if col:
            wanted_cols.append(col)
            col_to_ensg[col] = ensg
    if not wanted_cols:
        return pd.DataFrame(), 0
    usecols = [idx_name] + wanted_cols
    df = pd.read_csv(crispr_path, index_col=0, usecols=usecols, low_memory=False)
    df.index = df.index.astype(str)
    gbm_present = [m for m in gbm_models if m in df.index]
    if not gbm_present:
        return pd.DataFrame(), 0
    sub = df.loc[gbm_present]
    med = sub.median(axis=0)
    mn = sub.min(axis=0)
    mx = sub.max(axis=0)
    rows: list[tuple[str, float, float, float]] = []
    for col in med.index:
        e = col_to_ensg.get(col)
        if not e:
            continue
        rows.append((e, float(med[col]), float(mn[col]), float(mx[col])))
    agg = pd.DataFrame(rows, columns=["ensg", "median", "min", "max"]).set_index("ensg")
    return agg, len(gbm_present)


def write_depmap_na_outputs(
    paths: list[tuple[Path, Path]],
    reason: str,
) -> None:
    rr = repo_root()
    for dea_p, out_p in paths:
        if not dea_p.is_file():
            continue
        dea = pd.read_csv(dea_p, sep="\t")
        dea["depmap_crispr_median_gbm"] = np.nan
        dea["depmap_crispr_min_gbm"] = np.nan
        dea["depmap_crispr_max_gbm"] = np.nan
        dea["depmap_n_gbm_lines"] = 0
        out_p.parent.mkdir(parents=True, exist_ok=True)
        dea.to_csv(out_p, sep="\t", index=False)
        print(f"Wrote {out_p} (DepMap unavailable: {reason})")
    prov = {"status": "skipped", "reason": reason}
    (rr / "results" / "module3" / "depmap_crispr_join_provenance.json").write_text(
        json.dumps(prov, indent=2),
        encoding="utf-8",
    )


def join_one_dea(
    dea_path: Path,
    out_path: Path,
    crispr_agg: pd.DataFrame,
    n_models: int,
) -> None:
    dea = pd.read_csv(dea_path, sep="\t")
    dea["_ensg"] = dea["gene_id"].map(ensg_base)
    if crispr_agg.empty:
        dea["depmap_crispr_median_gbm"] = np.nan
        dea["depmap_crispr_min_gbm"] = np.nan
        dea["depmap_crispr_max_gbm"] = np.nan
    else:
        hit = crispr_agg.reindex(dea["_ensg"])
        dea["depmap_crispr_median_gbm"] = hit["median"].to_numpy()
        dea["depmap_crispr_min_gbm"] = hit["min"].to_numpy()
        dea["depmap_crispr_max_gbm"] = hit["max"].to_numpy()
    dea["depmap_n_gbm_lines"] = n_models
    dea = dea.drop(columns=["_ensg"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dea.to_csv(out_path, sep="\t", index=False)
    non_na = dea["depmap_crispr_median_gbm"].notna().sum()
    print(f"Wrote {out_path} rows={len(dea)} with DepMap median CRISPR for {non_na} genes")


def main() -> int:
    cfg = load_integration_cfg()
    dm = cfg.get("depmap_crispr_join") or {}
    root = data_root()
    rr = repo_root()
    paths = extend_dea_pairs_paths(rr, dm)
    try:
        rel = latest_depmap_dir(root)
    except FileNotFoundError as e:
        print(f"WARNING: {e}", file=sys.stderr)
        write_depmap_na_outputs(paths, str(e))
        return 0
    crispr_path = rel / dm.get("crispr_gene_effect_csv", "CRISPRGeneEffect.csv")
    model_path = rel / dm.get("model_csv", "Model.csv")
    if not crispr_path.is_file() or not model_path.is_file():
        print(f"WARNING: Missing DepMap files under {rel}", file=sys.stderr)
        write_depmap_na_outputs(paths, "missing CRISPRGeneEffect.csv or Model.csv")
        return 0

    hrel = dm.get("hgnc_tsv", "{data_root}/references/hgnc_complete_set.txt")
    hgnc_path = Path(hrel.replace("{data_root}", str(root)).replace("/", os.sep))
    if not hgnc_path.is_file():
        print(f"WARNING: Missing HGNC at {hgnc_path}", file=sys.stderr)
        write_depmap_na_outputs(paths, "missing HGNC TSV for Ensembl→Entrez mapping")
        return 0

    primary = str(dm.get("oncotree_primary_contains", "Glioblastoma"))
    lineage_fb = dm.get("oncotree_lineage_fallback")
    lineage_fb = str(lineage_fb) if lineage_fb else None

    gbm_models = detect_gbm_models(model_path, primary, lineage_fb)
    if not gbm_models:
        print(
            "WARNING: No DepMap models matched GBM filter; writing NaN DepMap columns.",
            file=sys.stderr,
        )
        write_depmap_na_outputs(paths, "no GBM models matched Oncotree filter")
        return 0
    print(f"DepMap release {rel.name}: {len(gbm_models)} GBM-related models in Model.csv")

    wanted: set[str] = set()
    for dea_p, _ in paths:
        if not dea_p.is_file():
            continue
        d = pd.read_csv(dea_p, sep="\t", usecols=["gene_id"])
        wanted.update(d["gene_id"].map(ensg_base))

    if not wanted:
        print("No DEA tables found.", file=sys.stderr)
        return 3
    if not any(p[0].is_file() for p in paths):
        print("No DEA input files on disk.", file=sys.stderr)
        return 3

    try:
        ensg_to_ez = load_ensg_to_entrez(hgnc_path, wanted)
        crispr_agg, n_lines = read_crispr_gbm_gene_aggregates(crispr_path, gbm_models, ensg_to_ez)
    except Exception as e:
        print(f"WARNING: DepMap CRISPR join failed: {e}", file=sys.stderr)
        write_depmap_na_outputs(paths, f"crispr_error: {e}")
        return 0

    if crispr_agg.empty or n_lines == 0:
        print("WARNING: No overlapping CRISPR columns or GBM lines in matrix.", file=sys.stderr)
        write_depmap_na_outputs(paths, "empty CRISPR aggregate (check ModelID vs matrix index)")
        return 0

    prov = {
        "status": "ok",
        "crispr_layout": "rows=models_columns=SYMBOL_entrez",
        "depmap_release_dir": str(rel),
        "n_gbm_models_in_model_csv": len(gbm_models),
        "n_gbm_models_in_crispr_matrix": n_lines,
        "n_dea_genes_with_entrez_in_hgnc": len(ensg_to_ez),
        "n_genes_matched_in_crispr": int(len(crispr_agg)),
        "oncotree_primary_contains": primary,
    }
    (rr / "results" / "module3" / "depmap_crispr_join_provenance.json").write_text(
        json.dumps(prov, indent=2),
        encoding="utf-8",
    )

    for dea_p, out_p in paths:
        if not dea_p.is_file():
            print(f"SKIP missing DEA {dea_p}", file=sys.stderr)
            continue
        join_one_dea(dea_p, out_p, crispr_agg, n_lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
