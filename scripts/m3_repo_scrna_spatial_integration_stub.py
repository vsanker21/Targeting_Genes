#!/usr/bin/env python3
"""
Outline M3: scRNA/spatial outline quartet checklist vs scrna_spatial stub, deconvolution, Cell Ranger M3 stubs.

Config: config/m3_repo_scrna_spatial_outline_inputs.yaml — m3_repo_scrna_spatial_integration_stub
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
    p = repo_root() / "config" / "m3_repo_scrna_spatial_outline_inputs.yaml"
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


def _m3_deconv_integration_stub_echo_block(dec: dict[str, Any] | None) -> dict[str, Any]:
    """Tier + artifact_kind plus checklist-derived RCTD / Cell2location fields for cross-slice echo."""
    empty = {
        "readiness_tier": None,
        "artifact_kind": None,
        "in_repo_cell2location_or_rctd": None,
        "cell2location_run_status": None,
        "cell2location_has_signature_extract_diagnostic": None,
        "cell2location_has_gene_intersection_diagnostic": None,
        "rctd_run_status": None,
    }
    if not dec:
        return empty
    cl = dec.get("checklist")
    ck: dict[str, Any] = cl if isinstance(cl, dict) else {}
    return {
        "readiness_tier": dec.get("readiness_tier"),
        "artifact_kind": dec.get("artifact_kind"),
        "in_repo_cell2location_or_rctd": ck.get("in_repo_cell2location_or_rctd"),
        "cell2location_run_status": ck.get("cell2location_run_status"),
        "cell2location_has_signature_extract_diagnostic": ck.get(
            "cell2location_has_signature_extract_diagnostic"
        ),
        "cell2location_has_gene_intersection_diagnostic": ck.get(
            "cell2location_has_gene_intersection_diagnostic"
        ),
        "rctd_run_status": ck.get("rctd_run_status"),
    }


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("m3_repo_scrna_spatial_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_scrna_spatial_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_repo_scrna_spatial_paths_status.json") or {}
    scrna = _read_json(rr, "results/module3/scrna_spatial_integration_stub.json")
    dec = _read_json(rr, "results/module3/m3_deconvolution_integration_stub.json")
    cr = _read_json(rr, "results/module3/m3_cellranger_output_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_repo_scrna_spatial_paths_status.json "
            "(run m3_repo_scrna_spatial_paths_status)"
        )

    g = _group(paths_doc, "module3_scrna_spatial_repo_outline_outputs")
    n_ok = _n_ok(g)
    n_chk = int(g.get("n_checks") or 0)
    ch: list[dict[str, Any]] = list(g.get("checks") or [])

    s_t = _tier_letter(scrna)
    d_t = _tier_letter(dec)
    c_t = _tier_letter(cr)
    parent_signal = any(t and t != "D" for t in (s_t, d_t, c_t))

    readiness_tier = "D"
    if n_chk > 0 and n_ok >= n_chk:
        readiness_tier = "B"
    elif n_ok >= 2:
        readiness_tier = "C"
    elif parent_signal:
        readiness_tier = "C"

    checklist = {str(c.get("name", f"check_{i}")): bool(c.get("exists")) for i, c in enumerate(ch)}

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_repo_scrna_spatial_integration_stub",
        "note": "Cross-module M3 manifest slice for scRNA/spatial workflow JSON/flags; aligns with deconvolution and Cell Ranger outline stubs.",
        "paths_status_echo": {
            "module3_scrna_spatial_repo_outline_outputs": {"n_existing": n_ok, "n_checks": n_chk},
            "repo_root": paths_doc.get("repo_root"),
        },
        "scrna_spatial_integration_stub_echo": {
            "readiness_tier": s_t,
            "artifact_kind": scrna.get("artifact_kind") if scrna else None,
        },
        "m3_deconvolution_integration_stub_echo": _m3_deconv_integration_stub_echo_block(dec),
        "m3_cellranger_output_integration_stub_echo": {
            "readiness_tier": c_t,
            "artifact_kind": cr.get("artifact_kind") if cr else None,
        },
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "All four module3_sc_workflow + scrna_spatial outline JSON/flag paths present under results/module3.",
            "C": "At least two paths present, or scrna_spatial / deconvolution / Cell Ranger stubs show partial readiness.",
            "D": "Fewer than two paths and no parent stub signal.",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Run m3_sc_workflow_paths_status and m3_scrna_spatial_integration_stub after data_root sc/spatial trees exist.",
            "Use m3_deconvolution_paths_status and m3_cellranger_output for downstream staging vs this quartet.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m3_repo_scrna_spatial_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m3_repo_scrna_spatial_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
