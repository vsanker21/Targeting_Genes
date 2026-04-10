#!/usr/bin/env python3
"""
Set prisma screening_log.records_identified_total from a frozen PubMed esearch count (NCBI E-utilities).

Does not substitute for title/abstract or full-text screening tallies — those remain manual.

  python scripts/sync_prisma_pubmed_identified_count.py [--dry-run]

Requires network. Set NCBI_EMAIL for courteous API use (optional but recommended).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_PRISMA = _REPO / "config" / "prisma_literature_search.yaml"

PUBMED_QUERY = (
    "(glioblastoma OR \"diffuse glioma\" OR GBM) AND "
    "(expression OR transcriptom* OR RNA-seq OR microarray) AND "
    "(\"differential expression\" OR differentially expressed OR DESeq OR edgeR OR limma OR "
    "integration OR \"cross-platform\" OR batch OR recount OR harmoniz*)"
)


def _esearch_count(term: str, *, email: str) -> int:
    params = {
        "db": "pubmed",
        "term": term,
        "retmode": "xml",
        "retmax": "0",
    }
    if email:
        params["email"] = email
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": f"TargetingGenesPrismaSync/1.0 ({email or 'no-email'})"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read()
    root = ET.fromstring(body)
    cnt = root.findtext("Count")
    if cnt is None or not str(cnt).strip().isdigit():
        raise RuntimeError(f"unexpected esearch XML: {body[:500]!r}")
    return int(cnt)


def _patch_yaml(text: str, *, count: int, query: str, utc: str) -> str:
    text, n_sub = re.subn(
        r"^(\s*records_identified_total:\s*).*$",
        r"\g<1>" + str(count),
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n_sub != 1:
        raise RuntimeError("could not find records_identified_total: line to patch")

    qyaml = json.dumps(query)
    text, n_pub = re.subn(
        r"^(\s*pubmed_block_1:\s*).*$",
        r"\g<1>" + qyaml,
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n_pub != 1:
        raise RuntimeError("could not find pubmed_block_1: line to patch")

    block = (
        f"  pubmed_identified_count_retrieved_utc: \"{utc}\"\n"
        f'  pubmed_identified_count_tool: "scripts/sync_prisma_pubmed_identified_count.py (NCBI esearch.fcgi)"\n'
    )
    if "pubmed_identified_count_retrieved_utc:" not in text:
        text, n_inj = re.subn(
            r"^(\s*data_extraction_template:.*\n)(\s*suggested_reporting_checklist:)",
            r"\1" + block + r"\2",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if n_inj != 1:
            raise RuntimeError("could not inject pubmed timestamp block before suggested_reporting_checklist")
    else:
        text = re.sub(
            r"^\s*pubmed_identified_count_retrieved_utc:.*\n",
            f'  pubmed_identified_count_retrieved_utc: "{utc}"\n',
            text,
            count=1,
            flags=re.MULTILINE,
        )
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--query", type=str, default="", help="Override PubMed query string")
    args = ap.parse_args()

    import os

    email = os.environ.get("NCBI_EMAIL", "").strip()
    term = args.query.strip() or PUBMED_QUERY
    try:
        n = _esearch_count(term, email=email)
    except Exception as e:
        print(f"ERROR: PubMed esearch failed: {e}", file=sys.stderr)
        return 1
    time.sleep(0.35)

    utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"PubMed Count={n} retrieved_utc={utc}")
    if args.dry_run:
        return 0

    raw = _PRISMA.read_text(encoding="utf-8")
    out = _patch_yaml(raw, count=n, query=term, utc=utc)
    _PRISMA.write_text(out, encoding="utf-8")
    print(f"Updated {_PRISMA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
