"""M3 export manifest edges to M1/M2/M4/M5/M6/M7 and M4-M7 manifest rules."""

from __future__ import annotations

from pathlib import Path

from snakefile_rule_block import rule_block
from snakefile_text_cache import snakefile_text

_ROOT = Path(__file__).resolve().parents[1]
_SNAKE = snakefile_text()


def test_m2_maf_annotation_integration_stub_rule_exists() -> None:
    assert "rule m2_maf_annotation_integration_stub:" in _SNAKE


def test_m2_2_variant_annotation_rules_exist() -> None:
    assert "rule m2_2_variant_annotation_paths_status:" in _SNAKE
    assert "rule m2_2_variant_annotation_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_maf_annotation_stub() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "maf_annotation_integration_stub.json" in blk
    assert "maf_annotation_integration_stub.flag" in blk


def test_m3_export_manifest_depends_on_m2_2_variant_annotation_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m2_2_variant_annotation_paths_status.json" in blk
    assert "m2_2_variant_annotation_integration_stub.json" in blk


def test_m2_2_depmap_mirror_rules_exist() -> None:
    assert "rule m2_2_depmap_mirror_paths_status:" in _SNAKE
    assert "rule m2_2_depmap_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_m2_2_depmap_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m2_2_depmap_mirror_paths_status.json" in blk
    assert "m2_2_depmap_mirror_integration_stub.json" in blk


def test_m2_2_maf_mutsig_mirror_rules_exist() -> None:
    assert "rule m2_2_maf_mutsig_mirror_paths_status:" in _SNAKE
    assert "rule m2_2_maf_mutsig_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_m2_2_maf_mutsig_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m2_2_maf_mutsig_mirror_paths_status.json" in blk
    assert "m2_2_maf_mutsig_mirror_integration_stub.json" in blk


def test_m2_2_outline_driver_mirror_rules_exist() -> None:
    assert "rule m2_2_outline_driver_mirror_paths_status:" in _SNAKE
    assert "rule m2_2_outline_driver_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_m2_2_outline_driver_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m2_2_outline_driver_mirror_paths_status.json" in blk
    assert "m2_2_outline_driver_mirror_integration_stub.json" in blk


def test_m2_tcga_maf_join_dea_emits_join_provenance() -> None:
    blk = rule_block(_SNAKE, "m2_tcga_maf_join_dea")
    assert "tcga_maf_join_provenance.json" in blk


def test_m6_structure_admet_integration_stub_rule_exists() -> None:
    assert "rule m6_structure_admet_integration_stub:" in _SNAKE


def test_m6_export_manifest_depends_on_admet_stub() -> None:
    blk = rule_block(_SNAKE, "m6_export_manifest")
    assert "structure_admet_integration_stub.json" in blk
    assert "structure_admet_integration_stub.flag" in blk


def test_m6_export_manifest_depends_on_structure_bridge_data_tables() -> None:
    blk = rule_block(_SNAKE, "m6_export_manifest")
    assert 'm6br_welch="results/module6/structure_druggability_bridge_welch.tsv"' in blk
    assert (
        'm6br_sw_cl="results/module6/structure_druggability_bridge_stratified/welch_integrated/'
        'dea_welch_subtype_Classical_structure_bridge.tsv"' in blk
    )


def test_m7_gts_validation_integration_stub_rule_exists() -> None:
    assert "rule m7_gts_validation_integration_stub:" in _SNAKE


def test_m7_export_glioma_results_docx_rule_exists() -> None:
    assert "rule m7_export_glioma_results_docx:" in _SNAKE
    blk = rule_block(_SNAKE, "m7_export_glioma_results_docx")
    assert "export_glioma_target_results_docx.py" in blk
    assert "glioma_target_results_report.docx" in blk
    assert "glioma_target_tier1_welch.tsv" in blk


def test_m7_glioma_target_deliverables_rule_exists() -> None:
    assert "rule m7_glioma_target_deliverables:" in _SNAKE
    blk = rule_block(_SNAKE, "m7_glioma_target_deliverables")
    assert "glioma_target_visualization.flag" in blk
    assert "glioma_target_results_report.docx" in blk
    assert "glioma_target_deliverables.flag" in blk


def test_m7_export_manifest_depends_on_gts_validation_stub() -> None:
    blk = rule_block(_SNAKE, "m7_export_manifest")
    assert "gts_validation_integration_stub.json" in blk
    assert "gts_validation_integration_stub.flag" in blk


