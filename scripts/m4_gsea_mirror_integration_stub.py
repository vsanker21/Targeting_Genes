#!/usr/bin/env python3
"""
Outline M4: GSEA or MSigDB mirror staging checklist (no fgsea or GSEA execution).

Reads m4_gsea_mirror_paths_status.json, optional gsea_prerank_export provenance from module2_integration.yaml,
and m4_string_cache_integration_stub.json when present.

Config: config/m4_gsea_mirror_outline_inputs.yaml (m4_gsea_mirror_integration_stub).
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
    p = repo_root() / "config" / "m4_gsea_mirror_outline_inputs.yaml"
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
    block = doc.get("m4_gsea_mirror_integration_stub") or {}
    if not block.get("enabled", True):
        print("m4_gsea_mirror_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module4/m4_gsea_mirror_paths_status.json") or {}
    str_stub = _read_json(rr, "results/module4/m4_string_cache_integration_stub.json")

    integ = yaml.safe_load((rr / "config" / "module2_integration.yaml").read_text(encoding="utf-8-sig"))
    gsea_block = (integ.get("gsea_prerank_export") or {}) if integ else {}
    prov_rel = str(gsea_block.get("aggregate_provenance_json", "results/module4/gsea_prerank_export_provenance.json"))
    prov_path = rr / prov_rel.replace("/", os.sep)
    in_repo_gsea_prov = prov_path.is_file()

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module4/m4_gsea_mirror_paths_status.json (run m4_gsea_mirror_paths_status)"
        )

    g_msig = _group(paths_doc, "msigdb_gene_set_mirror") or {}
    g_ext = _group(paths_doc, "external_prerank_and_enrichment") or {}

    msig_ok = _n_ok(g_msig) > 0
    ext_ok = _n_ok(g_ext) > 0

    readiness_tier = "D"
    if msig_ok and ext_ok:
        readiness_tier = "B"
    elif msig_ok or ext_ok:
        readiness_tier = "C"
    elif in_repo_gsea_prov:
        readiness_tier = "C"
    elif str_stub:
        readiness_tier = "C"

    str_echo: dict[str, Any] = {}
    if str_stub:
        str_echo = {
            "readiness_tier": str_stub.get("readiness_tier"),
            "artifact_kind": str_stub.get("artifact_kind"),
        }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_section": "M4",
        "artifact_kind": "m4_gsea_mirror_integration_stub",
        "note": "Checklist only; point local fgsea or GSEADesktop at data_root mirrors and in-repo .rnk under results/module4/gsea/.",
        "paths_status_echo": {
            "msigdb_gene_set_mirror": {"n_existing": _n_ok(g_msig), "n_checks": int(g_msig.get("n_checks") or 0)},
            "external_prerank_and_enrichment": {"n_existing": _n_ok(g_ext), "n_checks": int(g_ext.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "gsea_prerank_aggregate_provenance_config": prov_rel,
        "in_repo_gsea_prerank_provenance_present": in_repo_gsea_prov,
        "m4_string_cache_stub_echo": str_echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Both MSigDB or GMT mirror and external prerank or enrichment staging show at least one path.",
            "C": "One mirror dimension, in-repo gsea prerank provenance JSON, or STRING cache stub echo only.",
            "D": "No mirror paths and no in-repo prerank provenance or STRING cache stub.",
        },
        "checklist": {
            "msigdb_or_gmt_mirror_staged": msig_ok,
            "external_prerank_or_enrichment_staged": ext_ok,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Run export_dea_gsea_prerank_rnk.py via Snakemake to populate results/module4/gsea/*.rnk.",
            "Mirror MSigDB GMTs under data_root/gsea/msigdb_gmt_mirror for offline fgsea or GSEA.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module4/m4_gsea_mirror_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module4/m4_gsea_mirror_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
