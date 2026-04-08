"""Regression: M3 export manifest lists M2.1 CPTAC/methylation path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_TEXT = (Path(__file__).resolve().parents[1] / "scripts" / "write_module3_export_manifest.py").read_text(
    encoding="utf-8"
)


def test_write_module3_export_manifest_includes_cptac_methylation_paths() -> None:
    assert "m2_cptac_methylation_paths_status.json" in _TEXT
    assert "m2_1.cptac_methylation_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_cptac_methylation_stub() -> None:
    assert "m2_cptac_methylation_integration_stub.json" in _TEXT
    assert "m2_1.cptac_methylation_integration_stub" in _TEXT
