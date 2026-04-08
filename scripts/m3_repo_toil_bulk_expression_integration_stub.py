#!/usr/bin/env python3
"""
Outline M3: TOIL bulk TPM hub checklist vs M2.1 Xena hub mirror stub.

Config: config/m3_repo_toil_bulk_expression_outline_inputs.yaml — m3_repo_toil_bulk_expression_integration_stub
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
    p = repo_root() / "config" / "m3_repo_toil_bulk_expression_outline_inputs.yaml"
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
    block = doc.get("m3_repo_toil_bulk_expression_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_toil_bulk_expression_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_repo_toil_bulk_expression_paths_status.json") or {}
    m2tx = _read_json(rr, "results/module3/m2_1_toil_xena_hub_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_repo_toil_bulk_expression_paths_status.json "
            "(run m3_repo_toil_bulk_expression_paths_status)"
        )

    g = _group(paths_doc, "toil_gbm_vs_brain_hub_outputs")
    n_ok = _n_ok(g)

    readiness_tier = "D"
    if n_ok >= 2:
        readiness_tier = "B"
    elif n_ok >= 1:
        readiness_tier = "C"
    elif m2tx:
        readiness_tier = "C"

    tx_echo: dict[str, Any] = {}
    if m2tx:
        tx_echo = {"readiness_tier": m2tx.get("readiness_tier"), "artifact_kind": m2tx.get("artifact_kind")}

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_repo_toil_bulk_expression_integration_stub",
        "note": "TPM parquet feeds dea_tumor_normal, stratified_dea, and Verhaak; build from Xena hub per project docs.",
        "paths_status_echo": {
            "toil_gbm_vs_brain_hub_outputs": {"n_existing": n_ok, "n_checks": int(g.get("n_checks") or 0)},
            "repo_root": paths_doc.get("repo_root"),
        },
        "m2_1_toil_xena_hub_stub_echo": tx_echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "TPM parquet and sample TSV both present.",
            "C": "Only one file, or M2.1 TOIL Xena hub integration stub echo only.",
            "D": "No hub outputs and no TOIL Xena stub echo.",
        },
        "checklist": {
            "toil_tpm_parquet": bool((g.get("checks") or [{}])[0].get("exists")),
            "toil_sample_tsv": bool(
                len(g.get("checks") or []) > 1 and (g.get("checks") or [{}, {}])[1].get("exists")
            ),
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Populate results/module3/toil_gbm_vs_brain_tpm.parquet from gtex_xena_toil hub files.",
            "Keep paths aligned with module2_integration.yaml and dea_tumor_normal.yaml expression_parquet keys.",
        ],
    }

    out_rel = str(
        block.get("output_json", "results/module3/m3_repo_toil_bulk_expression_integration_stub.json")
    )
    flag_rel = str(block.get("done_flag", "results/module3/m3_repo_toil_bulk_expression_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
