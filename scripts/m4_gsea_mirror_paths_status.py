#!/usr/bin/env python3
"""
Outline M4: optional GSEA or MSigDB mirror path presence under data_root.

Config: config/m4_gsea_mirror_outline_inputs.yaml (m4_gsea_mirror_path_checks).
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
    for root, _, files in os.walk(path):
        n += len(files)
        if n >= max_files:
            return n, True
    return n, False


def _one_check(dr: Path, item: dict[str, Any]) -> dict[str, Any]:
    name = str(item.get("name", ""))
    rel = str(item.get("path_template", "")).replace("{data_root}", str(dr)).replace("/", os.sep)
    p = Path(rel)
    if p.is_file():
        return {
            "name": name,
            "path": str(p),
            "kind": "file",
            "exists": True,
            "size_bytes": p.stat().st_size,
        }
    if p.is_dir():
        nf, trunc = count_files_shallow(p)
        return {
            "name": name,
            "path": str(p),
            "kind": "directory",
            "exists": True,
            "n_files_under": nf,
            "file_count_truncated": trunc,
        }
    return {"name": name, "path": str(p), "exists": False, "kind": "missing"}


def main() -> int:
    rr = repo_root()
    dr = data_root()
    cfg_path = rr / "config" / "m4_gsea_mirror_outline_inputs.yaml"
    if not cfg_path.is_file():
        print(f"Missing {cfg_path}", file=sys.stderr)
        return 1
    doc = yaml.safe_load(cfg_path.read_text(encoding="utf-8-sig"))
    block = doc.get("m4_gsea_mirror_path_checks") or {}
    if not block.get("enabled", True):
        print("m4_gsea_mirror_path_checks disabled")
        return 0

    groups_out: list[dict[str, Any]] = []
    for grp in block.get("groups") or []:
        gid = str(grp.get("id", ""))
        checks = [_one_check(dr, item) for item in (grp.get("path_checks") or [])]
        n_ok = sum(1 for c in checks if c.get("exists"))
        groups_out.append(
            {
                "id": gid,
                "summary": grp.get("summary"),
                "checks": checks,
                "n_existing": n_ok,
                "n_checks": len(checks),
            }
        )

    out_doc = {
        "data_root": str(dr.resolve()),
        "outline_section": "M4",
        "artifact_kind": "m4_gsea_mirror_paths_status",
        "groups": groups_out,
        "note": "Presence only; in-repo prerank export remains export_dea_gsea_prerank_rnk.py to results/module4/gsea/.",
    }
    out_rel = str(block.get("output_json", "results/module4/m4_gsea_mirror_paths_status.json"))
    flag_rel = str(block.get("done_flag", "results/module4/m4_gsea_mirror_paths_status.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
