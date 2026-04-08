"""Smoke: M3 outline path-status scripts write JSON + flag under a temp repo + data_root."""

from __future__ import annotations

import importlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[1]

# (module, config basename, output json basename, payload list key: groups or checks)
_CASES: tuple[tuple[str, str, str, str], ...] = (
    (
        "module3_deconvolution_paths_status",
        "m3_deconvolution_outline_inputs.yaml",
        "m3_deconvolution_paths_status.json",
        "groups",
    ),
    (
        "m3_cellranger_output_paths_status",
        "m3_cellranger_output_outline_inputs.yaml",
        "m3_cellranger_output_paths_status.json",
        "groups",
    ),
    (
        "m3_repo_scrna_spatial_paths_status",
        "m3_repo_scrna_spatial_outline_inputs.yaml",
        "m3_repo_scrna_spatial_paths_status.json",
        "groups",
    ),
    (
        "m3_repo_deconvolution_paths_status",
        "m3_repo_deconvolution_outline_inputs.yaml",
        "m3_repo_deconvolution_paths_status.json",
        "groups",
    ),
    (
        "module3_sc_workflow_paths_status",
        "module3_inputs.yaml",
        "module3_sc_workflow_paths_status.json",
        "checks",
    ),
    (
        "m3_repo_sc_workflow_paths_status",
        "m3_repo_sc_workflow_outline_inputs.yaml",
        "m3_repo_sc_workflow_paths_status.json",
        "groups",
    ),
    (
        "m3_repo_cellranger_output_paths_status",
        "m3_repo_cellranger_output_outline_inputs.yaml",
        "m3_repo_cellranger_output_paths_status.json",
        "groups",
    ),
    (
        "m3_dryad_sra_paths_status",
        "m3_dryad_sra_outline_inputs.yaml",
        "m3_dryad_sra_paths_status.json",
        "groups",
    ),
    (
        "m3_repo_public_inputs_paths_status",
        "m3_repo_public_inputs_outline_inputs.yaml",
        "m3_repo_public_inputs_paths_status.json",
        "groups",
    ),
)


@pytest.mark.parametrize("mod_name,cfg_file,out_json,list_key", _CASES)
def test_paths_status_main_writes_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mod_name: str,
    cfg_file: str,
    out_json: str,
    list_key: str,
) -> None:
    rr = tmp_path / "repo"
    dr = tmp_path / "data"
    dr.mkdir()
    (rr / "config").mkdir(parents=True)
    shutil.copyfile(_ROOT / "config" / cfg_file, rr / "config" / cfg_file)

    m: Any = importlib.import_module(mod_name)
    monkeypatch.setattr(m, "repo_root", lambda: rr)
    monkeypatch.setattr(m, "data_root", lambda: dr)

    assert m.main() == 0

    out_p = rr / "results" / "module3" / out_json
    flag_n = out_json.replace(".json", ".flag")
    flag_p = rr / "results" / "module3" / flag_n
    assert out_p.is_file()
    assert flag_p.is_file()
    doc = json.loads(out_p.read_text(encoding="utf-8"))
    assert doc.get("outline_module") == 3
    seq = doc.get(list_key)
    assert isinstance(seq, list)
    assert len(seq) >= 1
