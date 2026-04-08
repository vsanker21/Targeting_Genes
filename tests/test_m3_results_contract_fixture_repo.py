"""Run results_contract tests against synthetic fixtures (no committed tests/fixtures tree required on CI)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.results_contract


def _write_minimal_contract_tree(root: Path) -> None:
    """Mirror tests/fixtures/m3_results_contract_repo content for contract assertions."""
    rctd = root / "results" / "module3" / "m3_deconvolution_rctd"
    c2l = root / "results" / "module3" / "m3_deconvolution_cell2location"
    rctd.mkdir(parents=True, exist_ok=True)
    c2l.mkdir(parents=True, exist_ok=True)
    (rctd / "rctd_run_provenance.json").write_text(
        json.dumps(
            {
                "status": "ok",
                "artifact_kind": "m3_deconvolution_rctd_run",
                "reference_rds": "/fixture/reference.rds",
                "spatial_rna_rds": "/fixture/spatialRNA.rds",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (rctd / "rctd_run.flag").write_text("ok\n", encoding="utf-8")
    (c2l / "cell2location_run_provenance.json").write_text(
        json.dumps(
            {
                "status": "inputs_ok",
                "artifact_kind": "m3_deconvolution_cell2location_run",
                "reference_h5ad": "/fixture/ref.h5ad",
                "spatial_h5ad": "/fixture/spat.h5ad",
                "training_enabled": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (c2l / "cell2location_run.flag").write_text("ok\n", encoding="utf-8")


def test_results_contract_with_fixture_repo(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    fixture_root = tmp_path / "m3_results_contract_repo"
    _write_minimal_contract_tree(fixture_root)
    env = {**os.environ, "M3_RESULTS_CONTRACT_REPO": str(fixture_root)}
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
