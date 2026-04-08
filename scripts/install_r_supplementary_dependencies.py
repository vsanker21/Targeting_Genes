#!/usr/bin/env python3
"""
Install Bioconductor + CRAN packages for supplementary fgsea / clusterProfiler (Snakemake install_r_supplementary_enrichment).

Uses the same Rscript resolution as Snakemake (RSCRIPT, R_HOME, config/rscript_local.yaml, PATH, …).

Run after R is installed, e.g.:
  python scripts/install_r_supplementary_dependencies.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import rscript_resolve as _rs  # noqa: E402


def main() -> int:
    rr = _SCRIPTS.parent
    try:
        rscript = _rs.resolve_rscript(rr)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        print(
            "Run: python scripts/configure_r_for_snakemake.py\n"
            "Or set GLIOMA_TARGET_RSCRIPT to your Rscript.exe, or add R\\bin to PATH.",
            file=sys.stderr,
        )
        return 1
    r_file = _SCRIPTS / "install_r_supplementary_enrichment.R"
    if not r_file.is_file():
        print(f"Missing {r_file}", file=sys.stderr)
        return 1
    print(f"Using Rscript: {rscript}", flush=True)
    subprocess.check_call([str(rscript), str(r_file)], cwd=str(rr))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
