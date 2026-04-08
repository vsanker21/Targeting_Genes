#!/usr/bin/env python3
"""
Outline M2.1: recount3 local mirror / cache staging checklist (no download execution).

Reads m2_1_recount3_mirror_paths_status.json and echoes m2_1_star_pairing_integration_stub when present.

Config: config/m2_1_recount3_mirror_outline_inputs.yaml — m2_1_recount3_mirror_integration_stub
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
    p = repo_root() / "config" / "m2_1_recount3_mirror_outline_inputs.yaml"
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
    block = doc.get("m2_1_recount3_mirror_integration_stub") or {}
    if not block.get("enabled", True):
        print("m2_1_recount3_mirror_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m2_1_recount3_mirror_paths_status.json") or {}
    star_stub = _read_json(rr, "results/module3/m2_1_star_pairing_integration_stub.json")
    r3_deseq2 = _read_json(rr, "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_provenance.json")
    r3_edger = _read_json(rr, "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_provenance.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m2_1_recount3_mirror_paths_status.json (run m2_1_recount3_mirror_paths_status)"
        )

    g_rse = _group(paths_doc, "recount3_rse_download_cache") or {}
    g_man = _group(paths_doc, "recount3_g029_gene_manifests") or {}
    g_pq = _group(paths_doc, "recount3_parquet_or_matrix_mirror") or {}

    rse_ok = _n_ok(g_rse) > 0
    man_ok = _n_ok(g_man) > 0
    pq_ok = _n_ok(g_pq) > 0
    in_repo_dea = r3_deseq2 is not None or r3_edger is not None

    readiness_tier = "D"
    if rse_ok and (man_ok or pq_ok or in_repo_dea):
        readiness_tier = "B"
    elif rse_ok or man_ok or pq_ok:
        readiness_tier = "C"
    elif in_repo_dea:
        readiness_tier = "C"
    elif star_stub:
        readiness_tier = "C"

    echo: dict[str, Any] = {}
    if star_stub:
        echo = {
            "readiness_tier": star_stub.get("readiness_tier"),
            "artifact_kind": star_stub.get("artifact_kind"),
        }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_section": "M2.1",
        "artifact_kind": "m2_1_recount3_mirror_integration_stub",
        "note": "Checklist only; use download_recount3_harmonized_g029.py or recount3 R for real pulls.",
        "paths_status_echo": {
            "recount3_rse_download_cache": {"n_existing": _n_ok(g_rse), "n_checks": int(g_rse.get("n_checks") or 0)},
            "recount3_g029_gene_manifests": {"n_existing": _n_ok(g_man), "n_checks": int(g_man.get("n_checks") or 0)},
            "recount3_parquet_or_matrix_mirror": {"n_existing": _n_ok(g_pq), "n_checks": int(g_pq.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "in_repo_recount3_dea_provenance": in_repo_dea,
        "star_pairing_stub_echo": echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "RSE/cache staging plus manifests, parquet mirror, or in-repo recount3 DEA provenance.",
            "C": "Partial mirror staging, in-repo DEA only, or STAR pairing stub echo.",
            "D": "No mirror paths and no recount3 DEA or pairing stub echo.",
        },
        "checklist": {
            "recount3_rse_or_cache_staged": rse_ok,
            "g029_manifests_or_gene_maps_staged": man_ok,
            "harmonized_matrix_mirror_staged": pq_ok,
            "in_repo_recount3_tcga_gbm_vs_gtex_dea": in_repo_dea,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Stage recount3 downloads under data_root/recount3/rse_download_cache with project IDs documented in g029_sample_manifests.",
            "Keep STAR pairing mirrors (m2_1_star_pairing_*) separate from recount3 harmonized G029 counts used by Snakemake m2_deseq2_recount3_* .",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m2_1_recount3_mirror_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m2_1_recount3_mirror_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
