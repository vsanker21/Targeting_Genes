#!/usr/bin/env python3
"""
GSEA-style preranked gene lists (two columns: HGNC symbol, ranking metric).

Metric per row: sign(effect) * (-log10(max(pvalue, pvalue_floor))).
Global Welch/OLS DEA plus optional integrated stratified DEA globs (outline Module 2.3 / 4/5).

Config: config/module2_integration.yaml — gsea_prerank_export
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
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


def build_ranked_symbol_df(
    dea: pd.DataFrame,
    eff_col: str,
    p_col: str,
    p_floor: float,
    ensg_map: dict[str, str],
) -> tuple[pd.DataFrame | None, int, str | None]:
    """
    Returns (out_df, n_no_symbol, error_reason).
    error_reason set when returning None.
    """
    for col in ("gene_id", eff_col, p_col):
        if col not in dea.columns:
            return None, 0, f"missing_{col}"

    eff = pd.to_numeric(dea[eff_col], errors="coerce")
    pv = pd.to_numeric(dea[p_col], errors="coerce")
    pv = pv.clip(lower=p_floor, upper=1.0)
    with np.errstate(divide="ignore"):
        neglog = -np.log10(pv.to_numpy(dtype=np.float64))
    sgn = np.sign(eff.to_numpy(dtype=np.float64))
    rank = sgn * neglog

    rows: list[tuple[str, float]] = []
    n_no_sym = 0
    for i, gid in enumerate(dea["gene_id"].astype(str)):
        sym = ensg_map.get(ensg_base(gid))
        r = rank[i]
        if not sym or not np.isfinite(r):
            if not sym:
                n_no_sym += 1
            continue
        rows.append((sym, float(r)))

    out_df = pd.DataFrame(rows, columns=["symbol", "rank_metric"])
    out_df = out_df.sort_values("rank_metric", ascending=False, kind="mergesort")
    out_df = out_df.drop_duplicates(subset=["symbol"], keep="first")
    return out_df, n_no_sym, None


def main() -> int:
    rr = repo_root()
    block = (load_integration_cfg().get("gsea_prerank_export") or {})
    if not block.get("enabled", True):
        print("gsea_prerank_export disabled")
        return 0

    hg = str(block.get("hgnc_tsv", "{data_root}/references/hgnc_complete_set.txt")).replace(
        "{data_root}", str(data_root())
    ).replace("/", os.sep)
    hgnc_path = Path(hg)
    p_floor = float(block.get("pvalue_floor", 1e-300))
    jobs = list(block.get("jobs") or [])
    sglobs = list(block.get("stratified_glob_jobs") or [])

    if not jobs and not sglobs:
        print("No gsea_prerank_export.jobs or stratified_glob_jobs configured", file=sys.stderr)
        return 1
    if not hgnc_path.is_file():
        print(f"Missing HGNC {hgnc_path}", file=sys.stderr)
        return 2

    ensg_map = load_ensg_to_symbol(hgnc_path)
    global_summaries: list[dict[str, Any]] = []
    strat_summaries: list[dict[str, Any]] = []

    for job in jobs:
        jname = str(job.get("job_name", "unnamed"))
        dea_path = rr / str(job["dea_tsv"])
        out_rnk = rr / str(job["output_rnk"])
        eff_col = str(job.get("effect_column", "delta_log2_expression"))
        p_col = str(job.get("pvalue_column", "pvalue"))

        if not dea_path.is_file():
            print(f"SKIP {jname}: missing {dea_path}", file=sys.stderr)
            global_summaries.append({"job_name": jname, "status": "skipped", "reason": "missing_dea"})
            continue

        dea = pd.read_csv(dea_path, sep="\t", low_memory=False)
        out_df, n_no_sym, err = build_ranked_symbol_df(dea, eff_col, p_col, p_floor, ensg_map)
        if err:
            print(f"SKIP {jname}: {err}", file=sys.stderr)
            global_summaries.append({"job_name": jname, "status": "skipped", "reason": err})
            continue

        out_rnk.parent.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(out_rnk, sep="\t", header=False, index=False)
        global_summaries.append(
            {
                "job_name": jname,
                "status": "ok",
                "n_genes_in_dea": int(len(dea)),
                "n_rows_written": int(len(out_df)),
                "n_gene_ids_no_symbol": n_no_sym,
                "output_rnk": str(out_rnk.relative_to(rr)).replace("\\", "/"),
                "effect_column": eff_col,
                "pvalue_column": p_col,
                "pvalue_floor": p_floor,
            }
        )
        print(f"Wrote {out_rnk} rows={len(out_df)} job={jname}")

    gsea_base = rr / "results/module4/gsea"
    suf = str(block.get("stratified_output_filename_suffix", "_signed_neg_log10_p.rnk"))

    for sjob in sglobs:
        tag = str(sjob.get("job_tag", "stratified")).strip() or "stratified"
        glob_pat = str(sjob.get("glob_input", "")).strip()
        eff_col = str(sjob.get("effect_column", "delta_log2_expression"))
        p_col = str(sjob.get("pvalue_column", "pvalue"))
        if not glob_pat:
            print(f"SKIP stratified job_tag={tag}: empty glob_input", file=sys.stderr)
            continue

        subdir = gsea_base / "stratified" / tag
        for path in sorted(rr.glob(glob_pat)):
            if not path.is_file() or "summary" in path.name.lower():
                continue
            if "_outline_drivers" in path.name:
                continue

            key = f"{tag}:{path.stem}"
            dea = pd.read_csv(path, sep="\t", low_memory=False)
            out_df, n_no_sym, err = build_ranked_symbol_df(dea, eff_col, p_col, p_floor, ensg_map)
            if err:
                print(f"SKIP {key}: {err}", file=sys.stderr)
                strat_summaries.append(
                    {
                        "job_tag": tag,
                        "input_tsv": str(path.relative_to(rr)).replace("\\", "/"),
                        "status": "skipped",
                        "reason": err,
                    }
                )
                continue

            out_rnk = subdir / f"{path.stem}{suf}"
            out_rnk.parent.mkdir(parents=True, exist_ok=True)
            out_df.to_csv(out_rnk, sep="\t", header=False, index=False)
            strat_summaries.append(
                {
                    "job_tag": tag,
                    "input_tsv": str(path.relative_to(rr)).replace("\\", "/"),
                    "status": "ok",
                    "n_genes_in_dea": int(len(dea)),
                    "n_rows_written": int(len(out_df)),
                    "n_gene_ids_no_symbol": n_no_sym,
                    "output_rnk": str(out_rnk.relative_to(rr)).replace("\\", "/"),
                    "effect_column": eff_col,
                    "pvalue_column": p_col,
                    "pvalue_floor": p_floor,
                }
            )
            print(f"Wrote {out_rnk} rows={len(out_df)} stratified {key}")

    prov_path = rr / str(
        block.get("aggregate_provenance_json", "results/module4/gsea_prerank_export_provenance.json")
    )
    prov_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "jobs": global_summaries,
        "stratified_jobs": strat_summaries,
    }
    prov_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {prov_path}")

    flag_path = rr / str(block.get("stratified_prerank_flag", "results/module4/gsea_stratified_prerank.flag"))
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    flag_path.write_text("ok\n" if sglobs else "no_stratified_glob_jobs\n", encoding="utf-8")
    print(f"Wrote {flag_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
