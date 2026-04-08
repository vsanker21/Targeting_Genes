#!/usr/bin/env python3
"""
Module 5 (outline): record availability of LINCS / cmapPy paths under data_root.

Does not fail if paths are missing (partial implementation per pipeline_outline.yaml).
Writes results/module5/module5_data_paths_status.json for future sRGES / connectivity rules.

Paths are defined in config/module5_inputs.yaml.
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
    cfg_path = rr / "config" / "module5_inputs.yaml"
    if not cfg_path.is_file():
        print(f"Missing {cfg_path}", file=sys.stderr)
        return 1
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    checks = cfg.get("path_checks") or []

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
        "outline_module": 5,
        "checks": rows,
        "note": "Presence only; Module 5 sRGES / LINCS connectivity rules consume these when exists=true.",
    }
    out_path = rr / "results" / "module5" / "module5_data_paths_status.json"
    flag_path = rr / "results" / "module5" / "module5_data_paths_status.flag"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
