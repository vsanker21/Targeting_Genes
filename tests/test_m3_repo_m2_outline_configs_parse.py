"""Regression: m3_repo_m2_* outline YAML configs parse as YAML."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[1]

_M3_REPO_M2_OUTLINE_CONFIGS = [
    "config/m3_repo_m2_cptac_methylation_outline_inputs.yaml",
    "config/m3_repo_m2_1_star_pairing_outline_inputs.yaml",
    "config/m3_repo_m2_1_recount3_mirror_outline_inputs.yaml",
    "config/m3_repo_m2_1_toil_xena_hub_outline_inputs.yaml",
    "config/m3_repo_m2_movics_outline_inputs.yaml",
    "config/m3_repo_m2_3_immune_tme_mirror_outline_inputs.yaml",
    "config/m3_repo_m2_2_variant_annotation_outline_inputs.yaml",
    "config/m3_repo_m2_2_depmap_mirror_outline_inputs.yaml",
    "config/m3_repo_m2_2_maf_mutsig_mirror_outline_inputs.yaml",
    "config/m3_repo_m2_2_outline_driver_mirror_outline_inputs.yaml",
]


@pytest.mark.parametrize("rel", _M3_REPO_M2_OUTLINE_CONFIGS)
def test_m3_repo_m2_outline_yaml_parses(rel: str) -> None:
    path = _ROOT / rel
    assert path.is_file(), f"missing {rel}"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), rel
    assert data, rel
