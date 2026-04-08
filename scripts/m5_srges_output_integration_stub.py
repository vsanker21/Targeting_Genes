#!/usr/bin/env python3
"""
Outline M5 supplement: sRGES / compound-ranking output staging gap checklist.

Reads m5_srges_output_paths_status.json, echoes srges_integration_stub and optional m5_l1000_data_paths_status.

Config: config/m5_srges_output_outline_inputs.yaml — m5_srges_output_integration_stub
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
    p = repo_root() / "config" / "m5_srges_output_outline_inputs.yaml"
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
    block = doc.get("m5_srges_output_integration_stub") or {}
    if not block.get("enabled", True):
        print("m5_srges_output_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module5/m5_srges_output_paths_status.json") or {}
    srges = _read_json(rr, "results/module5/srges_integration_stub.json")
    l1000_paths = _read_json(rr, "results/module5/m5_l1000_data_paths_status.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append("Missing results/module5/m5_srges_output_paths_status.json (run m5_srges_output_paths_status)")

    ranks = _group(paths_doc, "srges_rank_and_score_exports") or {}
    priors = _group(paths_doc, "compound_prior_metadata") or {}
    pathproj = _group(paths_doc, "pathway_projection_followup") or {}

    r_ok = _n_ok(ranks) > 0
    p_ok = _n_ok(priors) > 0
    w_ok = _n_ok(pathproj) > 0
    n_hit = sum(1 for x in (r_ok, p_ok, w_ok) if x)

    l1_batch = _group(l1000_paths or {}, "connectivity_batch_exports") or {}
    l1_batch_ok = _n_ok(l1_batch) > 0

    readiness_tier = "D"
    if r_ok and (p_ok or w_ok):
        readiness_tier = "B"
    elif n_hit >= 2:
        readiness_tier = "B"
    elif n_hit == 1:
        readiness_tier = "C"
    elif srges:
        readiness_tier = "C"
    elif l1_batch_ok:
        readiness_tier = "C"
    elif paths_doc.get("groups"):
        readiness_tier = "D"

    echo = {}
    if srges:
        echo = {
            "artifact_kind": srges.get("artifact_kind"),
            "connectivity_readiness_tier": (srges.get("connectivity_echo") or {}).get("readiness_tier"),
        }

    checklist: dict[str, Any] = {
        "srges_rank_exports_staged": r_ok,
        "compound_prior_tables_staged": p_ok,
        "pathway_projection_outputs_staged": w_ok,
        "l1000_data_connectivity_batch_group_hit": l1_batch_ok,
        "in_repo_srges_or_cmap_batch_scoring": False,
        "note": "Disease Entrez signatures and readiness live in-repo; compound ranks require external sRGES/cmapPy.",
    }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 5,
        "artifact_kind": "m5_srges_output_integration_stub",
        "note": "Planning artifact; no sRGES or L1000 perturbation scoring from this step.",
        "paths_status_echo": {
            "srges_rank_and_score_exports": {"n_existing": _n_ok(ranks), "n_checks": int(ranks.get("n_checks") or 0)},
            "compound_prior_metadata": {"n_existing": _n_ok(priors), "n_checks": int(priors.get("n_checks") or 0)},
            "pathway_projection_followup": {"n_existing": _n_ok(pathproj), "n_checks": int(pathproj.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "srges_integration_stub_echo": echo or None,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Rank exports plus priors or pathway follow-up staged, or two of three output dimensions.",
            "C": "One output dimension, or srges_integration_stub / L1000 connectivity_batch paths only.",
            "D": "No sRGES output staging and no favorable echo.",
        },
        "m5_srges_output_checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Save external sRGES or cmapPy rank tables under data_root/lincs paths in m5_srges_output_outline_inputs.yaml.",
            "Pair exports with m5_l1000_data_paths_status connectivity_batch_exports when batch connectivity is run off-repo.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module5/m5_srges_output_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module5/m5_srges_output_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
