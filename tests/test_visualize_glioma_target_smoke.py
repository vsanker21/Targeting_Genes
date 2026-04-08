"""Smoke test for scripts/visualize_glioma_target_results.py (requires matplotlib)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "visualize_glioma_target_results.py"

pytest.importorskip("matplotlib")


def _minimal_tier1_rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "hgnc_symbol": ["G1", "G2", "G3"],
            "gene_id": ["ENSG1.1", "ENSG2.1", "ENSG3.1"],
            "gts_evidence_tier": [1, 2, 2],
            "gts_stub_sort_metric": [10.0, 9.0, 8.0],
            "signed_neglog10_p": [20.0, 15.0, 10.0],
            "padj_bh": [0.01, 0.02, 0.03],
            "delta_log2_expression": [4.0, 3.0, 2.0],
            "depmap_crispr_median_gbm": [-1.2, -0.8, float("nan")],
            "outline_m21_high_confidence_screen": [True, True, False],
            "outline_m22_known_gbm_driver": [False, False, False],
            "gts_sub_E_norm": [0.9, 0.7, 0.5],
            "gts_sub_M_norm": [0.8, 0.6, 0.4],
            "gts_sub_D_norm": [0.5, 0.5, 0.5],
            "gts_sub_N_norm": [0.9, 0.5, 0.2],
            "glioma_target_score": [0.85, 0.65, 0.45],
            "glioma_target_tier": [1, 2, 3],
        }
    )


def test_visualize_cli_writes_png_panels(tmp_path: Path) -> None:
    t1 = tmp_path / "tier1.tsv"
    full = tmp_path / "full.tsv"
    _minimal_tier1_rows().to_csv(t1, sep="\t", index=False)
    _minimal_tier1_rows().to_csv(full, sep="\t", index=False)
    out_png = tmp_path / "out.png"
    out_pdf = tmp_path / "out.pdf"
    panel_dir = tmp_path / "panels"
    r = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--tier1-tsv",
            str(t1),
            "--full-tsv",
            str(full),
            "--output",
            str(out_png),
            "--output-pdf",
            str(out_pdf),
            "--panel-dir",
            str(panel_dir),
            "--dpi",
            "72",
            "--fig-width",
            "8",
            "--fig-height",
            "5",
            "--top-bars",
            "3",
            "--top-heat",
            "3",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert out_png.is_file() and out_png.stat().st_size > 500
    assert out_pdf.is_file() and out_pdf.stat().st_size > 500
    pngs = sorted(panel_dir.glob("*.png"))
    assert len(pngs) == 6
