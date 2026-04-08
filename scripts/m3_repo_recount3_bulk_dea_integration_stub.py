#!/usr/bin/env python3
"""
Outline M3: recount3 bulk DEA artifact checklist vs M2.1 recount3 data mirror stub.

Config: config/m3_repo_recount3_bulk_dea_outline_inputs.yaml — m3_repo_recount3_bulk_dea_integration_stub
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
    p = repo_root() / "config" / "m3_repo_recount3_bulk_dea_outline_inputs.yaml"
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
    block = doc.get("m3_repo_recount3_bulk_dea_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_recount3_bulk_dea_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_repo_recount3_bulk_dea_paths_status.json") or {}
    m2r3 = _read_json(rr, "results/module3/m2_1_recount3_mirror_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_repo_recount3_bulk_dea_paths_status.json "
            "(run m3_repo_recount3_bulk_dea_paths_status)"
        )

    g = _group(paths_doc, "recount3_gbm_vs_gtex_brain_dea_outputs")
    n_ok = _n_ok(g)
    n_chk = int(g.get("n_checks") or 0)

    readiness_tier = "D"
    if n_ok >= 4:
        readiness_tier = "B"
    elif n_ok >= 2:
        readiness_tier = "B"
    elif n_ok >= 1:
        readiness_tier = "C"
    elif m2r3:
        readiness_tier = "C"

    r3_echo: dict[str, Any] = {}
    if m2r3:
        r3_echo = {"readiness_tier": m2r3.get("readiness_tier"), "artifact_kind": m2r3.get("artifact_kind")}

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_repo_recount3_bulk_dea_integration_stub",
        "note": "Feeds module2_integration extra_dea_pairs, mutsig, MAF joins, and M5 Entrez signatures.",
        "paths_status_echo": {
            "recount3_gbm_vs_gtex_brain_dea_outputs": {"n_existing": n_ok, "n_checks": n_chk},
            "repo_root": paths_doc.get("repo_root"),
        },
        "m2_1_recount3_mirror_stub_echo": r3_echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Most or all core recount3 DEA artifacts present (TSVs, concordance, counts parquet).",
            "C": "Partial artifacts or M2.1 recount3 mirror stub echo only.",
            "D": "No DEA outputs and no recount3 mirror stub echo.",
        },
        "checklist": {
            "deseq2_and_edger_tsv": n_ok >= 2,
            "concordance_json": any(
                c.get("exists") and "concordance" in str(c.get("path", "")).lower()
                for c in (g.get("checks") or [])
            ),
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Run Snakemake m2_deseq2_recount3_tcga_gbm_vs_gtex_brain and m2_edger_recount3_* after recount3 counts matrix exists.",
            "See config/deseq2_recount3_tcga_gtex.yaml and pipeline_outline M2.1 recount3 bullet.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m3_repo_recount3_bulk_dea_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m3_repo_recount3_bulk_dea_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
