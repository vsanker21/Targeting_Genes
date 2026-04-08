#!/usr/bin/env python3
"""
Download recount3 gene-sum matrices (GENCODE G029) for TCGA GBM and GTEx brain.

Writes under data_root/recount3/harmonized_g029/ (see config/deseq2_recount3_tcga_gtex.yaml).
Uses the same HTTPS fallback helpers as download_all_required.py.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import download_all_required as ext  # noqa: E402


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(str(cfg["data_root"]).replace("/", os.sep))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="Re-download even if files exist and sizes match.")
    args = ap.parse_args()

    rr = repo_root()
    block = yaml.safe_load((rr / "config" / "deseq2_recount3_tcga_gtex.yaml").read_text(encoding="utf-8")).get(
        "deseq2_recount3_tcga_gbm_vs_gtex_brain"
    ) or {}
    if not block.get("enabled", True):
        print("deseq2_recount3_tcga_gbm_vs_gtex_brain disabled")
        return 0

    root = data_root()
    base = block["recount3_base_url"].rstrip("/")
    sub = block.get("local_cache_subdir", "recount3/harmonized_g029").replace("/", os.sep)
    out_dir = root / sub
    out_dir.mkdir(parents=True, exist_ok=True)

    pairs = [
        (block["tcga_gbm_g029_relpath"], "tcga_gbm"),
        (block["gtex_brain_g029_relpath"], "gtex_brain"),
    ]
    for rel, label in pairs:
        url = f"{base}/{rel.replace(chr(92), '/')}"
        dest = out_dir / Path(rel).name
        expected = None
        if dest.is_file() and not args.force:
            print(f"[skip exists] {label} {dest}")
            continue
        print(f"GET {label} …")
        ext.download_with_fallback(url, dest, resume=False)
        print(f"  -> {dest} ({dest.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