def test_m2_cptac_methylation_rules_exist() -> None:
    assert "rule m2_cptac_methylation_paths_status:" in _SNAKE
    assert "rule m2_cptac_methylation_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_cptac_methylation_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m2_cptac_methylation_paths_status.json" in blk
    assert "m2_cptac_methylation_integration_stub.json" in blk


def test_m2_1_star_pairing_rules_exist() -> None:
    assert "rule m2_1_star_pairing_paths_status:" in _SNAKE
    assert "rule m2_1_star_pairing_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_m2_1_star_pairing_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m2_1_star_pairing_paths_status.json" in blk
    assert "m2_1_star_pairing_integration_stub.json" in blk


def test_m2_1_recount3_mirror_rules_exist() -> None:
    assert "rule m2_1_recount3_mirror_paths_status:" in _SNAKE
    assert "rule m2_1_recount3_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_m2_1_recount3_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m2_1_recount3_mirror_paths_status.json" in blk
    assert "m2_1_recount3_mirror_integration_stub.json" in blk


def test_m2_1_toil_xena_hub_rules_exist() -> None:
    assert "rule m2_1_toil_xena_hub_paths_status:" in _SNAKE
    assert "rule m2_1_toil_xena_hub_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_m2_1_toil_xena_hub_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m2_1_toil_xena_hub_paths_status.json" in blk
    assert "m2_1_toil_xena_hub_integration_stub.json" in blk


def test_m2_movics_rules_exist() -> None:
    assert "rule m2_movics_paths_status:" in _SNAKE
    assert "rule m2_movics_integration_stub:" in _SNAKE
    assert "rule m2_movics_intnmf_tcga_gbm:" in _SNAKE
    assert "rule m2_movics_intnmf_depmap_mae:" in _SNAKE
    assert "rule m2_movics_depmap_intnmf_characterize:" in _SNAKE


def test_m3_export_manifest_depends_on_movics_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m2_movics_paths_status.json" in blk
    assert "m2_movics_integration_stub.json" in blk


def test_m2_3_immune_tme_mirror_rules_exist() -> None:
    assert "rule m2_3_immune_tme_mirror_paths_status:" in _SNAKE
    assert "rule m2_3_immune_tme_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_m2_3_immune_tme_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m2_3_immune_tme_mirror_paths_status.json" in blk
    assert "m2_3_immune_tme_mirror_integration_stub.json" in blk


def test_m1_outline_rules_exist() -> None:
    assert "rule m1_outline_paths_status:" in _SNAKE
    assert "rule m1_outline_integration_stub:" in _SNAKE


def test_m1_harmony_batch_rules_exist() -> None:
    assert "rule m1_harmony_batch_paths_status:" in _SNAKE
    assert "rule m1_harmony_batch_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_m1_outline_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m1_outline_paths_status.json" in blk
    assert "m1_outline_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_m1_harmony_batch_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m1_harmony_batch_paths_status.json" in blk
    assert "m1_harmony_batch_integration_stub.json" in blk


def test_m1_reference_gdc_rules_exist() -> None:
    assert "rule m1_reference_gdc_paths_status:" in _SNAKE
    assert "rule m1_reference_gdc_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_m1_reference_gdc_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m1_reference_gdc_paths_status.json" in blk
    assert "m1_reference_gdc_integration_stub.json" in blk


def test_m1_batch_correction_mirror_rules_exist() -> None:
    assert "rule m1_batch_correction_mirror_paths_status:" in _SNAKE
    assert "rule m1_batch_correction_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_m1_batch_correction_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m1_batch_correction_mirror_paths_status.json" in blk
    assert "m1_batch_correction_mirror_integration_stub.json" in blk


def test_m3_repo_m1_outline_rules_exist() -> None:
    assert "rule m3_repo_m1_outline_paths_status:" in _SNAKE
    assert "rule m3_repo_m1_outline_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_m1_outline_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_m1_outline_paths_status.json" in blk
    assert "m3_repo_m1_outline_integration_stub.json" in blk


def test_m3_repo_m1_harmony_batch_rules_exist() -> None:
    assert "rule m3_repo_m1_harmony_batch_paths_status:" in _SNAKE
    assert "rule m3_repo_m1_harmony_batch_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_m1_harmony_batch_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_m1_harmony_batch_paths_status.json" in blk
    assert "m3_repo_m1_harmony_batch_integration_stub.json" in blk


