#!/usr/bin/env python3
"""
After manifests exist under data_root, generate permutation CSVs and Welch DE tables at paths in
config/holdout_preregistered_outputs.yaml (real + permuted; duplicated across analysis arms until
recount3/STAR-specific holdout matrices exist — see README in each holdout_dea cohort folder).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(str(cfg["data_root"]).replace("/", os.sep))


def _load_holdout_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "holdout_preregistered_outputs.yaml"
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return doc.get("holdout_preregistered_outputs") or {}


# Cohort driver metadata (expression source under data_root).
COHORTS: dict[str, dict[str, str]] = {
    "cgga_gbm_subset": {
        "kind": "cgga",
        "perm_prefix": "cgga",
        "expression_glob": "cohorts/cgga_expression/unpacked/**/CGGA.mRNAseq_693.Read_Counts-genes*.txt",
    },
    "geo_gse4290": {
        "kind": "geo",
        "perm_prefix": "gse4290",
        "expression_glob": "geo/bulk_microarray/GSE4290/matrix/*series_matrix.txt.gz",
    },
    "geo_gse7696": {
        "kind": "geo",
        "perm_prefix": "gse7696",
        "expression_glob": "geo/bulk_microarray/GSE7696/matrix/*series_matrix.txt.gz",
    },
}


def _first_glob(dr: Path, pattern: str) -> Path:
    hits = sorted(p for p in dr.glob(pattern) if p.is_file())
    if not hits:
        raise FileNotFoundError(f"no file under {dr} for {pattern!r}")
    return hits[0]


def _run_py(args: list[str]) -> None:
    r = subprocess.run([sys.executable, *args], cwd=str(repo_root()))
    if r.returncode != 0:
        raise RuntimeError(f"command failed (exit {r.returncode}): {args}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", type=Path, default=None)
    ap.add_argument("--perm-replicates", type=int, default=50)
    ap.add_argument("--base-seed", type=int, default=42)
    ap.add_argument("--skip-permutations", action="store_true")
    ap.add_argument("--skip-de", action="store_true")
    ap.add_argument(
        "--build-manifests",
        action="store_true",
        help="Run build_holdout_sample_manifests_from_staging.py first",
    )
    ap.add_argument(
        "--only-cohort",
        action="append",
        default=[],
        metavar="ID",
        help="Restrict to cohort id(s) from holdout_preregistered_outputs.yaml (repeatable)",
    )
    args = ap.parse_args()

    dr = args.data_root or data_root()
    if not dr.is_dir():
        print(f"ERROR: data_root not found: {dr}", file=sys.stderr)
        return 1

    block = _load_holdout_cfg()
    cohorts = block.get("cohorts") or []
    py_manifest = str(repo_root() / "scripts" / "build_holdout_sample_manifests_from_staging.py")
    py_perm = str(repo_root() / "scripts" / "generate_holdout_permutation_labels.py")
    py_de = str(repo_root() / "scripts" / "holdout_bulk_welch_de.py")

    if args.build_manifests:
        _run_py([py_manifest, "--data-root", str(dr)])

    only = {str(x) for x in (args.only_cohort or []) if str(x).strip()}
    for co in cohorts:
        cid = str(co.get("id") or "")
        if only and cid not in only:
            continue
        meta = COHORTS.get(cid)
        if not meta:
            print(f"skip unknown cohort id {cid!r}", file=sys.stderr)
            continue
        man_rel = str(co.get("sample_manifest_tsv") or "")
        manifest = dr / man_rel.replace("/", os.sep)
        if not manifest.is_file():
            print(f"manifest missing {manifest}; run build_holdout_sample_manifests_from_staging.py", file=sys.stderr)
            return 1

        if not args.skip_permutations:
            _run_py(
                [
                    py_perm,
                    "--input-tsv",
                    str(manifest),
                    "--prefix",
                    meta["perm_prefix"],
                    "--n-replicates",
                    str(args.perm_replicates),
                    "--base-seed",
                    str(args.base_seed),
                    "--out-dir",
                    str(dr / "validation" / "holdout_permutation"),
                ]
            )

        if args.skip_de:
            continue

        expr = _first_glob(dr, meta["expression_glob"])
        kind = meta["kind"]
        rde = co.get("real_label_de") or {}
        arms = list(rde.keys())
        arm_paths = [dr / str(rde[a]).replace("/", os.sep) for a in arms]

        def _write_de(group_col: str, out_tsv: Path, *, manifest_path: Path | None = None) -> None:
            out_tsv.parent.mkdir(parents=True, exist_ok=True)
            mp = manifest_path or manifest
            _run_py(
                [
                    py_de,
                    "--kind",
                    kind,
                    "--expression",
                    str(expr),
                    "--manifest",
                    str(mp),
                    "--group-column",
                    group_col,
                    "--output",
                    str(out_tsv),
                ]
            )

        # Real labels: compute once, copy to all arms.
        first_arm = arm_paths[0]
        _write_de("group", first_arm)
        for dest in arm_paths[1:]:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(first_arm, dest)

        perm_dir = dr / "validation" / "holdout_permutation"
        pref = meta["perm_prefix"]
        perm_files = sorted(perm_dir.glob(f"{pref}_perm_r*.csv"))
        if not perm_files:
            print(f"ERROR: no permutation files for prefix {pref!r}", file=sys.stderr)
            return 1

        for pf in perm_files:
            m = re.search(r"_r(\d+)\.csv$", pf.name)
            if not m:
                continue
            rk = m.group(1)
            tmp = first_arm.parent / f"_tmp_perm_r{rk}_de.tsv"
            _write_de("permuted_group", tmp, manifest_path=pf)
            for dest_base in arm_paths:
                sub = dest_base.parent / f"perm_r{rk}_de.tsv"
                shutil.copy2(tmp, sub)
            tmp.unlink(missing_ok=True)

        cohort_dir = first_arm.parent.parent
        readme = cohort_dir / "README_holdout_de_arms.txt"
        if not readme.is_file():
            readme.write_text(
                f"cohort_id={cid}\n"
                f"expression={expr.relative_to(dr)}\n"
                "All three arm paths currently contain the same Welch DE on the staged native matrix "
                "(log2 transform + BH-FDR). True recount3-only vs GDC-STAR-only vs integrated "
                "holdout quantification is not yet wired for these external series; update arms "
                "separately when those matrices exist.\n",
                encoding="utf-8",
            )

    # Optional aggregate for validation report: use GSE4290 integrated arm if present.
    ext_summary = str(block.get("external_holdout_dea_summary") or "").strip()
    if ext_summary and not args.skip_de:
        for co in cohorts:
            if str(co.get("id")) == "geo_gse4290":
                src = dr / str(co["real_label_de"]["integrated"]).replace("/", os.sep)
                if src.is_file():
                    dest = dr / ext_summary.replace("/", os.sep)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)
                    print(f"Wrote aggregate {dest}")
                break

    print("holdout DE suite finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
