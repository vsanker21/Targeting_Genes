"""Hardcoded results/module{4,5,6,7}/ paths in export-manifest writers must appear in matching Snakemake rules."""

from __future__ import annotations

import re
from pathlib import Path

from snakefile_rule_block import rule_block
from snakefile_text_cache import snakefile_text

_ROOT = Path(__file__).resolve().parents[1]
_SNAKE = snakefile_text()

_EXCLUDE_EXACT = {
    "results/module4/module4_export_manifest.json",
    "results/module5/module5_export_manifest.json",
    "results/module6/module6_export_manifest.json",
    "results/module7/module7_export_manifest.json",
}
# Directory roots walked with rglob; individual files are listed separately on the rules.
_DIR_SCAN_ROOTS = {
    "results/module4/gsea/stratified",
    "results/module6/structure_druggability_bridge_stratified",
    "results/module7/gts_candidate_stratified",
}


def _quoted_results_paths(script: Path, module: int) -> set[str]:
    text = script.read_text(encoding="utf-8")
    rx = re.compile(rf'"results/module{module}/[^"]+"')
    return {m.group(0).strip('"') for m in rx.finditer(text)}


def _assert_writer_paths_in_rule(module: int, rule_name: str) -> None:
    script = _ROOT / "scripts" / f"write_module{module}_export_manifest.py"
    paths = _quoted_results_paths(script, module)
    paths -= _EXCLUDE_EXACT
    paths -= _DIR_SCAN_ROOTS
    blk = rule_block(_SNAKE, rule_name)
    missing = sorted(p for p in paths if p not in blk)
    assert not missing, (
        f"write_module{module}_export_manifest.py literals missing from {rule_name}:\n" + "\n".join(missing)
    )


def test_write_module4_export_manifest_literals_in_m4_export_manifest_rule() -> None:
    _assert_writer_paths_in_rule(4, "m4_export_manifest")


def test_write_module5_export_manifest_literals_in_m5_export_manifest_rule() -> None:
    _assert_writer_paths_in_rule(5, "m5_export_manifest")


def test_write_module6_export_manifest_literals_in_m6_export_manifest_rule() -> None:
    _assert_writer_paths_in_rule(6, "m6_export_manifest")


def test_write_module7_export_manifest_literals_in_m7_export_manifest_rule() -> None:
    _assert_writer_paths_in_rule(7, "m7_export_manifest")
