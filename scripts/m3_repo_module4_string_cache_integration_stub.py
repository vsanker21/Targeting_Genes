#!/usr/bin/env python3
"""
Outline M3: M4 STRING cache outline checklist vs m4_string_cache stub, m4_network stub, and M3 network slice.

Config: config/m3_repo_module4_string_cache_outline_inputs.yaml — m3_repo_module4_string_cache_integration_stub
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
    p = repo_root() / "config" / "m3_repo_module4_string_cache_outline_inputs.yaml"
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
    block = doc.get("m3_repo_module4_string_cache_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_module4_string_cache_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_repo_module4_string_cache_paths_status.json") or {}
    m4str_stub = _read_json(rr, "results/module4/m4_string_cache_integration_stub.json")
    m4net_stub = _read_json(rr, "results/module4/m4_network_integration_stub.json")
    m3r4n_stub = _read_json(rr, "results/module3/m3_repo_module4_network_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_repo_module4_string_cache_paths_status.json "
            "(run m3_repo_module4_string_cache_paths_status)"
        )

    g = _group(paths_doc, "module4_string_cache_repo_outline_outputs")
    n_ok = _n_ok(g)
    n_chk = int(g.get("n_checks") or 0)
    ch: list[dict[str, Any]] = list(g.get("checks") or [])

    str_t = _tier_letter(m4str_stub)
    net_t = _tier_letter(m4net_stub)
    m3n_t = _tier_letter(m3r4n_stub)
    parent_signal = any(t and t != "D" for t in (str_t, net_t, m3n_t))

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
        "artifact_kind": "m3_repo_module4_string_cache_integration_stub",
        "note": "Cross-module M3 manifest slice for m4_string_cache outline JSON/flags; complements m3_repo_module4_network and hub/GSEA STRING exports.",
        "paths_status_echo": {
            "module4_string_cache_repo_outline_outputs": {"n_existing": n_ok, "n_checks": n_chk},
            "repo_root": paths_doc.get("repo_root"),
        },
        "m4_string_cache_integration_stub_echo": {
            "readiness_tier": str_t,
            "artifact_kind": m4str_stub.get("artifact_kind") if m4str_stub else None,
        },
        "m4_network_integration_stub_echo": {
            "readiness_tier": net_t,
            "artifact_kind": m4net_stub.get("artifact_kind") if m4net_stub else None,
        },
        "m3_repo_module4_network_stub_echo": {
            "readiness_tier": m3n_t,
            "artifact_kind": m3r4n_stub.get("artifact_kind") if m3r4n_stub else None,
        },
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "All four m4_string_cache outline JSON/flag paths present under results/module4.",
            "C": "At least two paths present, or a parent STRING-cache / network / M3-network stub shows partial readiness.",
            "D": "Fewer than two paths and no parent stub signal.",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Run m4_string_cache_paths_status and m4_string_cache_integration_stub after data_root/networks STRING mirrors exist.",
            "Cross-check dea_string_export_provenance.json jobs with cached API responses under string_api_json_cache.",
        ],
    }

    out_rel = str(
        block.get("output_json", "results/module3/m3_repo_module4_string_cache_integration_stub.json")
    )
    flag_rel = str(
        block.get("done_flag", "results/module3/m3_repo_module4_string_cache_integration_stub.flag")
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
