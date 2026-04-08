#!/usr/bin/env python3
"""
Outline M4: KEGG and Reactome mirror checklist (no pathway enrichment execution).

Reads m4_pathway_database_mirror_paths_status.json and m4_gsea_mirror_integration_stub.json when present.

Config: config/m4_pathway_database_mirror_outline_inputs.yaml (m4_pathway_database_mirror_integration_stub).
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
    p = repo_root() / "config" / "m4_pathway_database_mirror_outline_inputs.yaml"
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


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("m4_pathway_database_mirror_integration_stub") or {}
    if not block.get("enabled", True):
        print("m4_pathway_database_mirror_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module4/m4_pathway_database_mirror_paths_status.json") or {}
    gsea_stub = _read_json(rr, "results/module4/m4_gsea_mirror_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module4/m4_pathway_database_mirror_paths_status.json "
            "(run m4_pathway_database_mirror_paths_status)"
        )

    g_k = _group(paths_doc, "kegg_pathway_mirror")
    g_r = _group(paths_doc, "reactome_pathway_mirror")
    g_sup = _group(paths_doc, "supplementary_open_pathway_gmts")
    nk = _n_ok(g_k)
    nr = _n_ok(g_r)
    nsup = _n_ok(g_sup)

    readiness_tier = "D"
    if nk >= 1 and nr >= 1:
        readiness_tier = "B"
    elif nk >= 1 or nr >= 1:
        readiness_tier = "C"
    elif gsea_stub:
        readiness_tier = "C"

    gsea_echo: dict[str, Any] = {}
    if gsea_stub:
        gsea_echo = {
            "readiness_tier": gsea_stub.get("readiness_tier"),
            "artifact_kind": gsea_stub.get("artifact_kind"),
        }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_section": "M4",
        "artifact_kind": "m4_pathway_database_mirror_integration_stub",
        "note": "Checklist only; pair mirrors with results/module4/gsea/*.rnk and MSigDB GMT staging from m4_gsea_mirror.",
        "paths_status_echo": {
            "kegg_pathway_mirror": {"n_existing": nk, "n_checks": int(g_k.get("n_checks") or 0)},
            "reactome_pathway_mirror": {"n_existing": nr, "n_checks": int(g_r.get("n_checks") or 0)},
            "supplementary_open_pathway_gmts": {
                "n_existing": nsup,
                "n_checks": int(g_sup.get("n_checks") or 0),
            },
            "data_root": paths_doc.get("data_root"),
        },
        "m4_gsea_mirror_stub_echo": gsea_echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "At least one KEGG and one Reactome staging path present.",
            "C": "Only KEGG or only Reactome paths, or GSEA mirror stub echo only.",
            "D": "No pathway mirrors and no GSEA mirror stub echo.",
        },
        "checklist": {
            "kegg_mirror_partial_or_complete": nk > 0,
            "reactome_mirror_partial_or_complete": nr > 0,
            "supplementary_wikipathways_and_pathwaycommons_gmts": nsup >= 2,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Mirror KEGG and Reactome releases under data_root/pathways respecting each database license.",
            "Use m4_gsea_mirror for MSigDB GMTs and fgsea or GSEA output trees.",
            "Optional: run download_supplementary_reference_resources.py for WikiPathways + PathwayCommons GMTs under references/pathways/.",
        ],
    }

    out_rel = str(
        block.get("output_json", "results/module4/m4_pathway_database_mirror_integration_stub.json")
    )
    flag_rel = str(
        block.get("done_flag", "results/module4/m4_pathway_database_mirror_integration_stub.flag")
    )
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
