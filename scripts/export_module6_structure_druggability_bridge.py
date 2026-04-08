#!/usr/bin/env python3
"""
Module 6 (outline stub): map high-priority GTS candidates to UniProt accessions and AlphaFold DB URLs.

Does not run structure prediction or pocket scoring; prepares a review table for ChEMBL / DGIdb /
Open Targets–style follow-up (see Project_Outline Module 6).
Optional stratified globs consume subtype GTS stubs under results/module7/gts_candidate_stratified/.

Config: config/module6_inputs.yaml — structure_druggability_bridge
"""

from __future__ import annotations

import json
import os
import re
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


def load_m6_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module6_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def resolve_template(s: str, dr: Path) -> str:
    return str(s).replace("{data_root}", str(dr)).replace("/", os.sep)


def rel_to_repo(rr: Path, p: Path) -> str:
    try:
        return p.resolve().relative_to(rr.resolve()).as_posix()
    except ValueError:
        return str(p.as_posix())


def primary_uniprot(raw: str | float | None) -> str | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    if not s:
        return None
    for part in re.split(r"[,;\s|]+", s):
        p = part.strip()
        if p:
            return p
    return None


def load_hgnc_symbol_meta(
    hgnc_path: Path,
    *,
    approved_only: bool,
) -> dict[str, dict[str, Any]]:
    df = pd.read_csv(hgnc_path, sep="\t", dtype=str, low_memory=False)
    need = {"symbol", "uniprot_ids", "entrez_id"}
    if not need.issubset(df.columns):
        raise ValueError(f"HGNC missing columns {need}: {hgnc_path}")
    if approved_only and "status" in df.columns:
        df = df[df["status"].str.strip().str.lower() == "approved"]
    out: dict[str, dict[str, Any]] = {}
    for _, row in df.iterrows():
        sym = str(row.get("symbol", "") or "").strip()
        if not sym or sym in out:
            continue
        out[sym] = {
            "entrez_id": str(row.get("entrez_id", "") or "").strip() or None,
            "uniprot_ids_raw": str(row.get("uniprot_ids", "") or "").strip() or None,
            "uniprot_primary": primary_uniprot(row.get("uniprot_ids")),
            "name": str(row.get("name", "") or "").strip() or None,
        }
    return out


def bridge_one_gts_table(
    gts_path: Path,
    out_path: Path,
    sym_meta: dict[str, dict[str, Any]],
    max_tier: int,
    max_rows: int,
    rr: Path,
) -> dict[str, Any]:
    gts = pd.read_csv(gts_path, sep="\t", low_memory=False)
    if "hgnc_symbol" not in gts.columns or "gts_evidence_tier" not in gts.columns:
        raise ValueError(f"{gts_path}: need hgnc_symbol, gts_evidence_tier")
    sub = gts[gts["gts_evidence_tier"] <= max_tier].copy()
    sub = sub.head(max_rows)

    rows_out: list[dict[str, Any]] = []
    n_uni = 0
    for _, r in sub.iterrows():
        sym = str(r["hgnc_symbol"]).strip()
        meta = sym_meta.get(sym) or {}
        up = meta.get("uniprot_primary")
        if up:
            n_uni += 1
        af_url = f"https://alphafold.ebi.ac.uk/entry/{up}" if up else ""
        row = {c: r[c] for c in r.index}
        row["entrez_id"] = meta.get("entrez_id") or ""
        row["uniprot_ids_hgnc"] = meta.get("uniprot_ids_raw") or ""
        row["uniprot_primary"] = up or ""
        row["hgnc_name"] = meta.get("name") or ""
        row["alphafold_ebi_entry_url"] = af_url
        rows_out.append(row)

    out_df = pd.DataFrame(rows_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, sep="\t", index=False)
    return {
        "gts_input": rel_to_repo(rr, gts_path),
        "output": rel_to_repo(rr, out_path),
        "n_rows": int(len(out_df)),
        "n_with_uniprot_primary": int(n_uni),
        "max_evidence_tier": max_tier,
        "max_rows_cap": max_rows,
    }


