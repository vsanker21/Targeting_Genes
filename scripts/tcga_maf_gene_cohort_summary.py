#!/usr/bin/env python3
"""
Aggregate TCGA-style MAF files to cohort gene-level counts (Hugo → Ensembl via HGNC).
Used for outline §2.2 alongside DepMap; MutSig2CV remains external.

Config: config/tcga_mutation_layer.yaml — maf_glob empty → skip with empty summary + provenance.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from glob import glob
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


def load_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "tcga_mutation_layer.yaml"
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    hg = str(raw.get("hgnc_tsv", "")).replace("{data_root}", str(data_root())).replace("/", os.sep)
    raw = dict(raw)
    raw["hgnc_tsv"] = Path(hg)
    return raw


def ensg_base(gene_id: str) -> str:
    s = str(gene_id).strip()
    if "." in s and s.startswith("ENSG"):
        return s.split(".", 1)[0]
    return s


def load_hgnc_symbol_to_ensg(hgnc_path: Path) -> dict[str, str]:
    df = pd.read_csv(hgnc_path, sep="\t", dtype=str, low_memory=False)
    out: dict[str, str] = {}
    for _, row in df.iterrows():
        sym = str(row.get("symbol", "") or "").strip().upper()
        eid = str(row.get("ensembl_gene_id", "") or "").strip()
        if sym and eid:
            out[sym] = ensg_base(eid)
    return out


def resolve_maf_files(glob_pat: str, dr: Path) -> list[Path]:
    pat = (glob_pat or "").strip()
    if not pat:
        return []
    p = Path(pat)
    if not p.is_absolute():
        p = dr / pat
    paths = sorted({Path(x) for x in glob(str(p))})
    return [x for x in paths if x.is_file()]


def main() -> int:
    rr = repo_root()
    cfg = load_cfg()
    out_tsv = rr / cfg["gene_summary_tsv"]
    prov_path = rr / cfg["provenance_json"]
    out_tsv.parent.mkdir(parents=True, exist_ok=True)

    maf_files = resolve_maf_files(str(cfg.get("maf_glob", "")), data_root())
    allowed = {str(x).strip() for x in (cfg.get("variant_classifications") or [])}

    if not maf_files:
        empty = pd.DataFrame(
            columns=["gene_id", "n_tcga_samples_mutated", "n_mutation_records"],
        )
        empty.to_csv(out_tsv, sep="\t", index=False)
        prov_path.write_text(
            json.dumps(
                {
                    "status": "skipped",
                    "reason": "maf_glob empty or no matching MAF files",
                    "maf_glob": cfg.get("maf_glob", ""),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"No MAF inputs; wrote empty {out_tsv}")
        return 0

    hgnc_path = cfg["hgnc_tsv"]
    if not hgnc_path.is_file():
        print(f"Missing HGNC: {hgnc_path}", file=sys.stderr)
        return 2
    sym_to_ensg = load_hgnc_symbol_to_ensg(hgnc_path)

    sample_hits: dict[str, set[str]] = defaultdict(set)
    mut_count: dict[str, int] = defaultdict(int)
    n_rows_used = 0

    usecols_try = ["Hugo_Symbol", "Tumor_Sample_Barcode", "Variant_Classification"]

    for mf in maf_files:
        try:
            head = pd.read_csv(mf, sep="\t", nrows=0, low_memory=False, comment="#")
        except Exception as e:
            print(f"Skip unreadable {mf}: {e}", file=sys.stderr)
            continue
        cols = [c for c in usecols_try if c in head.columns]
        if len(cols) < 3:
            print(
                f"Skip {mf}: need columns {usecols_try}, got {head.columns.tolist()[:12]}",
                file=sys.stderr,
            )
            continue
        reader = pd.read_csv(
            mf,
            sep="\t",
            usecols=cols,
            dtype=str,
            low_memory=False,
            comment="#",
            chunksize=100_000,
        )
        for chunk in reader:
            vc = chunk["Variant_Classification"].fillna("").astype(str).str.strip()
            mask = vc.isin(allowed)
            if not mask.any():
                continue
            sub = chunk.loc[mask]
            for _, row in sub.iterrows():
                sym = str(row["Hugo_Symbol"] or "").strip().upper()
                if not sym or sym == "UNKNOWN":
                    continue
                eid = sym_to_ensg.get(sym)
                if not eid:
                    continue
                bar = str(row["Tumor_Sample_Barcode"] or "").strip()
                if not bar:
                    continue
                sample_hits[eid].add(bar)
                mut_count[eid] += 1
                n_rows_used += 1

    rows = []
    for eid in sorted(set(sample_hits) | set(mut_count)):
        rows.append(
            {
                "gene_id": eid,
                "n_tcga_samples_mutated": len(sample_hits.get(eid, ())),
                "n_mutation_records": mut_count.get(eid, 0),
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(out_tsv, sep="\t", index=False)

    prov = {
        "status": "ok",
        "maf_files": [str(p) for p in maf_files],
        "n_variant_rows_used": n_rows_used,
        "n_genes": len(out),
        "variant_classifications": sorted(allowed),
    }
    prov_path.write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(f"Wrote {out_tsv} ({len(out)} genes) from {len(maf_files)} MAF file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
