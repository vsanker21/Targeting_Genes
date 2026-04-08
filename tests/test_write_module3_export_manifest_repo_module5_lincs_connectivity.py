"""Regression: M3 export manifest lists Module 5 LINCS repo path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TEXT = (_ROOT / "scripts" / "write_module3_export_manifest.py").read_text(encoding="utf-8")
_YAML = (_ROOT / "config" / "m3_repo_module5_lincs_connectivity_outline_inputs.yaml").read_text(encoding="utf-8")


def test_write_module3_export_manifest_includes_repo_module5_lincs_connectivity_paths() -> None:
    assert "m3_repo_module5_lincs_connectivity_paths_status.json" in _TEXT
    assert "m3_sc.repo_module5_lincs_connectivity_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_module5_lincs_connectivity_stub() -> None:
    assert "m3_repo_module5_lincs_connectivity_integration_stub.json" in _TEXT
    assert "m3_sc.repo_module5_lincs_connectivity_integration_stub" in _TEXT


def test_module5_lincs_connectivity_outline_data_paths_in_manifest() -> None:
    assert "lincs_disease_signature_welch_entrez.tsv" in _YAML
    assert "cmap_tooling_scan.json" in _YAML
    assert "results/module5/lincs_disease_signature_welch_entrez.tsv" in _TEXT
    assert "m5.lincs_connectivity.signature_welch_entrez_tsv" in _TEXT
    assert "results/module5/srges_integration_stub.json" in _TEXT
    assert "m5.lincs_connectivity.srges_integration_stub" in _TEXT
