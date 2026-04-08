"""report_pipeline_planned_extensions.py writes JSON with extension registry."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_report_pipeline_planned_extensions_writes_json(tmp_path) -> None:
    rr = tmp_path / "repo"
    (rr / "scripts").mkdir(parents=True)
    (rr / "config").mkdir(parents=True)
    shutil.copy(_ROOT / "config" / "pipeline_planned_extensions.yaml", rr / "config" / "pipeline_planned_extensions.yaml")
    shutil.copy(_ROOT / "scripts" / "report_pipeline_planned_extensions.py", rr / "scripts" / "report_pipeline_planned_extensions.py")

    r = subprocess.run(
        [sys.executable, str(rr / "scripts" / "report_pipeline_planned_extensions.py")],
        cwd=str(rr),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    out = rr / "results" / "pipeline_planned_extensions_report.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert "extensions" in doc
    counts = doc.get("counts_by_status") or {}
    assert counts
    assert sum(counts.values()) == len(doc["extensions"])
