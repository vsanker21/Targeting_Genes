"""Regression: M3 export manifest lists M2.2 variant annotation path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_TEXT = (Path(__file__).resolve().parents[1] / "scripts" / "write_module3_export_manifest.py").read_text(
    encoding="utf-8"
)


def test_write_module3_export_manifest_includes_m2_2_variant_annotation_paths() -> None:
    assert "m2_2_variant_annotation_paths_status.json" in _TEXT
    assert "m2_2.variant_annotation_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_m2_2_variant_annotation_stub() -> None:
    assert "m2_2_variant_annotation_integration_stub.json" in _TEXT
    assert "m2_2.variant_annotation_integration_stub" in _TEXT
