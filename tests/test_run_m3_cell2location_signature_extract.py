"""Unit tests for cell2location signature extraction helpers (no cell2location package required)."""

from __future__ import annotations

import json

import numpy as np
import pytest

anndata = pytest.importorskip("anndata")
import pandas as pd

from run_m3_cell2location_orchestrate import (
    _extract_signature_df,
    _intersect_spatial_and_signatures,
    _mod_factor_names,
    _try_extract_q05_signatures,
    _varm_to_dense_df,
)


def _ref_with_mod(genes: list[str], factor_names: list[str]) -> anndata.AnnData:
    ad = anndata.AnnData(X=np.zeros((2, len(genes))), var=pd.DataFrame(index=genes))
    ad.uns["mod"] = {"factor_names": np.array(factor_names)}
    return ad


def test_mod_factor_names_numpy_array() -> None:
    ad = anndata.AnnData(X=np.zeros((1, 1)))
    ad.uns["mod"] = {"factor_names": np.array(["A", "B"])}
    assert _mod_factor_names(ad) == ["A", "B"]


def test_mod_factor_names_missing() -> None:
    ad = anndata.AnnData(X=np.zeros((1, 1)))
    assert _mod_factor_names(ad) is None


def test_mod_factor_names_factor_names_underscore_in_mod() -> None:
    ad = anndata.AnnData(X=np.zeros((1, 1)))
    ad.uns["mod"] = {"factor_names_": ["p", "q"]}
    assert _mod_factor_names(ad) == ["p", "q"]


def test_mod_factor_names_top_level_uns() -> None:
    ad = anndata.AnnData(X=np.zeros((1, 1)))
    ad.uns["regressor_factor_names"] = np.array(["r", "s"])
    assert _mod_factor_names(ad) == ["r", "s"]


def test_extract_var_exact_factor_columns() -> None:
    genes = ["g1", "g2", "g3"]
    ad = _ref_with_mod(genes, ["T1", "T2"])
    for fn in ["T1", "T2"]:
        ad.var[f"means_per_cluster_mu_fg_{fn}"] = np.arange(len(genes), dtype=float)
    df = _extract_signature_df(ad)
    assert list(df.columns) == ["T1", "T2"]
    assert df.shape == (3, 2)


def test_extract_var_integer_suffix_columns() -> None:
    genes = ["g1", "g2"]
    ad = _ref_with_mod(genes, ["A", "B"])
    ad.var["means_per_cluster_mu_fg_0"] = [1.0, 2.0]
    ad.var["means_per_cluster_mu_fg_1"] = [3.0, 4.0]
    df = _extract_signature_df(ad)
    assert list(df.columns) == ["A", "B"]
    assert df.iloc[0, 0] == 1.0 and df.iloc[1, 1] == 4.0


def test_extract_varm_dense_genes_by_factors() -> None:
    genes = ["a", "b", "c"]
    ad = _ref_with_mod(genes, ["x", "y"])
    ad.varm["means_per_cluster_mu_fg"] = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    df = _extract_signature_df(ad)
    assert df.shape == (3, 2)
    assert list(df.columns) == ["x", "y"]


def test_varm_to_dense_df_transposed_via_stub() -> None:
    """AnnData varm must be (n_vars, K); some exports are (K, n_vars) — _varm_to_dense_df transposes."""

    class _Stub:
        n_vars = 2
        var_names = pd.Index(["a", "b"])
        varm = {"means_per_cluster_mu_fg": np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])}  # (K, G)

    df = _varm_to_dense_df(_Stub(), "means_per_cluster_mu_fg", ["p", "q", "r"])
    assert df.shape == (2, 3)
    assert np.allclose(df.iloc[0].values, [1.0, 3.0, 5.0])


def test_try_q05_var_columns() -> None:
    genes = ["g1", "g2"]
    ad = _ref_with_mod(genes, ["A", "B"])
    ad.var["q05_per_cluster_mu_fg_A"] = [0.1, 0.2]
    ad.var["q05_per_cluster_mu_fg_B"] = [0.3, 0.4]
    df = _try_extract_q05_signatures(ad, ["A", "B"])
    assert df is not None
    assert df.shape == (2, 2)


def test_try_q05_var_integer_suffix_without_factor_names() -> None:
    genes = ["g1", "g2"]
    ad = anndata.AnnData(X=np.zeros((1, 2)), var=pd.DataFrame(index=genes))
    ad.var["q05_per_cluster_mu_fg_0"] = [0.1, 0.2]
    ad.var["q05_per_cluster_mu_fg_1"] = [0.3, 0.4]
    df = _try_extract_q05_signatures(ad, None)
    assert df is not None
    assert list(df.columns) == ["0", "1"]
    assert df.shape == (2, 2)


def test_extract_means_without_mod_factor_names_integer_suffix() -> None:
    genes = ["g1", "g2"]
    ad = anndata.AnnData(X=np.zeros((1, 2)), var=pd.DataFrame(index=genes))
    ad.var["means_per_cluster_mu_fg_0"] = [1.0, 2.0]
    ad.var["means_per_cluster_mu_fg_1"] = [3.0, 4.0]
    df = _extract_signature_df(ad)
    assert list(df.columns) == ["0", "1"]
    assert df.iloc[0, 0] == 1.0


