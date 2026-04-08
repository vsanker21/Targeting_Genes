"""Regression: M6 export manifest lists structure/ADMET integration stub artifacts."""

from __future__ import annotations

from pathlib import Path

_TEXT = (Path(__file__).resolve().parents[1] / "scripts" / "write_module6_export_manifest.py").read_text(
    encoding="utf-8"
)


def test_write_module6_export_manifest_includes_admet_stub_paths() -> None:
    assert "structure_admet_integration_stub.json" in _TEXT
    assert "module6.structure_admet_integration_stub" in _TEXT
