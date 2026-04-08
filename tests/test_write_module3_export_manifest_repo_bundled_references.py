"""Regression: M3 export manifest lists repo-bundled references path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TEXT = (_ROOT / "scripts" / "write_module3_export_manifest.py").read_text(encoding="utf-8")
_YAML = (_ROOT / "config" / "m3_repo_bundled_references_outline_inputs.yaml").read_text(encoding="utf-8")


def test_write_module3_export_manifest_includes_repo_bundled_references_paths() -> None:
    assert "m3_repo_bundled_references_paths_status.json" in _TEXT
    assert "m3_sc.repo_bundled_references_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_bundled_references_stub() -> None:
    assert "m3_repo_bundled_references_integration_stub.json" in _TEXT
    assert "m3_sc.repo_bundled_references_integration_stub" in _TEXT


def test_bundled_references_outline_paths_in_manifest() -> None:
    assert "references/verhaak_msigdb_c2_cgp_2024.1.Hs.gmt" in _YAML
    assert "references/gbm_known_drivers_outline.yaml" in _TEXT
    assert "refs.bundled.gbm_known_drivers_yaml" in _TEXT
