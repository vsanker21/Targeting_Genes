"""Regression: M3 export manifest lists M6 structure tooling + ADMET path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TEXT = (_ROOT / "scripts" / "write_module3_export_manifest.py").read_text(encoding="utf-8")
_YAML = (_ROOT / "config" / "m3_repo_module6_structure_tooling_outline_inputs.yaml").read_text(encoding="utf-8")


def test_write_module3_export_manifest_includes_repo_module6_structure_tooling_paths() -> None:
    assert "m3_repo_module6_structure_tooling_paths_status.json" in _TEXT
    assert "m3_sc.repo_module6_structure_tooling_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_module6_structure_tooling_stub() -> None:
    assert "m3_repo_module6_structure_tooling_integration_stub.json" in _TEXT
    assert "m3_sc.repo_module6_structure_tooling_integration_stub" in _TEXT


def test_module6_structure_tooling_outline_paths_status_in_manifest_admet_via_bridge() -> None:
    assert "module6_structure_tooling_paths_status.json" in _YAML
    assert "results/module6/module6_structure_tooling_paths_status.json" in _TEXT
    assert "m6.structure_tooling.paths_status_json" in _TEXT
    assert "structure_admet_integration_stub.json" in _YAML
    assert "results/module6/structure_admet_integration_stub.json" in _TEXT
    assert "m6.structure_admet_integration_stub" in _TEXT
