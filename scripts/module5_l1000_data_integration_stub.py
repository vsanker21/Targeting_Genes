#!/usr/bin/env python3
"""
Outline M5: L1000 / GCTX / CLUE data staging gap checklist (no cmapPy batch queries).

Reads m5_l1000_data_paths_status.json and echoes srges_integration_stub for connectivity context.

Config: config/m5_l1000_data_outline_inputs.yaml — m5_l1000_data_integration_stub
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
    p = repo_root() / "config" / "m5_l1000_data_outline_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


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


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("m5_l1000_data_integration_stub") or {}
    if not block.get("enabled", True):
        print("m5_l1000_data_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module5/m5_l1000_data_paths_status.json") or {}
    srges = _read_json(rr, "results/module5/srges_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append("Missing results/module5/m5_l1000_data_paths_status.json (run m5_l1000_data_paths_status)")

    gctx = _group(paths_doc, "l1000_gctx_mirror") or {}
    clue = _group(paths_doc, "clue_api_cache") or {}
    cmap_ref = _group(paths_doc, "cmap_reference_files") or {}
    batch = _group(paths_doc, "connectivity_batch_exports") or {}

    def n_ok(g: dict[str, Any]) -> int:
        return int(g.get("n_existing") or 0)

    gctx_ok = n_ok(gctx) > 0
    clue_ok = n_ok(clue) > 0
    cmap_ok = n_ok(cmap_ref) > 0
    batch_ok = n_ok(batch) > 0
    n_groups_hit = sum(1 for x in (gctx_ok, clue_ok, cmap_ok, batch_ok) if x)

    readiness_tier = "D"
    if gctx_ok and (clue_ok or batch_ok):
        readiness_tier = "B"
    elif n_groups_hit >= 2:
        readiness_tier = "B"
    elif n_groups_hit == 1:
        readiness_tier = "C"
    elif paths_doc.get("groups"):
        readiness_tier = "D"
    if srges and readiness_tier == "D":
        readiness_tier = "C"

    echo: dict[str, Any] = {}
    if srges:
        echo = {
            "connectivity_readiness_tier": (srges.get("connectivity_echo") or {}).get("readiness_tier"),
            "artifact_kind": srges.get("artifact_kind"),
        }

    checklist: dict[str, Any] = {
        "l1000_gctx_or_level5_mirror_staged": gctx_ok,
        "clue_api_response_or_cache_staged": clue_ok,
        "cmap_landmark_reference_staged": cmap_ok,
        "connectivity_query_batch_exports_staged": batch_ok,
        "cmapPy_batch_connectivity_in_repo": False,
        "automated_clue_api_runner_in_repo": False,
        "note": "Entrez signatures remain in lincs_disease_signature_*_entrez.tsv; this stub tracks bulk L1000 reference data staging for external cmapPy/sRGES drivers.",
    }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 5,
        "artifact_kind": "m5_l1000_data_integration_stub",
        "note": "Checklist only; no GCTX read, no L1000 perturbation ranking, no CLUE HTTP client in-repo.",
        "paths_status_echo": {
            "l1000_gctx_mirror": {"n_existing": n_ok(gctx), "n_checks": int(gctx.get("n_checks") or 0)},
            "clue_api_cache": {"n_existing": n_ok(clue), "n_checks": int(clue.get("n_checks") or 0)},
            "cmap_reference_files": {"n_existing": n_ok(cmap_ref), "n_checks": int(cmap_ref.get("n_checks") or 0)},
            "connectivity_batch_exports": {"n_existing": n_ok(batch), "n_checks": int(batch.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "srges_stub_echo": echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "GCTX mirror plus CLUE cache or saved connectivity batch exports, or two or more L1000 data dimensions staged.",
            "C": "One staging dimension, or only sRGES gap stub without on-disk L1000 data paths.",
            "D": "No L1000 data staging paths and no sRGES stub echo.",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Mirror a subset GCTX or Level 5 file under data_root/lincs/ and point cmapPy GCT reader at it from a notebook.",
            "Cache CLUE API responses or export cmap batch connectivity tables for diffing against Entrez disease signatures.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module5/m5_l1000_data_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module5/m5_l1000_data_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
