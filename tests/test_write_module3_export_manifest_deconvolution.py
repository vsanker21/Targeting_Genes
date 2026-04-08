"""Regression: M3 export manifest lists deconvolution outline path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_TEXT = (Path(__file__).resolve().parents[1] / "scripts" / "write_module3_export_manifest.py").read_text(
    encoding="utf-8"
)


def test_write_module3_export_manifest_includes_deconvolution_paths() -> None:
    assert "m3_deconvolution_paths_status.json" in _TEXT
    assert "m3_sc.deconvolution_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_deconvolution_stub() -> None:
    assert "m3_deconvolution_integration_stub.json" in _TEXT
    assert "m3_sc.deconvolution_integration_stub" in _TEXT


def test_write_module3_export_manifest_includes_rctd_and_cell2location_runs() -> None:
    assert "m3_deconvolution_rctd/rctd_run_provenance.json" in _TEXT
    assert "m3_sc.deconvolution_rctd_provenance" in _TEXT
    assert "m3_deconvolution_cell2location/cell2location_run_provenance.json" in _TEXT
    assert "m3_sc.deconvolution_cell2location_provenance" in _TEXT
    assert "spatial_cell2location.h5ad" in _TEXT
    assert "m3_sc.deconvolution_cell2location_result_h5ad" in _TEXT
    assert "spot_cell_abundance_means.tsv" in _TEXT
    assert "m3_sc.deconvolution_cell2location_abundance_tsv" in _TEXT


