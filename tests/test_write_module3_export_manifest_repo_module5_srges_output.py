"""Regression: M3 export manifest lists M5 sRGES output outline path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TEXT = (_ROOT / "scripts" / "write_module3_export_manifest.py").read_text(encoding="utf-8")
_YAML = (_ROOT / "config" / "m3_repo_module5_srges_output_outline_inputs.yaml").read_text(encoding="utf-8")


def test_write_module3_export_manifest_includes_repo_module5_srges_output_paths() -> None:
    assert "m3_repo_module5_srges_output_paths_status.json" in _TEXT
    assert "m3_sc.repo_module5_srges_output_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_module5_srges_output_stub() -> None:
    assert "m3_repo_module5_srges_output_integration_stub.json" in _TEXT
    assert "m3_sc.repo_module5_srges_output_integration_stub" in _TEXT


def test_module5_srges_output_outline_repo_paths_in_manifest() -> None:
    assert "results/module5/m5_srges_output_paths_status.json" in _YAML
    assert "results/module5/m5_srges_output_integration_stub.flag" in _TEXT
    assert "m5.srges_output.integration_stub_flag" in _TEXT
