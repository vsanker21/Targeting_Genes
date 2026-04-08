"""Regression: M3 export manifest lists in-repo GDC matrix path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TEXT = (_ROOT / "scripts" / "write_module3_export_manifest.py").read_text(encoding="utf-8")
_YAML = (_ROOT / "config" / "m3_repo_gdc_expression_matrix_outline_inputs.yaml").read_text(encoding="utf-8")


def test_write_module3_export_manifest_includes_repo_gdc_expression_matrix_paths() -> None:
    assert "m3_repo_gdc_expression_matrix_paths_status.json" in _TEXT
    assert "m3_sc.repo_gdc_expression_matrix_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_gdc_expression_matrix_stub() -> None:
    assert "m3_repo_gdc_expression_matrix_integration_stub.json" in _TEXT
    assert "m3_sc.repo_gdc_expression_matrix_integration_stub" in _TEXT


def test_gdc_expression_matrix_outline_inventories_cohort_summary_json() -> None:
    assert "gdc_counts_cohort_summary.json" in _YAML
    assert "results/module2/gdc_counts_cohort_summary.json" in _TEXT


def test_export_manifest_lists_module2_gdc_matrix_artifacts() -> None:
    for needle, tag in (
        ("results/module2/tcga_gbm_star_tpm_matrix.parquet", "gdc_repo.tpm_matrix_parquet"),
        ("results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet", "gdc_repo.counts_matrix_parquet"),
        ("results/module2/tcga_gbm_sample_meta.tsv", "gdc_repo.sample_meta_tsv"),
        ("results/module2/gdc_counts_matrix_qc.json", "gdc_repo.counts_matrix_qc"),
        ("results/module2/gdc_counts_cohort_summary.json", "gdc_repo.counts_cohort_summary"),
    ):
        assert needle in _TEXT
        assert tag in _TEXT
