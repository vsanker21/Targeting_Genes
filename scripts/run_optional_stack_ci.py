#!/usr/bin/env python3
"""
Local parity with `.github/workflows/optional-stack.yml`: pytest + ensure_optional_third_party_functional.

Default: `pytest tests -q` then ensure with `--no-bootstrap-gnina --no-gnina-required` (safe on Linux CI
and dev machines without GNINA).

Usage:
  python scripts/run_optional_stack_ci.py
  python scripts/run_optional_stack_ci.py --strict-binaries
  python scripts/run_optional_stack_ci.py --skip-pip
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="Run optional-stack checks (pytest + ensure script).")
    ap.add_argument(
        "--strict-binaries",
        action="store_true",
        help="Omit --no-gnina-required so ensure uses OS defaults (GNINA required on non-Windows).",
    )
    ap.add_argument(
        "--skip-pytest",
        action="store_true",
        help="Only run ensure_optional_third_party_functional.py.",
    )
    ap.add_argument(
        "--skip-pip",
        action="store_true",
        help="Forward --skip-pip to ensure (skip pip install of requirements-optional.txt).",
    )
    args = ap.parse_args()
    rr = repo_root()

    if not args.skip_pytest:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "tests", "-q"],
            cwd=str(rr),
        )
        if r.returncode != 0:
            return r.returncode

    cmd = [
        sys.executable,
        str(rr / "scripts" / "ensure_optional_third_party_functional.py"),
        "--no-bootstrap-gnina",
    ]
    if not args.strict_binaries:
        cmd.append("--no-gnina-required")
    if args.skip_pip:
        cmd.append("--skip-pip")
    env = os.environ.copy()
    # Match pytest.ini: quiet cmapPy parse_gct FutureWarnings during ensure.
    prev = env.get("PYTHONWARNINGS", "")
    cmap_filter = "ignore::FutureWarning:cmapPy.pandasGEXpress.parse_gct"
    env["PYTHONWARNINGS"] = cmap_filter if not prev.strip() else f"{prev},{cmap_filter}"
    r2 = subprocess.run(cmd, cwd=str(rr), env=env)
    return r2.returncode


if __name__ == "__main__":
    raise SystemExit(main())
