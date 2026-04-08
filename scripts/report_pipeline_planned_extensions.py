#!/usr/bin/env python3
"""
Emit results/pipeline_planned_extensions_report.json from config/pipeline_planned_extensions.yaml.

This does NOT implement the listed extensions; it records honest status for governance / roadmap.
Exit 0 if the report is written successfully.
"""

from __future__ import annotations

import json
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    rr = repo_root()
    src = rr / "config" / "pipeline_planned_extensions.yaml"
    if not src.is_file():
        print(f"Missing {src}", file=sys.stderr)
        return 1
    doc = yaml.safe_load(src.read_text(encoding="utf-8"))
    out = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "host": socket.gethostname(),
        "source_config": str(src.relative_to(rr)).replace("\\", "/"),
        "disclaimer": doc.get("disclaimer", "").strip(),
        "extensions": doc.get("extensions") or [],
        "counts_by_status": {},
    }
    for row in out["extensions"]:
        st = str(row.get("implementation_status", "unknown"))
        out["counts_by_status"][st] = out["counts_by_status"].get(st, 0) + 1

    dest = rr / "results" / "pipeline_planned_extensions_report.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {dest}")
    print(f"Status counts: {out['counts_by_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
