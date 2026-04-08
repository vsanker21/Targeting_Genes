"""Regression: M7 export manifest lists external GTS score mirror path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_TEXT = (Path(__file__).resolve().parents[1] / "scripts" / "write_module7_export_manifest.py").read_text(
    encoding="utf-8"
)


def test_write_module7_export_manifest_includes_gts_external_score_mirror_paths() -> None:
    assert "m7_gts_external_score_mirror_paths_status.json" in _TEXT
    assert "m7_gts_external_score_mirror_paths_status" in _TEXT


def test_write_module7_export_manifest_includes_gts_external_score_mirror_stub() -> None:
    assert "m7_gts_external_score_mirror_integration_stub.json" in _TEXT
    assert "m7_gts_external_score_mirror_integration_stub" in _TEXT
