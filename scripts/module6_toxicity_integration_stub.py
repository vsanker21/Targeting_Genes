#!/usr/bin/env python3
"""
Outline M6: CNS / off-tumor / organ toxicity staging gap checklist (no assays).

Reads m6_toxicity_paths_status.json and echoes structure_admet_integration_stub when present.

Config: config/m6_toxicity_outline_inputs.yaml — m6_toxicity_integration_stub
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
    p = repo_root() / "config" / "m6_toxicity_outline_inputs.yaml"
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


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("m6_toxicity_integration_stub") or {}
    if not block.get("enabled", True):
        print("m6_toxicity_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module6/m6_toxicity_paths_status.json") or {}
    admet_stub = _read_json(rr, "results/module6/structure_admet_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append("Missing results/module6/m6_toxicity_paths_status.json (run m6_toxicity_paths_status)")

    cns = _group(paths_doc, "cns_penetration_safety") or {}
    off_tumor = _group(paths_doc, "off_tumor_expression_reference") or {}
    organ = _group(paths_doc, "organ_toxicity_panels") or {}
    admet_exp = _group(paths_doc, "computational_admet_exports") or {}

    def n_ok(g: dict[str, Any]) -> int:
        return int(g.get("n_existing") or 0)

    cns_ok = n_ok(cns) > 0
    off_ok = n_ok(off_tumor) > 0
    organ_ok = n_ok(organ) > 0
    admet_ok = n_ok(admet_exp) > 0
    n_groups_hit = sum(1 for x in (cns_ok, off_ok, organ_ok, admet_ok) if x)

    readiness_tier = "D"
    if cns_ok and off_ok:
        readiness_tier = "B"
    elif n_groups_hit >= 2:
        readiness_tier = "B"
    elif n_groups_hit == 1:
        readiness_tier = "C"
    elif paths_doc.get("groups"):
        readiness_tier = "D"
    if admet_stub and readiness_tier == "D":
        readiness_tier = "C"

    echo: dict[str, Any] = {}
    if admet_stub:
        echo = {
            "readiness_tier": admet_stub.get("readiness_tier"),
            "artifact_kind": admet_stub.get("artifact_kind"),
        }

    checklist: dict[str, Any] = {
        "cns_safety_or_bbb_panel_staged": cns_ok,
        "off_tumor_expression_reference_staged": off_ok,
        "organ_toxicity_pathway_panel_staged": organ_ok,
        "batch_admet_prediction_export_staged": admet_ok,
        "in_repo_tox_assays_or_ic50": False,
        "in_repo_cns_penetration_model": False,
        "note": "Join structure_druggability_bridge targets with staged panels externally; outline §6 pocket/ADMET gaps remain in structure_admet_integration_stub.",
    }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 6,
        "artifact_kind": "m6_toxicity_integration_stub",
        "note": "Checklist only; no hERG, hepatotoxicity, or BBB permeability computation in-repo.",
        "paths_status_echo": {
            "cns_penetration_safety": {"n_existing": n_ok(cns), "n_checks": int(cns.get("n_checks") or 0)},
            "off_tumor_expression_reference": {"n_existing": n_ok(off_tumor), "n_checks": int(off_tumor.get("n_checks") or 0)},
            "organ_toxicity_panels": {"n_existing": n_ok(organ), "n_checks": int(organ.get("n_checks") or 0)},
            "computational_admet_exports": {"n_existing": n_ok(admet_exp), "n_checks": int(admet_exp.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "structure_admet_stub_echo": echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "CNS safety and off-tumor expression references both staged, or two or more toxicity dimensions staged.",
            "C": "One staging dimension, or only structure/ADMET gap stub without external toxicity paths.",
            "D": "No toxicity staging paths and no ADMET stub echo.",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Curate gene-level CNS safety and off-tumor expression tables keyed to HGNC symbols matching the structure bridge.",
            "Run commercial or open ADMET batches outside the repo and stage CSVs under data_root/toxicity/admet_batch_exports.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module6/m6_toxicity_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module6/m6_toxicity_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
