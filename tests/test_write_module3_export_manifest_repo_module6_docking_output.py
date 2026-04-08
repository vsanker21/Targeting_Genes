"""Regression: M3 export manifest lists M6 docking output path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TEXT = (_ROOT / "scripts" / "write_module3_export_manifest.py").read_text(encoding="utf-8")
_YAML = (_ROOT / "config" / "m3_repo_module6_docking_output_outline_inputs.yaml").read_text(encoding="utf-8")


def test_write_module3_export_manifest_includes_repo_module6_docking_output_paths() -> None:
    assert "m3_repo_module6_docking_output_paths_status.json" in _TEXT
    assert "m3_sc.repo_module6_docking_output_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_module6_docking_output_stub() -> None:
    assert "m3_repo_module6_docking_output_integration_stub.json" in _TEXT
    assert "m3_sc.repo_module6_docking_output_integration_stub" in _TEXT


def test_module6_docking_output_outline_data_paths_in_manifest() -> None:
    assert "m6_docking_output_paths_status.json" in _YAML
    assert "results/module6/m6_docking_output_paths_status.json" in _TEXT
    assert "m6.docking_output.paths_status_json" in _TEXT
