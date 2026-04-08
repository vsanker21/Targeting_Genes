#!/usr/bin/env python3
"""
Outline M4: STRING API / offline PPI cache staging gap checklist (no HTTP).

Reads m4_string_cache_paths_status.json and echoes m4_network_integration_stub when present.

Config: config/m4_string_cache_outline_inputs.yaml — m4_string_cache_integration_stub
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
    p = repo_root() / "config" / "m4_string_cache_outline_inputs.yaml"
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
    block = doc.get("m4_string_cache_integration_stub") or {}
    if not block.get("enabled", True):
        print("m4_string_cache_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module4/m4_string_cache_paths_status.json") or {}
    net_stub = _read_json(rr, "results/module4/m4_network_integration_stub.json")
    str_prov = _read_json(rr, "results/module3/dea_string_export_provenance.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append("Missing results/module4/m4_string_cache_paths_status.json (run m4_string_cache_paths_status)")

    api_c = _group(paths_doc, "string_api_response_cache") or {}
    edges = _group(paths_doc, "string_edge_list_exports") or {}
    alias = _group(paths_doc, "string_protein_alias_map") or {}
    meta = _group(paths_doc, "string_version_or_metadata") or {}

    def n_ok(g: dict[str, Any]) -> int:
        return int(g.get("n_existing") or 0)

    api_ok = n_ok(api_c) > 0
    edge_ok = n_ok(edges) > 0
    alias_ok = n_ok(alias) > 0
    meta_ok = n_ok(meta) > 0
    n_groups_hit = sum(1 for x in (api_ok, edge_ok, alias_ok, meta_ok) if x)

    readiness_tier = "D"
    if api_ok and edge_ok:
        readiness_tier = "B"
    elif n_groups_hit >= 2:
        readiness_tier = "B"
    elif n_groups_hit == 1:
        readiness_tier = "C"
    elif paths_doc.get("groups"):
        readiness_tier = "D"
    if net_stub and readiness_tier == "D":
        readiness_tier = "C"
    if str_prov and readiness_tier == "D":
        readiness_tier = "C"

    n_str_jobs = len((str_prov or {}).get("jobs") or [])

    checklist: dict[str, Any] = {
        "string_api_json_cache_staged": api_ok,
        "offline_edge_tsv_or_graphml_staged": edge_ok,
        "protein_alias_or_identifier_map_staged": alias_ok,
        "string_version_manifest_staged": meta_ok,
        "m4_string_api_network_rule_outputs_on_disk": False,
        "note": "fetch_string_network_api.py + m4_string_api_network remain the in-repo API hook; this stub tracks mirrors for air-gapped or batch replay use.",
    }

    echo: dict[str, Any] = {}
    if net_stub:
        echo = {
            "readiness_tier": net_stub.get("readiness_tier"),
            "artifact_kind": net_stub.get("artifact_kind"),
        }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 4,
        "artifact_kind": "m4_string_cache_integration_stub",
        "note": "Checklist only; no STRINGdb REST client execution from this artifact.",
        "paths_status_echo": {
            "string_api_response_cache": {"n_existing": n_ok(api_c), "n_checks": int(api_c.get("n_checks") or 0)},
            "string_edge_list_exports": {"n_existing": n_ok(edges), "n_checks": int(edges.get("n_checks") or 0)},
            "string_protein_alias_map": {"n_existing": n_ok(alias), "n_checks": int(alias.get("n_checks") or 0)},
            "string_version_or_metadata": {"n_existing": n_ok(meta), "n_checks": int(meta.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "m4_network_stub_echo": echo,
        "dea_string_export_jobs": n_str_jobs,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "API response cache and edge-list exports both staged, or two or more STRING cache dimensions.",
            "C": "One cache dimension, or only network / STRING list provenance on disk.",
            "D": "No STRING cache staging paths.",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Archive m4_string_api_network JSON outputs under data_root/networks/string_api_cache for reproducible offline joins.",
            "Pair cached edges with the same STRING version documented in module2_integration string_api_network_fetch settings.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module4/m4_string_cache_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module4/m4_string_cache_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
