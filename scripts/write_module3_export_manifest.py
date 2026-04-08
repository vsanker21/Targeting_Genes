#!/usr/bin/env python3
"""
Inventory key Module 3 bulk-DE / integration artifacts (provenance JSONs, flags, concordance).

Paths are curated (not a full directory walk). Use for pipeline_results_index and audits.
RCTD / Cell2location run files appear in ``_ARTIFACTS`` but are listed in
``_ARTIFACTS_EXEMPT_FROM_SNAKEFILE_MANIFEST_INPUTS`` so ``rule m3_export_manifest`` does not
pull optional conda deconv rules into every DAG.
Cell2location ``cell2location_run_provenance.json`` may add ``signature_extract_diagnostic`` /
``gene_intersection_diagnostic`` on training failures (inventory row unchanged; see orchestrator + DATA_MANIFEST).

Config: config/module3_inputs.yaml — module3_export_manifest (extra_artifacts; optional_tags
marks built-in rows as optional when R edgeR or similar was not run).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

import manifest_optional


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module3_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def describe_path(rr: Path, rel: str | None, *, tag: str) -> dict[str, Any]:
    out: dict[str, Any] = {"tag": tag, "path": rel}
    if not rel:
        out["exists"] = False
        return out
    p = rr / str(rel).replace("/", os.sep)
    out["path_posix"] = str(Path(rel).as_posix())
    if not p.is_file():
        out["exists"] = False
        out["size_bytes"] = None
        return out
    st = p.stat()
    out["exists"] = True
    out["size_bytes"] = int(st.st_size)
    out["mtime_utc"] = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
    if p.suffix.lower() in (".tsv", ".txt", ".json", ".flag"):
        try:
            with p.open("rb") as f:
                out["n_newlines"] = sum(1 for _ in f)
        except OSError:
            out["n_newlines"] = None
    return out


# (relative path from repo root, manifest tag)
_ARTIFACTS: list[tuple[str, str]] = [
    ("results/module3/cohort_design_summary.json", "cohort_design.summary"),
    ("results/module3/dea_gbm_vs_gtex_brain_provenance.json", "bulk_dea.welch.provenance"),
    ("results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate_provenance.json", "bulk_dea.ols.provenance"),
    ("results/module3/dea_gbm_vs_gtex_brain.tsv", "bulk_dea.welch.tsv"),
    ("results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv", "bulk_dea.ols.tsv"),
    ("results/module3/tcga_gbm_verhaak_subtype_summary.json", "verhaak.subtype_summary"),
    ("results/module3/tcga_gbm_verhaak_subtype_scores.tsv", "verhaak.subtype_scores_tsv"),
    ("results/module3/mean_log_tpm_by_verhaak_subtype.tsv", "verhaak.mean_log_tpm_by_subtype_tsv"),
    ("results/module3/mean_log_tpm_by_verhaak_subtype_provenance.json", "mean_log_tpm_subtype.provenance"),
    ("results/module3/stratified_dea/stratified_dea_provenance.json", "stratified_dea.welch.provenance"),
    ("results/module3/stratified_ols_dea/stratified_ols_dea_provenance.json", "stratified_dea.ols.provenance"),
    ("results/module3/stratified_dea/summary.tsv", "stratified_dea.welch.summary_tsv"),
    ("results/module3/stratified_ols_dea/summary.tsv", "stratified_dea.ols.summary_tsv"),
    ("results/module3/stratified_dea_integration_provenance.json", "stratified_dea.integration.provenance"),
    ("results/module3/stratified_dea_integration.flag", "stratified_dea.integration.flag"),
    ("results/module3/stratified_integrated_outline_drivers.flag", "stratified_dea.outline_drivers.flag"),
    ("results/module3/depmap_crispr_join_provenance.json", "join.depmap_crispr.provenance"),
    ("results/module3/depmap_somatic_join_provenance.json", "join.depmap_somatic.provenance"),
    ("results/module3/tcga_maf_layer_provenance.json", "join.tcga_maf_layer.provenance"),
    ("results/module3/tcga_maf_join_provenance.json", "join.tcga_maf.provenance"),
    ("results/module3/mutsig_join_provenance.json", "join.mutsig.provenance"),
    ("results/module3/dea_string_export_provenance.json", "string_export.provenance"),
    ("results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_provenance.json", "recount3.deseq2.provenance"),
    ("results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_provenance.json", "recount3.edger.provenance"),
    ("results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_vs_edger_concordance.json", "recount3.deseq2_vs_edger"),
    (
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_results.tsv",
        "recount3.deseq2_results_tsv",
    ),
    (
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_qlf_results.tsv",
        "recount3.edger_qlf_results_tsv",
    ),
    ("results/module3/toil_welch_vs_recount3_bulk_effect_correlation.json", "cross_assay.toil_vs_recount3"),
    (
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/recount3_de_counts_matrix.parquet",
        "recount3.counts_matrix",
    ),
    (
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/recount3_de_sample_meta.tsv",
        "recount3.sample_meta",
    ),
    ("results/module3/deseq2_tcga_gbm/primary_vs_recurrent/deseq2_provenance.json", "gdc_star.deseq2.primary_vs_recurrent"),
    (
        "results/module3/deseq2_tcga_gbm/primary_vs_solid_tissue_normal/deseq2_provenance.json",
        "gdc_star.deseq2.primary_vs_solid_normal",
    ),
    ("results/module3/edger_tcga_gbm/primary_vs_recurrent/edger_provenance.json", "gdc_star.edger.primary_vs_recurrent"),
    (
        "results/module3/edger_tcga_gbm/primary_vs_solid_tissue_normal/edger_provenance.json",
        "gdc_star.edger.primary_vs_solid_normal",
    ),
    (
        "results/module3/deseq2_tcga_gbm/primary_vs_recurrent/deseq2_results.tsv",
        "gdc_star.deseq2.primary_vs_recurrent.tsv",
    ),
    (
        "results/module3/deseq2_tcga_gbm/primary_vs_solid_tissue_normal/deseq2_results.tsv",
        "gdc_star.deseq2.primary_vs_solid_normal.tsv",
    ),
    (
        "results/module3/edger_tcga_gbm/primary_vs_recurrent/edger_qlf_results.tsv",
        "gdc_star.edger.primary_vs_recurrent.qlf_tsv",
    ),
    (
        "results/module3/edger_tcga_gbm/primary_vs_solid_tissue_normal/edger_qlf_results.tsv",
        "gdc_star.edger.primary_vs_solid_normal.qlf_tsv",
    ),
    ("results/module3/module3_public_inputs_status.json", "m3_sc.public_inputs_status"),
    ("results/module3/module3_public_inputs_status.flag", "m3_sc.public_inputs.flag"),
    ("results/module3/module3_sc_workflow_paths_status.json", "m3_sc.workflow_paths_status"),
    ("results/module3/module3_sc_workflow_paths_status.flag", "m3_sc.workflow_paths.flag"),
    ("results/module3/scrna_spatial_integration_stub.json", "m3_sc.scrna_spatial_integration_stub"),
    ("results/module3/scrna_spatial_integration_stub.flag", "m3_sc.scrna_spatial_integration_stub.flag"),
    ("results/module3/m3_repo_scrna_spatial_paths_status.json", "m3_sc.repo_scrna_spatial_paths_status"),
    ("results/module3/m3_repo_scrna_spatial_paths_status.flag", "m3_sc.repo_scrna_spatial_paths_status.flag"),
    (
        "results/module3/m3_repo_scrna_spatial_integration_stub.json",
        "m3_sc.repo_scrna_spatial_integration_stub",
    ),
    (
        "results/module3/m3_repo_scrna_spatial_integration_stub.flag",
        "m3_sc.repo_scrna_spatial_integration_stub.flag",
    ),
    ("results/module3/m3_repo_public_inputs_paths_status.json", "m3_sc.repo_public_inputs_paths_status"),
    ("results/module3/m3_repo_public_inputs_paths_status.flag", "m3_sc.repo_public_inputs_paths_status.flag"),
    ("results/module3/m3_repo_public_inputs_integration_stub.json", "m3_sc.repo_public_inputs_integration_stub"),
    ("results/module3/m3_repo_public_inputs_integration_stub.flag", "m3_sc.repo_public_inputs_integration_stub.flag"),
    ("results/module3/m3_repo_sc_workflow_paths_status.json", "m3_sc.repo_sc_workflow_paths_status"),
    ("results/module3/m3_repo_sc_workflow_paths_status.flag", "m3_sc.repo_sc_workflow_paths_status.flag"),
    ("results/module3/m3_repo_sc_workflow_integration_stub.json", "m3_sc.repo_sc_workflow_integration_stub"),
    ("results/module3/m3_repo_sc_workflow_integration_stub.flag", "m3_sc.repo_sc_workflow_integration_stub.flag"),
    ("results/module3/m3_deconvolution_paths_status.json", "m3_sc.deconvolution_paths_status"),
    ("results/module3/m3_deconvolution_paths_status.flag", "m3_sc.deconvolution_paths_status.flag"),
    ("results/module3/m3_deconvolution_integration_stub.json", "m3_sc.deconvolution_integration_stub"),
    ("results/module3/m3_deconvolution_integration_stub.flag", "m3_sc.deconvolution_integration_stub.flag"),
    (
        "results/module3/m3_deconvolution_rctd/rctd_run_provenance.json",
        "m3_sc.deconvolution_rctd_provenance",
    ),
    ("results/module3/m3_deconvolution_rctd/rctd_run.flag", "m3_sc.deconvolution_rctd_flag"),
    (
        "results/module3/m3_deconvolution_cell2location/cell2location_run_provenance.json",
        "m3_sc.deconvolution_cell2location_provenance",
    ),
    (
        "results/module3/m3_deconvolution_cell2location/cell2location_run.flag",
        "m3_sc.deconvolution_cell2location_flag",
    ),
    (
        "results/module3/m3_deconvolution_cell2location/spatial_cell2location.h5ad",
        "m3_sc.deconvolution_cell2location_result_h5ad",
    ),
    (
        "results/module3/m3_deconvolution_cell2location/spot_cell_abundance_means.tsv",
        "m3_sc.deconvolution_cell2location_abundance_tsv",
    ),
    ("results/module3/m3_repo_deconvolution_paths_status.json", "m3_sc.repo_deconvolution_paths_status"),
    ("results/module3/m3_repo_deconvolution_paths_status.flag", "m3_sc.repo_deconvolution_paths_status.flag"),
    ("results/module3/m3_repo_deconvolution_integration_stub.json", "m3_sc.repo_deconvolution_integration_stub"),
    ("results/module3/m3_repo_deconvolution_integration_stub.flag", "m3_sc.repo_deconvolution_integration_stub.flag"),
    ("results/module3/m3_cellranger_output_paths_status.json", "m3_sc.cellranger_output_paths_status"),
    ("results/module3/m3_cellranger_output_paths_status.flag", "m3_sc.cellranger_output_paths_status.flag"),
    ("results/module3/m3_cellranger_output_integration_stub.json", "m3_sc.cellranger_output_integration_stub"),
    ("results/module3/m3_cellranger_output_integration_stub.flag", "m3_sc.cellranger_output_integration_stub.flag"),
    ("results/module3/m3_repo_cellranger_output_paths_status.json", "m3_sc.repo_cellranger_output_paths_status"),
    ("results/module3/m3_repo_cellranger_output_paths_status.flag", "m3_sc.repo_cellranger_output_paths_status.flag"),
    ("results/module3/m3_repo_cellranger_output_integration_stub.json", "m3_sc.repo_cellranger_output_integration_stub"),
    ("results/module3/m3_repo_cellranger_output_integration_stub.flag", "m3_sc.repo_cellranger_output_integration_stub.flag"),
    ("results/module3/m3_dryad_sra_paths_status.json", "m3_sc.dryad_sra_paths_status"),
    ("results/module3/m3_dryad_sra_paths_status.flag", "m3_sc.dryad_sra_paths_status.flag"),
    ("results/module3/m3_dryad_sra_integration_stub.json", "m3_sc.dryad_sra_integration_stub"),
    ("results/module3/m3_dryad_sra_integration_stub.flag", "m3_sc.dryad_sra_integration_stub.flag"),
    ("results/module3/m3_repo_dryad_sra_paths_status.json", "m3_sc.repo_dryad_sra_paths_status"),
    ("results/module3/m3_repo_dryad_sra_paths_status.flag", "m3_sc.repo_dryad_sra_paths_status.flag"),
    ("results/module3/m3_repo_dryad_sra_integration_stub.json", "m3_sc.repo_dryad_sra_integration_stub"),
    ("results/module3/m3_repo_dryad_sra_integration_stub.flag", "m3_sc.repo_dryad_sra_integration_stub.flag"),
    ("results/module3/m3_geo_pipelines_mirror_paths_status.json", "m3_sc.geo_pipelines_mirror_paths_status"),
    ("results/module3/m3_geo_pipelines_mirror_paths_status.flag", "m3_sc.geo_pipelines_mirror_paths_status.flag"),
    ("results/module3/m3_geo_pipelines_mirror_integration_stub.json", "m3_sc.geo_pipelines_mirror_integration_stub"),
    ("results/module3/m3_geo_pipelines_mirror_integration_stub.flag", "m3_sc.geo_pipelines_mirror_integration_stub.flag"),
    ("results/module3/m3_repo_geo_pipelines_mirror_paths_status.json", "m3_sc.repo_geo_pipelines_mirror_paths_status"),
    ("results/module3/m3_repo_geo_pipelines_mirror_paths_status.flag", "m3_sc.repo_geo_pipelines_mirror_paths_status.flag"),
    ("results/module3/m3_repo_geo_pipelines_mirror_integration_stub.json", "m3_sc.repo_geo_pipelines_mirror_integration_stub"),
    ("results/module3/m3_repo_geo_pipelines_mirror_integration_stub.flag", "m3_sc.repo_geo_pipelines_mirror_integration_stub.flag"),
    ("results/module3/m3_tcga_recount_lincs_mirror_paths_status.json", "m3_sc.tcga_recount_lincs_mirror_paths_status"),
    ("results/module3/m3_tcga_recount_lincs_mirror_paths_status.flag", "m3_sc.tcga_recount_lincs_mirror_paths_status.flag"),
    ("results/module3/m3_tcga_recount_lincs_mirror_integration_stub.json", "m3_sc.tcga_recount_lincs_mirror_integration_stub"),
    ("results/module3/m3_tcga_recount_lincs_mirror_integration_stub.flag", "m3_sc.tcga_recount_lincs_mirror_integration_stub.flag"),
    ("results/module3/m3_repo_tcga_recount_lincs_mirror_paths_status.json", "m3_sc.repo_tcga_recount_lincs_mirror_paths_status"),
    ("results/module3/m3_repo_tcga_recount_lincs_mirror_paths_status.flag", "m3_sc.repo_tcga_recount_lincs_mirror_paths_status.flag"),
    ("results/module3/m3_repo_tcga_recount_lincs_mirror_integration_stub.json", "m3_sc.repo_tcga_recount_lincs_mirror_integration_stub"),
    ("results/module3/m3_repo_tcga_recount_lincs_mirror_integration_stub.flag", "m3_sc.repo_tcga_recount_lincs_mirror_integration_stub.flag"),
    ("references/verhaak_msigdb_c2_cgp_2024.1.Hs.gmt", "refs.bundled.verhaak_msigdb_c2_cgp_gmt"),
    ("references/verhaak_msigdb_c4_cgn_2024.1.Hs.gmt", "refs.bundled.verhaak_msigdb_c4_cgn_gmt"),
    ("references/verhaak_centroids_user_template.tsv", "refs.bundled.verhaak_centroids_template_tsv"),
    ("references/gbm_known_drivers_outline.yaml", "refs.bundled.gbm_known_drivers_yaml"),
    ("results/module3/m3_repo_bundled_references_paths_status.json", "m3_sc.repo_bundled_references_paths_status"),
    ("results/module3/m3_repo_bundled_references_paths_status.flag", "m3_sc.repo_bundled_references_paths_status.flag"),
    ("results/module3/m3_repo_bundled_references_integration_stub.json", "m3_sc.repo_bundled_references_integration_stub"),
    ("results/module3/m3_repo_bundled_references_integration_stub.flag", "m3_sc.repo_bundled_references_integration_stub.flag"),
    ("results/module3/m3_repo_gdc_expression_matrix_paths_status.json", "m3_sc.repo_gdc_expression_matrix_paths_status"),
    ("results/module3/m3_repo_gdc_expression_matrix_paths_status.flag", "m3_sc.repo_gdc_expression_matrix_paths_status.flag"),
    ("results/module3/m3_repo_gdc_expression_matrix_integration_stub.json", "m3_sc.repo_gdc_expression_matrix_integration_stub"),
    ("results/module3/m3_repo_gdc_expression_matrix_integration_stub.flag", "m3_sc.repo_gdc_expression_matrix_integration_stub.flag"),
    ("results/module2/tcga_gbm_star_tpm_matrix.parquet", "gdc_repo.tpm_matrix_parquet"),
    ("results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet", "gdc_repo.counts_matrix_parquet"),
    ("results/module2/tcga_gbm_sample_meta.tsv", "gdc_repo.sample_meta_tsv"),
    ("results/module2/gdc_counts_matrix_qc.json", "gdc_repo.counts_matrix_qc"),
    ("results/module2/gdc_counts_cohort_summary.json", "gdc_repo.counts_cohort_summary"),
    ("results/module3/toil_gbm_vs_brain_tpm.parquet", "toil_hub.tpm_parquet"),
    ("results/module3/toil_gbm_vs_brain_samples.tsv", "toil_hub.samples_tsv"),
    ("results/module3/m3_repo_toil_bulk_expression_paths_status.json", "m3_sc.repo_toil_bulk_expression_paths_status"),
    ("results/module3/m3_repo_toil_bulk_expression_paths_status.flag", "m3_sc.repo_toil_bulk_expression_paths_status.flag"),
    ("results/module3/m3_repo_toil_bulk_expression_integration_stub.json", "m3_sc.repo_toil_bulk_expression_integration_stub"),
    ("results/module3/m3_repo_toil_bulk_expression_integration_stub.flag", "m3_sc.repo_toil_bulk_expression_integration_stub.flag"),
    ("results/module3/m3_repo_recount3_bulk_dea_paths_status.json", "m3_sc.repo_recount3_bulk_dea_paths_status"),
    ("results/module3/m3_repo_recount3_bulk_dea_paths_status.flag", "m3_sc.repo_recount3_bulk_dea_paths_status.flag"),
    ("results/module3/m3_repo_recount3_bulk_dea_integration_stub.json", "m3_sc.repo_recount3_bulk_dea_integration_stub"),
    ("results/module3/m3_repo_recount3_bulk_dea_integration_stub.flag", "m3_sc.repo_recount3_bulk_dea_integration_stub.flag"),
    ("results/module3/m3_repo_bulk_welch_ols_dea_paths_status.json", "m3_sc.repo_bulk_welch_ols_dea_paths_status"),
    ("results/module3/m3_repo_bulk_welch_ols_dea_paths_status.flag", "m3_sc.repo_bulk_welch_ols_dea_paths_status.flag"),
    ("results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.json", "m3_sc.repo_bulk_welch_ols_dea_integration_stub"),
    ("results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.flag", "m3_sc.repo_bulk_welch_ols_dea_integration_stub.flag"),
    ("results/module3/m3_repo_toil_vs_recount3_correlation_paths_status.json", "m3_sc.repo_toil_vs_recount3_correlation_paths_status"),
    ("results/module3/m3_repo_toil_vs_recount3_correlation_paths_status.flag", "m3_sc.repo_toil_vs_recount3_correlation_paths_status.flag"),
    ("results/module3/m3_repo_toil_vs_recount3_correlation_integration_stub.json", "m3_sc.repo_toil_vs_recount3_correlation_integration_stub"),
    ("results/module3/m3_repo_toil_vs_recount3_correlation_integration_stub.flag", "m3_sc.repo_toil_vs_recount3_correlation_integration_stub.flag"),
    ("results/module3/m3_repo_stratified_bulk_dea_paths_status.json", "m3_sc.repo_stratified_bulk_dea_paths_status"),
    ("results/module3/m3_repo_stratified_bulk_dea_paths_status.flag", "m3_sc.repo_stratified_bulk_dea_paths_status.flag"),
    ("results/module3/m3_repo_stratified_bulk_dea_integration_stub.json", "m3_sc.repo_stratified_bulk_dea_integration_stub"),
    ("results/module3/m3_repo_stratified_bulk_dea_integration_stub.flag", "m3_sc.repo_stratified_bulk_dea_integration_stub.flag"),
    ("results/module3/m3_repo_cohort_verhaak_subtype_paths_status.json", "m3_sc.repo_cohort_verhaak_subtype_paths_status"),
    ("results/module3/m3_repo_cohort_verhaak_subtype_paths_status.flag", "m3_sc.repo_cohort_verhaak_subtype_paths_status.flag"),
    ("results/module3/m3_repo_cohort_verhaak_subtype_integration_stub.json", "m3_sc.repo_cohort_verhaak_subtype_integration_stub"),
    ("results/module3/m3_repo_cohort_verhaak_subtype_integration_stub.flag", "m3_sc.repo_cohort_verhaak_subtype_integration_stub.flag"),
    ("results/module3/m3_repo_bulk_join_provenance_paths_status.json", "m3_sc.repo_bulk_join_provenance_paths_status"),
    ("results/module3/m3_repo_bulk_join_provenance_paths_status.flag", "m3_sc.repo_bulk_join_provenance_paths_status.flag"),
    ("results/module3/m3_repo_bulk_join_provenance_integration_stub.json", "m3_sc.repo_bulk_join_provenance_integration_stub"),
    ("results/module3/m3_repo_bulk_join_provenance_integration_stub.flag", "m3_sc.repo_bulk_join_provenance_integration_stub.flag"),
    ("results/module3/m3_repo_gdc_star_tcga_gbm_dea_paths_status.json", "m3_sc.repo_gdc_star_tcga_gbm_dea_paths_status"),
    ("results/module3/m3_repo_gdc_star_tcga_gbm_dea_paths_status.flag", "m3_sc.repo_gdc_star_tcga_gbm_dea_paths_status.flag"),
    ("results/module3/m3_repo_gdc_star_tcga_gbm_dea_integration_stub.json", "m3_sc.repo_gdc_star_tcga_gbm_dea_integration_stub"),
    ("results/module3/m3_repo_gdc_star_tcga_gbm_dea_integration_stub.flag", "m3_sc.repo_gdc_star_tcga_gbm_dea_integration_stub.flag"),
    ("results/module5/lincs_disease_signature_welch_entrez.tsv", "m5.lincs_connectivity.signature_welch_entrez_tsv"),
    ("results/module5/lincs_disease_signature_ols_entrez.tsv", "m5.lincs_connectivity.signature_ols_entrez_tsv"),
    (
        "results/module5/lincs_disease_signature_recount3_pydeseq2_entrez.tsv",
        "m5.lincs_connectivity.signature_recount3_pydeseq2_entrez_tsv",
    ),
    (
        "results/module5/lincs_disease_signature_recount3_edger_entrez.tsv",
        "m5.lincs_connectivity.signature_recount3_edger_entrez_tsv",
    ),
    ("results/module5/lincs_disease_signature_provenance.json", "m5.lincs_connectivity.signature_provenance"),
    ("results/module5/lincs_disease_signature.flag", "m5.lincs_connectivity.signature_flag"),
    ("results/module5/lincs_stratified_signature.flag", "m5.lincs_connectivity.stratified_signature_flag"),
    (
        "results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Classical_entrez.tsv",
        "m5.lincs_connectivity.stratified.welch.classical_entrez_tsv",
    ),
    (
        "results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Mesenchymal_entrez.tsv",
        "m5.lincs_connectivity.stratified.welch.mesenchymal_entrez_tsv",
    ),
    (
        "results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Neural_entrez.tsv",
        "m5.lincs_connectivity.stratified.welch.neural_entrez_tsv",
    ),
    (
        "results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Proneural_entrez.tsv",
        "m5.lincs_connectivity.stratified.welch.proneural_entrez_tsv",
    ),
    (
        "results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Classical_entrez.tsv",
        "m5.lincs_connectivity.stratified.ols.classical_entrez_tsv",
    ),
    (
        "results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Mesenchymal_entrez.tsv",
        "m5.lincs_connectivity.stratified.ols.mesenchymal_entrez_tsv",
    ),
    (
        "results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Neural_entrez.tsv",
        "m5.lincs_connectivity.stratified.ols.neural_entrez_tsv",
    ),
    (
        "results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Proneural_entrez.tsv",
        "m5.lincs_connectivity.stratified.ols.proneural_entrez_tsv",
    ),
    ("results/module5/cmap_tooling_scan.json", "m5.lincs_connectivity.cmap_tooling_scan"),
    ("results/module5/lincs_connectivity_readiness.json", "m5.lincs_connectivity.connectivity_readiness"),
    ("results/module5/lincs_signature_pack.json", "m5.lincs_connectivity.signature_pack"),
    ("results/module5/srges_integration_stub.json", "m5.lincs_connectivity.srges_integration_stub"),
    (
        "results/module3/m3_repo_module5_lincs_connectivity_paths_status.json",
        "m3_sc.repo_module5_lincs_connectivity_paths_status",
    ),
    (
        "results/module3/m3_repo_module5_lincs_connectivity_paths_status.flag",
        "m3_sc.repo_module5_lincs_connectivity_paths_status.flag",
    ),
    (
        "results/module3/m3_repo_module5_lincs_connectivity_integration_stub.json",
        "m3_sc.repo_module5_lincs_connectivity_integration_stub",
    ),
    (
        "results/module3/m3_repo_module5_lincs_connectivity_integration_stub.flag",
        "m3_sc.repo_module5_lincs_connectivity_integration_stub.flag",
    ),
    ("results/module5/m5_l1000_data_paths_status.json", "m5.l1000_data.paths_status_json"),
    ("results/module5/m5_l1000_data_paths_status.flag", "m5.l1000_data.paths_status_flag"),
    ("results/module5/m5_l1000_data_integration_stub.json", "m5.l1000_data.integration_stub_json"),
    ("results/module5/m5_l1000_data_integration_stub.flag", "m5.l1000_data.integration_stub_flag"),
    (
        "results/module3/m3_repo_module5_l1000_data_paths_status.json",
        "m3_sc.repo_module5_l1000_data_paths_status",
    ),
    (
        "results/module3/m3_repo_module5_l1000_data_paths_status.flag",
        "m3_sc.repo_module5_l1000_data_paths_status.flag",
    ),
    (
        "results/module3/m3_repo_module5_l1000_data_integration_stub.json",
        "m3_sc.repo_module5_l1000_data_integration_stub",
    ),
    (
        "results/module3/m3_repo_module5_l1000_data_integration_stub.flag",
        "m3_sc.repo_module5_l1000_data_integration_stub.flag",
    ),
    ("results/module5/m5_modality_paths_status.json", "m5.modality.paths_status_json"),
    ("results/module5/m5_modality_paths_status.flag", "m5.modality.paths_status_flag"),
    ("results/module5/m5_modality_integration_stub.json", "m5.modality.integration_stub_json"),
    ("results/module5/m5_modality_integration_stub.flag", "m5.modality.integration_stub_flag"),
    ("results/module3/m3_repo_module5_modality_paths_status.json", "m3_sc.repo_module5_modality_paths_status"),
    ("results/module3/m3_repo_module5_modality_paths_status.flag", "m3_sc.repo_module5_modality_paths_status.flag"),
    (
        "results/module3/m3_repo_module5_modality_integration_stub.json",
        "m3_sc.repo_module5_modality_integration_stub",
    ),
    (
        "results/module3/m3_repo_module5_modality_integration_stub.flag",
        "m3_sc.repo_module5_modality_integration_stub.flag",
    ),
    ("results/module5/m5_srges_output_paths_status.json", "m5.srges_output.paths_status_json"),
    ("results/module5/m5_srges_output_paths_status.flag", "m5.srges_output.paths_status_flag"),
    ("results/module5/m5_srges_output_integration_stub.json", "m5.srges_output.integration_stub_json"),
    ("results/module5/m5_srges_output_integration_stub.flag", "m5.srges_output.integration_stub_flag"),
    (
        "results/module3/m3_repo_module5_srges_output_paths_status.json",
        "m3_sc.repo_module5_srges_output_paths_status",
    ),
    (
        "results/module3/m3_repo_module5_srges_output_paths_status.flag",
        "m3_sc.repo_module5_srges_output_paths_status.flag",
    ),
    (
        "results/module3/m3_repo_module5_srges_output_integration_stub.json",
        "m3_sc.repo_module5_srges_output_integration_stub",
    ),
    (
        "results/module3/m3_repo_module5_srges_output_integration_stub.flag",
        "m3_sc.repo_module5_srges_output_integration_stub.flag",
    ),
    (
        "results/module5/m5_lincs_connectivity_mirror_paths_status.json",
        "m5.lincs_connectivity_mirror.paths_status_json",
    ),
    (
        "results/module5/m5_lincs_connectivity_mirror_paths_status.flag",
        "m5.lincs_connectivity_mirror.paths_status_flag",
    ),
    (
        "results/module5/m5_lincs_connectivity_mirror_integration_stub.json",
        "m5.lincs_connectivity_mirror.integration_stub_json",
    ),
    (
        "results/module5/m5_lincs_connectivity_mirror_integration_stub.flag",
        "m5.lincs_connectivity_mirror.integration_stub_flag",
    ),
    (
        "results/module3/m3_repo_module5_lincs_connectivity_mirror_paths_status.json",
        "m3_sc.repo_module5_lincs_connectivity_mirror_paths_status",
    ),
    (
        "results/module3/m3_repo_module5_lincs_connectivity_mirror_paths_status.flag",
        "m3_sc.repo_module5_lincs_connectivity_mirror_paths_status.flag",
    ),
    (
        "results/module3/m3_repo_module5_lincs_connectivity_mirror_integration_stub.json",
        "m3_sc.repo_module5_lincs_connectivity_mirror_integration_stub",
    ),
    (
        "results/module3/m3_repo_module5_lincs_connectivity_mirror_integration_stub.flag",
        "m3_sc.repo_module5_lincs_connectivity_mirror_integration_stub.flag",
    ),
    ("results/module4/wgcna_hub_expr_subset.parquet", "m4.hub_gsea.wgcna_expr_subset_parquet"),
    ("results/module4/wgcna_hub_expr_subset_long.tsv", "m4.hub_gsea.wgcna_expr_subset_long_tsv"),
    ("results/module4/wgcna_hub_expr_subset_provenance.json", "m4.hub_gsea.wgcna_expr_subset_provenance"),
    (
        "results/module4/wgcna_hub_expr_subset_recount3_only.parquet",
        "m4.hub_gsea.wgcna_expr_subset_recount3_only_parquet",
    ),
    (
        "results/module4/wgcna_hub_expr_subset_recount3_only_long.tsv",
        "m4.hub_gsea.wgcna_expr_subset_recount3_only_long_tsv",
    ),
    (
        "results/module4/wgcna_hub_expr_subset_recount3_only_provenance.json",
        "m4.hub_gsea.wgcna_expr_subset_recount3_only_provenance",
    ),
    ("results/module4/wgcna_hub_sample_traits.tsv", "m4.hub_gsea.wgcna_sample_traits_tsv"),
    (
        "results/module4/wgcna_hub_sample_traits_provenance.json",
        "m4.hub_gsea.wgcna_sample_traits_provenance",
    ),
    (
        "results/module4/wgcna_hub_sample_traits_recount3_only.tsv",
        "m4.hub_gsea.wgcna_sample_traits_recount3_only_tsv",
    ),
    (
        "results/module4/wgcna_hub_sample_traits_recount3_only_provenance.json",
        "m4.hub_gsea.wgcna_sample_traits_recount3_only_provenance",
    ),
    ("results/module4/wgcna_hub_gene_overlap_summary.json", "m4.hub_gsea.wgcna_gene_overlap_summary"),
    (
        "results/module4/stratified_string_export_provenance.json",
        "m4.hub_gsea.stratified_string_export_provenance",
    ),
    (
        "results/module4/gsea/dea_welch_signed_neg_log10_p.rnk",
        "m4.hub_gsea.gsea_welch_signed_neg_log10_p_rnk",
    ),
    (
        "results/module4/gsea/dea_ols_signed_neg_log10_p.rnk",
        "m4.hub_gsea.gsea_ols_signed_neg_log10_p_rnk",
    ),
    (
        "results/module4/gsea/recount3_pydeseq2_signed_neg_log10_p.rnk",
        "m4.hub_gsea.gsea_recount3_pydeseq2_signed_neg_log10_p_rnk",
    ),
    (
        "results/module4/gsea/recount3_edger_signed_neg_log10_p.rnk",
        "m4.hub_gsea.gsea_recount3_edger_signed_neg_log10_p_rnk",
    ),
    ("results/module4/gsea_prerank_export_provenance.json", "m4.hub_gsea.gsea_prerank_export_provenance"),
    ("results/module4/gsea_stratified_prerank.flag", "m4.hub_gsea.gsea_stratified_prerank_flag"),
    (
        "results/module4/gsea/stratified/welch_integrated/dea_welch_subtype_Classical_signed_neg_log10_p.rnk",
        "m4.hub_gsea.stratified_welch.classical_rnk",
    ),
    (
        "results/module4/gsea/stratified/welch_integrated/dea_welch_subtype_Mesenchymal_signed_neg_log10_p.rnk",
        "m4.hub_gsea.stratified_welch.mesenchymal_rnk",
    ),
    (
        "results/module4/gsea/stratified/welch_integrated/dea_welch_subtype_Neural_signed_neg_log10_p.rnk",
        "m4.hub_gsea.stratified_welch.neural_rnk",
    ),
    (
        "results/module4/gsea/stratified/welch_integrated/dea_welch_subtype_Proneural_signed_neg_log10_p.rnk",
        "m4.hub_gsea.stratified_welch.proneural_rnk",
    ),
    (
        "results/module4/gsea/stratified/ols_integrated/dea_ols_subtype_Classical_signed_neg_log10_p.rnk",
        "m4.hub_gsea.stratified_ols.classical_rnk",
    ),
    (
        "results/module4/gsea/stratified/ols_integrated/dea_ols_subtype_Mesenchymal_signed_neg_log10_p.rnk",
        "m4.hub_gsea.stratified_ols.mesenchymal_rnk",
    ),
    (
        "results/module4/gsea/stratified/ols_integrated/dea_ols_subtype_Neural_signed_neg_log10_p.rnk",
        "m4.hub_gsea.stratified_ols.neural_rnk",
    ),
    (
        "results/module4/gsea/stratified/ols_integrated/dea_ols_subtype_Proneural_signed_neg_log10_p.rnk",
        "m4.hub_gsea.stratified_ols.proneural_rnk",
    ),
    ("results/module3/m3_repo_module4_hub_gsea_paths_status.json", "m3_sc.repo_module4_hub_gsea_paths_status"),
    ("results/module3/m3_repo_module4_hub_gsea_paths_status.flag", "m3_sc.repo_module4_hub_gsea_paths_status.flag"),
    (
        "results/module3/m3_repo_module4_hub_gsea_integration_stub.json",
        "m3_sc.repo_module4_hub_gsea_integration_stub",
    ),
    (
        "results/module3/m3_repo_module4_hub_gsea_integration_stub.flag",
        "m3_sc.repo_module4_hub_gsea_integration_stub.flag",
    ),
    ("results/module4/m4_network_paths_status.json", "m4.network.paths_status_json"),
    ("results/module4/m4_network_paths_status.flag", "m4.network.paths_status_flag"),
    ("results/module4/m4_network_integration_stub.json", "m4.network.integration_stub_json"),
    ("results/module4/m4_network_integration_stub.flag", "m4.network.integration_stub_flag"),
    ("results/module3/m3_repo_module4_network_paths_status.json", "m3_sc.repo_module4_network_paths_status"),
    ("results/module3/m3_repo_module4_network_paths_status.flag", "m3_sc.repo_module4_network_paths_status.flag"),
    (
        "results/module3/m3_repo_module4_network_integration_stub.json",
        "m3_sc.repo_module4_network_integration_stub",
    ),
    (
        "results/module3/m3_repo_module4_network_integration_stub.flag",
        "m3_sc.repo_module4_network_integration_stub.flag",
    ),
    ("results/module4/m4_string_cache_paths_status.json", "m4.string_cache.paths_status_json"),
    ("results/module4/m4_string_cache_paths_status.flag", "m4.string_cache.paths_status_flag"),
    ("results/module4/m4_string_cache_integration_stub.json", "m4.string_cache.integration_stub_json"),
    ("results/module4/m4_string_cache_integration_stub.flag", "m4.string_cache.integration_stub_flag"),
    (
        "results/module3/m3_repo_module4_string_cache_paths_status.json",
        "m3_sc.repo_module4_string_cache_paths_status",
    ),
    (
        "results/module3/m3_repo_module4_string_cache_paths_status.flag",
        "m3_sc.repo_module4_string_cache_paths_status.flag",
    ),
    (
        "results/module3/m3_repo_module4_string_cache_integration_stub.json",
        "m3_sc.repo_module4_string_cache_integration_stub",
    ),
    (
        "results/module3/m3_repo_module4_string_cache_integration_stub.flag",
        "m3_sc.repo_module4_string_cache_integration_stub.flag",
    ),
    (
        "results/module4/m4_pathway_database_mirror_paths_status.json",
        "m4.pathway_database_mirror.paths_status_json",
    ),
    (
        "results/module4/m4_pathway_database_mirror_paths_status.flag",
        "m4.pathway_database_mirror.paths_status_flag",
    ),
    (
        "results/module4/m4_pathway_database_mirror_integration_stub.json",
        "m4.pathway_database_mirror.integration_stub_json",
    ),
    (
        "results/module4/m4_pathway_database_mirror_integration_stub.flag",
        "m4.pathway_database_mirror.integration_stub_flag",
    ),
    (
        "results/module3/m3_repo_module4_pathway_database_mirror_paths_status.json",
        "m3_sc.repo_module4_pathway_database_mirror_paths_status",
    ),
    (
        "results/module3/m3_repo_module4_pathway_database_mirror_paths_status.flag",
        "m3_sc.repo_module4_pathway_database_mirror_paths_status.flag",
    ),
    (
        "results/module3/m3_repo_module4_pathway_database_mirror_integration_stub.json",
        "m3_sc.repo_module4_pathway_database_mirror_integration_stub",
    ),
    (
        "results/module3/m3_repo_module4_pathway_database_mirror_integration_stub.flag",
        "m3_sc.repo_module4_pathway_database_mirror_integration_stub.flag",
    ),
    ("results/module4/m4_gsea_mirror_paths_status.json", "m4.gsea_mirror.paths_status_json"),
    ("results/module4/m4_gsea_mirror_paths_status.flag", "m4.gsea_mirror.paths_status_flag"),
    ("results/module4/m4_gsea_mirror_integration_stub.json", "m4.gsea_mirror.integration_stub_json"),
    ("results/module4/m4_gsea_mirror_integration_stub.flag", "m4.gsea_mirror.integration_stub_flag"),
    ("results/module3/m3_repo_module4_gsea_mirror_paths_status.json", "m3_sc.repo_module4_gsea_mirror_paths_status"),
    ("results/module3/m3_repo_module4_gsea_mirror_paths_status.flag", "m3_sc.repo_module4_gsea_mirror_paths_status.flag"),
    (
        "results/module3/m3_repo_module4_gsea_mirror_integration_stub.json",
        "m3_sc.repo_module4_gsea_mirror_integration_stub",
    ),
    (
        "results/module3/m3_repo_module4_gsea_mirror_integration_stub.flag",
        "m3_sc.repo_module4_gsea_mirror_integration_stub.flag",
    ),
    ("results/module7/gts_candidate_table_welch_stub.tsv", "m7.gts_stub.global_welch_tsv"),
    ("results/module7/glioma_target_tier1_welch.tsv", "m7.glioma_target.tier1_welch_tsv"),
    ("results/module7/gts_candidate_table_ols_stub.tsv", "m7.gts_stub.global_ols_tsv"),
    (
        "results/module7/gts_candidate_table_recount3_pydeseq2_stub.tsv",
        "m7.gts_stub.global_recount3_pydeseq2_tsv",
    ),
    (
        "results/module7/gts_candidate_table_recount3_edger_stub.tsv",
        "m7.gts_stub.global_recount3_edger_tsv",
    ),
    ("results/module7/gts_candidate_stub_provenance.json", "m7.gts_stub.candidate_provenance"),
    ("results/module7/gts_candidate_stub.flag", "m7.gts_stub.candidate_flag"),
    ("results/module7/gts_stratified_candidate_stub.flag", "m7.gts_stub.stratified_candidate_flag"),
    (
        "results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Classical_gts_stub.tsv",
        "m7.gts_stub.stratified.welch.classical_tsv",
    ),
    (
        "results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Mesenchymal_gts_stub.tsv",
        "m7.gts_stub.stratified.welch.mesenchymal_tsv",
    ),
    (
        "results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Neural_gts_stub.tsv",
        "m7.gts_stub.stratified.welch.neural_tsv",
    ),
    (
        "results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Proneural_gts_stub.tsv",
        "m7.gts_stub.stratified.welch.proneural_tsv",
    ),
    (
        "results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Classical_gts_stub.tsv",
        "m7.gts_stub.stratified.ols.classical_tsv",
    ),
    (
        "results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Mesenchymal_gts_stub.tsv",
        "m7.gts_stub.stratified.ols.mesenchymal_tsv",
    ),
    (
        "results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Neural_gts_stub.tsv",
        "m7.gts_stub.stratified.ols.neural_tsv",
    ),
    (
        "results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Proneural_gts_stub.tsv",
        "m7.gts_stub.stratified.ols.proneural_tsv",
    ),
    ("results/module7/gts_validation_integration_stub.json", "m7.gts_validation_integration_stub"),
    ("results/module7/gts_validation_integration_stub.flag", "m7.gts_validation_integration_stub.flag"),
    ("results/module3/m3_repo_module7_gts_stub_paths_status.json", "m3_sc.repo_module7_gts_stub_paths_status"),
    ("results/module3/m3_repo_module7_gts_stub_paths_status.flag", "m3_sc.repo_module7_gts_stub_paths_status.flag"),
    (
        "results/module3/m3_repo_module7_gts_stub_integration_stub.json",
        "m3_sc.repo_module7_gts_stub_integration_stub",
    ),
    (
        "results/module3/m3_repo_module7_gts_stub_integration_stub.flag",
        "m3_sc.repo_module7_gts_stub_integration_stub.flag",
    ),
    ("results/module7/m7_validation_paths_status.json", "m7.validation.paths_status_json"),
    ("results/module7/m7_validation_paths_status.flag", "m7.validation.paths_status_flag"),
    ("results/module7/m7_validation_integration_stub.json", "m7.validation.integration_stub_json"),
    ("results/module7/m7_validation_integration_stub.flag", "m7.validation.integration_stub_flag"),
    ("results/module3/m3_repo_module7_validation_paths_status.json", "m3_sc.repo_module7_validation_paths_status"),
    ("results/module3/m3_repo_module7_validation_paths_status.flag", "m3_sc.repo_module7_validation_paths_status.flag"),
    (
        "results/module3/m3_repo_module7_validation_integration_stub.json",
        "m3_sc.repo_module7_validation_integration_stub",
    ),
    (
        "results/module3/m3_repo_module7_validation_integration_stub.flag",
        "m3_sc.repo_module7_validation_integration_stub.flag",
    ),
    (
        "results/module7/m7_gts_external_score_mirror_paths_status.json",
        "m7.gts_external_score_mirror.paths_status_json",
    ),
    (
        "results/module7/m7_gts_external_score_mirror_paths_status.flag",
        "m7.gts_external_score_mirror.paths_status_flag",
    ),
    (
        "results/module7/m7_gts_external_score_mirror_integration_stub.json",
        "m7.gts_external_score_mirror.integration_stub_json",
    ),
    (
        "results/module7/m7_gts_external_score_mirror_integration_stub.flag",
        "m7.gts_external_score_mirror.integration_stub_flag",
    ),
    (
        "results/module3/m3_repo_module7_gts_external_score_mirror_paths_status.json",
        "m3_sc.repo_module7_gts_external_score_mirror_paths_status",
    ),
    (
        "results/module3/m3_repo_module7_gts_external_score_mirror_paths_status.flag",
        "m3_sc.repo_module7_gts_external_score_mirror_paths_status.flag",
    ),
    (
        "results/module3/m3_repo_module7_gts_external_score_mirror_integration_stub.json",
        "m3_sc.repo_module7_gts_external_score_mirror_integration_stub",
    ),
    (
        "results/module3/m3_repo_module7_gts_external_score_mirror_integration_stub.flag",
        "m3_sc.repo_module7_gts_external_score_mirror_integration_stub.flag",
    ),
    ("results/module6/structure_druggability_bridge_welch.tsv", "m6.structure_bridge.global_welch_tsv"),
    ("results/module6/structure_druggability_bridge_ols.tsv", "m6.structure_bridge.global_ols_tsv"),
    (
        "results/module6/structure_druggability_bridge_recount3_pydeseq2.tsv",
        "m6.structure_bridge.global_recount3_pydeseq2_tsv",
    ),
    (
        "results/module6/structure_druggability_bridge_recount3_edger.tsv",
        "m6.structure_bridge.global_recount3_edger_tsv",
    ),
    ("results/module6/structure_druggability_bridge_provenance.json", "m6.structure_bridge.provenance"),
    ("results/module6/structure_druggability_bridge.flag", "m6.structure_bridge.flag"),
    ("results/module6/structure_druggability_bridge_stratified.flag", "m6.structure_bridge.stratified_flag"),
    (
        "results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Classical_structure_bridge.tsv",
        "m6.structure_bridge.stratified.welch.classical_tsv",
    ),
    (
        "results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Mesenchymal_structure_bridge.tsv",
        "m6.structure_bridge.stratified.welch.mesenchymal_tsv",
    ),
    (
        "results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Neural_structure_bridge.tsv",
        "m6.structure_bridge.stratified.welch.neural_tsv",
    ),
    (
        "results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Proneural_structure_bridge.tsv",
        "m6.structure_bridge.stratified.welch.proneural_tsv",
    ),
    (
        "results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Classical_structure_bridge.tsv",
        "m6.structure_bridge.stratified.ols.classical_tsv",
    ),
    (
        "results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Mesenchymal_structure_bridge.tsv",
        "m6.structure_bridge.stratified.ols.mesenchymal_tsv",
    ),
    (
        "results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Neural_structure_bridge.tsv",
        "m6.structure_bridge.stratified.ols.neural_tsv",
    ),
    (
        "results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Proneural_structure_bridge.tsv",
        "m6.structure_bridge.stratified.ols.proneural_tsv",
    ),
    ("results/module6/structure_admet_integration_stub.json", "m6.structure_admet_integration_stub"),
    ("results/module6/structure_admet_integration_stub.flag", "m6.structure_admet_integration_stub.flag"),
    (
        "results/module3/m3_repo_module6_structure_bridge_paths_status.json",
        "m3_sc.repo_module6_structure_bridge_paths_status",
    ),
    (
        "results/module3/m3_repo_module6_structure_bridge_paths_status.flag",
        "m3_sc.repo_module6_structure_bridge_paths_status.flag",
    ),
    (
        "results/module3/m3_repo_module6_structure_bridge_integration_stub.json",
        "m3_sc.repo_module6_structure_bridge_integration_stub",
    ),
    (
        "results/module3/m3_repo_module6_structure_bridge_integration_stub.flag",
        "m3_sc.repo_module6_structure_bridge_integration_stub.flag",
    ),
    (
        "results/module6/module6_structure_tooling_paths_status.json",
        "m6.structure_tooling.paths_status_json",
    ),
    (
        "results/module6/module6_structure_tooling_paths_status.flag",
        "m6.structure_tooling.paths_status_flag",
    ),
    (
        "results/module3/m3_repo_module6_structure_tooling_paths_status.json",
        "m3_sc.repo_module6_structure_tooling_paths_status",
    ),
    (
        "results/module3/m3_repo_module6_structure_tooling_paths_status.flag",
        "m3_sc.repo_module6_structure_tooling_paths_status.flag",
    ),
    (
        "results/module3/m3_repo_module6_structure_tooling_integration_stub.json",
        "m3_sc.repo_module6_structure_tooling_integration_stub",
    ),
    (
        "results/module3/m3_repo_module6_structure_tooling_integration_stub.flag",
        "m3_sc.repo_module6_structure_tooling_integration_stub.flag",
    ),
    ("results/tooling/vendor_tooling_paths_status.json", "tooling.vendor.paths_status_json"),
    ("results/tooling/vendor_tooling_paths_status.flag", "tooling.vendor.paths_status_flag"),
    ("results/tooling/vendor_tooling_integration_stub.json", "tooling.vendor.integration_stub_json"),
    ("results/tooling/vendor_tooling_integration_stub.flag", "tooling.vendor.integration_stub_flag"),
    ("results/module3/m3_repo_tooling_vendor_paths_status.json", "m3_sc.repo_tooling_vendor_paths_status"),
    ("results/module3/m3_repo_tooling_vendor_paths_status.flag", "m3_sc.repo_tooling_vendor_paths_status.flag"),
    (
        "results/module3/m3_repo_tooling_vendor_integration_stub.json",
        "m3_sc.repo_tooling_vendor_integration_stub",
    ),
    (
        "results/module3/m3_repo_tooling_vendor_integration_stub.flag",
        "m3_sc.repo_tooling_vendor_integration_stub.flag",
    ),
    ("results/module6/m6_docking_output_paths_status.json", "m6.docking_output.paths_status_json"),
    ("results/module6/m6_docking_output_paths_status.flag", "m6.docking_output.paths_status_flag"),
    ("results/module6/m6_docking_output_integration_stub.json", "m6.docking_output.integration_stub_json"),
    ("results/module6/m6_docking_output_integration_stub.flag", "m6.docking_output.integration_stub_flag"),
    (
        "results/module3/m3_repo_module6_docking_output_paths_status.json",
        "m3_sc.repo_module6_docking_output_paths_status",
    ),
    (
        "results/module3/m3_repo_module6_docking_output_paths_status.flag",
        "m3_sc.repo_module6_docking_output_paths_status.flag",
    ),
    (
        "results/module3/m3_repo_module6_docking_output_integration_stub.json",
        "m3_sc.repo_module6_docking_output_integration_stub",
    ),
    (
        "results/module3/m3_repo_module6_docking_output_integration_stub.flag",
        "m3_sc.repo_module6_docking_output_integration_stub.flag",
    ),
    ("results/module6/m6_toxicity_paths_status.json", "m6.toxicity.paths_status_json"),
    ("results/module6/m6_toxicity_paths_status.flag", "m6.toxicity.paths_status_flag"),
    ("results/module6/m6_toxicity_integration_stub.json", "m6.toxicity.integration_stub_json"),
    ("results/module6/m6_toxicity_integration_stub.flag", "m6.toxicity.integration_stub_flag"),
    (
        "results/module3/m3_repo_module6_toxicity_paths_status.json",
        "m3_sc.repo_module6_toxicity_paths_status",
    ),
    (
        "results/module3/m3_repo_module6_toxicity_paths_status.flag",
        "m3_sc.repo_module6_toxicity_paths_status.flag",
    ),
    (
        "results/module3/m3_repo_module6_toxicity_integration_stub.json",
        "m3_sc.repo_module6_toxicity_integration_stub",
    ),
    (
        "results/module3/m3_repo_module6_toxicity_integration_stub.flag",
        "m3_sc.repo_module6_toxicity_integration_stub.flag",
    ),
    (
        "results/module6/m6_compound_library_mirror_paths_status.json",
        "m6.compound_library_mirror.paths_status_json",
    ),
    (
        "results/module6/m6_compound_library_mirror_paths_status.flag",
        "m6.compound_library_mirror.paths_status_flag",
    ),
    (
        "results/module6/m6_compound_library_mirror_integration_stub.json",
        "m6.compound_library_mirror.integration_stub_json",
    ),
    (
        "results/module6/m6_compound_library_mirror_integration_stub.flag",
        "m6.compound_library_mirror.integration_stub_flag",
    ),
    (
        "results/module3/m3_repo_module6_compound_library_mirror_paths_status.json",
        "m3_sc.repo_module6_compound_library_mirror_paths_status",
    ),
    (
        "results/module3/m3_repo_module6_compound_library_mirror_paths_status.flag",
        "m3_sc.repo_module6_compound_library_mirror_paths_status.flag",
    ),
    (
        "results/module3/m3_repo_module6_compound_library_mirror_integration_stub.json",
        "m3_sc.repo_module6_compound_library_mirror_integration_stub",
    ),
    (
        "results/module3/m3_repo_module6_compound_library_mirror_integration_stub.flag",
        "m3_sc.repo_module6_compound_library_mirror_integration_stub.flag",
    ),
    ("results/module3/maf_annotation_integration_stub.json", "m2_2.maf_annotation_integration_stub"),
    ("results/module3/maf_annotation_integration_stub.flag", "m2_2.maf_annotation_integration_stub.flag"),
    ("results/module3/m3_repo_m2_maf_annotation_paths_status.json", "m3_sc.repo_m2_maf_annotation_paths_status"),
    ("results/module3/m3_repo_m2_maf_annotation_paths_status.flag", "m3_sc.repo_m2_maf_annotation_paths_status.flag"),
    ("results/module3/m3_repo_m2_maf_annotation_integration_stub.json", "m3_sc.repo_m2_maf_annotation_integration_stub"),
    ("results/module3/m3_repo_m2_maf_annotation_integration_stub.flag", "m3_sc.repo_m2_maf_annotation_integration_stub.flag"),
    ("results/module3/m2_2_variant_annotation_paths_status.json", "m2_2.variant_annotation_paths_status"),
    ("results/module3/m2_2_variant_annotation_paths_status.flag", "m2_2.variant_annotation_paths_status.flag"),
    ("results/module3/m2_2_variant_annotation_integration_stub.json", "m2_2.variant_annotation_integration_stub"),
    ("results/module3/m2_2_variant_annotation_integration_stub.flag", "m2_2.variant_annotation_integration_stub.flag"),
    ("results/module3/m2_2_depmap_mirror_paths_status.json", "m2_2.depmap_mirror_paths_status"),
    ("results/module3/m2_2_depmap_mirror_paths_status.flag", "m2_2.depmap_mirror_paths_status.flag"),
    ("results/module3/m2_2_depmap_mirror_integration_stub.json", "m2_2.depmap_mirror_integration_stub"),
    ("results/module3/m2_2_depmap_mirror_integration_stub.flag", "m2_2.depmap_mirror_integration_stub.flag"),
    ("results/module3/m2_2_maf_mutsig_mirror_paths_status.json", "m2_2.maf_mutsig_mirror_paths_status"),
    ("results/module3/m2_2_maf_mutsig_mirror_paths_status.flag", "m2_2.maf_mutsig_mirror_paths_status.flag"),
    ("results/module3/m2_2_maf_mutsig_mirror_integration_stub.json", "m2_2.maf_mutsig_mirror_integration_stub"),
    ("results/module3/m2_2_maf_mutsig_mirror_integration_stub.flag", "m2_2.maf_mutsig_mirror_integration_stub.flag"),
    ("results/module3/m2_2_outline_driver_mirror_paths_status.json", "m2_2.outline_driver_mirror_paths_status"),
    ("results/module3/m2_2_outline_driver_mirror_paths_status.flag", "m2_2.outline_driver_mirror_paths_status.flag"),
    ("results/module3/m2_2_outline_driver_mirror_integration_stub.json", "m2_2.outline_driver_mirror_integration_stub"),
    ("results/module3/m2_2_outline_driver_mirror_integration_stub.flag", "m2_2.outline_driver_mirror_integration_stub.flag"),
    ("results/module3/m2_cptac_methylation_paths_status.json", "m2_1.cptac_methylation_paths_status"),
    ("results/module3/m2_cptac_methylation_paths_status.flag", "m2_1.cptac_methylation_paths_status.flag"),
    ("results/module3/m2_cptac_methylation_integration_stub.json", "m2_1.cptac_methylation_integration_stub"),
    ("results/module3/m2_cptac_methylation_integration_stub.flag", "m2_1.cptac_methylation_integration_stub.flag"),
    ("results/module3/m2_1_star_pairing_paths_status.json", "m2_1.star_pairing_paths_status"),
    ("results/module3/m2_1_star_pairing_paths_status.flag", "m2_1.star_pairing_paths_status.flag"),
    ("results/module3/m2_1_star_pairing_integration_stub.json", "m2_1.star_pairing_integration_stub"),
    ("results/module3/m2_1_star_pairing_integration_stub.flag", "m2_1.star_pairing_integration_stub.flag"),
    ("results/module3/m2_1_recount3_mirror_paths_status.json", "m2_1.recount3_mirror_paths_status"),
    ("results/module3/m2_1_recount3_mirror_paths_status.flag", "m2_1.recount3_mirror_paths_status.flag"),
    ("results/module3/m2_1_recount3_mirror_integration_stub.json", "m2_1.recount3_mirror_integration_stub"),
    ("results/module3/m2_1_recount3_mirror_integration_stub.flag", "m2_1.recount3_mirror_integration_stub.flag"),
    ("results/module3/m2_1_toil_xena_hub_paths_status.json", "m2_1.toil_xena_hub_paths_status"),
    ("results/module3/m2_1_toil_xena_hub_paths_status.flag", "m2_1.toil_xena_hub_paths_status.flag"),
    ("results/module3/m2_1_toil_xena_hub_integration_stub.json", "m2_1.toil_xena_hub_integration_stub"),
    ("results/module3/m2_1_toil_xena_hub_integration_stub.flag", "m2_1.toil_xena_hub_integration_stub.flag"),
    ("results/module3/m2_movics_paths_status.json", "m2_3.movics_paths_status"),
    ("results/module3/m2_movics_paths_status.flag", "m2_3.movics_paths_status.flag"),
    ("results/module3/m2_movics_integration_stub.json", "m2_3.movics_integration_stub"),
    ("results/module3/m2_movics_integration_stub.flag", "m2_3.movics_integration_stub.flag"),
    ("results/module3/m2_3_immune_tme_mirror_paths_status.json", "m2_3.immune_tme_mirror_paths_status"),
    ("results/module3/m2_3_immune_tme_mirror_paths_status.flag", "m2_3.immune_tme_mirror_paths_status.flag"),
    ("results/module3/m2_3_immune_tme_mirror_integration_stub.json", "m2_3.immune_tme_mirror_integration_stub"),
    ("results/module3/m2_3_immune_tme_mirror_integration_stub.flag", "m2_3.immune_tme_mirror_integration_stub.flag"),
    ("results/module3/m3_repo_m2_cptac_methylation_paths_status.json", "m3_sc.repo_m2_cptac_methylation_paths_status"),
    ("results/module3/m3_repo_m2_cptac_methylation_paths_status.flag", "m3_sc.repo_m2_cptac_methylation_paths_status.flag"),
    ("results/module3/m3_repo_m2_cptac_methylation_integration_stub.json", "m3_sc.repo_m2_cptac_methylation_integration_stub"),
    ("results/module3/m3_repo_m2_cptac_methylation_integration_stub.flag", "m3_sc.repo_m2_cptac_methylation_integration_stub.flag"),
    ("results/module3/m3_repo_m2_1_star_pairing_paths_status.json", "m3_sc.repo_m2_1_star_pairing_paths_status"),
    ("results/module3/m3_repo_m2_1_star_pairing_paths_status.flag", "m3_sc.repo_m2_1_star_pairing_paths_status.flag"),
    ("results/module3/m3_repo_m2_1_star_pairing_integration_stub.json", "m3_sc.repo_m2_1_star_pairing_integration_stub"),
    ("results/module3/m3_repo_m2_1_star_pairing_integration_stub.flag", "m3_sc.repo_m2_1_star_pairing_integration_stub.flag"),
    ("results/module3/m3_repo_m2_1_recount3_mirror_paths_status.json", "m3_sc.repo_m2_1_recount3_mirror_paths_status"),
    ("results/module3/m3_repo_m2_1_recount3_mirror_paths_status.flag", "m3_sc.repo_m2_1_recount3_mirror_paths_status.flag"),
    ("results/module3/m3_repo_m2_1_recount3_mirror_integration_stub.json", "m3_sc.repo_m2_1_recount3_mirror_integration_stub"),
    ("results/module3/m3_repo_m2_1_recount3_mirror_integration_stub.flag", "m3_sc.repo_m2_1_recount3_mirror_integration_stub.flag"),
    ("results/module3/m3_repo_m2_1_toil_xena_hub_paths_status.json", "m3_sc.repo_m2_1_toil_xena_hub_paths_status"),
    ("results/module3/m3_repo_m2_1_toil_xena_hub_paths_status.flag", "m3_sc.repo_m2_1_toil_xena_hub_paths_status.flag"),
    ("results/module3/m3_repo_m2_1_toil_xena_hub_integration_stub.json", "m3_sc.repo_m2_1_toil_xena_hub_integration_stub"),
    ("results/module3/m3_repo_m2_1_toil_xena_hub_integration_stub.flag", "m3_sc.repo_m2_1_toil_xena_hub_integration_stub.flag"),
    ("results/module3/m3_repo_m2_movics_paths_status.json", "m3_sc.repo_m2_movics_paths_status"),
    ("results/module3/m3_repo_m2_movics_paths_status.flag", "m3_sc.repo_m2_movics_paths_status.flag"),
    ("results/module3/m3_repo_m2_movics_integration_stub.json", "m3_sc.repo_m2_movics_integration_stub"),
    ("results/module3/m3_repo_m2_movics_integration_stub.flag", "m3_sc.repo_m2_movics_integration_stub.flag"),
    ("results/module3/m3_repo_m2_3_immune_tme_mirror_paths_status.json", "m3_sc.repo_m2_3_immune_tme_mirror_paths_status"),
    ("results/module3/m3_repo_m2_3_immune_tme_mirror_paths_status.flag", "m3_sc.repo_m2_3_immune_tme_mirror_paths_status.flag"),
    ("results/module3/m3_repo_m2_3_immune_tme_mirror_integration_stub.json", "m3_sc.repo_m2_3_immune_tme_mirror_integration_stub"),
    ("results/module3/m3_repo_m2_3_immune_tme_mirror_integration_stub.flag", "m3_sc.repo_m2_3_immune_tme_mirror_integration_stub.flag"),
    ("results/module3/m3_repo_m2_2_variant_annotation_paths_status.json", "m3_sc.repo_m2_2_variant_annotation_paths_status"),
    ("results/module3/m3_repo_m2_2_variant_annotation_paths_status.flag", "m3_sc.repo_m2_2_variant_annotation_paths_status.flag"),
    ("results/module3/m3_repo_m2_2_variant_annotation_integration_stub.json", "m3_sc.repo_m2_2_variant_annotation_integration_stub"),
    ("results/module3/m3_repo_m2_2_variant_annotation_integration_stub.flag", "m3_sc.repo_m2_2_variant_annotation_integration_stub.flag"),
    ("results/module3/m3_repo_m2_2_depmap_mirror_paths_status.json", "m3_sc.repo_m2_2_depmap_mirror_paths_status"),
    ("results/module3/m3_repo_m2_2_depmap_mirror_paths_status.flag", "m3_sc.repo_m2_2_depmap_mirror_paths_status.flag"),
    ("results/module3/m3_repo_m2_2_depmap_mirror_integration_stub.json", "m3_sc.repo_m2_2_depmap_mirror_integration_stub"),
    ("results/module3/m3_repo_m2_2_depmap_mirror_integration_stub.flag", "m3_sc.repo_m2_2_depmap_mirror_integration_stub.flag"),
    ("results/module3/m3_repo_m2_2_maf_mutsig_mirror_paths_status.json", "m3_sc.repo_m2_2_maf_mutsig_mirror_paths_status"),
    ("results/module3/m3_repo_m2_2_maf_mutsig_mirror_paths_status.flag", "m3_sc.repo_m2_2_maf_mutsig_mirror_paths_status.flag"),
    ("results/module3/m3_repo_m2_2_maf_mutsig_mirror_integration_stub.json", "m3_sc.repo_m2_2_maf_mutsig_mirror_integration_stub"),
    ("results/module3/m3_repo_m2_2_maf_mutsig_mirror_integration_stub.flag", "m3_sc.repo_m2_2_maf_mutsig_mirror_integration_stub.flag"),
    ("results/module3/m3_repo_m2_2_outline_driver_mirror_paths_status.json", "m3_sc.repo_m2_2_outline_driver_mirror_paths_status"),
    ("results/module3/m3_repo_m2_2_outline_driver_mirror_paths_status.flag", "m3_sc.repo_m2_2_outline_driver_mirror_paths_status.flag"),
    ("results/module3/m3_repo_m2_2_outline_driver_mirror_integration_stub.json", "m3_sc.repo_m2_2_outline_driver_mirror_integration_stub"),
    ("results/module3/m3_repo_m2_2_outline_driver_mirror_integration_stub.flag", "m3_sc.repo_m2_2_outline_driver_mirror_integration_stub.flag"),
    ("results/module3/m1_outline_paths_status.json", "m1.outline_paths_status"),
    ("results/module3/m1_outline_paths_status.flag", "m1.outline_paths_status.flag"),
    ("results/module3/m1_outline_integration_stub.json", "m1.outline_integration_stub"),
    ("results/module3/m1_outline_integration_stub.flag", "m1.outline_integration_stub.flag"),
    ("results/module3/m1_harmony_batch_paths_status.json", "m1.harmony_batch_paths_status"),
    ("results/module3/m1_harmony_batch_paths_status.flag", "m1.harmony_batch_paths_status.flag"),
    ("results/module3/m1_harmony_batch_integration_stub.json", "m1.harmony_batch_integration_stub"),
    ("results/module3/m1_harmony_batch_integration_stub.flag", "m1.harmony_batch_integration_stub.flag"),
    ("results/module3/m1_reference_gdc_paths_status.json", "m1.reference_gdc_paths_status"),
    ("results/module3/m1_reference_gdc_paths_status.flag", "m1.reference_gdc_paths_status.flag"),
    ("results/module3/m1_reference_gdc_integration_stub.json", "m1.reference_gdc_integration_stub"),
    ("results/module3/m1_reference_gdc_integration_stub.flag", "m1.reference_gdc_integration_stub.flag"),
    ("results/module3/m1_batch_correction_mirror_paths_status.json", "m1.batch_correction_mirror_paths_status"),
    ("results/module3/m1_batch_correction_mirror_paths_status.flag", "m1.batch_correction_mirror_paths_status.flag"),
    ("results/module3/m1_batch_correction_mirror_integration_stub.json", "m1.batch_correction_mirror_integration_stub"),
    ("results/module3/m1_batch_correction_mirror_integration_stub.flag", "m1.batch_correction_mirror_integration_stub.flag"),
    ("results/module3/m3_repo_m1_outline_paths_status.json", "m3_sc.repo_m1_outline_paths_status"),
    ("results/module3/m3_repo_m1_outline_paths_status.flag", "m3_sc.repo_m1_outline_paths_status.flag"),
    ("results/module3/m3_repo_m1_outline_integration_stub.json", "m3_sc.repo_m1_outline_integration_stub"),
    ("results/module3/m3_repo_m1_outline_integration_stub.flag", "m3_sc.repo_m1_outline_integration_stub.flag"),
    ("results/module3/m3_repo_m1_harmony_batch_paths_status.json", "m3_sc.repo_m1_harmony_batch_paths_status"),
    ("results/module3/m3_repo_m1_harmony_batch_paths_status.flag", "m3_sc.repo_m1_harmony_batch_paths_status.flag"),
    (
        "results/module3/m3_repo_m1_harmony_batch_integration_stub.json",
        "m3_sc.repo_m1_harmony_batch_integration_stub",
    ),
    (
        "results/module3/m3_repo_m1_harmony_batch_integration_stub.flag",
        "m3_sc.repo_m1_harmony_batch_integration_stub.flag",
    ),
    ("results/module3/m3_repo_m1_reference_gdc_paths_status.json", "m3_sc.repo_m1_reference_gdc_paths_status"),
    ("results/module3/m3_repo_m1_reference_gdc_paths_status.flag", "m3_sc.repo_m1_reference_gdc_paths_status.flag"),
    (
        "results/module3/m3_repo_m1_reference_gdc_integration_stub.json",
        "m3_sc.repo_m1_reference_gdc_integration_stub",
    ),
    (
        "results/module3/m3_repo_m1_reference_gdc_integration_stub.flag",
        "m3_sc.repo_m1_reference_gdc_integration_stub.flag",
    ),
    (
        "results/module3/m3_repo_m1_batch_correction_mirror_paths_status.json",
        "m3_sc.repo_m1_batch_correction_mirror_paths_status",
    ),
    (
        "results/module3/m3_repo_m1_batch_correction_mirror_paths_status.flag",
        "m3_sc.repo_m1_batch_correction_mirror_paths_status.flag",
    ),
    (
        "results/module3/m3_repo_m1_batch_correction_mirror_integration_stub.json",
        "m3_sc.repo_m1_batch_correction_mirror_integration_stub",
    ),
    (
        "results/module3/m3_repo_m1_batch_correction_mirror_integration_stub.flag",
        "m3_sc.repo_m1_batch_correction_mirror_integration_stub.flag",
    ),
]

# Inventoried for audits / pipeline_results_index but must not be named inputs on rule
# m3_export_manifest: Snakemake would otherwise schedule optional conda rules (RCTD, Cell2location)
# and fail dry-runs when RDS/h5ad under data_root are absent.
_ARTIFACTS_EXEMPT_FROM_SNAKEFILE_MANIFEST_INPUTS: frozenset[str] = frozenset(
    {
        "results/module3/m3_deconvolution_rctd/rctd_run_provenance.json",
        "results/module3/m3_deconvolution_rctd/rctd_run.flag",
        "results/module3/m3_deconvolution_cell2location/cell2location_run_provenance.json",
        "results/module3/m3_deconvolution_cell2location/cell2location_run.flag",
        "results/module3/m3_deconvolution_cell2location/spatial_cell2location.h5ad",
        "results/module3/m3_deconvolution_cell2location/spot_cell_abundance_means.tsv",
    }
)


def _append_extra_artifacts(rr: Path, block: dict[str, Any], artifacts: list[dict[str, Any]]) -> None:
    for i, item in enumerate(block.get("extra_artifacts") or []):
        if not isinstance(item, dict):
            continue
        rel = str(item.get("path", "") or "").strip()
        if not rel:
            continue
        tag = str(item.get("tag", "") or "").strip() or f"extra.{i}"
        row = describe_path(rr, rel, tag=tag)
        if bool(item.get("optional")):
            row["optional"] = True
        artifacts.append(row)


def main() -> int:
    rr = repo_root()
    doc_all = load_cfg()
    block = doc_all.get("module3_export_manifest") or {}
    if not block.get("enabled", True):
        print("module3_export_manifest disabled")
        return 0

    out_rel = str(block.get("output_json", "results/module3/module3_export_manifest.json"))
    out_path = rr / out_rel.replace("/", os.sep)

    artifacts: list[dict[str, Any]] = []
    for rel, tag in _ARTIFACTS:
        artifacts.append(describe_path(rr, rel, tag=tag))
    _append_extra_artifacts(rr, block, artifacts)
    manifest_optional.apply_optional_tags_to_artifacts(artifacts, block.get("optional_tags") or [])

    doc = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifacts": artifacts,
        "note": "Curated bulk-DE and integration paths under results/module3/; not exhaustive.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    n_ok = sum(1 for a in artifacts if a.get("exists"))
    print(f"Wrote {out_path} ({len(artifacts)} entries, {n_ok} existing on disk)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
