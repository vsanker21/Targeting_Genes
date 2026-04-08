"""Unit tests for scripts/snakemake_subprocess_env.py (Snakemake subprocess env helper)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from snakemake_subprocess_env import (
    OPTIONAL_RULE_ALL_ENV_KEYS,
    optional_rule_all_env_keys_from_snakefile,
    snakemake_subprocess_env,
)

_REPO = Path(__file__).resolve().parents[1]


def test_optional_rule_all_env_keys_match_snakefile() -> None:
    """Keep OPTIONAL_RULE_ALL_ENV_KEYS aligned with Snakefile `_rule_all_optional_inputs`."""
    from_snake = optional_rule_all_env_keys_from_snakefile(_REPO / "Snakefile")
    assert from_snake == set(OPTIONAL_RULE_ALL_ENV_KEYS), (
        f"Snakefile keys: {sorted(from_snake)}\n"
        f"helper keys: {sorted(OPTIONAL_RULE_ALL_ENV_KEYS)}\n"
        "Update scripts/snakemake_subprocess_env.py OPTIONAL_RULE_ALL_ENV_KEYS."
    )


def test_snakemake_subprocess_env_strips_optional_rule_all_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in OPTIONAL_RULE_ALL_ENV_KEYS:
        monkeypatch.setenv(k, "1")
    monkeypatch.setenv("GLIOMA_TARGET_DATA_ROOT", "/tmp/x")
    env = snakemake_subprocess_env(extra={"OTHER": "y"})
    for k in OPTIONAL_RULE_ALL_ENV_KEYS:
        assert k not in env
    assert env.get("OTHER") == "y"
    assert env.get("GLIOMA_TARGET_DATA_ROOT") == "/tmp/x"


def test_snakemake_subprocess_env_without_extra_copies_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GLIOMA_TARGET_INCLUDE_M7_DELIVERABLES", raising=False)
    env = snakemake_subprocess_env()
    assert env.get("PATH") == os.environ.get("PATH")
