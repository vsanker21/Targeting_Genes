#!/usr/bin/env python3
"""
Outline M3: Dryad spatial + SRA GSE57872 staging checklist (no downloads).

Reads m3_dryad_sra_paths_status.json and scrna_spatial_integration_stub.json when present.

Config: config/m3_dryad_sra_outline_inputs.yaml — m3_dryad_sra_integration_stub
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
    p = repo_root() / "config" / "m3_dryad_sra_outline_inputs.yaml"
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
    block = doc.get("m3_dryad_sra_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_dryad_sra_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_dryad_sra_paths_status.json") or {}
    scrna = _read_json(rr, "results/module3/scrna_spatial_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append("Missing results/module3/m3_dryad_sra_paths_status.json (run m3_dryad_sra_paths_status)")

    g_dryad = _group(paths_doc, "dryad_spatial_gbm_bundle") or {}
    g_sra = _group(paths_doc, "sra_gse57872_derived") or {}

    dryad_n = _n_ok(g_dryad)
    sra_n = _n_ok(g_sra)

    readiness_tier = "D"
    if dryad_n >= 2 and sra_n >= 1:
        readiness_tier = "B"
    elif dryad_n >= 2 or sra_n >= 2:
        readiness_tier = "B"
    elif dryad_n >= 1 or sra_n >= 1:
        readiness_tier = "C"
    elif scrna:
        readiness_tier = "C"

    echo: dict[str, Any] = {}
    if scrna:
        echo = {"readiness_tier": scrna.get("readiness_tier"), "artifact_kind": scrna.get("artifact_kind")}

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_dryad_sra_integration_stub",
        "note": "Checklist only; fetch Dryad and SRA with external tools.",
        "paths_status_echo": {
            "dryad_spatial_gbm_bundle": {"n_existing": dryad_n, "n_checks": int(g_dryad.get("n_checks") or 0)},
            "sra_gse57872_derived": {"n_existing": sra_n, "n_checks": int(g_sra.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "scrna_spatial_stub_echo": echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Multiple Dryad modality dirs and/or strong SRA staging.",
            "C": "Partial Dryad or SRA paths, or scRNA/spatial integration stub only.",
            "D": "No Dryad/SRA staging paths and no stub echo.",
        },
        "checklist": {
            "dryad_spatial_bundle_partial_or_complete": dryad_n > 0,
            "sra_gse57872_staging": sra_n > 0,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Unpack Dryad doi:10.5061/dryad.h70rxwdmj under data_root/dryad/spatial_gbm preserving modality folder names.",
            "Stage GSE57872 FASTQ or count matrices under data_root/sra/GSE57872 for alignment with geo scrna_seq paths.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m3_dryad_sra_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m3_dryad_sra_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
