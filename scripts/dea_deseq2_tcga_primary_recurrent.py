#!/usr/bin/env python3
"""
PyDESeq2: TCGA-GBM GDC STAR counts — Recurrent vs Primary tumor.

Config block: deseq2_tcga_primary_vs_recurrent in config/deseq2_tcga_gbm.yaml.
Implementation: scripts/tcga_gbm_deseq2_two_group.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Scripts directory on path for imports when run as python scripts/...
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from tcga_gbm_deseq2_two_group import main as run_block


if __name__ == "__main__":
    raise SystemExit(run_block("deseq2_tcga_primary_vs_recurrent"))
