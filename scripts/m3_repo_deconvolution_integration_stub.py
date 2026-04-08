#!/usr/bin/env python3
"""
Outline M3: integration stub for m3_repo_deconvolution manifest slice (echoes deconvolution + scRNA/spatial repo stubs).

Config: config/m3_repo_deconvolution_outline_inputs.yaml — m3_repo_deconvolution_integration_stub
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


def _echo_block_from_deconv_integration_stub(dec_data: dict[str, Any]) -> dict[str, Any]:
    """Compact mirror of m3_deconvolution_integration_stub.json for export-manifest consumers."""
    return {
        "readiness_tier": dec_data.get("readiness_tier"),
        "artifact_kind": dec_data.get("artifact_kind"),
        "checklist": dec_data.get("checklist"),
        "n_recommended_next_steps": len(dec_data.get("recommended_next_steps") or []),
    }


def main() -> int:
    rr = repo_root()
    dr = data_root()
    cfg_path = rr / "config" / "m3_repo_deconvolution_outline_inputs.yaml"
    if not cfg_path.is_file():
        print(f"Missing {cfg_path}", file=sys.stderr)
        return 1
    doc = yaml.safe_load(cfg_path.read_text(encoding="utf-8-sig"))
    block = doc.get("m3_repo_deconvolution_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_deconvolution_integration_stub disabled")
        return 0

    dec_stub = rr / "results" / "module3" / "m3_deconvolution_integration_stub.json"
    scrna_repo_stub = rr / "results" / "module3" / "m3_repo_scrna_spatial_integration_stub.json"
    echo_paths = [dec_stub, scrna_repo_stub]
    missing = [p for p in echo_paths if not p.is_file()]
    if missing:
        print("Missing prerequisite stubs:", file=sys.stderr)
        for p in missing:
            print(f"  {p}", file=sys.stderr)
        return 1

    dec_data: dict[str, Any] = {}
    try:
        dec_data = json.loads(dec_stub.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        dec_data = {}

    out_doc: dict[str, Any] = {
        "repo_root": str(rr.resolve()),
        "data_root": str(dr.resolve()),
        "outline_module": 3,
        "group": "module3_deconvolution_repo_outline_outputs",
        "echo_integration_stubs": [str(p.resolve()) for p in echo_paths],
        "m3_deconvolution_integration_stub_echo": _echo_block_from_deconv_integration_stub(dec_data),
        "note": (
            "M3 repo deconvolution manifest slice: echoes m3_deconvolution_integration_stub and "
            "m3_repo_scrna_spatial_integration_stub (scRNA/spatial repo outline). "
            "m3_deconvolution_integration_stub_echo carries checklist + tier from the main deconv stub JSON."
        ),
    }
    d_out = "results/module3/m3_repo_deconvolution_integration_stub.json"
    d_flag = "results/module3/m3_repo_deconvolution_integration_stub.flag"
    out_rel = str(block.get("output_json", d_out))
    flag_rel = str(block.get("done_flag", d_flag))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
