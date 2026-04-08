#!/usr/bin/env python3
"""
Outline M7: full GTS + validation roadmap gap report (no composite score or benchmarks).

Echoes gts_candidate_stub_provenance.json and states what is still required for a weighted
multi-modality GTS and automated validation (outline §7).

Config: config/module7_inputs.yaml — gts_validation_integration_stub
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


def load_m7_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module7_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _read_json(rr: Path, rel: str) -> dict[str, Any] | None:
    p = rr / rel.replace("/", os.sep)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    rr = repo_root()
    cfg = load_m7_cfg()
    block = cfg.get("gts_validation_integration_stub") or {}
    if not block.get("enabled", True):
        print("gts_validation_integration_stub disabled")
        return 0

    prov = _read_json(rr, "results/module7/gts_candidate_stub_provenance.json") or {}
    blockers: list[str] = []
    if not prov:
        blockers.append("Missing results/module7/gts_candidate_stub_provenance.json (run m7_gts_candidate_stub)")

    jobs = prov.get("jobs") or []
    strat = [s for s in (prov.get("stratified_jobs") or []) if s.get("status") == "ok"]
    n_global = len(jobs)
    n_strat = len(strat)

    stub_mode = bool(prov.get("stub", True))
    gts_meta = prov.get("gts_score") or {}
    ver = str(gts_meta.get("version") or "")
    composite_v1 = ver in ("1.0", "1.1") and gts_meta.get("enabled") is not False
    tier1_total = 0
    for j in jobs:
        tc = j.get("tier_counts") or {}
        tier1_total += int(tc.get("1") or 0)

    readiness_tier = "D"
    if n_global >= 4 and n_strat >= 8:
        readiness_tier = "B" if tier1_total > 0 else "C"
    elif n_global >= 1:
        readiness_tier = "C"
    elif prov:
        readiness_tier = "D"

    checklist: dict[str, Any] = {
        "gts_candidate_stub_tables": n_global > 0,
        "stratified_gts_stub_tables": n_strat > 0,
        "explicit_evidence_tiers_in_stub": True,
        "composite_weighted_gts_score": composite_v1,
        "modality_specific_arms_lincs_structure_scrna": False,
        "prospective_or_external_validation_cohort_hooks": False,
        "automated_benchmark_regression_suite": False,
        "note": (
            "GLIOMA-TARGET v1.x (glioma_target_score) combines E+M (+ v1.1 D+N) via config/glioma_target_score.yaml; "
            "S/D/N/T still outstanding. External validation and benchmark automation remain future work."
        ),
    }

    recommended: list[str] = [
        "Define composite GTS = f(bulk DEA, DepMap, optional scRNA, structure, LINCS) with documented weights and uncertainty.",
        "Reserve held-out tumor samples or external cohorts for tier-list calibration; avoid reusing DEA FDR as sole validation.",
        "Add Snakemake checkpoints or CI tests that diff top-N overlap across pipeline versions when inputs are frozen.",
    ]

    out = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 7,
        "artifact_kind": "gts_validation_integration_stub",
        "note": "Planning JSON only; no new scores, weights, or benchmark metrics computed.",
        "gts_stub_provenance_echo": {
            "n_global_jobs": n_global,
            "n_stratified_jobs_ok": n_strat,
            "stub": stub_mode,
            "metric_summary": prov.get("metric"),
            "thresholds": prov.get("thresholds"),
            "gts_score": prov.get("gts_score"),
        },
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "four global GTS stubs + eight stratified stubs with tier-1 candidates present",
            "C": "partial GTS stub coverage",
            "D": "missing provenance or empty jobs",
        },
        "full_gts_validation_checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": recommended,
    }

    out_rel = str(block.get("output_json", "results/module7/gts_validation_integration_stub.json"))
    out_path = rr / out_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")

    flag_rel = str(block.get("done_flag", "results/module7/gts_validation_integration_stub.flag"))
    (rr / flag_rel.replace("/", os.sep)).write_text("ok\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
