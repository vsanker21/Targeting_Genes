#!/usr/bin/env python3
"""
Outline M3: TOIL Welch and OLS bulk DEA checklist vs TOIL TPM hub slice stub.

Config: config/m3_repo_bulk_welch_ols_dea_outline_inputs.yaml — m3_repo_bulk_welch_ols_dea_integration_stub
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
    p = repo_root() / "config" / "m3_repo_bulk_welch_ols_dea_outline_inputs.yaml"
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
    block = doc.get("m3_repo_bulk_welch_ols_dea_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_bulk_welch_ols_dea_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_repo_bulk_welch_ols_dea_paths_status.json") or {}
    toil_hub = _read_json(rr, "results/module3/m3_repo_toil_bulk_expression_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_repo_bulk_welch_ols_dea_paths_status.json "
            "(run m3_repo_bulk_welch_ols_dea_paths_status)"
        )

    g = _group(paths_doc, "toil_bulk_welch_ols_dea_outputs")
    n_ok = _n_ok(g)
    n_chk = int(g.get("n_checks") or 0)
    ch: list[dict[str, Any]] = list(g.get("checks") or [])

    readiness_tier = "D"
    if n_ok >= 4:
        readiness_tier = "B"
    elif n_ok >= 2:
        readiness_tier = "B"
    elif n_ok >= 1:
        readiness_tier = "C"
    elif toil_hub:
        readiness_tier = "C"

    hub_echo: dict[str, Any] = {}
    if toil_hub:
        hub_echo = {"readiness_tier": toil_hub.get("readiness_tier"), "artifact_kind": toil_hub.get("artifact_kind")}

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_repo_bulk_welch_ols_dea_integration_stub",
        "note": "Downstream of toil_gbm_vs_brain TPM; feeds DepMap, MutSig, STRING, LINCS Entrez exports.",
        "paths_status_echo": {
            "toil_bulk_welch_ols_dea_outputs": {"n_existing": n_ok, "n_checks": n_chk},
            "repo_root": paths_doc.get("repo_root"),
        },
        "m3_repo_toil_bulk_expression_stub_echo": hub_echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Welch and OLS TSVs plus both provenance JSONs, or at least both DEA TSVs.",
            "C": "Partial outputs or TOIL bulk hub integration stub echo only.",
            "D": "No DEA artifacts and no TOIL hub stub echo.",
        },
        "checklist": {
            "welch_dea_tsv": bool(len(ch) > 0 and ch[0].get("exists")),
            "ols_dea_tsv": bool(len(ch) > 1 and ch[1].get("exists")),
            "welch_provenance_json": bool(len(ch) > 2 and ch[2].get("exists")),
            "ols_provenance_json": bool(len(ch) > 3 and ch[3].get("exists")),
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Run dea_gbm_vs_gtex_brain Snakemake rules after TOIL TPM parquet exists.",
            "Keep columns aligned with scripts/dea_string_filters.py and export_module5_lincs_disease_signature.py.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
