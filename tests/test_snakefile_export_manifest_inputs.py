"""Regression: m3_export_manifest stub and repo-mirror inputs vs Snakefile."""

from __future__ import annotations

from pathlib import Path

from snakefile_rule_block import rule_block
from snakefile_text_cache import snakefile_text

_ROOT = Path(__file__).resolve().parents[1]
_SNAKE = snakefile_text()


def test_m3_scrna_spatial_integration_stub_rule_exists() -> None:
    assert "rule m3_scrna_spatial_integration_stub:" in _SNAKE


def test_m3_public_inputs_status_rule_exists() -> None:
    assert "rule m3_public_inputs_status:" in _SNAKE


def test_m3_export_manifest_depends_on_scrna_stub() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "scrna_spatial_integration_stub.json" in blk
    assert "scrna_spatial_integration_stub.flag" in blk


def test_m3_repo_scrna_spatial_rules_exist() -> None:
    assert "rule m3_repo_scrna_spatial_paths_status:" in _SNAKE
    assert "rule m3_repo_scrna_spatial_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_scrna_spatial_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_scrna_spatial_paths_status.json" in blk
    assert "m3_repo_scrna_spatial_integration_stub.json" in blk


def test_m3_repo_public_inputs_rules_exist() -> None:
    assert "rule m3_repo_public_inputs_paths_status:" in _SNAKE
    assert "rule m3_repo_public_inputs_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_public_inputs_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_public_inputs_paths_status.json" in blk
    assert "m3_repo_public_inputs_integration_stub.json" in blk


def test_m3_repo_sc_workflow_rules_exist() -> None:
    assert "rule m3_repo_sc_workflow_paths_status:" in _SNAKE
    assert "rule m3_repo_sc_workflow_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_sc_workflow_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_sc_workflow_paths_status.json" in blk
    assert "m3_repo_sc_workflow_integration_stub.json" in blk


def test_m3_deconvolution_rules_exist() -> None:
    assert "rule m3_deconvolution_paths_status:" in _SNAKE
    assert "rule m3_deconvolution_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_deconvolution_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_deconvolution_paths_status.json" in blk
    assert "m3_deconvolution_integration_stub.json" in blk


def test_m3_export_manifest_does_not_depend_on_optional_rctd_cell2location_run_outputs() -> None:
    """RCTD/c2l files are in module3_export_manifest JSON only (see _ARTIFACTS_EXEMPT_FROM_SNAKEFILE_MANIFEST_INPUTS)."""
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_deconvolution_rctd/rctd_run_provenance.json" not in blk
    assert "spatial_cell2location.h5ad" not in blk


def test_m3_cellranger_output_rules_exist() -> None:
    assert "rule m3_cellranger_output_paths_status:" in _SNAKE
    assert "rule m3_cellranger_output_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_cellranger_output_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_cellranger_output_paths_status.json" in blk
    assert "m3_cellranger_output_integration_stub.json" in blk


def test_m3_repo_deconvolution_rules_exist() -> None:
    assert "rule m3_repo_deconvolution_paths_status:" in _SNAKE
    assert "rule m3_repo_deconvolution_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_deconvolution_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_deconvolution_paths_status.json" in blk
    assert "m3_repo_deconvolution_integration_stub.json" in blk


def test_m3_repo_cellranger_output_rules_exist() -> None:
    assert "rule m3_repo_cellranger_output_paths_status:" in _SNAKE
    assert "rule m3_repo_cellranger_output_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_cellranger_output_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_cellranger_output_paths_status.json" in blk
    assert "m3_repo_cellranger_output_integration_stub.json" in blk


def test_m3_dryad_sra_rules_exist() -> None:
    assert "rule m3_dryad_sra_paths_status:" in _SNAKE
    assert "rule m3_dryad_sra_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_dryad_sra_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_dryad_sra_paths_status.json" in blk
    assert "m3_dryad_sra_integration_stub.json" in blk


def test_m3_geo_pipelines_mirror_rules_exist() -> None:
    assert "rule m3_geo_pipelines_mirror_paths_status:" in _SNAKE
    assert "rule m3_geo_pipelines_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_geo_pipelines_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_geo_pipelines_mirror_paths_status.json" in blk
    assert "m3_geo_pipelines_mirror_integration_stub.json" in blk


