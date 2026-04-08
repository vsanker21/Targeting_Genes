"""Tests for scripts/write_pipeline_results_index.py (optional_path_posix merge + unmatched)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "write_pipeline_results_index",
    _ROOT / "scripts" / "write_pipeline_results_index.py",
)
assert _SPEC and _SPEC.loader
_wpri = importlib.util.module_from_spec(_SPEC)
sys.modules["write_pipeline_results_index"] = _wpri
_SPEC.loader.exec_module(_wpri)


def _write_minimal_repo(
    tmp: Path,
    *,
    optional_path_posix: list[str],
    artifact_path: str = "results/stub.txt",
    create_stub: bool = True,
) -> None:
    (tmp / "config").mkdir(parents=True)
    (tmp / "results").mkdir(parents=True)
    man = {
        "outline_module": 3,
        "artifacts": [
            {
                "tag": "stub",
                "path": artifact_path,
                "path_posix": artifact_path,
            }
        ],
    }
    mp = tmp / "results" / "module3_export_manifest.json"
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(json.dumps(man), encoding="utf-8")
    inv = {
        "pipeline_results_index": {
            "enabled": True,
            "output_json": "results/pipeline_results_index.json",
            "optional_path_posix": optional_path_posix,
            "manifest_paths": ["results/module3_export_manifest.json"],
            "provenance_paths": [],
        }
    }
    (tmp / "config" / "pipeline_inventory.yaml").write_text(
        yaml.safe_dump(inv, sort_keys=False),
        encoding="utf-8",
    )
    if create_stub:
        stub = tmp / Path(artifact_path)
        stub.parent.mkdir(parents=True, exist_ok=True)
        stub.write_text("x", encoding="utf-8")


def test_optional_path_posix_marks_optional(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rr = tmp_path / "repo"
    ap = "results/stub.txt"
    _write_minimal_repo(rr, optional_path_posix=[ap], artifact_path=ap)
    monkeypatch.setattr(_wpri, "repo_root", lambda: rr)
    assert _wpri.main() == 0
    out = json.loads((rr / "results" / "pipeline_results_index.json").read_text(encoding="utf-8"))
    assert out["summary"]["optional_path_posix_unmatched"] == []
    assert out["summary"]["index_schema"] == _wpri.INDEX_SCHEMA
    ss = out["summary"]["sources_summary"]
    assert ss["n_manifest"] == 1 and ss["n_manifest_loaded"] == 1
    assert ss["n_provenance"] == 0
    ent = next(e for e in out["entries"] if e["path_posix"] == ap)
    assert ent.get("optional") is True


def test_absolute_provenance_output_dedupes_manifest_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Harvested absolute paths under repo root merge with manifest-relative keys."""
    rr = tmp_path / "repo"
    ap = "results/stub.txt"
    _write_minimal_repo(rr, optional_path_posix=[], artifact_path=ap)
    abs_out = str((rr / ap).resolve())
    prov = {"jobs": [{"status": "ok", "tag": "provjob", "output": abs_out}]}
    prov_path = rr / "results" / "fake_provenance.json"
    prov_path.write_text(json.dumps(prov), encoding="utf-8")
    inv_path = rr / "config" / "pipeline_inventory.yaml"
    data = yaml.safe_load(inv_path.read_text(encoding="utf-8"))
    data["pipeline_results_index"]["provenance_paths"] = [
        {"path": "results/fake_provenance.json", "module": 3}
    ]
    inv_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(_wpri, "repo_root", lambda: rr)
    assert _wpri.main() == 0
    out = json.loads((rr / "results" / "pipeline_results_index.json").read_text(encoding="utf-8"))
    stub = [e for e in out["entries"] if e["path_posix"] == ap]
    assert len(stub) == 1
    assert len(stub[0]["sources"]) == 2
    assert "provjob:output" in stub[0]["tags"]


def test_strict_fails_when_required_path_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rr = tmp_path / "repo"
    ap = "results/stub.txt"
    _write_minimal_repo(rr, optional_path_posix=[], artifact_path=ap, create_stub=False)
    monkeypatch.setattr(_wpri, "repo_root", lambda: rr)
    assert _wpri.main(["--strict"]) == 1
    out = json.loads((rr / "results" / "pipeline_results_index.json").read_text(encoding="utf-8"))
    assert out["summary"]["strict_mode"] is True
    assert out["summary"]["strict_ok"] is False
    assert out["summary"]["strict_triggers"] == ["cli"]
    assert out["summary"]["n_missing_required"] == 1
    assert ap in out["summary"]["missing_required_path_posix"]
    assert out["summary"]["missing_optional_path_posix"] == []


