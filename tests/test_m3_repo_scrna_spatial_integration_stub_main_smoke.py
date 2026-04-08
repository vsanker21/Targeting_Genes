"""Smoke: m3_repo_scrna_spatial_integration_stub main() with paths_status + deconv stub JSON."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_repo_scrna_spatial_integration_stub_main_writes_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rr = tmp_path / "repo"
    (rr / "config").mkdir(parents=True)
    shutil.copyfile(
        _ROOT / "config" / "m3_repo_scrna_spatial_outline_inputs.yaml",
        rr / "config" / "m3_repo_scrna_spatial_outline_inputs.yaml",
    )
    mod3 = rr / "results" / "module3"
    mod3.mkdir(parents=True)

    (mod3 / "m3_repo_scrna_spatial_paths_status.json").write_text(
        json.dumps({"groups": []}),
        encoding="utf-8",
    )
    dec = {
        "readiness_tier": "B",
        "artifact_kind": "m3_deconvolution_integration_stub",
        "checklist": {
            "in_repo_cell2location_or_rctd": True,
            "cell2location_run_status": "inputs_ok",
            "rctd_run_status": "create_failed",
        },
    }
    (mod3 / "m3_deconvolution_integration_stub.json").write_text(
        json.dumps(dec),
        encoding="utf-8",
    )

    import m3_repo_scrna_spatial_integration_stub as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    assert m.main() == 0

    out = mod3 / "m3_repo_scrna_spatial_integration_stub.json"
    fl = mod3 / "m3_repo_scrna_spatial_integration_stub.flag"
    assert out.is_file()
    assert fl.is_file()
    payload = json.loads(out.read_text(encoding="utf-8"))
    echo = payload.get("m3_deconvolution_integration_stub_echo") or {}
    assert echo.get("readiness_tier") == "B"
    assert echo.get("in_repo_cell2location_or_rctd") is True
    assert echo.get("cell2location_run_status") == "inputs_ok"
    assert echo.get("rctd_run_status") == "create_failed"
    assert payload.get("artifact_kind") == "m3_repo_scrna_spatial_integration_stub"
    assert payload.get("blockers") == []
