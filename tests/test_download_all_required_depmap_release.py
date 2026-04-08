"""DepMap portal release selection (must not pick wrong YYQq family from shared quarter tie)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_DAR_PATH = _ROOT / "scripts" / "download_all_required.py"


def _load_download_all_required():
    spec = importlib.util.spec_from_file_location("download_all_required", _DAR_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_resolve_depmap_release_only_considers_releases_with_all_files() -> None:
    dar = _load_download_all_required()
    rows = [
        {"release": "Harmonized Public Proteomics 26Q1", "filename": "harmonized_MS_CCLE_Gygi.csv"},
        {"release": "Harmonized Public Proteomics 26Q1", "filename": "uniprot_hugo_entrez_id_mapping.csv"},
        {"release": "DepMap Public 26Q1", "filename": "Model.csv"},
        {"release": "DepMap Public 26Q1", "filename": "CRISPRGeneEffect.csv"},
    ]
    want = ["Model.csv", "CRISPRGeneEffect.csv"]
    assert dar.resolve_depmap_release(rows, None, want) == "DepMap Public 26Q1"


def test_resolve_depmap_release_prefers_depmap_public_on_quarter_tie() -> None:
    dar = _load_download_all_required()
    rows = []
    for fn in ("Model.csv", "CRISPRGeneEffect.csv"):
        rows.append({"release": "DepMap Public 26Q1", "filename": fn})
        rows.append({"release": "Other Bundle 26Q1", "filename": fn})
    want = ["Model.csv", "CRISPRGeneEffect.csv"]
    assert dar.resolve_depmap_release(rows, None, want) == "DepMap Public 26Q1"


def test_resolve_depmap_release_prefer_validates_files() -> None:
    dar = _load_download_all_required()
    rows = [
        {"release": "DepMap Public 25Q3", "filename": "Model.csv"},
    ]
    with pytest.raises(RuntimeError, match="missing files"):
        dar.resolve_depmap_release(rows, "DepMap Public 25Q3", ["Model.csv", "CRISPRGeneEffect.csv"])
