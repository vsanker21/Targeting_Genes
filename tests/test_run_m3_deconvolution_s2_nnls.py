"""M3 S2 NNLS: requires real TSVs under GLIOMA_TARGET_DATA_ROOT (paths from repo config)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "run_m3_deconvolution_s2_nnls.py"


def test_m3_deconvolution_s2_nnls_runs_on_minimal_wide_tsvs(tmp_path: Path) -> None:
    dr = tmp_path / "data_root"
    sub = dr / "m3_deconvolution_nnls"
    sub.mkdir(parents=True)
    (sub / "reference_profile_wide.tsv").write_text(
        "gene_id\tA\tB\nG1\t1.0\t0.5\nG2\t0.5\t1.0\n",
        encoding="utf-8",
    )
    (sub / "spatial_counts_wide.tsv").write_text(
        "spot_id\tG1\tG2\ns1\t1.0\t1.0\n",
        encoding="utf-8",
    )

    r = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        cwd=str(_ROOT),
        env={**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(dr)},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr

    out_dir = _ROOT / "results" / "module3" / "m3_deconvolution_s2"
    prov = json.loads((out_dir / "deconvolution_s2_provenance.json").read_text(encoding="utf-8"))
    assert prov.get("status") == "ok"
    assert prov.get("n_spots") == 1
    frac_txt = (out_dir / "spot_celltype_fractions.tsv").read_text(encoding="utf-8")
    assert "A" in frac_txt and "B" in frac_txt


def test_m3_deconvolution_s2_nnls_fails_without_data_root_files(tmp_path: Path) -> None:
    dr = tmp_path / "empty"
    dr.mkdir()
    r = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        cwd=str(_ROOT),
        env={**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(dr)},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode != 0
