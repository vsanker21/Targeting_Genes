#!/usr/bin/env python3
"""
Build a gene × sample matrix from GDC open TCGA-GBM STAR gene count TSVs.

- Reads gdc_files_manifest.json under data_root/gdc/tcga_gbm_open_star_counts/
- Fetches case/sample submitter IDs per file_id (cached under results/module1/)
- Keeps protein_coding genes with gene_id starting with ENSG (drops N_* stats rows)
- Modes: --kind tpm (tpm_unstranded) or --kind counts (unstranded STAR counts; integer)

Environment: GLIOMA_TARGET_DATA_ROOT (optional; else config/data_sources.yaml).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

GDC_FILE = "https://api.gdc.cancer.gov/files"


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = Path(__file__).resolve().parents[1] / "config" / "data_sources.yaml"
    dr = yaml.safe_load(cfg.read_text(encoding="utf-8")).get("data_root", "")
    return Path(dr.replace("/", os.sep))


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_manifest(gdc_dir: Path) -> list[dict[str, Any]]:
    p = gdc_dir / "gdc_files_manifest.json"
    if not p.is_file():
        raise FileNotFoundError(f"Missing manifest: {p}")
    obj = json.loads(p.read_text(encoding="utf-8"))
    return list(obj.get("hits") or [])


def fetch_file_case(file_id: str) -> dict[str, Any]:
    url = f"{GDC_FILE}/{file_id}?expand=cases,cases.samples"
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode("utf-8"))["data"]
    cases = data.get("cases") or []
    if not cases:
        return {
            "file_id": file_id,
            "case_submitter_id": None,
            "sample_submitter_id": None,
            "sample_type": None,
        }
    c0 = cases[0]
    samples = c0.get("samples") or []
    s0 = samples[0] if samples else {}
    return {
        "file_id": file_id,
        "case_submitter_id": c0.get("submitter_id"),
        "sample_submitter_id": s0.get("submitter_id"),
        "sample_type": s0.get("sample_type"),
    }


def load_or_fetch_case_meta(
    hits: list[dict[str, Any]], cache_path: Path, workers: int = 8
) -> dict[str, dict[str, Any]]:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    by_id: dict[str, dict[str, Any]] = {}
    if cache_path.is_file():
        prev = json.loads(cache_path.read_text(encoding="utf-8"))
        by_id = {x["file_id"]: x for x in prev.get("records", [])}
    need = [h["file_id"] for h in hits if h["file_id"] not in by_id]
    if need:
        print(f"GDC: fetching case metadata for {len(need)} files …")

        def one(fid: str) -> dict[str, Any]:
            return fetch_file_case(fid)

        with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
            futs = {ex.submit(one, fid): fid for fid in need}
            for fut in as_completed(futs):
                rec = fut.result()
                by_id[rec["file_id"]] = rec
        cache_path.write_text(
            json.dumps({"records": list(by_id.values())}, indent=2),
            encoding="utf-8",
        )
    return by_id


def column_name(meta: dict[str, Any], file_id: str) -> str:
    sid = meta.get("sample_submitter_id") or meta.get("case_submitter_id")
    if sid:
        return str(sid)
    return file_id[:12]


def read_gene_value_series(tsv_path: Path, col_name: str, value_column: str) -> pd.Series:
    df = pd.read_csv(tsv_path, sep="\t", comment="#", low_memory=False)
    if "gene_id" not in df.columns or value_column not in df.columns:
        raise ValueError(f"Unexpected columns in {tsv_path}: {df.columns.tolist()}")
    mask = df["gene_id"].astype(str).str.startswith("ENSG", na=False)
    if "gene_type" in df.columns:
        mask &= df["gene_type"].astype(str) == "protein_coding"
    vals = df.loc[mask].set_index("gene_id")[value_column]
    if value_column == "unstranded":
        s = vals.round().astype("int64")
    else:
        s = vals.astype(float)
    s.name = col_name
    return s


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--kind",
        choices=("tpm", "counts"),
        default="tpm",
        help="tpm: tpm_unstranded; counts: unstranded STAR gene counts (int64).",
    )
    args = ap.parse_args()

    root = data_root()
    rr = repo_root()
    gdc_dir = root / "gdc" / "tcga_gbm_open_star_counts"
    out_dir = rr / "results" / "module2"
    cache_path = rr / "results" / "module1" / "gdc_file_case_metadata.json"
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.kind == "tpm":
        value_col = "tpm_unstranded"
        matrix_name = "tcga_gbm_star_tpm_matrix.parquet"
    else:
        value_col = "unstranded"
        matrix_name = "tcga_gbm_star_unstranded_counts_matrix.parquet"

    hits = load_manifest(gdc_dir)
    if not hits:
        print("No files in manifest.", file=sys.stderr)
        return 1

    meta_by_file = load_or_fetch_case_meta(hits, cache_path)
    series_list: list[pd.Series] = []
    meta_rows: list[dict[str, Any]] = []
    used_names: dict[str, int] = {}

    for h in hits:
        fid = h["file_id"]
        fn = h["file_name"]
        tsv = gdc_dir / fn
        if not tsv.is_file():
            print(f"SKIP missing file {tsv}", file=sys.stderr)
            continue
        meta = meta_by_file.get(fid) or {}
        base = column_name(meta, fid)
        n = used_names.get(base, 0)
        used_names[base] = n + 1
        col = base if n == 0 else f"{base}__{fid[:8]}"
        series_list.append(read_gene_value_series(tsv, col, value_col))
        meta_rows.append(
            {
                "column_name": col,
                "file_id": fid,
                "file_name": fn,
                "case_submitter_id": meta.get("case_submitter_id"),
                "sample_submitter_id": meta.get("sample_submitter_id"),
                "sample_type": meta.get("sample_type"),
            }
        )

    if not series_list:
        print("No TSV series loaded.", file=sys.stderr)
        return 2

    print(f"Concatenating {len(series_list)} samples …")
    mat = pd.concat(series_list, axis=1)
    mat.index.name = "gene_id"
    mat.columns.name = "sample"

    matrix_path = out_dir / matrix_name
    meta_path = out_dir / "tcga_gbm_sample_meta.tsv"
    mat.to_parquet(matrix_path)
    # Avoid parallel Snakemake jobs both rewriting the same meta; TPM build is the default writer.
    if args.kind == "tpm" or not meta_path.is_file():
        pd.DataFrame(meta_rows).to_csv(meta_path, sep="\t", index=False)
        print(f"Wrote {meta_path}")
    print(f"Wrote {matrix_path} shape={mat.shape} dtype={mat.dtypes.iloc[0] if len(mat.columns) else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
