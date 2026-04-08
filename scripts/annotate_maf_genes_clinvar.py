#!/usr/bin/env python3
"""
M2.2: Join TCGA MAF cohort gene summary (Ensembl gene_id) to ClinVar gene_specific_summary.txt by HGNC symbol.
Downloads ClinVar TSV to data_root if missing. No OncoKB / MutSig / VEP variant-level calls.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
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
    return Path(cfg["data_root"].replace("/", os.sep))


def ensg_base(gene_id: str) -> str:
    s = str(gene_id).strip()
    if "." in s and s.startswith("ENSG"):
        return s.split(".", 1)[0]
    return s


def load_hgnc_ensg_to_symbol(hgnc_path: Path) -> dict[str, str]:
    df = pd.read_csv(hgnc_path, sep="\t", dtype=str, low_memory=False)
    out: dict[str, str] = {}
    for _, row in df.iterrows():
        eid = str(row.get("ensembl_gene_id", "") or "").strip()
        sym = str(row.get("symbol", "") or "").strip()
        if eid and sym:
            out[ensg_base(eid)] = sym
    return out


def ensure_clinvar_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        head = dest.read_text(encoding="utf-8", errors="replace")[:4000]
        if "Symbol" in head and "\t" in head:
            return
    print(f"Downloading ClinVar gene summary → {dest}")
    urllib.request.urlretrieve(url, dest)  # noqa: S310 — fixed NCBI HTTPS URL from config


def read_clinvar_gene_specific_summary(path: Path) -> pd.DataFrame:
    """Parse NCBI gene_specific_summary.txt (comment lines, header line starts with #Symbol)."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    header: list[str] | None = None
    start = 0
    for i, line in enumerate(lines):
        if line.startswith("#") and "\t" in line:
            rest = line[1:].strip()
            if rest.startswith("Symbol\t"):
                header = rest.split("\t")
                start = i + 1
                break
    if not header:
        raise ValueError(f"Could not find #Symbol header in {path}")
    body = "\n".join(lines[start:])
    from io import StringIO

    df = pd.read_csv(StringIO(body), sep="\t", names=header, low_memory=False)
    df["Symbol"] = df["Symbol"].astype(str).str.strip()
    return df


def load_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "m2_2_clinvar_gene_annotation.yaml"
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    dr = data_root()
    hg = str(raw["hgnc_tsv"]).replace("{data_root}", str(dr)).replace("/", os.sep)
    raw = dict(raw)
    raw["hgnc_tsv"] = Path(hg)
    cache_rel = str(raw["clinvar"]["cache_relative"])
    raw["clinvar_local"] = dr / cache_rel.replace("/", os.sep)
    return raw


def main() -> int:
    rr = repo_root()
    cfg = load_cfg()
    out_tsv = rr / cfg["output_tsv"]
    prov_path = rr / cfg["provenance_json"]
    out_tsv.parent.mkdir(parents=True, exist_ok=True)

    maf_path = rr / cfg["maf_gene_summary_tsv"]
    if not maf_path.is_file():
        print(f"Missing MAF gene summary: {maf_path}", file=sys.stderr)
        return 2

    maf = pd.read_csv(maf_path, sep="\t", dtype=str, low_memory=False)
    if maf.empty or "gene_id" not in maf.columns:
        prov = {
            "status": "skipped",
            "reason": "empty MAF gene summary or missing gene_id column",
            "maf_rows": int(len(maf)),
        }
        empty = maf.copy()
        prov_path.write_text(json.dumps(prov, indent=2), encoding="utf-8")
        empty.to_csv(out_tsv, sep="\t", index=False)
        print(f"Wrote empty join {out_tsv} (no MAF genes)")
        return 0

    hgnc_path = cfg["hgnc_tsv"]
    if not hgnc_path.is_file():
        print(f"Missing HGNC: {hgnc_path}", file=sys.stderr)
        return 2

    url = str(cfg["clinvar"]["tab_delimited_url"])
    clinvar_path = cfg["clinvar_local"]
    try:
        ensure_clinvar_file(url, clinvar_path)
    except Exception as e:
        print(f"ClinVar download failed: {e}", file=sys.stderr)
        return 3

    ensg_to_sym = load_hgnc_ensg_to_symbol(hgnc_path)
    maf["gene_id_base"] = maf["gene_id"].map(ensg_base)
    maf["gene_symbol"] = maf["gene_id_base"].map(lambda x: ensg_to_sym.get(x, ""))

    cv = read_clinvar_gene_specific_summary(clinvar_path)
    cv = cv.drop_duplicates(subset=["Symbol"], keep="first")
    # One row per symbol in ClinVar file; merge left
    merged = maf.merge(cv, left_on="gene_symbol", right_on="Symbol", how="left", suffixes=("", "_clinvar"))
    merged.drop(columns=["Symbol"], errors="ignore", inplace=True)
    merged.to_csv(out_tsv, sep="\t", index=False)

    n_with_sym = int((maf["gene_symbol"] != "").sum())
    n_clinvar_hit = int(merged["GeneID"].notna().sum()) if "GeneID" in merged.columns else 0
    prov = {
        "status": "ok",
        "clinvar_url": url,
        "clinvar_local": str(clinvar_path),
        "maf_genes": int(len(maf)),
        "genes_with_hgnc_symbol": n_with_sym,
        "rows_with_clinvar_gene_row": n_clinvar_hit,
        "output_tsv": str(out_tsv),
    }
    prov_path.write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(f"Wrote {out_tsv} ({len(merged)} rows, {n_clinvar_hit} with ClinVar gene summary match)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