def test_strict_fails_on_optional_path_posix_unmatched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rr = tmp_path / "repo"
    ap = "results/stub.txt"
    _write_minimal_repo(
        rr,
        optional_path_posix=[ap, "results/typo_not_in_index.txt"],
        artifact_path=ap,
    )
    monkeypatch.setattr(_wpri, "repo_root", lambda: rr)
    assert _wpri.main(["--strict"]) == 1
    out = json.loads((rr / "results" / "pipeline_results_index.json").read_text(encoding="utf-8"))
    assert out["summary"]["strict_ok"] is False
    assert out["summary"]["strict_triggers"] == ["cli"]


def test_strict_passes_when_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rr = tmp_path / "repo"
    ap = "results/stub.txt"
    _write_minimal_repo(rr, optional_path_posix=[ap], artifact_path=ap)
    monkeypatch.setattr(_wpri, "repo_root", lambda: rr)
    assert _wpri.main(["--strict"]) == 0
    out = json.loads((rr / "results" / "pipeline_results_index.json").read_text(encoding="utf-8"))
    assert out["summary"]["strict_ok"] is True
    assert out["summary"]["strict_triggers"] == ["cli"]


def test_strict_cli_and_env_both_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rr = tmp_path / "repo"
    ap = "results/stub.txt"
    _write_minimal_repo(rr, optional_path_posix=[ap], artifact_path=ap)
    monkeypatch.setattr(_wpri, "repo_root", lambda: rr)
    monkeypatch.setenv("GLIOMA_TARGET_PIPELINE_INDEX_STRICT", "on")
    assert _wpri.main(["--strict"]) == 0
    out = json.loads((rr / "results" / "pipeline_results_index.json").read_text(encoding="utf-8"))
    assert out["summary"]["strict_triggers"] == ["cli", "env"]


def test_env_strict_passes_when_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rr = tmp_path / "repo"
    ap = "results/stub.txt"
    _write_minimal_repo(rr, optional_path_posix=[ap], artifact_path=ap)
    monkeypatch.setattr(_wpri, "repo_root", lambda: rr)
    monkeypatch.setenv("GLIOMA_TARGET_PIPELINE_INDEX_STRICT", "1")
    assert _wpri.main([]) == 0
    out = json.loads((rr / "results" / "pipeline_results_index.json").read_text(encoding="utf-8"))
    assert out["summary"]["strict_mode"] is True
    assert out["summary"]["strict_ok"] is True
    assert out["summary"]["strict_triggers"] == ["env"]


def test_env_strict_fails_when_required_path_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rr = tmp_path / "repo"
    ap = "results/stub.txt"
    _write_minimal_repo(rr, optional_path_posix=[], artifact_path=ap, create_stub=False)
    monkeypatch.setattr(_wpri, "repo_root", lambda: rr)
    monkeypatch.setenv("GLIOMA_TARGET_PIPELINE_INDEX_STRICT", "yes")
    assert _wpri.main([]) == 1


def test_env_strict_not_enabled_for_false_or_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing required path only fails strict when env is a truthy token."""
    rr = tmp_path / "repo"
    ap = "results/stub.txt"
    _write_minimal_repo(rr, optional_path_posix=[], artifact_path=ap, create_stub=False)
    monkeypatch.setattr(_wpri, "repo_root", lambda: rr)
    for val in ("false", "0", "no", "off", "maybe"):
        monkeypatch.setenv("GLIOMA_TARGET_PIPELINE_INDEX_STRICT", val)
        assert _wpri.main([]) == 0
        out = json.loads((rr / "results" / "pipeline_results_index.json").read_text(encoding="utf-8"))
        assert "strict_mode" not in out["summary"]


def test_optional_path_posix_unmatched_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    rr = tmp_path / "repo"
    ap = "results/stub.txt"
    _write_minimal_repo(rr, optional_path_posix=[ap, "results/does_not_exist_in_index.txt"], artifact_path=ap)
    monkeypatch.setattr(_wpri, "repo_root", lambda: rr)
    assert _wpri.main() == 0
    err = capsys.readouterr().err
    assert "does_not_exist_in_index" in err
    out = json.loads((rr / "results" / "pipeline_results_index.json").read_text(encoding="utf-8"))
    assert out["summary"]["optional_path_posix_unmatched"] == ["results/does_not_exist_in_index.txt"]
    ent = next(e for e in out["entries"] if e["path_posix"] == ap)
    assert ent.get("optional") is True
