#!/usr/bin/env python3
"""
Module 5 (outline): sRGES / LINCS L1000 integration checklist.

Merges lincs_connectivity_readiness + lincs_signature_pack into a single stub artifact so
Snakemake and pipeline_results_index can track the gap between Entrez signatures and full sRGES.
When results/module5/m5_srges_run_provenance.json exists (optional m5_srges_run), the checklist
records in-repo compound ranking from real perturbation_tsv under data_root.

Config: config/module5_inputs.yaml — srges_integration_stub
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


def _read_json(rr: Path, rel: str) -> dict[str, Any] | None:
    p = rr / rel.replace("/", os.sep)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    rr = repo_root()
    cfg = load_m5_cfg()
    block = cfg.get("srges_integration_stub") or {}
    if not block.get("enabled", True):
        print("srges_integration_stub disabled")
        return 0

    ready = _read_json(rr, "results/module5/lincs_connectivity_readiness.json") or {}
    pack = _read_json(rr, "results/module5/lincs_signature_pack.json") or {}
    dp = _read_json(rr, "results/module5/module5_data_paths_status.json") or {}
    srges_run = _read_json(rr, "results/module5/m5_srges_run_provenance.json")

    n_global = len(pack.get("global_signatures") or [])
    n_strat = len(pack.get("stratified_signatures") or [])
    sigs_ok = bool((ready.get("signatures") or {}).get("ready"))

    blockers: list[str] = list(ready.get("blockers") or [])
    if not pack:
        blockers.append("Missing results/module5/lincs_signature_pack.json (run m5_lincs_signature_pack)")

    srges_ok = bool(srges_run and str(srges_run.get("status", "")).lower() == "ok")

    checklist: dict[str, Any] = {
        "disease_signature_entrez": sigs_ok,
        "connectivity_readiness_tier": ready.get("readiness_tier"),
        "l1000_reference": {
            "note": "Full sRGES needs perturbation × gene reference (GCTX or CLUE API), not produced here.",
            "data_root_path_checks": [c.get("name") for c in (dp.get("checks") or [])],
        },
        "srges_execution": srges_ok,
        "in_repo_m5_srges_run": srges_ok,
    }

    out = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 5,
        "artifact_kind": "srges_integration_stub",
        "note": (
            "Stub checklist only: no sRGES scores, no L1000 perturbation ranking. "
            "Use lincs_disease_signature_*_entrez.tsv with cmapPy/CLUE or external sRGES code."
        ),
        "connectivity_echo": {
            "readiness_tier": ready.get("readiness_tier"),
            "signatures": ready.get("signatures"),
            "tooling": ready.get("tooling"),
        },
        "signature_pack_echo": {
            "n_global_signatures": n_global,
            "n_stratified_signatures": n_strat,
            "defaults_for_connectivity": pack.get("defaults_for_connectivity"),
        },
        "srges_pipeline_checklist": checklist,
        "m5_srges_run_echo": (
            {
                "reference_mode": srges_run.get("reference_mode"),
                "n_compounds_ranked": srges_run.get("n_compounds_ranked"),
                "rank_tsv": srges_run.get("rank_tsv"),
                "signature_job_tag": srges_run.get("signature_job_tag"),
            }
            if srges_run
            else {}
        ),
        "blockers": blockers,
        "recommended_next_steps": list(ready.get("recommended_next_steps") or [])
        + [
            "Obtain L1000 level 5 GCTX (or use CLUE API) and implement sRGES / connectivity scoring against Entrez signatures.",
        ]
        + (
            [
                "m5_srges_run completed in-repo; stage cmapPy/CLUE mirror exports under data_root for m5_srges_output_paths_status if you track external rank files.",
            ]
            if srges_ok
            else []
        ),
    }

    out_rel = str(block.get("output_json", "results/module5/srges_integration_stub.json"))
    out_path = rr / out_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")

    flag_rel = str(block.get("done_flag", "results/module5/srges_integration_stub.flag"))
    (rr / flag_rel.replace("/", os.sep)).write_text("ok\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
