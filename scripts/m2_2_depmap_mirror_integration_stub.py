#!/usr/bin/env python3
"""
Outline M2.2: DepMap data mirror staging checklist (no DepMap API).

Reads m2_2_depmap_mirror_paths_status.json, maf_annotation_integration_stub.json, and in-repo DepMap join provenance when present.

Config: config/m2_2_depmap_mirror_outline_inputs.yaml — m2_2_depmap_mirror_integration_stub
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
    p = repo_root() / "config" / "m2_2_depmap_mirror_outline_inputs.yaml"
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
    block = doc.get("m2_2_depmap_mirror_integration_stub") or {}
    if not block.get("enabled", True):
        print("m2_2_depmap_mirror_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m2_2_depmap_mirror_paths_status.json") or {}
    maf_stub = _read_json(rr, "results/module3/maf_annotation_integration_stub.json")
    crispr_prov = _read_json(rr, "results/module3/depmap_crispr_join_provenance.json")
    somatic_prov = _read_json(rr, "results/module3/depmap_somatic_join_provenance.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m2_2_depmap_mirror_paths_status.json (run m2_2_depmap_mirror_paths_status)"
        )

    g_tree = _group(paths_doc, "depmap_public_release_tree") or {}
    g_crispr = _group(paths_doc, "depmap_crispr_and_dependency") or {}
    g_omics = _group(paths_doc, "depmap_omics_and_models") or {}

    tree_ok = _n_ok(g_tree) > 0
    crispr_aux_ok = _n_ok(g_crispr) > 0
    omics_ok = _n_ok(g_omics) > 0
    in_repo_joins = crispr_prov is not None or somatic_prov is not None

    readiness_tier = "D"
    if tree_ok and (crispr_aux_ok or omics_ok or in_repo_joins):
        readiness_tier = "B"
    elif tree_ok or crispr_aux_ok or omics_ok:
        readiness_tier = "C"
    elif in_repo_joins:
        readiness_tier = "C"
    elif maf_stub:
        readiness_tier = "C"

    maf_echo: dict[str, Any] = {}
    if maf_stub:
        maf_echo = {
            "readiness_tier": maf_stub.get("readiness_tier"),
            "artifact_kind": maf_stub.get("artifact_kind"),
        }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_section": "M2.2",
        "artifact_kind": "m2_2_depmap_mirror_integration_stub",
        "note": "Checklist only; use download_all_required.py or DepMap portal for real file drops.",
        "paths_status_echo": {
            "depmap_public_release_tree": {"n_existing": _n_ok(g_tree), "n_checks": int(g_tree.get("n_checks") or 0)},
            "depmap_crispr_and_dependency": {"n_existing": _n_ok(g_crispr), "n_checks": int(g_crispr.get("n_checks") or 0)},
            "depmap_omics_and_models": {"n_existing": _n_ok(g_omics), "n_checks": int(g_omics.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "in_repo_depmap_join_provenance": {
            "crispr": crispr_prov is not None,
            "somatic": somatic_prov is not None,
        },
        "maf_annotation_stub_echo": maf_echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "depmap/ release tree plus auxiliary mirrors or in-repo DepMap join provenance.",
            "C": "Partial mirror staging, joins-only, or MAF annotation stub echo.",
            "D": "No depmap mirror paths and no join provenance echo.",
        },
        "checklist": {
            "depmap_release_or_extract_staged": tree_ok,
            "crispr_dependency_aux_staged": crispr_aux_ok,
            "omics_or_model_metadata_staged": omics_ok,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Unpack DepMap Public CSV bundles under data_root/depmap/<release>/ to match depmap_shared.latest_depmap_dir().",
            "Re-run Snakemake join_dea_depmap_* rules after mirrors update; provenance JSONs will reflect new releases.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m2_2_depmap_mirror_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m2_2_depmap_mirror_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
