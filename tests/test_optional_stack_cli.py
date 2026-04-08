"""CLI surface checks for optional-stack scripts (no heavy installs)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_ensure_help_mentions_skip_pip() -> None:
    r = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "ensure_optional_third_party_functional.py"), "--help"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    assert "--skip-pip" in r.stdout


def test_run_optional_stack_ci_help_mentions_skip_pip() -> None:
    r = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "run_optional_stack_ci.py"), "--help"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    assert "--skip-pip" in r.stdout
