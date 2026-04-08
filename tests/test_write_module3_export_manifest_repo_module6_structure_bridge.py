"""Regression: M3 export manifest lists M6 structure bridge path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TEXT = (_ROOT / "scripts" / "write_module3_export_manifest.py").read_text(encoding="utf-8")
_YAML = (_ROOT / "config" / "m3_repo_module6_structure_bridge_outline_inputs.yaml").read_text(encoding="utf-8")


def test_write_module3_export_manifest_includes_repo_module6_structure_bridge_paths() -> None:
    assert "m3_repo_module6_structure_bridge_paths_status.json" in _TEXT
    assert "m3_sc.repo_module6_structure_bridge_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_module6_structure_bridge_stub() -> None:
    assert "m3_repo_module6_structure_bridge_integration_stub.json" in _TEXT
    assert "m3_sc.repo_module6_structure_bridge_integration_stub" in _TEXT


def test_module6_structure_bridge_outline_paths_in_manifest() -> None:
    assert "structure_druggability_bridge_welch.tsv" in _YAML
    assert "structure_druggability_bridge_provenance.json" in _YAML
    assert "results/module6/structure_druggability_bridge_welch.tsv" in _TEXT
    assert "m6.structure_bridge.global_welch_tsv" in _TEXT
    assert "results/module6/structure_druggability_bridge_provenance.json" in _TEXT
    assert "m6.structure_bridge.provenance" in _TEXT
    assert (
        "results/module6/structure_druggability_bridge_stratified/welch_integrated/"
        "dea_welch_subtype_Classical_structure_bridge.tsv" in _TEXT
    )
    assert "m6.structure_bridge.stratified.welch.classical_tsv" in _TEXT
    assert "results/module6/structure_admet_integration_stub.json" in _TEXT
    assert "m6.structure_admet_integration_stub" in _TEXT
