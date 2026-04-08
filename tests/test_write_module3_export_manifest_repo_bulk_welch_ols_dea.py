"""Regression: M3 export manifest lists TOIL Welch and OLS bulk DEA path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TEXT = (_ROOT / "scripts" / "write_module3_export_manifest.py").read_text(encoding="utf-8")
_YAML = (_ROOT / "config" / "m3_repo_bulk_welch_ols_dea_outline_inputs.yaml").read_text(encoding="utf-8")


def test_write_module3_export_manifest_includes_repo_bulk_welch_ols_dea_paths() -> None:
    assert "m3_repo_bulk_welch_ols_dea_paths_status.json" in _TEXT
    assert "m3_sc.repo_bulk_welch_ols_dea_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_bulk_welch_ols_dea_stub() -> None:
    assert "m3_repo_bulk_welch_ols_dea_integration_stub.json" in _TEXT
    assert "m3_sc.repo_bulk_welch_ols_dea_integration_stub" in _TEXT


def test_bulk_welch_ols_outline_dea_tsvs_in_manifest() -> None:
    assert "dea_gbm_vs_gtex_brain.tsv" in _YAML
    assert "dea_gbm_vs_gtex_brain_ols_region_covariate.tsv" in _YAML
    assert "results/module3/dea_gbm_vs_gtex_brain.tsv" in _TEXT
    assert "bulk_dea.welch.tsv" in _TEXT
    assert "results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv" in _TEXT
    assert "bulk_dea.ols.tsv" in _TEXT