def test_m3_tcga_recount_lincs_mirror_rules_exist() -> None:
    assert "rule m3_tcga_recount_lincs_mirror_paths_status:" in _SNAKE
    assert "rule m3_tcga_recount_lincs_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_tcga_recount_lincs_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_tcga_recount_lincs_mirror_paths_status.json" in blk
    assert "m3_tcga_recount_lincs_mirror_integration_stub.json" in blk


def test_m3_repo_dryad_sra_rules_exist() -> None:
    assert "rule m3_repo_dryad_sra_paths_status:" in _SNAKE
    assert "rule m3_repo_dryad_sra_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_dryad_sra_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_dryad_sra_paths_status.json" in blk
    assert "m3_repo_dryad_sra_integration_stub.json" in blk


def test_m3_repo_geo_pipelines_mirror_rules_exist() -> None:
    assert "rule m3_repo_geo_pipelines_mirror_paths_status:" in _SNAKE
    assert "rule m3_repo_geo_pipelines_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_geo_pipelines_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_geo_pipelines_mirror_paths_status.json" in blk
    assert "m3_repo_geo_pipelines_mirror_integration_stub.json" in blk


def test_m3_repo_tcga_recount_lincs_mirror_rules_exist() -> None:
    assert "rule m3_repo_tcga_recount_lincs_mirror_paths_status:" in _SNAKE
    assert "rule m3_repo_tcga_recount_lincs_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_tcga_recount_lincs_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_tcga_recount_lincs_mirror_paths_status.json" in blk
    assert "m3_repo_tcga_recount_lincs_mirror_integration_stub.json" in blk


def test_m3_repo_bundled_references_rules_exist() -> None:
    assert "rule m3_repo_bundled_references_paths_status:" in _SNAKE
    assert "rule m3_repo_bundled_references_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_bundled_references_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_bundled_references_paths_status.json" in blk
    assert "m3_repo_bundled_references_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_bundled_reference_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm3rbr_gmt_c2="references/verhaak_msigdb_c2_cgp_2024.1.Hs.gmt"' in blk
    assert 'm3rbr_drivers_yaml="references/gbm_known_drivers_outline.yaml"' in blk


def test_m3_repo_gdc_expression_matrix_rules_exist() -> None:
    assert "rule m3_repo_gdc_expression_matrix_paths_status:" in _SNAKE
    assert "rule m3_repo_gdc_expression_matrix_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_gdc_expression_matrix_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_gdc_expression_matrix_paths_status.json" in blk
    assert "m3_repo_gdc_expression_matrix_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module2_gdc_matrix_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm2gdc_tpm="results/module2/tcga_gbm_star_tpm_matrix.parquet"' in blk
    assert 'm2gdc_counts="results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet"' in blk
    assert 'm2gdc_meta="results/module2/tcga_gbm_sample_meta.tsv"' in blk
    assert 'm2gdc_qc="results/module2/gdc_counts_matrix_qc.json"' in blk
    assert 'm2gdc_cohort_sum="results/module2/gdc_counts_cohort_summary.json"' in blk


def test_m3_repo_toil_bulk_expression_rules_exist() -> None:
    assert "rule m3_repo_toil_bulk_expression_paths_status:" in _SNAKE
    assert "rule m3_repo_toil_bulk_expression_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_toil_bulk_expression_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_toil_bulk_expression_paths_status.json" in blk
    assert "m3_repo_toil_bulk_expression_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_toil_hub_matrix_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm3toil_tpm="results/module3/toil_gbm_vs_brain_tpm.parquet"' in blk
    assert 'm3toil_samples="results/module3/toil_gbm_vs_brain_samples.tsv"' in blk


def test_m3_repo_recount3_bulk_dea_rules_exist() -> None:
    assert "rule m3_repo_recount3_bulk_dea_paths_status:" in _SNAKE
    assert "rule m3_repo_recount3_bulk_dea_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_recount3_bulk_dea_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_recount3_bulk_dea_paths_status.json" in blk
    assert "m3_repo_recount3_bulk_dea_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_recount3_bulk_dea_result_tsvs() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert (
        'r3_deseq2_tsv="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_results.tsv"'
        in blk
    )
    assert (
        'r3_edger_qlf_tsv="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_qlf_results.tsv"'
        in blk
    )


