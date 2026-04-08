"""Smoke: m3_cellranger_output_integration_stub main() with minimal paths_status JSON."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_cellranger_output_integration_stub_main_writes_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rr = tmp_path / "repo"
    (rr / "config").mkdir(parents=True)
    shutil.copyfile(
        _ROOT / "config" / "m3_cellranger_output_outline_inputs.yaml",
        rr / "config" / "m3_cellranger_output_outline_inputs.yaml",
    )
    mod3 = rr / "results" / "module3"
    mod3.mkdir(parents=True)
    (mod3 / "m3_cellranger_output_paths_status.json").write_text(
        json.dumps({"groups": []}),
        encoding="utf-8",
    )

    import m3_cellranger_output_integration_stub as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    assert m.main() == 0

    out = mod3 / "m3_cellranger_output_integration_stub.json"
    fl = mod3 / "m3_cellranger_output_integration_stub.flag"
    assert out.is_file()
    assert fl.is_file()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload.get("artifact_kind") == "m3_cellranger_output_integration_stub"
    assert payload.get("readiness_tier") == "D"
    assert payload.get("blockers") == []
    ch = payload.get("checklist") or {}
    assert ch.get("cellranger_count_outs_staged") is False
