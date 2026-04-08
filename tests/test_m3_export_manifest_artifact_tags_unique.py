"""_ARTIFACTS tags in write_module3_export_manifest.py must be unique (stable manifest keys)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from m3_export_manifest_artifacts_ast import (
    artifact_rel_paths_in_order_from_write_module3_script,
    artifact_tags_from_write_module3_script,
)

_ROOT = Path(__file__).resolve().parents[1]
_MANIFEST_SCRIPT = _ROOT / "scripts" / "write_module3_export_manifest.py"


def test_m3_export_manifest_artifact_tags_are_unique() -> None:
    tags = artifact_tags_from_write_module3_script(_MANIFEST_SCRIPT)
    counts = Counter(tags)
    dups = sorted(t for t, c in counts.items() if c > 1)
    assert not dups, f"duplicate _ARTIFACTS tag(s): {dups}"


def test_m3_export_manifest_artifact_rel_paths_are_unique() -> None:
    paths = artifact_rel_paths_in_order_from_write_module3_script(_MANIFEST_SCRIPT)
    counts = Counter(paths)
    dups = sorted(p for p, c in counts.items() if c > 1)
    assert not dups, f"duplicate _ARTIFACTS path(s): {dups}"
