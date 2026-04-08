#!/usr/bin/env python3
"""
Discover the current WikiPathways Homo_sapiens GMT filename on wmcloud and optionally patch YAML.

  python scripts/sync_wikipathways_gmt_url.py [--write-yaml]

Set GLIOMA_TARGET_WIKIPATHWAYS_SYNC_YAML=1 to allow --write-yaml from Snakemake (safety).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[1]
_CFG = _REPO / "config" / "supplementary_reference_resources.yaml"
_INDEX = "https://wikipathways-data.wmcloud.org/current/gmt/"
# Index HTML uses single-quoted href (e.g. href='./wikipathways-YYYYMMDD-gmt-Homo_sapiens.gmt').
_PATTERN = re.compile(
    r"href=['\"](?:\./)?(wikipathways-(\d{8})-gmt-Homo_sapiens\.gmt)['\"]",
    re.I,
)
_UA = "GLIOMA-TARGET-wikipathways-sync/1.0"


def _latest_gmt_url(html: str) -> tuple[str | None, str | None]:
    """Return (full_url, filename) for the latest dated Homo_sapiens GMT in the index."""
    best: tuple[int, str, str] | None = None
    for m in _PATTERN.finditer(html):
        fn, ymd = m.group(1), m.group(2)
        key = int(ymd)
        if best is None or key > best[0]:
            best = (key, fn, f"{_INDEX.rstrip('/')}/{fn}")
    if best is None:
        return None, None
    return best[2], best[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--write-yaml",
        action="store_true",
        help="Patch supplementary_reference_resources.yaml when URL differs (needs env GLIOMA_TARGET_WIKIPATHWAYS_SYNC_YAML=1).",
    )
    ap.add_argument("--timeout", type=int, default=120)
    args = ap.parse_args()

    req = urllib.request.Request(_INDEX, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=args.timeout) as r:
        html = r.read().decode("utf-8", "replace")

    new_url, new_fn = _latest_gmt_url(html)
    if not new_url:
        print("Could not find Homo_sapiens GMT link in index", file=sys.stderr)
        return 1

    doc = yaml.safe_load(_CFG.read_text(encoding="utf-8"))
    pw = (doc.get("pathways") or {}).get("wikipathways_homo_sapiens_gmt") or {}
    old_url = str(pw.get("url") or "").strip()

    report = {
        "index_url": _INDEX,
        "resolved_latest_url": new_url,
        "resolved_latest_filename": new_fn,
        "yaml_current_url": old_url or None,
        "urls_match": old_url == new_url,
    }

    out_dir = _REPO / "results" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / "wikipathways_gmt_url_sync.json"
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out_json}")

    if old_url != new_url:
        print(f"NOTE: YAML URL differs from index latest.\n  yaml: {old_url}\n  latest: {new_url}")
        if args.write_yaml:
            if not os.environ.get("GLIOMA_TARGET_WIKIPATHWAYS_SYNC_YAML", "").strip().lower() in (
                "1",
                "true",
                "yes",
                "on",
            ):
                print(
                    "Refusing --write-yaml without GLIOMA_TARGET_WIKIPATHWAYS_SYNC_YAML=1",
                    file=sys.stderr,
                )
                return 2
            text = _CFG.read_text(encoding="utf-8")
            if old_url and old_url in text:
                text = text.replace(old_url, new_url, 1)
            else:
                print("Could not find old URL in YAML to replace", file=sys.stderr)
                return 3
            _CFG.write_text(text, encoding="utf-8")
            print(f"Updated {_CFG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
