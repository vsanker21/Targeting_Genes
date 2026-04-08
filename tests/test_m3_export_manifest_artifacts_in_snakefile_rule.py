"""Every _ARTIFACTS relative path in write_module3_export_manifest.py appears in rule m3_export_manifest."""

from __future__ import annotations

from pathlib import Path

import yaml

from m3_export_manifest_artifacts_ast import artifact_rel_paths_from_write_module3_script
from snakefile_rule_block import rule_block
from snakefile_text_cache import snakefile_text
from write_module3_export_manifest import _ARTIFACTS, _ARTIFACTS_EXEMPT_FROM_SNAKEFILE_MANIFEST_INPUTS

_ROOT = Path(__file__).resolve().parents[1]
_MANIFEST_SCRIPT = _ROOT / "scripts" / "write_module3_export_manifest.py"
_M3_CFG = _ROOT / "config" / "module3_inputs.yaml"
_SNAKE = snakefile_text()


def test_m3_export_manifest_artifacts_are_snakemake_inputs() -> None:
    artifacts = artifact_rel_paths_from_write_module3_script(_MANIFEST_SCRIPT)
    required = artifacts - _ARTIFACTS_EXEMPT_FROM_SNAKEFILE_MANIFEST_INPUTS
    blk = rule_block(_SNAKE, "m3_export_manifest")
    missing = sorted(p for p in required if p not in blk)
    assert not missing, f"{len(missing)} _ARTIFACTS path(s) missing from rule m3_export_manifest, e.g. {missing[:20]}"


def test_m3_export_manifest_exempt_artifacts_are_inventory_only() -> None:
    artifacts = artifact_rel_paths_from_write_module3_script(_MANIFEST_SCRIPT)
    assert _ARTIFACTS_EXEMPT_FROM_SNAKEFILE_MANIFEST_INPUTS <= artifacts
    blk = rule_block(_SNAKE, "m3_export_manifest")
    leaked = sorted(p for p in _ARTIFACTS_EXEMPT_FROM_SNAKEFILE_MANIFEST_INPUTS if p in blk)
    assert not leaked, (
        "optional RCTD/Cell2location paths must not be m3_export_manifest inputs (breaks snakemake dry-run): "
        f"{leaked}"
    )


def test_module3_optional_tags_cover_exempt_manifest_paths() -> None:
    """RCTD/c2l rows are optional in the JSON and must stay tagged so strict pipeline index passes."""
    doc = yaml.safe_load(_M3_CFG.read_text(encoding="utf-8"))
    opt = {str(t) for t in (doc.get("module3_export_manifest") or {}).get("optional_tags") or []}
    exempt_tags = {tag for path, tag in _ARTIFACTS if path in _ARTIFACTS_EXEMPT_FROM_SNAKEFILE_MANIFEST_INPUTS}
    missing = exempt_tags - opt
    assert not missing, f"module3_export_manifest.optional_tags missing: {sorted(missing)}"


def test_module3_inputs_extra_artifact_paths_are_snakemake_inputs() -> None:
    """Dynamic manifest rows from module3_inputs.yaml must be DAG inputs when present."""
    doc = yaml.safe_load(_M3_CFG.read_text(encoding="utf-8"))
    block = doc.get("module3_export_manifest") or {}
    extras = block.get("extra_artifacts") or []
    blk = rule_block(_SNAKE, "m3_export_manifest")
    missing: list[str] = []
    for i, item in enumerate(extras):
        if not isinstance(item, dict):
            continue
        rel = str(item.get("path", "") or "").strip().replace("\\", "/")
        if not rel:
            continue
        if rel not in blk:
            missing.append(f"[{i}] {rel}")
    assert not missing, (
        "extra_artifacts path(s) missing from rule m3_export_manifest "
        f"(add named input or the rule will not rebuild when they change): {missing}"
    )
