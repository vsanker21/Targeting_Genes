"""Regression: M3 export manifest lists cohort + Verhaak subtype path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TEXT = (_ROOT / "scripts" / "write_module3_export_manifest.py").read_text(encoding="utf-8")
_YAML = (_ROOT / "config" / "m3_repo_cohort_verhaak_subtype_outline_inputs.yaml").read_text(encoding="utf-8")


def test_write_module3_export_manifest_includes_repo_cohort_verhaak_subtype_paths() -> None:
    assert "m3_repo_cohort_verhaak_subtype_paths_status.json" in _TEXT
    assert "m3_sc.repo_cohort_verhaak_subtype_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_cohort_verhaak_subtype_stub() -> None:
    assert "m3_repo_cohort_verhaak_subtype_integration_stub.json" in _TEXT
    assert "m3_sc.repo_cohort_verhaak_subtype_integration_stub" in _TEXT


def test_cohort_verhaak_outline_subtype_tsvs_in_manifest() -> None:
    assert "tcga_gbm_verhaak_subtype_scores.tsv" in _YAML
    assert "mean_log_tpm_by_verhaak_subtype.tsv" in _YAML
    assert "results/module3/tcga_gbm_verhaak_subtype_scores.tsv" in _TEXT
    assert "verhaak.subtype_scores_tsv" in _TEXT
    assert "results/module3/mean_log_tpm_by_verhaak_subtype.tsv" in _TEXT
    assert "verhaak.mean_log_tpm_by_subtype_tsv" in _TEXT


def test_cohort_verhaak_outline_summary_and_mean_tpm_provenance_in_manifest() -> None:
    assert "tcga_gbm_verhaak_subtype_summary.json" in _YAML
    assert "mean_log_tpm_by_verhaak_subtype_provenance.json" in _YAML
    assert "results/module3/tcga_gbm_verhaak_subtype_summary.json" in _TEXT
    assert "verhaak.subtype_summary" in _TEXT
    assert "results/module3/mean_log_tpm_by_verhaak_subtype_provenance.json" in _TEXT
    assert "mean_log_tpm_subtype.provenance" in _TEXT