def test_m3_repo_bulk_welch_ols_dea_rules_exist() -> None:
    assert "rule m3_repo_bulk_welch_ols_dea_paths_status:" in _SNAKE
    assert "rule m3_repo_bulk_welch_ols_dea_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_bulk_welch_ols_dea_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_bulk_welch_ols_dea_paths_status.json" in blk
    assert "m3_repo_bulk_welch_ols_dea_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_bulk_welch_ols_dea_tsvs() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm3bwo_welch_tsv="results/module3/dea_gbm_vs_gtex_brain.tsv"' in blk
    assert (
        'm3bwo_ols_tsv="results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv"' in blk
    )


def test_m3_repo_toil_vs_recount3_correlation_rules_exist() -> None:
    assert "rule m3_repo_toil_vs_recount3_correlation_paths_status:" in _SNAKE
    assert "rule m3_repo_toil_vs_recount3_correlation_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_toil_vs_recount3_correlation_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_toil_vs_recount3_correlation_paths_status.json" in blk
    assert "m3_repo_toil_vs_recount3_correlation_integration_stub.json" in blk


def test_m3_export_manifest_cross_and_r3conc_match_toil_vs_recount3_outline() -> None:
    """m3_repo_toil_vs_recount3_correlation inventories these JSONs; rule m3_export_manifest names them cross / r3conc."""
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert (
        'cross="results/module3/toil_welch_vs_recount3_bulk_effect_correlation.json"' in blk
    )
    assert (
        'r3conc="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_vs_edger_concordance.json"'
        in blk
    )


def test_m3_repo_stratified_bulk_dea_rules_exist() -> None:
    assert "rule m3_repo_stratified_bulk_dea_paths_status:" in _SNAKE
    assert "rule m3_repo_stratified_bulk_dea_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_stratified_bulk_dea_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_stratified_bulk_dea_paths_status.json" in blk
    assert "m3_repo_stratified_bulk_dea_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_stratified_dea_summary_tsvs() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm3rsb_welch_sum="results/module3/stratified_dea/summary.tsv"' in blk
    assert 'm3rsb_ols_sum="results/module3/stratified_ols_dea/summary.tsv"' in blk


def test_m3_repo_cohort_verhaak_subtype_rules_exist() -> None:
    assert "rule m3_repo_cohort_verhaak_subtype_paths_status:" in _SNAKE
    assert "rule m3_repo_cohort_verhaak_subtype_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_cohort_verhaak_subtype_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_cohort_verhaak_subtype_paths_status.json" in blk
    assert "m3_repo_cohort_verhaak_subtype_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_cohort_verhaak_subtype_tsvs() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm3rcv_scores_tsv="results/module3/tcga_gbm_verhaak_subtype_scores.tsv"' in blk
    assert 'm3rcv_mean_tpm_tsv="results/module3/mean_log_tpm_by_verhaak_subtype.tsv"' in blk
    assert 'm3rcv_subtype_summary="results/module3/tcga_gbm_verhaak_subtype_summary.json"' in blk
    assert (
        'm3rcv_mean_tpm_prov="results/module3/mean_log_tpm_by_verhaak_subtype_provenance.json"' in blk
    )


def test_m3_repo_bulk_join_provenance_rules_exist() -> None:
    assert "rule m3_repo_bulk_join_provenance_paths_status:" in _SNAKE
    assert "rule m3_repo_bulk_join_provenance_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_bulk_join_provenance_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_bulk_join_provenance_paths_status.json" in blk
    assert "m3_repo_bulk_join_provenance_integration_stub.json" in blk


def test_m3_repo_gdc_star_tcga_gbm_dea_rules_exist() -> None:
    assert "rule m3_repo_gdc_star_tcga_gbm_dea_paths_status:" in _SNAKE
    assert "rule m3_repo_gdc_star_tcga_gbm_dea_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_gdc_star_tcga_gbm_dea_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_gdc_star_tcga_gbm_dea_paths_status.json" in blk
    assert "m3_repo_gdc_star_tcga_gbm_dea_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_gdc_star_tcga_gbm_dea_tsvs() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert (
        'm3rgs_d2_pr_tsv="results/module3/deseq2_tcga_gbm/primary_vs_recurrent/deseq2_results.tsv"'
        in blk
    )
    assert (
        'm3rgs_d2_psn_tsv="results/module3/deseq2_tcga_gbm/primary_vs_solid_tissue_normal/deseq2_results.tsv"'
        in blk
    )
    assert (
        'm3rgs_ed_pr_tsv="results/module3/edger_tcga_gbm/primary_vs_recurrent/edger_qlf_results.tsv"'
        in blk
    )
    assert (
        'm3rgs_ed_psn_tsv="results/module3/edger_tcga_gbm/primary_vs_solid_tissue_normal/edger_qlf_results.tsv"'
        in blk
    )


