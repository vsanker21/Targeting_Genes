"""Regression: M3 export manifest lists m3_repo_m1_* path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_TEXT = (Path(__file__).resolve().parents[1] / "scripts" / "write_module3_export_manifest.py").read_text(
    encoding="utf-8"
)


def test_manifest_includes_repo_m1_outline() -> None:
    assert "m3_repo_m1_outline_paths_status.json" in _TEXT
    assert "m3_sc.repo_m1_outline_paths_status" in _TEXT
    assert "m3_repo_m1_outline_integration_stub.json" in _TEXT
    assert "m3_sc.repo_m1_outline_integration_stub" in _TEXT


def test_manifest_includes_repo_m1_harmony_batch() -> None:
    assert "m3_repo_m1_harmony_batch_paths_status.json" in _TEXT
    assert "m3_sc.repo_m1_harmony_batch_paths_status" in _TEXT
    assert "m3_repo_m1_harmony_batch_integration_stub.json" in _TEXT


def test_manifest_includes_repo_m1_reference_gdc() -> None:
    assert "m3_repo_m1_reference_gdc_paths_status.json" in _TEXT
    assert "m3_sc.repo_m1_reference_gdc_paths_status" in _TEXT
    assert "m3_repo_m1_reference_gdc_integration_stub.json" in _TEXT


def test_manifest_includes_repo_m1_batch_correction_mirror() -> None:
    assert "m3_repo_m1_batch_correction_mirror_paths_status.json" in _TEXT
    assert "m3_sc.repo_m1_batch_correction_mirror_paths_status" in _TEXT
    assert "m3_repo_m1_batch_correction_mirror_integration_stub.json" in _TEXT
