#!/usr/bin/env python3
"""Regenerate outline governance artifacts: planned-extensions report + pipeline results index."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    steps = [
        [sys.executable, str(root / "scripts" / "report_pipeline_planned_extensions.py")],
        [sys.executable, str(root / "scripts" / "write_pipeline_results_index.py")],
    ]
    for cmd in steps:
        rc = subprocess.call(cmd, cwd=root)
        if rc != 0:
            return int(rc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
