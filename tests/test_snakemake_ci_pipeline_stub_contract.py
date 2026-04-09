"""Ensure pipeline dry-run stubs stay aligned with Snakefile (avoids CI-only MissingInputException)."""

from __future__ import annotations

import re
from pathlib import Path

from snakemake_ci_data_stubs import _PIPELINE_DRY_RUN_REPO_REL_FILES

_ROOT = Path(__file__).resolve().parents[1]


def _m2_outline_driver_flags_results_inputs() -> set[str]:
    """Relative paths under repo ``results/`` for rule ``m2_outline_driver_flags`` (file inputs only)."""
    text = (_ROOT / "Snakefile").read_text(encoding="utf-8")
    m = re.search(
        r"rule m2_outline_driver_flags:\s*(?:\"\"\"[^\"]*\"\"\")?\s*input:\s*(.*?)^\s*output:",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert m is not None, "Snakefile: rule m2_outline_driver_flags input block not found"
    block = m.group(1)
    out: set[str] = set()
    for mo in re.finditer(r'=\s*"(results/module3[^"]+)"', block):
        rel = mo.group(1)
        assert rel.startswith("results/"), rel
        out.add(rel[len("results/") :])
    return out


def test_pipeline_dry_run_stubs_cover_m2_outline_driver_flags_inputs() -> None:
    """If this fails, extend ``_PIPELINE_DRY_RUN_REPO_REL_FILES`` in ``snakemake_ci_data_stubs.py``."""
    required = _m2_outline_driver_flags_results_inputs()
    stub = set(_PIPELINE_DRY_RUN_REPO_REL_FILES)
    missing = sorted(required - stub)
    assert not missing, (
        "Snakefile m2_outline_driver_flags expects these under results/; add them to "
        f"_PIPELINE_DRY_RUN_REPO_REL_FILES: {missing}"
    )
