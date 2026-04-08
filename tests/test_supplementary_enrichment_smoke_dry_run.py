"""Dry-run the isolated supplementary smoke driver (no R, no Bioconductor)."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

from snakemake_subprocess_env import snakemake_subprocess_env


def _load_smoke_module(repo: Path):
    path = repo / "scripts" / "run_supplementary_enrichment_smoke.py"
    spec = importlib.util.spec_from_file_location("_rss_dry", path)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_supplementary_smoke_dry_run_exits_zero() -> None:
    repo = Path(__file__).resolve().parents[1]
    env = snakemake_subprocess_env(
        extra={"GLIOMA_TARGET_DATA_ROOT": str(repo / "references" / "demo_supplementary" / "data_root")}
    )
    smoke = _load_smoke_module(repo)
    dea = smoke._dea_path()
    cmd = [
        sys.executable,
        str(repo / "scripts" / "run_supplementary_enrichment_smoke.py"),
        "--dry-run",
    ]
    # CI / empty results: need demo snapshot. Dev machines with real TOIL DEA: never pass --copy-demo-results.
    if not smoke._dea_looks_real(dea):
        cmd.insert(-1, "--copy-demo-results")
    r = subprocess.run(
        cmd,
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "m4_run_fgsea_supplementary_pathways" in r.stdout
    assert "m2_verhaak_subtypes" not in r.stdout
