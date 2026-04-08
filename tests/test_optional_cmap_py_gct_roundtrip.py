"""Regression test for cmapPy GCT I/O (same check as ensure_optional_third_party_functional)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "ensure_optional_third_party_functional",
    _ROOT / "scripts" / "ensure_optional_third_party_functional.py",
)
assert _SPEC and _SPEC.loader
_mod = importlib.util.module_from_spec(_SPEC)
sys.modules["ensure_optional_third_party_functional"] = _mod
_SPEC.loader.exec_module(_mod)


def test_cmap_py_gct_roundtrip() -> None:
    pytest.importorskip("cmapPy")
    _mod.functional_cmap_py_gct_roundtrip()
