"""Unit tests for scripts/manifest_optional.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "manifest_optional",
    _ROOT / "scripts" / "manifest_optional.py",
)
assert _SPEC and _SPEC.loader
_mod = importlib.util.module_from_spec(_SPEC)
sys.modules["manifest_optional"] = _mod
_SPEC.loader.exec_module(_mod)


def test_apply_optional_tags_marks_matching_rows() -> None:
    rows = [
        {"tag": "a", "exists": True},
        {"tag": "b", "exists": True},
    ]
    _mod.apply_optional_tags_to_artifacts(rows, ["b", None])
    assert rows[0].get("optional") is None
    assert rows[1].get("optional") is True


def test_apply_optional_tags_empty_iterable() -> None:
    rows = [{"tag": "x"}]
    _mod.apply_optional_tags_to_artifacts(rows, [])
    assert "optional" not in rows[0]
