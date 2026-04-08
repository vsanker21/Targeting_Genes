#!/usr/bin/env python3
"""
Outline M6: structure / pocket / ADMET / docking gap report (no scoring or docking runs).

Combines module6_structure_tooling_paths_status and structure_druggability_bridge provenance
into one JSON for planning full §6 delivery (AutoSite, GNINA/Glide, toxicity panels).

Config: config/module6_inputs.yaml — structure_admet_integration_stub
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


def load_m6_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module6_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _read_json(rr: Path, rel: str) -> dict[str, Any] | None:
    p = rr / rel.replace("/", os.sep)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    rr = repo_root()
    cfg = load_m6_cfg()
    block = cfg.get("structure_admet_integration_stub") or {}
    if not block.get("enabled", True):
        print("structure_admet_integration_stub disabled")
        return 0

    tool = _read_json(rr, "results/module6/module6_structure_tooling_paths_status.json") or {}
    bridge = _read_json(rr, "results/module6/structure_druggability_bridge_provenance.json") or {}

    blockers: list[str] = []
    if not tool:
        blockers.append("Missing results/module6/module6_structure_tooling_paths_status.json")
    if not bridge:
        blockers.append("Missing results/module6/structure_druggability_bridge_provenance.json")

    tool_checks = tool.get("checks") or []
    n_tool = len(tool_checks)
    n_tool_ok = sum(1 for c in tool_checks if bool(c.get("exists")))
    p2rank = next((c for c in tool_checks if "p2rank" in str(c.get("name", "")).lower()), None)
    fpocket = next((c for c in tool_checks if "fpocket" in str(c.get("name", "")).lower()), None)
    gnina = next((c for c in tool_checks if "gnina" in str(c.get("name", "")).lower()), None)

    jobs = bridge.get("jobs") or []
    strat_ok = sum(1 for s in (bridge.get("stratified_jobs") or []) if s.get("status") == "ok")
    bridge_jobs_ok = len(jobs) > 0

    readiness_tier = "D"
    if bridge_jobs_ok and n_tool_ok >= 2:
        readiness_tier = "B"
    elif bridge_jobs_ok and n_tool_ok >= 1:
        readiness_tier = "C"
    elif bridge_jobs_ok:
        readiness_tier = "C"
    elif n_tool > 0:
        readiness_tier = "D"

    checklist: dict[str, Any] = {
        "structure_druggability_bridge_tables": bridge_jobs_ok,
        "stratified_bridge_jobs_ok": strat_ok,
        "p2rank_available": bool(p2rank and p2rank.get("exists")),
        "fpocket_available": bool(fpocket and fpocket.get("exists")),
        "gnina_marker_or_env_ready": bool(gnina and gnina.get("exists")),
        "batch_alphafold_structures": False,
        "pocket_scores_autosite_dogsite": False,
        "cns_off_tumor_toxicity_panel": False,
        "routine_glide_or_gnina_docking": False,
        "note": "Bridge TSVs carry UniProt and AlphaFold DB URLs only; pockets, ADMET, and poses are not computed in-repo.",
    }

    recommended: list[str] = [
        "Install or check out P2Rank/fpocket under data_root/tools per module6_inputs.yaml for pocket prediction.",
        "Add gnina_ready.flag or conda env when GNINA is available for GPU docking.",
        "For ADMET/CNS panels, plug structure_bridge outputs into external tools (e.g. SwissADME, eTox) outside this Snakemake layer.",
    ]
    if not bridge_jobs_ok:
        recommended.insert(0, "Run m6_structure_druggability_bridge after M7 GTS stubs.")

    out = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 6,
        "artifact_kind": "structure_admet_integration_stub",
        "note": "Planning artifact only; no molecular dynamics, docking, or toxicity prediction executed here.",
        "tooling_paths_echo": {
            "n_checks": n_tool,
            "n_existing": n_tool_ok,
            "data_root": tool.get("data_root"),
        },
        "structure_bridge_echo": {
            "n_global_jobs": len(jobs),
            "n_stratified_jobs_ok": strat_ok,
        },
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "bridge tables + at least two optional tooling paths present",
            "C": "bridge tables and/or partial tooling",
            "D": "incomplete bridge or path metadata only",
        },
        "m6_outline_checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": recommended,
    }

    out_rel = str(block.get("output_json", "results/module6/structure_admet_integration_stub.json"))
    out_path = rr / out_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")

    flag_rel = str(block.get("done_flag", "results/module6/structure_admet_integration_stub.flag"))
    (rr / flag_rel.replace("/", os.sep)).write_text("ok\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