def test_m3_repo_m1_reference_gdc_rules_exist() -> None:
    assert "rule m3_repo_m1_reference_gdc_paths_status:" in _SNAKE
    assert "rule m3_repo_m1_reference_gdc_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_m1_reference_gdc_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_m1_reference_gdc_paths_status.json" in blk
    assert "m3_repo_m1_reference_gdc_integration_stub.json" in blk


def test_m3_repo_m1_batch_correction_mirror_rules_exist() -> None:
    assert "rule m3_repo_m1_batch_correction_mirror_paths_status:" in _SNAKE
    assert "rule m3_repo_m1_batch_correction_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_m1_batch_correction_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_m1_batch_correction_mirror_paths_status.json" in blk
    assert "m3_repo_m1_batch_correction_mirror_integration_stub.json" in blk


def test_m3_repo_m2_cptac_methylation_rules_exist() -> None:
    assert "rule m3_repo_m2_cptac_methylation_paths_status:" in _SNAKE
    assert "rule m3_repo_m2_cptac_methylation_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_m2_cptac_methylation_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_m2_cptac_methylation_paths_status.json" in blk
    assert "m3_repo_m2_cptac_methylation_integration_stub.json" in blk


def test_m3_repo_m2_1_star_pairing_rules_exist() -> None:
    assert "rule m3_repo_m2_1_star_pairing_paths_status:" in _SNAKE
    assert "rule m3_repo_m2_1_star_pairing_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_m2_1_star_pairing_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_m2_1_star_pairing_paths_status.json" in blk
    assert "m3_repo_m2_1_star_pairing_integration_stub.json" in blk


def test_m3_repo_m2_1_recount3_mirror_rules_exist() -> None:
    assert "rule m3_repo_m2_1_recount3_mirror_paths_status:" in _SNAKE
    assert "rule m3_repo_m2_1_recount3_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_m2_1_recount3_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_m2_1_recount3_mirror_paths_status.json" in blk
    assert "m3_repo_m2_1_recount3_mirror_integration_stub.json" in blk


def test_m3_repo_m2_1_toil_xena_hub_rules_exist() -> None:
    assert "rule m3_repo_m2_1_toil_xena_hub_paths_status:" in _SNAKE
    assert "rule m3_repo_m2_1_toil_xena_hub_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_m2_1_toil_xena_hub_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_m2_1_toil_xena_hub_paths_status.json" in blk
    assert "m3_repo_m2_1_toil_xena_hub_integration_stub.json" in blk


def test_m3_repo_m2_movics_rules_exist() -> None:
    assert "rule m3_repo_m2_movics_paths_status:" in _SNAKE
    assert "rule m3_repo_m2_movics_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_m2_movics_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_m2_movics_paths_status.json" in blk
    assert "m3_repo_m2_movics_integration_stub.json" in blk


def test_m3_repo_m2_3_immune_tme_mirror_rules_exist() -> None:
    assert "rule m3_repo_m2_3_immune_tme_mirror_paths_status:" in _SNAKE
    assert "rule m3_repo_m2_3_immune_tme_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_m2_3_immune_tme_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_m2_3_immune_tme_mirror_paths_status.json" in blk
    assert "m3_repo_m2_3_immune_tme_mirror_integration_stub.json" in blk


def test_m3_repo_m2_2_variant_annotation_rules_exist() -> None:
    assert "rule m3_repo_m2_2_variant_annotation_paths_status:" in _SNAKE
    assert "rule m3_repo_m2_2_variant_annotation_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_m2_2_variant_annotation_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_m2_2_variant_annotation_paths_status.json" in blk
    assert "m3_repo_m2_2_variant_annotation_integration_stub.json" in blk


def test_m3_repo_m2_2_depmap_mirror_rules_exist() -> None:
    assert "rule m3_repo_m2_2_depmap_mirror_paths_status:" in _SNAKE
    assert "rule m3_repo_m2_2_depmap_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_m2_2_depmap_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_m2_2_depmap_mirror_paths_status.json" in blk
    assert "m3_repo_m2_2_depmap_mirror_integration_stub.json" in blk


def test_m3_repo_m2_2_maf_mutsig_mirror_rules_exist() -> None:
    assert "rule m3_repo_m2_2_maf_mutsig_mirror_paths_status:" in _SNAKE
    assert "rule m3_repo_m2_2_maf_mutsig_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_m2_2_maf_mutsig_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_m2_2_maf_mutsig_mirror_paths_status.json" in blk
    assert "m3_repo_m2_2_maf_mutsig_mirror_integration_stub.json" in blk


