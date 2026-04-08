#!/usr/bin/env python3
"""
Module 5 (outline): single JSON summarizing LINCS / cmapPy connectivity readiness (no queries run).

Combines module5_data_paths_status, cmap_tooling_scan, and lincs_disease_signature provenance
with on-disk checks for Entrez signature TSVs.

Config: config/module5_inputs.yaml — lincs_connectivity_readiness
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_m5_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module5_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def main() -> int:
    rr = repo_root()
    cfg = load_m5_cfg()
    block = cfg.get("lincs_connectivity_readiness") or {}
    if not block.get("enabled", True):
        print("lincs_connectivity_readiness disabled")
        return 0

    dp = rr / "results/module5/module5_data_paths_status.json"
    cmap_p = rr / "results/module5/cmap_tooling_scan.json"
    lincs_p = rr / "results/module5/lincs_disease_signature_provenance.json"

    blockers: list[str] = []
    notes: list[str] = []

    path_checks: dict[str, bool] = {}
    if dp.is_file():
        d0 = json.loads(dp.read_text(encoding="utf-8"))
        for c in d0.get("checks") or []:
            path_checks[str(c.get("name", ""))] = bool(c.get("exists"))
    else:
        blockers.append("Missing results/module5/module5_data_paths_status.json")

    cmap_doc: dict[str, Any] = {}
    if cmap_p.is_file():
        cmap_doc = json.loads(cmap_p.read_text(encoding="utf-8"))
    else:
        blockers.append("Missing results/module5/cmap_tooling_scan.json (run m5_cmap_tooling_scan)")
        notes.append("cmap_tooling_scan absent; treating cmapPy as unknown")

    cmap_importable = bool(cmap_doc.get("cmapPy_importable"))
    cmap_path_ok = bool(path_checks.get("cmapPy (pipelines)"))
    clue_path_ok = bool(path_checks.get("LINCS CLUE API subset"))
    tooling_ok = cmap_importable or cmap_path_ok or clue_path_ok

    opt_fn = cmap_doc.get("optional_third_party_functional")
    opt_gct_ok: bool | None = None
    if isinstance(opt_fn, dict):
        if "cmapPy_gct_roundtrip_ok" in opt_fn:
            opt_gct_ok = bool(opt_fn.get("cmapPy_gct_roundtrip_ok"))
        if opt_gct_ok is False:
            notes.append(
                "optional_third_party_functional report: cmapPy GCT round-trip failed — run scripts/ensure_optional_third_party_functional.py"
            )
        elif opt_gct_ok is True and cmap_importable:
            notes.append("optional_third_party_functional report: cmapPy GCT round-trip passed (I/O smoke OK)")

    sig_paths: list[str] = []
    if lincs_p.is_file():
        prov = json.loads(lincs_p.read_text(encoding="utf-8"))
        for j in prov.get("jobs") or []:
            rel = j.get("output")
            if rel:
                sig_paths.append(str(rel))
        for sj in prov.get("stratified_jobs") or []:
            if sj.get("status") == "ok" and sj.get("output"):
                sig_paths.append(str(sj["output"]))
    else:
        blockers.append("Missing lincs_disease_signature_provenance.json")

    n_sig_existing = 0
    for rel in sig_paths:
        p = rr / str(rel).replace("/", os.sep)
        if p.is_file():
            n_sig_existing += 1

    if not sig_paths:
        blockers.append("No Entrez signature outputs listed in lincs provenance")
    elif n_sig_existing < len(sig_paths):
        blockers.append(
            f"Only {n_sig_existing}/{len(sig_paths)} Entrez signature TSVs present on disk (run export_module5_lincs_disease_signature)"
        )

    signatures_ready = len(sig_paths) > 0 and n_sig_existing == len(sig_paths)

    if not cmap_importable and not cmap_path_ok:
        notes.append("cmapPy not importable and pipelines/cmapPy path missing — install package or clone cmapPy under data_root for in-Python connectivity")
    if not clue_path_ok:
        notes.append("LINCS CLUE API subset path missing — optional for CLUE REST workflows")

    readiness_tier = "D"
    if signatures_ready and tooling_ok:
        readiness_tier = "A" if cmap_importable else "B"
    elif signatures_ready:
        readiness_tier = "C"
    elif tooling_ok:
        readiness_tier = "D"

    recommended: list[str] = []
    if signatures_ready and not cmap_importable:
        recommended.append("pip/conda install cmapPy (or set PYTHONPATH) to match pipelines/cmapPy checkout")
    if signatures_ready and cmap_importable:
        recommended.append("Use Entrez TSVs under results/module5/lincs_disease_signature*.tsv as query signatures in cmapPy/CLUE tutorials")
    if not signatures_ready:
        recommended.append("snakemake m5_lincs_disease_signature (or python scripts/export_module5_lincs_disease_signature.py)")

    out = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 5,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "A": "Entrez signatures on disk + cmapPy importable (or path fallback not required for A)",
            "B": "Signatures on disk + local cmap/CLUE tree or import path available",
            "C": "Signatures on disk only; cmap tooling still missing",
            "D": "Incomplete signatures and/or no tooling path",
        },
        "signatures": {
            "n_paths_in_provenance": len(sig_paths),
            "n_existing_on_disk": n_sig_existing,
            "ready": signatures_ready,
        },
        "tooling": {
            "cmapPy_importable": cmap_importable,
            "path_cmapPy_pipelines": cmap_path_ok,
            "path_lincs_clue_subset": clue_path_ok,
            "any_tooling_path_or_import": tooling_ok,
            "optional_functional_report_in_cmap_scan": isinstance(opt_fn, dict),
            "optional_functional_gct_ok": opt_gct_ok,
        },
        "blockers": blockers,
        "notes": notes,
        "recommended_next_steps": recommended,
        "note": "Does not validate GCTX contents or run sRGES; heuristic only.",
    }

    out_rel = str(block.get("output_json", "results/module5/lincs_connectivity_readiness.json"))
    out_path = rr / out_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")

    flag_rel = str(block.get("done_flag", "results/module5/lincs_connectivity_readiness.flag"))
    (rr / flag_rel.replace("/", os.sep)).write_text("ok\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
