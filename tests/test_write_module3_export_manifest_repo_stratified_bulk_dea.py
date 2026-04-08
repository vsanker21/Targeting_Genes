"""Regression: M3 export manifest lists stratified bulk DEA path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TEXT = (_ROOT / "scripts" / "write_module3_export_manifest.py").read_text(encoding="utf-8")
_YAML = (_ROOT / "config" / "m3_repo_stratified_bulk_dea_outline_inputs.yaml").read_text(encoding="utf-8")


def test_write_module3_export_manifest_includes_repo_stratified_bulk_dea_paths() -> None:
    assert "m3_repo_stratified_bulk_dea_paths_status.json" in _TEXT
    assert "m3_sc.repo_stratified_bulk_dea_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_stratified_bulk_dea_stub() -> None:
    assert "m3_repo_stratified_bulk_dea_integration_stub.json" in _TEXT
    assert "m3_sc.repo_stratified_bulk_dea_integration_stub" in _TEXT


def test_stratified_bulk_dea_outline_summary_tsvs_in_manifest() -> None:
    assert "stratified_dea/summary.tsv" in _YAML
    assert "stratified_ols_dea/summary.tsv" in _YAML
    assert "results/module3/stratified_dea/summary.tsv" in _TEXT
    assert "stratified_dea.welch.summary_tsv" in _TEXT
    assert "results/module3/stratified_ols_dea/summary.tsv" in _TEXT
    assert "stratified_dea.ols.summary_tsv" in _TEXT
