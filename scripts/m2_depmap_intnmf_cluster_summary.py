#!/usr/bin/env python3
"""
Link DepMap IntNMF cluster assignments to Model.csv (lineage / subtype) and summarize mutation burden.

Inputs:
  - MOVICS cluster TSV (columns samID, clust from m2_movics_intnmf_depmap_mae)
  - DepMap Model.csv (under latest release under data_root/depmap/)
  - Optional: mutation_binary MAE .tsv.gz for per-model mutation counts
  - Optional: CRISPRGeneEffect.csv in the same DepMap release (mean dependency per model)

Outputs (under results/module3/m2_movics_intnmf_depmap_mae/ by default):
  - cluster_model_annotations.tsv
  - cluster_summary.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from depmap_shared import latest_depmap_dir  # noqa: E402


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def _top_counts(series: pd.Series, n: int = 5) -> list[dict[str, Any]]:
    vc = series.astype(str).value_counts().head(n)
    return [{"value": str(k), "n": int(v)} for k, v in vc.items()]


def _read_mutation_burden(mut_gz: Path, model_ids: list[str]) -> pd.Series:
    df = pd.read_csv(mut_gz, sep="\t", compression="gzip", index_col=0)
    df = df[[c for c in df.columns if c in model_ids]]
    return df.sum(axis=0).rename("mutation_burden")


def _read_crispr_means(crispr_csv: Path, model_ids: set[str]) -> pd.Series | None:
    """CRISPRGeneEffect: rows = ModelID (ACH-*), columns = genes (see join_dea_depmap_crispr.py)."""
    if not crispr_csv.is_file():
        return None
    parts: list[pd.DataFrame] = []
    for ch in pd.read_csv(crispr_csv, index_col=0, chunksize=500, low_memory=False):
        ch = ch[ch.index.astype(str).isin(model_ids)]
        if ch.empty:
            continue
        parts.append(ch.apply(pd.to_numeric, errors="coerce"))
    if not parts:
        return None
    df = pd.concat(parts)
    return df.mean(axis=1, skipna=True).rename("mean_crispr_dependency")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--clusters", type=Path, required=True, help="movics_depmap_mae_clusters.tsv")
    ap.add_argument("--out-annotations", type=Path, required=True)
    ap.add_argument("--out-summary", type=Path, required=True)
    ap.add_argument(
        "--mutation-gz",
        type=Path,
        default=None,
        help="Optional depmap_gbm_mutation_binary.tsv.gz for burden per model",
    )
    ap.add_argument(
        "--skip-crispr",
        action="store_true",
        help="Do not load CRISPRGeneEffect.csv even if present",
    )
    args = ap.parse_args()

    dr = data_root()
    rel = latest_depmap_dir(dr)
    model_csv = rel / "Model.csv"
    if not model_csv.is_file():
        print(f"Missing {model_csv}", file=sys.stderr)
        return 1

    cl = pd.read_csv(args.clusters, sep="\t")
    id_col = "samID" if "samID" in cl.columns else cl.columns[0]
    cl = cl.rename(columns={id_col: "ModelID"})
    mdf = pd.read_csv(model_csv, low_memory=False)
    mid = next((c for c in ("ModelID", "model_id", "ModelId") if c in mdf.columns), None)
    if mid is None:
        print(
            f"Model.csv missing ModelID column (got {list(mdf.columns)[:8]}...): {model_csv}",
            file=sys.stderr,
        )
        return 1
    keep_cols = [mid] + [
        c
        for c in (
            "CellLineName",
            "OncotreePrimaryDisease",
            "OncotreeSubtype",
            "OncotreeLineage",
            "ModelType",
            "PatientSubtypeFeatures",
            "PrimaryOrMetastasis",
            "SourceType",
        )
        if c in mdf.columns
    ]
    mdf = mdf[keep_cols].drop_duplicates(subset=[mid])
    merged = cl.merge(mdf, left_on="ModelID", right_on=mid, how="left")
    args.out_annotations.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(args.out_annotations, sep="\t", index=False)

    models = merged["ModelID"].astype(str).tolist()
    mut_burden: pd.Series | None = None
    mut_path = args.mutation_gz
    if mut_path is None:
        fetch_doc = yaml.safe_load(
            (repo_root() / "config" / "m2_movics_data_fetch.yaml").read_text(encoding="utf-8")
        )
        blk = fetch_doc.get("depmap_gbm_mae") or {}
        fn = blk.get("filenames") or {}
        od = str(blk.get("out_dir", "omics/multi_omics_mae"))
        mut_path = dr / od.replace("/", os.sep) / fn.get(
            "mutation_binary_gz", "depmap_gbm_mutation_binary.tsv.gz"
        )
        if not mut_path.is_file():
            mut_path = None
    if isinstance(mut_path, Path) and mut_path.is_file():
        mut_burden = _read_mutation_burden(mut_path, models)

    crispr_mean: pd.Series | None = None
    if not args.skip_crispr:
        crispr_p = rel / "CRISPRGeneEffect.csv"
        crispr_mean = _read_crispr_means(crispr_p, set(models))

    summary: dict[str, Any] = {
        "data_root": str(dr.resolve()),
        "depmap_release": rel.name,
        "n_models_in_clusters": int(len(merged)),
        "n_clusters": int(merged["clust"].nunique()),
        "clusters": {},
        "tcga_vs_depmap_note": (
            "TCGA rule m2_movics_intnmf_tcga_gbm = primary tumor expression (GDC STAR); "
            "DepMap rule m2_movics_intnmf_depmap_mae = cell-line models (this summary). "
            "Do not treat cluster IDs as comparable across cohorts."
        ),
    }

    for cval, sub in merged.groupby("clust"):
        key = str(int(cval) if pd.notna(cval) and float(cval) == int(float(cval)) else cval)
        block: dict[str, Any] = {"n": int(len(sub))}
        if "OncotreeLineage" in sub.columns:
            block["top_lineages"] = _top_counts(sub["OncotreeLineage"].fillna("NA"))
        if "OncotreePrimaryDisease" in sub.columns:
            block["top_primary_disease"] = _top_counts(sub["OncotreePrimaryDisease"].fillna("NA"))
        if "OncotreeSubtype" in sub.columns:
            block["top_subtypes"] = _top_counts(sub["OncotreeSubtype"].fillna("NA"))
        if mut_burden is not None:
            mb = mut_burden.reindex(sub["ModelID"].astype(str))
            block["mean_mutation_burden"] = round(float(mb.mean(skipna=True)), 4)
            block["median_mutation_burden"] = round(float(mb.median(skipna=True)), 4)
        if crispr_mean is not None:
            cm = crispr_mean.reindex(sub["ModelID"].astype(str))
            block["mean_crispr_dependency"] = round(float(cm.mean(skipna=True)), 6)  # mean of row means (genes)
        summary["clusters"][key] = block

    if crispr_mean is None:
        summary["crispr"] = {"status": "skipped", "reason": "no_CRISPRGeneEffect_or_no_column_overlap"}
    else:
        summary["crispr"] = {"status": "ok", "file": "CRISPRGeneEffect.csv"}

    args.out_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {args.out_annotations} and {args.out_summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
