#!/usr/bin/env python3
"""
Intersection of line-delimited HGNC symbol lists (uppercase, one symbol per line).

Used for WGCNA hub gene selection: e.g. recount3 PyDESeq2 vs edgeR DepMap-gated STRING
exports — keep only symbols present in every input file (cross-model robustness).

Usage:
  python intersect_symbol_lists.py OUTPUT.txt INPUT1.txt INPUT2.txt [INPUT3.txt ...]
"""

from __future__ import annotations

import sys
from pathlib import Path


def load_symbols(path: Path) -> set[str]:
    out: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip().upper()
        if s and not s.startswith("#"):
            out.add(s)
    return out


def main() -> int:
    if len(sys.argv) < 4:
        print(
            "Usage: intersect_symbol_lists.py OUTPUT.txt INPUT1.txt INPUT2.txt ...",
            file=sys.stderr,
        )
        return 1
    out_path = Path(sys.argv[1])
    in_paths = [Path(p) for p in sys.argv[2:]]
    sets: list[set[str]] = []
    for p in in_paths:
        if not p.is_file():
            print(f"Missing input {p}", file=sys.stderr)
            return 2
        sets.append(load_symbols(p))
    if not sets:
        print("No inputs", file=sys.stderr)
        return 3
    inter = set.intersection(*sets)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(sorted(inter)) + ("\n" if inter else ""), encoding="utf-8")
    print(f"Wrote {out_path} n_symbols={len(inter)} from {len(in_paths)} lists")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
