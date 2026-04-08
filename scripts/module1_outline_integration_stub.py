#!/usr/bin/env python3
"""
Outline M1: gap checklist for FASTQ reprocessing, external cohorts, harmonized multi-omics.

Reads m1_outline_paths_status.json and ComBat-Seq provenance when present. No nf-core or
ingestion jobs are run.

Config: config/m1_outline_inputs.yaml — m1_outline_integration_stub
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
    p = repo_root() / "config" / "m1_outline_inputs.yaml"
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
    block = doc.get("m1_outline_integration_stub") or {}
    if not block.get("enabled", True):
        print("m1_outline_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m1_outline_paths_status.json") or {}
    combat = _read_json(rr, "results/module1/combat_seq_tcga_gbm_primary/combat_seq_provenance.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append("Missing results/module3/m1_outline_paths_status.json (run m1_outline_paths_status)")

    ext = _group(paths_doc, "external_cohorts") or {}
    fastq = _group(paths_doc, "fastq_reprocessing") or {}
    hom = _group(paths_doc, "harmonized_multi_omics") or {}

    def n_ok(g: dict[str, Any]) -> int:
        return int(g.get("n_existing") or 0)

    ext_ok = n_ok(ext) > 0
    fastq_ok = n_ok(fastq) > 0
    hom_ok = n_ok(hom) > 0

    readiness_tier = "D"
    if hom_ok and ext_ok:
        readiness_tier = "B"
    elif hom_ok or ext_ok or fastq_ok:
        readiness_tier = "C"
    elif combat:
        readiness_tier = "C"
    elif paths_doc.get("groups"):
        readiness_tier = "D"

    checklist: dict[str, Any] = {
        "combat_seq_tcga_primary_counts": combat is not None,
        "external_cohort_paths_staged": ext_ok,
        "fastq_or_nfcore_work_staged": fastq_ok,
        "harmonized_multi_omics_staging": hom_ok,
        "harmony_scrna_batch_correction": False,
        "full_star_salmon_from_fastq_pipeline": False,
        "automated_cgga_cptac_cbttc_ingest": False,
        "note": "ComBat-Seq on GDC STAR counts is the in-repo M1 partial; remaining bullets need HPC, credentials, and parsers.",
    }

    recommended: list[str] = [
        "Populate data_root subdirs in config/m1_outline_inputs.yaml when downloads are licensed and available.",
        "Keep GLIOMA_TARGET_DATA_ROOT aligned with config/data_sources.yaml for CI and multi-machine clones.",
        "Wire nf-core/rnaseq or STAR-only Snakemake modules only after FASTQ staging and reference indices are pinned.",
    ]

    out = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 1,
        "artifact_kind": "m1_outline_integration_stub",
        "note": "Planning artifact; no FASTQ alignment, nf-core, or portal API calls.",
        "paths_status_echo": {
            "n_groups": len(paths_doc.get("groups") or []),
            "data_root": paths_doc.get("data_root"),
        },
        "combat_seq_provenance_present": combat is not None,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "harmonized multi-omics + at least one external cohort path present",
            "C": "partial staging or ComBat-Seq provenance only",
            "D": "no staged paths and no combat provenance",
        },
        "m1_outline_checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": recommended,
    }

    out_rel = str(block.get("output_json", "results/module3/m1_outline_integration_stub.json"))
    out_path = rr / out_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")

    flag_rel = str(block.get("done_flag", "results/module3/m1_outline_integration_stub.flag"))
    (rr / flag_rel.replace("/", os.sep)).write_text("ok\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
