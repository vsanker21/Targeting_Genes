"""Regression: M3 export manifest lists scRNA/spatial integration stub artifacts."""

from __future__ import annotations

from pathlib import Path

_TEXT = (Path(__file__).resolve().parents[1] / "scripts" / "write_module3_export_manifest.py").read_text(
    encoding="utf-8"
)


def test_write_module3_export_manifest_includes_scrna_stub_paths() -> None:
    assert "scrna_spatial_integration_stub.json" in _TEXT
    assert "m3_sc.scrna_spatial_integration_stub" in _TEXT


def test_write_module3_export_manifest_includes_maf_annotation_stub_paths() -> None:
    assert "maf_annotation_integration_stub.json" in _TEXT
    assert "m2_2.maf_annotation_integration_stub" in _TEXT
