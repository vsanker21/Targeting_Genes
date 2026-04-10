#!/usr/bin/env python3
"""
Write holdout sample manifests (sample_id, group) under data_root from staged CGGA / GEO files.

Contrast definitions (locked with preregistration commit):
  CGGA: primary GBM (WHO IV), MGMT promoter methylation methylated vs un-methylated (RNA-seq count table sample IDs).
  GSE4290: glioblastoma grade 4 vs epilepsy surgical controls (GEO series_matrix sample accessions).
  GSE7696: GBM vs non-tumoral (parsed from GEO Sample_title).

Requires GLIOMA_TARGET_DATA_ROOT (or data_sources.yaml data_root).
"""

from __future__ import annotations

import argparse
import gzip
import os
import sys
from pathlib import Path

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


def _find_one(root: Path, pattern: str) -> Path:
    hits = sorted(p for p in root.glob(pattern) if p.is_file())
    if not hits:
        raise FileNotFoundError(f"no match under {root} for {pattern!r}")
    return hits[0]


def _geo_meta_until_table(matrix_gz: Path) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    with gzip.open(matrix_gz, "rt", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.lower().startswith("!series_matrix_table_begin"):
                break
            if line.startswith("!Sample_geo_accession"):
                rows["gsm"] = [p.strip().strip('"') for p in line.split("\t")[1:]]
            elif line.startswith("!Sample_characteristics_ch1"):
                rows["char"] = [p.strip().strip('"') for p in line.split("\t")[1:]]
            elif line.startswith("!Sample_source_name_ch1"):
                rows["src"] = [p.strip().strip('"') for p in line.split("\t")[1:]]
            elif line.startswith("!Sample_title"):
                rows["title"] = [p.strip().strip('"') for p in line.split("\t")[1:]]
    return rows


def build_cgga_manifest(dr: Path) -> pd.DataFrame:
    unpacked = dr / "cohorts" / "cgga_expression" / "unpacked"
    clin = _find_one(unpacked, "**/CGGA.mRNAseq_693_clinical*.txt")
    df = pd.read_csv(clin, sep="\t")
    df["Grade"] = df["Grade"].astype(str)
    df["Histology"] = df["Histology"].astype(str)
    sub = df[(df["Histology"] == "GBM") & (df["Grade"].str.contains("IV", na=False)) & (df["PRS_type"] == "Primary")]
    m = sub["MGMTp_methylation_status"].astype(str)
    b = sub[m.isin(["methylated", "un-methylated"])].copy()
    b["sample_id"] = b["CGGA_ID"].astype(str)
    b["group"] = b["MGMTp_methylation_status"].astype(str)
    out = b[["sample_id", "group"]].drop_duplicates()
    return out


def build_gse4290_manifest(dr: Path) -> pd.DataFrame:
    gz = _find_one(dr, "geo/bulk_microarray/GSE4290/matrix/*series_matrix.txt.gz")
    meta = _geo_meta_until_table(gz)
    rows = []
    for gsm, char, src in zip(meta["gsm"], meta["char"], meta["src"]):
        cl, sl = char.lower(), src.lower()
        if "epilepsy" in sl:
            rows.append((gsm, "control"))
        elif "glioblastoma" in cl and "grade 4" in cl:
            rows.append((gsm, "tumor"))
    return pd.DataFrame(rows, columns=["sample_id", "group"])


def build_gse7696_manifest(dr: Path) -> pd.DataFrame:
    gz = _find_one(dr, "geo/bulk_microarray/GSE7696/matrix/*series_matrix.txt.gz")
    meta = _geo_meta_until_table(gz)
    rows = []
    for gsm, title in zip(meta["gsm"], meta["title"]):
        tl = title.lower()
        if "non-tumoral" in tl or "non-tumor" in tl:
            rows.append((gsm, "control"))
        elif "gbm" in tl:
            rows.append((gsm, "tumor"))
    return pd.DataFrame(rows, columns=["sample_id", "group"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", type=Path, default=None)
    args = ap.parse_args()

    dr = args.data_root or data_root()
    if not dr.is_dir():
        print(f"ERROR: data_root not found: {dr}", file=sys.stderr)
        return 1

    out_dir = dr / "validation" / "external_cohort_sample_meta"
    out_dir.mkdir(parents=True, exist_ok=True)

    specs = [
        ("cgga_gbm_holdout_samples.tsv", build_cgga_manifest, "CGGA RNA-seq 693: primary GBM WHO IV; MGMTp methylated vs un-methylated."),
        ("gse4290_holdout_samples.tsv", build_gse4290_manifest, "GSE4290: glioblastoma grade 4 vs epilepsy brain controls."),
        ("gse7696_holdout_samples.tsv", build_gse7696_manifest, "GSE7696: GBM vs non-tumoral (Sample_title)."),
    ]

    readme_lines = ["# Holdout sample manifests\n", f"data_root: {dr}\n\n"]
    for name, fn, note in specs:
        try:
            m = fn(dr)
        except Exception as e:
            print(f"ERROR building {name}: {e}", file=sys.stderr)
            return 1
        fp = out_dir / name
        m.to_csv(fp, sep="\t", index=False)
        print(f"Wrote {fp} ({len(m)} rows)")
        readme_lines.append(f"## {name}\n{note}\n\n")

    (out_dir / "README_holdout_manifests.txt").write_text("".join(readme_lines), encoding="utf-8")
    print(f"Wrote {out_dir / 'README_holdout_manifests.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
