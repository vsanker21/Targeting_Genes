"""Regression: M3 export manifest lists repo sc-workflow path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_TEXT = (Path(__file__).resolve().parents[1] / "scripts" / "write_module3_export_manifest.py").read_text(
    encoding="utf-8"
)


def test_write_module3_export_manifest_includes_repo_sc_workflow_paths() -> None:
    assert "m3_repo_sc_workflow_paths_status.json" in _TEXT
    assert "m3_sc.repo_sc_workflow_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_sc_workflow_stub() -> None:
    assert "m3_repo_sc_workflow_integration_stub.json" in _TEXT
    assert "m3_sc.repo_sc_workflow_integration_stub" in _TEXT