def test_m3_repo_m2_2_outline_driver_mirror_rules_exist() -> None:
    assert "rule m3_repo_m2_2_outline_driver_mirror_paths_status:" in _SNAKE
    assert "rule m3_repo_m2_2_outline_driver_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_m2_2_outline_driver_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_m2_2_outline_driver_mirror_paths_status.json" in blk
    assert "m3_repo_m2_2_outline_driver_mirror_integration_stub.json" in blk


def test_m3_repo_m2_maf_annotation_rules_exist() -> None:
    assert "rule m3_repo_m2_maf_annotation_paths_status:" in _SNAKE
    assert "rule m3_repo_m2_maf_annotation_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_m2_maf_annotation_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_m2_maf_annotation_paths_status.json" in blk
    assert "m3_repo_m2_maf_annotation_integration_stub.json" in blk


def test_m5_modality_rules_exist() -> None:
    assert "rule m5_modality_paths_status:" in _SNAKE
    assert "rule m5_modality_integration_stub:" in _SNAKE


def test_m5_export_manifest_depends_on_modality_artifacts() -> None:
    blk = rule_block(_SNAKE, "m5_export_manifest")
    assert "m5_modality_paths_status.json" in blk
    assert "m5_modality_integration_stub.json" in blk


def test_m5_export_manifest_depends_on_lincs_signature_entrez_tables() -> None:
    blk = rule_block(_SNAKE, "m5_export_manifest")
    assert 'm5lc_sig_w="results/module5/lincs_disease_signature_welch_entrez.tsv"' in blk
    assert (
        'm5lc_sw_cl="results/module5/lincs_disease_signature/stratified/welch_integrated/'
        'dea_welch_subtype_Classical_entrez.tsv"' in blk
    )
    assert (
        'm5lc_so_pr="results/module5/lincs_disease_signature/stratified/ols_integrated/'
        'dea_ols_subtype_Proneural_entrez.tsv"' in blk
    )


def test_m5_srges_run_rule_exists() -> None:
    assert "rule m5_srges_run:" in _SNAKE


def test_m5_srges_integration_stub_does_not_require_m5_srges_run_outputs() -> None:
    blk = rule_block(_SNAKE, "m5_srges_integration_stub")
    assert "m5_srges_compound_ranks.tsv" not in blk
    assert "m5_srges_run_provenance.json" not in blk
    assert "lincs_signature_pack.json" in blk


def test_m5_export_manifest_does_not_list_m5_srges_run_artifacts() -> None:
    blk = rule_block(_SNAKE, "m5_export_manifest")
    assert 'm5srgrank="results/module5/m5_srges_compound_ranks.tsv"' not in blk
    assert 'm5srgprov="results/module5/m5_srges_run_provenance.json"' not in blk


def test_m3_deconvolution_demo_rule_removed() -> None:
    assert "rule m3_deconvolution_demo:" not in _SNAKE


def test_m3_deconvolution_integration_stub_no_demo_or_s2_inputs() -> None:
    blk = rule_block(_SNAKE, "m3_deconvolution_integration_stub")
    assert "m3_deconvolution_demo" not in blk
    assert "m3_deconvolution_s2" not in blk
    assert "m3_deconvolution_paths_status.json" in blk


def test_m3_export_manifest_no_demo_or_s2_deconv_artifact_inputs() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3dd_" not in blk
    assert "m3s2_" not in blk


def test_m3_deconvolution_s2_nnls_rule_exists() -> None:
    assert "rule m3_deconvolution_s2_nnls:" in _SNAKE


def test_m3_deconvolution_rctd_and_cell2location_rules_exist() -> None:
    assert "rule m3_deconvolution_rctd_run:" in _SNAKE
    assert "rule m3_deconvolution_cell2location_run:" in _SNAKE
    assert "m3_rctd.yaml" in _SNAKE
    assert "_m3_rctd_conda_env_path" in _SNAKE
    assert "m3_rctd_spacexr_bioconda.yaml" in _SNAKE
    assert "_m3_cell2location_config_path" in _SNAKE
    assert "m3_cell2location.yaml" in _SNAKE