def test_m3_repo_module5_lincs_connectivity_rules_exist() -> None:
    assert "rule m3_repo_module5_lincs_connectivity_paths_status:" in _SNAKE
    assert "rule m3_repo_module5_lincs_connectivity_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module5_lincs_connectivity_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module5_lincs_connectivity_paths_status.json" in blk
    assert "m3_repo_module5_lincs_connectivity_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module5_lincs_connectivity_data_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm5lc_sig_w="results/module5/lincs_disease_signature_welch_entrez.tsv"' in blk
    assert 'm5lc_cmap="results/module5/cmap_tooling_scan.json"' in blk
    assert (
        'm5lc_sw_cl="results/module5/lincs_disease_signature/stratified/welch_integrated/'
        'dea_welch_subtype_Classical_entrez.tsv"' in blk
    )
    assert 'm5lc_srges="results/module5/srges_integration_stub.json"' in blk


def test_m3_repo_module5_l1000_data_manifest_slice_rules_exist() -> None:
    assert "rule m3_repo_module5_l1000_data_paths_status:" in _SNAKE
    assert "rule m3_repo_module5_l1000_data_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module5_l1000_data_manifest_slice() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module5_l1000_data_paths_status.json" in blk
    assert "m3_repo_module5_l1000_data_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module5_l1000_data_repo_outline_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm5l1_ps_js="results/module5/m5_l1000_data_paths_status.json"' in blk
    assert 'm5l1_ps_fl="results/module5/m5_l1000_data_paths_status.flag"' in blk
    assert 'm5l1_st_js="results/module5/m5_l1000_data_integration_stub.json"' in blk
    assert 'm5l1_st_fl="results/module5/m5_l1000_data_integration_stub.flag"' in blk


def test_m3_repo_module5_modality_manifest_slice_rules_exist() -> None:
    assert "rule m3_repo_module5_modality_paths_status:" in _SNAKE
    assert "rule m3_repo_module5_modality_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module5_modality_manifest_slice() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module5_modality_paths_status.json" in blk
    assert "m3_repo_module5_modality_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module5_modality_repo_outline_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm5mo_ps_js="results/module5/m5_modality_paths_status.json"' in blk
    assert 'm5mo_st_fl="results/module5/m5_modality_integration_stub.flag"' in blk


def test_m3_repo_module5_srges_output_manifest_slice_rules_exist() -> None:
    assert "rule m3_repo_module5_srges_output_paths_status:" in _SNAKE
    assert "rule m3_repo_module5_srges_output_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module5_srges_output_manifest_slice() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module5_srges_output_paths_status.json" in blk
    assert "m3_repo_module5_srges_output_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module5_srges_output_repo_outline_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm5so_ps_js="results/module5/m5_srges_output_paths_status.json"' in blk
    assert 'm5so_st_js="results/module5/m5_srges_output_integration_stub.json"' in blk


def test_m3_repo_module5_lincs_connectivity_mirror_manifest_slice_rules_exist() -> None:
    assert "rule m3_repo_module5_lincs_connectivity_mirror_paths_status:" in _SNAKE
    assert "rule m3_repo_module5_lincs_connectivity_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module5_lincs_connectivity_mirror_manifest_slice() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module5_lincs_connectivity_mirror_paths_status.json" in blk
    assert "m3_repo_module5_lincs_connectivity_mirror_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module5_lincs_connectivity_mirror_repo_outline_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm5lcm_ps_js="results/module5/m5_lincs_connectivity_mirror_paths_status.json"' in blk
    assert 'm5lcm_st_fl="results/module5/m5_lincs_connectivity_mirror_integration_stub.flag"' in blk


def test_m3_repo_module4_hub_gsea_rules_exist() -> None:
    assert "rule m3_repo_module4_hub_gsea_paths_status:" in _SNAKE
    assert "rule m3_repo_module4_hub_gsea_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module4_hub_gsea_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module4_hub_gsea_paths_status.json" in blk
    assert "m3_repo_module4_hub_gsea_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module4_hub_gsea_data_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm4hg_we_pq="results/module4/wgcna_hub_expr_subset.parquet"' in blk
    assert 'm4hg_rn_w="results/module4/gsea/dea_welch_signed_neg_log10_p.rnk"' in blk
    assert (
        'm4hg_rsw_cl="results/module4/gsea/stratified/welch_integrated/'
        'dea_welch_subtype_Classical_signed_neg_log10_p.rnk"' in blk
    )