def main() -> int:
    rr = repo_root()
    dr = data_root()
    cfg = load_m6_cfg()
    block = cfg.get("structure_druggability_bridge") or {}
    if not block.get("enabled", True):
        print("structure_druggability_bridge disabled")
        return 0

    hgnc_path = Path(resolve_template(block.get("hgnc_tsv", "{data_root}/references/hgnc_complete_set.txt"), dr))
    if not hgnc_path.is_file():
        print(f"Missing HGNC {hgnc_path}", file=sys.stderr)
        return 1

    max_tier = int(block.get("max_evidence_tier", 2))
    max_rows = int(block.get("max_rows_per_job", 800))
    approved_only = bool(block.get("hgnc_status_approved_only", True))
    jobs = list(block.get("jobs") or [])
    sglobs = list(block.get("stratified_glob_jobs") or [])
    if not jobs and not sglobs:
        print("structure_druggability_bridge: need jobs and/or stratified_glob_jobs", file=sys.stderr)
        return 1

    sym_meta = load_hgnc_symbol_meta(hgnc_path, approved_only=approved_only)
    summaries: list[dict[str, Any]] = []
    strat_summaries: list[dict[str, Any]] = []

    for job in jobs:
        tag = str(job.get("tag", "")).strip()
        gts_rel = str(job.get("gts_candidate_tsv", "")).strip()
        out_rel = str(job.get("output_tsv", "")).strip()
        if not tag or not gts_rel or not out_rel:
            print(f"skip incomplete job {job}", file=sys.stderr)
            continue
        gts_path = rr / gts_rel.replace("/", os.sep)
        if not gts_path.is_file():
            print(f"Missing GTS input {gts_path}", file=sys.stderr)
            return 1
        out_path = rr / out_rel.replace("/", os.sep)
        meta = bridge_one_gts_table(gts_path, out_path, sym_meta, max_tier, max_rows, rr)
        print(f"Wrote {out_path} rows={meta['n_rows']} tag={tag} with_uniprot={meta['n_with_uniprot_primary']}")
        summaries.append({"tag": tag, **meta})

    bridge_strat = rr / "results/module6/structure_druggability_bridge_stratified"

    for sjob in sglobs:
        tag = str(sjob.get("job_tag", "stratified")).strip() or "stratified"
        glob_pat = str(sjob.get("glob_input", "")).strip()
        if not glob_pat:
            print(f"SKIP stratified job_tag={tag}: empty glob_input", file=sys.stderr)
            continue
        subdir = bridge_strat / tag
        for path in sorted(rr.glob(glob_pat)):
            if not path.is_file():
                continue
            key = f"{tag}:{path.stem}"
            stem = path.stem
            if stem.endswith("_gts_stub"):
                stem = stem[: -len("_gts_stub")]
            out_path = subdir / f"{stem}_structure_bridge.tsv"
            try:
                meta = bridge_one_gts_table(path, out_path, sym_meta, max_tier, max_rows, rr)
            except ValueError as e:
                print(f"SKIP {key}: {e}", file=sys.stderr)
                strat_summaries.append(
                    {
                        "job_tag": tag,
                        "gts_input": rel_to_repo(rr, path),
                        "status": "skipped",
                        "reason": str(e),
                    }
                )
                continue
            print(
                f"Wrote {out_path} rows={meta['n_rows']} stratified {key} with_uniprot={meta['n_with_uniprot_primary']}"
            )
            strat_summaries.append({"job_tag": tag, "status": "ok", **meta})

    prov_path = rr / str(
        block.get("provenance_json", "results/module6/structure_druggability_bridge_provenance.json")
    ).replace("/", os.sep)
    prov_path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "outline_module": 6,
        "stub": True,
        "note": "UniProt from HGNC; AlphaFold DB URLs are EBI public entry pages. No pocket or toxicity scoring.",
        "note_stratified": "Subtype bridges inherit stratified GTS / DEA caveats.",
        "alphafold_url_template": "https://alphafold.ebi.ac.uk/entry/{uniprot_accession}",
        "jobs": summaries,
        "stratified_jobs": strat_summaries,
    }
    prov_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"Wrote {prov_path}")

    flag_path = rr / str(block.get("done_flag", "results/module6/structure_druggability_bridge.flag")).replace("/", os.sep)
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    flag_path.write_text("ok\n", encoding="utf-8")

    strat_flag = rr / str(
        block.get("stratified_done_flag", "results/module6/structure_druggability_bridge_stratified.flag")
    ).replace("/", os.sep)
    strat_flag.parent.mkdir(parents=True, exist_ok=True)
    strat_flag.write_text("ok\n" if sglobs else "no_stratified_glob_jobs\n", encoding="utf-8")
    print(f"Wrote {strat_flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
