"""How pytest subprocesses should invoke Snakemake (matches scripts/run_supplementary_enrichment_smoke.py)."""

from __future__ import annotations

import shutil
import subprocess
import sys


def snakemake_argv0() -> list[str]:
    """``snakemake`` on PATH, else ``sys.executable -m snakemake`` (Linux CI always has the former; Windows often needs -m)."""
    if shutil.which("snakemake"):
        return ["snakemake"]
    return [sys.executable, "-m", "snakemake"]


def snakemake_cli_ready() -> bool:
    """True if we can run Snakemake (console script or same-interpreter module)."""
    if shutil.which("snakemake"):
        return True
    r = subprocess.run(
        [sys.executable, "-m", "snakemake", "--version"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return r.returncode == 0
