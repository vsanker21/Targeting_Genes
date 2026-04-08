"""Regression: M3 export manifest lists recount3 bulk DEA path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TEXT = (_ROOT / "scripts" / "write_module3_export_manifest.py").read_text(encoding="utf-8")
_YAML = (_ROOT / "config" / "m3_repo_recount3_bulk_dea_outline_inputs.yaml").read_text(encoding="utf-8")


def test_write_module3_export_manifest_includes_repo_recount3_bulk_dea_paths() -> None:
    assert "m3_repo_recount3_bulk_dea_paths_status.json" in _TEXT
    assert "m3_sc.repo_recount3_bulk_dea_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_recount3_bulk_dea_stub() -> None:
    assert "m3_repo_recount3_bulk_dea_integration_stub.json" in _TEXT
    assert "m3_sc.repo_recount3_bulk_dea_integration_stub" in _TEXT


def test_recount3_bulk_dea_outline_includes_manifest_provenance_and_sample_meta() -> None:
    for needle in (
        "deseq2_provenance.json",
        "edger_provenance.json",
        "deseq2_results.tsv",
        "edger_qlf_results.tsv",
        "recount3_de_sample_meta.tsv",
    ):
        assert needle in _YAML
    for needle in (
        "deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_provenance.json",
        "deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_provenance.json",
        "deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_results.tsv",
        "deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_qlf_results.tsv",
        "deseq2_recount3_tcga_gbm_vs_gtex_brain/recount3_de_sample_meta.tsv",
    ):
        assert needle in _TEXT


def test_export_manifest_lists_recount3_bulk_dea_result_tsv_tags() -> None:
    assert "recount3.deseq2_results_tsv" in _TEXT
    assert "recount3.edger_qlf_results_tsv" in _TEXT
