#!/usr/bin/env python3
"""
Outline M7 external GTS-like score mirror checklist (no scoring jobs).

Reads m7_gts_external_score_mirror_paths_status.json, gts_validation_integration_stub.json (input),
and optionally m7_validation_integration_stub.json and gts_candidate_stub_provenance.json on disk.

Config: config/m7_gts_external_score_mirror_outline_inputs.yaml (m7_gts_external_score_mirror_integration_stub).
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
    p = repo_root() / "config" / "m7_gts_external_score_mirror_outline_inputs.yaml"
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
    block = doc.get("m7_gts_external_score_mirror_integration_stub") or {}
    if not block.get("enabled", True):
        print("m7_gts_external_score_mirror_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module7/m7_gts_external_score_mirror_paths_status.json") or {}
    gts_val = _read_json(rr, "results/module7/gts_validation_integration_stub.json")
    m7_val = _read_json(rr, "results/module7/m7_validation_integration_stub.json")
    gts_prov_path = rr / "results" / "module7" / "gts_candidate_stub_provenance.json"
    in_repo_gts_prov = gts_prov_path.is_file()

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module7/m7_gts_external_score_mirror_paths_status.json (run m7_gts_external_score_mirror_paths_status)"
        )

    g_comp = _group(paths_doc, "external_composite_or_tier_scores") or {}
    g_mod = _group(paths_doc, "modality_priority_exports") or {}

    comp_ok = _n_ok(g_comp) > 0
    mod_ok = _n_ok(g_mod) > 0

    readiness_tier = "D"
    if comp_ok and mod_ok:
        readiness_tier = "B"
    elif comp_ok or mod_ok:
        readiness_tier = "C"
    elif gts_val or m7_val or in_repo_gts_prov:
        readiness_tier = "C"

    gts_echo: dict[str, Any] = {}
    if gts_val:
        gts_echo = {
            "readiness_tier": gts_val.get("readiness_tier"),
            "artifact_kind": gts_val.get("artifact_kind"),
        }

    m7_val_echo: dict[str, Any] = {}
    if m7_val:
        m7_val_echo = {
            "readiness_tier": m7_val.get("readiness_tier"),
            "artifact_kind": m7_val.get("artifact_kind"),
        }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_section": "M7",
        "artifact_kind": "m7_gts_external_score_mirror_integration_stub",
        "note": "Checklist only; compare external score TSVs to results/module7/gts_candidate_table_*_stub.tsv offline.",
        "paths_status_echo": {
            "external_composite_or_tier_scores": {"n_existing": _n_ok(g_comp), "n_checks": int(g_comp.get("n_checks") or 0)},
            "modality_priority_exports": {"n_existing": _n_ok(g_mod), "n_checks": int(g_mod.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "gts_validation_integration_stub_echo": gts_echo,
        "m7_validation_integration_stub_echo": m7_val_echo,
        "in_repo_gts_candidate_stub_provenance_present": in_repo_gts_prov,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Both composite score staging and modality export trees show at least one path.",
            "C": "One mirror dimension or in-repo GTS validation or validation outline stub or GTS stub provenance only.",
            "D": "No mirror paths and no GTS or validation stub echo or stub provenance.",
        },
        "checklist": {
            "external_composite_scores_staged": comp_ok,
            "modality_priority_exports_staged": mod_ok,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Export scores from external prioritization pipelines under data_root/gts_external/composite_score_tables.",
            "Keep in-repo m7_gts_candidate_stub outputs as the default comparison baseline.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module7/m7_gts_external_score_mirror_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module7/m7_gts_external_score_mirror_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
