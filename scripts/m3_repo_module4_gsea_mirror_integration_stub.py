#!/usr/bin/env python3
"""
Outline M3: M4 GSEA mirror outline checklist vs m4 GSEA stub, hub/GSEA M3 slice, pathway-database M3 slice.

Config: config/m3_repo_module4_gsea_mirror_outline_inputs.yaml — m3_repo_module4_gsea_mirror_integration_stub
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
    p = repo_root() / "config" / "m3_repo_module4_gsea_mirror_outline_inputs.yaml"
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
    block = doc.get("m3_repo_module4_gsea_mirror_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_module4_gsea_mirror_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_repo_module4_gsea_mirror_paths_status.json") or {}
    gsm_stub = _read_json(rr, "results/module4/m4_gsea_mirror_integration_stub.json")
    hub_stub = _read_json(rr, "results/module3/m3_repo_module4_hub_gsea_integration_stub.json")
    pw_stub = _read_json(rr, "results/module3/m3_repo_module4_pathway_database_mirror_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_repo_module4_gsea_mirror_paths_status.json "
            "(run m3_repo_module4_gsea_mirror_paths_status)"
        )

    g = _group(paths_doc, "module4_gsea_mirror_repo_outline_outputs")
    n_ok = _n_ok(g)
    n_chk = int(g.get("n_checks") or 0)
    ch: list[dict[str, Any]] = list(g.get("checks") or [])

    gsm_t = _tier_letter(gsm_stub)
    hub_t = _tier_letter(hub_stub)
    pw_t = _tier_letter(pw_stub)
    parent_signal = any(t and t != "D" for t in (gsm_t, hub_t, pw_t))

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
        "artifact_kind": "m3_repo_module4_gsea_mirror_integration_stub",
        "note": "Cross-module M3 manifest slice for m4_gsea_mirror outline JSON/flags; aligns with in-repo prerank exports and KEGG/Reactome mirror planning.",
        "paths_status_echo": {
            "module4_gsea_mirror_repo_outline_outputs": {"n_existing": n_ok, "n_checks": n_chk},
            "repo_root": paths_doc.get("repo_root"),
        },
        "m4_gsea_mirror_integration_stub_echo": {
            "readiness_tier": gsm_t,
            "artifact_kind": gsm_stub.get("artifact_kind") if gsm_stub else None,
        },
        "m3_repo_module4_hub_gsea_stub_echo": {
            "readiness_tier": hub_t,
            "artifact_kind": hub_stub.get("artifact_kind") if hub_stub else None,
        },
        "m3_repo_module4_pathway_database_mirror_stub_echo": {
            "readiness_tier": pw_t,
            "artifact_kind": pw_stub.get("artifact_kind") if pw_stub else None,
        },
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "All four m4_gsea_mirror outline JSON/flag paths present under results/module4.",
            "C": "At least two paths present, or a parent GSEA / hub-GSEA / pathway-database M3 stub shows partial readiness.",
            "D": "Fewer than two paths and no parent stub signal.",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Run m4_gsea_mirror_paths_status and m4_gsea_mirror_integration_stub after data_root/gsea mirrors exist.",
            "Use results/module4/gsea/*.rnk with MSigDB GMT staging and m4_pathway_database_mirror planning stubs.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m3_repo_module4_gsea_mirror_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m3_repo_module4_gsea_mirror_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
