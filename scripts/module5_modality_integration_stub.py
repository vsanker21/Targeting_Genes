#!/usr/bin/env python3
"""
Outline M5: TMZ sensitization + CAR-T surface funnel gap checklist (no modeling).

Reads m5_modality_paths_status.json and optionally echoes sRGES stub presence for small-molecule context.

Config: config/m5_modality_outline_inputs.yaml — m5_modality_integration_stub
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
    p = repo_root() / "config" / "m5_modality_outline_inputs.yaml"
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
    block = doc.get("m5_modality_integration_stub") or {}
    if not block.get("enabled", True):
        print("m5_modality_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module5/m5_modality_paths_status.json") or {}
    srges = _read_json(rr, "results/module5/srges_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append("Missing results/module5/m5_modality_paths_status.json (run m5_modality_paths_status)")

    tmz = _group(paths_doc, "tmz_sensitization") or {}
    cart = _group(paths_doc, "cart_surface_funnel") or {}

    def n_ok(g: dict[str, Any]) -> int:
        return int(g.get("n_existing") or 0)

    tmz_ok = n_ok(tmz) > 0
    cart_ok = n_ok(cart) > 0

    readiness_tier = "D"
    if tmz_ok and cart_ok:
        readiness_tier = "B"
    elif tmz_ok or cart_ok:
        readiness_tier = "C"
    elif paths_doc.get("groups"):
        readiness_tier = "D"
    if srges and readiness_tier == "D":
        readiness_tier = "C"

    checklist: dict[str, Any] = {
        "tmz_staging_any_path": tmz_ok,
        "cart_staging_any_path": cart_ok,
        "mgmt_or_response_table_staged": tmz_ok,
        "surface_antigen_or_sc_derived_staged": cart_ok,
        "tmz_pharmacology_model_in_repo": False,
        "cart_ranking_or_deconvolution_in_repo": False,
        "note": "Join Entrez disease signatures (lincs_disease_signature_*) with external TMZ biomarker and CAR target lists when staging paths exist.",
    }

    out = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 5,
        "artifact_kind": "m5_modality_integration_stub",
        "note": "Checklist only; no TMZ IC50, MGMT modeling, or CAR-T scoring.",
        "paths_status_echo": {
            "tmz_sensitization": {"n_existing": n_ok(tmz), "n_checks": int(tmz.get("n_checks") or 0)},
            "cart_surface_funnel": {"n_existing": n_ok(cart), "n_checks": int(cart.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "srges_stub_present": srges is not None,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "At least one TMZ-related path and one CAR-related staging path exist under data_root.",
            "C": "Only one arm staged, or sRGES stub present while modality paths are empty.",
            "D": "No modality staging paths found (outline planning only).",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Stage MGMT beta / TMZ outcome tables and curated surface antigen panels before wiring treatment-stratified DEA or connectivity.",
            "Reuse m5_lincs_connectivity_readiness tier for small molecules; extend with TMZ/CAR-specific gene sets externally.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module5/m5_modality_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module5/m5_modality_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
