#!/usr/bin/env python3
"""
Outline M3: M6 structure tooling + ADMET gap checklist vs structure_admet stub and M6 bridge M3 slice.

Config: config/m3_repo_module6_structure_tooling_outline_inputs.yaml —
m3_repo_module6_structure_tooling_integration_stub
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
    p = repo_root() / "config" / "m3_repo_module6_structure_tooling_outline_inputs.yaml"
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
    block = doc.get("m3_repo_module6_structure_tooling_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_module6_structure_tooling_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_repo_module6_structure_tooling_paths_status.json") or {}
    admet = _read_json(rr, "results/module6/structure_admet_integration_stub.json")
    bridge_m3 = _read_json(rr, "results/module3/m3_repo_module6_structure_bridge_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_repo_module6_structure_tooling_paths_status.json "
            "(run m3_repo_module6_structure_tooling_paths_status)"
        )

    g = _group(paths_doc, "module6_structure_tooling_and_admet_repo_outline_outputs")
    n_ok = _n_ok(g)
    n_chk = int(g.get("n_checks") or 0)
    ch: list[dict[str, Any]] = list(g.get("checks") or [])

    ad_t = _tier_letter(admet)
    br_t = _tier_letter(bridge_m3)
    parent_signal = any(t and t != "D" for t in (ad_t, br_t))

    readiness_tier = "D"
    if n_chk > 0 and n_ok >= n_chk:
        readiness_tier = "B"
    elif n_ok >= 2:
        readiness_tier = "C"
    elif parent_signal:
        readiness_tier = "C"

    checklist = {str(c.get("name", f"check_{i}")): bool(c.get("exists")) for i, c in enumerate(ch)}

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_repo_module6_structure_tooling_integration_stub",
        "note": "Cross-module M3 manifest slice for M6 tooling paths + structure_admet stub; aligns with druggability bridge M3 slice.",
        "paths_status_echo": {
            "module6_structure_tooling_and_admet_repo_outline_outputs": {
                "n_existing": n_ok,
                "n_checks": n_chk,
            },
            "repo_root": paths_doc.get("repo_root"),
        },
        "structure_admet_integration_stub_echo": {
            "readiness_tier": ad_t,
            "artifact_kind": admet.get("artifact_kind") if admet else None,
        },
        "m3_repo_module6_structure_bridge_stub_echo": {
            "readiness_tier": br_t,
            "artifact_kind": bridge_m3.get("artifact_kind") if bridge_m3 else None,
        },
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "All four M6 tooling + structure_admet outline JSON/flag paths present under results/module6.",
            "C": "At least two paths present, or structure_admet / M6 bridge M3 integration_stub shows partial readiness.",
            "D": "Fewer than two paths and no parent stub signal.",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Run m6_structure_tooling_paths_status and m6_structure_admet_integration_stub after data_root tool paths exist.",
            "Use m3_repo_module6_structure_bridge for GTS→structure TSV readiness vs pocket tooling gaps.",
        ],
    }

    out_rel = str(
        block.get(
            "output_json",
            "results/module3/m3_repo_module6_structure_tooling_integration_stub.json",
        )
    )
    flag_rel = str(
        block.get(
            "done_flag",
            "results/module3/m3_repo_module6_structure_tooling_integration_stub.flag",
        )
    )
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
