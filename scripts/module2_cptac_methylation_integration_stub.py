#!/usr/bin/env python3
"""
Outline M2.1: CPTAC protein concordance + methylation silencing filter gap report (no DE joins).

Reads m2_cptac_methylation_paths_status.json and summarizes blockers for matched-sample
protein/RNA concordance and promoter methylation silencing gates.

Config: config/m2_cptac_methylation_inputs.yaml — cptac_methylation_integration_stub
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
    p = repo_root() / "config" / "m2_cptac_methylation_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _read_json(rr: Path, rel: str) -> dict[str, Any] | None:
    p = rr / rel.replace("/", os.sep)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("cptac_methylation_integration_stub") or {}
    if not block.get("enabled", True):
        print("cptac_methylation_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m2_cptac_methylation_paths_status.json") or {}
    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m2_cptac_methylation_paths_status.json (run m2_cptac_methylation_paths_status)"
        )

    checks = paths_doc.get("checks") or []
    n_ok = sum(1 for c in checks if bool(c.get("exists")))
    cptac_ok = any("cptac" in str(c.get("name", "")).lower() and c.get("exists") for c in checks)
    meth_ok = any(
        ("methylation" in str(c.get("name", "")).lower() or "methyl" in str(c.get("name", "")).lower())
        and c.get("exists")
        for c in checks
    )

    readiness_tier = "D"
    if cptac_ok and meth_ok:
        readiness_tier = "B"
    elif cptac_ok or meth_ok:
        readiness_tier = "C"
    elif len(checks) > 0:
        readiness_tier = "D"

    checklist: dict[str, Any] = {
        "cptac_proteome_data_staged": cptac_ok,
        "methylation_beta_or_idat_staged": meth_ok,
        "sample_id_map_rna_protein": False,
        "protein_de_concordance_filter": False,
        "promoter_methylation_silencing_filter": False,
        "note": "Requires harmonized sample IDs, CPTAC controlled-access agreements, and matched gene symbols (HGNC) across assays.",
    }

    recommended: list[str] = [
        "Stage CPTAC PSM or protein abundance tables under data_root/cptac/ with sample IDs alignable to TCGA barcodes used in TOIL/recount3.",
        "Stage Illumina beta values or IDAT + SampleSheet under data_root/methylation/; document genome build and probe manifest.",
        "After matrices exist, add Snakemake rules for inner-join concordance (spearman protein vs RNA) and methylation gates (e.g. high beta + low RNA).",
    ]

    out = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_section": "M2.1",
        "artifact_kind": "cptac_methylation_integration_stub",
        "note": "Checklist only; no CPTAC or methylation files are read beyond path status.",
        "paths_status_echo": {
            "n_checks": len(checks),
            "n_existing": n_ok,
            "data_root": paths_doc.get("data_root"),
        },
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "both CPTAC and methylation roots present on disk",
            "C": "one of CPTAC or methylation present",
            "D": "neither present or path status missing",
        },
        "m2_1_outline_checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": recommended,
    }

    out_rel = str(block.get("output_json", "results/module3/m2_cptac_methylation_integration_stub.json"))
    out_path = rr / out_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")

    flag_rel = str(block.get("done_flag", "results/module3/m2_cptac_methylation_integration_stub.flag"))
    (rr / flag_rel.replace("/", os.sep)).write_text("ok\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
