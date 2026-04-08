"""Regression: M3 export manifest lists M7 GTS stub path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TEXT = (_ROOT / "scripts" / "write_module3_export_manifest.py").read_text(encoding="utf-8")
_YAML = (_ROOT / "config" / "m3_repo_module7_gts_stub_outline_inputs.yaml").read_text(encoding="utf-8")


def test_write_module3_export_manifest_includes_repo_module7_gts_stub_paths() -> None:
    assert "m3_repo_module7_gts_stub_paths_status.json" in _TEXT
    assert "m3_sc.repo_module7_gts_stub_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_module7_gts_stub_integration() -> None:
    assert "m3_repo_module7_gts_stub_integration_stub.json" in _TEXT
    assert "m3_sc.repo_module7_gts_stub_integration_stub" in _TEXT


def test_module7_gts_stub_outline_data_paths_in_manifest() -> None:
    assert "gts_candidate_table_welch_stub.tsv" in _YAML
    assert "glioma_target_tier1_welch.tsv" in _YAML
    assert "results/module7/gts_candidate_table_welch_stub.tsv" in _TEXT
    assert "m7.gts_stub.global_welch_tsv" in _TEXT
    assert "gts_validation_integration_stub.json" in _YAML
    assert "results/module7/gts_validation_integration_stub.json" in _TEXT
    assert "m7.gts_validation_integration_stub" in _TEXT
