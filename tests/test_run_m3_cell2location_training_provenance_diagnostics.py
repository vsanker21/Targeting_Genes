"""Training-path provenance diagnostics: fake cell2location, no GPU / no real fit."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from cell2location_test_doubles import fake_cell2location_modules

anndata = pytest.importorskip("anndata")


def test_run_training_path_signature_extract_sets_prov_diagnostic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_pkg, fake_models = fake_cell2location_modules()
    monkeypatch.setitem(sys.modules, "cell2location", fake_pkg)
    monkeypatch.setitem(sys.modules, "cell2location.models", fake_models)

    from run_m3_cell2location_orchestrate import _run_training_path

    ref = anndata.AnnData(
        X=np.zeros((4, 2), dtype=float),
        obs=pd.DataFrame({"lb": np.repeat("A", 4)}, index=[f"o{i}" for i in range(4)]),
        var=pd.DataFrame(index=pd.Index(["g1", "g2"], dtype=str)),
    )
    spat = anndata.AnnData(
        X=np.zeros((2, 2)),
        obs=pd.DataFrame(index=[f"s{i}" for i in range(2)]),
        var=pd.DataFrame(index=pd.Index(["g1", "g2"], dtype=str)),
    )
    prov: dict[str, Any] = {}
    train_cfg = {"reference_labels_key": "lb"}
    blk: dict[str, Any] = {}

    with pytest.raises(RuntimeError):
        _run_training_path(rr=tmp_path, ref=ref, spat=spat, blk=blk, train_cfg=train_cfg, prov=prov)

    assert "signature_extract_diagnostic" in prov
    assert isinstance(prov["signature_extract_diagnostic"], dict)
    assert "varm_keys" in prov["signature_extract_diagnostic"]
    assert "signature_extract_error" in prov
    assert "gene_intersection_diagnostic" not in prov
    json.loads(json.dumps(prov, default=str))


def test_run_training_path_gene_intersection_sets_prov_diagnostic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_pkg, fake_models = fake_cell2location_modules()
    monkeypatch.setitem(sys.modules, "cell2location", fake_pkg)
    monkeypatch.setitem(sys.modules, "cell2location.models", fake_models)

    from run_m3_cell2location_orchestrate import _run_training_path

    ref = anndata.AnnData(
        X=np.zeros((4, 2), dtype=float),
        obs=pd.DataFrame({"lb": np.repeat("A", 4)}, index=[f"o{i}" for i in range(4)]),
        var=pd.DataFrame(index=pd.Index(["g1", "g2"], dtype=str)),
    )
    ref.uns["mod"] = {"factor_names": np.array(["T1"])}
    ref.var["means_per_cluster_mu_fg_T1"] = [1.0, 2.0]

    spat = anndata.AnnData(
        X=np.zeros((2, 1)),
        obs=pd.DataFrame(index=[f"s{i}" for i in range(2)]),
        var=pd.DataFrame(index=pd.Index(["z9"], dtype=str)),
    )
    prov: dict[str, Any] = {}
    train_cfg = {"reference_labels_key": "lb", "min_shared_genes": 10}
    blk: dict[str, Any] = {}

    with pytest.raises(RuntimeError):
        _run_training_path(rr=tmp_path, ref=ref, spat=spat, blk=blk, train_cfg=train_cfg, prov=prov)

    gid = prov.get("gene_intersection_diagnostic")
    assert isinstance(gid, dict)
    assert gid["n_shared_genes"] == 0
    assert gid["min_shared_genes_required"] == 10
    assert gid["n_spatial_var"] == 1
    assert gid["n_signature_rows"] == 2
    assert "signature_extract_diagnostic" not in prov
    json.loads(json.dumps(prov, default=str))


def test_cell2location_provenance_json_default_str_coerces_numpy() -> None:
    import numpy as np

    from run_m3_cell2location_orchestrate import _cell2location_provenance_json

    s = _cell2location_provenance_json({"x": np.int64(3), "y": "ok"})
    out = json.loads(s)
    assert out["x"] == "3"
    assert out["y"] == "ok"
