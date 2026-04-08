"""Every m3_repo_* outline path_checks path appears in rule m3_export_manifest inputs (DAG parity)."""

from __future__ import annotations

import re
from pathlib import Path

from snakefile_rule_block import rule_block
from snakefile_text_cache import snakefile_text

_ROOT = Path(__file__).resolve().parents[1]
_SNAKE = snakefile_text()
_CONFIG = _ROOT / "config"


def _yaml_outline_paths() -> set[str]:
    paths: set[str] = set()
    for yp in sorted(_CONFIG.glob("m3_repo_*_outline_inputs.yaml")):
        text = yp.read_text(encoding="utf-8")
        for m in re.finditer(r"path_template:\s*\"\{repo_root\}/([^\"]+)\"", text):
            paths.add(m.group(1).replace("\\", "/"))
    return paths


def test_m3_repo_outline_path_templates_are_m3_export_manifest_inputs() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    yaml_paths = _yaml_outline_paths()
    missing = sorted(p for p in yaml_paths if p not in blk)
    assert not missing, f"{len(missing)} outline path(s) missing from rule m3_export_manifest, e.g. {missing[:15]}"
