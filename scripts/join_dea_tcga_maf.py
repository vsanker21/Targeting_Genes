#!/usr/bin/env python3
"""
Join tcga_maf_gene_cohort_summary.py output to Welch + OLS DEA tables.

See config/tcga_mutation_layer.yaml.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

def ensg_base(gene_id: str) -> str:
    s = str(gene_id).strip()
    if "." in s and s.startswith("ENSG"):
        return s.split(".", 1)[0]
    return s


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
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def collect_maf_pairs(cfg: dict[str, Any], rr: Path) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = [
        (rr / str(cfg["dea_ols_tsv"]), rr / str(cfg["output_ols"])),
        (rr / str(cfg["dea_welch_tsv"]), rr / str(cfg["output_welch"])),
    ]
    for pair in cfg.get("extra_dea_pairs") or []:
        if not isinstance(pair, dict):
            continue
        inp = pair.get("input") or pair.get("dea_tsv")
        outp = pair.get("output")
        if inp and outp:
            pairs.append((rr / str(inp), rr / str(outp)))
    return pairs


def join_one(dea_path: Path, out_path: Path, summary: pd.DataFrame) -> None:
    dea = pd.read_csv(dea_path, sep="\t")
    dea["_ensg"] = dea["gene_id"].map(ensg_base)
    if summary.empty:
        dea["tcga_maf_n_samples_mutated"] = 0
        dea["tcga_maf_n_mutation_records"] = 0
    else:
        sm = summary.set_index("gene_id")
        hit = sm.reindex(dea["_ensg"])
        dea["tcga_maf_n_samples_mutated"] = hit["n_tcga_samples_mutated"].fillna(0).astype(int).to_numpy()
        dea["tcga_maf_n_mutation_records"] = hit["n_mutation_records"].fillna(0).astype(int).to_numpy()
    dea = dea.drop(columns=["_ensg"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dea.to_csv(out_path, sep="\t", index=False)
    print(f"Wrote {out_path}")


def main() -> int:
    rr = repo_root()
    cfg = load_cfg()
    summ_path = rr / cfg["gene_summary_tsv"]
    summary = pd.read_csv(summ_path, sep="\t") if summ_path.is_file() else pd.DataFrame()

    pairs = collect_maf_pairs(cfg, rr)
    for inp, outp in pairs:
        if not inp.is_file():
            print(f"Missing DEA input {inp}", file=sys.stderr)
            continue
        join_one(inp, outp, summary)

    prov = rr / "results" / "module3" / "tcga_maf_join_provenance.json"
    prov.parent.mkdir(parents=True, exist_ok=True)
    prov.write_text(
        json.dumps(
            {
                "gene_summary_tsv": str(summ_path),
                "summary_rows": len(summary),
                "data_root": str(data_root()),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
