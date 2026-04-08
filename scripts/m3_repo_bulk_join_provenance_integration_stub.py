#!/usr/bin/env python3
"""
Outline M3: bulk join provenance checklist vs global DEA, DepMap mirror, and MAF/MutSig mirror stubs.

Config: config/m3_repo_bulk_join_provenance_outline_inputs.yaml — m3_repo_bulk_join_provenance_integration_stub
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
    p = repo_root() / "config" / "m3_repo_bulk_join_provenance_outline_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8-sig"))


def _read_json(rr: Path, rel: str) -> dict[str, Any] | None:
    p = rr / rel.replace("/", os.sep)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _group(paths_doc: dict[str, Any], gid: str) -> dict[str, Any]:
    for g in paths_doc.get("groups") or []:
        if str(g.get("id")) == gid:
            return g
    return {}


def _n_ok(g: dict[str, Any]) -> int:
    return int(g.get("n_existing") or 0)


def _tier_letter(doc: dict[str, Any] | None) -> str | None:
    if not doc:
        return None
    t = doc.get("readiness_tier")
    return str(t) if t is not None else None


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("m3_repo_bulk_join_provenance_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_bulk_join_provenance_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_repo_bulk_join_provenance_paths_status.json") or {}
    wel_stub = _read_json(rr, "results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.json")
    dm_stub = _read_json(rr, "results/module3/m2_2_depmap_mirror_integration_stub.json")
    mm_stub = _read_json(rr, "results/module3/m2_2_maf_mutsig_mirror_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_repo_bulk_join_provenance_paths_status.json "
            "(run m3_repo_bulk_join_provenance_paths_status)"
        )

    g = _group(paths_doc, "bulk_join_provenance_repo_outputs")
    n_ok = _n_ok(g)
    n_chk = int(g.get("n_checks") or 0)
    ch: list[dict[str, Any]] = list(g.get("checks") or [])

    wel_t = _tier_letter(wel_stub)
    dm_t = _tier_letter(dm_stub)
    mm_t = _tier_letter(mm_stub)
    parent_signal = (
        (wel_t and wel_t != "D")
        or (dm_t and dm_t != "D")
        or (mm_t and mm_t != "D")
    )

    readiness_tier = "D"
    if n_ok >= 6:
        readiness_tier = "B"
    elif n_ok >= 3:
        readiness_tier = "C"
    elif parent_signal:
        readiness_tier = "C"

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_repo_bulk_join_provenance_integration_stub",
        "note": "DEA TSVs plus data_root DepMap/MAF/MutSig mirrors; STRING export uses filtered DEA gene lists.",
        "paths_status_echo": {
            "bulk_join_provenance_repo_outputs": {"n_existing": n_ok, "n_checks": n_chk},
            "repo_root": paths_doc.get("repo_root"),
        },
        "m3_repo_bulk_welch_ols_dea_stub_echo": {
            "readiness_tier": wel_t,
            "artifact_kind": wel_stub.get("artifact_kind") if wel_stub else None,
        },
        "m2_2_depmap_mirror_stub_echo": {
            "readiness_tier": dm_t,
            "artifact_kind": dm_stub.get("artifact_kind") if dm_stub else None,
        },
        "m2_2_maf_mutsig_mirror_stub_echo": {
            "readiness_tier": mm_t,
            "artifact_kind": mm_stub.get("artifact_kind") if mm_stub else None,
        },
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "All six join and STRING export provenance JSONs present.",
            "C": "At least three provenance JSONs, or DEA / DepMap / MAF-MutSig stub shows partial readiness.",
            "D": "Fewer than three JSONs and no parent stub signal.",
        },
        "checklist": {
            "depmap_crispr_join_provenance_json": bool(len(ch) > 0 and ch[0].get("exists")),
            "depmap_somatic_join_provenance_json": bool(len(ch) > 1 and ch[1].get("exists")),
            "tcga_maf_layer_provenance_json": bool(len(ch) > 2 and ch[2].get("exists")),
            "tcga_maf_join_provenance_json": bool(len(ch) > 3 and ch[3].get("exists")),
            "mutsig_join_provenance_json": bool(len(ch) > 4 and ch[4].get("exists")),
            "dea_string_export_provenance_json": bool(len(ch) > 5 and ch[5].get("exists")),
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Run m2_depmap_join_dea and m2_depmap_somatic_join_dea after DEA TSVs and DepMap tables exist.",
            "Run m2_tcga_maf_gene_summary and m2_tcga_maf_join_dea, m2_mutsig_join_dea, then m2_dea_string_export as needed.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m3_repo_bulk_join_provenance_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m3_repo_bulk_join_provenance_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
