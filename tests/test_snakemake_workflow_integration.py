"""Snakemake workflow checks beyond unit-level rule_block tests."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from snakemake_subprocess_env import snakemake_subprocess_env

_ROOT = Path(__file__).resolve().parents[1]


def _pipeline_index_targets() -> list[str]:
    inv = yaml.safe_load((_ROOT / "config" / "pipeline_inventory.yaml").read_text(encoding="utf-8"))
    pri = inv.get("pipeline_results_index") or {}
    out_json = str(pri.get("output_json", "") or "").strip().replace("\\", "/")
    manifests = [str(p).replace("\\", "/") for p in (pri.get("manifest_paths") or [])]
    return [*manifests, out_json]


@pytest.mark.integration
@pytest.mark.snakemake
@pytest.mark.skipif(not shutil.which("snakemake"), reason="snakemake not on PATH")
def test_snakemake_dry_run_pipeline_index_with_glioma_target_data_root(tmp_path: Path) -> None:
    """DAG should still resolve when GLIOMA_TARGET_DATA_ROOT points at an empty tree (parse-time check)."""
    data_root = tmp_path / "empty_data"
    data_root.mkdir()
    env = snakemake_subprocess_env(extra={"GLIOMA_TARGET_DATA_ROOT": str(data_root)})
    r = subprocess.run(
        ["snakemake", "--dry-run", *_pipeline_index_targets()],
        cwd=str(_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert r.returncode == 0, f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
