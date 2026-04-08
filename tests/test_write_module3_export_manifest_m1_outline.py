"""Regression: M3 export manifest lists M1 outline path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_TEXT = (Path(__file__).resolve().parents[1] / "scripts" / "write_module3_export_manifest.py").read_text(
    encoding="utf-8"
)


def test_write_module3_export_manifest_includes_m1_outline_paths() -> None:
    assert "m1_outline_paths_status.json" in _TEXT
    assert "m1.outline_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_m1_outline_stub() -> None:
    assert "m1_outline_integration_stub.json" in _TEXT
    assert "m1.outline_integration_stub" in _TEXT


def test_write_module3_export_manifest_includes_m1_harmony_batch() -> None:
    assert "m1_harmony_batch_paths_status.json" in _TEXT
    assert "m1.harmony_batch_paths_status" in _TEXT
    assert "m1_harmony_batch_integration_stub.json" in _TEXT
    assert "m1.harmony_batch_integration_stub" in _TEXT
