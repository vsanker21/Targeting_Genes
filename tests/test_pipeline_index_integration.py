"""Subprocess and optional real-repo checks for write_pipeline_results_index --strict."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "write_pipeline_results_index.py"


def _outline_mod_from_manifest_rel(rel: str) -> int:
    parts = rel.replace("\\", "/").strip().split("/")
    if len(parts) < 2 or not parts[1].startswith("module"):
        raise ValueError(f"unexpected manifest path: {rel!r}")
    return int(parts[1].replace("module", ""))


@pytest.mark.integration
def test_write_pipeline_results_index_strict_subprocess_minimal_inventory_repo(tmp_path: Path) -> None:
    """CLI --strict exit 0 on a tiny repo shaped like pipeline_inventory (empty artifacts / jobs)."""
    rr = tmp_path / "mini_repo"
    (rr / "scripts").mkdir(parents=True)
    shutil.copy2(_SCRIPT, rr / "scripts" / "write_pipeline_results_index.py")
    inv_src = yaml.safe_load((_ROOT / "config" / "pipeline_inventory.yaml").read_text(encoding="utf-8"))
    pri = dict(inv_src.get("pipeline_results_index") or {})
    pri["optional_path_posix"] = []
    # Real inventory lists M7 GTS TSV as a primary deliverable; mini_repo has no results/module7 files.
    pri["primary_deliverables"] = []
    inv_src["pipeline_results_index"] = pri
    (rr / "config").mkdir(parents=True, exist_ok=True)
    (rr / "config" / "pipeline_inventory.yaml").write_text(
        yaml.safe_dump(inv_src, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    for rel in pri.get("manifest_paths") or []:
        p = rr / str(rel).replace("/", os.sep)
        p.parent.mkdir(parents=True, exist_ok=True)
        mod = _outline_mod_from_manifest_rel(str(rel))
        p.write_text(json.dumps({"outline_module": mod, "artifacts": []}), encoding="utf-8")
    for item in pri.get("provenance_paths") or []:
        if not isinstance(item, dict):
            continue
        rel = str(item.get("path", "") or "").strip()
        p = rr / rel.replace("/", os.sep)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"jobs": []}), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(rr / "scripts" / "write_pipeline_results_index.py"), "--strict"],
        cwd=str(rr),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"stderr:\n{r.stderr}\nstdout:\n{r.stdout}"
    out_rel = str(pri.get("output_json", "results/pipeline_results_index.json")).strip()
    out = rr / out_rel.replace("/", os.sep)
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["summary"]["strict_ok"] is True


@pytest.mark.integration
def test_write_pipeline_results_index_strict_subprocess_real_repo_skips_without_manifests() -> None:
    """When results exist locally, ensure the same CLI the workflow uses passes strict."""
    sample = _ROOT / "results/module3/module3_export_manifest.json"
    if not sample.is_file():
        pytest.skip(
            "No results/module3/module3_export_manifest.json; build pipeline outputs or rely on the minimal-repo test"
        )
    r = subprocess.run(
        [sys.executable, str(_SCRIPT), "--strict"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"stderr:\n{r.stderr}\nstdout:\n{r.stdout}"
