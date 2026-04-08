#!/usr/bin/env python3
"""
Windows-oriented verification gate for repo + outline-aligned Snakemake DAG.

Runs, in order:
  1) pip install -r requirements.txt -r requirements-optional.txt -r requirements-dev.txt
  2) scripts/verify_python_environment.py
  3) scripts/run_optional_stack_ci.py  (pytest + ensure; GNINA optional on Windows)
  4) scripts/verify_optional_third_party_tooling.py  (non-strict; reports missing 10x/GNINA)
  5) pytest tests -q
  6) snakemake all -c <cores>  (unless --no-snakemake; subprocess env strips optional GLIOMA_TARGET_INCLUDE_* rule-all gates — see scripts/snakemake_subprocess_env.py)

Exit code: first failing step’s code. Cell Ranger, Space Ranger, and GNINA are not pip packages;
the optional stack reports their absence without failing on Windows.

Usage:
  python scripts/run_windows_outline_gate.py
  python scripts/run_windows_outline_gate.py --no-snakemake
  python scripts/run_windows_outline_gate.py -c 4
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_step(label: str, cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> int:
    print(f"\n=== {label} ===", flush=True)
    r = subprocess.run(cmd, cwd=str(cwd), env=env)
    if r.returncode != 0:
        print(f"FAIL: {label} (exit {r.returncode})", file=sys.stderr, flush=True)
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="Windows gate: pip + env + optional stack + tests + snakemake all.")
    ap.add_argument("-c", "--cores", type=int, default=1, help="Snakemake -c (default: 1)")
    ap.add_argument(
        "--no-snakemake",
        action="store_true",
        help="Skip snakemake all (faster; only Python gates).",
    )
    ap.add_argument(
        "--skip-pip",
        action="store_true",
        help="Skip pip install step.",
    )
    args = ap.parse_args()
    rr = repo_root()
    env = {**os.environ}

    if not args.skip_pip:
        rc = run_step(
            "pip install (core + optional + dev)",
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                "requirements.txt",
                "-r",
                "requirements-optional.txt",
                "-r",
                "requirements-dev.txt",
            ],
            cwd=rr,
            env=env,
        )
        if rc != 0:
            return rc

    flat: list[tuple[str, list[str]]] = [
        ("verify_python_environment", [sys.executable, str(rr / "scripts" / "verify_python_environment.py")]),
        ("run_optional_stack_ci", [sys.executable, str(rr / "scripts" / "run_optional_stack_ci.py")]),
        (
            "verify_optional_third_party_tooling",
            [sys.executable, str(rr / "scripts" / "verify_optional_third_party_tooling.py")],
        ),
        ("pytest", [sys.executable, "-m", "pytest", "tests", "-q"]),
        (
            "pipeline_planned_extensions_report",
            [sys.executable, str(rr / "scripts" / "report_pipeline_planned_extensions.py")],
        ),
    ]
    for label, cmd in flat:
        rc = run_step(label, cmd, cwd=rr, env=env)
        if rc != 0:
            return rc

    if not args.no_snakemake:
        scripts_dir = str(rr / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from snakemake_subprocess_env import snakemake_subprocess_env

        rc = run_step(
            f"snakemake all -c {args.cores}",
            [sys.executable, "-m", "snakemake", "all", "-c", str(args.cores)],
            cwd=rr,
            env=snakemake_subprocess_env(),
        )
        if rc != 0:
            return rc

    print("\n=== Windows outline gate: all requested steps succeeded ===", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
