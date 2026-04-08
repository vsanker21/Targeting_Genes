#!/usr/bin/env python3
"""
Install R packages for scripts/m2_movics_intnmf_tcga_gbm.R (MOVICS / IntNMF).

Uses the same Rscript resolution as Snakemake (see install_r_edger_dependencies.py).

  python scripts/install_r_movics_dependencies.py
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
            "Or set GLIOMA_TARGET_RSCRIPT to your Rscript.exe (R need not be on PATH).",
            file=sys.stderr,
        )
        return 1
    r_file = _SCRIPTS / "install_movics_pkgs.R"
    if not r_file.is_file():
        print(f"Missing {r_file}", file=sys.stderr)
        return 1
    print(f"Using Rscript: {rscript}", flush=True)
    subprocess.check_call([str(rscript), str(r_file)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
