#!/usr/bin/env python3
"""
Add boolean outline_m22_known_gbm_driver to DEA TSVs by Ensembl gene_id (via HGNC approved symbol).

Gene list: references/gbm_known_drivers_outline.yaml (from project outline Module 2.2 text).
This is a literature/outline reference flag, not somatic mutation status per sample.

Config: config/module2_integration.yaml — outline_driver_flags
"""

from __future__ import annotations

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
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def ensg_base(gene_id: str) -> str:
    s = str(gene_id).strip()
    if "." in s and s.startswith("ENSG"):
        return s.split(".", 1)[0]
    return s


def load_integration_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module2_integration.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def load_driver_ensg(symbols_yaml: Path, hgnc_path: Path) -> set[str]:
    raw = yaml.safe_load(symbols_yaml.read_text(encoding="utf-8"))
    want = {str(x).strip().upper() for x in (raw.get("gene_symbols") or []) if str(x).strip()}
    hg = pd.read_csv(hgnc_path, sep="\t", dtype=str, low_memory=False)
    out: set[str] = set()
    for _, row in hg.iterrows():
        sym = str(row.get("symbol", "") or "").strip().upper()
        eid = str(row.get("ensembl_gene_id", "") or "").strip()
        if sym in want and eid.startswith("ENSG"):
            out.add(ensg_base(eid))
    return out


def join_one(dea_path: Path, out_path: Path, driver_ensg: set[str], col: str) -> None:
    dea = pd.read_csv(dea_path, sep="\t", low_memory=False)
    e = dea["gene_id"].map(ensg_base)
    dea[col] = e.isin(driver_ensg)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dea.to_csv(out_path, sep="\t", index=False)
    n = int(dea[col].sum())
    print(f"Wrote {out_path} ({n} genes flagged as outline drivers)")


def main() -> int:
    rr = repo_root()
    cfg = load_integration_cfg()
    block = cfg.get("outline_driver_flags") or {}
    if not block.get("enabled", True):
        print("outline_driver_flags disabled")
        return 0

    sym_yml = rr / str(block.get("symbols_yaml", "references/gbm_known_drivers_outline.yaml"))
    hg_rel = str(block.get("hgnc_tsv", "{data_root}/references/hgnc_complete_set.txt"))
    hgnc_path = Path(hg_rel.replace("{data_root}", str(data_root())).replace("/", os.sep))
    col = str(block.get("gene_flag_column", "outline_m22_known_gbm_driver"))

    if not sym_yml.is_file():
        print(f"Missing {sym_yml}", file=sys.stderr)
        return 1
    if not hgnc_path.is_file():
        print(f"Missing HGNC {hgnc_path}", file=sys.stderr)
        return 2

    driver_ensg = load_driver_ensg(sym_yml, hgnc_path)
    if not driver_ensg:
        print("No driver Ensembl IDs resolved from HGNC", file=sys.stderr)
        return 3

    targets = block.get("targets") or []
    for t in targets:
        inp = rr / str(t["input"])
        outp = rr / str(t["output"])
        if not inp.is_file():
            print(f"SKIP missing {inp}", file=sys.stderr)
            continue
        join_one(inp, outp, driver_ensg, col)

    for pat in block.get("glob_targets") or []:
        glob_pat = str(pat).strip()
        if not glob_pat:
            continue
        for inp in sorted(rr.glob(glob_pat)):
            if not inp.is_file() or "summary" in inp.name.lower():
                continue
            # Avoid re-processing outputs from a previous run (prevents *_outline_drivers_outline_drivers*.tsv chains).
            if "_outline_drivers" in inp.stem:
                continue
            outp = inp.with_name(f"{inp.stem}_outline_drivers.tsv")
            join_one(inp, outp, driver_ensg, col)

    if block.get("glob_targets"):
        flag_rel = block.get(
            "stratified_integrated_drivers_flag",
            "results/module3/stratified_integrated_outline_drivers.flag",
        )
        flag_p = rr / str(flag_rel)
        flag_p.parent.mkdir(parents=True, exist_ok=True)
        flag_p.write_text("ok\n", encoding="utf-8")
        print(f"Wrote {flag_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
