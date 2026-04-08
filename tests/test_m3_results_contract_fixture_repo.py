"""Run results_contract tests against committed fixtures (no local results/ tree required)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.results_contract


def test_results_contract_with_fixture_repo() -> None:
    repo = Path(__file__).resolve().parents[1]
    fixture = repo / "tests" / "fixtures" / "m3_results_contract_repo"
    assert fixture.is_dir(), f"missing {fixture}"
    env = {**os.environ, "M3_RESULTS_CONTRACT_REPO": str(fixture)}
    target = repo / "tests" / "test_m3_deconv_committed_results_flag_contract.py"
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(target),
            "-m",
            "results_contract",
            "-q",
            "--no-header",
        ],
        cwd=str(repo),
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        pytest.fail(
            "results_contract subprocess failed:\n"
            f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
        )