def test_m3_repo_module4_network_rules_exist() -> None:
    assert "rule m3_repo_module4_network_paths_status:" in _SNAKE
    assert "rule m3_repo_module4_network_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module4_network_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module4_network_paths_status.json" in blk
    assert "m3_repo_module4_network_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module4_network_repo_outline_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm4n_ps_js="results/module4/m4_network_paths_status.json"' in blk
    assert 'm4n_st_fl="results/module4/m4_network_integration_stub.flag"' in blk


def test_m3_repo_module4_string_cache_rules_exist() -> None:
    assert "rule m3_repo_module4_string_cache_paths_status:" in _SNAKE
    assert "rule m3_repo_module4_string_cache_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module4_string_cache_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module4_string_cache_paths_status.json" in blk
    assert "m3_repo_module4_string_cache_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module4_string_cache_repo_outline_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm4stc_ps_js="results/module4/m4_string_cache_paths_status.json"' in blk
    assert 'm4stc_st_js="results/module4/m4_string_cache_integration_stub.json"' in blk


def test_m3_repo_module4_pathway_database_mirror_rules_exist() -> None:
    assert "rule m3_repo_module4_pathway_database_mirror_paths_status:" in _SNAKE
    assert "rule m3_repo_module4_pathway_database_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module4_pathway_database_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module4_pathway_database_mirror_paths_status.json" in blk
    assert "m3_repo_module4_pathway_database_mirror_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module4_pathway_database_mirror_repo_outline_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm4pwdm_ps_js="results/module4/m4_pathway_database_mirror_paths_status.json"' in blk
    assert 'm4pwdm_st_js="results/module4/m4_pathway_database_mirror_integration_stub.json"' in blk


def test_m3_repo_module4_gsea_mirror_rules_exist() -> None:
    assert "rule m3_repo_module4_gsea_mirror_paths_status:" in _SNAKE
    assert "rule m3_repo_module4_gsea_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module4_gsea_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module4_gsea_mirror_paths_status.json" in blk
    assert "m3_repo_module4_gsea_mirror_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module4_gsea_mirror_repo_outline_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm4gsm_ps_js="results/module4/m4_gsea_mirror_paths_status.json"' in blk
    assert 'm4gsm_st_fl="results/module4/m4_gsea_mirror_integration_stub.flag"' in blk


def test_m3_repo_module7_gts_stub_rules_exist() -> None:
    assert "rule m3_repo_module7_gts_stub_paths_status:" in _SNAKE
    assert "rule m3_repo_module7_gts_stub_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module7_gts_stub_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module7_gts_stub_paths_status.json" in blk
    assert "m3_repo_module7_gts_stub_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module7_gts_stub_data_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm7g_welch="results/module7/gts_candidate_table_welch_stub.tsv"' in blk
    assert 'm7g_t1_welch="results/module7/glioma_target_tier1_welch.tsv"' in blk
    assert (
        'm7g_sw_cl="results/module7/gts_candidate_stratified/welch_integrated/'
        'dea_welch_subtype_Classical_gts_stub.tsv"' in blk
    )
    assert 'm7g_val_js="results/module7/gts_validation_integration_stub.json"' in blk


def test_m3_repo_module7_validation_rules_exist() -> None:
    assert "rule m3_repo_module7_validation_paths_status:" in _SNAKE
    assert "rule m3_repo_module7_validation_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module7_validation_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module7_validation_paths_status.json" in blk
    assert "m3_repo_module7_validation_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module7_validation_repo_outline_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm7val_ps_js="results/module7/m7_validation_paths_status.json"' in blk
    assert 'm7val_st_fl="results/module7/m7_validation_integration_stub.flag"' in blk


def test_m3_repo_module7_gts_external_score_mirror_rules_exist() -> None:
    assert "rule m3_repo_module7_gts_external_score_mirror_paths_status:" in _SNAKE
    assert "rule m3_repo_module7_gts_external_score_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module7_gts_external_score_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module7_gts_external_score_mirror_paths_status.json" in blk
    assert "m3_repo_module7_gts_external_score_mirror_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module7_gts_external_score_mirror_repo_outline_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert (
        'm7gext_ps_js="results/module7/m7_gts_external_score_mirror_paths_status.json"' in blk
    )
    assert (
        'm7gext_st_js="results/module7/m7_gts_external_score_mirror_integration_stub.json"' in blk
    )


