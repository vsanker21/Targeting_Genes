"""Regression: M3 export manifest lists GDC STAR TCGA-GBM DEA path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TEXT = (_ROOT / "scripts" / "write_module3_export_manifest.py").read_text(encoding="utf-8")
_YAML = (_ROOT / "config" / "m3_repo_gdc_star_tcga_gbm_dea_outline_inputs.yaml").read_text(encoding="utf-8")


def test_write_module3_export_manifest_includes_repo_gdc_star_tcga_gbm_dea_paths() -> None:
    assert "m3_repo_gdc_star_tcga_gbm_dea_paths_status.json" in _TEXT
    assert "m3_sc.repo_gdc_star_tcga_gbm_dea_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_gdc_star_tcga_gbm_dea_stub() -> None:
    assert "m3_repo_gdc_star_tcga_gbm_dea_integration_stub.json" in _TEXT
    assert "m3_sc.repo_gdc_star_tcga_gbm_dea_integration_stub" in _TEXT


def test_gdc_star_tcga_gbm_outline_dea_tsvs_in_manifest() -> None:
    for needle in (
        "deseq2_results.tsv",
        "edger_qlf_results.tsv",
    ):
        assert needle in _YAML
    for path, tag in (
        (
            "results/module3/deseq2_tcga_gbm/primary_vs_recurrent/deseq2_results.tsv",
            "gdc_star.deseq2.primary_vs_recurrent.tsv",
        ),
        (
            "results/module3/deseq2_tcga_gbm/primary_vs_solid_tissue_normal/deseq2_results.tsv",
            "gdc_star.deseq2.primary_vs_solid_normal.tsv",
        ),
        (
            "results/module3/edger_tcga_gbm/primary_vs_recurrent/edger_qlf_results.tsv",
            "gdc_star.edger.primary_vs_recurrent.qlf_tsv",
        ),
        (
            "results/module3/edger_tcga_gbm/primary_vs_solid_tissue_normal/edger_qlf_results.tsv",
            "gdc_star.edger.primary_vs_solid_normal.qlf_tsv",
        ),
    ):
        assert path in _TEXT
        assert tag in _TEXT
