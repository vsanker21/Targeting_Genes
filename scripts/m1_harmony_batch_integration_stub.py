#!/usr/bin/env python3
"""
Outline M1 supplement: Harmony / scRNA batch correction gap checklist (vs ComBat-Seq on bulk).

Reads m1_harmony_batch_paths_status.json, echoes m1_outline_integration_stub when present.

Config: config/m1_harmony_batch_outline_inputs.yaml — m1_harmony_batch_integration_stub
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
    p = repo_root() / "config" / "m1_harmony_batch_outline_inputs.yaml"
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


def _n_ok(g: dict[str, Any]) -> int:
    return int(g.get("n_existing") or 0)


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("m1_harmony_batch_integration_stub") or {}
    if not block.get("enabled", True):
        print("m1_harmony_batch_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m1_harmony_batch_paths_status.json") or {}
    m1_stub = _read_json(rr, "results/module3/m1_outline_integration_stub.json")
    combat = _read_json(rr, "results/module1/combat_seq_tcga_gbm_primary/combat_seq_provenance.json")
    scrna_stub = _read_json(rr, "results/module3/scrna_spatial_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m1_harmony_batch_paths_status.json (run m1_harmony_batch_paths_status)"
        )

    obj = _group(paths_doc, "harmony_integrated_objects") or {}
    meta = _group(paths_doc, "batch_covariate_metadata") or {}
    cross = _group(paths_doc, "cross_dataset_integration_workspace") or {}

    obj_ok = _n_ok(obj) > 0
    meta_ok = _n_ok(meta) > 0
    cross_ok = _n_ok(cross) > 0
    n_hit = sum(1 for x in (obj_ok, meta_ok, cross_ok) if x)

    readiness_tier = "D"
    if obj_ok and meta_ok:
        readiness_tier = "B"
    elif n_hit >= 2:
        readiness_tier = "B"
    elif n_hit == 1:
        readiness_tier = "C"
    elif combat or (m1_stub and m1_stub.get("combat_seq_provenance_present")):
        readiness_tier = "C"
    elif paths_doc.get("groups"):
        readiness_tier = "D"

    m1_check = (m1_stub or {}).get("m1_outline_checklist") or {}
    harmony_false_in_m1_outline = not m1_check.get("harmony_scrna_batch_correction")

    checklist: dict[str, Any] = {
        "harmony_integrated_object_dirs_staged": obj_ok,
        "batch_covariate_or_run_config_staged": meta_ok,
        "cross_study_integration_workspace_staged": cross_ok,
        "combat_seq_bulk_counts_in_repo": combat is not None,
        "in_repo_harmony_or_scanpy_snakemake_rules": False,
        "m1_outline_stub_lists_harmony_as_not_wired": harmony_false_in_m1_outline,
        "note": "ComBat-Seq on GDC STAR counts remains the in-repo bulk batch partial; Harmony needs sc matrices + covariates under data_root.",
    }

    echo_m1 = {}
    if m1_stub:
        echo_m1 = {
            "readiness_tier": m1_stub.get("readiness_tier"),
            "combat_seq_provenance_present": m1_stub.get("combat_seq_provenance_present"),
        }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 1,
        "artifact_kind": "m1_harmony_batch_integration_stub",
        "note": "Planning artifact; no R harmony package or Scanpy external calls from this step.",
        "paths_status_echo": {
            "harmony_integrated_objects": {"n_existing": _n_ok(obj), "n_checks": int(obj.get("n_checks") or 0)},
            "batch_covariate_metadata": {"n_existing": _n_ok(meta), "n_checks": int(meta.get("n_checks") or 0)},
            "cross_dataset_integration_workspace": {"n_existing": _n_ok(cross), "n_checks": int(cross.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "m1_outline_stub_echo": echo_m1 or None,
        "scrna_spatial_stub_present": scrna_stub is not None,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Harmony-ready object dirs and batch metadata both staged, or two of three Harmony staging groups.",
            "C": "One staging group or ComBat-Seq provenance only (bulk proxy).",
            "D": "No Harmony staging paths and no ComBat echo.",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Align scrna_spatial_integration_stub and public GEO paths with directories listed in m1_harmony_batch_outline_inputs.yaml.",
            "Add richer batch columns than TSS-derived ComBat before wiring Bioconductor harmony or scanpy.external.pp.harmony_integrate.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m1_harmony_batch_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m1_harmony_batch_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
