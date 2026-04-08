"""Regression: M3 export manifest lists scRNA/spatial repo path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_TEXT = (Path(__file__).resolve().parents[1] / "scripts" / "write_module3_export_manifest.py").read_text(
    encoding="utf-8"
)


def test_write_module3_export_manifest_includes_repo_scrna_spatial_paths() -> None:
    assert "m3_repo_scrna_spatial_paths_status.json" in _TEXT
    assert "m3_sc.repo_scrna_spatial_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_scrna_spatial_stub() -> None:
    assert "m3_repo_scrna_spatial_integration_stub.json" in _TEXT
    assert "m3_sc.repo_scrna_spatial_integration_stub" in _TEXT
