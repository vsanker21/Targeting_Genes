"""Smoke: module3_public_inputs_status main() writes JSON + flag in a temp repo."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_module3_public_inputs_status_main_writes_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rr = tmp_path / "repo"
    dr = tmp_path / "data"
    dr.mkdir()
    (rr / "config").mkdir(parents=True)
    shutil.copyfile(_ROOT / "config" / "module3_inputs.yaml", rr / "config" / "module3_inputs.yaml")

    import module3_public_inputs_status as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    monkeypatch.setattr(m, "data_root", lambda: dr)
    assert m.main() == 0

    out = rr / "results" / "module3" / "module3_public_inputs_status.json"
    fl = rr / "results" / "module3" / "module3_public_inputs_status.flag"
    assert out.is_file()
    assert fl.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("outline_module") == 3
    assert isinstance(doc.get("checks"), list)

