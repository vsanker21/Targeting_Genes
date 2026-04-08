#!/usr/bin/env python3
"""
Outline M2.3: MOVICS / consensus clustering gap report (no R execution).

Compares optional multi-omics path staging to in-repo Verhaak subtype scoring + stratified DEA
as the current partial substitute for molecular subtype discovery.

Config: config/m2_movics_inputs.yaml — movics_integration_stub
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
    p = repo_root() / "config" / "m2_movics_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _read_json(rr: Path, rel: str) -> dict[str, Any] | None:
    p = rr / rel.replace("/", os.sep)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("movics_integration_stub") or {}
    if not block.get("enabled", True):
        print("movics_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m2_movics_paths_status.json") or {}
    verhaak = _read_json(rr, "results/module3/tcga_gbm_verhaak_subtype_summary.json")
    strat_flag = (rr / "results/module3/stratified_dea_integration.flag").is_file()

    blockers: list[str] = []
    if not paths_doc:
        blockers.append("Missing results/module3/m2_movics_paths_status.json (run m2_movics_paths_status)")

    checks = paths_doc.get("checks") or []
    n_ok = sum(1 for c in checks if bool(c.get("exists")))
    multi_omics_ok = any(
        "multi-omics" in str(c.get("name", "")).lower() or "mae" in str(c.get("name", "")).lower()
        for c in checks
        if c.get("exists")
    )

    readiness_tier = "D"
    if multi_omics_ok and n_ok >= 2:
        readiness_tier = "B"
    elif multi_omics_ok or n_ok >= 1:
        readiness_tier = "C"
    elif verhaak:
        readiness_tier = "C"
    elif len(checks) > 0:
        readiness_tier = "D"

    checklist: dict[str, Any] = {
        "in_repo_verhaak_subtype_scores": verhaak is not None,
        "stratified_dea_integration_flag": strat_flag,
        "movics_r_package_installed": False,
        "multi_omics_mae_or_summarized_experiment": multi_omics_ok,
        "consensus_clustering_across_algorithms": False,
        "note": "Pipeline uses MSigDB Verhaak + rank_aggregate (or centroid_cosine) and per-subtype DEA; MOVICS would unify multiple omics + cluster ensembles.",
    }

    recommended: list[str] = [
        "Install MOVICS in R and build MultiAssayExperiment with aligned TCGA/CGGA sample IDs before Snakemake integration.",
        "Stage harmonized RNA + optional protein/methylation matrices under data_root/omics/ with shared rownames (samples).",
        "Treat current Verhaak + stratified DEA as interpretable surrogate until consensus clustering is validated on the same cohort.",
    ]

    out = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_section": "M2.3",
        "artifact_kind": "movics_integration_stub",
        "note": "Checklist only; no clustering or MOVICS API calls.",
        "paths_status_echo": {
            "n_checks": len(checks),
            "n_existing": n_ok,
            "data_root": paths_doc.get("data_root"),
        },
        "verhaak_summary_present": verhaak is not None,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "multi-omics staging path present plus another cohort root",
            "C": "Verhaak summary and/or at least one external path present",
            "D": "no external omics staged and no Verhaak summary found",
        },
        "m2_3_outline_checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": recommended,
    }

    out_rel = str(block.get("output_json", "results/module3/m2_movics_integration_stub.json"))
    out_path = rr / out_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")

    flag_rel = str(block.get("done_flag", "results/module3/m2_movics_integration_stub.flag"))
    (rr / flag_rel.replace("/", os.sep)).write_text("ok\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
