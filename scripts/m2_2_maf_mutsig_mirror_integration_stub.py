#!/usr/bin/env python3
"""
Outline M2.2: MAF + MutSig mirror staging checklist (no MAF/MutSig jobs).

Reads m2_2_maf_mutsig_mirror_paths_status.json, maf_annotation_integration_stub.json,
and optional tcga_maf_layer / mutsig join provenance when on disk.

Config: config/m2_2_maf_mutsig_mirror_outline_inputs.yaml (m2_2_maf_mutsig_mirror_integration_stub).
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
    p = repo_root() / "config" / "m2_2_maf_mutsig_mirror_outline_inputs.yaml"
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
    block = doc.get("m2_2_maf_mutsig_mirror_integration_stub") or {}
    if not block.get("enabled", True):
        print("m2_2_maf_mutsig_mirror_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m2_2_maf_mutsig_mirror_paths_status.json") or {}
    maf_stub = _read_json(rr, "results/module3/maf_annotation_integration_stub.json")
    maf_layer_prov = _read_json(rr, "results/module3/tcga_maf_layer_provenance.json")
    mutsig_prov = _read_json(rr, "results/module3/mutsig_join_provenance.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m2_2_maf_mutsig_mirror_paths_status.json (run m2_2_maf_mutsig_mirror_paths_status)"
        )

    g_maf = _group(paths_doc, "tcga_maf_bulk_mirror") or {}
    g_ms = _group(paths_doc, "mutsig_gene_level_mirror") or {}

    maf_staged = _n_ok(g_maf) > 0
    mutsig_staged = _n_ok(g_ms) > 0
    maf_layer_ran = maf_layer_prov is not None
    mutsig_join_ran = mutsig_prov is not None

    readiness_tier = "D"
    if maf_staged and mutsig_staged:
        readiness_tier = "B"
    elif maf_staged or mutsig_staged:
        readiness_tier = "C"
    elif maf_layer_ran or mutsig_join_ran:
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
        "artifact_kind": "m2_2_maf_mutsig_mirror_integration_stub",
        "note": "Checklist only; point tcga_mutation_layer.yaml and mutsig_merge.yaml at mirrored files.",
        "paths_status_echo": {
            "tcga_maf_bulk_mirror": {"n_existing": _n_ok(g_maf), "n_checks": int(g_maf.get("n_checks") or 0)},
            "mutsig_gene_level_mirror": {"n_existing": _n_ok(g_ms), "n_checks": int(g_ms.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "in_repo_tcga_maf_layer_provenance": maf_layer_ran,
        "in_repo_mutsig_join_provenance": mutsig_join_ran,
        "maf_annotation_stub_echo": maf_echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Both MAF and MutSig mirror trees show at least one existing path.",
            "C": "One mirror dimension, in-repo MAF/MutSig join provenance, or MAF annotation stub only.",
            "D": "No mirror paths and no provenance or stub echo.",
        },
        "checklist": {
            "tcga_maf_mirror_staged": maf_staged,
            "mutsig_output_mirror_staged": mutsig_staged,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Set maf_glob in config/tcga_mutation_layer.yaml to files under data_root/mutations/tcga_gbm_maf_staging.",
            "Set mutsig_gene_tsv in config/mutsig_merge.yaml to a gene table under mutations/mutsig2cv_gene_outputs.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m2_2_maf_mutsig_mirror_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m2_2_maf_mutsig_mirror_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
