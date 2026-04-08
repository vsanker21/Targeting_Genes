#!/usr/bin/env python3
"""
Download high-value public datasets: GDSC, PRISM (via DepMap file index), Open Targets shard,
GDC TCGA-GBM open methylation beta TXT, CELLxGENE Census h5ad mirrors on public S3, optional CGGA HTTP.

  python scripts/download_high_value_public_datasets.py [--dry-run] [--gdc-workers N]

Config: config/high_value_public_datasets.yaml
CGGA URLs: config/m2_movics_data_fetch.yaml (cgga_http) — fetched via fetch_movics_staging_data.py.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml

_SCRIPTS = Path(__file__).resolve().parent
_REPO = _SCRIPTS.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import download_external_datasets as ext  # noqa: E402
import download_all_required as dar  # noqa: E402

GDC_FILES_ENDPOINT = "https://api.gdc.cancer.gov/files"
GDC_DATA_ENDPOINT = "https://api.gdc.cancer.gov/data"


def _load_cfg() -> dict[str, Any]:
    p = _REPO / "config" / "high_value_public_datasets.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _data_root() -> Path:
    return ext.data_root()


def _prism_release_sort_key(release: str) -> tuple[int, int]:
    m = re.search(r"(\d{2})Q(\d)", release or "")
    if not m:
        return (-1, -1)
    return int(m.group(1)), int(m.group(2))


def resolve_prism_file_rows(
    all_rows: list[dict[str, str]],
    release_contains: str,
    filename_substrings: list[str],
) -> tuple[str, list[dict[str, str]]]:
    cand = [r for r in all_rows if release_contains in (r.get("release") or "")]
    if not cand:
        raise RuntimeError(f"No DepMap files rows matched release_contains={release_contains!r}")
    rels = {r["release"] for r in cand}
    best_rel = max(rels, key=_prism_release_sort_key)
    picked: list[dict[str, str]] = []
    for r in all_rows:
        if r.get("release") != best_rel:
            continue
        fn = r.get("filename") or ""
        if any(sub in fn for sub in filename_substrings):
            picked.append(r)
    if not picked:
        raise RuntimeError(f"No files matched substrings under release {best_rel!r}")
    return best_rel, picked


def gdc_tcga_gbm_methylation_beta_manifest() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    filters: dict[str, Any] = {
        "op": "and",
        "content": [
            {"op": "=", "content": {"field": "cases.project.project_id", "value": "TCGA-GBM"}},
            {"op": "=", "content": {"field": "access", "value": "open"}},
            {"op": "=", "content": {"field": "data_category", "value": "DNA Methylation"}},
            {"op": "=", "content": {"field": "data_type", "value": "Methylation Beta Value"}},
            {"op": "=", "content": {"field": "data_format", "value": "TXT"}},
        ],
    }
    fields = ["file_id", "file_name", "file_size", "md5sum", "data_type"]
    hits: list[dict[str, Any]] = []
    page_size = 500
    offset = 0
    pagination: dict[str, Any] = {}
    while True:
        body = {
            "filters": filters,
            "fields": ",".join(fields),
            "format": "JSON",
            "size": page_size,
            "from": offset,
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            GDC_FILES_ENDPOINT,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": ext.USER_AGENT},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=ext.HTTP_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        chunk = payload["data"]["hits"]
        pagination = payload["data"]["pagination"]
        hits.extend(chunk)
        offset += len(chunk)
        if offset >= int(pagination.get("total", 0)) or not chunk:
            break
    return hits, pagination


def download_gdc_methylation_beta(root: Path, subdir: str, workers: int, dry_run: bool, report: dict[str, Any]) -> None:
    out_dir = root / subdir.replace("/", os.sep)
    print(f"GDC methylation: querying open TCGA-GBM beta TXT ...")
    hits, pagination = gdc_tcga_gbm_methylation_beta_manifest()
    total = int(pagination.get("total", len(hits)))
    print(f"GDC methylation: {len(hits)} / {total} files")
    meta_path = out_dir / "gdc_methylation_files_manifest.json"
    if dry_run:
        report["gdc_methylation"] = {"dry_run": True, "n_files": len(hits), "dest": str(out_dir)}
        print(f"  [dry-run] would write manifest + download under {out_dir}")
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps({"pagination": pagination, "hits": hits}, indent=2), encoding="utf-8")

    def one(hit: dict[str, Any]) -> tuple[str, str]:
        fid = hit["file_id"]
        fname = hit["file_name"]
        dest = out_dir / fname
        expected = int(hit["file_size"])
        if dest.is_file() and dest.stat().st_size == expected:
            return fname, "skip"
        url = f"{GDC_DATA_ENDPOINT}/{fid}"
        dar.download_with_fallback(url, dest, resume=False)
        if dest.stat().st_size != expected:
            raise RuntimeError(f"size mismatch {fname}")
        return fname, "ok"

    errors: list[str] = []
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = [ex.submit(one, h) for h in hits]
        for fut in as_completed(futs):
            try:
                name, status = fut.result()
                done += 1
                if status != "skip" or done <= 3 or done % 40 == 0 or done == len(hits):
                    print(f"  [{status}] {name} ({done}/{len(hits)})")
            except Exception as e:
                errors.append(str(e))
                print(f"  [FAIL] {e}")
    if errors:
        raise RuntimeError(f"GDC methylation downloads failed ({len(errors)}): {errors[:3]}")
    report["gdc_methylation"] = {"n_files": len(hits), "dest": str(out_dir)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Print planned operations only")
    ap.add_argument("--gdc-workers", type=int, default=4, help="Parallel GDC /data downloads for methylation")
    ap.add_argument(
        "--skip-gdc-methylation",
        action="store_true",
        help="Skip GDC TCGA-GBM open methylation beta phase (large; use for smoke tests).",
    )
    args = ap.parse_args()

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
        "components": [],
    }
    errors: list[str] = []

    try:
        blk = doc.get("gdsc_fitted_dose_response") or {}
        if blk.get("enabled"):
            dest_dir = root / str(blk.get("dest_dir", "pharmacogenomics/gdsc")).replace("/", os.sep)
            print("GDSC: fitted dose-response CSVs ...")
            for item in blk.get("files") or []:
                if not isinstance(item, dict):
                    continue
                url = item.get("url")
                fn = item.get("filename")
                if not url or not fn:
                    continue
                dest = dest_dir / fn
                print(f"  [{fn}] -> {dest}")
                if args.dry_run:
                    report["components"].append({"id": "gdsc", "file": fn, "dry_run": True})
                    continue
                dest_dir.mkdir(parents=True, exist_ok=True)
                t0 = time.time()
                dar.download_with_fallback(url, dest, resume=True)
                report["components"].append(
                    {
                        "id": "gdsc",
                        "file": fn,
                        "bytes": dest.stat().st_size,
                        "seconds": round(time.time() - t0, 2),
                    }
                )

        for prism_key in ("prism_depmap_primary", "prism_depmap_secondary"):
            blk = doc.get(prism_key) or {}
            if not blk.get("enabled"):
                continue
            dest_base = root / str(blk.get("dest_dir", "pharmacogenomics/prism_depmap")).replace("/", os.sep)
            subs = list(blk.get("filename_substrings") or [])
            rsub = str(blk.get("release_contains") or "")
            print(f"PRISM ({prism_key}): resolving DepMap release ...")
            if args.dry_run:
                report["components"].append({"id": prism_key, "dry_run": True, "release_contains": rsub})
                print(f"  [dry-run] would fetch DepMap CSV and download files matching {subs[:3]}...")
                continue
            rows = dar.fetch_depmap_rows()
            best_rel, picked = resolve_prism_file_rows(rows, rsub, subs)
            print(f"PRISM ({prism_key}): using {best_rel} ({len(picked)} files)")
            dest_base.mkdir(parents=True, exist_ok=True)
            for row in sorted(picked, key=lambda x: x["filename"]):
                dest = dest_base / row["filename"]
                print(f"  PRISM GET {row['filename']}")
                t0 = time.time()
                dar.download_with_fallback(row["url"], dest, resume=True)
                report["components"].append(
                    {
                        "id": prism_key,
                        "file": row["filename"],
                        "bytes": dest.stat().st_size,
                        "seconds": round(time.time() - t0, 2),
                    }
                )

        ot = doc.get("open_targets") or {}
        if ot.get("enabled"):
            ver = str(ot.get("platform_version") or "24.09")
            base = str(ot.get("dest_dir") or "pharmacogenomics/open_targets")
            bn = str(ot.get("target_json_basename") or "")
            url = f"https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/{ver}/output/etl/json/targets/{bn}"
            dest = root / base.replace("/", os.sep) / bn
            print(f"Open Targets: {bn} ...")
            if args.dry_run:
                report["components"].append({"id": "open_targets", "url": url, "dry_run": True})
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                t0 = time.time()
                dar.download_with_fallback(url, dest, resume=True)
                report["components"].append(
                    {
                        "id": "open_targets",
                        "file": bn,
                        "bytes": dest.stat().st_size,
                        "seconds": round(time.time() - t0, 2),
                    }
                )

        mb = doc.get("gdc_tcga_gbm_methylation_beta") or {}
        if mb.get("enabled") and not args.skip_gdc_methylation:
            sub = str(mb.get("subdir") or "gdc/tcga_gbm_open_methylation_beta")
            try:
                download_gdc_methylation_beta(root, sub, args.gdc_workers, args.dry_run, report)
            except Exception as ex:
                errors.append(f"gdc_methylation:{ex}")
                print(f"ERROR {ex}", file=sys.stderr)

        cxg = doc.get("cellxgene_census_h5ad") or {}
        if cxg.get("enabled"):
            s3base = str(cxg.get("s3_base_url") or "").rstrip("/")
            dest_root = root / str(cxg.get("dest_dir") or "references/scrna_cellxgene_census").replace("/", os.sep)
            print("CELLxGENE Census h5ad (public S3) ...")
            for ds in cxg.get("datasets") or []:
                if not isinstance(ds, dict):
                    continue
                did = str(ds.get("dataset_id") or "").strip()
                fn = str(ds.get("filename") or f"{did}.h5ad").strip()
                if not did:
                    continue
                url = f"{s3base}/{did}.h5ad"
                dest = dest_root / fn
                print(f"  [{did}] -> {dest}")
                if args.dry_run:
                    report["components"].append({"id": "cellxgene_census", "dataset_id": did, "dry_run": True})
                    continue
                dest_root.mkdir(parents=True, exist_ok=True)
                t0 = time.time()
                dar.download_with_fallback(url, dest, resume=True)
                report["components"].append(
                    {
                        "id": "cellxgene_census",
                        "dataset_id": did,
                        "bytes": dest.stat().st_size,
                        "seconds": round(time.time() - t0, 2),
                    }
                )

        cgga = doc.get("cgga") or {}
        if cgga.get("enabled") and cgga.get("invoke_movics_fetch"):
            print("CGGA: fetch_movics_staging_data (HTTP URLs from m2_movics_data_fetch.yaml) ...")
            if args.dry_run:
                report["components"].append({"id": "cgga_movics_fetch", "dry_run": True})
            else:
                r = subprocess.run(
                    [
                        sys.executable,
                        str(_REPO / "scripts" / "fetch_movics_staging_data.py"),
                        "--skip-depmap",
                        "--skip-cbttc",
                    ],
                    cwd=str(_REPO),
                    env={**os.environ},
                    capture_output=True,
                    text=True,
                )
                report["components"].append({"id": "cgga_movics_fetch", "exit_code": r.returncode})
                if r.returncode != 0:
                    errors.append("cgga_movics_fetch:nonzero_exit")
                    tail = (r.stderr or r.stdout or "").strip()[-2000:]
                    if tail:
                        print(tail, file=sys.stderr)
                else:
                    print(
                        "CGGA: fetch_movics_staging_data OK "
                        "(see results/module3/movics_staging_fetch_report.json)"
                    )

    except Exception as e:
        errors.append(str(e))
        print(f"ERROR: {e}", file=sys.stderr)

    report["finished"] = time.time()
    report["elapsed_sec"] = round(report["finished"] - report["started"], 2)
    report["errors"] = errors
    out = _REPO / "results" / "high_value_public_datasets_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
