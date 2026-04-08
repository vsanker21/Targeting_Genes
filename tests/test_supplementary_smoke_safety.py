"""Unit tests for run_supplementary_enrichment_smoke.py safety helpers (importlib load)."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_smoke_module(repo: Path):
    path = repo / "scripts" / "run_supplementary_enrichment_smoke.py"
    spec = importlib.util.spec_from_file_location("_rss_safety", path)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_dea_looks_real_below_threshold(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    m = _load_smoke_module(repo)
    n = m._REAL_DEA_MIN_LINES
    # Total lines n-1 (header + n-2 data rows) -> below threshold
    small = tmp_path / "dea.tsv"
    small.write_text("header\n" + "\n".join(f"g{i}" for i in range(n - 2)), encoding="utf-8")
    assert sum(1 for _ in small.open(encoding="utf-8")) == n - 1
    assert not m._dea_looks_real(small)


def test_dea_looks_real_at_threshold(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    m = _load_smoke_module(repo)
    n = m._REAL_DEA_MIN_LINES
    big = tmp_path / "dea.tsv"
    big.write_text("header\n" + "\n".join(f"g{i}" for i in range(n - 1)), encoding="utf-8")
    assert sum(1 for _ in big.open(encoding="utf-8")) == n
    assert m._dea_looks_real(big)


def test_line_count_caps(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    m = _load_smoke_module(repo)
    huge = tmp_path / "x.tsv"
    huge.write_text("h\n" + "\n".join("x" for _ in range(10_000)), encoding="utf-8")
    # _line_count caps at REAL_DEA_MIN_LINES + 50 for performance
    c = m._line_count(huge)
    assert c == m._REAL_DEA_MIN_LINES + 50
    assert m._dea_looks_real(huge)
