"""
Build a subprocess environment for Snakemake CLI calls.

Strips optional ``rule all`` gate variables (``GLIOMA_TARGET_INCLUDE_*``) so DAG resolution
matches the default pipeline when the parent shell has e.g. M7 reporting flags set.

Used by: pytest (via ``pythonpath``), ``run_supplementary_enrichment_smoke.py``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Must match every `_env_truthy("GLIOMA_TARGET_INCLUDE_…")` in Snakefile `_rule_all_optional_inputs`.
OPTIONAL_RULE_ALL_ENV_KEYS: tuple[str, ...] = (
    "GLIOMA_TARGET_INCLUDE_CLINVAR",
    "GLIOMA_TARGET_INCLUDE_M3_SCANPY",
    "GLIOMA_TARGET_INCLUDE_MOVICS",
    "GLIOMA_TARGET_INCLUDE_MOVICS_DEPMAP_MAE",
    "GLIOMA_TARGET_INCLUDE_SUPPLEMENTARY_WIRING",
    "GLIOMA_TARGET_INCLUDE_M7_DELIVERABLES",
    "GLIOMA_TARGET_INCLUDE_M7_VIZ",
    "GLIOMA_TARGET_INCLUDE_M7_DOCX",
    "GLIOMA_TARGET_INCLUDE_M5_SRGES_RUN",
    "GLIOMA_TARGET_INCLUDE_M3_DECONV_S2",
    "GLIOMA_TARGET_INCLUDE_M3_RCTD_RUN",
    "GLIOMA_TARGET_INCLUDE_M3_CELL2LOCATION_RUN",
)

M7_OPTIONAL_RULE_ALL_KEYS: tuple[str, ...] = tuple(
    k for k in OPTIONAL_RULE_ALL_ENV_KEYS if "_M7_" in k
)


def optional_rule_all_env_keys_from_snakefile(snakefile: Path) -> set[str]:
    """Parse Snakefile for `_env_truthy(\"GLIOMA_TARGET_INCLUDE_*\")` in `_rule_all_optional_inputs`."""
    text = snakefile.read_text(encoding="utf-8")
    i = text.find("def _rule_all_optional_inputs")
    if i < 0:
        return set()
    j = text.find("\ndef ", i + 1)
    block = text[i:] if j < 0 else text[i:j]
    return set(re.findall(r'_env_truthy\("(GLIOMA_TARGET_INCLUDE_[^"]+)"\)', block))


def snakemake_subprocess_env(*, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Copy ``os.environ``, apply ``extra``, then drop optional ``rule all`` gate env vars."""
    env = {**os.environ, **(extra or {})}
    for k in OPTIONAL_RULE_ALL_ENV_KEYS:
        env.pop(k, None)
    return env
