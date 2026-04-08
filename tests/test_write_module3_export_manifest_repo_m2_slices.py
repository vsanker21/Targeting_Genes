"""Regression: M3 export manifest lists m3_repo_m2_* path + stub artifacts."""

from __future__ import annotations

from pathlib import Path

_TEXT = (Path(__file__).resolve().parents[1] / "scripts" / "write_module3_export_manifest.py").read_text(
    encoding="utf-8"
)


def test_manifest_includes_repo_m2_cptac_methylation() -> None:
    assert "m3_repo_m2_cptac_methylation_paths_status.json" in _TEXT
    assert "m3_sc.repo_m2_cptac_methylation_paths_status" in _TEXT
    assert "m3_repo_m2_cptac_methylation_integration_stub.json" in _TEXT


def test_manifest_includes_repo_m2_1_star_pairing() -> None:
    assert "m3_repo_m2_1_star_pairing_paths_status.json" in _TEXT
    assert "m3_sc.repo_m2_1_star_pairing_paths_status" in _TEXT
    assert "m3_repo_m2_1_star_pairing_integration_stub.json" in _TEXT


def test_manifest_includes_repo_m2_1_recount3_mirror() -> None:
    assert "m3_repo_m2_1_recount3_mirror_paths_status.json" in _TEXT
    assert "m3_sc.repo_m2_1_recount3_mirror_paths_status" in _TEXT
    assert "m3_repo_m2_1_recount3_mirror_integration_stub.json" in _TEXT


def test_manifest_includes_repo_m2_1_toil_xena_hub() -> None:
    assert "m3_repo_m2_1_toil_xena_hub_paths_status.json" in _TEXT
    assert "m3_sc.repo_m2_1_toil_xena_hub_paths_status" in _TEXT
    assert "m3_repo_m2_1_toil_xena_hub_integration_stub.json" in _TEXT


def test_manifest_includes_repo_m2_movics() -> None:
    assert "m3_repo_m2_movics_paths_status.json" in _TEXT
    assert "m3_sc.repo_m2_movics_paths_status" in _TEXT
    assert "m3_repo_m2_movics_integration_stub.json" in _TEXT


def test_manifest_includes_repo_m2_3_immune_tme_mirror() -> None:
    assert "m3_repo_m2_3_immune_tme_mirror_paths_status.json" in _TEXT
    assert "m3_sc.repo_m2_3_immune_tme_mirror_paths_status" in _TEXT
    assert "m3_repo_m2_3_immune_tme_mirror_integration_stub.json" in _TEXT


def test_manifest_includes_repo_m2_2_variant_annotation() -> None:
    assert "m3_repo_m2_2_variant_annotation_paths_status.json" in _TEXT
    assert "m3_sc.repo_m2_2_variant_annotation_paths_status" in _TEXT
    assert "m3_repo_m2_2_variant_annotation_integration_stub.json" in _TEXT


def test_manifest_includes_repo_m2_2_depmap_mirror() -> None:
    assert "m3_repo_m2_2_depmap_mirror_paths_status.json" in _TEXT
    assert "m3_sc.repo_m2_2_depmap_mirror_paths_status" in _TEXT
    assert "m3_repo_m2_2_depmap_mirror_integration_stub.json" in _TEXT


def test_manifest_includes_repo_m2_2_maf_mutsig_mirror() -> None:
    assert "m3_repo_m2_2_maf_mutsig_mirror_paths_status.json" in _TEXT
    assert "m3_sc.repo_m2_2_maf_mutsig_mirror_paths_status" in _TEXT
    assert "m3_repo_m2_2_maf_mutsig_mirror_integration_stub.json" in _TEXT


def test_manifest_includes_repo_m2_2_outline_driver_mirror() -> None:
    assert "m3_repo_m2_2_outline_driver_mirror_paths_status.json" in _TEXT
    assert "m3_sc.repo_m2_2_outline_driver_mirror_paths_status" in _TEXT
    assert "m3_repo_m2_2_outline_driver_mirror_integration_stub.json" in _TEXT


def test_manifest_includes_repo_m2_maf_annotation() -> None:
    assert "m3_repo_m2_maf_annotation_paths_status.json" in _TEXT
    assert "m3_sc.repo_m2_maf_annotation_paths_status" in _TEXT
    assert "m3_repo_m2_maf_annotation_integration_stub.json" in _TEXT
