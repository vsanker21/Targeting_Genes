#!/usr/bin/env python3
"""
Module 5 (outline): single JSON catalog of all Entrez LINCS/cmapPy signature TSVs from provenance.

For external scripts: ordered paths, on-disk stats, and provenance fields (no cmapPy execution).

Config: config/module5_inputs.yaml — lincs_signature_pack
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_m5_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module5_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def file_stats(rr: Path, rel: str) -> dict[str, Any]:
    p = rr / rel.replace("/", os.sep)
    out: dict[str, Any] = {"path_posix": str(Path(rel).as_posix()), "exists": p.is_file()}
    if not out["exists"]:
        out["size_bytes"] = None
        out["n_data_rows"] = None
        out["mtime_utc"] = None
        return out
    st = p.stat()
    out["size_bytes"] = int(st.st_size)
    out["mtime_utc"] = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
    try:
        with p.open("rb") as f:
            nlines = sum(1 for _ in f)
        out["n_data_rows"] = max(0, nlines - 1)
    except OSError:
        out["n_data_rows"] = None
    return out


def main() -> int:
    rr = repo_root()
    cfg = load_m5_cfg()
    block = cfg.get("lincs_signature_pack") or {}
    if not block.get("enabled", True):
        print("lincs_signature_pack disabled")
        return 0

    prov_p = rr / "results/module5/lincs_disease_signature_provenance.json"
    if not prov_p.is_file():
        print(f"Missing {prov_p}", file=sys.stderr)
        return 1
    prov = json.loads(prov_p.read_text(encoding="utf-8"))

    global_sigs: list[dict[str, Any]] = []
    for job in prov.get("jobs") or []:
        rel = job.get("output")
        if not rel:
            continue
        st = file_stats(rr, str(rel))
        global_sigs.append(
            {
                "kind": "global",
                "tag": job.get("tag"),
                "input": job.get("input"),
                "n_entrez_unique": job.get("n_entrez_unique"),
                "effect_col": job.get("effect_col"),
                "p_col": job.get("p_col"),
                **st,
            }
        )

    strat_sigs: list[dict[str, Any]] = []
    for sj in prov.get("stratified_jobs") or []:
        if sj.get("status") != "ok":
            continue
        rel = sj.get("output")
        if not rel:
            continue
        st = file_stats(rr, str(rel))
        strat_sigs.append(
            {
                "kind": "stratified",
                "job_tag": sj.get("job_tag"),
                "input": sj.get("input"),
                "n_entrez_unique": sj.get("n_entrez_unique"),
                "effect_col": sj.get("effect_col"),
                "p_col": sj.get("p_col"),
                **st,
            }
        )

    defaults = dict(block.get("defaults_for_connectivity") or {})
    if not defaults:
        defaults = {"comment": "Set defaults_for_connectivity in module5_inputs.yaml if desired (e.g. primary global tag)."}

    doc = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 5,
        "tsv_columns": ["entrez_id", "signed_neglog10_p"],
        "metric": prov.get("metric"),
        "provenance_note": prov.get("note"),
        "defaults_for_connectivity": defaults,
        "global_signatures": global_sigs,
        "stratified_signatures": strat_sigs,
        "note": "Paths are repo-relative (path_posix). Use with cmapPy/CLUE after confirming Entrez ID space matches reference perturbations.",
    }

    out_rel = str(block.get("output_json", "results/module5/lincs_signature_pack.json"))
    flag_rel = str(block.get("done_flag", "results/module5/lincs_signature_pack.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    (rr / flag_rel.replace("/", os.sep)).write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} global={len(global_sigs)} stratified={len(strat_sigs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
