#!/usr/bin/env python3
"""
Outline M3: Module 7 GTS stub path checklist vs bulk DEA repo stubs and gts_validation_integration_stub.

Config: config/m3_repo_module7_gts_stub_outline_inputs.yaml — m3_repo_module7_gts_stub_integration_stub
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


def load_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "m3_repo_module7_gts_stub_outline_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8-sig"))


def _read_json(rr: Path, rel: str) -> dict[str, Any] | None:
    p = rr / rel.replace("/", os.sep)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _group(paths_doc: dict[str, Any], gid: str) -> dict[str, Any]:
    for g in paths_doc.get("groups") or []:
        if str(g.get("id")) == gid:
            return g
    return {}


def _n_ok(g: dict[str, Any]) -> int:
    return int(g.get("n_existing") or 0)


def _tier_letter(doc: dict[str, Any] | None) -> str | None:
    if not doc:
        return None
    t = doc.get("readiness_tier")
    return str(t) if t is not None else None


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("m3_repo_module7_gts_stub_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_module7_gts_stub_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_repo_module7_gts_stub_paths_status.json") or {}
    wel_stub = _read_json(rr, "results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.json")
    r3_stub = _read_json(rr, "results/module3/m3_repo_recount3_bulk_dea_integration_stub.json")
    strat_stub = _read_json(rr, "results/module3/m3_repo_stratified_bulk_dea_integration_stub.json")
    gts_val = _read_json(rr, "results/module7/gts_validation_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_repo_module7_gts_stub_paths_status.json "
            "(run m3_repo_module7_gts_stub_paths_status)"
        )

    g = _group(paths_doc, "module7_gts_candidate_stub_repo_outputs")
    n_ok = _n_ok(g)
    n_chk = int(g.get("n_checks") or 0)
    ch: list[dict[str, Any]] = list(g.get("checks") or [])

    wel_t = _tier_letter(wel_stub)
    r3_t = _tier_letter(r3_stub)
    strat_t = _tier_letter(strat_stub)
    gts_t = _tier_letter(gts_val)
    parent_signal = any(t and t != "D" for t in (wel_t, r3_t, strat_t, gts_t))

    readiness_tier = "D"
    if n_chk > 0 and n_ok >= n_chk:
        readiness_tier = "B"
    elif n_ok >= 9:
        readiness_tier = "C"
    elif parent_signal:
        readiness_tier = "C"

    checklist = {str(c.get("name", f"check_{i}")): bool(c.get("exists")) for i, c in enumerate(ch)}

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_repo_module7_gts_stub_integration_stub",
        "note": "Cross-module M3 manifest slice for M7 evidence-tier stub tables; full GTS scoring remains out of scope.",
        "paths_status_echo": {
            "module7_gts_candidate_stub_repo_outputs": {"n_existing": n_ok, "n_checks": n_chk},
            "repo_root": paths_doc.get("repo_root"),
        },
        "m3_repo_bulk_welch_ols_dea_stub_echo": {
            "readiness_tier": wel_t,
            "artifact_kind": wel_stub.get("artifact_kind") if wel_stub else None,
        },
        "m3_repo_recount3_bulk_dea_stub_echo": {
            "readiness_tier": r3_t,
            "artifact_kind": r3_stub.get("artifact_kind") if r3_stub else None,
        },
        "m3_repo_stratified_bulk_dea_stub_echo": {
            "readiness_tier": strat_t,
            "artifact_kind": strat_stub.get("artifact_kind") if strat_stub else None,
        },
        "gts_validation_integration_stub_echo": {
            "readiness_tier": gts_t,
            "artifact_kind": gts_val.get("artifact_kind") if gts_val else None,
        },
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "All paths in m3_repo_module7_gts_stub_outline_inputs (global + stratified stub TSVs, flags, gts_validation_integration_stub) present.",
            "C": "At least nine paths present, or a parent DEA / stratified / gts_validation stub shows partial readiness.",
            "D": "Fewer than nine paths and no parent stub signal.",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Run m7_gts_candidate_stub after DepMap CRISPR joins and DEA TSVs exist, then m7_gts_validation_integration_stub.",
            "Use module7_export_manifest and pipeline_results_index for optional vs required GTS-adjacent paths.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m3_repo_module7_gts_stub_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m3_repo_module7_gts_stub_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
