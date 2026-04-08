#!/usr/bin/env python3
"""
Extract TCGA GBM primary tumor + GTEx brain (cortex / frontal / cingulate / cerebellum)
columns from TOIL RSEM gene TPM — single pipeline for tumor and normals.

Writes Parquet (genes × samples, float32) and a sample manifest for DEA.
"""

from __future__ import annotations

import gzip
import json
import os
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
    cfg = repo_root() / "config" / "data_sources.yaml"
    dr = yaml.safe_load(cfg.read_text(encoding="utf-8")).get("data_root", "")
    return Path(dr.replace("/", os.sep))


def load_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "dea_tumor_normal.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def expand(p: str, root: Path) -> Path:
    return Path(p.replace("{data_root}", str(root)))


def collect_samples(cfg: dict[str, Any], pheno_path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Select tumor + GTEx brain normals; deduplicate IDs; sort for reproducible matrix column order
    (all tumor columns ascending, then all normal columns ascending). Manifest rows match column order.
    """
    allow = set(cfg["gtex_brain_detailed_categories"])
    tum = cfg["tumor"]
    by_id: dict[str, dict[str, Any]] = {}
    tumor_ids: list[str] = []
    normal_ids: list[str] = []

    with gzip.open(pheno_path, "rt", encoding="utf-8", errors="replace") as f:
        header = f.readline().strip().split("\t")
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) != len(header):
                continue
            row = dict(zip(header, parts))
            sid = row.get("sample", "")
            if not sid:
                continue
            if tum["study"] == row.get("_study") and tum["primary_site"] == row.get("_primary_site"):
                if tum["sample_type"] != row.get("_sample_type"):
                    continue
                if tum["detailed_category_substring"] not in row.get("detailed_category", ""):
                    continue
                if sid not in by_id:
                    tumor_ids.append(sid)
                by_id[sid] = {
                    "sample_id": sid,
                    "group": "tumor",
                    "study": row.get("_study"),
                    "detailed_category": row.get("detailed_category"),
                    "sample_type": row.get("_sample_type"),
                }
            elif row.get("_study") == "GTEX" and row.get("detailed_category") in allow:
                if sid not in by_id:
                    normal_ids.append(sid)
                by_id[sid] = {
                    "sample_id": sid,
                    "group": "normal",
                    "study": "GTEX",
                    "detailed_category": row.get("detailed_category"),
                    "sample_type": row.get("_sample_type", "Normal Tissue"),
                }

    tumor_ids = sorted(tumor_ids)
    normal_ids = sorted(normal_ids)
    ordered_ids = tumor_ids + normal_ids
    manifest_rows = [by_id[s] for s in ordered_ids]
    usecols = ["sample"] + ordered_ids
    return manifest_rows, usecols


def main() -> int:
    cfg = load_cfg()
    root = data_root()
    tpm_path = expand(cfg["toil"]["tpm_gz"], root)
    pheno_path = expand(cfg["toil"]["phenotype_gz"], root)
    if not tpm_path.is_file() or not pheno_path.is_file():
        print(f"Missing TOIL inputs: {tpm_path} / {pheno_path}", file=sys.stderr)
        return 1

    manifest_rows, usecols = collect_samples(cfg, pheno_path)
    if len(usecols) < 3:
        print("No samples selected.", file=sys.stderr)
        return 2

    with gzip.open(tpm_path, "rt", encoding="utf-8", errors="replace") as f:
        hdr = f.readline().strip().split("\t")
    want = set(usecols)
    missing = [c for c in usecols if c not in hdr]
    if missing:
        print(f"Columns missing in TPM matrix (first 5): {missing[:5]}", file=sys.stderr)
        return 3

    print(f"Reading {len(usecols)-1} samples from TOIL TPM …")
    df = pd.read_csv(
        tpm_path,
        sep="\t",
        compression="gzip",
        usecols=usecols,
        low_memory=False,
    )
    df = df.rename(columns={"sample": "gene_id"}).set_index("gene_id")
    df.index.name = "gene_id"

    out_parquet = repo_root() / cfg["output"]["expression_parquet"]
    out_samples = repo_root() / cfg["output"]["sample_table"]
    out_parquet.parent.mkdir(parents=True, exist_ok=True)
    df.astype("float32").to_parquet(out_parquet)
    pd.DataFrame(manifest_rows).to_csv(out_samples, sep="\t", index=False)

    summ = {
        "n_genes": int(df.shape[0]),
        "n_tumor": sum(1 for r in manifest_rows if r["group"] == "tumor"),
        "n_normal": sum(1 for r in manifest_rows if r["group"] == "normal"),
        "tpm_path": str(tpm_path),
    }
    (out_parquet.parent / "toil_extract_summary.json").write_text(
        json.dumps(summ, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {out_parquet} shape={df.shape}")
    print(f"Wrote {out_samples} ({summ['n_tumor']} tumor, {summ['n_normal']} normal)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
