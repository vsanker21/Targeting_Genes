#!/usr/bin/env python3
"""
Module 3 (outline): single-cell / spatial execution gap report (no Scanpy/Seurat runs).

Aggregates module3_public_inputs_status and module3_sc_workflow_paths_status into one JSON
for planning and pipeline_results_index provenance.

Config: config/module3_inputs.yaml — scrna_spatial_integration_stub
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


def load_m3_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module3_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _read_json(rr: Path, rel: str) -> dict[str, Any] | None:
    p = rr / rel.replace("/", os.sep)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _count_checks(doc: dict[str, Any]) -> tuple[int, int]:
    checks = doc.get("checks") or []
    n = len(checks)
    n_ok = sum(1 for c in checks if bool(c.get("exists")))
    return n, n_ok


def main() -> int:
    rr = repo_root()
    cfg = load_m3_cfg()
    block = cfg.get("scrna_spatial_integration_stub") or {}
    if not block.get("enabled", True):
        print("scrna_spatial_integration_stub disabled")
        return 0

    pub = _read_json(rr, "results/module3/module3_public_inputs_status.json") or {}
    scw = _read_json(rr, "results/module3/module3_sc_workflow_paths_status.json") or {}

    blockers: list[str] = []
    if not pub:
        blockers.append("Missing results/module3/module3_public_inputs_status.json (run m3_public_inputs_status)")
    if not scw:
        blockers.append("Missing results/module3/module3_sc_workflow_paths_status.json (run m3_sc_workflow_paths_status)")

    pub_n, pub_ok = _count_checks(pub)
    sc_n, sc_ok = _count_checks(scw)

    workspace_ok = False
    visium_ok = False
    for c in scw.get("checks") or []:
        name = str(c.get("name", ""))
        if "working directory" in name.lower() and c.get("exists"):
            workspace_ok = True
        if "visium" in name.lower() and c.get("exists"):
            visium_ok = True

    any_public_data = pub_ok > 0

    readiness_tier = "D"
    if workspace_ok and any_public_data:
        readiness_tier = "B" if visium_ok else "C"
    elif workspace_ok:
        readiness_tier = "C"
    elif any_public_data:
        readiness_tier = "C"
    elif pub_n > 0 or sc_n > 0:
        readiness_tier = "D"

    recommended: list[str] = []
    if not workspace_ok:
        recommended.append(
            "Create data_root/single_cell/workspace and stage h5ad or counts for Scanpy/Seurat workflows."
        )
    if not visium_ok:
        recommended.append(
            "Optional: point Visium/spaceranger outputs under data_root/spatial/visium_runs for spatial modules."
        )
    if pub_ok < pub_n:
        recommended.append("Fetch or link public GEO/SRA/Dryad paths listed in module3_inputs.yaml path_checks.")
    recommended.append(
        "Wire Snakemake rules for Scanpy/Seurat/Harmony only after matrices exist; this stub does not run them."
    )

    out = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "scrna_spatial_integration_stub",
        "note": "Path inventory + tier only; no normalization, clustering, or deconvolution executed in-repo.",
        "public_inputs_echo": {
            "n_checks": pub_n,
            "n_existing": pub_ok,
            "data_root": pub.get("data_root"),
        },
        "sc_workflow_paths_echo": {
            "n_checks": sc_n,
            "n_existing": sc_ok,
            "check_group": scw.get("check_group"),
            "data_root": scw.get("data_root"),
        },
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "workspace + public reference data + Visium root present",
            "C": "workspace or public data present, tooling partial",
            "D": "path checks only or nothing staged",
        },
        "flags": {
            "single_cell_workspace_ready": workspace_ok,
            "any_public_scrna_or_spatial_path": any_public_data,
            "visium_root_ready": visium_ok,
        },
        "blockers": blockers,
        "recommended_next_steps": recommended,
    }

    out_rel = str(block.get("output_json", "results/module3/scrna_spatial_integration_stub.json"))
    out_path = rr / out_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")

    flag_rel = str(block.get("done_flag", "results/module3/scrna_spatial_integration_stub.flag"))
    (rr / flag_rel.replace("/", os.sep)).write_text("ok\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
