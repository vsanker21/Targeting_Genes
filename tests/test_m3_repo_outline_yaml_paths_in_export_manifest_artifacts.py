"""Every path in config/m3_repo_*_outline_inputs.yaml path_checks is listed in _ARTIFACTS."""

from __future__ import annotations

import re
from pathlib import Path

from m3_export_manifest_artifacts_ast import artifact_rel_paths_from_write_module3_script

_ROOT = Path(__file__).resolve().parents[1]
_MANIFEST_SCRIPT = _ROOT / "scripts" / "write_module3_export_manifest.py"
_CONFIG = _ROOT / "config"


def _yaml_outline_paths() -> set[str]:
    paths: set[str] = set()
    for yp in sorted(_CONFIG.glob("m3_repo_*_outline_inputs.yaml")):
        text = yp.read_text(encoding="utf-8")
        for m in re.finditer(r"path_template:\s*\"\{repo_root\}/([^\"]+)\"", text):
            paths.add(m.group(1).replace("\\", "/"))
    return paths


def test_all_m3_repo_outline_path_templates_are_export_manifest_artifacts() -> None:
    artifacts = artifact_rel_paths_from_write_module3_script(_MANIFEST_SCRIPT)
    yaml_paths = _yaml_outline_paths()
    missing = sorted(yaml_paths - artifacts)
    assert not missing, f"{len(missing)} outline path(s) missing from _ARTIFACTS, e.g. {missing[:12]}"
