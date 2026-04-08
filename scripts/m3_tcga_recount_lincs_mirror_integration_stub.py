#!/usr/bin/env python3
"""
Outline M3: TCGA layout + recount3 + LINCS root checklist (no downloads).

Reads m3_tcga_recount_lincs_mirror_paths_status.json and m1_reference_gdc_integration_stub.json when present.

Config: config/m3_tcga_recount_lincs_mirror_outline_inputs.yaml — m3_tcga_recount_lincs_mirror_integration_stub
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
    p = repo_root() / "config" / "m3_tcga_recount_lincs_mirror_outline_inputs.yaml"
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
    block = doc.get("m3_tcga_recount_lincs_mirror_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_tcga_recount_lincs_mirror_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_tcga_recount_lincs_mirror_paths_status.json") or {}
    m1rg = _read_json(rr, "results/module3/m1_reference_gdc_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_tcga_recount_lincs_mirror_paths_status.json "
            "(run m3_tcga_recount_lincs_mirror_paths_status)"
        )

    g_tcga = _group(paths_doc, "tcga_gbm_uuid_case_layout")
    g_r3 = _group(paths_doc, "recount3_harmonized_g029_cache")
    g_lincs = _group(paths_doc, "lincs_clue_api_subset_root")
    total_ok = _n_ok(g_tcga) + _n_ok(g_r3) + _n_ok(g_lincs)

    readiness_tier = "D"
    if total_ok >= 3:
        readiness_tier = "B"
    elif total_ok >= 2:
        readiness_tier = "B"
    elif total_ok >= 1:
        readiness_tier = "C"
    elif m1rg:
        readiness_tier = "C"

    m1_echo: dict[str, Any] = {}
    if m1rg:
        m1_echo = {"readiness_tier": m1rg.get("readiness_tier"), "artifact_kind": m1rg.get("artifact_kind")}

    paths_echo = {
        gid: {"n_existing": _n_ok(_group(paths_doc, gid)), "n_checks": int(_group(paths_doc, gid).get("n_checks") or 0)}
        for gid in (
            "tcga_gbm_uuid_case_layout",
            "recount3_harmonized_g029_cache",
            "lincs_clue_api_subset_root",
        )
    }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_tcga_recount_lincs_mirror_integration_stub",
        "note": "Checklist only; stage TCGA cases, recount3 cache, and CLUE dumps with external tools.",
        "paths_status_echo": {"per_group": paths_echo, "total_existing": total_ok, "data_root": paths_doc.get("data_root")},
        "m1_reference_gdc_stub_echo": m1_echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Two or more companion roots present (TCGA cases, recount3, and/or LINCS).",
            "C": "One root present, or M1 reference/GDC integration stub echo only.",
            "D": "No paths staged and no M1 reference/GDC stub echo.",
        },
        "checklist": {
            "tcga_gbm_case_tree": _n_ok(g_tcga) > 0,
            "recount3_harmonized_g029": _n_ok(g_r3) > 0,
            "lincs_clue_api_subset": _n_ok(g_lincs) > 0,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Align folders with config/data_sources.yaml keys tcga_gbm, recount3, lincs.",
            "Use m1_reference_gdc and m2_1_recount3 mirror outlines for detailed STAR and recount3 staging.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m3_tcga_recount_lincs_mirror_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m3_tcga_recount_lincs_mirror_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