def test_m3_deconv_rctd_cell2location_rule_docstrings_note_flag_semantics() -> None:
    rblk = rule_block(_SNAKE, "m3_deconvolution_rctd_run")
    assert "rctd_run.flag only when provenance status is ok" in rblk
    cblk = rule_block(_SNAKE, "m3_deconvolution_cell2location_run")
    assert "cell2location_run.flag only when the script exits 0" in cblk


def test_m3_cell2location_conditional_sidecar_outputs_in_snakefile() -> None:
    assert "_m3_cell2location_training_enabled" in _SNAKE
    assert "_M3_C2L_RUN_OUTPUTS" in _SNAKE
    assert "**_M3_C2L_RUN_OUTPUTS" in _SNAKE
    i = _SNAKE.find("def _rule_all_optional_inputs")
    assert i >= 0
    j = _SNAKE.find("\ndef ", i + 1)
    block = _SNAKE[i:j]
    assert "_m3_cell2location_output_result_h5ad_repo_rel" in block


def test_m3_deconvolution_s2_gated_in_optional_rule_all() -> None:
    i = _SNAKE.find("def _rule_all_optional_inputs")
    assert i >= 0
    j = _SNAKE.find("\ndef ", i + 1)
    block = _SNAKE[i:j]
    assert "GLIOMA_TARGET_INCLUDE_M3_DECONV_S2" in block
    assert "m3_deconvolution_s2/deconvolution_s2_provenance.json" in block


def test_m3_deconv_rctd_cell2location_gated_in_optional_rule_all() -> None:
    i = _SNAKE.find("def _rule_all_optional_inputs")
    assert i >= 0
    j = _SNAKE.find("\ndef ", i + 1)
    block = _SNAKE[i:j]
    assert "GLIOMA_TARGET_INCLUDE_M3_RCTD_RUN" in block
    assert "m3_deconvolution_rctd/rctd_run_provenance.json" in block
    assert "GLIOMA_TARGET_INCLUDE_M3_CELL2LOCATION_RUN" in block
    assert "m3_deconvolution_cell2location/cell2location_run_provenance.json" in block
    assert "_m3_cell2location_training_enabled" in block


def test_m4_network_rules_exist() -> None:
    assert "rule m4_network_paths_status:" in _SNAKE
    assert "rule m4_network_integration_stub:" in _SNAKE


def test_m4_export_manifest_depends_on_network_artifacts() -> None:
    blk = rule_block(_SNAKE, "m4_export_manifest")
    assert "m4_network_paths_status.json" in blk
    assert "m4_network_integration_stub.json" in blk


def test_m4_string_cache_rules_exist() -> None:
    assert "rule m4_string_cache_paths_status:" in _SNAKE
    assert "rule m4_string_cache_integration_stub:" in _SNAKE


def test_m4_export_manifest_depends_on_string_cache_artifacts() -> None:
    blk = rule_block(_SNAKE, "m4_export_manifest")
    assert "m4_string_cache_paths_status.json" in blk
    assert "m4_string_cache_integration_stub.json" in blk


def test_m4_gsea_mirror_rules_exist() -> None:
    assert "rule m4_gsea_mirror_paths_status:" in _SNAKE
    assert "rule m4_gsea_mirror_integration_stub:" in _SNAKE


def test_m4_export_manifest_depends_on_gsea_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m4_export_manifest")
    assert "m4_gsea_mirror_paths_status.json" in blk
    assert "m4_gsea_mirror_integration_stub.json" in blk


def test_m4_pathway_database_mirror_rules_exist() -> None:
    assert "rule m4_pathway_database_mirror_paths_status:" in _SNAKE
    assert "rule m4_pathway_database_mirror_integration_stub:" in _SNAKE


def test_m4_export_manifest_depends_on_pathway_database_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m4_export_manifest")
    assert "m4_pathway_database_mirror_paths_status.json" in blk
    assert "m4_pathway_database_mirror_integration_stub.json" in blk


def test_m4_export_manifest_depends_on_stratified_gsea_prerank_rnks() -> None:
    blk = rule_block(_SNAKE, "m4_export_manifest")
    assert (
        'gsea_rsw_cl="results/module4/gsea/stratified/welch_integrated/'
        'dea_welch_subtype_Classical_signed_neg_log10_p.rnk"' in blk
    )
    assert (
        'gsea_rso_pr="results/module4/gsea/stratified/ols_integrated/'
        'dea_ols_subtype_Proneural_signed_neg_log10_p.rnk"' in blk
    )


