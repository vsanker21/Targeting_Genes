#!/usr/bin/env python3
"""
Outline M3: checklist for shipped references/ vs M2.3 MOVICS gap stub (no scoring).

Config: config/m3_repo_bundled_references_outline_inputs.yaml — m3_repo_bundled_references_integration_stub
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
    p = repo_root() / "config" / "m3_repo_bundled_references_outline_inputs.yaml"
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
    block = doc.get("m3_repo_bundled_references_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_bundled_references_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_repo_bundled_references_paths_status.json") or {}
    movics = _read_json(rr, "results/module3/m2_movics_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_repo_bundled_references_paths_status.json "
            "(run m3_repo_bundled_references_paths_status)"
        )

    g = _group(paths_doc, "repo_bundled_outline_references")
    n_ok = _n_ok(g)
    n_chk = int(g.get("n_checks") or 0)

    readiness_tier = "D"
    if n_ok >= 4 or (n_ok >= 3 and n_chk >= 4):
        readiness_tier = "B"
    elif n_ok >= 2:
        readiness_tier = "C"
    elif n_ok >= 1:
        readiness_tier = "C"
    elif movics:
        readiness_tier = "C"

    movics_echo: dict[str, Any] = {}
    if movics:
        movics_echo = {"readiness_tier": movics.get("readiness_tier"), "artifact_kind": movics.get("artifact_kind")}

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_repo_bundled_references_integration_stub",
        "note": "Verhaak and outline driver inputs shipped in-repo; replace GMT paths in module2_integration.yaml if you vendor alternates.",
        "paths_status_echo": {
            "repo_bundled_outline_references": {"n_existing": n_ok, "n_checks": n_chk},
            "repo_root": paths_doc.get("repo_root"),
        },
        "m2_movics_stub_echo": movics_echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Default Verhaak GMT, alternate GMT, centroid template, and driver YAML present.",
            "C": "Partial shipped set or MOVICS stub echo only.",
            "D": "Missing paths doc and no MOVICS stub echo.",
        },
        "checklist": {
            "verhaak_default_gmt": False,
            "verhaak_centroid_template": False,
            "outline_driver_yaml": False,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Keep references/*.gmt aligned with module2_integration.yaml gbm_verhaak.msigdb_gmt.",
            "Use m2_2_outline_driver_mirror for extra driver panels under data_root/drivers.",
        ],
    }

    for c in g.get("checks") or []:
        path_s = str(c.get("path", "")).replace("\\", "/").lower()
        if not c.get("exists"):
            continue
        if "verhaak_msigdb_c2_cgp" in path_s:
            payload["checklist"]["verhaak_default_gmt"] = True
        if "verhaak_centroids_user_template" in path_s:
            payload["checklist"]["verhaak_centroid_template"] = True
        if "gbm_known_drivers_outline" in path_s:
            payload["checklist"]["outline_driver_yaml"] = True

    out_rel = str(block.get("output_json", "results/module3/m3_repo_bundled_references_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m3_repo_bundled_references_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
