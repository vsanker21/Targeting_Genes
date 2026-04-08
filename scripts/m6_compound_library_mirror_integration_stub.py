#!/usr/bin/env python3
"""
Outline M6 compound or ligand library mirror checklist (no ligand prep or docking).

Reads m6_compound_library_mirror_paths_status.json and structure_admet_integration_stub.json when present.

Config: config/m6_compound_library_mirror_outline_inputs.yaml (m6_compound_library_mirror_integration_stub).
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
    p = repo_root() / "config" / "m6_compound_library_mirror_outline_inputs.yaml"
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
    block = doc.get("m6_compound_library_mirror_integration_stub") or {}
    if not block.get("enabled", True):
        print("m6_compound_library_mirror_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module6/m6_compound_library_mirror_paths_status.json") or {}
    admet_stub = _read_json(rr, "results/module6/structure_admet_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module6/m6_compound_library_mirror_paths_status.json (run m6_compound_library_mirror_paths_status)"
        )

    g_chem = _group(paths_doc, "chembl_pubchem_staging") or {}
    g_lib = _group(paths_doc, "docking_ready_ligand_sets") or {}

    chem_ok = _n_ok(g_chem) > 0
    lib_ok = _n_ok(g_lib) > 0

    readiness_tier = "D"
    if chem_ok and lib_ok:
        readiness_tier = "B"
    elif chem_ok or lib_ok:
        readiness_tier = "C"
    elif admet_stub:
        readiness_tier = "C"

    echo: dict[str, Any] = {}
    if admet_stub:
        echo = {
            "readiness_tier": admet_stub.get("readiness_tier"),
            "artifact_kind": admet_stub.get("artifact_kind"),
        }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 6,
        "artifact_kind": "m6_compound_library_mirror_integration_stub",
        "note": "Checklist only; point GNINA or Glide at data_root/compounds/docking_ready_ligand_library after external prep.",
        "paths_status_echo": {
            "chembl_pubchem_staging": {"n_existing": _n_ok(g_chem), "n_checks": int(g_chem.get("n_checks") or 0)},
            "docking_ready_ligand_sets": {"n_existing": _n_ok(g_lib), "n_checks": int(g_lib.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "structure_admet_integration_stub_echo": echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Both identifier or SDF mirror and docking-ready ligand staging show at least one path.",
            "C": "One mirror dimension or structure or ADMET gap stub echo only.",
            "D": "No mirror paths and no ADMET stub echo.",
        },
        "checklist": {
            "chembl_or_pubchem_mirror_staged": chem_ok,
            "docking_ready_ligand_library_staged": lib_ok,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Download or subset ChEMBL or PubChem into data_root/compounds/chembl_or_vendor_sdf_mirror.",
            "Run Open Babel or RDKit externally to build PDBQT or SDF libraries under docking_ready_ligand_library.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module6/m6_compound_library_mirror_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module6/m6_compound_library_mirror_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
