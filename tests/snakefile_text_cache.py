"""Load Snakefile once per process; many tests call rule_block on the same large file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def snakefile_text() -> str:
    return (_REPO_ROOT / "Snakefile").read_text(encoding="utf-8")
