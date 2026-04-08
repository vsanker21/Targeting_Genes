"""Regression: M6 export manifest lists toxicity outline path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_TEXT = (Path(__file__).resolve().parents[1] / "scripts" / "write_module6_export_manifest.py").read_text(
    encoding="utf-8"
)


def test_write_module6_export_manifest_includes_toxicity_paths() -> None:
    assert "m6_toxicity_paths_status.json" in _TEXT
    assert "module6.m6_toxicity_paths_status" in _TEXT


def test_write_module6_export_manifest_includes_toxicity_stub() -> None:
    assert "m6_toxicity_integration_stub.json" in _TEXT
    assert "module6.m6_toxicity_integration_stub" in _TEXT
