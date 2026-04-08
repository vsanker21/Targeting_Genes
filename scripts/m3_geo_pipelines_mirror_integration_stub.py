#!/usr/bin/env python3
"""
Outline M3: GEO + pipelines mirror checklist (no downloads, no pipelines execution).

Reads m3_geo_pipelines_mirror_paths_status.json and scrna_spatial_integration_stub.json when present.

Config: config/m3_geo_pipelines_mirror_outline_inputs.yaml — m3_geo_pipelines_mirror_integration_stub
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
    p = repo_root() / "config" / "m3_geo_pipelines_mirror_outline_inputs.yaml"
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
    block = doc.get("m3_geo_pipelines_mirror_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_geo_pipelines_mirror_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_geo_pipelines_mirror_paths_status.json") or {}
    scrna = _read_json(rr, "results/module3/scrna_spatial_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_geo_pipelines_mirror_paths_status.json (run m3_geo_pipelines_mirror_paths_status)"
        )

    g_scrna = _group(paths_doc, "geo_scrna_seq_mirror")
    g_pipe = _group(paths_doc, "pipelines_git_clones_mirror")
    geo_total = sum(_n_ok(_group(paths_doc, gid)) for gid in (
        "geo_epigenetic_mirror",
        "geo_external_validation_mirror",
        "geo_scrna_seq_mirror",
        "geo_spatial_mirror",
        "geo_bulk_microarray_mirror",
    ))
    pipe_n = _n_ok(g_pipe)
    scrna_n = _n_ok(g_scrna)

    readiness_tier = "D"
    if geo_total >= 4 and pipe_n >= 2:
        readiness_tier = "B"
    elif geo_total >= 2 or pipe_n >= 2:
        readiness_tier = "B"
    elif geo_total >= 1 or pipe_n >= 1:
        readiness_tier = "C"
    elif scrna:
        readiness_tier = "C"

    echo: dict[str, Any] = {}
    if scrna:
        echo = {"readiness_tier": scrna.get("readiness_tier"), "artifact_kind": scrna.get("artifact_kind")}

    paths_echo = {
        gid: {"n_existing": _n_ok(_group(paths_doc, gid)), "n_checks": int(_group(paths_doc, gid).get("n_checks") or 0)}
        for gid in (
            "geo_epigenetic_mirror",
            "geo_external_validation_mirror",
            "geo_scrna_seq_mirror",
            "geo_spatial_mirror",
            "geo_bulk_microarray_mirror",
            "pipelines_git_clones_mirror",
        )
    }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_geo_pipelines_mirror_integration_stub",
        "note": "Checklist only; mirror GEO with download_external_datasets or manual staging; clone nf-core repos under data_root/pipelines.",
        "paths_status_echo": {"per_group": paths_echo, "geo_total_existing": geo_total, "data_root": paths_doc.get("data_root")},
        "scrna_spatial_stub_echo": echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Several GEO roots and/or multiple pipeline clone dirs present.",
            "C": "At least one GEO or pipeline path, or scRNA/spatial integration stub only.",
            "D": "No staging paths and no stub echo.",
        },
        "checklist": {
            "any_geo_series_root": geo_total > 0,
            "any_pipeline_clone": pipe_n > 0,
            "gse57872_geo_path": scrna_n > 0,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Populate data_root/geo/... per data_sources.yaml geo: keys for studies you need.",
            "Shallow-clone nf-core pipelines and cmapPy under data_root/pipelines per data_sources.yaml pipelines:.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m3_geo_pipelines_mirror_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m3_geo_pipelines_mirror_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
