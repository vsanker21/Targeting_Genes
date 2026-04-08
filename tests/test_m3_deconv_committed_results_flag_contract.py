"""RCTD / Cell2location flag vs provenance contract when artifacts exist under ``results/``.

``results/`` is gitignored by default; these tests skip when paths are absent. They still run when
developers keep local ``results/`` trees or force-add artifacts, and catch orphan success flags.

Set ``M3_RESULTS_CONTRACT_REPO`` to a directory that contains a ``results/module3/...`` tree (for example
``tests/fixtures/m3_results_contract_repo``) to exercise the contract without a full pipeline run; see
``tests/test_m3_results_contract_fixture_repo.py``.

Run only these checks: ``pytest -m results_contract`` (see ``pytest.ini``).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Final

import pytest

pytestmark = pytest.mark.results_contract


def _repo_root() -> Path:
    env = os.environ.get("M3_RESULTS_CONTRACT_REPO", "").strip()
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]

# (subdir under results/module3/, provenance filename, flag filename, snakemake rule hint)
_SPECS: Final[dict[str, tuple[str, str, str, str]]] = {
    "rctd": (
        "m3_deconvolution_rctd",
        "rctd_run_provenance.json",
        "rctd_run.flag",
        "m3_deconvolution_rctd_run",
    ),
    "cell2location": (
        "m3_deconvolution_cell2location",
        "cell2location_run_provenance.json",
        "cell2location_run.flag",
        "m3_deconvolution_cell2location_run",
    ),
}


def _prov_flag_paths(method: str) -> tuple[Path, Path]:
    sub, prov_n, flag_n, _rule = _SPECS[method]
    d = _repo_root() / "results" / "module3" / sub
    return d / prov_n, d / flag_n


@pytest.mark.parametrize("method", sorted(_SPECS.keys()))
def test_orphan_flag_without_provenance(method: str) -> None:
    prov_p, flag_p = _prov_flag_paths(method)
    if not flag_p.is_file():
        pytest.skip(f"no {flag_p.name} on disk")
    if not prov_p.is_file():
        _, _, _, rerun = _SPECS[method]
        pytest.fail(
            f"{flag_p.name} exists without {prov_p.name}; remove the orphan flag "
            f"(or re-run {rerun})."
        )


def test_rctd_committed_provenance_and_flag_consistency() -> None:
    prov_p, flag_p = _prov_flag_paths("rctd")
    if not prov_p.is_file():
        pytest.skip("no committed rctd_run_provenance.json")
    doc = json.loads(prov_p.read_text(encoding="utf-8"))
    st = str(doc.get("status", "")).strip().lower()
    if st == "ok":
        assert flag_p.is_file(), "rctd status ok requires rctd_run.flag for Snakemake contract"
    elif st in ("rds_load_failed", "spacexr_missing", "create_failed"):
        assert not flag_p.is_file(), (
            f"rctd status {st!r} must not leave rctd_run.flag (remove stale flag or re-run wrapper)"
        )
    else:
        pytest.fail(
            f"unexpected rctd provenance status {st!r}; "
            "expected ok, rds_load_failed, spacexr_missing, or create_failed"
        )


def test_cell2location_committed_provenance_and_flag_consistency() -> None:
    prov_p, flag_p = _prov_flag_paths("cell2location")
    if not prov_p.is_file():
        pytest.skip("no committed cell2location_run_provenance.json")
    doc = json.loads(prov_p.read_text(encoding="utf-8"))
    st = str(doc.get("status", "")).strip().lower()
    if st in ("inputs_ok", "trained_ok"):
        assert flag_p.is_file(), "cell2location success status requires cell2location_run.flag"
    elif st == "training_failed":
        assert not flag_p.is_file(), (
            "training_failed must not leave cell2location_run.flag (remove stale flag or re-run orchestrator)"
        )
    else:
        pytest.fail(
            f"unexpected cell2location provenance status {st!r}; "
            "expected inputs_ok, trained_ok, or training_failed"
        )
