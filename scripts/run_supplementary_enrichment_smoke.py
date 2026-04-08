#!/usr/bin/env python3
"""
End-to-end smoke test for supplementary pathway enrichment (PathwayCommons decompress,
fgsea + clusterProfiler plans, R package install, run R drivers) using committed demo files.

Does not require your full TCGA/GTEx data_root — only:
  references/demo_supplementary/data_root/  (pathways GMT + gz, HGNC slice)
  references/demo_supplementary/repo_results/  (minimal DEA + prerank, copied only when you opt in)

**Safety (default):** This script does **not** copy demo snapshots into results/ unless you pass
**--copy-demo-results**. That avoids overwriting a real **results/module3/dea_gbm_vs_gtex_brain.tsv**
(~16k genes) with the tiny demo table. Use **--copy-demo-results** on a clean clone or in CI.
If **--copy-demo-results** is set but a **large** DEA file already exists, the script **exits with
an error** unless you also pass **--force-demo-copy** (explicit overwrite).

When not copying, you must already have:
  results/module3/dea_gbm_vs_gtex_brain.tsv
  results/module4/gsea/dea_welch_signed_neg_log10_p.rnk

Usage:
  python scripts/run_supplementary_enrichment_smoke.py --dry-run
  python scripts/run_supplementary_enrichment_smoke.py --copy-demo-results   # CI / no real DEA yet
  python scripts/run_supplementary_enrichment_smoke.py                      # real DEA + prerank already in results/

Requires: snakemake on PATH, R + successful install_r_supplementary_dependencies.py (or let Snakemake run install rule).

Env:
  GLIOMA_TARGET_DATA_ROOT — if set, must point at a layout with pathways + hgnc; default is repo demo data_root.
  Optional Snakemake ``GLIOMA_TARGET_INCLUDE_*`` rule-all flags from your shell are stripped for the
  snakemake subprocess so dry-run matches the default DAG (see scripts/snakemake_subprocess_env.py).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO / "scripts"
_DEMO = _REPO / "references" / "demo_supplementary"
_DEMO_DR = _DEMO / "data_root"
_SNAPSHOT = _DEMO / "repo_results"

# Demo DEA has ~40 rows; real TOIL DEA has ~16k. Treat >= this many lines as "real" (early exit on count).
_REAL_DEA_MIN_LINES = 200


def _line_count(path: Path, cap: int = _REAL_DEA_MIN_LINES + 50) -> int:
    n = 0
    try:
        with path.open(encoding="utf-8", errors="replace") as f:
            for _ in f:
                n += 1
                if n >= cap:
                    return n
    except OSError:
        return 0
    return n


def _dea_path() -> Path:
    return _REPO / "results" / "module3" / "dea_gbm_vs_gtex_brain.tsv"


def _rnk_path() -> Path:
    return _REPO / "results" / "module4" / "gsea" / "dea_welch_signed_neg_log10_p.rnk"


def _dea_looks_real(path: Path) -> bool:
    if not path.is_file():
        return False
    return _line_count(path) >= _REAL_DEA_MIN_LINES


def _copy_tree(src: Path, dst: Path) -> None:
    if not src.is_dir():
        raise FileNotFoundError(f"Missing demo directory: {src}")
    dst.mkdir(parents=True, exist_ok=True)
    for p in src.rglob("*"):
        if p.is_file():
            rel = p.relative_to(src)
            out = dst / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, out)


def main() -> int:
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    from snakemake_subprocess_env import snakemake_subprocess_env

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--copy-demo-results",
        action="store_true",
        help="Copy references/demo_supplementary/repo_results/ into results/ (CI or empty results only).",
    )
    ap.add_argument(
        "--force-demo-copy",
        action="store_true",
        help="With --copy-demo-results: overwrite even if a large (real) DEA table already exists. Dangerous.",
    )
    ap.add_argument(
        "--skip-copy-results",
        action="store_true",
        help="Deprecated: same as default (do not copy demo snapshot). Overrides --copy-demo-results.",
    )
    ap.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Pass snakemake --dry-run (DAG only, no execution).",
    )
    ap.add_argument(
        "--incremental",
        action="store_true",
        help="Omit --forcerun (reuse existing outputs when up to date).",
    )
    ap.add_argument(
        "snakemake_extra",
        nargs="*",
        help="Additional snakemake CLI args (e.g. --forceall).",
    )
    args = ap.parse_args()
    extra: list[str] = []
    if args.dry_run:
        extra.append("--dry-run")
    extra.extend(args.snakemake_extra)

    if not _DEMO_DR.is_dir():
        print(f"Missing {_DEMO_DR}", file=sys.stderr)
        return 1

    data_root = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if not data_root:
        data_root = str(_DEMO_DR.resolve())
        os.environ["GLIOMA_TARGET_DATA_ROOT"] = data_root

    do_copy = bool(args.copy_demo_results) and not args.skip_copy_results
    if args.skip_copy_results and args.copy_demo_results:
        print("NOTE: --skip-copy-results overrides --copy-demo-results (no demo copy).", file=sys.stderr)
        do_copy = False

    if do_copy:
        if not _SNAPSHOT.is_dir():
            print(f"Missing {_SNAPSHOT}", file=sys.stderr)
            return 1
        dea = _dea_path()
        if _dea_looks_real(dea) and not args.force_demo_copy:
            print(
                "ERROR: Refusing to copy demo results: "
                f"{dea} has >= {_REAL_DEA_MIN_LINES} lines (looks like real TOIL DEA).\n"
                "  Run without --copy-demo-results to keep your real DEA, or pass --force-demo-copy to overwrite (not recommended).",
                file=sys.stderr,
            )
            return 1
        res = _REPO / "results"
        res.mkdir(parents=True, exist_ok=True)
        _copy_tree(_SNAPSHOT, res)
        print("Copied demo repo_results snapshot into results/", flush=True)
    else:
        dea, rnk = _dea_path(), _rnk_path()
        missing = [str(p) for p in (dea, rnk) if not p.is_file()]
        if missing:
            print(
                "ERROR: Supplementary smoke needs Welch DEA + prerank in results/ (or use --copy-demo-results).\n"
                "  Missing:\n    " + "\n    ".join(missing),
                file=sys.stderr,
            )
            return 1

    allowed = [
        "pathwaycommons_hgnc_gmt_plain",
        "m4_supplementary_open_enrichment_plan",
        "m4_clusterprofiler_supplementary_plan",
        "install_r_supplementary_enrichment",
        "m4_run_fgsea_supplementary_pathways",
        "m4_run_clusterprofiler_supplementary_pathways",
    ]
    # Explicit goals: without positional targets Snakemake defaults to rule all (hundreds of inputs).
    supplementary_goals = [
        "results/module4/gsea/fgsea_supplementary_pathways_results.tsv",
        "results/module4/gsea/clusterprofiler_supplementary_enricher.tsv",
    ]
    cmd = ["snakemake", "-c", "1", *extra, "--allowed-rules", *allowed]
    if not args.incremental:
        cmd.extend(["--forcerun", *allowed])
    cmd.extend(supplementary_goals)
    print("GLIOMA_TARGET_DATA_ROOT=", data_root, flush=True)
    print("Running:", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(_REPO), env=snakemake_subprocess_env())


if __name__ == "__main__":
    raise SystemExit(main())
