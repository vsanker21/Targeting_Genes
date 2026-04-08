#!/usr/bin/env python3
"""Run M3 RCTD wrapper: validate RDS paths, call R (spacexr) via run_m3_rctd_wrapper.R.

Writes ``rctd_run_provenance.json`` with ``artifact_kind``, ``status``, and RDS / spacexr / create.RCTD flags.
``run_m3_rctd_wrapper.R`` writes ``rctd_run.flag`` only when ``status`` is ``ok`` and exits **1** otherwise
(aligned with ``cell2location_run.flag`` semantics).

RCTD wrapper honors ``GLIOMA_TARGET_RCTD_TEST_MODE`` (prefer ``create.RCTD(..., test_mode=TRUE)`` for CI) and
``GLIOMA_TARGET_RCTD_FALLBACK_TEST_MODE`` (retry with ``test_mode`` after a failed full create).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import yaml

from rscript_resolve import resolve_rscript


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def main() -> int:
    rr = repo_root()
    dr = data_root()
    cfg_p = rr / "config" / "m3_deconvolution_rctd_inputs.yaml"
    doc = yaml.safe_load(cfg_p.read_text(encoding="utf-8"))
    blk = doc.get("m3_deconvolution_rctd") or {}
    ref_rel = blk.get("reference_rds")
    spat_rel = blk.get("spatial_rna_rds")
    if not ref_rel or not spat_rel:
        print("config/m3_deconvolution_rctd_inputs.yaml: reference_rds and spatial_rna_rds required", file=sys.stderr)
        return 1
    ref_p = dr / str(ref_rel).replace("/", os.sep)
    spat_p = dr / str(spat_rel).replace("/", os.sep)
    if not ref_p.is_file():
        print(f"Missing reference RDS under data_root: {ref_p}", file=sys.stderr)
        return 1
    if not spat_p.is_file():
        print(f"Missing spatial RDS under data_root: {spat_p}", file=sys.stderr)
        return 1

    try:
        rscript = resolve_rscript(rr)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        print(
            "Install R or use: snakemake --use-conda -c1 m3_deconvolution_rctd_run "
            "(env workflow/envs/m3_rctd.yaml puts Rscript on PATH).",
            file=sys.stderr,
        )
        return 1

    out = rr / "results" / "module3" / "m3_deconvolution_rctd"
    out.mkdir(parents=True, exist_ok=True)
    wrap = rr / "scripts" / "run_m3_rctd_wrapper.R"
    cmd = [rscript, str(wrap), str(ref_p), str(spat_p), str(out)]
    try:
        subprocess.check_call(cmd, cwd=str(rr))
    except subprocess.CalledProcessError as e:
        print(
            "m3_rctd: R wrapper exited with non-zero status "
            f"({e.returncode}). See {out / 'rctd_run_provenance.json'} for "
            "'status' (rctd_run.flag is written only when status is ok).",
            file=sys.stderr,
        )
        return e.returncode if e.returncode else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
