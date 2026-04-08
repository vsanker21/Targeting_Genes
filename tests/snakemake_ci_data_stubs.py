"""Minimal files under a temp GLIOMA_TARGET_DATA_ROOT so Snakemake --dry-run can resolve common edges on CI."""

from __future__ import annotations

import os
from pathlib import Path

# Inputs for rule toil_gbm_brain_tpm (Snakemake 8+ validates paths during DAG build).
_TOIL_GTEX = (
    "gtex/xena_toil/TcgaTargetGtex_rsem_gene_tpm.gz",
    "gtex/xena_toil/TcgaTargetGTEX_phenotype.txt.gz",
)


def touch_toil_gtex_placeholder_inputs(data_root: Path) -> None:
    """Create empty placeholder files (existence-only for dry-run input checks)."""
    for rel in _TOIL_GTEX:
        p = data_root / rel.replace("/", os.sep)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"")
