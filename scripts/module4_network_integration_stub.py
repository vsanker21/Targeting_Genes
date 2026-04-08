#!/usr/bin/env python3
"""
Outline M4: external WGCNA / SCENIC+ / BioGRID / SLAYER gap checklist (no network inference).

Reads m4_network_paths_status.json and optionally in-repo WGCNA hub + STRING provenance echoes.

Config: config/m4_network_outline_inputs.yaml — m4_network_integration_stub
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
    p = repo_root() / "config" / "m4_network_outline_inputs.yaml"
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
    block = doc.get("m4_network_integration_stub") or {}
    if not block.get("enabled", True):
        print("m4_network_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module4/m4_network_paths_status.json") or {}
    hub_overlap = _read_json(rr, "results/module4/wgcna_hub_gene_overlap_summary.json")
    str_prov = _read_json(rr, "results/module3/dea_string_export_provenance.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append("Missing results/module4/m4_network_paths_status.json (run m4_network_paths_status)")

    wgc = _group(paths_doc, "external_wgcna_workspace") or {}
    sc = _group(paths_doc, "scenic_plus_audit") or {}
    bio = _group(paths_doc, "biogrid_interaction_cache") or {}
    sl = _group(paths_doc, "slayer_style_pairs") or {}

    def n_ok(g: dict[str, Any]) -> int:
        return int(g.get("n_existing") or 0)

    wgc_ok = n_ok(wgc) > 0
    sc_ok = n_ok(sc) > 0
    bio_ok = n_ok(bio) > 0
    sl_ok = n_ok(sl) > 0
    n_groups_hit = sum(1 for x in (wgc_ok, sc_ok, bio_ok, sl_ok) if x)

    readiness_tier = "D"
    if n_groups_hit >= 2:
        readiness_tier = "B"
    elif n_groups_hit == 1:
        readiness_tier = "C"
    elif paths_doc.get("groups"):
        readiness_tier = "D"
    if hub_overlap and readiness_tier == "D":
        readiness_tier = "C"
    if str_prov and readiness_tier == "D":
        readiness_tier = "C"

    n_str_jobs = len((str_prov or {}).get("jobs") or [])

    checklist: dict[str, Any] = {
        "in_repo_tpm_hub_and_traits_exported": hub_overlap is not None,
        "string_gene_lists_provenance_jobs": n_str_jobs,
        "external_wgcna_workspace_staged": wgc_ok,
        "scenic_or_pyscenic_output_staged": sc_ok,
        "biogrid_or_pair_metric_cache_staged": bio_ok,
        "slayer_style_pair_tables_staged": sl_ok,
        "in_repo_wgcna_blocks_or_tom": False,
        "in_repo_scenic_regulons": False,
        "in_repo_biogrid_metrics": False,
        "in_repo_slayer_scoring": False,
        "note": "Use wgcna_hub_expr_subset*.parquet + traits TSV with external R WGCNA; STRING API fetch optional via m4_string_api_network.",
    }

    out = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 4,
        "artifact_kind": "m4_network_integration_stub",
        "note": "Checklist only; no blockwise WGCNA, regulon inference, or SLAYER computation.",
        "paths_status_echo": {
            "external_wgcna_workspace": {"n_existing": n_ok(wgc), "n_checks": int(wgc.get("n_checks") or 0)},
            "scenic_plus_audit": {"n_existing": n_ok(sc), "n_checks": int(sc.get("n_checks") or 0)},
            "biogrid_interaction_cache": {"n_existing": n_ok(bio), "n_checks": int(bio.get("n_checks") or 0)},
            "slayer_style_pairs": {"n_existing": n_ok(sl), "n_checks": int(sl.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "wgcna_hub_overlap_summary_present": hub_overlap is not None,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Two or more of the four path-check groups have at least one existing path under data_root.",
            "C": "Exactly one group staged, or only in-repo hub overlap / STRING export provenance (no external staging).",
            "D": "No external staging paths and no hub/STRING echo to upgrade tier.",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Run blockwise WGCNA in R on results/module4/wgcna_hub_expr_subset*.parquet with wgcna_hub_sample_traits*.tsv.",
            "Stage BioGRID MITAB or SLAYER pair exports under data_root/networks/ for joint analysis with DepMap CRISPR joins in M2.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module4/m4_network_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module4/m4_network_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
