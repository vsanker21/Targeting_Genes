#!/usr/bin/env python3
"""
Verify third-party packages from requirements.txt import cleanly.

Run from repo root after: pip install -r requirements.txt

Exit code 0 if all checks pass; 1 if any import fails.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path


def main() -> int:
    rr = Path(__file__).resolve().parents[1]
    req = rr / "requirements.txt"
    if not req.is_file():
        print(f"Missing {req}", file=sys.stderr)
        return 1

    modules: list[str] = []
    for line in req.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # "pkg>=1.0" or "pkg==1.0"
        name = line.split(";", 1)[0].strip()
        for sep in ("==", ">=", "<=", "~=", "!=", "<", ">"):
            if sep in name:
                name = name.split(sep, 1)[0].strip()
                break
        # PyPI name -> import name
        mapping = {
            "pyyaml": "yaml",
            "pyarrow": "pyarrow",
        }
        mod = mapping.get(name.lower(), name.lower().replace("-", "_"))
        if mod not in modules:
            modules.append(mod)

    failed: list[str] = []
    for mod in modules:
        try:
            importlib.import_module(mod)
            print(f"ok  import {mod}")
        except ImportError as e:
            print(f"FAIL import {mod}: {e}", file=sys.stderr)
            failed.append(mod)

    # Snakemake CLI (module layout varies by version)
    try:
        r = subprocess.run(
            [sys.executable, "-m", "snakemake", "--version"],
            cwd=rr,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if r.returncode == 0:
            ver = (r.stdout or r.stderr or "").strip().splitlines()[0]
            print(f"ok  snakemake CLI: {ver}")
        else:
            print(f"FAIL snakemake --version: {r.stderr or r.stdout}", file=sys.stderr)
            failed.append("snakemake-cli")
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"FAIL snakemake CLI: {e}", file=sys.stderr)
        failed.append("snakemake-cli")

    if failed:
        print(f"\n{len(failed)} check(s) failed: {failed}", file=sys.stderr)
        return 1
    print("\nAll environment checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
