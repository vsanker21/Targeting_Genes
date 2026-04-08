#!/usr/bin/env python3
"""
Outline M1 batch-corrected expression mirror checklist (no ComBat or Harmony execution).

Reads m1_batch_correction_mirror_paths_status.json, m1_harmony_batch_integration_stub.json when present,
and combat_seq_tcga_gbm.yaml in-repo job provenance when the output file exists.

Config: config/m1_batch_correction_mirror_outline_inputs.yaml (m1_batch_correction_mirror_integration_stub).
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
    p = repo_root() / "config" / "m1_batch_correction_mirror_outline_inputs.yaml"
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
    block = doc.get("m1_batch_correction_mirror_integration_stub") or {}
    if not block.get("enabled", True):
        print("m1_batch_correction_mirror_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m1_batch_correction_mirror_paths_status.json") or {}
    harm_stub = _read_json(rr, "results/module3/m1_harmony_batch_integration_stub.json")

    combat_doc = yaml.safe_load((rr / "config" / "combat_seq_tcga_gbm.yaml").read_text(encoding="utf-8-sig"))
    cblock = (combat_doc.get("combat_seq_tcga_gbm_primary") or {}) if combat_doc else {}
    out_dir = str(cblock.get("output_dir", "results/module1/combat_seq_tcga_gbm_primary")).rstrip("/")
    prov_name = str(cblock.get("output_provenance", "combat_seq_provenance.json"))
    combat_prov = rr / out_dir.replace("/", os.sep) / prov_name
    in_repo_combat_prov = combat_prov.is_file()

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m1_batch_correction_mirror_paths_status.json (run m1_batch_correction_mirror_paths_status)"
        )

    g_combat = _group(paths_doc, "combat_seq_or_limma_staging") or {}
    g_cross = _group(paths_doc, "cross_cohort_integrated_counts") or {}

    combat_mirror_ok = _n_ok(g_combat) > 0
    cross_ok = _n_ok(g_cross) > 0

    readiness_tier = "D"
    if combat_mirror_ok and cross_ok:
        readiness_tier = "B"
    elif combat_mirror_ok or cross_ok:
        readiness_tier = "C"
    elif in_repo_combat_prov:
        readiness_tier = "C"
    elif harm_stub:
        readiness_tier = "C"

    harm_echo: dict[str, Any] = {}
    if harm_stub:
        harm_echo = {
            "readiness_tier": harm_stub.get("readiness_tier"),
            "artifact_kind": harm_stub.get("artifact_kind"),
        }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_section": "M1",
        "artifact_kind": "m1_batch_correction_mirror_integration_stub",
        "note": "Checklist only; use combat_seq_tcga_gbm_primary Snakemake rule for in-repo ComBat-Seq stub or mirror external matrices under data_root/batch_correction/.",
        "paths_status_echo": {
            "combat_seq_or_limma_staging": {"n_existing": _n_ok(g_combat), "n_checks": int(g_combat.get("n_checks") or 0)},
            "cross_cohort_integrated_counts": {"n_existing": _n_ok(g_cross), "n_checks": int(g_cross.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "combat_seq_tcga_gbm_primary_provenance_config": str(combat_prov.relative_to(rr)).replace("\\", "/"),
        "in_repo_combat_seq_provenance_present": in_repo_combat_prov,
        "m1_harmony_batch_integration_stub_echo": harm_echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Both external ComBat or limma staging and cross-cohort harmonized count trees show at least one path.",
            "C": "One mirror dimension, in-repo combat_seq provenance JSON, or Harmony batch stub echo only.",
            "D": "No mirror paths and no in-repo combat provenance or Harmony stub echo.",
        },
        "checklist": {
            "combat_or_limma_mirror_staged": combat_mirror_ok,
            "cross_cohort_harmonized_counts_staged": cross_ok,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Run m1_combat_seq_tcga_gbm_primary when GDC STAR matrix exists, or copy adjusted matrices under data_root/batch_correction/adjusted_matrix_exports.",
            "Align with m1_harmony_batch_paths_status for scRNA- or object-level Harmony mirrors.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m1_batch_correction_mirror_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m1_batch_correction_mirror_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
