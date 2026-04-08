"""Smoke tests for Cell2location orchestrator (paths + validate-only; no full training)."""

from __future__ import annotations

import builtins
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from cell2location_test_doubles import fake_cell2location_modules

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "run_m3_cell2location_orchestrate.py"


def test_cell2location_config_path_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import run_m3_cell2location_orchestrate as m

    rr = tmp_path / "repo"
    (rr / "config").mkdir(parents=True)
    alt = rr / "config" / "alt_cell2location.yaml"
    alt.write_text(
        "m3_deconvolution_cell2location:\n  reference_h5ad: a.h5ad\n  spatial_h5ad: b.h5ad\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(m, "repo_root", lambda: rr)
    monkeypatch.setenv("GLIOMA_TARGET_M3_CELL2LOCATION_CONFIG", "config/alt_cell2location.yaml")
    assert m.cell2location_config_path().resolve() == alt.resolve()


def test_cell2location_orchestrate_fails_when_h5ad_missing(tmp_path: Path) -> None:
    dr = tmp_path / "data"
    dr.mkdir()
    r = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        cwd=str(_ROOT),
        env={**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(dr)},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 1
    combined = (r.stderr or "") + (r.stdout or "")
    assert "Missing reference h5ad" in combined or "Missing spatial h5ad" in combined


def test_cell2location_orchestrate_validate_only_writes_provenance_in_repo_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    anndata = pytest.importorskip("anndata")
    import numpy as np
    import pandas as pd

    rr = tmp_path / "repo"
    (rr / "config").mkdir(parents=True)
    dr = tmp_path / "data"
    rel = Path("m3_spatial_deconv/cell2location")
    (dr / rel).mkdir(parents=True)
    ref_p = dr / rel / "ref.h5ad"
    spat_p = dr / rel / "spat.h5ad"
    ad_ref = anndata.AnnData(
        np.zeros((2, 2), dtype=float),
        obs=pd.DataFrame(index=["a0", "a1"]),
        var=pd.DataFrame(index=["g1", "g2"]),
    )
    ad_spat = anndata.AnnData(
        np.zeros((1, 2), dtype=float),
        obs=pd.DataFrame(index=["s0"]),
        var=pd.DataFrame(index=["g1", "g2"]),
    )
    ad_ref.write_h5ad(ref_p)
    ad_spat.write_h5ad(spat_p)

    cfg = """m3_deconvolution_cell2location:
  reference_h5ad: m3_spatial_deconv/cell2location/ref.h5ad
  spatial_h5ad: m3_spatial_deconv/cell2location/spat.h5ad
  training:
    enabled: false
"""
    (rr / "config" / "m3_deconvolution_cell2location_inputs.yaml").write_text(cfg, encoding="utf-8")

    import run_m3_cell2location_orchestrate as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    monkeypatch.setattr(m, "data_root", lambda: dr)

    rc = m.main()
    assert rc == 0

    prov_p = rr / "results" / "module3" / "m3_deconvolution_cell2location" / "cell2location_run_provenance.json"
    flag_p = rr / "results" / "module3" / "m3_deconvolution_cell2location" / "cell2location_run.flag"
    assert prov_p.is_file()
    assert flag_p.is_file()
    doc = json.loads(prov_p.read_text(encoding="utf-8"))
    assert doc.get("status") == "inputs_ok"
    assert doc.get("training_enabled") is False
    assert int(doc.get("n_ref_obs", 0)) == 2
    assert int(doc.get("n_spatial_obs", 0)) == 1


def test_main_training_failed_on_import_error_writes_provenance_and_no_ok_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    anndata = pytest.importorskip("anndata")
    import numpy as np
    import pandas as pd

    rr = tmp_path / "repo"
    (rr / "config").mkdir(parents=True)
    dr = tmp_path / "data"
    rel = Path("m3_spatial_deconv/cell2location")
    (dr / rel).mkdir(parents=True)
    ref_p = dr / rel / "ref.h5ad"
    spat_p = dr / rel / "spat.h5ad"
    ad_ref = anndata.AnnData(
        np.zeros((2, 2), dtype=float),
        obs=pd.DataFrame(index=["a0", "a1"]),
        var=pd.DataFrame(index=["g1", "g2"]),
    )
    ad_spat = anndata.AnnData(
        np.zeros((1, 2), dtype=float),
        obs=pd.DataFrame(index=["s0"]),
        var=pd.DataFrame(index=["g1", "g2"]),
    )
    ad_ref.write_h5ad(ref_p)
    ad_spat.write_h5ad(spat_p)

    cfg = """m3_deconvolution_cell2location:
  reference_h5ad: m3_spatial_deconv/cell2location/ref.h5ad
  spatial_h5ad: m3_spatial_deconv/cell2location/spat.h5ad
  training:
    enabled: true
    reference_labels_key: cell_type
"""
    (rr / "config" / "m3_deconvolution_cell2location_inputs.yaml").write_text(cfg, encoding="utf-8")

    out_d = rr / "results" / "module3" / "m3_deconvolution_cell2location"
    out_d.mkdir(parents=True)
    flag_p = out_d / "cell2location_run.flag"
    flag_p.write_text("ok\n", encoding="utf-8")

    orig_imp = builtins.__import__

    def guarded_import(
        name: str,
        globals_arg: dict | None = None,
        locals_arg: dict | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ):
        if name == "cell2location":
            raise ImportError("blocked_for_test")
        return orig_imp(name, globals_arg, locals_arg, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    import run_m3_cell2location_orchestrate as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    monkeypatch.setattr(m, "data_root", lambda: dr)

    assert m.main() == 1

    prov_p = out_d / "cell2location_run_provenance.json"
    assert prov_p.is_file()
    assert not flag_p.exists()
    doc = json.loads(prov_p.read_text(encoding="utf-8"))
    assert doc.get("status") == "training_failed"
    assert doc.get("cell2location_import_ok") is False
    assert doc.get("training_enabled") is True
    err = capsys.readouterr().err
    assert "cell2location_run_provenance.json" in err
    assert "cell2location_run.flag" in err


def test_main_training_path_nonzero_rc_prints_stderr_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    anndata = pytest.importorskip("anndata")
    import numpy as np
    import pandas as pd

    fake_pkg, fake_models = fake_cell2location_modules()
    monkeypatch.setitem(sys.modules, "cell2location", fake_pkg)
    monkeypatch.setitem(sys.modules, "cell2location.models", fake_models)

    rr = tmp_path / "repo"
    (rr / "config").mkdir(parents=True)
    dr = tmp_path / "data"
    rel = Path("m3_spatial_deconv/cell2location")
    (dr / rel).mkdir(parents=True)
    ref_p = dr / rel / "ref.h5ad"
    spat_p = dr / rel / "spat.h5ad"
    ad_ref = anndata.AnnData(
        np.zeros((2, 2), dtype=float),
        obs=pd.DataFrame({"cell_type": ["A", "B"]}, index=["a0", "a1"]),
        var=pd.DataFrame(index=["g1", "g2"]),
    )
    ad_spat = anndata.AnnData(
        np.zeros((1, 2), dtype=float),
        obs=pd.DataFrame(index=["s0"]),
        var=pd.DataFrame(index=["g1", "g2"]),
    )
    ad_ref.write_h5ad(ref_p)
    ad_spat.write_h5ad(spat_p)

    cfg = """m3_deconvolution_cell2location:
  reference_h5ad: m3_spatial_deconv/cell2location/ref.h5ad
  spatial_h5ad: m3_spatial_deconv/cell2location/spat.h5ad
  training:
    enabled: true
    reference_labels_key: cell_type
"""
    (rr / "config" / "m3_deconvolution_cell2location_inputs.yaml").write_text(cfg, encoding="utf-8")

    import run_m3_cell2location_orchestrate as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    monkeypatch.setattr(m, "data_root", lambda: dr)
    monkeypatch.setattr(m, "_run_training_path", lambda **kwargs: 1)

    assert m.main() == 1
    err = capsys.readouterr().err
    assert "exited with code 1" in err
    assert "cell2location_run_provenance.json" in err
    assert "cell2location_run.flag" in err


def test_main_training_path_exception_prints_stderr_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    anndata = pytest.importorskip("anndata")
    import numpy as np
    import pandas as pd

    fake_pkg, fake_models = fake_cell2location_modules()
    monkeypatch.setitem(sys.modules, "cell2location", fake_pkg)
    monkeypatch.setitem(sys.modules, "cell2location.models", fake_models)

    rr = tmp_path / "repo"
    (rr / "config").mkdir(parents=True)
    dr = tmp_path / "data"
    rel = Path("m3_spatial_deconv/cell2location")
    (dr / rel).mkdir(parents=True)
    ref_p = dr / rel / "ref.h5ad"
    spat_p = dr / rel / "spat.h5ad"
    ad_ref = anndata.AnnData(
        np.zeros((2, 2), dtype=float),
        obs=pd.DataFrame({"cell_type": ["A", "B"]}, index=["a0", "a1"]),
        var=pd.DataFrame(index=["g1", "g2"]),
    )
    ad_spat = anndata.AnnData(
        np.zeros((1, 2), dtype=float),
        obs=pd.DataFrame(index=["s0"]),
        var=pd.DataFrame(index=["g1", "g2"]),
    )
    ad_ref.write_h5ad(ref_p)
    ad_spat.write_h5ad(spat_p)

    cfg = """m3_deconvolution_cell2location:
  reference_h5ad: m3_spatial_deconv/cell2location/ref.h5ad
  spatial_h5ad: m3_spatial_deconv/cell2location/spat.h5ad
  training:
    enabled: true
    reference_labels_key: cell_type
"""
    (rr / "config" / "m3_deconvolution_cell2location_inputs.yaml").write_text(cfg, encoding="utf-8")

    import run_m3_cell2location_orchestrate as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    monkeypatch.setattr(m, "data_root", lambda: dr)

    def boom(**_kwargs: object) -> int:
        raise ValueError("training_path_boom")

    monkeypatch.setattr(m, "_run_training_path", boom)

    assert m.main() == 1
    err = capsys.readouterr().err
    assert "Cell2location training failed" in err
    assert "training_path_boom" in err
    assert "cell2location_run_provenance.json" in err
    assert "cell2location_run.flag" in err

    out_d = rr / "results" / "module3" / "m3_deconvolution_cell2location"
    prov_p = out_d / "cell2location_run_provenance.json"
    assert prov_p.is_file()
    doc = json.loads(prov_p.read_text(encoding="utf-8"))
    assert doc.get("status") == "training_failed"
    assert "ValueError" in str(doc.get("training_error", ""))


def test_cell2location_orchestrate_imports_main() -> None:
    import run_m3_cell2location_orchestrate as m

    assert callable(m.main)
