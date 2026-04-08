#!/usr/bin/env python3
"""
Outline M2: M3 manifest slice — echoes prerequisite M2 outline JSON artifacts.

Config: config/m3_repo_m2_1_toil_xena_hub_outline_inputs.yaml — m3_repo_m2_1_toil_xena_hub_integration_stub
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def main() -> int:
    rr = repo_root()
    dr = data_root()
    cfg_path = rr / "config" / "m3_repo_m2_1_toil_xena_hub_outline_inputs.yaml"
    if not cfg_path.is_file():
        print(f"Missing {cfg_path}", file=sys.stderr)
        return 1
    doc = yaml.safe_load(cfg_path.read_text(encoding="utf-8-sig"))
    block = doc.get("m3_repo_m2_1_toil_xena_hub_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_m2_1_toil_xena_hub_integration_stub disabled")
        return 0

    m3 = rr / "results" / "module3"
    echo_paths = [m3 / "m2_1_toil_xena_hub_integration_stub.json", m3 / "m1_outline_integration_stub.json"]
    missing = [p for p in echo_paths if not p.is_file()]
    if missing:
        print("Missing prerequisite artifacts:", file=sys.stderr)
        for p in missing:
            print(f"  {p}", file=sys.stderr)
        return 1

    out_doc: dict[str, Any] = {
        "repo_root": str(rr.resolve()),
        "data_root": str(dr.resolve()),
        "outline_module": 2,
        "group": "module3_m2_1_toil_xena_hub_repo_outline_outputs",
        "echo_integration_stubs": [str(p.resolve()) for p in echo_paths],
        "note": "M3 manifest slice for m2_1_toil_xena_hub; echoes TOIL hub + M1 outline stubs.",
    }
    out_rel = str(block.get("output_json", ""))
    flag_rel = str(block.get("done_flag", ""))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, indent=2), encoding="utf-8")
    flag_path.write_text("ok" + chr(10), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
