"""Smoke tests for scripts/export_glioma_target_results_docx.py (requires python-docx)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "export_glioma_target_results_docx.py"

pytest.importorskip("docx")


def _minimal_tier1_tsv(path: Path) -> None:
    df = pd.DataFrame(
        {
            "hgnc_symbol": ["G1", "G2"],
            "gene_id": ["ENSG1.1", "ENSG2.1"],
            "glioma_target_score": [0.9, 0.5],
            "glioma_target_tier": [1, 2],
            "gts_sub_E_norm": [0.9, 0.5],
            "gts_sub_M_norm": [0.8, 0.4],
            "gts_sub_D_norm": [0.5, 0.5],
            "gts_sub_N_norm": [0.7, 0.3],
            "delta_log2_expression": [3.0, 2.0],
            "depmap_crispr_median_gbm": [-1.0, float("nan")],
            "gts_evidence_tier": [1, 2],
            "outline_m22_known_gbm_driver": [False, True],
        }
    )
    df.to_csv(path, sep="\t", index=False)


def _run_docx(*, tier1: Path, out_docx: Path, pipeline_index: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--tier1-tsv",
            str(tier1),
            "--pipeline-index",
            str(pipeline_index),
            "--output",
            str(out_docx),
            "--top-n",
            "10",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_export_docx_cli_without_index_json(tmp_path: Path) -> None:
    tier1 = tmp_path / "tier1.tsv"
    out_docx = tmp_path / "report.docx"
    missing_idx = tmp_path / "no_such_index.json"
    _minimal_tier1_tsv(tier1)
    r = _run_docx(tier1=tier1, out_docx=out_docx, pipeline_index=missing_idx)
    assert r.returncode == 0, r.stderr + r.stdout
    assert out_docx.is_file() and out_docx.stat().st_size > 2_000


def test_export_docx_cli_with_index_summary(tmp_path: Path) -> None:
    tier1 = tmp_path / "tier1.tsv"
    out_docx = tmp_path / "report.docx"
    idx = tmp_path / "pipeline_results_index.json"
    _minimal_tier1_tsv(tier1)
    idx.write_text(
        json.dumps(
            {
                "summary": {
                    "n_paths_unique": 12,
                    "n_existing": 10,
                    "n_missing_required": 0,
                    "primary_deliverables": [
                        {"id": "test_deliverable", "path_posix": "results/x.tsv", "tier_filter": "optional"}
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    r = _run_docx(tier1=tier1, out_docx=out_docx, pipeline_index=idx)
    assert r.returncode == 0, r.stderr + r.stdout
    assert out_docx.is_file() and out_docx.stat().st_size > 2_500
