#!/usr/bin/env python3
"""
Export HGNC symbols from DEA tables for STRING-DB / PPI (outline Module 4).

Each job: FDR filter (padj_bh / padj / FDR via resolve_fdr_column), optional outline_m21_high_confidence_screen, optional
min_abs_effect on an effect column (Welch: delta_log2_expression; OLS: beta_tumor_vs_ref_normal),
optional numeric_filters on joined columns (e.g. DepMap: depmap_crispr_median_gbm lte -0.5 —
more negative Chronos-style scores indicate stronger dependency in screened GBM lines).

Config: config/module2_integration.yaml — dea_string_export.jobs (or legacy single-job keys).

Filter implementation: scripts/dea_string_filters.py (shared with export_stratified_dea_string_lists.py).
See docs/DEA_METHODOLOGY.md for hub-scale effect interpretation.
"""

from __future__ import annotations

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
from dea_string_filters import filter_dea, resolve_fdr_column


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


def load_ensg_to_symbol(hgnc_path: Path) -> dict[str, str]:
    df = pd.read_csv(hgnc_path, sep="\t", dtype=str, low_memory=False)
    out: dict[str, str] = {}
    for _, row in df.iterrows():
        eid = str(row.get("ensembl_gene_id", "") or "").strip()
        sym = str(row.get("symbol", "") or "").strip()
        if not eid.startswith("ENSG") or not sym:
            continue
        base = ensg_base(eid)
        if base not in out:
            out[base] = sym
    return out


def legacy_job_from_block(block: dict[str, Any]) -> dict[str, Any] | None:
    p = block.get("welch_dea_tsv") or block.get("dea_tsv")
    if not p:
        return None
    return {
        "job_name": "legacy_welch",
        "dea_tsv": p,
        "output_txt": block.get("output_txt", "results/module3/dea_welch_fdr05_symbols_for_string.txt"),
        "padj_max": block.get("padj_max", 0.05),
        "require_outline_m21_high_confidence_screen": block.get(
            "require_outline_m21_high_confidence_screen", False
        ),
        "min_abs_effect": block.get("min_abs_effect"),
        "effect_column": block.get("effect_column", "delta_log2_expression"),
    }


def collect_jobs(block: dict[str, Any]) -> list[dict[str, Any]]:
    jobs = list(block.get("jobs") or [])
    leg = legacy_job_from_block(block)
    if leg and not jobs:
        jobs = [leg]
    return jobs


def main() -> int:
    rr = repo_root()
    cfg = load_integration_cfg()
    block = cfg.get("dea_string_export") or {}
    hg = str(block.get("hgnc_tsv", "{data_root}/references/hgnc_complete_set.txt")).replace(
        "{data_root}", str(data_root())
    ).replace("/", os.sep)
    hgnc_path = Path(hg)
    jobs = collect_jobs(block)
    if not jobs:
        print("No dea_string_export jobs configured", file=sys.stderr)
        return 1
    if not hgnc_path.is_file():
        print(f"Missing HGNC {hgnc_path}", file=sys.stderr)
        return 2

    ensg_map = load_ensg_to_symbol(hgnc_path)
    summaries: list[dict[str, Any]] = []

    for job in jobs:
        jname = str(job.get("job_name", "unnamed"))
        dea_path = rr / str(job["dea_tsv"])
        out_txt = rr / str(job["output_txt"])
        if not dea_path.is_file():
            print(f"SKIP {jname}: missing {dea_path}", file=sys.stderr)
            summaries.append({"job_name": jname, "status": "skipped", "reason": "missing_dea"})
            continue

        dea = pd.read_csv(dea_path, sep="\t", low_memory=False)
        if "gene_id" not in dea.columns or resolve_fdr_column(dea) is None:
            print(f"SKIP {jname}: bad columns (need gene_id + padj_bh/padj/FDR)", file=sys.stderr)
            summaries.append({"job_name": jname, "status": "skipped", "reason": "bad_columns"})
            continue

        sub = filter_dea(dea, job)
        sig = sub["gene_id"].astype(str)
        symbols: list[str] = []
        skipped = 0
        for gid in sig:
            sym = ensg_map.get(ensg_base(gid))
            if sym:
                symbols.append(sym)
            else:
                skipped += 1
        symbols = sorted(set(symbols))
        out_txt.parent.mkdir(parents=True, exist_ok=True)
        out_txt.write_text("\n".join(symbols) + ("\n" if symbols else ""), encoding="utf-8")
        summaries.append(
            {
                "job_name": jname,
                "status": "ok",
                "n_rows_after_filters": int(len(sub)),
                "n_symbols_exported": len(symbols),
                "n_gene_ids_no_symbol": skipped,
                "output_txt": str(out_txt.relative_to(rr)).replace("\\", "/"),
                "filters": {
                    "padj_max": float(job.get("padj_max", 0.05)),
                    "fdr_column_effective": str(job.get("fdr_column", "") or "").strip()
                    or resolve_fdr_column(dea)
                    or "",
                    "require_outline_m21_high_confidence_screen": bool(
                        job.get("require_outline_m21_high_confidence_screen", False)
                    ),
                    "min_abs_effect": job.get("min_abs_effect"),
                    "effect_column": job.get("effect_column"),
                    "numeric_filters": job.get("numeric_filters"),
                },
            }
        )
        print(f"Wrote {out_txt} ({len(symbols)} symbols) job={jname}")

    prov_path = rr / str(
        block.get("aggregate_provenance_json", "results/module3/dea_string_export_provenance.json")
    )
    prov_path.parent.mkdir(parents=True, exist_ok=True)
    prov_path.write_text(json.dumps({"jobs": summaries}, indent=2), encoding="utf-8")
    print(f"Wrote {prov_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
