#!/usr/bin/env python3
"""
Download curated open-source files into GLIOMA_TARGET_DATA_ROOT (GBM Detection shared tree).

Config: config/open_source_data_extensions.yaml — HTTPS GETs plus optional GEO series.
Does not replace download_all_required.py phases; extends them for gene sets, deconvolution priors, etc.

  python scripts/download_open_source_extensions.py [--dry-run] [--only ID]
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

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

import download_external_datasets as ext  # noqa: E402


def _load_cfg() -> dict[str, Any]:
    p = _ROOT / "config" / "open_source_data_extensions.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _data_root() -> Path:
    return ext.data_root()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Print planned downloads only")
    ap.add_argument("--only", type=str, default="", help="Run a single download id")
    args = ap.parse_args()

    root = _data_root()
    if not root.is_dir():
        if args.dry_run:
            print(f"NOTE: data_root missing (dry-run only): {root}")
        else:
            print(f"ERROR: data_root not a directory: {root}", file=sys.stderr)
            return 1

    doc = _load_cfg()
    report: dict[str, Any] = {
        "data_root": str(root.resolve()),
        "started": time.time(),
        "items": [],
    }
    errors: list[str] = []

    for item in doc.get("downloads") or []:
        if not isinstance(item, dict):
            continue
        eid = str(item.get("id", "")).strip()
        if not eid or not item.get("enabled", False):
            continue
        if args.only and eid != args.only:
            continue
        url = item.get("url")
        dest_rel = item.get("dest")
        if not url or not dest_rel:
            print(f"skip {eid}: missing url or dest", file=sys.stderr)
            continue
        dest = root / str(dest_rel).replace("/", os.sep)
        desc = item.get("description", "")
        print(f"  [{eid}] -> {dest}")
        if args.dry_run:
            report["items"].append({"id": eid, "dest": str(dest), "dry_run": True})
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        try:
            ext.download_file(str(url), dest)
        except Exception as ex:
            print(f"ERROR {eid}: {ex}", file=sys.stderr)
            report["items"].append({"id": eid, "error": str(ex)})
            errors.append(eid)
            continue
        st = dest.stat().st_size
        report["items"].append(
            {
                "id": eid,
                "url": url,
                "dest": str(dest),
                "bytes": st,
                "seconds": round(time.time() - t0, 2),
                "description": desc,
            }
        )

    geo = doc.get("geo_series") or {}
    if geo.get("enabled") and not args.only:
        gse_ids = list(geo.get("gse_ids") or [])
        if args.dry_run:
            for gse in gse_ids:
                print(f"  [GEO {gse}] (dry-run)")
                report["items"].append({"id": f"geo_{gse}", "dry_run": True})
        else:
            for gse in gse_ids:
                gse = str(gse).strip()
                if not gse.startswith("GSE"):
                    continue
                print(f"  GEO {gse} ...")
                t0 = time.time()
                try:
                    ext.download_geo_series(gse, root)
                    report["items"].append(
                        {"id": f"geo_{gse}", "seconds": round(time.time() - t0, 2), "status": "ok"}
                    )
                except Exception as ex:
                    print(f"ERROR GEO {gse}: {ex}", file=sys.stderr)
                    report["items"].append({"id": f"geo_{gse}", "error": str(ex)})
                    errors.append(f"geo_{gse}")

    report["finished"] = time.time()
    report["elapsed_sec"] = round(report["finished"] - report["started"], 2)
    report["errors"] = errors
    out = _ROOT / "results" / "open_source_extensions_download_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
