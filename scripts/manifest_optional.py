"""Shared helpers for module export manifest JSON rows (optional tagging).

Used by write_module{3,4,5,6,7}_export_manifest.py (same directory → importable as manifest_optional).
"""

from __future__ import annotations

from typing import Any, Iterable


def apply_optional_tags_to_artifacts(
    artifacts: list[dict[str, Any]],
    optional_tags: Iterable[str | None],
) -> None:
    """Set row['optional'] = True when row['tag'] is in optional_tags (None entries ignored)."""
    tag_set = {str(t) for t in optional_tags if t is not None}
    for row in artifacts:
        if row.get("tag") in tag_set:
            row["optional"] = True
