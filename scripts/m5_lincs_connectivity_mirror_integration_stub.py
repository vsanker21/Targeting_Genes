#!/usr/bin/env python3
"""
Outline M5 LINCS connectivity or cmap query result mirror checklist (no cmapPy or CLUE execution).

Reads m5_lincs_connectivity_mirror_paths_status.json, lincs_connectivity_readiness.json when present,
and m5_l1000_data_integration_stub.json for staging echo.

Config: config/m5_lincs_connectivity_mirror_outline_inputs.yaml (m5_lincs_connectivity_mirror_integration_stub).
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
    p = repo_root() / "config" / "m5_lincs_connectivity_mirror_outline_inputs.yaml"
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
    block = doc.get("m5_lincs_connectivity_mirror_integration_stub") or {}
    if not block.get("enabled", True):
        print("m5_lincs_connectivity_mirror_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module5/m5_lincs_connectivity_mirror_paths_status.json") or {}
    readiness = _read_json(rr, "results/module5/lincs_connectivity_readiness.json")
    l1_stub = _read_json(rr, "results/module5/m5_l1000_data_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module5/m5_lincs_connectivity_mirror_paths_status.json (run m5_lincs_connectivity_mirror_paths_status)"
        )

    g_cmap = _group(paths_doc, "cmap_query_response_mirror") or {}
    g_mat = _group(paths_doc, "connectivity_matrix_staging") or {}

    cmap_ok = _n_ok(g_cmap) > 0
    mat_ok = _n_ok(g_mat) > 0

    readiness_tier = "D"
    if cmap_ok and mat_ok:
        readiness_tier = "B"
    elif cmap_ok or mat_ok:
        readiness_tier = "C"
    elif readiness is not None:
        readiness_tier = "C"
    elif l1_stub:
        readiness_tier = "C"

    l1_echo: dict[str, Any] = {}
    if l1_stub:
        l1_echo = {
            "readiness_tier": l1_stub.get("readiness_tier"),
            "artifact_kind": l1_stub.get("artifact_kind"),
        }

    readiness_echo: dict[str, Any] = {}
    if readiness:
        readiness_echo = {
            "readiness_tier": readiness.get("readiness_tier"),
            "artifact_kind": readiness.get("artifact_kind"),
        }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_section": "M5",
        "artifact_kind": "m5_lincs_connectivity_mirror_integration_stub",
        "note": "Checklist only; run cmapPy or CLUE externally and drop exports under data_root/lincs/.",
        "paths_status_echo": {
            "cmap_query_response_mirror": {"n_existing": _n_ok(g_cmap), "n_checks": int(g_cmap.get("n_checks") or 0)},
            "connectivity_matrix_staging": {"n_existing": _n_ok(g_mat), "n_checks": int(g_mat.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "lincs_connectivity_readiness_present": readiness is not None,
        "lincs_connectivity_readiness_echo": readiness_echo,
        "m5_l1000_data_integration_stub_echo": l1_echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Both cmap or CLUE export mirror and connectivity matrix staging show at least one path.",
            "C": "One mirror dimension, in-repo lincs_connectivity_readiness.json, or L1000 data integration stub only.",
            "D": "No mirror paths and no readiness JSON or L1000 stub echo.",
        },
        "checklist": {
            "cmap_or_clue_export_mirror_staged": cmap_ok,
            "connectivity_matrix_or_manifest_staged": mat_ok,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Populate lincs_connectivity_readiness via Snakemake after signatures and cmap scan exist.",
            "Save cmapPy or CLUE batch outputs under data_root/lincs/cmap_query_response_cache or connectivity_matrix_exports.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module5/m5_lincs_connectivity_mirror_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module5/m5_lincs_connectivity_mirror_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
