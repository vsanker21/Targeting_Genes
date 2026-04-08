#!/usr/bin/env python3
"""
Outline M1: reference + GDC staging gap checklist (no GDC HTTP).

Reads m1_reference_gdc_paths_status.json, m1_outline_integration_stub.json, and optional in-repo GDC QC JSON.

Config: config/m1_reference_gdc_outline_inputs.yaml — m1_reference_gdc_integration_stub
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
    p = repo_root() / "config" / "m1_reference_gdc_outline_inputs.yaml"
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
    block = doc.get("m1_reference_gdc_integration_stub") or {}
    if not block.get("enabled", True):
        print("m1_reference_gdc_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m1_reference_gdc_paths_status.json") or {}
    m1_stub = _read_json(rr, "results/module3/m1_outline_integration_stub.json")
    gdc_qc = _read_json(rr, "results/module2/gdc_counts_matrix_qc.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m1_reference_gdc_paths_status.json (run m1_reference_gdc_paths_status)"
        )

    g_ref = _group(paths_doc, "reference_annotation_bundle") or {}
    g_gdc = _group(paths_doc, "gdc_open_star_counts_staging") or {}
    g_aux = _group(paths_doc, "gdc_client_cache_auxiliary") or {}

    ref_core = _n_ok(g_ref) >= 2
    gdc_bundle = _n_ok(g_gdc) >= 1
    manifest_ok = any(
        c.get("exists")
        and "manifest" in str(c.get("path", "")).replace("\\", "/").lower()
        for c in (g_gdc.get("checks") or [])
    )
    aux_ok = _n_ok(g_aux) > 0

    readiness_tier = "D"
    if ref_core and (gdc_bundle or gdc_qc is not None):
        readiness_tier = "B"
    elif ref_core or gdc_bundle or manifest_ok:
        readiness_tier = "C"
    elif gdc_qc is not None:
        readiness_tier = "C"
    elif aux_ok:
        readiness_tier = "C"
    elif m1_stub:
        readiness_tier = "C"

    m1_echo: dict[str, Any] = {}
    if m1_stub:
        m1_echo = {
            "readiness_tier": m1_stub.get("readiness_tier"),
            "artifact_kind": m1_stub.get("artifact_kind"),
        }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 1,
        "artifact_kind": "m1_reference_gdc_integration_stub",
        "note": "Checklist only; use download_all_required.py / GDC client for real pulls.",
        "paths_status_echo": {
            "reference_annotation_bundle": {"n_existing": _n_ok(g_ref), "n_checks": int(g_ref.get("n_checks") or 0)},
            "gdc_open_star_counts_staging": {"n_existing": _n_ok(g_gdc), "n_checks": int(g_gdc.get("n_checks") or 0)},
            "gdc_client_cache_auxiliary": {"n_existing": _n_ok(g_aux), "n_checks": int(g_aux.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "gdc_manifest_path_reported_present": manifest_ok,
        "in_repo_gdc_counts_matrix_qc": gdc_qc is not None,
        "m1_outline_stub_echo": m1_echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Core reference files plus GDC STAR staging or in-repo gdc_counts_matrix_qc.json.",
            "C": "Partial reference or GDC staging, QC-only, auxiliary cache, or M1 outline stub echo.",
            "D": "No reference/GDC paths and no QC or M1 echo.",
        },
        "checklist": {
            "reference_bundle_partial_or_complete": _n_ok(g_ref) > 0,
            "gdc_star_counts_dir_or_manifest_staged": gdc_bundle or manifest_ok,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Keep GENCODE/HGNC/blacklist versions aligned with methods_traceability.yaml and STAR matrix gene IDs.",
            "Stage STAR count TSVs and gdc_files_manifest.json before build_gdc_gbm_expression_matrix / cohort matrices.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m1_reference_gdc_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m1_reference_gdc_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
