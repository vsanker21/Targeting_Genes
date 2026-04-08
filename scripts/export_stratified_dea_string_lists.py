#!/usr/bin/env python3
"""
Per-subtype HGNC symbol lists from integrated stratified DEA tables (outline Module 2.3 / 4).

For each config job, globs Welch or OLS integrated TSVs and applies the same filters as
dea_string_export (see scripts/dea_string_filters.py).

Config: config/module2_integration.yaml — stratified_string_export
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from dea_string_filters import filter_dea

import export_dea_string_gene_list as ese


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def filter_dict_from_job(jdef: dict[str, Any], path_stem: str, tag: str) -> dict[str, Any]:
    return {
        "job_name": f"{tag}:{path_stem}",
        "padj_max": float(jdef.get("padj_max", 0.05)),
        "require_outline_m21_high_confidence_screen": bool(
            jdef.get("require_outline_m21_high_confidence_screen", False)
        ),
        "effect_column": jdef.get("effect_column"),
        "min_abs_effect": jdef.get("min_abs_effect"),
        "numeric_filters": jdef.get("numeric_filters"),
    }


def main() -> int:
    rr = repo_root()
    cfg = ese.load_integration_cfg()
    block = cfg.get("stratified_string_export") or {}
    if not block.get("enabled", True):
        print("stratified_string_export disabled")
        return 0

    hg = str(block.get("hgnc_tsv", "{data_root}/references/hgnc_complete_set.txt")).replace(
        "{data_root}", str(ese.data_root())
    ).replace("/", os.sep)
    hgnc_path = Path(hg)
    if not hgnc_path.is_file():
        print(f"Missing HGNC {hgnc_path}", file=sys.stderr)
        return 2

    out_root = rr / str(block.get("output_root", "results/module4/stratified_string"))
    jobs = list(block.get("jobs") or [])
    if not jobs:
        print("No stratified_string_export.jobs configured", file=sys.stderr)
        return 1

    ensg_map = ese.load_ensg_to_symbol(hgnc_path)
    summaries: list[dict[str, Any]] = []

    for jdef in jobs:
        tag = str(jdef.get("job_tag", "job")).strip() or "job"
        glob_pat = str(jdef.get("glob_input", "")).strip()
        suf = str(jdef.get("output_filename_suffix", "_string_m21_high_confidence.txt"))
        if not glob_pat:
            print(f"SKIP job_tag={tag}: empty glob_input", file=sys.stderr)
            continue

        subdir = out_root / tag
        matched = sorted(rr.glob(glob_pat))
        for path in matched:
            if not path.is_file() or "summary" in path.name.lower():
                continue
            if "_outline_drivers" in path.name:
                continue
            fj = filter_dict_from_job(jdef, path.stem, tag)
            dea = pd.read_csv(path, sep="\t", low_memory=False)
            if "padj_bh" not in dea.columns or "gene_id" not in dea.columns:
                summaries.append(
                    {
                        "job_tag": tag,
                        "input_tsv": str(path.relative_to(rr)).replace("\\", "/"),
                        "status": "skipped",
                        "reason": "bad_columns",
                    }
                )
                continue

            sub = filter_dea(dea, fj)
            symbols: list[str] = []
            skipped = 0
            for gid in sub["gene_id"].astype(str):
                sym = ensg_map.get(ese.ensg_base(gid))
                if sym:
                    symbols.append(sym)
                else:
                    skipped += 1
            symbols = sorted(set(symbols))
            out_txt = subdir / f"{path.stem}{suf}"
            out_txt.parent.mkdir(parents=True, exist_ok=True)
            out_txt.write_text("\n".join(symbols) + ("\n" if symbols else ""), encoding="utf-8")
            summaries.append(
                {
                    "job_tag": tag,
                    "input_tsv": str(path.relative_to(rr)).replace("\\", "/"),
                    "status": "ok",
                    "output_txt": str(out_txt.relative_to(rr)).replace("\\", "/"),
                    "n_rows_after_filters": int(len(sub)),
                    "n_symbols_exported": len(symbols),
                    "n_gene_ids_no_symbol": skipped,
                    "filters": {k: v for k, v in fj.items() if k != "job_name"},
                }
            )
            print(f"Wrote {out_txt} ({len(symbols)} symbols) {tag}/{path.name}")

    prov_path = rr / str(
        block.get(
            "aggregate_provenance_json",
            "results/module4/stratified_string_export_provenance.json",
        )
    )
    prov_path.parent.mkdir(parents=True, exist_ok=True)
    prov_path.write_text(json.dumps({"jobs": summaries}, indent=2), encoding="utf-8")
    print(f"Wrote {prov_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