def test_m4_export_manifest_depends_on_string_api_network_artifacts() -> None:
    blk = rule_block(_SNAKE, "m4_export_manifest")
    assert 'm4sa_prov="results/module4/string_api/string_api_fetch_provenance.json"' in blk
    assert 'm4sa_r3="results/module4/string_api/recount3_depmap_crispr_consensus_network.json"' in blk


def test_m7_validation_rules_exist() -> None:
    assert "rule m7_validation_paths_status:" in _SNAKE
    assert "rule m7_validation_integration_stub:" in _SNAKE


def test_m7_export_manifest_depends_on_validation_outline_artifacts() -> None:
    blk = rule_block(_SNAKE, "m7_export_manifest")
    assert "m7_validation_paths_status.json" in blk
    assert "m7_validation_integration_stub.json" in blk


def test_m7_gts_external_score_mirror_rules_exist() -> None:
    assert "rule m7_gts_external_score_mirror_paths_status:" in _SNAKE
    assert "rule m7_gts_external_score_mirror_integration_stub:" in _SNAKE


def test_m7_export_manifest_depends_on_gts_external_score_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m7_export_manifest")
    assert "m7_gts_external_score_mirror_paths_status.json" in blk
    assert "m7_gts_external_score_mirror_integration_stub.json" in blk


def test_m6_toxicity_rules_exist() -> None:
    assert "rule m6_toxicity_paths_status:" in _SNAKE
    assert "rule m6_toxicity_integration_stub:" in _SNAKE


def test_m6_export_manifest_depends_on_toxicity_artifacts() -> None:
    blk = rule_block(_SNAKE, "m6_export_manifest")
    assert "m6_toxicity_paths_status.json" in blk
    assert "m6_toxicity_integration_stub.json" in blk


def test_m6_docking_output_rules_exist() -> None:
    assert "rule m6_docking_output_paths_status:" in _SNAKE
    assert "rule m6_docking_output_integration_stub:" in _SNAKE


def test_m6_export_manifest_depends_on_docking_output_artifacts() -> None:
    blk = rule_block(_SNAKE, "m6_export_manifest")
    assert "m6_docking_output_paths_status.json" in blk
    assert "m6_docking_output_integration_stub.json" in blk


def test_m6_compound_library_mirror_rules_exist() -> None:
    assert "rule m6_compound_library_mirror_paths_status:" in _SNAKE
    assert "rule m6_compound_library_mirror_integration_stub:" in _SNAKE


def test_m6_export_manifest_depends_on_compound_library_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m6_export_manifest")
    assert "m6_compound_library_mirror_paths_status.json" in blk
    assert "m6_compound_library_mirror_integration_stub.json" in blk


def test_m5_l1000_data_rules_exist() -> None:
    assert "rule m5_l1000_data_paths_status:" in _SNAKE
    assert "rule m5_l1000_data_integration_stub:" in _SNAKE


def test_m5_export_manifest_depends_on_l1000_data_artifacts() -> None:
    blk = rule_block(_SNAKE, "m5_export_manifest")
    assert "m5_l1000_data_paths_status.json" in blk
    assert "m5_l1000_data_integration_stub.json" in blk


def test_m5_srges_output_rules_exist() -> None:
    assert "rule m5_srges_output_paths_status:" in _SNAKE
    assert "rule m5_srges_output_integration_stub:" in _SNAKE


def test_m5_export_manifest_depends_on_srges_output_artifacts() -> None:
    blk = rule_block(_SNAKE, "m5_export_manifest")
    assert "m5_srges_output_paths_status.json" in blk
    assert "m5_srges_output_integration_stub.json" in blk


def test_m5_lincs_connectivity_mirror_rules_exist() -> None:
    assert "rule m5_lincs_connectivity_mirror_paths_status:" in _SNAKE
    assert "rule m5_lincs_connectivity_mirror_integration_stub:" in _SNAKE


def test_m5_export_manifest_depends_on_lincs_connectivity_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m5_export_manifest")
    assert "m5_lincs_connectivity_mirror_paths_status.json" in blk
    assert "m5_lincs_connectivity_mirror_integration_stub.json" in blk


def test_vendor_tooling_rules_exist() -> None:
    assert "rule vendor_tooling_paths_status:" in _SNAKE
    assert "rule vendor_tooling_integration_stub:" in _SNAKE
