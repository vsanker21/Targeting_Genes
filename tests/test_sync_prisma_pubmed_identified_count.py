from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load_sync_module():
    p = _ROOT / "scripts" / "sync_prisma_pubmed_identified_count.py"
    spec = importlib.util.spec_from_file_location("sync_prisma_pubmed", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_patch_yaml_updates_identified_and_query() -> None:
    sp = _load_sync_module()
    raw = """prisma_literature_search:
  search_strings:
    pubmed_block_1: ""
  screening_log:
    records_identified_total: null
  data_extraction_template: "docs/x.md"
  suggested_reporting_checklist:
    - "a"
"""
    out = sp._patch_yaml(raw, count=3607, query='(brain) AND "test"', utc="2026-04-10T00:00:00Z")
    assert "records_identified_total: 3607" in out
    assert "brain" in out and "test" in out
    assert "pubmed_identified_count_retrieved_utc" in out
