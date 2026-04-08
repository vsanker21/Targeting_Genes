"""Regression: M4 export manifest lists GSEA mirror path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_TEXT = (Path(__file__).resolve().parents[1] / "scripts" / "write_module4_export_manifest.py").read_text(
    encoding="utf-8"
)


def test_write_module4_export_manifest_includes_gsea_mirror_paths() -> None:
    assert "m4_gsea_mirror_paths_status.json" in _TEXT
    assert "m4_gsea_mirror_paths_status" in _TEXT


def test_write_module4_export_manifest_includes_gsea_mirror_stub() -> None:
    assert "m4_gsea_mirror_integration_stub.json" in _TEXT
    assert "m4_gsea_mirror_integration_stub" in _TEXT
