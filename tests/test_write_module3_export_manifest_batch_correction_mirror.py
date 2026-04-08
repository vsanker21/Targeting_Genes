"""Regression: M3 export manifest lists M1 batch-correction mirror path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_TEXT = (Path(__file__).resolve().parents[1] / "scripts" / "write_module3_export_manifest.py").read_text(
    encoding="utf-8"
)


def test_write_module3_export_manifest_includes_batch_correction_mirror_paths() -> None:
    assert "m1_batch_correction_mirror_paths_status.json" in _TEXT
    assert "m1.batch_correction_mirror_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_batch_correction_mirror_stub() -> None:
    assert "m1_batch_correction_mirror_integration_stub.json" in _TEXT
    assert "m1.batch_correction_mirror_integration_stub" in _TEXT
