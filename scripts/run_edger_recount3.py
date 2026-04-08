#!/usr/bin/env python3
"""Run edgeR on recount3 prepared matrix (same as Snakemake m2_edger_recount3_tcga_gbm_vs_gtex_brain)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from rscript_resolve import resolve_rscript


def main() -> int:
    rr = Path(__file__).resolve().parents[1]
    rscript = resolve_rscript(rr)
    rcmd = str(rr / "scripts" / "edger_recount3_tcga_gbm_vs_gtex_brain.R")
    return subprocess.call([rscript, rcmd], cwd=str(rr))


if __name__ == "__main__":
    raise SystemExit(main())