def test_extract_means_named_var_suffixes_without_mod_sorted_lex() -> None:
    genes = ["g1", "g2"]
    ad = anndata.AnnData(X=np.zeros((1, 2)), var=pd.DataFrame(index=genes))
    ad.var["means_per_cluster_mu_fg_TypeB"] = [1.0, 2.0]
    ad.var["means_per_cluster_mu_fg_TypeA"] = [3.0, 4.0]
    df = _extract_signature_df(ad)
    assert list(df.columns) == ["TypeA", "TypeB"]
    assert float(df.iloc[0, 0]) == 3.0


def test_extract_varm_noncanonical_key_without_mod() -> None:
    genes = ["a", "b", "c"]
    ad = anndata.AnnData(X=np.zeros((1, 3)), var=pd.DataFrame(index=genes))
    ad.varm["means_per_cluster_mu_fg_export"] = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    df = _extract_signature_df(ad)
    assert df.shape == (3, 2)
    assert list(df.columns) == ["0", "1"]


def test_extract_uns_means_matrix_without_mod() -> None:
    genes = ["a", "b"]
    ad = anndata.AnnData(X=np.zeros((1, 2)), var=pd.DataFrame(index=genes))
    ad.uns["means_per_cluster_mu_fg_stash"] = np.array([[1.0, 2.0], [3.0, 4.0]])
    df = _extract_signature_df(ad)
    assert df.shape == (2, 2)


def test_extract_varm_dataframe_without_mod() -> None:
    genes = ["a", "b", "c"]
    ad = anndata.AnnData(X=np.zeros((1, 3)), var=pd.DataFrame(index=genes))
    ad.varm["means_per_cluster_mu_fg_table"] = pd.DataFrame(
        np.arange(6, dtype=float).reshape(3, 2),
        index=ad.var_names.astype(str),
        columns=["c0", "c1"],
    )
    df = _extract_signature_df(ad)
    assert df.shape == (3, 2)


def test_try_q05_alternate_varm_key() -> None:
    genes = ["a", "b", "c"]
    ad = _ref_with_mod(genes, ["x", "y"])
    ad.varm["q05_per_cluster_mu_fg_f"] = np.array([[0.5, 0.6], [0.7, 0.8], [0.9, 1.0]])
    df = _try_extract_q05_signatures(ad, ["x", "y"])
    assert df is not None
    assert df.shape == (3, 2)


def test_prefer_q05_before_means() -> None:
    genes = ["g1", "g2"]
    ad = _ref_with_mod(genes, ["A", "B"])
    ad.var["means_per_cluster_mu_fg_A"] = [10.0, 20.0]
    ad.var["means_per_cluster_mu_fg_B"] = [30.0, 40.0]
    ad.var["q05_per_cluster_mu_fg_A"] = [1.0, 2.0]
    ad.var["q05_per_cluster_mu_fg_B"] = [3.0, 4.0]
    df = _extract_signature_df(ad, prefer_q05=True)
    assert float(df.iloc[0, 0]) == 1.0
    df_m = _extract_signature_df(ad, prefer_q05=False)
    assert float(df_m.iloc[0, 0]) == 10.0


def test_extract_failure_includes_diagnostic_json() -> None:
    ad = anndata.AnnData(X=np.zeros((1, 1)), var=pd.DataFrame(index=["g1"]))
    ad.uns["mod"] = {"factor_names": ["A"]}
    with pytest.raises(RuntimeError) as exc:
        _extract_signature_df(ad)
    msg = str(exc.value)
    assert "Diagnostic snapshot" in msg
    blob = msg.split("Diagnostic snapshot: ", 1)[1]
    diag = json.loads(blob)
    assert "varm_keys" in diag
    assert "layer_keys_sample" in diag
    assert "uns_keys_per_cluster_guess" in diag


def test_intersect_spatial_and_signatures_order() -> None:
    genes_sp = [f"g{i}" for i in range(12)]
    spat = anndata.AnnData(X=np.zeros((1, 12)), var=pd.DataFrame(index=genes_sp))
    sig = pd.DataFrame(
        np.arange(12 * 2).reshape(12, 2),
        index=genes_sp,
        columns=["a", "b"],
    )
    sub_spat, sub_sig = _intersect_spatial_and_signatures(spat, sig)
    assert list(sub_spat.var_names) == genes_sp
    assert sub_sig.shape == (12, 2)


def test_intersect_respects_min_shared_genes() -> None:
    genes_sp = [f"g{i}" for i in range(5)]
    spat = anndata.AnnData(X=np.zeros((1, 5)), var=pd.DataFrame(index=genes_sp))
    sig = pd.DataFrame(np.zeros((5, 2)), index=genes_sp, columns=["a", "b"])
    with pytest.raises(RuntimeError, match="need at least 10"):
        _intersect_spatial_and_signatures(spat, sig, min_shared_genes=10)
    sub_sp, sub_si = _intersect_spatial_and_signatures(spat, sig, min_shared_genes=5)
    assert sub_sp.n_vars == 5


def test_varm_to_dense_df_invalid_shape_raises() -> None:
    class _Stub:
        n_vars = 3
        var_names = pd.Index(["a", "b", "c"])
        varm = {"means_per_cluster_mu_fg": np.zeros((99, 99))}

    with pytest.raises(RuntimeError, match="does not match"):
        _varm_to_dense_df(_Stub(), "means_per_cluster_mu_fg", ["x"])
