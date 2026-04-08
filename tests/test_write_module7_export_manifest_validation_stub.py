"""Regression: M7 export manifest lists GTS validation integration stub artifacts."""

from __future__ import annotations

from pathlib import Path

_TEXT = (Path(__file__).resolve().parents[1] / "scripts" / "write_module7_export_manifest.py").read_text(
    encoding="utf-8"
)


def test_write_module7_export_manifest_includes_gts_validation_stub_paths() -> None:
    assert "gts_validation_integration_stub.json" in _TEXT
    assert "gts_validation.integration_stub" in _TEXT
