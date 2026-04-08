"""Smoke: module3_deconvolution_integration_stub main() writes JSON + flag in a temp repo layout."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_integration_stub_main_writes_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rr = tmp_path / "repo"
    (rr / "config").mkdir(parents=True)
    shutil.copyfile(
        _ROOT / "config" / "m3_deconvolution_outline_inputs.yaml",
        rr / "config" / "m3_deconvolution_outline_inputs.yaml",
    )
    out_mod3 = rr / "results" / "module3"
    out_mod3.mkdir(parents=True)
    (out_mod3 / "m3_deconvolution_paths_status.json").write_text(
        '{"groups": []}',
        encoding="utf-8",
    )

    import module3_deconvolution_integration_stub as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    assert m.main() == 0

    js = rr / "results" / "module3" / "m3_deconvolution_integration_stub.json"
    fl = rr / "results" / "module3" / "m3_deconvolution_integration_stub.flag"
    assert js.is_file()
    assert fl.is_file()
    doc = json.loads(js.read_text(encoding="utf-8"))
    assert "checklist" in doc
    assert "recommended_next_steps" in doc
    assert doc.get("blockers") == []


def test_integration_stub_main_includes_rctd_followup_when_provenance_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rr = tmp_path / "repo"
    (rr / "config").mkdir(parents=True)
    shutil.copyfile(
        _ROOT / "config" / "m3_deconvolution_outline_inputs.yaml",
        rr / "config" / "m3_deconvolution_outline_inputs.yaml",
    )
    out_mod3 = rr / "results" / "module3"
    out_mod3.mkdir(parents=True)
    (out_mod3 / "m3_deconvolution_paths_status.json").write_text(
        '{"groups": []}',
        encoding="utf-8",
    )
    (out_mod3 / "m3_deconvolution_rctd").mkdir(parents=True)
    (out_mod3 / "m3_deconvolution_rctd" / "rctd_run_provenance.json").write_text(
        json.dumps(
            {
                "status": "spacexr_missing",
                "ref_load_ok": True,
                "spatial_load_ok": True,
                "spacexr_available": False,
            }
        ),
        encoding="utf-8",
    )

    import module3_deconvolution_integration_stub as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    assert m.main() == 0

    doc = json.loads(
        (rr / "results" / "module3" / "m3_deconvolution_integration_stub.json").read_text(encoding="utf-8")
    )
    steps = doc.get("recommended_next_steps") or []
    assert any("spacexr is not installed" in str(s) for s in steps)
    assert doc.get("checklist", {}).get("rctd_run_status") == "spacexr_missing"


def test_integration_stub_main_includes_cell2location_training_failed_followup_and_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rr = tmp_path / "repo"
    (rr / "config").mkdir(parents=True)
    shutil.copyfile(
        _ROOT / "config" / "m3_deconvolution_outline_inputs.yaml",
        rr / "config" / "m3_deconvolution_outline_inputs.yaml",
    )
    out_mod3 = rr / "results" / "module3"
    out_mod3.mkdir(parents=True)
    (out_mod3 / "m3_deconvolution_paths_status.json").write_text(
        '{"groups": []}',
        encoding="utf-8",
    )
    (out_mod3 / "m3_deconvolution_cell2location").mkdir(parents=True)
    c2l_doc = {
        "status": "training_failed",
        "training_error": "ValueError: boom",
        "gene_intersection_diagnostic": {
            "n_shared_genes": 0,
            "min_shared_genes_required": 50,
            "n_spatial_var": 100,
            "n_signature_rows": 80,
        },
    }
    (out_mod3 / "m3_deconvolution_cell2location" / "cell2location_run_provenance.json").write_text(
        json.dumps(c2l_doc),
        encoding="utf-8",
    )

    import module3_deconvolution_integration_stub as m

    monkeypatch.setattr(m, "repo_root", lambda: rr)
    assert m.main() == 0

    doc = json.loads(
        (rr / "results" / "module3" / "m3_deconvolution_integration_stub.json").read_text(encoding="utf-8")
    )
    ch = doc.get("checklist") or {}
    assert ch.get("in_repo_cell2location_or_rctd") is True
    assert ch.get("cell2location_run_status") == "training_failed"
    assert ch.get("cell2location_has_gene_intersection_diagnostic") is True
    assert ch.get("cell2location_has_signature_extract_diagnostic") is False

    steps = doc.get("recommended_next_steps") or []
    assert any("training or import failed" in str(s) for s in steps)
    assert any("ValueError: boom" in str(s) for s in steps)
    assert any("gene_intersection_diagnostic" in str(s) for s in steps)
