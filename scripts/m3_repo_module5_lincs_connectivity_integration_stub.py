#!/usr/bin/env python3
"""
Outline M3: Module 5 LINCS signature + connectivity checklist vs bulk DEA and L1000 data stubs.

Config: config/m3_repo_module5_lincs_connectivity_outline_inputs.yaml — m3_repo_module5_lincs_connectivity_integration_stub
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
    p = repo_root() / "config" / "m3_repo_module5_lincs_connectivity_outline_inputs.yaml"
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
    block = doc.get("m3_repo_module5_lincs_connectivity_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_module5_lincs_connectivity_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_repo_module5_lincs_connectivity_paths_status.json") or {}
    wel_stub = _read_json(rr, "results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.json")
    r3_stub = _read_json(rr, "results/module3/m3_repo_recount3_bulk_dea_integration_stub.json")
    strat_stub = _read_json(rr, "results/module3/m3_repo_stratified_bulk_dea_integration_stub.json")
    l1k_stub = _read_json(rr, "results/module5/m5_l1000_data_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_repo_module5_lincs_connectivity_paths_status.json "
            "(run m3_repo_module5_lincs_connectivity_paths_status)"
        )

    g = _group(paths_doc, "module5_lincs_repo_connectivity_outputs")
    n_ok = _n_ok(g)
    n_chk = int(g.get("n_checks") or 0)
    ch: list[dict[str, Any]] = list(g.get("checks") or [])

    wel_t = _tier_letter(wel_stub)
    r3_t = _tier_letter(r3_stub)
    strat_t = _tier_letter(strat_stub)
    l1k_t = _tier_letter(l1k_stub)
    parent_signal = any(
        t and t != "D" for t in (wel_t, r3_t, strat_t, l1k_t)
    )

    readiness_tier = "D"
    if n_chk > 0 and n_ok >= n_chk:
        readiness_tier = "B"
    elif n_ok >= 10:
        readiness_tier = "C"
    elif parent_signal:
        readiness_tier = "C"

    checklist = {str(c.get("name", f"check_{i}")): bool(c.get("exists")) for i, c in enumerate(ch)}

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_repo_module5_lincs_connectivity_integration_stub",
        "note": "Cross-module pack: M5 Entrez signatures and connectivity tiers vs M3 bulk DEA and data_root L1000 staging.",
        "paths_status_echo": {
            "module5_lincs_repo_connectivity_outputs": {"n_existing": n_ok, "n_checks": n_chk},
            "repo_root": paths_doc.get("repo_root"),
        },
        "m3_repo_bulk_welch_ols_dea_stub_echo": {
            "readiness_tier": wel_t,
            "artifact_kind": wel_stub.get("artifact_kind") if wel_stub else None,
        },
        "m3_repo_recount3_bulk_dea_stub_echo": {
            "readiness_tier": r3_t,
            "artifact_kind": r3_stub.get("artifact_kind") if r3_stub else None,
        },
        "m3_repo_stratified_bulk_dea_stub_echo": {
            "readiness_tier": strat_t,
            "artifact_kind": strat_stub.get("artifact_kind") if strat_stub else None,
        },
        "m5_l1000_data_stub_echo": {
            "readiness_tier": l1k_t,
            "artifact_kind": l1k_stub.get("artifact_kind") if l1k_stub else None,
        },
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "All paths in m3_repo_module5_lincs_connectivity_outline_inputs (signatures, stratified Entrez TSVs, cmap scan, connectivity pack, srges stub) present.",
            "C": "At least ten paths present, or a parent bulk-DEA / stratified / recount3 / L1000 stub shows partial readiness.",
            "D": "Fewer than ten paths and no parent stub signal.",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Run m5_lincs_disease_signature, m5_cmap_tooling_scan, m5_lincs_connectivity_readiness, m5_lincs_signature_pack, m5_srges_integration_stub after bulk DEA TSVs exist.",
            "Stage L1000 GCTX or CLUE caches under data_root (m5_l1000_data_paths_status) before cmapPy batch connectivity.",
        ],
    }

    out_rel = str(
        block.get("output_json", "results/module3/m3_repo_module5_lincs_connectivity_integration_stub.json")
    )
    flag_rel = str(
        block.get("done_flag", "results/module3/m3_repo_module5_lincs_connectivity_integration_stub.flag")
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
