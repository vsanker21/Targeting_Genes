"""Regression: authoritative pipeline outline YAML parses."""

from __future__ import annotations

from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]


def test_pipeline_outline_yaml_parses() -> None:
    path = _ROOT / "config" / "pipeline_outline.yaml"
    assert path.is_file()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and data
    assert "modules" in data
    assert isinstance(data["modules"], dict)
