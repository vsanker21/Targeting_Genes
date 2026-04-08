#!/usr/bin/env python3
"""
Outline M3: Cell Ranger processed-output staging gap checklist (no single-cell execution).

Reads m3_cellranger_output_paths_status.json and echoes scrna_spatial_integration_stub when present.

Config: config/m3_cellranger_output_outline_inputs.yaml — m3_cellranger_output_integration_stub
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
    p = repo_root() / "config" / "m3_cellranger_output_outline_inputs.yaml"
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


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("m3_cellranger_output_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_cellranger_output_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_cellranger_output_paths_status.json") or {}
    scrna = _read_json(rr, "results/module3/scrna_spatial_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_cellranger_output_paths_status.json (run m3_cellranger_output_paths_status)"
        )

    g_count = _group(paths_doc, "cellranger_count_matrices") or {}
    g_aggr = _group(paths_doc, "cellranger_aggr_or_multi") or {}
    g_conv = _group(paths_doc, "scanpy_seurat_converted_objects") or {}

    def n_ok(g: dict[str, Any]) -> int:
        return int(g.get("n_existing") or 0)

    count_ok = n_ok(g_count) > 0
    aggr_ok = n_ok(g_aggr) > 0
    conv_ok = n_ok(g_conv) > 0

    readiness_tier = "D"
    if count_ok:
        readiness_tier = "B"
    elif aggr_ok or conv_ok:
        readiness_tier = "C"
    elif scrna:
        readiness_tier = "C"

    echo: dict[str, Any] = {}
    if scrna:
        echo = {
            "readiness_tier": scrna.get("readiness_tier"),
            "artifact_kind": scrna.get("artifact_kind"),
        }

    checklist: dict[str, Any] = {
        "cellranger_count_outs_staged": count_ok,
        "cellranger_aggr_or_spaceranger_staged": aggr_ok,
        "converted_h5ad_or_seurat_staged": conv_ok,
        "in_repo_cellranger_count": False,
        "note": "Vendor binaries: vendor_tooling_paths_status; raw GEO/SRA roots: module3_public_inputs_status.",
    }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_cellranger_output_integration_stub",
        "note": "Checklist only; no Cell Ranger, Space Ranger, or Scanpy jobs in-repo.",
        "paths_status_echo": {
            "cellranger_count_matrices": {"n_existing": n_ok(g_count), "n_checks": int(g_count.get("n_checks") or 0)},
            "cellranger_aggr_or_multi": {"n_existing": n_ok(g_aggr), "n_checks": int(g_aggr.get("n_checks") or 0)},
            "scanpy_seurat_converted_objects": {"n_existing": n_ok(g_conv), "n_checks": int(g_conv.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "scrna_spatial_stub_echo": echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "At least one cellranger count / per-library outs staging path exists.",
            "C": "Only aggr, spatial, or converted-object staging; or scRNA/spatial integration stub echo.",
            "D": "No processed-output staging paths and no useful stub echo.",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Stage `outs/` from licensed cellranger count runs under data_root/scrna/cellranger_count_outs with one folder per GEM/library.",
            "After Scanpy/Seurat QC in an external env, place merged .h5ad or RDS archives for deconvolution and pseudobulk cross-checks.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m3_cellranger_output_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m3_cellranger_output_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
