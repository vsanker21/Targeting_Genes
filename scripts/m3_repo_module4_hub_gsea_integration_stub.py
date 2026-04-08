#!/usr/bin/env python3
"""
Outline M3: Module 4 WGCNA hub + GSEA prerank checklist vs TOIL TPM and bulk DEA repo stubs plus M4 GSEA mirror stub.

Config: config/m3_repo_module4_hub_gsea_outline_inputs.yaml — m3_repo_module4_hub_gsea_integration_stub
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
    p = repo_root() / "config" / "m3_repo_module4_hub_gsea_outline_inputs.yaml"
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
    block = doc.get("m3_repo_module4_hub_gsea_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_module4_hub_gsea_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_repo_module4_hub_gsea_paths_status.json") or {}
    toil_stub = _read_json(rr, "results/module3/m3_repo_toil_bulk_expression_integration_stub.json")
    wel_stub = _read_json(rr, "results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.json")
    r3_stub = _read_json(rr, "results/module3/m3_repo_recount3_bulk_dea_integration_stub.json")
    strat_stub = _read_json(rr, "results/module3/m3_repo_stratified_bulk_dea_integration_stub.json")
    gsea_mirror_stub = _read_json(rr, "results/module4/m4_gsea_mirror_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_repo_module4_hub_gsea_paths_status.json "
            "(run m3_repo_module4_hub_gsea_paths_status)"
        )

    g = _group(paths_doc, "module4_wgcna_gsea_stratified_string_repo_outputs")
    n_ok = _n_ok(g)
    n_chk = int(g.get("n_checks") or 0)
    ch: list[dict[str, Any]] = list(g.get("checks") or [])

    toil_t = _tier_letter(toil_stub)
    wel_t = _tier_letter(wel_stub)
    r3_t = _tier_letter(r3_stub)
    strat_t = _tier_letter(strat_stub)
    gsea_t = _tier_letter(gsea_mirror_stub)
    parent_signal = any(t and t != "D" for t in (toil_t, wel_t, r3_t, strat_t, gsea_t))

    readiness_tier = "D"
    if n_chk > 0 and n_ok >= n_chk:
        readiness_tier = "B"
    elif n_ok >= 13:
        readiness_tier = "C"
    elif parent_signal:
        readiness_tier = "C"

    checklist = {str(c.get("name", f"check_{i}")): bool(c.get("exists")) for i, c in enumerate(ch)}

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_repo_module4_hub_gsea_integration_stub",
        "note": "Co-expression hub and prerank exports under results/module4; distinct from m4_network_* external workspace staging.",
        "paths_status_echo": {
            "module4_wgcna_gsea_stratified_string_repo_outputs": {"n_existing": n_ok, "n_checks": n_chk},
            "repo_root": paths_doc.get("repo_root"),
        },
        "m3_repo_toil_bulk_expression_stub_echo": {
            "readiness_tier": toil_t,
            "artifact_kind": toil_stub.get("artifact_kind") if toil_stub else None,
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
        "m4_gsea_mirror_stub_echo": {
            "readiness_tier": gsea_t,
            "artifact_kind": gsea_mirror_stub.get("artifact_kind") if gsea_mirror_stub else None,
        },
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "All paths in m3_repo_module4_hub_gsea_outline_inputs (WGCNA hub, GSEA prerank, stratified .rnk, STRING export provenance) present.",
            "C": "At least thirteen paths present, or a parent TPM/DEA/GSEA-mirror stub shows partial readiness.",
            "D": "Fewer than thirteen paths and no parent stub signal.",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Run m4_wgcna_hub_expr_subset, traits, overlap, export_dea_gsea_prerank_rnk, and stratified STRING export rules after DEA and TPM hub exist.",
            "Mirror MSigDB or enrichment outputs under data_root/gsea (m4_gsea_mirror_paths_status) for offline fgsea.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m3_repo_module4_hub_gsea_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m3_repo_module4_hub_gsea_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
