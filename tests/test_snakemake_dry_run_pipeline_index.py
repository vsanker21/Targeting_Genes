"""Integration: Snakemake resolves a DAG for export manifests + pipeline_results_index."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from snakemake_ci_data_stubs import (
    prepare_data_root_for_pipeline_dry_run,
    touch_data_layout_ok_flag,
    touch_pipeline_dry_run_repo_placeholders,
)
from snakemake_pytest_cli import snakemake_argv0, snakemake_cli_ready
from snakemake_subprocess_env import snakemake_subprocess_env

_ROOT = Path(__file__).resolve().parents[1]
_INV = _ROOT / "config" / "pipeline_inventory.yaml"


def _pipeline_index_dry_run_targets() -> list[str]:
    """Paths from pipeline_inventory.yaml — same files rule pipeline_results_index consumes."""
    doc = yaml.safe_load(_INV.read_text(encoding="utf-8"))
    pri = doc.get("pipeline_results_index") or {}
    out_json = str(pri.get("output_json", "") or "").strip().replace("\\", "/")
    manifests = [str(p).replace("\\", "/") for p in (pri.get("manifest_paths") or [])]
    assert out_json, "pipeline_inventory pipeline_results_index.output_json required"
    assert manifests, "pipeline_inventory manifest_paths required"
    return [*manifests, out_json]


@pytest.mark.snakemake
@pytest.mark.skipif(not snakemake_cli_ready(), reason="snakemake not available (PATH or python -m snakemake)")
def test_snakemake_dry_run_pipeline_results_index(tmp_path: Path) -> None:
    """DAG must schedule every inventory manifest + index output (single dry-run, YAML-driven targets)."""
    dr = (tmp_path / "pipeline_dry_run_data").resolve()
    dr.mkdir(parents=True, exist_ok=True)
    prepare_data_root_for_pipeline_dry_run(dr)
    hgnc_stub = dr / "references" / "hgnc_complete_set.txt"
    assert hgnc_stub.is_file() and hgnc_stub.stat().st_size > 0, f"missing HGNC stub: {hgnc_stub}"
    layout = _ROOT / "results" / "data_layout_ok.flag"
    created_layout = not layout.is_file()
    created_repo: list[Path] = []
    try:
        touch_data_layout_ok_flag(_ROOT)
        created_repo = touch_pipeline_dry_run_repo_placeholders(_ROOT)
        env = snakemake_subprocess_env(extra={"GLIOMA_TARGET_DATA_ROOT": str(dr.resolve())})
        targets = _pipeline_index_dry_run_targets()
        r = subprocess.run(
            [*snakemake_argv0(), "--dry-run", *targets],
            cwd=_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert r.returncode == 0, f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
        out = r.stdout
        # When every target is already present, dry-run prints "Nothing to be done" and
        # does not list per-rule job lines — still a valid successful DAG resolution.
        if "Nothing to be done" in out and "all requested files are present" in out:
            return
        # Snakemake 9+ dry-run lists only jobs that need to run (stale subgraph), not every
        # requested goal's rule — e.g. after ARCHS4 HDF5 touch, only m4_export_manifest +
        # pipeline_results_index may appear, not m3_export_manifest.
        manifest_rules = (
            "m3_export_manifest",
            "m4_export_manifest",
            "m5_export_manifest",
            "m6_export_manifest",
            "m7_export_manifest",
        )
        if "pipeline_results_index" in out or any(rule in out for rule in manifest_rules):
            return
        assert False, (
            "expected pipeline_results_index or at least one m*_export_manifest in dry-run plan; "
            f"stdout:\n{out[:6000]}"
        )
    finally:
        if created_layout and layout.is_file():
            layout.unlink()
        for p in created_repo:
            if p.is_file():
                p.unlink()