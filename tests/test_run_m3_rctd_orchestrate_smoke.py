"""Smoke tests for RCTD orchestrator (path validation only; no R execution)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from subprocess import CalledProcessError

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "run_m3_rctd_orchestrate.py"


def test_rctd_orchestrate_fails_when_rds_missing(tmp_path: Path) -> None:
    dr = tmp_path / "data"
    dr.mkdir()
    r = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        cwd=str(_ROOT),
        env={**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(dr)},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 1
    assert "Missing reference RDS" in r.stderr or "Missing reference RDS" in r.stdout


def test_rctd_orchestrate_propagates_wrapper_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rr = tmp_path / "repo"
    (rr / "config").mkdir(parents=True)
    dr = tmp_path / "data"
    dr.mkdir()
    (dr / "ref.rds").write_bytes(b"x")
    (dr / "spat.rds").write_bytes(b"y")
    (rr / "config" / "m3_deconvolution_rctd_inputs.yaml").write_text(
        "m3_deconvolution_rctd:\n  reference_rds: ref.rds\n  spatial_rna_rds: spat.rds\n",
        encoding="utf-8",
    )

    import run_m3_rctd_orchestrate as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    monkeypatch.setattr(m, "data_root", lambda: dr)
    monkeypatch.setattr(m, "resolve_rscript", lambda _rr: "Rscript_stub")

    def boom(*_a: object, **_k: object) -> None:
        raise CalledProcessError(3, ["Rscript_stub"])

    monkeypatch.setattr(subprocess, "check_call", boom)
    assert m.main() == 3


def test_rctd_orchestrate_stderr_hints_provenance_on_wrapper_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rr = tmp_path / "repo"
    (rr / "config").mkdir(parents=True)
    dr = tmp_path / "data"
    dr.mkdir()
    (dr / "ref.rds").write_bytes(b"x")
    (dr / "spat.rds").write_bytes(b"y")
    (rr / "config" / "m3_deconvolution_rctd_inputs.yaml").write_text(
        "m3_deconvolution_rctd:\n  reference_rds: ref.rds\n  spatial_rna_rds: spat.rds\n",
        encoding="utf-8",
    )

    import run_m3_rctd_orchestrate as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    monkeypatch.setattr(m, "data_root", lambda: dr)
    monkeypatch.setattr(m, "resolve_rscript", lambda _rr: "Rscript_stub")

    def boom(*_a: object, **_k: object) -> None:
        raise CalledProcessError(2, ["Rscript_stub"])

    monkeypatch.setattr(subprocess, "check_call", boom)
    assert m.main() == 2
    err = capsys.readouterr().err
    assert "rctd_run_provenance.json" in err
    assert "rctd_run.flag" in err


def test_rctd_wrapper_r_script_flag_only_on_ok_exit() -> None:
    """Contract: flag + exit code align with Snakemake success (see DATA_MANIFEST)."""
    text = (_ROOT / "scripts" / "run_m3_rctd_wrapper.R").read_text(encoding="utf-8")
    assert "identical(prov$status, \"ok\")" in text
    assert "quit(status" in text
    assert "file.remove(flag_path)" in text


def test_rctd_orchestrate_imports_resolve_rscript() -> None:
    """Orchestrator module loads (rscript_resolve available on pythonpath)."""
    import run_m3_rctd_orchestrate as m

    assert callable(m.main)
