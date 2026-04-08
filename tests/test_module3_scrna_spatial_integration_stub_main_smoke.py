"""Smoke: module3_scrna_spatial_integration_stub main() writes JSON + flag with minimal inputs."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_module3_scrna_spatial_integration_stub_main_writes_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rr = tmp_path / "repo"
    (rr / "config").mkdir(parents=True)
    shutil.copyfile(_ROOT / "config" / "module3_inputs.yaml", rr / "config" / "module3_inputs.yaml")

    mod3 = rr / "results" / "module3"
    mod3.mkdir(parents=True)
    # Minimal prerequisite inputs: empty checks lists are fine (tier stays D).
    (mod3 / "module3_public_inputs_status.json").write_text(
        json.dumps({"outline_module": 3, "checks": []}),
        encoding="utf-8",
    )
    (mod3 / "module3_sc_workflow_paths_status.json").write_text(
        json.dumps({"outline_module": 3, "checks": [], "check_group": "sc_workflow_tooling"}),
        encoding="utf-8",
    )

    import module3_scrna_spatial_integration_stub as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    assert m.main() == 0

    out = mod3 / "scrna_spatial_integration_stub.json"
    fl = mod3 / "scrna_spatial_integration_stub.flag"
    assert out.is_file()
    assert fl.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("outline_module") == 3
    assert doc.get("artifact_kind") == "scrna_spatial_integration_stub"
    assert doc.get("readiness_tier") in ("B", "C", "D")


def test_module3_scrna_spatial_integration_stub_writes_output_with_blockers_when_inputs_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rr = tmp_path / "repo"
    (rr / "config").mkdir(parents=True)
    shutil.copyfile(_ROOT / "config" / "module3_inputs.yaml", rr / "config" / "module3_inputs.yaml")

    import module3_scrna_spatial_integration_stub as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    assert m.main() == 0

    mod3 = rr / "results" / "module3"
    out = mod3 / "scrna_spatial_integration_stub.json"
    fl = mod3 / "scrna_spatial_integration_stub.flag"
    assert out.is_file()
    assert fl.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    blockers = doc.get("blockers") or []
    assert blockers
    assert any("module3_public_inputs_status.json" in str(b) for b in blockers)
    assert any("module3_sc_workflow_paths_status.json" in str(b) for b in blockers)

