#!/usr/bin/env python3
"""
Outline M3: checklist for in-repo GDC matrices vs M1 reference/GDC staging stub.

Config: config/m3_repo_gdc_expression_matrix_outline_inputs.yaml — m3_repo_gdc_expression_matrix_integration_stub
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
    p = repo_root() / "config" / "m3_repo_gdc_expression_matrix_outline_inputs.yaml"
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


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("m3_repo_gdc_expression_matrix_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_gdc_expression_matrix_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_repo_gdc_expression_matrix_paths_status.json") or {}
    m1rg = _read_json(rr, "results/module3/m1_reference_gdc_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_repo_gdc_expression_matrix_paths_status.json "
            "(run m3_repo_gdc_expression_matrix_paths_status)"
        )

    g_mat = _group(paths_doc, "gdc_repo_expression_matrices")
    g_comp = _group(paths_doc, "gdc_repo_matrix_companion")
    n_mat = _n_ok(g_mat)
    n_comp = _n_ok(g_comp)
    total = n_mat + n_comp

    readiness_tier = "D"
    if n_mat >= 2 and n_comp >= 1:
        readiness_tier = "B"
    elif n_mat >= 2:
        readiness_tier = "B"
    elif n_mat >= 1 or n_comp >= 1:
        readiness_tier = "C"
    elif m1rg:
        readiness_tier = "C"

    m1_echo: dict[str, Any] = {}
    if m1rg:
        m1_echo = {"readiness_tier": m1rg.get("readiness_tier"), "artifact_kind": m1rg.get("artifact_kind")}

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_repo_gdc_expression_matrix_integration_stub",
        "note": "Parquet matrices enable TCGA-internal DEA rules; raw counts TSVs live under data_root per m1_reference_gdc.",
        "paths_status_echo": {
            "gdc_repo_expression_matrices": {"n_existing": n_mat, "n_checks": int(g_mat.get("n_checks") or 0)},
            "gdc_repo_matrix_companion": {"n_existing": n_comp, "n_checks": int(g_comp.get("n_checks") or 0)},
            "total_existing": total,
            "repo_root": paths_doc.get("repo_root"),
        },
        "m1_reference_gdc_stub_echo": m1_echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Both TPM and counts parquets present; ideally sample meta or QC JSON too.",
            "C": "Partial matrices or companions, or M1 reference/GDC stub echo only.",
            "D": "No built matrices on disk and no M1 stub echo.",
        },
        "checklist": {
            "tpm_and_counts_parquets": n_mat >= 2,
            "sample_meta_or_qc": n_comp > 0,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Run build_gdc_gbm_expression_matrix and validate_gdc_counts_matrix per README after staging STAR TSVs.",
            "Align gene IDs with references/hgnc and module2_integration.yaml.",
        ],
    }

    out_rel = str(
        block.get("output_json", "results/module3/m3_repo_gdc_expression_matrix_integration_stub.json")
    )
    flag_rel = str(block.get("done_flag", "results/module3/m3_repo_gdc_expression_matrix_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
