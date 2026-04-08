#!/usr/bin/env python3
"""
Outline M3: M7 validation outline checklist vs m7_validation_integration_stub and M7 GTS stub M3 slice.

Config: config/m3_repo_module7_validation_outline_inputs.yaml — m3_repo_module7_validation_integration_stub
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
    p = repo_root() / "config" / "m3_repo_module7_validation_outline_inputs.yaml"
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
    block = doc.get("m3_repo_module7_validation_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_module7_validation_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_repo_module7_validation_paths_status.json") or {}
    m7_stub = _read_json(rr, "results/module7/m7_validation_integration_stub.json")
    gts_m3 = _read_json(rr, "results/module3/m3_repo_module7_gts_stub_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_repo_module7_validation_paths_status.json "
            "(run m3_repo_module7_validation_paths_status)"
        )

    g = _group(paths_doc, "module7_validation_repo_outline_outputs")
    n_ok = _n_ok(g)
    n_chk = int(g.get("n_checks") or 0)
    ch: list[dict[str, Any]] = list(g.get("checks") or [])

    m7_t = _tier_letter(m7_stub)
    gts_t = _tier_letter(gts_m3)
    parent_signal = any(t and t != "D" for t in (m7_t, gts_t))

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
        "artifact_kind": "m3_repo_module7_validation_integration_stub",
        "note": "Cross-module M3 manifest slice for m7_validation outline JSON/flags; aligns with GTS stub M3 slice and data_root holdout staging.",
        "paths_status_echo": {
            "module7_validation_repo_outline_outputs": {"n_existing": n_ok, "n_checks": n_chk},
            "repo_root": paths_doc.get("repo_root"),
        },
        "m7_validation_integration_stub_echo": {
            "readiness_tier": m7_t,
            "artifact_kind": m7_stub.get("artifact_kind") if m7_stub else None,
        },
        "m3_repo_module7_gts_stub_echo": {
            "readiness_tier": gts_t,
            "artifact_kind": gts_m3.get("artifact_kind") if gts_m3 else None,
        },
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "All four m7_validation outline JSON/flag paths present under results/module7.",
            "C": "At least two paths present, or m7_validation / M7 GTS-stub M3 integration_stub shows partial readiness.",
            "D": "Fewer than two paths and no parent stub signal.",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Run m7_validation_paths_status and m7_validation_integration_stub after data_root/validation trees exist.",
            "Cross-check gts_validation_integration_stub and m3_repo_module7_gts_stub for benchmark vs holdout gaps.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m3_repo_module7_validation_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m3_repo_module7_validation_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
