#!/usr/bin/env python3
"""
Module 5 (outline): Entrez-level disease signature from bulk DEA for LINCS / cmapPy workflows.

Writes tab-separated tables (with header) suitable as input to connectivity or sRGES-style
pipelines that expect Entrez IDs. Metric matches GSEA prerank convention:
  sign(effect) * (-log10(max(pvalue, p_floor))).

Does not run cmapPy or query CLUE; see module5_data_paths_status for local tool data.
Integrated stratified tables are written under results/module5/lincs_disease_signature/stratified/.

Config: config/module5_inputs.yaml — lincs_disease_signature
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


def load_m5_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module5_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def resolve_template(s: str, dr: Path) -> str:
    return str(s).replace("{data_root}", str(dr)).replace("/", os.sep)


def load_ensg_to_entrez(hgnc_path: Path, wanted_ensg: set[str]) -> dict[str, int]:
    hg = pd.read_csv(hgnc_path, sep="\t", dtype=str, low_memory=False)
    if "ensembl_gene_id" not in hg.columns or "entrez_id" not in hg.columns:
        raise ValueError(f"HGNC missing ensembl_gene_id or entrez_id: {hgnc_path}")
    out: dict[str, int] = {}
    for _, row in hg.iterrows():
        eid = str(row.get("ensembl_gene_id", "") or "").strip()
        ez = str(row.get("entrez_id", "") or "").strip()
        if not eid or not ez or not ez.isdigit():
            continue
        base = ensg_base(eid)
        if base in wanted_ensg:
            out[base] = int(ez)
    return out


def build_entrez_signature(
    dea_path: Path,
    effect_col: str,
    p_col: str,
    p_floor: float,
    hgnc_path: Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    dea = pd.read_csv(dea_path, sep="\t", low_memory=False)
    for col in ("gene_id", effect_col, p_col):
        if col not in dea.columns:
            raise ValueError(f"{dea_path}: missing column {col!r}")

    wanted = {ensg_base(str(g)) for g in dea["gene_id"].astype(str)}
    ensg_ez = load_ensg_to_entrez(hgnc_path, wanted)

    eff = pd.to_numeric(dea[effect_col], errors="coerce")
    pv = pd.to_numeric(dea[p_col], errors="coerce").clip(lower=p_floor, upper=1.0)
    with np.errstate(divide="ignore"):
        neglog = -np.log10(pv.to_numpy(dtype=np.float64))
    sgn = np.sign(eff.to_numpy(dtype=np.float64))
    metric = sgn * neglog

    rows: list[tuple[int, float]] = []
    n_no_entrez = 0
    for i, gid in enumerate(dea["gene_id"].astype(str)):
        base = ensg_base(gid)
        ez = ensg_ez.get(base)
        m = metric[i]
        if ez is None:
            n_no_entrez += 1
            continue
        if not np.isfinite(m):
            continue
        rows.append((ez, float(m)))

    if not rows:
        raise RuntimeError(f"{dea_path}: no Entrez-mapped rows with finite metric")

    sig = pd.DataFrame(rows, columns=["entrez_id", "signed_neglog10_p"])
    n_before = len(sig)
    sig["_abs_m"] = sig["signed_neglog10_p"].abs()
    sig = sig.sort_values("_abs_m", ascending=False).drop_duplicates("entrez_id", keep="first")
    sig = sig.drop(columns=["_abs_m"]).sort_values("entrez_id")

    meta = {
        "input": str(dea_path.as_posix()),
        "n_dea_rows": int(len(dea)),
        "n_with_entrez": int(n_before),
        "n_entrez_unique": int(len(sig)),
        "n_skipped_no_entrez": int(n_no_entrez),
        "n_collapsed_duplicate_entrez": int(n_before - len(sig)),
        "effect_col": effect_col,
        "p_col": p_col,
        "p_floor": float(p_floor),
    }
    return sig, meta


def rel_to_repo(rr: Path, p: Path) -> str:
    try:
        return p.resolve().relative_to(rr.resolve()).as_posix()
    except ValueError:
        return str(p.as_posix())


def main() -> int:
    rr = repo_root()
    dr = data_root()
    cfg = load_m5_cfg()
    block = cfg.get("lincs_disease_signature") or {}
    if not block.get("enabled", True):
        print("lincs_disease_signature disabled in module5_inputs.yaml")
        return 0

    hgnc_rel = block.get("hgnc_tsv", "{data_root}/references/hgnc_complete_set.txt")
    hgnc_path = Path(resolve_template(hgnc_rel, dr))
    if not hgnc_path.is_file():
        print(f"Missing HGNC: {hgnc_path}", file=sys.stderr)
        return 1

    p_floor = float(block.get("pvalue_floor", 1e-300))
    jobs = list(block.get("jobs") or [])
    sglobs = list(block.get("stratified_glob_jobs") or [])
    if not jobs and not sglobs:
        print("lincs_disease_signature: need jobs and/or stratified_glob_jobs", file=sys.stderr)
        return 1

    summaries: list[dict[str, Any]] = []
    for job in jobs:
        tag = str(job.get("tag", "")).strip()
        dea_rel = str(job.get("dea_tsv", "")).strip()
        eff_col = str(job.get("effect_col", "")).strip()
        p_col = str(job.get("p_col", "pvalue")).strip()
        out_rel = str(job.get("output_tsv", "")).strip()
        if not tag or not dea_rel or not eff_col or not out_rel:
            print(f"skip incomplete job: {job}", file=sys.stderr)
            continue
        dea_path = rr / dea_rel.replace("/", os.sep)
        if not dea_path.is_file():
            print(f"Missing DEA input {dea_path}", file=sys.stderr)
            return 1
        sig, meta = build_entrez_signature(dea_path, eff_col, p_col, p_floor, hgnc_path)
        out_path = rr / out_rel.replace("/", os.sep)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sig.to_csv(out_path, sep="\t", index=False)
        print(f"Wrote {out_path} rows={len(sig)} tag={tag}")
        summaries.append(
            {
                "tag": tag,
                "output": rel_to_repo(rr, out_path),
                **{**meta, "input": rel_to_repo(rr, dea_path)},
            }
        )

    strat_summaries: list[dict[str, Any]] = []
    sig_base = rr / "results/module5/lincs_disease_signature" / "stratified"
    suf = str(block.get("stratified_output_suffix", "_entrez.tsv"))

    for sjob in sglobs:
        tag = str(sjob.get("job_tag", "stratified")).strip() or "stratified"
        glob_pat = str(sjob.get("glob_input", "")).strip()
        eff_col = str(sjob.get("effect_col", "delta_log2_expression"))
        p_col = str(sjob.get("p_col", "pvalue"))
        if not glob_pat:
            print(f"SKIP stratified job_tag={tag}: empty glob_input", file=sys.stderr)
            continue
        subdir = sig_base / tag
        for path in sorted(rr.glob(glob_pat)):
            if not path.is_file() or "summary" in path.name.lower():
                continue
            if "_outline_drivers" in path.name:
                continue
            key = f"{tag}:{path.stem}"
            try:
                sig, meta = build_entrez_signature(path, eff_col, p_col, p_floor, hgnc_path)
            except (RuntimeError, ValueError) as e:
                print(f"SKIP {key}: {e}", file=sys.stderr)
                strat_summaries.append(
                    {
                        "job_tag": tag,
                        "input": rel_to_repo(rr, path),
                        "status": "skipped",
                        "reason": str(e),
                    }
                )
                continue
            out_name = f"{path.stem}{suf}" if suf.startswith("_") else f"{path.stem}_{suf}"
            out_path = subdir / out_name
            out_path.parent.mkdir(parents=True, exist_ok=True)
            sig.to_csv(out_path, sep="\t", index=False)
            print(f"Wrote {out_path} rows={len(sig)} stratified {key}")
            strat_summaries.append(
                {
                    "job_tag": tag,
                    "input": rel_to_repo(rr, path),
                    "status": "ok",
                    "output": rel_to_repo(rr, out_path),
                    "n_dea_rows": meta["n_dea_rows"],
                    "n_entrez_unique": meta["n_entrez_unique"],
                    "n_skipped_no_entrez": meta["n_skipped_no_entrez"],
                    "effect_col": eff_col,
                    "p_col": p_col,
                    "p_floor": p_floor,
                }
            )

    prov_path = rr / str(block.get("provenance_json", "results/module5/lincs_disease_signature_provenance.json")).replace(
        "/", os.sep
    )
    prov_path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "outline_module": 5,
        "metric": "sign(effect) * (-log10(max(p_col, pvalue_floor)))",
        "note": "Entrez-level signature for LINCS/cmapPy-style connectivity; not sRGES scores. Stratified tables share DEA non-independence caveats.",
        "jobs": summaries,
        "stratified_jobs": strat_summaries,
    }
    prov_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"Wrote {prov_path}")

    flag_path = rr / str(block.get("done_flag", "results/module5/lincs_disease_signature.flag")).replace("/", os.sep)
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    flag_path.write_text("ok\n", encoding="utf-8")

    strat_flag = rr / str(
        block.get("stratified_done_flag", "results/module5/lincs_stratified_signature.flag")
    ).replace("/", os.sep)
    strat_flag.parent.mkdir(parents=True, exist_ok=True)
    strat_flag.write_text("ok\n" if sglobs else "no_stratified_glob_jobs\n", encoding="utf-8")
    print(f"Wrote {strat_flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
