"""Smoke: write_module3_export_manifest main() writes the manifest JSON in a temp repo."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_write_module3_export_manifest_main_writes_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rr = tmp_path / "repo"
    (rr / "config").mkdir(parents=True)
    shutil.copyfile(_ROOT / "config" / "module3_inputs.yaml", rr / "config" / "module3_inputs.yaml")

    import write_module3_export_manifest as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    assert m.main() == 0

    out = rr / "results" / "module3" / "module3_export_manifest.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("outline_module") == 3
    artifacts = doc.get("artifacts")
    assert isinstance(artifacts, list)
    assert artifacts, "manifest should list curated artifacts even if none exist on disk"

