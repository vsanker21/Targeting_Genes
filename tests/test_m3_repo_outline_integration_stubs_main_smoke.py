"""Smoke: M3 repo outline integration stubs write JSON + flag with prerequisites present."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _prep_cfg(rr: Path, cfg_name: str) -> None:
    (rr / "config").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_ROOT / "config" / cfg_name, rr / "config" / cfg_name)


def test_m3_repo_public_inputs_integration_stub_main_writes_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rr = tmp_path / "repo"
    dr = tmp_path / "data"
    dr.mkdir()
    _prep_cfg(rr, "m3_repo_public_inputs_outline_inputs.yaml")

    mod3 = rr / "results" / "module3"
    mod3.mkdir(parents=True)
    (mod3 / "module3_public_inputs_status.json").write_text("{}", encoding="utf-8")
    (mod3 / "scrna_spatial_integration_stub.json").write_text("{}", encoding="utf-8")

    import m3_repo_public_inputs_integration_stub as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    monkeypatch.setattr(m, "data_root", lambda: dr)
    assert m.main() == 0

    out = mod3 / "m3_repo_public_inputs_integration_stub.json"
    flag = mod3 / "m3_repo_public_inputs_integration_stub.flag"
    assert out.is_file()
    assert flag.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("outline_module") == 3
    assert doc.get("group") == "module3_public_inputs_repo_outline_outputs"


def test_m3_repo_sc_workflow_integration_stub_main_writes_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rr = tmp_path / "repo"
    dr = tmp_path / "data"
    dr.mkdir()
    _prep_cfg(rr, "m3_repo_sc_workflow_outline_inputs.yaml")

    mod3 = rr / "results" / "module3"
    mod3.mkdir(parents=True)
    (mod3 / "module3_sc_workflow_paths_status.json").write_text("{}", encoding="utf-8")
    (mod3 / "scrna_spatial_integration_stub.json").write_text("{}", encoding="utf-8")

    import m3_repo_sc_workflow_integration_stub as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    monkeypatch.setattr(m, "data_root", lambda: dr)
    assert m.main() == 0

    out = mod3 / "m3_repo_sc_workflow_integration_stub.json"
    flag = mod3 / "m3_repo_sc_workflow_integration_stub.flag"
    assert out.is_file()
    assert flag.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("outline_module") == 3
    assert doc.get("group") == "module3_sc_workflow_repo_outline_outputs"


def test_m3_repo_cellranger_output_integration_stub_main_writes_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rr = tmp_path / "repo"
    dr = tmp_path / "data"
    dr.mkdir()
    _prep_cfg(rr, "m3_repo_cellranger_output_outline_inputs.yaml")

    mod3 = rr / "results" / "module3"
    mod3.mkdir(parents=True)
    (mod3 / "m3_cellranger_output_integration_stub.json").write_text("{}", encoding="utf-8")
    (mod3 / "m3_repo_scrna_spatial_integration_stub.json").write_text("{}", encoding="utf-8")

    import m3_repo_cellranger_output_integration_stub as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    monkeypatch.setattr(m, "data_root", lambda: dr)
    assert m.main() == 0

    out = mod3 / "m3_repo_cellranger_output_integration_stub.json"
    flag = mod3 / "m3_repo_cellranger_output_integration_stub.flag"
    assert out.is_file()
    assert flag.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("outline_module") == 3
    assert doc.get("group") == "module3_cellranger_output_repo_outline_outputs"

