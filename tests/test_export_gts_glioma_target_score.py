"""GLIOMA-TARGET composite v1 columns from export_gts_candidate_table.apply_glioma_target_composite."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[1]
_EXPORT = _ROOT / "scripts" / "export_gts_candidate_table.py"
_GTS_YAML = _ROOT / "config" / "glioma_target_score.yaml"


def _load_export_mod():
    spec = importlib.util.spec_from_file_location("export_gts_candidate_table", _EXPORT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_glioma_target_config_exists_and_versioned() -> None:
    doc = yaml.safe_load(_GTS_YAML.read_text(encoding="utf-8"))
    assert doc.get("version") == "1.1"
    w = doc.get("weights") or {}
    s = float(w.get("E", 0)) + float(w.get("M", 0)) + float(w.get("D", 0)) + float(w.get("N", 0))
    assert abs(s - 1.0) < 1e-6


def test_apply_glioma_target_composite_columns_and_bounds() -> None:
    mod = _load_export_mod()
    cfg = yaml.safe_load(_GTS_YAML.read_text(encoding="utf-8"))
    out = pd.DataFrame(
        {
            "hgnc_symbol": ["A", "B", "C"],
            "gene_id": ["ENSG1.1", "ENSG2.1", "ENSG3.1"],
            "gts_evidence_tier": [2, 2, 3],
            "gts_stub_sort_metric": [10.0, 9.0, 8.0],
            "signed_neglog10_p": [50.0, 10.0, 5.0],
            "padj_bh": [0.01, 0.02, 0.04],
            "delta_log2_expression": [6.0, 3.0, 1.0],
            "depmap_crispr_median_gbm": [-2.5, -0.5, float("nan")],
            "outline_m21_high_confidence_screen": [True, True, False],
            "outline_m22_known_gbm_driver": [False, True, False],
        }
    )
    uni = {"A": 1.0, "B": 1.0, "C": 0.0}
    str_set = {"A", "B"}
    res = mod.apply_glioma_target_composite(
        out,
        "delta_log2_expression",
        cfg,
        symbol_uniprot=uni,
        string_set=str_set,
    )
    assert "glioma_target_score" in res.columns
    assert "glioma_target_tier" in res.columns
    assert "gts_sub_D_norm" in res.columns and "gts_sub_N_norm" in res.columns
    assert res["glioma_target_score"].between(0.0, 1.0).all()
    assert set(res["glioma_target_tier"].unique()).issubset({1, 2, 3, 4})
    # Stronger expression + dependency should not rank last after sort
    assert res.iloc[0]["hgnc_symbol"] == "A"


def test_apply_glioma_target_composite_disabled_sorts_legacy() -> None:
    mod = _load_export_mod()
    out = pd.DataFrame(
        {
            "hgnc_symbol": ["X", "Y"],
            "gene_id": ["ENSGx.1", "ENSGy.1"],
            "gts_evidence_tier": [1, 2],
            "gts_stub_sort_metric": [20.0, 10.0],
            "signed_neglog10_p": [5.0, 5.0],
            "padj_bh": [0.01, 0.01],
            "eff": [1.0, 2.0],
            "depmap_crispr_median_gbm": [float("nan"), float("nan")],
            "outline_m21_high_confidence_screen": [False, False],
            "outline_m22_known_gbm_driver": [False, False],
        }
    )
    res = mod.apply_glioma_target_composite(out, "eff", {"enabled": False})
    assert "glioma_target_score" not in res.columns
    assert res.iloc[0]["gts_evidence_tier"] == 1
