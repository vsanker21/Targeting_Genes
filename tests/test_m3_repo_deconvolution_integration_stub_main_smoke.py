"""Smoke: m3_repo_deconvolution_integration_stub main() with prerequisite stub JSON files."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_repo_deconv_integration_stub_main_writes_echo_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rr = tmp_path / "repo"
    dr = tmp_path / "data"
    dr.mkdir()
    (rr / "config").mkdir(parents=True)
    shutil.copyfile(
        _ROOT / "config" / "m3_repo_deconvolution_outline_inputs.yaml",
        rr / "config" / "m3_repo_deconvolution_outline_inputs.yaml",
    )
    mod3 = rr / "results" / "module3"
    mod3.mkdir(parents=True)

    dec_payload = {
        "readiness_tier": "C",
        "artifact_kind": "m3_deconvolution_integration_stub",
        "checklist": {
            "in_repo_cell2location_or_rctd": True,
            "cell2location_run_status": "training_failed",
        },
        "recommended_next_steps": ["hint one"],
    }
    (mod3 / "m3_deconvolution_integration_stub.json").write_text(
        json.dumps(dec_payload), encoding="utf-8"
    )
    (mod3 / "m3_repo_scrna_spatial_integration_stub.json").write_text("{}", encoding="utf-8")

    import m3_repo_deconvolution_integration_stub as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    monkeypatch.setattr(m, "data_root", lambda: dr)

    assert m.main() == 0

    out = mod3 / "m3_repo_deconvolution_integration_stub.json"
    fl = mod3 / "m3_repo_deconvolution_integration_stub.flag"
    assert out.is_file()
    assert fl.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    echo = doc.get("m3_deconvolution_integration_stub_echo") or {}
    assert echo.get("readiness_tier") == "C"
    assert echo.get("n_recommended_next_steps") == 1
    ch = echo.get("checklist") or {}
    assert ch.get("in_repo_cell2location_or_rctd") is True
    assert ch.get("cell2location_run_status") == "training_failed"
