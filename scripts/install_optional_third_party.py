#!/usr/bin/env python3
"""
Install optional Python packages (cmapPy, etc.) from requirements-optional.txt.

Does not install Cell Ranger or GNINA binaries (see README + config/third_party_tooling.yaml).
For pip + cmapPy GCT round-trip + binary smoke tests, run ensure_optional_third_party_functional.py
or scripts/run_optional_stack_ci.py (pytest + ensure, CI defaults).

Usage:
  python scripts/install_optional_third_party.py
  python scripts/install_optional_third_party.py --conda-gnina
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="Install optional third-party Python deps (cmapPy).")
    ap.add_argument(
        "--conda-gnina",
        action="store_true",
        help="Run: conda install -c conda-forge gnina -y (active conda env)",
    )
    args = ap.parse_args()
    rr = repo_root()
    req = rr / "requirements-optional.txt"
    if not req.is_file():
        print(f"Missing {req}", file=sys.stderr)
        return 1

    print("pip install -r requirements-optional.txt …")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", str(req)],
        cwd=str(rr),
    )
    print("Optional pip packages installed.")

    if args.conda_gnina:
        conda = shutil.which("conda")
        if not conda:
            print("conda not found on PATH; skip --conda-gnina", file=sys.stderr)
            return 1
        prefix = os.environ.get("CONDA_PREFIX", "").strip()
        cmd = [conda, "install", "-c", "conda-forge", "gnina", "-y"]
        if prefix:
            cmd = [conda, "install", "-p", prefix, "-c", "conda-forge", "gnina", "-y"]
        print(" ".join(cmd), "…")
        subprocess.check_call(cmd)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
