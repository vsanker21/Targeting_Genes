"""Guards on demo snapshot copy (never clobber real TOIL DEA by accident)."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_smoke(repo: Path):
    path = repo / "scripts" / "run_supplementary_enrichment_smoke.py"
    spec = importlib.util.spec_from_file_location("rss", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dea_looks_real_threshold(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    m = _load_smoke(repo)
    small = tmp_path / "dea.tsv"
    small.write_text("gene_id\tpadj\n" + "\n".join(f"ENSG{i}\t0.1" for i in range(50)), encoding="utf-8")
    assert m._dea_looks_real(small) is False

    big = tmp_path / "dea2.tsv"
    big.write_text("gene_id\tpadj\n" + "\n".join(f"ENSG{i}\t0.1" for i in range(250)), encoding="utf-8")
    assert m._dea_looks_real(big) is True
