#!/usr/bin/env python3
"""
Cross-cutting: vendor binary / conda install gap checklist (Cell Ranger, Space Ranger, GNINA).

Reads vendor_tooling_paths_status.json and, when present, slims results/third_party_tooling_status.json.

Config: config/vendor_tooling_outline_inputs.yaml — vendor_tooling_integration_stub
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
    p = repo_root() / "config" / "vendor_tooling_outline_inputs.yaml"
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


def _n_ok(g: dict[str, Any]) -> int:
    return int(g.get("n_existing") or 0)


def _slim_third_party(doc: dict[str, Any]) -> dict[str, Any]:
    bins = doc.get("binaries") or []
    slim_bins = [
        {"id": b.get("id"), "on_path": b.get("on_path"), "resolved_path": b.get("resolved_path")}
        for b in bins
        if isinstance(b, dict)
    ]
    markers = doc.get("data_root_markers") or []
    slim_m = [
        {"name": m.get("name"), "exists": m.get("exists"), "path": m.get("path")}
        for m in markers
        if isinstance(m, dict)
    ]
    conda = doc.get("conda") or {}
    return {
        "binaries": slim_bins,
        "data_root_markers": slim_m,
        "conda_gnina": {"checked": conda.get("checked"), "installed": conda.get("installed")},
    }


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("vendor_tooling_integration_stub") or {}
    if not block.get("enabled", True):
        print("vendor_tooling_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/tooling/vendor_tooling_paths_status.json") or {}
    tp = _read_json(rr, "results/third_party_tooling_status.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append("Missing results/tooling/vendor_tooling_paths_status.json (run vendor_tooling_paths_status)")

    cr = _group(paths_doc, "cell_ranger_vendor_tree") or {}
    sr = _group(paths_doc, "space_ranger_vendor_tree") or {}
    gn = _group(paths_doc, "gnina_data_root_markers") or {}
    conda_g = _group(paths_doc, "repo_conda_gnina_bootstrap") or {}

    cr_ok = _n_ok(cr) > 0
    sr_ok = _n_ok(sr) > 0
    gn_ok = _n_ok(gn) > 0
    conda_ok = _n_ok(conda_g) > 0
    n_groups_hit = sum(1 for x in (cr_ok, sr_ok, gn_ok, conda_ok) if x)

    readiness_tier = "D"
    if cr_ok and (gn_ok or conda_ok):
        readiness_tier = "A"
    elif n_groups_hit >= 2:
        readiness_tier = "B"
    elif n_groups_hit == 1:
        readiness_tier = "C"
    elif paths_doc.get("groups"):
        readiness_tier = "D"

    if tp:
        bins = [b for b in (tp.get("binaries") or []) if isinstance(b, dict) and b.get("id")]
        all_on_path = len(bins) > 0 and all(bool(b.get("on_path")) for b in bins)
        if all_on_path and readiness_tier == "D":
            readiness_tier = "C"
        if all_on_path and readiness_tier == "C":
            readiness_tier = "B"

    checklist: dict[str, Any] = {
        "cell_ranger_vendor_tree_staged": cr_ok,
        "space_ranger_vendor_tree_staged": sr_ok,
        "gnina_marker_or_flag_staged": gn_ok,
        "repo_conda_gnina_prefix_present": conda_ok,
        "note": "PATH resolution lives in verify_optional_third_party_tooling.py; this stub tracks data_root and repo conda trees.",
    }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": "tooling",
        "artifact_kind": "vendor_tooling_integration_stub",
        "paths_status_echo": {
            "cell_ranger_vendor_tree": {"n_existing": _n_ok(cr), "n_checks": int(cr.get("n_checks") or 0)},
            "space_ranger_vendor_tree": {"n_existing": _n_ok(sr), "n_checks": int(sr.get("n_checks") or 0)},
            "gnina_data_root_markers": {"n_existing": _n_ok(gn), "n_checks": int(gn.get("n_checks") or 0)},
            "repo_conda_gnina_bootstrap": {"n_existing": _n_ok(conda_g), "n_checks": int(conda_g.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
            "repo_root": paths_doc.get("repo_root"),
        },
        "third_party_tooling_echo": _slim_third_party(tp) if tp else None,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "A": "Cell Ranger tree staged plus GNINA marker or conda GNINA prefix.",
            "B": "Two or more staging dimensions, or all PATH binaries resolved per third_party_tooling_status.",
            "C": "One staging dimension or partial PATH coverage.",
            "D": "No vendor staging paths and no favorable third-party status echo.",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Run snakemake verify_optional_third_party_tooling -c1 after installs to refresh results/third_party_tooling_status.json.",
            "See README third-party section and config/third_party_tooling.yaml for download links.",
        ],
    }

    out_rel = str(block.get("output_json", "results/tooling/vendor_tooling_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/tooling/vendor_tooling_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
