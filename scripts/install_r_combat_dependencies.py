#!/usr/bin/env python3
"""Install R packages for scripts/combat_seq_tcga_gbm_subset.R (sva::ComBat_seq)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import configure_r_for_snakemake as _cfg  # noqa: E402


def main() -> int:
    rscript = _cfg.discover_rscript()
    if rscript is None:
        print(
            "Rscript not found. Run: python scripts/configure_r_for_snakemake.py",
            file=sys.stderr,
        )
        return 1
    r_file = _SCRIPTS / "install_combat_pkgs.R"
    print(f"Using Rscript: {rscript}", flush=True)
    subprocess.check_call([str(rscript), str(r_file)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
