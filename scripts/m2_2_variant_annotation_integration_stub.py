#!/usr/bin/env python3
"""
Outline M2.2: VEP / OncoKB / ClinVar staging gap checklist (after MAF annotation stub).

Config: config/m2_2_variant_annotation_outline_inputs.yaml — m2_2_variant_annotation_integration_stub
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
    p = repo_root() / "config" / "m2_2_variant_annotation_outline_inputs.yaml"
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


def _n_ok(g: dict[str, Any]) -> int:
    return int(g.get("n_existing") or 0)


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("m2_2_variant_annotation_integration_stub") or {}
    if not block.get("enabled", True):
        print("m2_2_variant_annotation_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m2_2_variant_annotation_paths_status.json") or {}
    maf_stub = _read_json(rr, "results/module3/maf_annotation_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m2_2_variant_annotation_paths_status.json "
            "(run m2_2_variant_annotation_paths_status)"
        )

    vep = _group(paths_doc, "vep_or_functional_annotation_outputs") or {}
    onco = _group(paths_doc, "oncokb_annotation_staging") or {}
    clin = _group(paths_doc, "clinvar_reference_staging") or {}

    vep_ok = _n_ok(vep) > 0
    onco_ok = _n_ok(onco) > 0
    clin_ok = _n_ok(clin) > 0
    n_hit = sum(1 for x in (vep_ok, onco_ok, clin_ok) if x)

    maf_check = (maf_stub or {}).get("oncokb_clinvar_checklist") or {}
    maf_on_disk = maf_stub is not None

    readiness_tier = "D"
    if vep_ok and onco_ok and clin_ok:
        readiness_tier = "A"
    elif n_hit >= 2:
        readiness_tier = "B"
    elif n_hit == 1:
        readiness_tier = "C"
    elif maf_on_disk:
        readiness_tier = "C"
    elif paths_doc.get("groups"):
        readiness_tier = "D"

    checklist: dict[str, Any] = {
        "vep_or_functional_annotation_cache_staged": vep_ok,
        "oncokb_annotation_cache_staged": onco_ok,
        "clinvar_reference_staged": clin_ok,
        "maf_annotation_integration_stub_on_disk": maf_on_disk,
        "in_repo_oncokb_or_clinvar_api_calls": False,
        "note": "Gene-level MAF summaries are in-repo; per-variant OncoKB/ClinVar need licensed tools and coordinates.",
    }

    maf_echo = None
    if maf_stub:
        maf_echo = {
            "artifact_kind": maf_stub.get("artifact_kind"),
            "oncokb_variant_annotation": maf_check.get("oncokb_variant_annotation"),
            "clinvar_variant_annotation": maf_check.get("clinvar_variant_annotation"),
        }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_section": "M2.2",
        "artifact_kind": "m2_2_variant_annotation_integration_stub",
        "note": "Planning artifact; no VEP, OncoKB, or ClinVar I/O beyond path scan.",
        "paths_status_echo": {
            "vep_or_functional_annotation_outputs": {
                "n_existing": _n_ok(vep),
                "n_checks": int(vep.get("n_checks") or 0),
            },
            "oncokb_annotation_staging": {"n_existing": _n_ok(onco), "n_checks": int(onco.get("n_checks") or 0)},
            "clinvar_reference_staging": {"n_existing": _n_ok(clin), "n_checks": int(clin.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "maf_annotation_stub_echo": maf_echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "A": "VEP/functional, OncoKB, and ClinVar staging paths all present.",
            "B": "Two of three annotation reference dimensions staged.",
            "C": "One staging dimension or MAF annotation stub only.",
            "D": "No caches staged and no MAF stub.",
        },
        "m2_2_variant_annotation_checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Populate data_root/variants/* per m2_2_variant_annotation_outline_inputs.yaml after licensing review.",
            "Run m2_maf_annotation_integration_stub first to align gene-level summaries with variant-level plans.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m2_2_variant_annotation_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m2_2_variant_annotation_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
