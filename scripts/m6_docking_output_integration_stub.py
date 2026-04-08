#!/usr/bin/env python3
"""
Outline M6 supplement: docking pose / score export staging gap checklist.

Reads m6_docking_output_paths_status.json and echoes structure_admet_integration_stub.

Config: config/m6_docking_output_outline_inputs.yaml — m6_docking_output_integration_stub
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
    p = repo_root() / "config" / "m6_docking_output_outline_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8-sig"))


def _read_json(rr: Path, rel: str) -> dict[str, Any] | None:
    p = rr / rel.replace("/", os.sep)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _group(paths_doc: dict[str, Any], gid: str) -> dict[str, Any] | None:
    for g in paths_doc.get("groups") or []:
        if str(g.get("id")) == gid:
            return g
    return None


def _n_ok(g: dict[str, Any]) -> int:
    return int(g.get("n_existing") or 0)


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("m6_docking_output_integration_stub") or {}
    if not block.get("enabled", True):
        print("m6_docking_output_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module6/m6_docking_output_paths_status.json") or {}
    admet_stub = _read_json(rr, "results/module6/structure_admet_integration_stub.json")
    tool_doc = _read_json(rr, "results/module6/module6_structure_tooling_paths_status.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module6/m6_docking_output_paths_status.json (run m6_docking_output_paths_status)"
        )

    gnina = _group(paths_doc, "gnina_pose_and_score_exports") or {}
    glide = _group(paths_doc, "glide_pose_archives") or {}
    batch = _group(paths_doc, "batch_virtual_screen_outputs") or {}

    g_ok = _n_ok(gnina) > 0
    gl_ok = _n_ok(glide) > 0
    b_ok = _n_ok(batch) > 0
    n_hit = sum(1 for x in (g_ok, gl_ok, b_ok) if x)

    readiness_tier = "D"
    if g_ok and (gl_ok or b_ok):
        readiness_tier = "B"
    elif n_hit >= 2:
        readiness_tier = "B"
    elif n_hit == 1:
        readiness_tier = "C"
    elif admet_stub:
        readiness_tier = "C"
    elif paths_doc.get("groups"):
        readiness_tier = "D"

    echo = {}
    if admet_stub:
        echo = {
            "readiness_tier": admet_stub.get("readiness_tier"),
            "artifact_kind": admet_stub.get("artifact_kind"),
        }

    n_tool = sum(1 for c in (tool_doc or {}).get("checks") or [] if c.get("exists"))

    checklist: dict[str, Any] = {
        "gnina_pose_or_score_export_staged": g_ok,
        "glide_run_archive_staged": gl_ok,
        "batch_virtual_screen_output_staged": b_ok,
        "structure_tooling_path_checks_hit": n_tool > 0,
        "in_repo_docking_or_rescoring_jobs": False,
        "note": "structure_druggability_bridge lists targets; docking runs stay off-repo unless mirrored under data_root/docking.",
    }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 6,
        "artifact_kind": "m6_docking_output_integration_stub",
        "note": "Planning artifact; no docking engines invoked from this step.",
        "paths_status_echo": {
            "gnina_pose_and_score_exports": {"n_existing": _n_ok(gnina), "n_checks": int(gnina.get("n_checks") or 0)},
            "glide_pose_archives": {"n_existing": _n_ok(glide), "n_checks": int(glide.get("n_checks") or 0)},
            "batch_virtual_screen_outputs": {"n_existing": _n_ok(batch), "n_checks": int(batch.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "structure_admet_stub_echo": echo or None,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "GNINA exports plus Glide or batch screen staging, or two of three docking output dimensions.",
            "C": "One docking output dimension or structure_admet_integration_stub only.",
            "D": "No docking output paths and no favorable ADMET stub echo.",
        },
        "m6_docking_output_checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Mirror external GNINA/Glide/Vina outputs under paths in m6_docking_output_outline_inputs.yaml for audits.",
            "Align receptors and box definitions with AlphaFold URLs from structure_druggability_bridge exports.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module6/m6_docking_output_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module6/m6_docking_output_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
