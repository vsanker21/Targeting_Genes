"""Regression: M3 export manifest lists M4 STRING cache path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TEXT = (_ROOT / "scripts" / "write_module3_export_manifest.py").read_text(encoding="utf-8")
_YAML = (_ROOT / "config" / "m3_repo_module4_string_cache_outline_inputs.yaml").read_text(encoding="utf-8")


def test_write_module3_export_manifest_includes_repo_module4_string_cache_paths() -> None:
    assert "m3_repo_module4_string_cache_paths_status.json" in _TEXT
    assert "m3_sc.repo_module4_string_cache_paths_status" in _TEXT


def test_write_module3_export_manifest_includes_repo_module4_string_cache_stub() -> None:
    assert "m3_repo_module4_string_cache_integration_stub.json" in _TEXT
    assert "m3_sc.repo_module4_string_cache_integration_stub" in _TEXT


def test_module4_string_cache_outline_data_paths_in_manifest() -> None:
    assert "m4_string_cache_paths_status.json" in _YAML
    assert "results/module4/m4_string_cache_paths_status.json" in _TEXT
    assert "m4.string_cache.paths_status_json" in _TEXT
