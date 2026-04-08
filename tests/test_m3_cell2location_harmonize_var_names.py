"""Unit tests for training-time gene name harmonization in run_m3_cell2location_orchestrate."""

from __future__ import annotations

import numpy as np
import pytest

from run_m3_cell2location_orchestrate import _harmonize_var_names_adata


@pytest.mark.parametrize(
    ("strip_v", "upper", "inp", "expect_any_of"),
    [
        (True, False, ["TP53.1", "EGFR.2"], ["TP53", "EGFR"]),
        (False, True, ["tp53", "egfr"], ["TP53", "EGFR"]),
        (True, True, ["tp53.10"], ["TP53"]),
    ],
)
def test_harmonize_var_names(
    strip_v: bool, upper: bool, inp: list[str], expect_any_of: list[str]
) -> None:
    anndata = pytest.importorskip("anndata")
    X = np.ones((2, len(inp)), dtype=np.float32)
    ad = anndata.AnnData(X=X)
    ad.var_names = inp
    ad.obs_names = ["a", "b"]
    hb = {
        "enabled": True,
        "strip_version_suffix": strip_v,
        "uppercase": upper,
    }
    out = _harmonize_var_names_adata(ad, hb)
    got = list(out.var_names.astype(str))
    assert set(got) == set(expect_any_of)
    assert out.n_vars == len(expect_any_of)
