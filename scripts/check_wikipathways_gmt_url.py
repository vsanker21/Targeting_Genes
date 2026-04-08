#!/usr/bin/env python3
"""HEAD-request the WikiPathways GMT URL from supplementary_reference_resources.yaml (exit 1 if not HTTP 200)."""

from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[1]
_CFG = _REPO / "config/supplementary_reference_resources.yaml"
_UA = "GLIOMA-TARGET-wikipathways-check/1.0"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args()
    if not _CFG.is_file():
        print(f"Missing {_CFG}", file=sys.stderr)
        return 1
    doc = yaml.safe_load(_CFG.read_text(encoding="utf-8"))
    pw = (doc.get("pathways") or {}).get("wikipathways_homo_sapiens_gmt") or {}
    url = str(pw.get("url") or "").strip()
    if not url:
        print("No pathways.wikipathways_homo_sapiens_gmt.url in YAML", file=sys.stderr)
        return 1
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as r:
            code = getattr(r, "status", r.getcode())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} for {url}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"URL error: {e}", file=sys.stderr)
        return 1
    if code != 200:
        print(f"Unexpected status {code} for {url}", file=sys.stderr)
        return 1
    print(f"OK {code} {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
