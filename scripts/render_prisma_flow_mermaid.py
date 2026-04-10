#!/usr/bin/env python3
"""
Emit a PRISMA 2020-style flowchart (Mermaid) from config/prisma_literature_search.yaml screening_log.

  python scripts/render_prisma_flow_mermaid.py [--output PATH] [--demo]

Use --demo for a layout-only figure before real screening counts exist.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import yaml

_REPO = Path(__file__).resolve().parents[1]


def _load_prisma() -> dict[str, Any]:
    p = _REPO / "config" / "prisma_literature_search.yaml"
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return doc.get("prisma_literature_search") or {}


def _n(v: Any, demo: int) -> str:
    if v is None:
        return "?" if not demo else str(demo)
    return str(int(v))


def build_mermaid(block: dict[str, Any], *, demo: bool) -> str:
    sl = block.get("screening_log") or {}
    # Demo numbers are arbitrary placeholders for figure layout only.
    d = 1200 if demo else 0
    ident = _n(sl.get("records_identified_total"), 2400 + d)
    dup = _n(sl.get("duplicates_removed"), 400 + d // 4)
    screened = _n(sl.get("records_screened_title_abstract"), 2000 + d)
    excl_ta = _n(sl.get("records_excluded_title_abstract"), 1700 + d)
    ft = _n(sl.get("full_text_assessed"), 300 + d // 5)
    excl_list = sl.get("full_text_excluded_with_reasons") or []
    if demo:
        excl_ft = _n(None, 220 + d // 10)
    else:
        excl_ft = str(len(excl_list))
    qual = sl.get("studies_qualitative_synthesis")
    quant = sl.get("studies_quantitative_analysis")
    n_qual = _n(qual, 65 + d // 50) if demo or qual is not None else "?"
    n_quant = _n(quant, 12 + d // 100) if demo or quant is not None else "?"

    title = block.get("objective_one_liner", "").strip().replace("\n", " ")[:120]
    hdr = f"%% PRISMA flow — {title}\n%% Regenerate: python scripts/render_prisma_flow_mermaid.py\n"
    return f"""{hdr}flowchart TD
    A["Records identified<br/>databases n = {ident}"]
    B["Duplicates removed<br/>n = {dup}"]
    C["Records screened<br/>title/abstract n = {screened}"]
    D["Records excluded<br/>title/abstract n = {excl_ta}"]
    E["Reports sought for retrieval"]
    F["Reports not retrieved"]
    G["Reports assessed<br/>full-text n = {ft}"]
    H["Reports excluded full-text<br/>n = {excl_ft}"]
    I["Studies included in<br/>qualitative synthesis n = {n_qual}"]
    J["Studies in quantitative<br/>synthesis n = {n_quant}"]

    A --> B
    B --> C
    C --> D
    C --> E
    E --> F
    E --> G
    G --> H
    G --> I
    I --> J
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--output",
        type=Path,
        default=_REPO / "results" / "manuscript" / "prisma_flowchart.mmd",
        help="Output .mmd path",
    )
    ap.add_argument("--demo", action="store_true", help="Use placeholder counts for layout")
    args = ap.parse_args()

    block = _load_prisma()
    text = build_mermaid(block, demo=args.demo)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"Wrote {args.output}")
    print("Render: paste into https://mermaid.live or use Mermaid CLI / Quarto / Obsidian.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
