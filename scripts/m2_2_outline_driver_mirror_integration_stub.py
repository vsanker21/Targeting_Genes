#!/usr/bin/env python3
"""
Outline M2.2: extended driver panel mirror checklist (no join_dea_outline_driver_flags execution).

Reads m2_2_outline_driver_mirror_paths_status.json, maf_annotation_integration_stub.json,
references/gbm_known_drivers_outline.yaml, module2_integration.yaml outline_driver_flags,
and an optional sample *_outline_drivers.tsv when present.

Config: config/m2_2_outline_driver_mirror_outline_inputs.yaml (m2_2_outline_driver_mirror_integration_stub).
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
    p = repo_root() / "config" / "m2_2_outline_driver_mirror_outline_inputs.yaml"
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
    block = doc.get("m2_2_outline_driver_mirror_integration_stub") or {}
    if not block.get("enabled", True):
        print("m2_2_outline_driver_mirror_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m2_2_outline_driver_mirror_paths_status.json") or {}
    maf_stub = _read_json(rr, "results/module3/maf_annotation_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m2_2_outline_driver_mirror_paths_status.json (run m2_2_outline_driver_mirror_paths_status)"
        )

    g_user = _group(paths_doc, "user_driver_panel_staging") or {}
    g_cat = _group(paths_doc, "census_or_catalog_mirror") or {}

    user_ok = _n_ok(g_user) > 0
    cat_ok = _n_ok(g_cat) > 0

    in_repo_drivers = rr / "references" / "gbm_known_drivers_outline.yaml"
    in_repo_symbols = in_repo_drivers.is_file()

    integ_cfg = yaml.safe_load((rr / "config" / "module2_integration.yaml").read_text(encoding="utf-8-sig"))
    od = (integ_cfg.get("outline_driver_flags") or {}) if integ_cfg else {}
    sym_rel = str(od.get("symbols_yaml", "references/gbm_known_drivers_outline.yaml"))
    cfg_symbols_path = rr / sym_rel.replace("/", os.sep)
    cfg_symbols_exists = cfg_symbols_path.is_file()

    sample_outline_tsv = rr / "results" / "module3" / "dea_gbm_vs_gtex_brain_outline_drivers.tsv"
    sample_join_ran = sample_outline_tsv.is_file()

    readiness_tier = "D"
    if user_ok and cat_ok:
        readiness_tier = "B"
    elif user_ok or cat_ok:
        readiness_tier = "C"
    elif in_repo_symbols or sample_join_ran:
        readiness_tier = "C"
    elif maf_stub:
        readiness_tier = "C"

    maf_echo: dict[str, Any] = {}
    if maf_stub:
        maf_echo = {
            "readiness_tier": maf_stub.get("readiness_tier"),
            "artifact_kind": maf_stub.get("artifact_kind"),
        }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_section": "M2.2",
        "artifact_kind": "m2_2_outline_driver_mirror_integration_stub",
        "note": "Checklist only; point outline_driver_flags.symbols_yaml at a mirrored file if you replace the in-repo list.",
        "paths_status_echo": {
            "user_driver_panel_staging": {"n_existing": _n_ok(g_user), "n_checks": int(g_user.get("n_checks") or 0)},
            "census_or_catalog_mirror": {"n_existing": _n_ok(g_cat), "n_checks": int(g_cat.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "in_repo_gbm_known_drivers_outline_yaml": in_repo_symbols,
        "module2_integration_symbols_yaml": sym_rel,
        "module2_integration_symbols_path_resolved_exists": cfg_symbols_exists,
        "sample_outline_drivers_tsv_present": sample_join_ran,
        "sample_outline_drivers_tsv": str(sample_outline_tsv.relative_to(rr)) if sample_join_ran else None,
        "maf_annotation_stub_echo": maf_echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Both user panel staging and catalog mirror trees show at least one existing path.",
            "C": "One mirror dimension, in-repo driver YAML, sample outline_drivers TSV, or MAF annotation stub only.",
            "D": "No mirror paths and no in-repo driver list, sample join output, or stub echo.",
        },
        "checklist": {
            "user_driver_panel_mirror_staged": user_ok,
            "census_or_catalog_mirror_staged": cat_ok,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Keep references/gbm_known_drivers_outline.yaml as default, or copy an extended list under data_root/drivers/ and set outline_driver_flags.symbols_yaml.",
            "Run join_dea_outline_driver_flags.py after DEA tables exist to emit *_outline_drivers.tsv files.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m2_2_outline_driver_mirror_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m2_2_outline_driver_mirror_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
