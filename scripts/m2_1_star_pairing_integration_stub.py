#!/usr/bin/env python3
"""
Outline M2.1: GDC STAR + GTEx STAR paired bulk DEA gap checklist (recount3 workaround echo).

Config: config/m2_1_star_pairing_outline_inputs.yaml — m2_1_star_pairing_integration_stub
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
    p = repo_root() / "config" / "m2_1_star_pairing_outline_inputs.yaml"
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


def _n_ok(g: dict[str, Any]) -> int:
    return int(g.get("n_existing") or 0)


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("m2_1_star_pairing_integration_stub") or {}
    if not block.get("enabled", True):
        print("m2_1_star_pairing_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m2_1_star_pairing_paths_status.json") or {}
    r3_deseq2 = _read_json(rr, "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_provenance.json")
    r3_edger = _read_json(rr, "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_provenance.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m2_1_star_pairing_paths_status.json (run m2_1_star_pairing_paths_status)"
        )

    gdc = _group(paths_doc, "gdc_star_counts_mirror") or {}
    gtex = _group(paths_doc, "gtex_star_counts_mirror") or {}
    maps = _group(paths_doc, "paired_tumor_normal_maps") or {}

    gdc_ok = _n_ok(gdc) > 0
    gtex_ok = _n_ok(gtex) > 0
    maps_ok = _n_ok(maps) > 0
    n_hit = sum(1 for x in (gdc_ok, gtex_ok, maps_ok) if x)

    recount3_ok = r3_deseq2 is not None or r3_edger is not None

    readiness_tier = "D"
    if gdc_ok and gtex_ok and maps_ok:
        readiness_tier = "A"
    elif n_hit >= 2:
        readiness_tier = "B"
    elif n_hit == 1:
        readiness_tier = "C"
    elif recount3_ok:
        readiness_tier = "C"
    elif paths_doc.get("groups"):
        readiness_tier = "D"

    checklist: dict[str, Any] = {
        "gdc_star_mirror_staged": gdc_ok,
        "gtex_star_mirror_staged": gtex_ok,
        "paired_tcga_gtex_map_staged": maps_ok,
        "recount3_tcga_gbm_vs_gtex_brain_provenance_on_disk": recount3_ok,
        "true_gdc_star_plus_gtex_star_paired_deseq2_in_repo": False,
        "note": "Paired integer-count DEA in-repo uses recount3 G029 harmonized counts, not GDC+GTEx STAR file parity; see planned extension gdc_gtex_open_star_counts_api.",
    }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_section": "M2.1",
        "artifact_kind": "m2_1_star_pairing_integration_stub",
        "note": "Checklist only; no GDC downloads or STAR counting.",
        "paths_status_echo": {
            "gdc_star_counts_mirror": {"n_existing": _n_ok(gdc), "n_checks": int(gdc.get("n_checks") or 0)},
            "gtex_star_counts_mirror": {"n_existing": _n_ok(gtex), "n_checks": int(gtex.get("n_checks") or 0)},
            "paired_tumor_normal_maps": {"n_existing": _n_ok(maps), "n_checks": int(maps.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "recount3_provenance_echo": {
            "deseq2": r3_deseq2 is not None,
            "edger": r3_edger is not None,
        },
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "A": "GDC STAR mirror, GTEx STAR mirror, and pairing map all staged.",
            "B": "Two of three STAR/pairing dimensions staged.",
            "C": "One staging dimension or recount3 workaround outputs present.",
            "D": "No mirrors and no recount3 provenance echo.",
        },
        "m2_1_star_pairing_checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Mirror STAR count tables under data_root paths in m2_1_star_pairing_outline_inputs.yaml when API and storage allow.",
            "Until then, use Snakemake m2_deseq2_recount3_tcga_gbm_vs_gtex_brain / m2_edger_recount3_tcga_gbm_vs_gtex_brain for harmonized bulk DEA.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m2_1_star_pairing_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m2_1_star_pairing_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
