"""Regression: M3 export manifest lists TCGA + recount3 + LINCS mirror path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_TEXT = (Path(__file__).resolve().parents[1] / "scripts" / "write_module3_export_manifest.py").read_text(
    encoding="utf-8"
)


def test_write_module3_export_manifest_includes_tcga_recount_lincs_paths() -> None:
    assert "m3_tcga_recount_lincs_mirror_paths_status.json" in _TEXT
    assert "m3_sc.tcga_recount_lincs_mirror_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_tcga_recount_lincs_stub() -> None:
    assert "m3_tcga_recount_lincs_mirror_integration_stub.json" in _TEXT
    assert "m3_sc.tcga_recount_lincs_mirror_integration_stub" in _TEXT
