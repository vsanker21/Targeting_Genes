from __future__ import annotations

import gzip
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
_SCR = _ROOT / "scripts"
if str(_SCR) not in sys.path:
    sys.path.insert(0, str(_SCR))

from holdout_geo_expression import load_geo_series_matrix


def _write_minimal_matrix_gz(path: Path) -> None:
    lines = [
        "!Series_matrix_table_begin\n",
        '"ID_REF"\t"GSM1"\t"GSM2"\n',
        '"p1"\t1.0\t4.0\n',
        '"p2"\t2.0\t5.0\n',
        "!Series_matrix_table_end\n",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.writelines(lines)


def test_load_geo_series_matrix_subset(tmp_path: Path) -> None:
    gz = tmp_path / "mini_series_matrix.txt.gz"
    _write_minimal_matrix_gz(gz)
    idx, mat, cols = load_geo_series_matrix(gz, ["GSM2", "GSM1"])
    assert list(cols) == ["GSM2", "GSM1"]
    assert list(idx) == ["p1", "p2"]
    assert mat.shape == (2, 2)
    np.testing.assert_allclose(mat[0], [4.0, 1.0])
