"""Regression: M6 export manifest lists compound library mirror path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_TEXT = (Path(__file__).resolve().parents[1] / "scripts" / "write_module6_export_manifest.py").read_text(
    encoding="utf-8"
)


def test_write_module6_export_manifest_includes_compound_library_mirror_paths() -> None:
    assert "m6_compound_library_mirror_paths_status.json" in _TEXT
    assert "module6.m6_compound_library_mirror_paths_status" in _TEXT


def test_write_module6_export_manifest_includes_compound_library_mirror_stub() -> None:
    assert "m6_compound_library_mirror_integration_stub.json" in _TEXT
    assert "module6.m6_compound_library_mirror_integration_stub" in _TEXT
