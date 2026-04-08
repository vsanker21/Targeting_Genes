#!/usr/bin/env python3
"""
Download supplementary reference resources (ARCHS4/recount matrices, Expression Atlas gene TSVs,
WikiPathways + PathwayCommons GMT, ChEMBL UniProt map + DGIdb tables, ClinVar gene summary,
gnomAD LOF-by-gene, optional DrugCentral dump).

  python scripts/download_supplementary_reference_resources.py [--dry-run] [--skip-archs4-h5] [--force-archs4-h5] [--with-drugcentral]

Config: config/supplementary_reference_resources.yaml
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import yaml

_SCRIPTS = Path(__file__).resolve().parent
_REPO = _SCRIPTS.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import download_all_required as dar  # noqa: E402
import download_external_datasets as ext  # noqa: E402


def _load_cfg() -> dict[str, Any]:
    p = _REPO / "config" / "supplementary_reference_resources.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _data_root() -> Path:
    return ext.data_root()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--skip-archs4-h5",
        action="store_true",
        help="Skip large gtex_matrix.h5 / tcga_matrix.h5 (~1.3 GB total).",
    )
    ap.add_argument(
        "--force-archs4-h5",
        action="store_true",
        help="Delete existing ARCHS4 HDF5 (and *.h5.partial) under data_root, then re-download from S3.",
    )
    ap.add_argument(
        "--with-drugcentral",
        action="store_true",
        help="Download DrugCentral PostgreSQL dump (~1.4 GB) even when enabled: false in YAML.",
    )
    args = ap.parse_args()
    if args.skip_archs4_h5 and args.force_archs4_h5:
        print("ERROR: --skip-archs4-h5 and --force-archs4-h5 are mutually exclusive.", file=sys.stderr)
        return 1

    root = _data_root()
    if not root.is_dir():
        if args.dry_run:
            print(f"NOTE: data_root missing (dry-run): {root}")
        else:
            print(f"ERROR: data_root not a directory: {root}", file=sys.stderr)
            return 1

    doc = _load_cfg()
    report: dict[str, Any] = {
        "data_root": str(root.resolve()),
        "started": time.time(),
        "dry_run": args.dry_run,
        "items": [],
    }
    errors: list[str] = []

    try:
        ar = doc.get("archs4_recount_matrices") or {}
        if ar.get("enabled") and not args.skip_archs4_h5:
            base = root / str(ar.get("dest_dir", "references/archs4_recount")).replace("/", os.sep)
            archs4_jobs: list[tuple[str, str, Path]] = []
            for item in ar.get("files") or []:
                if not isinstance(item, dict):
                    continue
                url, fn = item.get("url"), item.get("filename")
                if not url or not fn:
                    continue
                archs4_jobs.append((str(url), str(fn), base / fn))
            if args.force_archs4_h5 and archs4_jobs:
                if args.dry_run:
                    report["items"].append(
                        {
                            "id": "archs4",
                            "dry_run": True,
                            "force_redownload": True,
                            "files": [fn for _, fn, _ in archs4_jobs],
                        }
                    )
                else:
                    for _, fn, dest in archs4_jobs:
                        partial = dest.with_suffix(dest.suffix + ".partial")
                        if dest.is_file():
                            dest.unlink()
                            print(f"  [ARCHS4/recount] removed existing {fn}")
                        partial.unlink(missing_ok=True)
                    report["items"].append(
                        {
                            "id": "archs4",
                            "force_redownload": True,
                            "removed": [fn for _, fn, _ in archs4_jobs],
                        }
                    )
            for url, fn, dest in archs4_jobs:
                print(f"  [ARCHS4/recount] {fn} -> {dest}")
                if args.dry_run:
                    if not args.force_archs4_h5:
                        report["items"].append({"id": "archs4", "file": fn, "dry_run": True})
                    continue
                base.mkdir(parents=True, exist_ok=True)
                t0 = time.time()
                dar.download_with_fallback(url, dest, resume=True)
                report["items"].append(
                    {
                        "id": "archs4",
                        "file": fn,
                        "bytes": dest.stat().st_size,
                        "seconds": round(time.time() - t0, 2),
                    }
                )
        elif ar.get("enabled") and args.skip_archs4_h5:
            report["items"].append({"id": "archs4", "skipped": True, "reason": "skip_archs4_h5"})

        ea = doc.get("expression_atlas_gene_baselines") or {}
        if ea.get("enabled"):
            tmpl = str(ea.get("url_template") or "")
            ed = root / str(ea.get("dest_dir", "references/expression_atlas_genes")).replace("/", os.sep)
            for g in ea.get("genes") or []:
                if not isinstance(g, dict):
                    continue
                eid = str(g.get("ensembl_id") or "").strip()
                sym = str(g.get("symbol") or "gene").strip()
                if not eid or not tmpl:
                    continue
                url = tmpl.format(ensembl_id=eid)
                dest = ed / f"{sym}_{eid}.tsv"
                print(f"  [ExpressionAtlas] {sym} ({eid}) -> {dest}")
                if args.dry_run:
                    report["items"].append({"id": f"gx_{sym}", "dry_run": True})
                    continue
                ed.mkdir(parents=True, exist_ok=True)
                t0 = time.time()
                dar.download_with_fallback(url, dest, resume=False)
                report["items"].append(
                    {
                        "id": f"gx_{sym}",
                        "bytes": dest.stat().st_size,
                        "seconds": round(time.time() - t0, 2),
                    }
                )

        pw = doc.get("pathways") or {}
        for key, blk in pw.items():
            if not isinstance(blk, dict) or not blk.get("enabled"):
                continue
            url, rel = blk.get("url"), blk.get("dest")
            if not url or not rel:
                continue
            dest = root / str(rel).replace("/", os.sep)
            print(f"  [pathway:{key}] -> {dest}")
            if args.dry_run:
                report["items"].append({"id": key, "dry_run": True})
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            t0 = time.time()
            dar.download_with_fallback(url, dest, resume=True)
            report["items"].append(
                {"id": key, "bytes": dest.stat().st_size, "seconds": round(time.time() - t0, 2)}
            )

        dt = doc.get("drug_target") or {}
        cm = dt.get("chembl_uniprot_mapping") or {}
        if cm.get("enabled"):
            url, rel = cm.get("url"), cm.get("dest")
            if url and rel:
                dest = root / str(rel).replace("/", os.sep)
                print(f"  [ChEMBL UniProt map] -> {dest}")
                if args.dry_run:
                    report["items"].append({"id": "chembl_uniprot", "dry_run": True})
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    t0 = time.time()
                    dar.download_with_fallback(url, dest, resume=True)
                    report["items"].append(
                        {
                            "id": "chembl_uniprot",
                            "bytes": dest.stat().st_size,
                            "seconds": round(time.time() - t0, 2),
                        }
                    )
        dg = dt.get("dgidb") or {}
        if dg.get("enabled"):
            ddir = root / str(dg.get("dest_dir", "references/dgidb")).replace("/", os.sep)
            for item in dg.get("files") or []:
                if not isinstance(item, dict):
                    continue
                url, fn = item.get("url"), item.get("filename")
                if not url or not fn:
                    continue
                dest = ddir / fn
                print(f"  [DGIdb] {fn}")
                if args.dry_run:
                    report["items"].append({"id": f"dgidb_{fn}", "dry_run": True})
                    continue
                ddir.mkdir(parents=True, exist_ok=True)
                t0 = time.time()
                dar.download_with_fallback(url, dest, resume=True)
                report["items"].append(
                    {
                        "id": f"dgidb_{fn}",
                        "bytes": dest.stat().st_size,
                        "seconds": round(time.time() - t0, 2),
                    }
                )

        vi = doc.get("variant_interpretation") or {}
        for key, blk in vi.items():
            if not isinstance(blk, dict) or not blk.get("enabled"):
                continue
            url, rel = blk.get("url"), blk.get("dest")
            if not url or not rel:
                continue
            dest = root / str(rel).replace("/", os.sep)
            print(f"  [variant:{key}] -> {dest}")
            if args.dry_run:
                report["items"].append({"id": key, "dry_run": True})
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            t0 = time.time()
            dar.download_with_fallback(url, dest, resume=True)
            report["items"].append(
                {"id": key, "bytes": dest.stat().st_size, "seconds": round(time.time() - t0, 2)}
            )

        dc = doc.get("drugcentral") or {}
        if dc.get("enabled") or args.with_drugcentral:
            url, rel = dc.get("url"), dc.get("dest")
            if url and rel:
                dest = root / str(rel).replace("/", os.sep)
                print(f"  [DrugCentral] (large) -> {dest}")
                if args.dry_run:
                    report["items"].append({"id": "drugcentral", "dry_run": True})
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    t0 = time.time()
                    dar.download_with_fallback(url, dest, resume=True)
                    report["items"].append(
                        {
                            "id": "drugcentral",
                            "bytes": dest.stat().st_size,
                            "seconds": round(time.time() - t0, 2),
                        }
                    )

    except Exception as e:
        errors.append(str(e))
        print(f"ERROR: {e}", file=sys.stderr)

    report["finished"] = time.time()
    report["elapsed_sec"] = round(report["finished"] - report["started"], 2)
    report["errors"] = errors
    out = _REPO / "results" / "supplementary_reference_resources_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
