#!/usr/bin/env python3
"""
Module 3 (outline): optional Scanpy / Seurat / spatial workflow roots under data_root.

Presence only — for planning in-repo scRNA-seq or Visium rules. Does not run Scanpy.

Paths are defined in config/module3_inputs.yaml — sc_workflow_path_checks.
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


def count_files_shallow(path: Path, max_files: int = 50000) -> tuple[int, bool]:
    n = 0
    truncated = False
    for root, _, files in os.walk(path):
        n += len(files)
        if n >= max_files:
            truncated = True
            return n, truncated
    return n, truncated


def main() -> int:
    rr = repo_root()
    dr = data_root()
    cfg_path = rr / "config" / "module3_inputs.yaml"
    if not cfg_path.is_file():
        print(f"Missing {cfg_path}", file=sys.stderr)
        return 1
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    block = cfg.get("sc_workflow_path_checks") or {}
    if not block.get("enabled", True):
        print("sc_workflow_path_checks disabled")
        return 0
    checks = block.get("path_checks") or []

    rows: list[dict[str, Any]] = []
    for item in checks:
        name = str(item.get("name", ""))
        rel = str(item.get("path_template", "")).replace("{data_root}", str(dr)).replace("/", os.sep)
        p = Path(rel)
        if p.is_file():
            rows.append(
                {
                    "name": name,
                    "path": str(p),
                    "kind": "file",
                    "exists": True,
                    "size_bytes": p.stat().st_size,
                }
            )
        elif p.is_dir():
            nf, trunc = count_files_shallow(p)
            rows.append(
                {
                    "name": name,
                    "path": str(p),
                    "kind": "directory",
                    "exists": True,
                    "n_files_under": nf,
                    "file_count_truncated": trunc,
                }
            )
        else:
            rows.append({"name": name, "path": str(p), "exists": False, "kind": "missing"})

    out = {
        "data_root": str(dr.resolve()),
        "outline_module": 3,
        "check_group": "sc_workflow_tooling",
        "checks": rows,
        "note": "Optional local trees for Scanpy/Seurat/spaceranger tutorials or refs; not validated for outline CAR-T niche coverage.",
    }
    out_rel = str(block.get("output_json", "results/module3/module3_sc_workflow_paths_status.json"))
    flag_rel = str(block.get("done_flag", "results/module3/module3_sc_workflow_paths_status.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