def test_m3_repo_module6_structure_bridge_rules_exist() -> None:
    assert "rule m3_repo_module6_structure_bridge_paths_status:" in _SNAKE
    assert "rule m3_repo_module6_structure_bridge_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module6_structure_bridge_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module6_structure_bridge_paths_status.json" in blk
    assert "m3_repo_module6_structure_bridge_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module6_structure_bridge_data_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm6br_welch="results/module6/structure_druggability_bridge_welch.tsv"' in blk
    assert 'm6br_prov="results/module6/structure_druggability_bridge_provenance.json"' in blk
    assert (
        'm6br_sw_cl="results/module6/structure_druggability_bridge_stratified/welch_integrated/'
        'dea_welch_subtype_Classical_structure_bridge.tsv"' in blk
    )
    assert 'm6br_admet_js="results/module6/structure_admet_integration_stub.json"' in blk


def test_m3_repo_module6_structure_tooling_rules_exist() -> None:
    assert "rule m3_repo_module6_structure_tooling_paths_status:" in _SNAKE
    assert "rule m3_repo_module6_structure_tooling_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module6_structure_tooling_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module6_structure_tooling_paths_status.json" in blk
    assert "m3_repo_module6_structure_tooling_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module6_structure_tooling_paths_status_repo_outline_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm6stool_ps_js="results/module6/module6_structure_tooling_paths_status.json"' in blk
    assert 'm6stool_ps_fl="results/module6/module6_structure_tooling_paths_status.flag"' in blk


def test_m3_repo_tooling_vendor_rules_exist() -> None:
    assert "rule m3_repo_tooling_vendor_paths_status:" in _SNAKE
    assert "rule m3_repo_tooling_vendor_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_tooling_vendor_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_tooling_vendor_paths_status.json" in blk
    assert "m3_repo_tooling_vendor_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_tooling_vendor_data_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm3tv_paths_js="results/tooling/vendor_tooling_paths_status.json"' in blk
    assert 'm3tv_stub_js="results/tooling/vendor_tooling_integration_stub.json"' in blk


def test_m3_repo_module6_docking_output_rules_exist() -> None:
    assert "rule m3_repo_module6_docking_output_paths_status:" in _SNAKE
    assert "rule m3_repo_module6_docking_output_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module6_docking_output_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module6_docking_output_paths_status.json" in blk
    assert "m3_repo_module6_docking_output_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module6_docking_output_repo_outline_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm6dock_ps_js="results/module6/m6_docking_output_paths_status.json"' in blk
    assert 'm6dock_st_js="results/module6/m6_docking_output_integration_stub.json"' in blk


def test_m3_repo_module6_toxicity_rules_exist() -> None:
    assert "rule m3_repo_module6_toxicity_paths_status:" in _SNAKE
    assert "rule m3_repo_module6_toxicity_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module6_toxicity_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module6_toxicity_paths_status.json" in blk
    assert "m3_repo_module6_toxicity_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module6_toxicity_repo_outline_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm6tox_ps_js="results/module6/m6_toxicity_paths_status.json"' in blk
    assert 'm6tox_st_fl="results/module6/m6_toxicity_integration_stub.flag"' in blk


def test_m3_repo_module6_compound_library_mirror_rules_exist() -> None:
    assert "rule m3_repo_module6_compound_library_mirror_paths_status:" in _SNAKE
    assert "rule m3_repo_module6_compound_library_mirror_integration_stub:" in _SNAKE


def test_m3_export_manifest_depends_on_repo_module6_compound_library_mirror_artifacts() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert "m3_repo_module6_compound_library_mirror_paths_status.json" in blk
    assert "m3_repo_module6_compound_library_mirror_integration_stub.json" in blk


def test_m3_export_manifest_depends_on_module6_compound_library_mirror_repo_outline_files() -> None:
    blk = rule_block(_SNAKE, "m3_export_manifest")
    assert 'm6clm_ps_js="results/module6/m6_compound_library_mirror_paths_status.json"' in blk
    assert 'm6clm_st_js="results/module6/m6_compound_library_mirror_integration_stub.json"' in blk
