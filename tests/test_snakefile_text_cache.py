"""snakefile_text_cache: single read of the workflow file per pytest process."""

from __future__ import annotations

from snakefile_text_cache import snakefile_text


def test_snakefile_text_nonempty_and_has_core_rules() -> None:
    text = snakefile_text()
    assert len(text) > 50_000
    assert "rule all:" in text
    assert "rule pipeline_results_index:" in text
    assert "rule m3_export_manifest:" in text


def test_snakefile_text_returns_same_object_when_called_again() -> None:
    a = snakefile_text()
    b = snakefile_text()
    assert a is b
