"""Snakemake workflow checks beyond unit-level rule_block tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from snakemake_ci_data_stubs import (
    assert_pipeline_dry_run_repo_placeholders,
    prepare_data_root_for_pipeline_dry_run,
    touch_data_layout_ok_flag,
    touch_pipeline_dry_run_repo_placeholders,
)
from snakemake_pytest_cli import snakemake_argv0, snakemake_cli_ready
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
@pytest.mark.skipif(not snakemake_cli_ready(), reason="snakemake not available (PATH or python -m snakemake)")
def test_snakemake_dry_run_pipeline_index_with_glioma_target_data_root(tmp_path: Path) -> None:
    """DAG should still resolve when GLIOMA_TARGET_DATA_ROOT points at a stub tree (TOIL inputs for dry-run)."""
    data_root = tmp_path / "empty_data"
    data_root.mkdir()
    prepare_data_root_for_pipeline_dry_run(data_root)
    layout = _ROOT / "results" / "data_layout_ok.flag"
    created_layout = not layout.is_file()
    created_repo: list[Path] = []
    try:
        touch_data_layout_ok_flag(_ROOT)
        created_repo = touch_pipeline_dry_run_repo_placeholders(_ROOT)
        assert_pipeline_dry_run_repo_placeholders(_ROOT)
        env = snakemake_subprocess_env(extra={"GLIOMA_TARGET_DATA_ROOT": str(data_root.resolve())})
        r = subprocess.run(
            [*snakemake_argv0(), "--dry-run", *_pipeline_index_targets()],
            cwd=str(_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert r.returncode == 0, f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    finally:
        if created_layout and layout.is_file():
            layout.unlink()
        for p in created_repo:
            if p.is_file():
                p.unlink()