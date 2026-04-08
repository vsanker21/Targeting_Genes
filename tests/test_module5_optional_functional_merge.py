"""Unit tests for optional_third_party_functional merge into M5 cmap scan summary."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "module5_cmap_tooling_scan",
    _ROOT / "scripts" / "module5_cmap_tooling_scan.py",
)
assert _SPEC and _SPEC.loader
_m5 = importlib.util.module_from_spec(_SPEC)
sys.modules["module5_cmap_tooling_scan"] = _m5
_SPEC.loader.exec_module(_m5)


def test_summarize_optional_functional_gct_ok(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    rr = tmp_path / "repo"
    (rr / "config").mkdir(parents=True)
    rep = rr / "results" / "optional_third_party_functional_report.json"
    rep.parent.mkdir(parents=True)
    rep.write_text(
        json.dumps(
            {
                "generated_utc": "2020-01-01T00:00:00+00:00",
                "checks": [
                    {"id": "cmapPy_pip", "ok": True, "skipped": True},
                    {"id": "cmapPy_gct_roundtrip", "ok": True},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(_m5, "repo_root", lambda: rr)
    out = _m5.summarize_optional_functional_report(rep)
    assert out is not None
    assert out["cmapPy_gct_roundtrip_ok"] is True
    assert out["report_path"] == "results/optional_third_party_functional_report.json"
    assert any(c.get("id") == "cmapPy_pip" and c.get("skipped") is True for c in out["checks"])


def test_summarize_optional_functional_malformed(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    rr = tmp_path / "repo"
    rep = rr / "bad.json"
    rep.parent.mkdir(parents=True)
    rep.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(_m5, "repo_root", lambda: rr)
    assert _m5.summarize_optional_functional_report(rep) is None
