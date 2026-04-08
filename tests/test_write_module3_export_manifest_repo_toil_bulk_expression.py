"""Regression: M3 export manifest lists TOIL bulk hub path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TEXT = (_ROOT / "scripts" / "write_module3_export_manifest.py").read_text(encoding="utf-8")
_YAML = (_ROOT / "config" / "m3_repo_toil_bulk_expression_outline_inputs.yaml").read_text(encoding="utf-8")


def test_write_module3_export_manifest_includes_repo_toil_bulk_paths() -> None:
    assert "m3_repo_toil_bulk_expression_paths_status.json" in _TEXT
    assert "m3_sc.repo_toil_bulk_expression_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_toil_bulk_stub() -> None:
    assert "m3_repo_toil_bulk_expression_integration_stub.json" in _TEXT
    assert "m3_sc.repo_toil_bulk_expression_integration_stub" in _TEXT


def test_toil_bulk_expression_outline_paths_in_manifest() -> None:
    assert "toil_gbm_vs_brain_tpm.parquet" in _YAML
    assert "toil_gbm_vs_brain_samples.tsv" in _YAML
    assert "results/module3/toil_gbm_vs_brain_tpm.parquet" in _TEXT
    assert "toil_hub.tpm_parquet" in _TEXT
    assert "results/module3/toil_gbm_vs_brain_samples.tsv" in _TEXT
    assert "toil_hub.samples_tsv" in _TEXT
