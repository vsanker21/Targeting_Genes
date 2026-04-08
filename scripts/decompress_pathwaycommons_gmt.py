#!/usr/bin/env python3
"""Decompress PathwayCommons *.gmt.gz to plain *.gmt (stdlib gzip; no extra deps)."""

from __future__ import annotations

import argparse
import gzip
import shutil
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gz", type=Path, required=True, help="Input .gmt.gz path")
    ap.add_argument("--out", type=Path, required=True, help="Output .gmt path")
    args = ap.parse_args()
    src, dst = args.gz.resolve(), args.out.resolve()
    if not src.is_file():
        print(f"ERROR: missing gzip input: {src}", file=sys.stderr)
        return 1
    dst.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(src, "rb") as f_in, open(dst, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out, length=1024 * 1024)
    print(f"Wrote {dst} ({dst.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
