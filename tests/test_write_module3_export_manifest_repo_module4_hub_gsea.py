"""Regression: M3 export manifest lists M4 hub + GSEA path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TEXT = (_ROOT / "scripts" / "write_module3_export_manifest.py").read_text(encoding="utf-8")
_YAML = (_ROOT / "config" / "m3_repo_module4_hub_gsea_outline_inputs.yaml").read_text(encoding="utf-8")


def test_write_module3_export_manifest_includes_repo_module4_hub_gsea_paths() -> None:
    assert "m3_repo_module4_hub_gsea_paths_status.json" in _TEXT
    assert "m3_sc.repo_module4_hub_gsea_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_module4_hub_gsea_stub() -> None:
    assert "m3_repo_module4_hub_gsea_integration_stub.json" in _TEXT
    assert "m3_sc.repo_module4_hub_gsea_integration_stub" in _TEXT


def test_module4_hub_gsea_outline_data_paths_in_manifest() -> None:
    assert "wgcna_hub_expr_subset.parquet" in _YAML
    assert "results/module4/wgcna_hub_expr_subset.parquet" in _TEXT
    assert "m4.hub_gsea.wgcna_expr_subset_parquet" in _TEXT
    assert "dea_welch_signed_neg_log10_p.rnk" in _YAML
    assert "results/module4/gsea/dea_welch_signed_neg_log10_p.rnk" in _TEXT
    assert "m4.hub_gsea.gsea_welch_signed_neg_log10_p_rnk" in _TEXT
