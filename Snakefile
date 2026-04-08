"""
GLIOMA-TARGET workflow entry. Data paths honor GLIOMA_TARGET_DATA_ROOT.

Outline mapping (Project_Outline.docx / Project_Outline_extracted.txt):
  • fetch_public_data / verify_data_layout / GDC matrices → toward Module 1 (harmonization) + Module 2 inputs
  • toil_gbm_brain_tpm + DEA rules → Module 2 §2.1 (DEA), TOIL-coherent implementation
See docs/PIPELINE_ALIGNMENT.md and config/pipeline_outline.yaml for full seven-module status.
"""

import os
import subprocess
import sys
from pathlib import Path

import yaml

_ROOT = Path(workflow.basedir).resolve()
_SCRIPTS_DIR = str(_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
_DS_PATH = _ROOT / "config" / "data_sources.yaml"
with open(_DS_PATH, encoding="utf-8") as f:
    _data_sources = yaml.safe_load(f)

DATA_ROOT = Path(
    os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip() or _data_sources["data_root"]
)


def _m5_srges_perturbation_tsv_path() -> str:
    doc = yaml.safe_load((_ROOT / "config" / "m5_srges.yaml").read_text(encoding="utf-8"))
    blk = doc.get("m5_srges_run") or {}
    pt = blk.get("perturbation_tsv")
    if not pt:
        raise ValueError("config/m5_srges.yaml: m5_srges_run.perturbation_tsv is required")
    t = str(pt).replace("{data_root}", str(DATA_ROOT))
    p = Path(t.replace("/", os.sep))
    if p.is_absolute():
        return str(p.resolve())
    rel = str(pt).replace("{data_root}/", "").replace("{data_root}", "").strip("/\\").replace("/", os.sep)
    return str((DATA_ROOT / rel).resolve())


def _m3_s2_reference_profile_tsv() -> str:
    doc = yaml.safe_load((_ROOT / "config" / "m3_deconvolution_s2_nnls.yaml").read_text(encoding="utf-8"))
    blk = doc.get("m3_deconvolution_s2_nnls") or {}
    r = blk.get("reference_profile_tsv")
    if not r:
        raise ValueError("config/m3_deconvolution_s2_nnls.yaml: reference_profile_tsv required")
    rel = str(r).strip("/\\").replace("/", os.sep)
    return str((DATA_ROOT / rel).resolve())


def _m3_s2_spatial_counts_tsv() -> str:
    doc = yaml.safe_load((_ROOT / "config" / "m3_deconvolution_s2_nnls.yaml").read_text(encoding="utf-8"))
    blk = doc.get("m3_deconvolution_s2_nnls") or {}
    s = blk.get("spatial_counts_tsv")
    if not s:
        raise ValueError("config/m3_deconvolution_s2_nnls.yaml: spatial_counts_tsv required")
    rel = str(s).strip("/\\").replace("/", os.sep)
    return str((DATA_ROOT / rel).resolve())


def _m3_rctd_reference_rds() -> str:
    doc = yaml.safe_load((_ROOT / "config" / "m3_deconvolution_rctd_inputs.yaml").read_text(encoding="utf-8"))
    blk = doc.get("m3_deconvolution_rctd") or {}
    r = blk.get("reference_rds")
    if not r:
        raise ValueError("config/m3_deconvolution_rctd_inputs.yaml: reference_rds required")
    rel = str(r).strip("/\\").replace("/", os.sep)
    return str((DATA_ROOT / rel).resolve())


def _m3_rctd_spatial_rds() -> str:
    doc = yaml.safe_load((_ROOT / "config" / "m3_deconvolution_rctd_inputs.yaml").read_text(encoding="utf-8"))
    blk = doc.get("m3_deconvolution_rctd") or {}
    s = blk.get("spatial_rna_rds")
    if not s:
        raise ValueError("config/m3_deconvolution_rctd_inputs.yaml: spatial_rna_rds required")
    rel = str(s).strip("/\\").replace("/", os.sep)
    return str((DATA_ROOT / rel).resolve())


def _m3_rctd_conda_env_path() -> Path:
    """Default ``m3_rctd.yaml``. ``GLIOMA_TARGET_M3_RCTD_BUNDLE_SPACEXR=1`` selects Bioconda spacexr (Linux/macOS)."""
    envs = _ROOT / "workflow" / "envs"
    if os.environ.get("GLIOMA_TARGET_M3_RCTD_BUNDLE_SPACEXR", "").strip().lower() in ("1", "true", "yes"):
        return envs / "m3_rctd_spacexr_bioconda.yaml"
    return envs / "m3_rctd.yaml"


def _m3_cell2location_config_path() -> Path:
    """Override with ``GLIOMA_TARGET_M3_CELL2LOCATION_CONFIG`` (repo-relative or absolute path to a YAML file)."""
    alt = os.environ.get("GLIOMA_TARGET_M3_CELL2LOCATION_CONFIG", "").strip()
    if not alt:
        return _ROOT / "config" / "m3_deconvolution_cell2location_inputs.yaml"
    p = Path(alt)
    return p.resolve() if p.is_absolute() else (_ROOT / p).resolve()


def _m3_cell2location_blk() -> dict:
    doc = yaml.safe_load(_m3_cell2location_config_path().read_text(encoding="utf-8"))
    return doc.get("m3_deconvolution_cell2location") or {}


def _m3_cell2location_ref_h5ad() -> str:
    blk = _m3_cell2location_blk()
    r = blk.get("reference_h5ad")
    if not r:
        raise ValueError("config/m3_deconvolution_cell2location_inputs.yaml: reference_h5ad required")
    rel = str(r).strip("/\\").replace("/", os.sep)
    return str((DATA_ROOT / rel).resolve())


def _m3_cell2location_spatial_h5ad() -> str:
    blk = _m3_cell2location_blk()
    s = blk.get("spatial_h5ad")
    if not s:
        raise ValueError("config/m3_deconvolution_cell2location_inputs.yaml: spatial_h5ad required")
    rel = str(s).strip("/\\").replace("/", os.sep)
    return str((DATA_ROOT / rel).resolve())


def _m3_cell2location_training_enabled() -> bool:
    blk = _m3_cell2location_blk()
    return bool((blk.get("training") or {}).get("enabled", False))


def _m3_cell2location_output_result_h5ad_repo_rel() -> str:
    blk = _m3_cell2location_blk()
    p = blk.get("output_result_h5ad") or "results/module3/m3_deconvolution_cell2location/spatial_cell2location.h5ad"
    return str(p).replace("\\", "/")


def _m3_cell2location_output_abundance_tsv_repo_rel() -> str:
    blk = _m3_cell2location_blk()
    p = blk.get("output_abundance_tsv") or (
        "results/module3/m3_deconvolution_cell2location/spot_cell_abundance_means.tsv"
    )
    return str(p).replace("\\", "/")


def _m3_cell2location_conda_env_path() -> Path:
    """Full training: m3_cell2location.yaml. Validate-only smoke: GLIOMA_TARGET_M3_C2L_CONDA_ENV=light."""
    mode = os.environ.get("GLIOMA_TARGET_M3_C2L_CONDA_ENV", "").strip().lower()
    envs = _ROOT / "workflow" / "envs"
    if mode in ("light", "validate", "minimal"):
        return envs / "m3_cell2location_light.yaml"
    return envs / "m3_cell2location.yaml"


# Orchestrator always writes prov JSON; cell2location_run.flag only on exit 0 (training_failed drops stale flag).
_M3_C2L_RUN_OUTPUTS: dict[str, str] = {
    "prov": "results/module3/m3_deconvolution_cell2location/cell2location_run_provenance.json",
    "flag": "results/module3/m3_deconvolution_cell2location/cell2location_run.flag",
}
if _m3_cell2location_training_enabled():
    _M3_C2L_RUN_OUTPUTS["result_h5ad"] = _m3_cell2location_output_result_h5ad_repo_rel()
    _M3_C2L_RUN_OUTPUTS["abundance_tsv"] = _m3_cell2location_output_abundance_tsv_repo_rel()


def _depmap_mae_gz_paths() -> tuple[str, str, str]:
    """DepMap MAE .tsv.gz paths under DATA_ROOT from config/m2_movics_data_fetch.yaml."""
    doc = yaml.safe_load((_ROOT / "config" / "m2_movics_data_fetch.yaml").read_text(encoding="utf-8"))
    blk = doc.get("depmap_gbm_mae") or {}
    fn = blk.get("filenames") or {}
    od = str(blk.get("out_dir", "omics/multi_omics_mae")).replace("/", os.sep)
    root = DATA_ROOT / od
    expr = root / fn.get("expression_gz", "depmap_gbm_expression_logtpm.tsv.gz")
    cn = root / fn.get("copy_number_gz", "depmap_gbm_cnv_log2.tsv.gz")
    mut = root / fn.get("mutation_binary_gz", "depmap_gbm_mutation_binary.tsv.gz")
    return str(expr), str(cn), str(mut)


def _depmap_model_csv(wildcards) -> str:
    from depmap_shared import latest_depmap_dir

    return str(latest_depmap_dir(DATA_ROOT) / "Model.csv")


def _rscript_exe() -> str:
    """Rscript path: env / Windows registry / rscript_local.yaml — R\bin need not be on PATH."""
    from rscript_resolve import resolve_rscript

    return resolve_rscript(_ROOT)


def _wgcna_symbol_list_paths_for_block(block_name: str) -> list[str]:
    p = _ROOT / "config" / "module2_integration.yaml"
    block = yaml.safe_load(p.read_text(encoding="utf-8")).get(block_name) or {}
    rels = block.get("symbol_list_paths") or []
    return [str((_ROOT / rel.replace("/", os.sep)).resolve()) for rel in rels]


def _wgcna_symbol_list_input_paths(wildcards) -> list[str]:
    return _wgcna_symbol_list_paths_for_block("wgcna_hub_subset")


def _wgcna_symbol_list_input_paths_recount3_only(wildcards) -> list[str]:
    return _wgcna_symbol_list_paths_for_block("wgcna_hub_subset_recount3_only")


def require_dir(path: Path, name: str) -> None:
    if not path.is_dir():
        raise FileNotFoundError(f"{name} not found: {path}")


def _env_truthy(name: str) -> bool:
    """True when env var is 1/true/yes/on (case-insensitive). Used for optional rule all targets."""
    v = os.environ.get(name, "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _rule_all_optional_inputs(wildcards) -> list[str]:
    """Extra rule all outputs gated by env (see GLIOMA_TARGET_INCLUDE_*)."""
    o: list[str] = []
    if _env_truthy("GLIOMA_TARGET_INCLUDE_CLINVAR"):
        o.extend(
            [
                "results/module3/m2_2_clinvar/maf_genes_with_clinvar_gene_summary.tsv",
                "results/module3/m2_2_clinvar/clinvar_gene_annotation_provenance.json",
            ]
        )
    if _env_truthy("GLIOMA_TARGET_INCLUDE_M3_SCANPY"):
        o.extend(
            [
                "results/module3/scrna_gse57872_scanpy/obs_qc_leiden.tsv",
                "results/module3/scrna_gse57872_scanpy/qc_cluster_metrics.json",
                "results/module3/scrna_gse57872_scanpy/run_provenance.json",
            ]
        )
    if _env_truthy("GLIOMA_TARGET_INCLUDE_MOVICS"):
        o.extend(
            [
                "results/module3/m2_movics_intnmf/movics_intnmf_clusters.tsv",
                "results/module3/m2_movics_intnmf/movics_intnmf_provenance.json",
            ]
        )
    if _env_truthy("GLIOMA_TARGET_INCLUDE_MOVICS_DEPMAP_MAE"):
        o.extend(
            [
                "results/module3/m2_movics_intnmf_depmap_mae/movics_depmap_mae_clusters.tsv",
                "results/module3/m2_movics_intnmf_depmap_mae/movics_depmap_mae_provenance.json",
                "results/module3/m2_movics_intnmf_depmap_mae/cluster_model_annotations.tsv",
                "results/module3/m2_movics_intnmf_depmap_mae/cluster_summary.json",
            ]
        )
    if _env_truthy("GLIOMA_TARGET_INCLUDE_SUPPLEMENTARY_WIRING"):
        o.extend(
            [
                "results/r_supplementary_enrichment_packages.flag",
                "results/reports/wikipathways_gmt_url_sync.json",
                "results/module3/wikipathways_gmt_url_ok.flag",
                "results/module4/pathwaycommons_hgnc_gmt_plain.flag",
                "results/module4/m4_supplementary_open_enrichment_plan.json",
                "results/module4/m4_clusterprofiler_supplementary_plan.json",
                "results/module4/r_external/fgsea_supplementary_pathways.R",
                "results/module4/r_external/clusterprofiler_supplementary_pathways.R",
                "results/module4/gsea/fgsea_supplementary_pathways_results.tsv",
                "results/module4/gsea/clusterprofiler_supplementary_enricher.tsv",
                "results/module4/archs4_recount_h5_summary.json",
                "results/module4/archs4_outline_driver_expression_context.json",
                "results/module4/drugcentral_postgres_load_status.json",
                "results/module3/dea_gbm_vs_gtex_brain_archs4.tsv",
                "results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate_archs4.tsv",
                "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_archs4.tsv",
                "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_archs4.tsv",
                "results/module3/dea_archs4_join_provenance.json",
            ]
        )
    # M7_DELIVERABLES implies viz + docx via m7_glioma_target_deliverables (do not also set VIZ/DOCX to avoid duplicate rule all inputs).
    if _env_truthy("GLIOMA_TARGET_INCLUDE_M7_DELIVERABLES"):
        o.append("results/module7/glioma_target_deliverables.flag")
    else:
        if _env_truthy("GLIOMA_TARGET_INCLUDE_M7_VIZ"):
            o.extend(
                [
                    "results/module7/glioma_target_results_uhd.png",
                    "results/module7/glioma_target_results_uhd.pdf",
                    "results/module7/glioma_target_panels/01_tier1_ranked_bars.png",
                    "results/module7/glioma_target_panels/02_E_M_landscape.png",
                    "results/module7/glioma_target_panels/03_cohort_hexbin_context.png",
                    "results/module7/glioma_target_panels/04_subscore_heatmap.png",
                    "results/module7/glioma_target_panels/05_score_distribution.png",
                    "results/module7/glioma_target_panels/06_subscore_violin.png",
                    "results/module7/glioma_target_visualization.flag",
                ]
            )
        if _env_truthy("GLIOMA_TARGET_INCLUDE_M7_DOCX"):
            o.append("results/module7/glioma_target_results_report.docx")
    if _env_truthy("GLIOMA_TARGET_INCLUDE_M5_SRGES_RUN"):
        o.extend(
            [
                "results/module5/m5_srges_compound_ranks.tsv",
                "results/module5/m5_srges_run_provenance.json",
                "results/module5/m5_srges_run.flag",
            ]
        )
    if _env_truthy("GLIOMA_TARGET_INCLUDE_M3_DECONV_S2"):
        o.extend(
            [
                "results/module3/m3_deconvolution_s2/spot_celltype_fractions.tsv",
                "results/module3/m3_deconvolution_s2/deconvolution_s2_provenance.json",
                "results/module3/m3_deconvolution_s2/deconvolution_s2.flag",
            ]
        )
    if _env_truthy("GLIOMA_TARGET_INCLUDE_M3_RCTD_RUN"):
        o.extend(
            [
                "results/module3/m3_deconvolution_rctd/rctd_run_provenance.json",
                "results/module3/m3_deconvolution_rctd/rctd_run.flag",
            ]
        )
    if _env_truthy("GLIOMA_TARGET_INCLUDE_M3_CELL2LOCATION_RUN"):
        o.extend(
            [
                "results/module3/m3_deconvolution_cell2location/cell2location_run_provenance.json",
                "results/module3/m3_deconvolution_cell2location/cell2location_run.flag",
            ]
        )
        if _m3_cell2location_training_enabled():
            o.append(_m3_cell2location_output_result_h5ad_repo_rel())
            o.append(_m3_cell2location_output_abundance_tsv_repo_rel())
    return o


rule all:
    input:
        "results/data_layout_ok.flag",
        "results/module2/tcga_gbm_star_tpm_matrix.parquet",
        "results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet",
        "results/module2/gdc_counts_matrix_qc.json",
        "results/module2/tcga_gbm_sample_meta.tsv",
        "results/module1/combat_seq_tcga_gbm_primary/combat_seq_adjusted_counts.parquet",
        "results/module1/combat_seq_tcga_gbm_primary/combat_seq_provenance.json",
        "results/module3/cohort_design_summary.json",
        "results/module3/dea_gbm_vs_gtex_brain.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv",
        "results/module3/tcga_gbm_verhaak_subtype_scores.tsv",
        "results/module3/tcga_gbm_verhaak_subtype_summary.json",
        "results/module3/dea_gbm_vs_gtex_brain_ols_depmap_crispr.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_depmap_crispr.tsv",
        "results/module3/stratified_dea/summary.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_ols_depmap_somatic.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_depmap_somatic.tsv",
        "results/module3/depmap_gbm_somatic_by_gene.tsv",
        "results/module3/tcga_gbm_maf_gene_summary.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_ols_tcga_maf.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_tcga_maf.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_tcga_maf.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_tcga_maf.tsv",
        "results/module3/stratified_ols_dea/summary.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_mutsig.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_ols_mutsig.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_mutsig.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_mutsig.tsv",
        "results/module3/stratified_dea_integration.flag",
        "results/module2/gdc_counts_cohort_summary.json",
        "results/module3/deseq2_tcga_gbm/primary_vs_recurrent/deseq2_results.tsv",
        "results/module3/deseq2_tcga_gbm/primary_vs_recurrent/deseq2_provenance.json",
        "results/module3/deseq2_tcga_gbm/primary_vs_solid_tissue_normal/deseq2_results.tsv",
        "results/module3/deseq2_tcga_gbm/primary_vs_solid_tissue_normal/deseq2_provenance.json",
        "results/module3/edger_tcga_gbm/primary_vs_recurrent/edger_qlf_results.tsv",
        "results/module3/edger_tcga_gbm/primary_vs_recurrent/edger_provenance.json",
        "results/module3/edger_tcga_gbm/primary_vs_solid_tissue_normal/edger_qlf_results.tsv",
        "results/module3/edger_tcga_gbm/primary_vs_solid_tissue_normal/edger_provenance.json",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_results.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_provenance.json",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/recount3_de_counts_matrix.parquet",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/recount3_de_sample_meta.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_qlf_results.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_provenance.json",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_depmap_crispr.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_depmap_crispr.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_depmap_somatic.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_depmap_somatic.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_archs4.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate_archs4.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_archs4.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_archs4.tsv",
        "results/module3/dea_archs4_join_provenance.json",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_vs_edger_concordance.json",
        "results/module3/toil_welch_vs_recount3_bulk_effect_correlation.json",
        "results/module3/m2_3_movics_vs_consensus_method_contrast.json",
        "results/module3/m2_3_consensus_star_primary/consensus_sample_clusters.tsv",
        "results/module3/m2_3_consensus_star_primary/consensus_provenance.json",
        "results/module3/dea_gbm_vs_gtex_brain_outline_drivers.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_ols_outline_drivers.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_depmap_crispr_outline_drivers.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_ols_depmap_crispr_outline_drivers.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_depmap_somatic_outline_drivers.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_ols_depmap_somatic_outline_drivers.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_tcga_maf_outline_drivers.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_ols_tcga_maf_outline_drivers.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_mutsig_outline_drivers.tsv",
        "results/module3/dea_gbm_vs_gtex_brain_ols_mutsig_outline_drivers.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_outline_drivers.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_outline_drivers.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_depmap_crispr_outline_drivers.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_depmap_crispr_outline_drivers.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_depmap_somatic_outline_drivers.tsv",
        "results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_depmap_somatic_outline_drivers.tsv",
        "results/module3/stratified_integrated_outline_drivers.flag",
        "results/module3/mean_log_tpm_by_verhaak_subtype.tsv",
        "results/module3/dea_welch_fdr05_symbols_for_string.txt",
        "results/module3/dea_welch_string_m21_high_confidence.txt",
        "results/module3/dea_welch_string_fdr_lfc_ge_1p5.txt",
        "results/module3/dea_ols_string_m21_high_confidence.txt",
        "results/module3/dea_welch_string_m21_depmap_crispr_median_lte_minus0p5.txt",
        "results/module3/dea_ols_string_m21_depmap_crispr_median_lte_minus0p5.txt",
        "results/module3/dea_recount3_pydeseq2_string_fdr05.txt",
        "results/module3/dea_recount3_edger_string_fdr05.txt",
        "results/module3/dea_recount3_pydeseq2_string_depmap_crispr_median_lte_minus0p5.txt",
        "results/module3/dea_recount3_edger_string_depmap_crispr_median_lte_minus0p5.txt",
        "results/module3/dea_recount3_depmap_crispr_consensus_string.txt",
        "results/module3/dea_string_export_provenance.json",
        "results/module4/wgcna_hub_expr_subset.parquet",
        "results/module4/wgcna_hub_expr_subset_long.tsv",
        "results/module4/wgcna_hub_expr_subset_provenance.json",
        "results/module4/wgcna_hub_expr_subset_recount3_only.parquet",
        "results/module4/wgcna_hub_expr_subset_recount3_only_long.tsv",
        "results/module4/wgcna_hub_expr_subset_recount3_only_provenance.json",
        "results/module4/wgcna_hub_sample_traits.tsv",
        "results/module4/wgcna_hub_sample_traits_provenance.json",
        "results/module4/wgcna_hub_sample_traits_recount3_only.tsv",
        "results/module4/wgcna_hub_sample_traits_recount3_only_provenance.json",
        "results/module4/wgcna_hub_gene_overlap_summary.json",
        "results/module4/stratified_string_export_provenance.json",
        "results/module4/gsea/dea_welch_signed_neg_log10_p.rnk",
        "results/module4/gsea/dea_ols_signed_neg_log10_p.rnk",
        "results/module4/gsea/recount3_pydeseq2_signed_neg_log10_p.rnk",
        "results/module4/gsea/recount3_edger_signed_neg_log10_p.rnk",
        "results/module4/gsea_prerank_export_provenance.json",
        "results/module4/gsea_stratified_prerank.flag",
        "results/module4/m4_network_paths_status.json",
        "results/module4/m4_network_paths_status.flag",
        "results/module4/m4_network_integration_stub.json",
        "results/module4/m4_network_integration_stub.flag",
        "results/module4/m4_string_cache_paths_status.json",
        "results/module4/m4_string_cache_paths_status.flag",
        "results/module4/m4_string_cache_integration_stub.json",
        "results/module4/m4_string_cache_integration_stub.flag",
        "results/module4/m4_gsea_mirror_paths_status.json",
        "results/module4/m4_gsea_mirror_paths_status.flag",
        "results/module4/m4_gsea_mirror_integration_stub.json",
        "results/module4/m4_gsea_mirror_integration_stub.flag",
        "results/module4/m4_pathway_database_mirror_paths_status.json",
        "results/module4/m4_pathway_database_mirror_paths_status.flag",
        "results/module4/m4_pathway_database_mirror_integration_stub.json",
        "results/module4/m4_pathway_database_mirror_integration_stub.flag",
        "results/module3/supplementary_reference_resources_paths_status.json",
        "results/module3/supplementary_reference_resources_paths_status.flag",
        "results/module4/module4_export_manifest.json",
        "results/module5/module5_data_paths_status.flag",
        "results/module5/cmap_tooling_scan.json",
        "results/module5/cmap_tooling_scan.flag",
        "results/module5/lincs_disease_signature_welch_entrez.tsv",
        "results/module5/lincs_disease_signature_ols_entrez.tsv",
        "results/module5/lincs_disease_signature_recount3_pydeseq2_entrez.tsv",
        "results/module5/lincs_disease_signature_recount3_edger_entrez.tsv",
        "results/module5/lincs_disease_signature_provenance.json",
        "results/module5/lincs_disease_signature.flag",
        "results/module5/lincs_stratified_signature.flag",
        "results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Classical_entrez.tsv",
        "results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Mesenchymal_entrez.tsv",
        "results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Neural_entrez.tsv",
        "results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Proneural_entrez.tsv",
        "results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Classical_entrez.tsv",
        "results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Mesenchymal_entrez.tsv",
        "results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Neural_entrez.tsv",
        "results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Proneural_entrez.tsv",
        "results/module5/module5_export_manifest.json",
        "results/module5/lincs_connectivity_readiness.json",
        "results/module5/lincs_connectivity_readiness.flag",
        "results/module5/lincs_signature_pack.json",
        "results/module5/lincs_signature_pack.flag",
        "results/module5/srges_integration_stub.json",
        "results/module5/srges_integration_stub.flag",
        "results/module5/m5_modality_paths_status.json",
        "results/module5/m5_modality_paths_status.flag",
        "results/module5/m5_modality_integration_stub.json",
        "results/module5/m5_modality_integration_stub.flag",
        "results/module5/m5_l1000_data_paths_status.json",
        "results/module5/m5_l1000_data_paths_status.flag",
        "results/module5/m5_l1000_data_integration_stub.json",
        "results/module5/m5_l1000_data_integration_stub.flag",
        "results/module5/m5_srges_output_paths_status.json",
        "results/module5/m5_srges_output_paths_status.flag",
        "results/module5/m5_srges_output_integration_stub.json",
        "results/module5/m5_srges_output_integration_stub.flag",
        "results/module5/m5_lincs_connectivity_mirror_paths_status.json",
        "results/module5/m5_lincs_connectivity_mirror_paths_status.flag",
        "results/module5/m5_lincs_connectivity_mirror_integration_stub.json",
        "results/module5/m5_lincs_connectivity_mirror_integration_stub.flag",
        "results/module7/gts_candidate_table_welch_stub.tsv",
        "results/module7/glioma_target_tier1_welch.tsv",
        "results/module7/gts_candidate_table_ols_stub.tsv",
        "results/module7/gts_candidate_table_recount3_pydeseq2_stub.tsv",
        "results/module7/gts_candidate_table_recount3_edger_stub.tsv",
        "results/module7/gts_candidate_stub_provenance.json",
        "results/module7/gts_candidate_stub.flag",
        "results/module7/gts_stratified_candidate_stub.flag",
        "results/module7/gts_validation_integration_stub.json",
        "results/module7/gts_validation_integration_stub.flag",
        "results/module7/m7_validation_paths_status.json",
        "results/module7/m7_validation_paths_status.flag",
        "results/module7/m7_validation_integration_stub.json",
        "results/module7/m7_validation_integration_stub.flag",
        "results/module7/m7_gts_external_score_mirror_paths_status.json",
        "results/module7/m7_gts_external_score_mirror_paths_status.flag",
        "results/module7/m7_gts_external_score_mirror_integration_stub.json",
        "results/module7/m7_gts_external_score_mirror_integration_stub.flag",
        "results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Classical_gts_stub.tsv",
        "results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Mesenchymal_gts_stub.tsv",
        "results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Neural_gts_stub.tsv",
        "results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Proneural_gts_stub.tsv",
        "results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Classical_gts_stub.tsv",
        "results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Mesenchymal_gts_stub.tsv",
        "results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Neural_gts_stub.tsv",
        "results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Proneural_gts_stub.tsv",
        "results/module7/module7_export_manifest.json",
        "results/module6/structure_druggability_bridge_welch.tsv",
        "results/module6/structure_druggability_bridge_ols.tsv",
        "results/module6/structure_druggability_bridge_recount3_pydeseq2.tsv",
        "results/module6/structure_druggability_bridge_recount3_edger.tsv",
        "results/module6/structure_druggability_bridge_provenance.json",
        "results/module6/structure_druggability_bridge.flag",
        "results/module6/structure_druggability_bridge_stratified.flag",
        "results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Classical_structure_bridge.tsv",
        "results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Mesenchymal_structure_bridge.tsv",
        "results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Neural_structure_bridge.tsv",
        "results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Proneural_structure_bridge.tsv",
        "results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Classical_structure_bridge.tsv",
        "results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Mesenchymal_structure_bridge.tsv",
        "results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Neural_structure_bridge.tsv",
        "results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Proneural_structure_bridge.tsv",
        "results/module6/module6_structure_tooling_paths_status.json",
        "results/module6/module6_structure_tooling_paths_status.flag",
        "results/module6/structure_admet_integration_stub.json",
        "results/module6/structure_admet_integration_stub.flag",
        "results/module6/m6_toxicity_paths_status.json",
        "results/module6/m6_toxicity_paths_status.flag",
        "results/module6/m6_toxicity_integration_stub.json",
        "results/module6/m6_toxicity_integration_stub.flag",
        "results/module6/m6_docking_output_paths_status.json",
        "results/module6/m6_docking_output_paths_status.flag",
        "results/module6/m6_docking_output_integration_stub.json",
        "results/module6/m6_docking_output_integration_stub.flag",
        "results/module6/m6_compound_library_mirror_paths_status.json",
        "results/module6/m6_compound_library_mirror_paths_status.flag",
        "results/module6/m6_compound_library_mirror_integration_stub.json",
        "results/module6/m6_compound_library_mirror_integration_stub.flag",
        "results/module6/module6_export_manifest.json",
        "results/module3/module3_export_manifest.json",
        "results/tooling/vendor_tooling_paths_status.json",
        "results/tooling/vendor_tooling_paths_status.flag",
        "results/tooling/vendor_tooling_integration_stub.json",
        "results/tooling/vendor_tooling_integration_stub.flag",
        "results/pipeline_results_index.json",
        "results/pipeline_planned_extensions_report.json",
        "results/module3/module3_public_inputs_status.json",
        "results/module3/module3_public_inputs_status.flag",
        "results/module3/module3_sc_workflow_paths_status.json",
        "results/module3/module3_sc_workflow_paths_status.flag",
        "results/module3/scrna_spatial_integration_stub.json",
        "results/module3/scrna_spatial_integration_stub.flag",
        "results/module3/m3_repo_scrna_spatial_paths_status.json",
        "results/module3/m3_repo_scrna_spatial_paths_status.flag",
        "results/module3/m3_repo_scrna_spatial_integration_stub.json",
        "results/module3/m3_repo_scrna_spatial_integration_stub.flag",
        "results/module3/m3_repo_public_inputs_paths_status.json",
        "results/module3/m3_repo_public_inputs_paths_status.flag",
        "results/module3/m3_repo_public_inputs_integration_stub.json",
        "results/module3/m3_repo_public_inputs_integration_stub.flag",
        "results/module3/m3_repo_sc_workflow_paths_status.json",
        "results/module3/m3_repo_sc_workflow_paths_status.flag",
        "results/module3/m3_repo_sc_workflow_integration_stub.json",
        "results/module3/m3_repo_sc_workflow_integration_stub.flag",
        "results/module3/m3_deconvolution_paths_status.json",
        "results/module3/m3_deconvolution_paths_status.flag",
        "results/module3/m3_deconvolution_integration_stub.json",
        "results/module3/m3_deconvolution_integration_stub.flag",
        "results/module3/m3_cellranger_output_paths_status.json",
        "results/module3/m3_cellranger_output_paths_status.flag",
        "results/module3/m3_cellranger_output_integration_stub.json",
        "results/module3/m3_cellranger_output_integration_stub.flag",
        "results/module3/m3_repo_deconvolution_paths_status.json",
        "results/module3/m3_repo_deconvolution_paths_status.flag",
        "results/module3/m3_repo_deconvolution_integration_stub.json",
        "results/module3/m3_repo_deconvolution_integration_stub.flag",
        "results/module3/m3_repo_cellranger_output_paths_status.json",
        "results/module3/m3_repo_cellranger_output_paths_status.flag",
        "results/module3/m3_repo_cellranger_output_integration_stub.json",
        "results/module3/m3_repo_cellranger_output_integration_stub.flag",
        "results/module3/m3_dryad_sra_paths_status.json",
        "results/module3/m3_dryad_sra_paths_status.flag",
        "results/module3/m3_dryad_sra_integration_stub.json",
        "results/module3/m3_dryad_sra_integration_stub.flag",
        "results/module3/m3_geo_pipelines_mirror_paths_status.json",
        "results/module3/m3_geo_pipelines_mirror_paths_status.flag",
        "results/module3/m3_geo_pipelines_mirror_integration_stub.json",
        "results/module3/m3_geo_pipelines_mirror_integration_stub.flag",
        "results/module3/m3_tcga_recount_lincs_mirror_paths_status.json",
        "results/module3/m3_tcga_recount_lincs_mirror_paths_status.flag",
        "results/module3/m3_tcga_recount_lincs_mirror_integration_stub.json",
        "results/module3/m3_tcga_recount_lincs_mirror_integration_stub.flag",
        "results/module3/m3_repo_dryad_sra_paths_status.json",
        "results/module3/m3_repo_dryad_sra_paths_status.flag",
        "results/module3/m3_repo_dryad_sra_integration_stub.json",
        "results/module3/m3_repo_dryad_sra_integration_stub.flag",
        "results/module3/m3_repo_geo_pipelines_mirror_paths_status.json",
        "results/module3/m3_repo_geo_pipelines_mirror_paths_status.flag",
        "results/module3/m3_repo_geo_pipelines_mirror_integration_stub.json",
        "results/module3/m3_repo_geo_pipelines_mirror_integration_stub.flag",
        "results/module3/m3_repo_tcga_recount_lincs_mirror_paths_status.json",
        "results/module3/m3_repo_tcga_recount_lincs_mirror_paths_status.flag",
        "results/module3/m3_repo_tcga_recount_lincs_mirror_integration_stub.json",
        "results/module3/m3_repo_tcga_recount_lincs_mirror_integration_stub.flag",
        "results/module3/m3_repo_bundled_references_paths_status.json",
        "results/module3/m3_repo_bundled_references_paths_status.flag",
        "results/module3/m3_repo_bundled_references_integration_stub.json",
        "results/module3/m3_repo_bundled_references_integration_stub.flag",
        "results/module3/m3_repo_gdc_expression_matrix_paths_status.json",
        "results/module3/m3_repo_gdc_expression_matrix_paths_status.flag",
        "results/module3/m3_repo_gdc_expression_matrix_integration_stub.json",
        "results/module3/m3_repo_gdc_expression_matrix_integration_stub.flag",
        "results/module3/m3_repo_toil_bulk_expression_paths_status.json",
        "results/module3/m3_repo_toil_bulk_expression_paths_status.flag",
        "results/module3/m3_repo_toil_bulk_expression_integration_stub.json",
        "results/module3/m3_repo_toil_bulk_expression_integration_stub.flag",
        "results/module3/m3_repo_recount3_bulk_dea_paths_status.json",
        "results/module3/m3_repo_recount3_bulk_dea_paths_status.flag",
        "results/module3/m3_repo_recount3_bulk_dea_integration_stub.json",
        "results/module3/m3_repo_recount3_bulk_dea_integration_stub.flag",
        "results/module3/m3_repo_bulk_welch_ols_dea_paths_status.json",
        "results/module3/m3_repo_bulk_welch_ols_dea_paths_status.flag",
        "results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.json",
        "results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.flag",
        "results/module3/m3_repo_toil_vs_recount3_correlation_paths_status.json",
        "results/module3/m3_repo_toil_vs_recount3_correlation_paths_status.flag",
        "results/module3/m3_repo_toil_vs_recount3_correlation_integration_stub.json",
        "results/module3/m3_repo_toil_vs_recount3_correlation_integration_stub.flag",
        "results/module3/m3_repo_stratified_bulk_dea_paths_status.json",
        "results/module3/m3_repo_stratified_bulk_dea_paths_status.flag",
        "results/module3/m3_repo_stratified_bulk_dea_integration_stub.json",
        "results/module3/m3_repo_stratified_bulk_dea_integration_stub.flag",
        "results/module3/m3_repo_cohort_verhaak_subtype_paths_status.json",
        "results/module3/m3_repo_cohort_verhaak_subtype_paths_status.flag",
        "results/module3/m3_repo_cohort_verhaak_subtype_integration_stub.json",
        "results/module3/m3_repo_cohort_verhaak_subtype_integration_stub.flag",
        "results/module3/m3_repo_bulk_join_provenance_paths_status.json",
        "results/module3/m3_repo_bulk_join_provenance_paths_status.flag",
        "results/module3/m3_repo_bulk_join_provenance_integration_stub.json",
        "results/module3/m3_repo_bulk_join_provenance_integration_stub.flag",
        "results/module3/m3_repo_gdc_star_tcga_gbm_dea_paths_status.json",
        "results/module3/m3_repo_gdc_star_tcga_gbm_dea_paths_status.flag",
        "results/module3/m3_repo_gdc_star_tcga_gbm_dea_integration_stub.json",
        "results/module3/m3_repo_gdc_star_tcga_gbm_dea_integration_stub.flag",
        "results/module3/m3_repo_module5_lincs_connectivity_paths_status.json",
        "results/module3/m3_repo_module5_lincs_connectivity_paths_status.flag",
        "results/module3/m3_repo_module5_lincs_connectivity_integration_stub.json",
        "results/module3/m3_repo_module5_lincs_connectivity_integration_stub.flag",
        "results/module3/m3_repo_module5_l1000_data_paths_status.json",
        "results/module3/m3_repo_module5_l1000_data_paths_status.flag",
        "results/module3/m3_repo_module5_l1000_data_integration_stub.json",
        "results/module3/m3_repo_module5_l1000_data_integration_stub.flag",
        "results/module3/m3_repo_module5_modality_paths_status.json",
        "results/module3/m3_repo_module5_modality_paths_status.flag",
        "results/module3/m3_repo_module5_modality_integration_stub.json",
        "results/module3/m3_repo_module5_modality_integration_stub.flag",
        "results/module3/m3_repo_module5_srges_output_paths_status.json",
        "results/module3/m3_repo_module5_srges_output_paths_status.flag",
        "results/module3/m3_repo_module5_srges_output_integration_stub.json",
        "results/module3/m3_repo_module5_srges_output_integration_stub.flag",
        "results/module3/m3_repo_module5_lincs_connectivity_mirror_paths_status.json",
        "results/module3/m3_repo_module5_lincs_connectivity_mirror_paths_status.flag",
        "results/module3/m3_repo_module5_lincs_connectivity_mirror_integration_stub.json",
        "results/module3/m3_repo_module5_lincs_connectivity_mirror_integration_stub.flag",
        "results/module3/m3_repo_module4_hub_gsea_paths_status.json",
        "results/module3/m3_repo_module4_hub_gsea_paths_status.flag",
        "results/module3/m3_repo_module4_hub_gsea_integration_stub.json",
        "results/module3/m3_repo_module4_hub_gsea_integration_stub.flag",
        "results/module3/m3_repo_module4_network_paths_status.json",
        "results/module3/m3_repo_module4_network_paths_status.flag",
        "results/module3/m3_repo_module4_network_integration_stub.json",
        "results/module3/m3_repo_module4_network_integration_stub.flag",
        "results/module3/m3_repo_module4_string_cache_paths_status.json",
        "results/module3/m3_repo_module4_string_cache_paths_status.flag",
        "results/module3/m3_repo_module4_string_cache_integration_stub.json",
        "results/module3/m3_repo_module4_string_cache_integration_stub.flag",
        "results/module3/m3_repo_module4_pathway_database_mirror_paths_status.json",
        "results/module3/m3_repo_module4_pathway_database_mirror_paths_status.flag",
        "results/module3/m3_repo_module4_pathway_database_mirror_integration_stub.json",
        "results/module3/m3_repo_module4_pathway_database_mirror_integration_stub.flag",
        "results/module3/m3_repo_module4_gsea_mirror_paths_status.json",
        "results/module3/m3_repo_module4_gsea_mirror_paths_status.flag",
        "results/module3/m3_repo_module4_gsea_mirror_integration_stub.json",
        "results/module3/m3_repo_module4_gsea_mirror_integration_stub.flag",
        "results/module3/m3_repo_module7_gts_stub_paths_status.json",
        "results/module3/m3_repo_module7_gts_stub_paths_status.flag",
        "results/module3/m3_repo_module7_gts_stub_integration_stub.json",
        "results/module3/m3_repo_module7_gts_stub_integration_stub.flag",
        "results/module3/m3_repo_module7_validation_paths_status.json",
        "results/module3/m3_repo_module7_validation_paths_status.flag",
        "results/module3/m3_repo_module7_validation_integration_stub.json",
        "results/module3/m3_repo_module7_validation_integration_stub.flag",
        "results/module3/m3_repo_module7_gts_external_score_mirror_paths_status.json",
        "results/module3/m3_repo_module7_gts_external_score_mirror_paths_status.flag",
        "results/module3/m3_repo_module7_gts_external_score_mirror_integration_stub.json",
        "results/module3/m3_repo_module7_gts_external_score_mirror_integration_stub.flag",
        "results/module3/m3_repo_module6_structure_bridge_paths_status.json",
        "results/module3/m3_repo_module6_structure_bridge_paths_status.flag",
        "results/module3/m3_repo_module6_structure_bridge_integration_stub.json",
        "results/module3/m3_repo_module6_structure_bridge_integration_stub.flag",
        "results/module3/m3_repo_module6_structure_tooling_paths_status.json",
        "results/module3/m3_repo_module6_structure_tooling_paths_status.flag",
        "results/module3/m3_repo_module6_structure_tooling_integration_stub.json",
        "results/module3/m3_repo_module6_structure_tooling_integration_stub.flag",
        "results/module3/m3_repo_tooling_vendor_paths_status.json",
        "results/module3/m3_repo_tooling_vendor_paths_status.flag",
        "results/module3/m3_repo_tooling_vendor_integration_stub.json",
        "results/module3/m3_repo_tooling_vendor_integration_stub.flag",
        "results/module3/m3_repo_module6_docking_output_paths_status.json",
        "results/module3/m3_repo_module6_docking_output_paths_status.flag",
        "results/module3/m3_repo_module6_docking_output_integration_stub.json",
        "results/module3/m3_repo_module6_docking_output_integration_stub.flag",
        "results/module3/m3_repo_module6_toxicity_paths_status.json",
        "results/module3/m3_repo_module6_toxicity_paths_status.flag",
        "results/module3/m3_repo_module6_toxicity_integration_stub.json",
        "results/module3/m3_repo_module6_toxicity_integration_stub.flag",
        "results/module3/m3_repo_module6_compound_library_mirror_paths_status.json",
        "results/module3/m3_repo_module6_compound_library_mirror_paths_status.flag",
        "results/module3/m3_repo_module6_compound_library_mirror_integration_stub.json",
        "results/module3/m3_repo_module6_compound_library_mirror_integration_stub.flag",
        "results/module3/maf_annotation_integration_stub.json",
        "results/module3/maf_annotation_integration_stub.flag",
        "results/module3/m3_repo_m2_maf_annotation_paths_status.json",
        "results/module3/m3_repo_m2_maf_annotation_paths_status.flag",
        "results/module3/m3_repo_m2_maf_annotation_integration_stub.json",
        "results/module3/m3_repo_m2_maf_annotation_integration_stub.flag",
        "results/module3/m2_2_variant_annotation_paths_status.json",
        "results/module3/m2_2_variant_annotation_paths_status.flag",
        "results/module3/m2_2_variant_annotation_integration_stub.json",
        "results/module3/m2_2_variant_annotation_integration_stub.flag",
        "results/module3/m2_2_depmap_mirror_paths_status.json",
        "results/module3/m2_2_depmap_mirror_paths_status.flag",
        "results/module3/m2_2_depmap_mirror_integration_stub.json",
        "results/module3/m2_2_depmap_mirror_integration_stub.flag",
        "results/module3/m2_2_maf_mutsig_mirror_paths_status.json",
        "results/module3/m2_2_maf_mutsig_mirror_paths_status.flag",
        "results/module3/m2_2_maf_mutsig_mirror_integration_stub.json",
        "results/module3/m2_2_maf_mutsig_mirror_integration_stub.flag",
        "results/module3/m2_2_outline_driver_mirror_paths_status.json",
        "results/module3/m2_2_outline_driver_mirror_paths_status.flag",
        "results/module3/m2_2_outline_driver_mirror_integration_stub.json",
        "results/module3/m2_2_outline_driver_mirror_integration_stub.flag",
        "results/module3/m2_cptac_methylation_paths_status.json",
        "results/module3/m2_cptac_methylation_paths_status.flag",
        "results/module3/m2_cptac_methylation_integration_stub.json",
        "results/module3/m2_cptac_methylation_integration_stub.flag",
        "results/module3/m2_1_star_pairing_paths_status.json",
        "results/module3/m2_1_star_pairing_paths_status.flag",
        "results/module3/m2_1_star_pairing_integration_stub.json",
        "results/module3/m2_1_star_pairing_integration_stub.flag",
        "results/module3/m2_1_recount3_mirror_paths_status.json",
        "results/module3/m2_1_recount3_mirror_paths_status.flag",
        "results/module3/m2_1_recount3_mirror_integration_stub.json",
        "results/module3/m2_1_recount3_mirror_integration_stub.flag",
        "results/module3/m2_1_toil_xena_hub_paths_status.json",
        "results/module3/m2_1_toil_xena_hub_paths_status.flag",
        "results/module3/m2_1_toil_xena_hub_integration_stub.json",
        "results/module3/m2_1_toil_xena_hub_integration_stub.flag",
        "results/module3/m2_movics_paths_status.json",
        "results/module3/m2_movics_paths_status.flag",
        "results/module3/m2_movics_integration_stub.json",
        "results/module3/m2_movics_integration_stub.flag",
        "results/module3/m2_3_immune_tme_mirror_paths_status.json",
        "results/module3/m2_3_immune_tme_mirror_paths_status.flag",
        "results/module3/m2_3_immune_tme_mirror_integration_stub.json",
        "results/module3/m2_3_immune_tme_mirror_integration_stub.flag",
        "results/module3/m3_repo_m2_cptac_methylation_paths_status.json",
        "results/module3/m3_repo_m2_cptac_methylation_paths_status.flag",
        "results/module3/m3_repo_m2_cptac_methylation_integration_stub.json",
        "results/module3/m3_repo_m2_cptac_methylation_integration_stub.flag",
        "results/module3/m3_repo_m2_1_star_pairing_paths_status.json",
        "results/module3/m3_repo_m2_1_star_pairing_paths_status.flag",
        "results/module3/m3_repo_m2_1_star_pairing_integration_stub.json",
        "results/module3/m3_repo_m2_1_star_pairing_integration_stub.flag",
        "results/module3/m3_repo_m2_1_recount3_mirror_paths_status.json",
        "results/module3/m3_repo_m2_1_recount3_mirror_paths_status.flag",
        "results/module3/m3_repo_m2_1_recount3_mirror_integration_stub.json",
        "results/module3/m3_repo_m2_1_recount3_mirror_integration_stub.flag",
        "results/module3/m3_repo_m2_1_toil_xena_hub_paths_status.json",
        "results/module3/m3_repo_m2_1_toil_xena_hub_paths_status.flag",
        "results/module3/m3_repo_m2_1_toil_xena_hub_integration_stub.json",
        "results/module3/m3_repo_m2_1_toil_xena_hub_integration_stub.flag",
        "results/module3/m3_repo_m2_movics_paths_status.json",
        "results/module3/m3_repo_m2_movics_paths_status.flag",
        "results/module3/m3_repo_m2_movics_integration_stub.json",
        "results/module3/m3_repo_m2_movics_integration_stub.flag",
        "results/module3/m3_repo_m2_3_immune_tme_mirror_paths_status.json",
        "results/module3/m3_repo_m2_3_immune_tme_mirror_paths_status.flag",
        "results/module3/m3_repo_m2_3_immune_tme_mirror_integration_stub.json",
        "results/module3/m3_repo_m2_3_immune_tme_mirror_integration_stub.flag",
        "results/module3/m3_repo_m2_2_variant_annotation_paths_status.json",
        "results/module3/m3_repo_m2_2_variant_annotation_paths_status.flag",
        "results/module3/m3_repo_m2_2_variant_annotation_integration_stub.json",
        "results/module3/m3_repo_m2_2_variant_annotation_integration_stub.flag",
        "results/module3/m3_repo_m2_2_depmap_mirror_paths_status.json",
        "results/module3/m3_repo_m2_2_depmap_mirror_paths_status.flag",
        "results/module3/m3_repo_m2_2_depmap_mirror_integration_stub.json",
        "results/module3/m3_repo_m2_2_depmap_mirror_integration_stub.flag",
        "results/module3/m3_repo_m2_2_maf_mutsig_mirror_paths_status.json",
        "results/module3/m3_repo_m2_2_maf_mutsig_mirror_paths_status.flag",
        "results/module3/m3_repo_m2_2_maf_mutsig_mirror_integration_stub.json",
        "results/module3/m3_repo_m2_2_maf_mutsig_mirror_integration_stub.flag",
        "results/module3/m3_repo_m2_2_outline_driver_mirror_paths_status.json",
        "results/module3/m3_repo_m2_2_outline_driver_mirror_paths_status.flag",
        "results/module3/m3_repo_m2_2_outline_driver_mirror_integration_stub.json",
        "results/module3/m3_repo_m2_2_outline_driver_mirror_integration_stub.flag",
        "results/module3/m1_outline_paths_status.json",
        "results/module3/m1_outline_paths_status.flag",
        "results/module3/m1_outline_integration_stub.json",
        "results/module3/m1_outline_integration_stub.flag",
        "results/module3/m1_harmony_batch_paths_status.json",
        "results/module3/m1_harmony_batch_paths_status.flag",
        "results/module3/m1_harmony_batch_integration_stub.json",
        "results/module3/m1_harmony_batch_integration_stub.flag",
        "results/module3/m1_reference_gdc_paths_status.json",
        "results/module3/m1_reference_gdc_paths_status.flag",
        "results/module3/m1_reference_gdc_integration_stub.json",
        "results/module3/m1_reference_gdc_integration_stub.flag",
        "results/module3/m1_batch_correction_mirror_paths_status.json",
        "results/module3/m1_batch_correction_mirror_paths_status.flag",
        "results/module3/m1_batch_correction_mirror_integration_stub.json",
        "results/module3/m1_batch_correction_mirror_integration_stub.flag",
        "results/module3/m3_repo_m1_outline_paths_status.json",
        "results/module3/m3_repo_m1_outline_paths_status.flag",
        "results/module3/m3_repo_m1_outline_integration_stub.json",
        "results/module3/m3_repo_m1_outline_integration_stub.flag",
        "results/module3/m3_repo_m1_harmony_batch_paths_status.json",
        "results/module3/m3_repo_m1_harmony_batch_paths_status.flag",
        "results/module3/m3_repo_m1_harmony_batch_integration_stub.json",
        "results/module3/m3_repo_m1_harmony_batch_integration_stub.flag",
        "results/module3/m3_repo_m1_reference_gdc_paths_status.json",
        "results/module3/m3_repo_m1_reference_gdc_paths_status.flag",
        "results/module3/m3_repo_m1_reference_gdc_integration_stub.json",
        "results/module3/m3_repo_m1_reference_gdc_integration_stub.flag",
        "results/module3/m3_repo_m1_batch_correction_mirror_paths_status.json",
        "results/module3/m3_repo_m1_batch_correction_mirror_paths_status.flag",
        "results/module3/m3_repo_m1_batch_correction_mirror_integration_stub.json",
        "results/module3/m3_repo_m1_batch_correction_mirror_integration_stub.flag",
        _rule_all_optional_inputs,


rule verify_python_environment:
    """Confirm requirements.txt imports and Snakemake CLI (manual: snakemake verify_python_environment -c1)."""
    output:
        "results/verify_python_environment.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "verify_python_environment.py")],
            cwd=str(_ROOT),
        )
        Path(output[0]).parent.mkdir(parents=True, exist_ok=True)
        Path(output[0]).write_text("ok\n", encoding="utf-8")


rule optional_third_party_python_stack:
    """
    Programmatic optional stack: pip cmapPy + GCT round-trip functional test; GNINA bootstrap/path smoke;
    10x tools optional unless GLIOMA_TARGET_REQUIRE_10X_OPTIONAL_STACK=1.
    Manual: snakemake optional_third_party_python_stack -c1
    Fast path (skip conda env bootstrap): set GLIOMA_TARGET_OPTIONAL_NO_CONDA_BOOTSTRAP=1
    Require Cell Ranger on PATH: set GLIOMA_TARGET_REQUIRE_10X_OPTIONAL_STACK=1
    Override GNINA strictness: GLIOMA_TARGET_GNINA_REQUIRED=1|0 (else OS default: required off Windows).
    CI-style (cmapPy only, no conda GNINA): set GLIOMA_TARGET_OPTIONAL_NO_CONDA_BOOTSTRAP=1 and GLIOMA_TARGET_GNINA_REQUIRED=0
    """
    input:
        tpcfg=str(_ROOT / "config" / "third_party_tooling.yaml"),
        optreq=str(_ROOT / "requirements-optional.txt"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        ok="results/optional_third_party_python.ok",
        rep="results/optional_third_party_functional_report.json",
    run:
        cmd = [
            sys.executable,
            str(_ROOT / "scripts" / "ensure_optional_third_party_functional.py"),
            "--json-out",
            "results/optional_third_party_functional_report.json",
        ]
        ev = os.environ.get("GLIOMA_TARGET_OPTIONAL_NO_CONDA_BOOTSTRAP", "").strip().lower()
        if ev in ("1", "true", "yes"):
            cmd.append("--no-bootstrap-gnina")
        if os.environ.get("GLIOMA_TARGET_REQUIRE_10X_OPTIONAL_STACK", "").strip().lower() in ("1", "true", "yes"):
            cmd.append("--require-10x-tools")
        gn = os.environ.get("GLIOMA_TARGET_GNINA_REQUIRED", "").strip().lower()
        if gn in ("1", "true", "yes"):
            cmd.append("--gnina-required")
        elif gn in ("0", "false", "no"):
            cmd.append("--no-gnina-required")
        subprocess.check_call(cmd, cwd=str(_ROOT))
        Path(output.ok).write_text("ok\n", encoding="utf-8")


rule optional_stack_ci:
    """
    Same checks as GitHub Actions job optional-stack: run_optional_stack_ci.py (pytest + ensure).
    Manual: snakemake optional_stack_ci -c1
    GLIOMA_TARGET_OPTIONAL_STACK_CI_STRICT=1  -> --strict-binaries (GNINA required on non-Windows)
    GLIOMA_TARGET_OPTIONAL_STACK_SKIP_PIP=1    -> --skip-pip on ensure
    """
    input:
        pytest_ini=str(_ROOT / "pytest.ini"),
        test_cmap=str(_ROOT / "tests" / "test_optional_cmap_py_gct_roundtrip.py"),
        test_cli=str(_ROOT / "tests" / "test_optional_stack_cli.py"),
        runner=str(_ROOT / "scripts" / "run_optional_stack_ci.py"),
        ensure=str(_ROOT / "scripts" / "ensure_optional_third_party_functional.py"),
        optreq=str(_ROOT / "requirements-optional.txt"),
        tpcfg=str(_ROOT / "config" / "third_party_tooling.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        ok="results/optional_stack_ci.ok",
        rep="results/optional_third_party_functional_report.json",
    run:
        cmd = [sys.executable, str(_ROOT / "scripts" / "run_optional_stack_ci.py")]
        if os.environ.get("GLIOMA_TARGET_OPTIONAL_STACK_CI_STRICT", "").strip().lower() in (
            "1",
            "true",
            "yes",
        ):
            cmd.append("--strict-binaries")
        if os.environ.get("GLIOMA_TARGET_OPTIONAL_STACK_SKIP_PIP", "").strip().lower() in (
            "1",
            "true",
            "yes",
        ):
            cmd.append("--skip-pip")
        subprocess.check_call(cmd, cwd=str(_ROOT))
        Path(output.ok).write_text("ok\n", encoding="utf-8")


rule verify_optional_third_party_tooling:
    """Report PATH binaries + conda gnina + pip imports (non-strict). Manual: snakemake verify_optional_third_party_tooling -c1"""
    input:
        tpcfg=str(_ROOT / "config" / "third_party_tooling.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        "results/third_party_tooling_status.json",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "verify_optional_third_party_tooling.py")],
            cwd=str(_ROOT),
        )


rule vendor_tooling_paths_status:
    """Cross-cutting: optional Cell Ranger / Space Ranger / GNINA / conda-GNINA paths under data_root and repo."""
    input:
        vcfg=str(_ROOT / "config" / "vendor_tooling_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/tooling/vendor_tooling_paths_status.json",
        flag="results/tooling/vendor_tooling_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "vendor_tooling_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule vendor_tooling_integration_stub:
    """Cross-cutting: vendor install checklist; echoes third_party_tooling_status.json when on disk."""
    input:
        vcfg=str(_ROOT / "config" / "vendor_tooling_outline_inputs.yaml"),
        js="results/tooling/vendor_tooling_paths_status.json",
        flag="results/tooling/vendor_tooling_paths_status.flag",
    output:
        out_js="results/tooling/vendor_tooling_integration_stub.json",
        out_f="results/tooling/vendor_tooling_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "vendor_tooling_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule fetch_public_data:
    """
    Full public-data pull: GEO, TOIL Xena, references, DepMap (GCS), GDC TCGA-GBM TSVs.
    Run manually: snakemake fetch_public_data -c1
    """
    output:
        "results/fetch_public_data.done",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "download_all_required.py")],
            cwd=str(_ROOT),
        )
        Path(output[0]).parent.mkdir(parents=True, exist_ok=True)
        Path(output[0]).write_text("ok\n", encoding="utf-8")


rule verify_data_layout:
    output:
        "results/data_layout_ok.flag",
    run:
        require_dir(DATA_ROOT, "data_root")
        require_dir(DATA_ROOT / "tcga" / "TCGA-GBM", "TCGA-GBM")
        require_dir(DATA_ROOT / "geo" / "scrna_seq" / "GSE57872", "GEO GSE57872")
        require_dir(DATA_ROOT / "dryad" / "spatial_gbm", "Dryad spatial_gbm")
        require_dir(
            DATA_ROOT / "geo" / "bulk_microarray" / "GSE4290" / "matrix",
            "GEO bulk_microarray GSE4290",
        )
        tpm = DATA_ROOT / "gtex" / "xena_toil" / "TcgaTargetGtex_rsem_gene_tpm.gz"
        if not tpm.is_file() or tpm.stat().st_size < 1_000_000_000:
            raise FileNotFoundError(
                f"GTEx/TOIL gene TPM missing or too small (expected ~1.3 GB .gz): {tpm}"
            )
        Path(output[0]).parent.mkdir(parents=True, exist_ok=True)
        Path(output[0]).write_text(f"data_root={DATA_ROOT.resolve()}\n", encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(_ROOT / "scripts" / "verify_data_layout.py")],
            cwd=str(_ROOT),
            env={**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)},
        )
        if r.returncode != 0:
            raise RuntimeError("verify_data_layout.py reported missing paths")


rule tcga_gbm_tpm_matrix:
    """
    Outline M1/M2 inputs: stack GDC STAR tpm_unstranded into Parquet + sample metadata (TCGA-GBM bulk RNA).
    """
    input:
        layout="results/data_layout_ok.flag",
        manifest=str(DATA_ROOT / "gdc" / "tcga_gbm_open_star_counts" / "gdc_files_manifest.json"),
    output:
        matrix="results/module2/tcga_gbm_star_tpm_matrix.parquet",
        meta="results/module2/tcga_gbm_sample_meta.tsv",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "build_gdc_gbm_expression_matrix.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule tcga_gbm_counts_matrix:
    """
    Outline M2 §2.1 (future DESeq2/edgeR): STAR unstranded integer counts; within-TCGA DE or matched normal counts.
    Depends on TPM matrix so sample meta is written once (no concurrent meta overwrite).
    """
    input:
        layout="results/data_layout_ok.flag",
        tpm_matrix="results/module2/tcga_gbm_star_tpm_matrix.parquet",
        manifest=str(DATA_ROOT / "gdc" / "tcga_gbm_open_star_counts" / "gdc_files_manifest.json"),
    output:
        "results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "build_gdc_gbm_expression_matrix.py"),
                "--kind",
                "counts",
            ],
            cwd=str(_ROOT),
            env=env,
        )


rule toil_gbm_brain_tpm:
    """Outline M2 §2.1: TOIL RSEM hub subset — GBM primary + GTEx brain (single pipeline vs tumor+normal)."""
    input:
        tpm=str(DATA_ROOT / "gtex" / "xena_toil" / "TcgaTargetGtex_rsem_gene_tpm.gz"),
        pheno=str(DATA_ROOT / "gtex" / "xena_toil" / "TcgaTargetGTEX_phenotype.txt.gz"),
    output:
        expr="results/module3/toil_gbm_vs_brain_tpm.parquet",
        samples="results/module3/toil_gbm_vs_brain_samples.tsv",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "extract_toil_gbm_brain_tpm.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule expression_cohort_summary:
    """QC JSON: sample counts, GTEx region breakdown, parquet/manifest column cross-check + outline traceability."""
    input:
        expr="results/module3/toil_gbm_vs_brain_tpm.parquet",
        samples="results/module3/toil_gbm_vs_brain_samples.tsv",
        trace=str(_ROOT / "config" / "methods_traceability.yaml"),
    output:
        "results/module3/cohort_design_summary.json",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "summarize_expression_cohort.py")],
            cwd=str(_ROOT),
        )


rule validate_gdc_counts_matrix:
    """Sanity checks on STAR unstranded integer matrix (written next to rule output)."""
    input:
        "results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet",
    output:
        "results/module2/gdc_counts_matrix_qc.json",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "validate_gdc_counts_matrix.py")],
            cwd=str(_ROOT),
        )


rule gdc_counts_cohort_summary:
    """Outline M2.1 prep: counts matrix vs sample meta overlap, sparsity, library scale (for future DESeq2/edgeR design)."""
    input:
        counts="results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet",
        meta="results/module2/tcga_gbm_sample_meta.tsv",
    output:
        "results/module2/gdc_counts_cohort_summary.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "summarize_gdc_counts_cohort.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_deseq2_tcga_primary_recurrent:
    """
    Milestone M2.1 (partial): PyDESeq2 on GDC STAR integer counts — Recurrent vs Primary (within TCGA-GBM).
    Requires pydeseq2 (requirements-optional.txt). Does not use GTEx normals (separate pipeline).
    """
    input:
        counts="results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet",
        meta="results/module2/tcga_gbm_sample_meta.tsv",
        cfg=str(_ROOT / "config" / "deseq2_tcga_gbm.yaml"),
    output:
        tsv="results/module3/deseq2_tcga_gbm/primary_vs_recurrent/deseq2_results.tsv",
        prov="results/module3/deseq2_tcga_gbm/primary_vs_recurrent/deseq2_provenance.json",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "dea_deseq2_tcga_primary_recurrent.py")],
            cwd=str(_ROOT),
        )


rule m2_deseq2_tcga_primary_vs_solid_normal:
    """
    M2.1 extension: PyDESeq2 Primary Tumor vs TCGA Solid Tissue Normal (n=5) on the same STAR matrix.
    Very low power; provenance lists caveats. Requires pydeseq2.
    """
    input:
        counts="results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet",
        meta="results/module2/tcga_gbm_sample_meta.tsv",
        cfg=str(_ROOT / "config" / "deseq2_tcga_gbm.yaml"),
    output:
        tsv="results/module3/deseq2_tcga_gbm/primary_vs_solid_tissue_normal/deseq2_results.tsv",
        prov="results/module3/deseq2_tcga_gbm/primary_vs_solid_tissue_normal/deseq2_provenance.json",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "dea_deseq2_tcga_primary_vs_solid_normal.py")],
            cwd=str(_ROOT),
        )


rule m2_edger_tcga_primary_recurrent:
    """
    M2.1: edgeR glmQLF on the same aggregated STAR counts as PyDESeq2 — Recurrent vs Primary.
    Needs Rscript (see _rscript_exe: RSCRIPT, R_HOME, config rscript, or PATH) plus CRAN/Bioconductor packages.
    """
    input:
        counts="results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet",
        meta="results/module2/tcga_gbm_sample_meta.tsv",
        cfg=str(_ROOT / "config" / "deseq2_tcga_gbm.yaml"),
        rscript=str(_ROOT / "scripts" / "edger_tcga_gbm_two_group.R"),
    output:
        tsv="results/module3/edger_tcga_gbm/primary_vs_recurrent/edger_qlf_results.tsv",
        prov="results/module3/edger_tcga_gbm/primary_vs_recurrent/edger_provenance.json",
    run:
        subprocess.check_call(
            [
                _rscript_exe(),
                str(_ROOT / "scripts" / "edger_tcga_gbm_two_group.R"),
                "deseq2_tcga_primary_vs_recurrent",
            ],
            cwd=str(_ROOT),
        )


rule m2_edger_tcga_primary_vs_solid_normal:
    """
    M2.1: edgeR glmQLF Primary Tumor vs Solid Tissue Normal (n=5); same caveats as PyDESeq2 stub.
    """
    input:
        counts="results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet",
        meta="results/module2/tcga_gbm_sample_meta.tsv",
        cfg=str(_ROOT / "config" / "deseq2_tcga_gbm.yaml"),
        rscript=str(_ROOT / "scripts" / "edger_tcga_gbm_two_group.R"),
    output:
        tsv="results/module3/edger_tcga_gbm/primary_vs_solid_tissue_normal/edger_qlf_results.tsv",
        prov="results/module3/edger_tcga_gbm/primary_vs_solid_tissue_normal/edger_provenance.json",
    run:
        subprocess.check_call(
            [
                _rscript_exe(),
                str(_ROOT / "scripts" / "edger_tcga_gbm_two_group.R"),
                "deseq2_tcga_primary_vs_solid_normal",
            ],
            cwd=str(_ROOT),
        )


rule m2_deseq2_recount3_tcga_gbm_vs_gtex_brain:
    """
    PyDESeq2 on recount3 harmonized G029 gene counts: TCGA-GBM tumor vs GTEx brain normal.
    Writes recount3_de_counts_matrix.parquet + recount3_de_sample_meta.tsv for edgeR (m2_edger_recount3_*).
    Downloads .gz to data_root/recount3/harmonized_g029 (override with env RECOUNT3_CACHE_DIR).
    Not GDC STAR — see deseq2_provenance.json. Requires pydeseq2.
    """
    input:
        star="results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet",
        cfg=str(_ROOT / "config" / "deseq2_recount3_tcga_gtex.yaml"),
        py=str(_ROOT / "scripts" / "dea_deseq2_recount3_tcga_gbm_vs_gtex_brain.py"),
        shared=str(_ROOT / "scripts" / "recount3_tcga_gbm_gtex_brain_matrix.py"),
    output:
        tsv="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_results.tsv",
        prov="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_provenance.json",
        matrix="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/recount3_de_counts_matrix.parquet",
        meta="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/recount3_de_sample_meta.tsv",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "dea_deseq2_recount3_tcga_gbm_vs_gtex_brain.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_edger_recount3_tcga_gbm_vs_gtex_brain:
    """
    edgeR glmQLF on the same recount3 integer matrix as m2_deseq2_recount3_tcga_gbm_vs_gtex_brain.
    """
    input:
        matrix="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/recount3_de_counts_matrix.parquet",
        meta="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/recount3_de_sample_meta.tsv",
        cfg=str(_ROOT / "config" / "deseq2_recount3_tcga_gtex.yaml"),
        rscript=str(_ROOT / "scripts" / "edger_recount3_tcga_gbm_vs_gtex_brain.R"),
    output:
        tsv="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_qlf_results.tsv",
        prov="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_provenance.json",
    run:
        subprocess.check_call(
            [_rscript_exe(), str(_ROOT / "scripts" / "edger_recount3_tcga_gbm_vs_gtex_brain.R")],
            cwd=str(_ROOT),
        )


rule m2_recount3_deseq2_edger_concordance:
    """Spearman concordance between PyDESeq2 and edgeR on the same recount3 matrix (requires scipy)."""
    input:
        py="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_results.tsv",
        ed="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_qlf_results.tsv",
        script=str(_ROOT / "scripts" / "compare_recount3_pydeseq2_edger.py"),
    output:
        js="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_vs_edger_concordance.json",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "compare_recount3_pydeseq2_edger.py")],
            cwd=str(_ROOT),
        )


rule m2_toil_welch_vs_recount3_bulk_effect_correlation:
    """Cross-assay: TOIL Welch + OLS TPM effects vs recount3 PyDESeq2/edgeR LFC (matched ENSG; scipy)."""
    input:
        welch="results/module3/dea_gbm_vs_gtex_brain.tsv",
        ols="results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv",
        py="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_results.tsv",
        ed="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_qlf_results.tsv",
        script=str(_ROOT / "scripts" / "compare_toil_bulk_vs_recount3_effects.py"),
    output:
        "results/module3/toil_welch_vs_recount3_bulk_effect_correlation.json",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "compare_toil_bulk_vs_recount3_effects.py")],
            cwd=str(_ROOT),
        )


rule m1_combat_seq_tcga_gbm_primary:
    """
    M1 stub: ComBat-Seq (sva) on Primary Tumor GDC STAR counts; batch = TCGA TSS code from barcode.
    Requires R + Bioconductor sva and CRAN yaml/jsonlite/arrow. See combat_seq_provenance.json caveats.
    """
    input:
        counts="results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet",
        meta="results/module2/tcga_gbm_sample_meta.tsv",
        cfg=str(_ROOT / "config" / "combat_seq_tcga_gbm.yaml"),
        rscript=str(_ROOT / "scripts" / "combat_seq_tcga_gbm_subset.R"),
    output:
        pq="results/module1/combat_seq_tcga_gbm_primary/combat_seq_adjusted_counts.parquet",
        prov="results/module1/combat_seq_tcga_gbm_primary/combat_seq_provenance.json",
    run:
        subprocess.check_call(
            [
                _rscript_exe(),
                str(_ROOT / "scripts" / "combat_seq_tcga_gbm_subset.R"),
                str(_ROOT / "config" / "combat_seq_tcga_gbm.yaml"),
            ],
            cwd=str(_ROOT),
        )


rule m1_outline_paths_status:
    """Outline M1: grouped optional paths (cohorts, FASTQ, harmonized omics) under data_root."""
    input:
        m1cfg=str(_ROOT / "config" / "m1_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m1_outline_paths_status.json",
        flag="results/module3/m1_outline_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module1_outline_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m1_outline_integration_stub:
    """Outline M1: FASTQ/cohort/harmonized-omics gap checklist (paths + optional ComBat provenance)."""
    input:
        m1cfg=str(_ROOT / "config" / "m1_outline_inputs.yaml"),
        js="results/module3/m1_outline_paths_status.json",
        flag="results/module3/m1_outline_paths_status.flag",
    output:
        out_js="results/module3/m1_outline_integration_stub.json",
        out_f="results/module3/m1_outline_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module1_outline_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m1_harmony_batch_paths_status:
    """Outline M1 supplement: optional Harmony / scRNA batch covariate staging under data_root."""
    input:
        m1hcfg=str(_ROOT / "config" / "m1_harmony_batch_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m1_harmony_batch_paths_status.json",
        flag="results/module3/m1_harmony_batch_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m1_harmony_batch_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m1_harmony_batch_integration_stub:
    """Outline M1 supplement: Harmony vs ComBat-Seq gap checklist (after m1_outline_integration_stub)."""
    input:
        m1hcfg=str(_ROOT / "config" / "m1_harmony_batch_outline_inputs.yaml"),
        js="results/module3/m1_harmony_batch_paths_status.json",
        flag="results/module3/m1_harmony_batch_paths_status.flag",
        m1_stub_js="results/module3/m1_outline_integration_stub.json",
        m1_stub_f="results/module3/m1_outline_integration_stub.flag",
    output:
        out_js="results/module3/m1_harmony_batch_integration_stub.json",
        out_f="results/module3/m1_harmony_batch_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m1_harmony_batch_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m1_reference_gdc_paths_status:
    """Outline M1: optional reference bundle + GDC open STAR staging under data_root (presence only)."""
    input:
        m1rg=str(_ROOT / "config" / "m1_reference_gdc_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m1_reference_gdc_paths_status.json",
        flag="results/module3/m1_reference_gdc_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m1_reference_gdc_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m1_reference_gdc_integration_stub:
    """Outline M1: reference/GDC staging checklist (after M1 outline stub; GDC QC echo when on disk)."""
    input:
        m1rg=str(_ROOT / "config" / "m1_reference_gdc_outline_inputs.yaml"),
        js="results/module3/m1_reference_gdc_paths_status.json",
        flag="results/module3/m1_reference_gdc_paths_status.flag",
        m1_outline_stub_js="results/module3/m1_outline_integration_stub.json",
        m1_outline_stub_f="results/module3/m1_outline_integration_stub.flag",
    output:
        out_js="results/module3/m1_reference_gdc_integration_stub.json",
        out_f="results/module3/m1_reference_gdc_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m1_reference_gdc_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m1_batch_correction_mirror_paths_status:
    """Outline M1 optional ComBat-Seq or cross-cohort batch-corrected count mirrors under data_root (presence only)."""
    input:
        m1bcmcfg=str(_ROOT / "config" / "m1_batch_correction_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m1_batch_correction_mirror_paths_status.json",
        flag="results/module3/m1_batch_correction_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m1_batch_correction_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m1_batch_correction_mirror_integration_stub:
    """Outline M1 batch-correction mirror checklist (Harmony stub echo; combat_seq_tcga_gbm provenance path)."""
    input:
        m1bcmcfg=str(_ROOT / "config" / "m1_batch_correction_mirror_outline_inputs.yaml"),
        js="results/module3/m1_batch_correction_mirror_paths_status.json",
        flag="results/module3/m1_batch_correction_mirror_paths_status.flag",
        harm_stub_js="results/module3/m1_harmony_batch_integration_stub.json",
        harm_stub_f="results/module3/m1_harmony_batch_integration_stub.flag",
        combat_cfg=str(_ROOT / "config" / "combat_seq_tcga_gbm.yaml"),
    output:
        out_js="results/module3/m1_batch_correction_mirror_integration_stub.json",
        out_f="results/module3/m1_batch_correction_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m1_batch_correction_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_m1_outline_paths_status:
    """Outline M1: results/module3 m1_outline path-status + integration_stub JSON/flag presence (M3 manifest slice)."""
    input:
        m3r1ocfg=str(_ROOT / "config" / "m3_repo_m1_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_m1_outline_paths_status.json",
        flag="results/module3/m3_repo_m1_outline_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m1_outline_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_m1_outline_integration_stub:
    """Outline M1: M1 outline repo manifest slice (echoes m1_outline stub + paths_status JSON)."""
    input:
        m3r1ocfg=str(_ROOT / "config" / "m3_repo_m1_outline_inputs.yaml"),
        js="results/module3/m3_repo_m1_outline_paths_status.json",
        flag="results/module3/m3_repo_m1_outline_paths_status.flag",
        m1o_js="results/module3/m1_outline_paths_status.json",
        m1o_f="results/module3/m1_outline_paths_status.flag",
        m1o_stub_js="results/module3/m1_outline_integration_stub.json",
        m1o_stub_f="results/module3/m1_outline_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_m1_outline_integration_stub.json",
        out_f="results/module3/m3_repo_m1_outline_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m1_outline_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_m1_harmony_batch_paths_status:
    """Outline M1: results/module3 m1_harmony_batch quartet presence (M3 manifest slice)."""
    input:
        m3r1hbcfg=str(_ROOT / "config" / "m3_repo_m1_harmony_batch_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_m1_harmony_batch_paths_status.json",
        flag="results/module3/m3_repo_m1_harmony_batch_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m1_harmony_batch_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_m1_harmony_batch_integration_stub:
    """Outline M1: Harmony batch repo manifest slice (echoes harmony + m1_outline stubs)."""
    input:
        m3r1hbcfg=str(_ROOT / "config" / "m3_repo_m1_harmony_batch_outline_inputs.yaml"),
        js="results/module3/m3_repo_m1_harmony_batch_paths_status.json",
        flag="results/module3/m3_repo_m1_harmony_batch_paths_status.flag",
        m1hb_js="results/module3/m1_harmony_batch_paths_status.json",
        m1hb_f="results/module3/m1_harmony_batch_paths_status.flag",
        m1hb_stub_js="results/module3/m1_harmony_batch_integration_stub.json",
        m1hb_stub_f="results/module3/m1_harmony_batch_integration_stub.flag",
        m1o_stub_js="results/module3/m1_outline_integration_stub.json",
        m1o_stub_f="results/module3/m1_outline_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_m1_harmony_batch_integration_stub.json",
        out_f="results/module3/m3_repo_m1_harmony_batch_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m1_harmony_batch_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_m1_reference_gdc_paths_status:
    """Outline M1: results/module3 m1_reference_gdc quartet presence (M3 manifest slice)."""
    input:
        m3r1rgcfg=str(_ROOT / "config" / "m3_repo_m1_reference_gdc_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_m1_reference_gdc_paths_status.json",
        flag="results/module3/m3_repo_m1_reference_gdc_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m1_reference_gdc_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_m1_reference_gdc_integration_stub:
    """Outline M1: reference/GDC repo manifest slice (echoes reference/GDC + m1_outline stubs)."""
    input:
        m3r1rgcfg=str(_ROOT / "config" / "m3_repo_m1_reference_gdc_outline_inputs.yaml"),
        js="results/module3/m3_repo_m1_reference_gdc_paths_status.json",
        flag="results/module3/m3_repo_m1_reference_gdc_paths_status.flag",
        m1rg_js="results/module3/m1_reference_gdc_paths_status.json",
        m1rg_f="results/module3/m1_reference_gdc_paths_status.flag",
        m1rg_stub_js="results/module3/m1_reference_gdc_integration_stub.json",
        m1rg_stub_f="results/module3/m1_reference_gdc_integration_stub.flag",
        m1o_stub_js="results/module3/m1_outline_integration_stub.json",
        m1o_stub_f="results/module3/m1_outline_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_m1_reference_gdc_integration_stub.json",
        out_f="results/module3/m3_repo_m1_reference_gdc_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m1_reference_gdc_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_m1_batch_correction_mirror_paths_status:
    """Outline M1: results/module3 m1_batch_correction_mirror quartet presence (M3 manifest slice)."""
    input:
        m3r1bcmcfg=str(_ROOT / "config" / "m3_repo_m1_batch_correction_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_m1_batch_correction_mirror_paths_status.json",
        flag="results/module3/m3_repo_m1_batch_correction_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m1_batch_correction_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_m1_batch_correction_mirror_integration_stub:
    """Outline M1: batch-correction mirror repo manifest slice (echoes BCM + Harmony stubs)."""
    input:
        m3r1bcmcfg=str(_ROOT / "config" / "m3_repo_m1_batch_correction_mirror_outline_inputs.yaml"),
        js="results/module3/m3_repo_m1_batch_correction_mirror_paths_status.json",
        flag="results/module3/m3_repo_m1_batch_correction_mirror_paths_status.flag",
        m1bcm_js="results/module3/m1_batch_correction_mirror_paths_status.json",
        m1bcm_f="results/module3/m1_batch_correction_mirror_paths_status.flag",
        m1bcm_stub_js="results/module3/m1_batch_correction_mirror_integration_stub.json",
        m1bcm_stub_f="results/module3/m1_batch_correction_mirror_integration_stub.flag",
        m1hb_stub_js="results/module3/m1_harmony_batch_integration_stub.json",
        m1hb_stub_f="results/module3/m1_harmony_batch_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_m1_batch_correction_mirror_integration_stub.json",
        out_f="results/module3/m3_repo_m1_batch_correction_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "m3_repo_m1_batch_correction_mirror_integration_stub.py"),
            ],
            cwd=str(_ROOT),
        )


rule m3_public_inputs_status:
    """Outline M3: record which public scRNA/spatial paths exist under data_root (non-fatal if missing)."""
    input:
        m3cfg=str(_ROOT / "config" / "module3_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/module3_public_inputs_status.json",
        flag="results/module3/module3_public_inputs_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module3_public_inputs_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_sc_workflow_paths_status:
    """Outline M3 prep: optional Scanpy/Seurat/Visium workflow paths under data_root (presence only)."""
    input:
        m3cfg=str(_ROOT / "config" / "module3_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/module3_sc_workflow_paths_status.json",
        flag="results/module3/module3_sc_workflow_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module3_sc_workflow_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule supplementary_reference_resources_paths_status:
    """ARCHS4/Atlas/pathways/drug-target/variant supplementary files under data_root (presence only)."""
    input:
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/supplementary_reference_resources_paths_status.json",
        flag="results/module3/supplementary_reference_resources_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "supplementary_reference_resources_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule check_wikipathways_gmt_url:
    """HEAD the WikiPathways GMT URL from supplementary_reference_resources.yaml (fails build if 404)."""
    input:
        cfg=str(_ROOT / "config" / "supplementary_reference_resources.yaml"),
    output:
        flag="results/module3/wikipathways_gmt_url_ok.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "check_wikipathways_gmt_url.py")],
            cwd=str(_ROOT),
        )
        Path(output.flag).parent.mkdir(parents=True, exist_ok=True)
        Path(output.flag).write_text("ok\n", encoding="utf-8")


rule pathwaycommons_hgnc_gmt_plain:
    """Expand PathwayCommons12.All.hgnc.gmt.gz to plain .gmt for tools that do not read gzip."""
    input:
        gz=str(DATA_ROOT / "references" / "pathways" / "PathwayCommons12.All.hgnc.gmt.gz"),
    output:
        gmt=str(DATA_ROOT / "references" / "pathways" / "PathwayCommons12.All.hgnc.gmt"),
        flag="results/module4/pathwaycommons_hgnc_gmt_plain.flag",
    run:
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "decompress_pathwaycommons_gmt.py"),
                "--gz",
                str(input.gz),
                "--out",
                str(output.gmt),
            ],
            cwd=str(_ROOT),
        )
        Path(output.flag).parent.mkdir(parents=True, exist_ok=True)
        Path(output.flag).write_text("ok\n", encoding="utf-8")


rule m4_supplementary_open_enrichment_plan:
    """JSON + R script wiring WikiPathways + PathwayCommons GMTs to fgsea (run R separately)."""
    input:
        ds=str(_ROOT / "config" / "data_sources.yaml"),
        wiki=str(DATA_ROOT / "references" / "pathways" / "wikipathways-Homo_sapiens.gmt"),
        pc_done="results/module4/pathwaycommons_hgnc_gmt_plain.flag",
    output:
        js="results/module4/m4_supplementary_open_enrichment_plan.json",
        r="results/module4/r_external/fgsea_supplementary_pathways.R",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "build_m4_supplementary_enrichment_plan.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule archs4_recount_h5_summary:
    """Summarize ARCHS4/recount HDF5 layouts (optional h5py; see requirements-optional.txt)."""
    input:
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module4/archs4_recount_h5_summary.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "archs4_recount_h5_summarize.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule install_r_supplementary_enrichment:
    """One-time Bioconductor/CRAN installs for fgsea + clusterProfiler (R required)."""
    input:
        rscript=str(_ROOT / "scripts" / "install_r_supplementary_enrichment.R"),
    output:
        flag="results/r_supplementary_enrichment_packages.flag",
    run:
        subprocess.check_call([_rscript_exe(), str(input.rscript)], cwd=str(_ROOT))
        Path(output.flag).parent.mkdir(parents=True, exist_ok=True)
        Path(output.flag).write_text("ok\n", encoding="utf-8")


rule sync_wikipathways_gmt_url_report:
    """Compare YAML WikiPathways GMT URL to latest on wmcloud index (no YAML write)."""
    input:
        sync_py=str(_ROOT / "scripts" / "sync_wikipathways_gmt_url.py"),
    output:
        js="results/reports/wikipathways_gmt_url_sync.json",
    run:
        subprocess.check_call(
            [sys.executable, str(input.sync_py)],
            cwd=str(_ROOT),
        )


rule m4_clusterprofiler_supplementary_plan:
    """Emit clusterProfiler enricher R script (ORA vs prerank universe)."""
    input:
        ds=str(_ROOT / "config" / "data_sources.yaml"),
        dea="results/module3/dea_gbm_vs_gtex_brain.tsv",
        rnk="results/module4/gsea/dea_welch_signed_neg_log10_p.rnk",
        hgnc=str(DATA_ROOT / "references" / "hgnc_complete_set.txt"),
        wiki=str(DATA_ROOT / "references" / "pathways" / "wikipathways-Homo_sapiens.gmt"),
        pc_done="results/module4/pathwaycommons_hgnc_gmt_plain.flag",
    output:
        js="results/module4/m4_clusterprofiler_supplementary_plan.json",
        r="results/module4/r_external/clusterprofiler_supplementary_pathways.R",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "build_m4_clusterprofiler_enrichment_plan.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m4_run_fgsea_supplementary_pathways:
    """Run fgsea on WikiPathways + PathwayCommons GMTs (multilevel test; minSize/maxSize bounded)."""
    input:
        r_ok="results/r_supplementary_enrichment_packages.flag",
        rscript="results/module4/r_external/fgsea_supplementary_pathways.R",
        rnk="results/module4/gsea/dea_welch_signed_neg_log10_p.rnk",
    output:
        tsv="results/module4/gsea/fgsea_supplementary_pathways_results.tsv",
    run:
        subprocess.check_call([_rscript_exe(), str(input.rscript)], cwd=str(_ROOT))


rule m4_run_clusterprofiler_supplementary_pathways:
    """Run clusterProfiler::enricher on DEA FDR hits vs custom GMT TERM2GENE."""
    input:
        r_ok="results/r_supplementary_enrichment_packages.flag",
        rscript="results/module4/r_external/clusterprofiler_supplementary_pathways.R",
        rnk="results/module4/gsea/dea_welch_signed_neg_log10_p.rnk",
    output:
        tsv="results/module4/gsea/clusterprofiler_supplementary_enricher.tsv",
    run:
        subprocess.check_call([_rscript_exe(), str(input.rscript)], cwd=str(_ROOT))


rule archs4_outline_driver_expression_context:
    """Mean log1p ARCHS4 counts for outline GBM driver symbols (GTEx + TCGA HDF5)."""
    input:
        ds=str(_ROOT / "config" / "data_sources.yaml"),
        drivers=str(_ROOT / "references" / "gbm_known_drivers_outline.yaml"),
        gtex=str(DATA_ROOT / "references" / "archs4_recount" / "gtex_matrix.h5"),
        tcga=str(DATA_ROOT / "references" / "archs4_recount" / "tcga_matrix.h5"),
    output:
        js="results/module4/archs4_outline_driver_expression_context.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "archs4_outline_driver_expression_context.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule drugcentral_postgres_load_status:
    """Load DrugCentral SQL gzip into Postgres when GLIOMA_TARGET_DRUGCENTRAL_LOAD=1; else skip JSON."""
    input:
        py=str(_ROOT / "scripts" / "drugcentral_postgres_load_status.py"),
    output:
        js="results/module4/drugcentral_postgres_load_status.json",
    run:
        subprocess.check_call(
            [sys.executable, str(input.py)],
            cwd=str(_ROOT),
            env={**os.environ},
        )


rule m3_scrna_spatial_integration_stub:
    """Outline M3: merge public + sc/spatial path status into one planning JSON (no scRNA execution)."""
    input:
        m3cfg=str(_ROOT / "config" / "module3_inputs.yaml"),
        pub_js="results/module3/module3_public_inputs_status.json",
        pub_f="results/module3/module3_public_inputs_status.flag",
        sc_js="results/module3/module3_sc_workflow_paths_status.json",
        sc_f="results/module3/module3_sc_workflow_paths_status.flag",
    output:
        js="results/module3/scrna_spatial_integration_stub.json",
        flag="results/module3/scrna_spatial_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module3_scrna_spatial_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_public_inputs_paths_status:
    """Outline M3: results/module3 module3_public_inputs_status JSON/flag presence."""
    input:
        m3rpicfg=str(_ROOT / "config" / "m3_repo_public_inputs_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_public_inputs_paths_status.json",
        flag="results/module3/m3_repo_public_inputs_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_public_inputs_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_public_inputs_integration_stub:
    """Outline M3: public-inputs repo manifest slice (echoes module3_public_inputs + scrna_spatial stub)."""
    input:
        m3rpicfg=str(_ROOT / "config" / "m3_repo_public_inputs_outline_inputs.yaml"),
        js="results/module3/m3_repo_public_inputs_paths_status.json",
        flag="results/module3/m3_repo_public_inputs_paths_status.flag",
        pub_js="results/module3/module3_public_inputs_status.json",
        pub_f="results/module3/module3_public_inputs_status.flag",
        scrna_js="results/module3/scrna_spatial_integration_stub.json",
        scrna_f="results/module3/scrna_spatial_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_public_inputs_integration_stub.json",
        out_f="results/module3/m3_repo_public_inputs_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_public_inputs_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_sc_workflow_paths_status:
    """Outline M3: results/module3 module3_sc_workflow_paths_status JSON/flag presence."""
    input:
        m3rswcfg=str(_ROOT / "config" / "m3_repo_sc_workflow_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_sc_workflow_paths_status.json",
        flag="results/module3/m3_repo_sc_workflow_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_sc_workflow_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_sc_workflow_integration_stub:
    """Outline M3: sc-workflow repo manifest slice (echoes module3_sc_workflow_paths + scrna_spatial stub)."""
    input:
        m3rswcfg=str(_ROOT / "config" / "m3_repo_sc_workflow_outline_inputs.yaml"),
        js="results/module3/m3_repo_sc_workflow_paths_status.json",
        flag="results/module3/m3_repo_sc_workflow_paths_status.flag",
        scw_js="results/module3/module3_sc_workflow_paths_status.json",
        scw_f="results/module3/module3_sc_workflow_paths_status.flag",
        scrna_js="results/module3/scrna_spatial_integration_stub.json",
        scrna_f="results/module3/scrna_spatial_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_sc_workflow_integration_stub.json",
        out_f="results/module3/m3_repo_sc_workflow_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_sc_workflow_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_scrna_spatial_paths_status:
    """Outline M3: results/module3 module3_sc_workflow + scrna_spatial_integration_stub JSON/flag presence."""
    input:
        m3rsscfg=str(_ROOT / "config" / "m3_repo_scrna_spatial_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_scrna_spatial_paths_status.json",
        flag="results/module3/m3_repo_scrna_spatial_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_scrna_spatial_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_scrna_spatial_integration_stub:
    """Outline M3: scRNA/spatial quartet checklist (echoes scrna_spatial, deconvolution, Cell Ranger stubs)."""
    input:
        m3rsscfg=str(_ROOT / "config" / "m3_repo_scrna_spatial_outline_inputs.yaml"),
        js="results/module3/m3_repo_scrna_spatial_paths_status.json",
        flag="results/module3/m3_repo_scrna_spatial_paths_status.flag",
        scw_js="results/module3/module3_sc_workflow_paths_status.json",
        scw_f="results/module3/module3_sc_workflow_paths_status.flag",
        scrna_js="results/module3/scrna_spatial_integration_stub.json",
        scrna_f="results/module3/scrna_spatial_integration_stub.flag",
        m3dec_stub_js="results/module3/m3_deconvolution_integration_stub.json",
        m3dec_stub_f="results/module3/m3_deconvolution_integration_stub.flag",
        m3cr_stub_js="results/module3/m3_cellranger_output_integration_stub.json",
        m3cr_stub_f="results/module3/m3_cellranger_output_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_scrna_spatial_integration_stub.json",
        out_f="results/module3/m3_repo_scrna_spatial_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_scrna_spatial_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_deconvolution_s2_nnls:
    """
    M3 S2: scipy NNLS on real reference + spatial wide TSVs under data_root (optional rule all).
    Not RCTD/Cell2location. Paths: config/m3_deconvolution_s2_nnls.yaml.
    """
    input:
        cfg=str(_ROOT / "config" / "m3_deconvolution_s2_nnls.yaml"),
        py=str(_ROOT / "scripts" / "run_m3_deconvolution_s2_nnls.py"),
        ref_tsv=lambda wildcards: _m3_s2_reference_profile_tsv(),
        spat_tsv=lambda wildcards: _m3_s2_spatial_counts_tsv(),
    output:
        frac="results/module3/m3_deconvolution_s2/spot_celltype_fractions.tsv",
        prov="results/module3/m3_deconvolution_s2/deconvolution_s2_provenance.json",
        flag="results/module3/m3_deconvolution_s2/deconvolution_s2.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "run_m3_deconvolution_s2_nnls.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_deconvolution_rctd_run:
    """
    M3: shell RCTD (R spacexr) on user-staged Reference + SpatialRNA RDS under data_root.
    Optional rule all: GLIOMA_TARGET_INCLUDE_M3_RCTD_RUN=1. Conda: m3_rctd.yaml, or m3_rctd_spacexr_bioconda.yaml when
    GLIOMA_TARGET_M3_RCTD_BUNDLE_SPACEXR=1 (Linux/macOS; Bioconda spacexr).
    rctd_run_provenance.json is always written; rctd_run.flag only when provenance status is ok (wrapper exits 1 otherwise).
    """
    input:
        cfg=str(_ROOT / "config" / "m3_deconvolution_rctd_inputs.yaml"),
        py=str(_ROOT / "scripts" / "run_m3_rctd_orchestrate.py"),
        ref_rds=lambda wildcards: _m3_rctd_reference_rds(),
        spat_rds=lambda wildcards: _m3_rctd_spatial_rds(),
    output:
        prov="results/module3/m3_deconvolution_rctd/rctd_run_provenance.json",
        flag="results/module3/m3_deconvolution_rctd/rctd_run.flag",
    conda:
        str(_m3_rctd_conda_env_path())
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "run_m3_rctd_orchestrate.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_deconvolution_cell2location_run:
    """
    M3: Cell2location (Python) on user-staged reference + spatial AnnData h5ad under data_root.
    Optional rule all: GLIOMA_TARGET_INCLUDE_M3_CELL2LOCATION_RUN=1. Conda env: m3_cell2location.yaml (training) or
    m3_cell2location_light.yaml when GLIOMA_TARGET_M3_C2L_CONDA_ENV=light (validate-only; training.enabled must be false).
    Config file defaults to config/m3_deconvolution_cell2location_inputs.yaml; override with GLIOMA_TARGET_M3_CELL2LOCATION_CONFIG.
    When config training.enabled is true, Snakemake also tracks output_result_h5ad / output_abundance_tsv (YAML).
    cell2location_run_provenance.json is always written on an orchestrator run; cell2location_run.flag only when the script exits 0.
    """
    input:
        cfg=lambda wildcards: str(_m3_cell2location_config_path()),
        py=str(_ROOT / "scripts" / "run_m3_cell2location_orchestrate.py"),
        ref_h5ad=lambda wildcards: _m3_cell2location_ref_h5ad(),
        spat_h5ad=lambda wildcards: _m3_cell2location_spatial_h5ad(),
    output:
        **_M3_C2L_RUN_OUTPUTS,
    conda:
        str(_m3_cell2location_conda_env_path())
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "run_m3_cell2location_orchestrate.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_deconvolution_paths_status:
    """Outline M3: deconvolution / pseudobulk cell-state DE optional staging paths under data_root."""
    input:
        m3decfg=str(_ROOT / "config" / "m3_deconvolution_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_deconvolution_paths_status.json",
        flag="results/module3/m3_deconvolution_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module3_deconvolution_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_deconvolution_integration_stub:
    """Outline M3: deconvolution + cell-state DE gap checklist (after scRNA/spatial integration stub)."""
    input:
        m3decfg=str(_ROOT / "config" / "m3_deconvolution_outline_inputs.yaml"),
        js="results/module3/m3_deconvolution_paths_status.json",
        flag="results/module3/m3_deconvolution_paths_status.flag",
        scrna_js="results/module3/scrna_spatial_integration_stub.json",
        scrna_f="results/module3/scrna_spatial_integration_stub.flag",
    output:
        out_js="results/module3/m3_deconvolution_integration_stub.json",
        out_f="results/module3/m3_deconvolution_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module3_deconvolution_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_cellranger_output_paths_status:
    """Outline M3: optional Cell Ranger / Space Ranger processed outs under data_root."""
    input:
        m3crcfg=str(_ROOT / "config" / "m3_cellranger_output_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_cellranger_output_paths_status.json",
        flag="results/module3/m3_cellranger_output_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_cellranger_output_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_cellranger_output_integration_stub:
    """Outline M3: processed single-cell matrix staging checklist (after scRNA/spatial stub)."""
    input:
        m3crcfg=str(_ROOT / "config" / "m3_cellranger_output_outline_inputs.yaml"),
        js="results/module3/m3_cellranger_output_paths_status.json",
        flag="results/module3/m3_cellranger_output_paths_status.flag",
        scrna_js="results/module3/scrna_spatial_integration_stub.json",
        scrna_f="results/module3/scrna_spatial_integration_stub.flag",
    output:
        out_js="results/module3/m3_cellranger_output_integration_stub.json",
        out_f="results/module3/m3_cellranger_output_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_cellranger_output_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_deconvolution_paths_status:
    """Outline M3: results/module3 m3_deconvolution path-status + integration_stub JSON/flag presence."""
    input:
        m3rdeccfg=str(_ROOT / "config" / "m3_repo_deconvolution_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_deconvolution_paths_status.json",
        flag="results/module3/m3_repo_deconvolution_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_deconvolution_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_deconvolution_integration_stub:
    """Outline M3: deconvolution repo manifest slice (echoes m3_deconvolution + m3_repo_scrna_spatial stubs)."""
    input:
        m3rdeccfg=str(_ROOT / "config" / "m3_repo_deconvolution_outline_inputs.yaml"),
        js="results/module3/m3_repo_deconvolution_paths_status.json",
        flag="results/module3/m3_repo_deconvolution_paths_status.flag",
        dec_stub_js="results/module3/m3_deconvolution_integration_stub.json",
        dec_stub_f="results/module3/m3_deconvolution_integration_stub.flag",
        rss_stub_js="results/module3/m3_repo_scrna_spatial_integration_stub.json",
        rss_stub_f="results/module3/m3_repo_scrna_spatial_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_deconvolution_integration_stub.json",
        out_f="results/module3/m3_repo_deconvolution_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_deconvolution_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_cellranger_output_paths_status:
    """Outline M3: results/module3 m3_cellranger_output path-status + integration_stub JSON/flag presence."""
    input:
        m3rcrcfg=str(_ROOT / "config" / "m3_repo_cellranger_output_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_cellranger_output_paths_status.json",
        flag="results/module3/m3_repo_cellranger_output_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_cellranger_output_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_cellranger_output_integration_stub:
    """Outline M3: Cell Ranger output repo manifest slice (echoes m3_cellranger + m3_repo_scrna_spatial stubs)."""
    input:
        m3rcrcfg=str(_ROOT / "config" / "m3_repo_cellranger_output_outline_inputs.yaml"),
        js="results/module3/m3_repo_cellranger_output_paths_status.json",
        flag="results/module3/m3_repo_cellranger_output_paths_status.flag",
        cr_stub_js="results/module3/m3_cellranger_output_integration_stub.json",
        cr_stub_f="results/module3/m3_cellranger_output_integration_stub.flag",
        rss_stub_js="results/module3/m3_repo_scrna_spatial_integration_stub.json",
        rss_stub_f="results/module3/m3_repo_scrna_spatial_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_cellranger_output_integration_stub.json",
        out_f="results/module3/m3_repo_cellranger_output_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_cellranger_output_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_dryad_sra_paths_status:
    """Outline M3: Dryad spatial GBM + SRA GSE57872 staging paths under data_root (presence only)."""
    input:
        m3dscfg=str(_ROOT / "config" / "m3_dryad_sra_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_dryad_sra_paths_status.json",
        flag="results/module3/m3_dryad_sra_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_dryad_sra_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_dryad_sra_integration_stub:
    """Outline M3: Dryad + SRA staging checklist (after scRNA/spatial integration stub)."""
    input:
        m3dscfg=str(_ROOT / "config" / "m3_dryad_sra_outline_inputs.yaml"),
        js="results/module3/m3_dryad_sra_paths_status.json",
        flag="results/module3/m3_dryad_sra_paths_status.flag",
        scrna_js="results/module3/scrna_spatial_integration_stub.json",
        scrna_f="results/module3/scrna_spatial_integration_stub.flag",
    output:
        out_js="results/module3/m3_dryad_sra_integration_stub.json",
        out_f="results/module3/m3_dryad_sra_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_dryad_sra_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_geo_pipelines_mirror_paths_status:
    """Outline M3: GEO series roots + pipelines git-clone dirs under data_root (presence only)."""
    input:
        m3gpmcfg=str(_ROOT / "config" / "m3_geo_pipelines_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_geo_pipelines_mirror_paths_status.json",
        flag="results/module3/m3_geo_pipelines_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_geo_pipelines_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_geo_pipelines_mirror_integration_stub:
    """Outline M3: GEO + pipelines mirror checklist (after scRNA/spatial integration stub)."""
    input:
        m3gpmcfg=str(_ROOT / "config" / "m3_geo_pipelines_mirror_outline_inputs.yaml"),
        js="results/module3/m3_geo_pipelines_mirror_paths_status.json",
        flag="results/module3/m3_geo_pipelines_mirror_paths_status.flag",
        scrna_js="results/module3/scrna_spatial_integration_stub.json",
        scrna_f="results/module3/scrna_spatial_integration_stub.flag",
    output:
        out_js="results/module3/m3_geo_pipelines_mirror_integration_stub.json",
        out_f="results/module3/m3_geo_pipelines_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_geo_pipelines_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_tcga_recount_lincs_mirror_paths_status:
    """Outline M3: TCGA-GBM case tree, recount3 G029 cache, LINCS clue subset root (presence only)."""
    input:
        m3tcrcfg=str(_ROOT / "config" / "m3_tcga_recount_lincs_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_tcga_recount_lincs_mirror_paths_status.json",
        flag="results/module3/m3_tcga_recount_lincs_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_tcga_recount_lincs_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_tcga_recount_lincs_mirror_integration_stub:
    """Outline M3: TCGA + recount3 + LINCS root checklist (after M1 reference/GDC integration stub)."""
    input:
        m3tcrcfg=str(_ROOT / "config" / "m3_tcga_recount_lincs_mirror_outline_inputs.yaml"),
        js="results/module3/m3_tcga_recount_lincs_mirror_paths_status.json",
        flag="results/module3/m3_tcga_recount_lincs_mirror_paths_status.flag",
        m1rg_stub_js="results/module3/m1_reference_gdc_integration_stub.json",
        m1rg_stub_f="results/module3/m1_reference_gdc_integration_stub.flag",
    output:
        out_js="results/module3/m3_tcga_recount_lincs_mirror_integration_stub.json",
        out_f="results/module3/m3_tcga_recount_lincs_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_tcga_recount_lincs_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_dryad_sra_paths_status:
    """Outline M3: results/module3 m3_dryad_sra path-status + integration_stub JSON/flag presence."""
    input:
        m3rdscfg=str(_ROOT / "config" / "m3_repo_dryad_sra_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_dryad_sra_paths_status.json",
        flag="results/module3/m3_repo_dryad_sra_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_dryad_sra_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_dryad_sra_integration_stub:
    """Outline M3: Dryad/SRA mirror repo manifest slice (echoes m3_dryad_sra + m3_repo_scrna_spatial stubs)."""
    input:
        m3rdscfg=str(_ROOT / "config" / "m3_repo_dryad_sra_outline_inputs.yaml"),
        js="results/module3/m3_repo_dryad_sra_paths_status.json",
        flag="results/module3/m3_repo_dryad_sra_paths_status.flag",
        ds_stub_js="results/module3/m3_dryad_sra_integration_stub.json",
        ds_stub_f="results/module3/m3_dryad_sra_integration_stub.flag",
        rss_stub_js="results/module3/m3_repo_scrna_spatial_integration_stub.json",
        rss_stub_f="results/module3/m3_repo_scrna_spatial_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_dryad_sra_integration_stub.json",
        out_f="results/module3/m3_repo_dryad_sra_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_dryad_sra_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_geo_pipelines_mirror_paths_status:
    """Outline M3: results/module3 m3_geo_pipelines_mirror path-status + integration_stub JSON/flag presence."""
    input:
        m3rgeocfg=str(_ROOT / "config" / "m3_repo_geo_pipelines_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_geo_pipelines_mirror_paths_status.json",
        flag="results/module3/m3_repo_geo_pipelines_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_geo_pipelines_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_geo_pipelines_mirror_integration_stub:
    """Outline M3: GEO/pipelines mirror repo manifest slice (echoes m3_geo + m3_repo_scrna_spatial stubs)."""
    input:
        m3rgeocfg=str(_ROOT / "config" / "m3_repo_geo_pipelines_mirror_outline_inputs.yaml"),
        js="results/module3/m3_repo_geo_pipelines_mirror_paths_status.json",
        flag="results/module3/m3_repo_geo_pipelines_mirror_paths_status.flag",
        gpm_stub_js="results/module3/m3_geo_pipelines_mirror_integration_stub.json",
        gpm_stub_f="results/module3/m3_geo_pipelines_mirror_integration_stub.flag",
        rss_stub_js="results/module3/m3_repo_scrna_spatial_integration_stub.json",
        rss_stub_f="results/module3/m3_repo_scrna_spatial_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_geo_pipelines_mirror_integration_stub.json",
        out_f="results/module3/m3_repo_geo_pipelines_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_geo_pipelines_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_tcga_recount_lincs_mirror_paths_status:
    """Outline M3: results/module3 m3_tcga_recount_lincs_mirror path-status + integration_stub JSON/flag presence."""
    input:
        m3rtclcfg=str(_ROOT / "config" / "m3_repo_tcga_recount_lincs_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_tcga_recount_lincs_mirror_paths_status.json",
        flag="results/module3/m3_repo_tcga_recount_lincs_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_tcga_recount_lincs_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_tcga_recount_lincs_mirror_integration_stub:
    """Outline M3: TCGA/recount3/LINCS mirror repo manifest slice (echoes m3_tcga mirror + M1 GDC stubs)."""
    input:
        m3rtclcfg=str(_ROOT / "config" / "m3_repo_tcga_recount_lincs_mirror_outline_inputs.yaml"),
        js="results/module3/m3_repo_tcga_recount_lincs_mirror_paths_status.json",
        flag="results/module3/m3_repo_tcga_recount_lincs_mirror_paths_status.flag",
        tcr_stub_js="results/module3/m3_tcga_recount_lincs_mirror_integration_stub.json",
        tcr_stub_f="results/module3/m3_tcga_recount_lincs_mirror_integration_stub.flag",
        m1rg_stub_js="results/module3/m1_reference_gdc_integration_stub.json",
        m1rg_stub_f="results/module3/m1_reference_gdc_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_tcga_recount_lincs_mirror_integration_stub.json",
        out_f="results/module3/m3_repo_tcga_recount_lincs_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_tcga_recount_lincs_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_bundled_references_paths_status:
    """Outline M3: repository references/ Verhaak GMT + driver YAML presence (clone root, not data_root)."""
    input:
        m3rbrcfg=str(_ROOT / "config" / "m3_repo_bundled_references_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_bundled_references_paths_status.json",
        flag="results/module3/m3_repo_bundled_references_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_bundled_references_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_bundled_references_integration_stub:
    """Outline M3: shipped references checklist (after MOVICS integration stub)."""
    input:
        m3rbrcfg=str(_ROOT / "config" / "m3_repo_bundled_references_outline_inputs.yaml"),
        js="results/module3/m3_repo_bundled_references_paths_status.json",
        flag="results/module3/m3_repo_bundled_references_paths_status.flag",
        movics_stub_js="results/module3/m2_movics_integration_stub.json",
        movics_stub_f="results/module3/m2_movics_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_bundled_references_integration_stub.json",
        out_f="results/module3/m3_repo_bundled_references_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_bundled_references_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_gdc_expression_matrix_paths_status:
    """Outline M3: in-repo GDC STAR TPM and counts parquets under results/module2 (presence only)."""
    input:
        m3rgmcfg=str(_ROOT / "config" / "m3_repo_gdc_expression_matrix_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_gdc_expression_matrix_paths_status.json",
        flag="results/module3/m3_repo_gdc_expression_matrix_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_gdc_expression_matrix_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_gdc_expression_matrix_integration_stub:
    """Outline M3: built GDC matrix checklist (after M1 reference/GDC integration stub)."""
    input:
        m3rgmcfg=str(_ROOT / "config" / "m3_repo_gdc_expression_matrix_outline_inputs.yaml"),
        js="results/module3/m3_repo_gdc_expression_matrix_paths_status.json",
        flag="results/module3/m3_repo_gdc_expression_matrix_paths_status.flag",
        m1rg_stub_js="results/module3/m1_reference_gdc_integration_stub.json",
        m1rg_stub_f="results/module3/m1_reference_gdc_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_gdc_expression_matrix_integration_stub.json",
        out_f="results/module3/m3_repo_gdc_expression_matrix_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_gdc_expression_matrix_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_toil_bulk_expression_paths_status:
    """Outline M3: in-repo TOIL TPM parquet and sample TSV under results/module3 (presence only)."""
    input:
        m3rtbcfg=str(_ROOT / "config" / "m3_repo_toil_bulk_expression_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_toil_bulk_expression_paths_status.json",
        flag="results/module3/m3_repo_toil_bulk_expression_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_toil_bulk_expression_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_toil_bulk_expression_integration_stub:
    """Outline M3: TOIL bulk hub checklist (after M2.1 TOIL Xena hub integration stub)."""
    input:
        m3rtbcfg=str(_ROOT / "config" / "m3_repo_toil_bulk_expression_outline_inputs.yaml"),
        js="results/module3/m3_repo_toil_bulk_expression_paths_status.json",
        flag="results/module3/m3_repo_toil_bulk_expression_paths_status.flag",
        m2tx_stub_js="results/module3/m2_1_toil_xena_hub_integration_stub.json",
        m2tx_stub_f="results/module3/m2_1_toil_xena_hub_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_toil_bulk_expression_integration_stub.json",
        out_f="results/module3/m3_repo_toil_bulk_expression_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_toil_bulk_expression_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_recount3_bulk_dea_paths_status:
    """Outline M3: in-repo recount3 PyDESeq2 and edgeR DEA artifacts under results/module3 (presence only)."""
    input:
        m3rr3cfg=str(_ROOT / "config" / "m3_repo_recount3_bulk_dea_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_recount3_bulk_dea_paths_status.json",
        flag="results/module3/m3_repo_recount3_bulk_dea_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_recount3_bulk_dea_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_recount3_bulk_dea_integration_stub:
    """Outline M3: recount3 bulk DEA checklist (after M2.1 recount3 mirror integration stub)."""
    input:
        m3rr3cfg=str(_ROOT / "config" / "m3_repo_recount3_bulk_dea_outline_inputs.yaml"),
        js="results/module3/m3_repo_recount3_bulk_dea_paths_status.json",
        flag="results/module3/m3_repo_recount3_bulk_dea_paths_status.flag",
        m2r3_stub_js="results/module3/m2_1_recount3_mirror_integration_stub.json",
        m2r3_stub_f="results/module3/m2_1_recount3_mirror_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_recount3_bulk_dea_integration_stub.json",
        out_f="results/module3/m3_repo_recount3_bulk_dea_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_recount3_bulk_dea_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_bulk_welch_ols_dea_paths_status:
    """Outline M3: in-repo TOIL Welch and OLS bulk DEA TSVs and provenance under results/module3."""
    input:
        m3bwocfg=str(_ROOT / "config" / "m3_repo_bulk_welch_ols_dea_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_bulk_welch_ols_dea_paths_status.json",
        flag="results/module3/m3_repo_bulk_welch_ols_dea_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_bulk_welch_ols_dea_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_bulk_welch_ols_dea_integration_stub:
    """Outline M3: Welch and OLS bulk DEA checklist (after TOIL TPM hub slice integration stub)."""
    input:
        m3bwocfg=str(_ROOT / "config" / "m3_repo_bulk_welch_ols_dea_outline_inputs.yaml"),
        js="results/module3/m3_repo_bulk_welch_ols_dea_paths_status.json",
        flag="results/module3/m3_repo_bulk_welch_ols_dea_paths_status.flag",
        m3rtb_stub_js="results/module3/m3_repo_toil_bulk_expression_integration_stub.json",
        m3rtb_stub_f="results/module3/m3_repo_toil_bulk_expression_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.json",
        out_f="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_bulk_welch_ols_dea_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_toil_vs_recount3_correlation_paths_status:
    """Outline M3: in-repo TOIL vs recount3 cross-assay correlation JSON and recount3 concordance paths."""
    input:
        m3tvrcfg=str(_ROOT / "config" / "m3_repo_toil_vs_recount3_correlation_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_toil_vs_recount3_correlation_paths_status.json",
        flag="results/module3/m3_repo_toil_vs_recount3_correlation_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_toil_vs_recount3_correlation_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_toil_vs_recount3_correlation_integration_stub:
    """Outline M3: cross-assay correlation checklist (after Welch/OLS and recount3 bulk-DEA repo stubs)."""
    input:
        m3tvrcfg=str(_ROOT / "config" / "m3_repo_toil_vs_recount3_correlation_outline_inputs.yaml"),
        js="results/module3/m3_repo_toil_vs_recount3_correlation_paths_status.json",
        flag="results/module3/m3_repo_toil_vs_recount3_correlation_paths_status.flag",
        m3bwo_stub_js="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.json",
        m3bwo_stub_f="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.flag",
        m3rr3_stub_js="results/module3/m3_repo_recount3_bulk_dea_integration_stub.json",
        m3rr3_stub_f="results/module3/m3_repo_recount3_bulk_dea_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_toil_vs_recount3_correlation_integration_stub.json",
        out_f="results/module3/m3_repo_toil_vs_recount3_correlation_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_toil_vs_recount3_correlation_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_stratified_bulk_dea_paths_status:
    """Outline M3: stratified Welch/OLS provenance and integration flags under results/module3."""
    input:
        m3rsbcfg=str(_ROOT / "config" / "m3_repo_stratified_bulk_dea_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_stratified_bulk_dea_paths_status.json",
        flag="results/module3/m3_repo_stratified_bulk_dea_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_stratified_bulk_dea_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_stratified_bulk_dea_integration_stub:
    """Outline M3: stratified bulk DEA checklist (after TOIL TPM hub and global Welch/OLS repo stubs)."""
    input:
        m3rsbcfg=str(_ROOT / "config" / "m3_repo_stratified_bulk_dea_outline_inputs.yaml"),
        js="results/module3/m3_repo_stratified_bulk_dea_paths_status.json",
        flag="results/module3/m3_repo_stratified_bulk_dea_paths_status.flag",
        m3rtb_stub_js="results/module3/m3_repo_toil_bulk_expression_integration_stub.json",
        m3rtb_stub_f="results/module3/m3_repo_toil_bulk_expression_integration_stub.flag",
        m3bwo_stub_js="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.json",
        m3bwo_stub_f="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_stratified_bulk_dea_integration_stub.json",
        out_f="results/module3/m3_repo_stratified_bulk_dea_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_stratified_bulk_dea_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_cohort_verhaak_subtype_paths_status:
    """Outline M3: cohort design, Verhaak subtype scores/summary, mean TPM-by-subtype under results/module3."""
    input:
        m3rcvcfg=str(_ROOT / "config" / "m3_repo_cohort_verhaak_subtype_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_cohort_verhaak_subtype_paths_status.json",
        flag="results/module3/m3_repo_cohort_verhaak_subtype_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_cohort_verhaak_subtype_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_cohort_verhaak_subtype_integration_stub:
    """Outline M3: cohort + Verhaak checklist (after TOIL TPM hub and bundled references stubs)."""
    input:
        m3rcvcfg=str(_ROOT / "config" / "m3_repo_cohort_verhaak_subtype_outline_inputs.yaml"),
        js="results/module3/m3_repo_cohort_verhaak_subtype_paths_status.json",
        flag="results/module3/m3_repo_cohort_verhaak_subtype_paths_status.flag",
        m3rtb_stub_js="results/module3/m3_repo_toil_bulk_expression_integration_stub.json",
        m3rtb_stub_f="results/module3/m3_repo_toil_bulk_expression_integration_stub.flag",
        m3rbr_stub_js="results/module3/m3_repo_bundled_references_integration_stub.json",
        m3rbr_stub_f="results/module3/m3_repo_bundled_references_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_cohort_verhaak_subtype_integration_stub.json",
        out_f="results/module3/m3_repo_cohort_verhaak_subtype_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_cohort_verhaak_subtype_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_bulk_join_provenance_paths_status:
    """Outline M3: DepMap, MAF, MutSig join and STRING export provenance JSONs under results/module3."""
    input:
        m3rbjcfg=str(_ROOT / "config" / "m3_repo_bulk_join_provenance_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_bulk_join_provenance_paths_status.json",
        flag="results/module3/m3_repo_bulk_join_provenance_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_bulk_join_provenance_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_bulk_join_provenance_integration_stub:
    """Outline M3: join provenance checklist (after global DEA, DepMap mirror, MAF/MutSig mirror stubs)."""
    input:
        m3rbjcfg=str(_ROOT / "config" / "m3_repo_bulk_join_provenance_outline_inputs.yaml"),
        js="results/module3/m3_repo_bulk_join_provenance_paths_status.json",
        flag="results/module3/m3_repo_bulk_join_provenance_paths_status.flag",
        m3bwo_stub_js="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.json",
        m3bwo_stub_f="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.flag",
        m2dm_stub_js="results/module3/m2_2_depmap_mirror_integration_stub.json",
        m2dm_stub_f="results/module3/m2_2_depmap_mirror_integration_stub.flag",
        m2mm_stub_js="results/module3/m2_2_maf_mutsig_mirror_integration_stub.json",
        m2mm_stub_f="results/module3/m2_2_maf_mutsig_mirror_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_bulk_join_provenance_integration_stub.json",
        out_f="results/module3/m3_repo_bulk_join_provenance_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_bulk_join_provenance_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_gdc_star_tcga_gbm_dea_paths_status:
    """Outline M3: GDC STAR PyDESeq2 and edgeR provenance JSONs (within-TCGA-GBM) under results/module3."""
    input:
        m3rgscfg=str(_ROOT / "config" / "m3_repo_gdc_star_tcga_gbm_dea_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_gdc_star_tcga_gbm_dea_paths_status.json",
        flag="results/module3/m3_repo_gdc_star_tcga_gbm_dea_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_gdc_star_tcga_gbm_dea_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_gdc_star_tcga_gbm_dea_integration_stub:
    """Outline M3: GDC STAR DEA provenance checklist (after in-repo GDC matrix and STAR pairing stubs)."""
    input:
        m3rgscfg=str(_ROOT / "config" / "m3_repo_gdc_star_tcga_gbm_dea_outline_inputs.yaml"),
        js="results/module3/m3_repo_gdc_star_tcga_gbm_dea_paths_status.json",
        flag="results/module3/m3_repo_gdc_star_tcga_gbm_dea_paths_status.flag",
        m3rgm_stub_js="results/module3/m3_repo_gdc_expression_matrix_integration_stub.json",
        m3rgm_stub_f="results/module3/m3_repo_gdc_expression_matrix_integration_stub.flag",
        m2sp_stub_js="results/module3/m2_1_star_pairing_integration_stub.json",
        m2sp_stub_f="results/module3/m2_1_star_pairing_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_gdc_star_tcga_gbm_dea_integration_stub.json",
        out_f="results/module3/m3_repo_gdc_star_tcga_gbm_dea_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_gdc_star_tcga_gbm_dea_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_module5_lincs_connectivity_paths_status:
    """Outline M3: Module 5 LINCS Entrez signatures, cmap scan, connectivity readiness, and related JSON under results/module5."""
    input:
        m3rmlcfg=str(_ROOT / "config" / "m3_repo_module5_lincs_connectivity_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module5_lincs_connectivity_paths_status.json",
        flag="results/module3/m3_repo_module5_lincs_connectivity_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module5_lincs_connectivity_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module5_lincs_connectivity_integration_stub:
    """Outline M3: M5 LINCS signature pack checklist (echoes bulk DEA repo stubs and m5_l1000_data stub)."""
    input:
        m3rmlcfg=str(_ROOT / "config" / "m3_repo_module5_lincs_connectivity_outline_inputs.yaml"),
        js="results/module3/m3_repo_module5_lincs_connectivity_paths_status.json",
        flag="results/module3/m3_repo_module5_lincs_connectivity_paths_status.flag",
        m3bwo_stub_js="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.json",
        m3bwo_stub_f="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.flag",
        m3rr3_stub_js="results/module3/m3_repo_recount3_bulk_dea_integration_stub.json",
        m3rr3_stub_f="results/module3/m3_repo_recount3_bulk_dea_integration_stub.flag",
        m3rsb_stub_js="results/module3/m3_repo_stratified_bulk_dea_integration_stub.json",
        m3rsb_stub_f="results/module3/m3_repo_stratified_bulk_dea_integration_stub.flag",
        m5l1k_stub_js="results/module5/m5_l1000_data_integration_stub.json",
        m5l1k_stub_f="results/module5/m5_l1000_data_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module5_lincs_connectivity_integration_stub.json",
        out_f="results/module3/m3_repo_module5_lincs_connectivity_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module5_lincs_connectivity_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_module5_l1000_data_paths_status:
    """Outline M3: results/module5 m5_l1000_data path-status + integration stub JSON/flag presence."""
    input:
        m3r5l1cfg=str(_ROOT / "config" / "m3_repo_module5_l1000_data_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module5_l1000_data_paths_status.json",
        flag="results/module3/m3_repo_module5_l1000_data_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module5_l1000_data_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module5_l1000_data_integration_stub:
    """Outline M3: M5 L1000 data outline checklist (echoes m5_l1000_data_integration_stub, M5 LINCS M3 slice)."""
    input:
        m3r5l1cfg=str(_ROOT / "config" / "m3_repo_module5_l1000_data_outline_inputs.yaml"),
        js="results/module3/m3_repo_module5_l1000_data_paths_status.json",
        flag="results/module3/m3_repo_module5_l1000_data_paths_status.flag",
        m5l1_ps_js="results/module5/m5_l1000_data_paths_status.json",
        m5l1_ps_f="results/module5/m5_l1000_data_paths_status.flag",
        m5l1_stub_js="results/module5/m5_l1000_data_integration_stub.json",
        m5l1_stub_f="results/module5/m5_l1000_data_integration_stub.flag",
        m3rml_stub_js="results/module3/m3_repo_module5_lincs_connectivity_integration_stub.json",
        m3rml_stub_f="results/module3/m3_repo_module5_lincs_connectivity_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module5_l1000_data_integration_stub.json",
        out_f="results/module3/m3_repo_module5_l1000_data_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module5_l1000_data_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_module5_modality_paths_status:
    """Outline M3: results/module5 m5_modality path-status + integration stub JSON/flag presence."""
    input:
        m3r5modcfg=str(_ROOT / "config" / "m3_repo_module5_modality_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module5_modality_paths_status.json",
        flag="results/module3/m3_repo_module5_modality_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module5_modality_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module5_modality_integration_stub:
    """Outline M3: M5 modality outline checklist (echoes m5_modality_integration_stub, M5 LINCS M3 slice)."""
    input:
        m3r5modcfg=str(_ROOT / "config" / "m3_repo_module5_modality_outline_inputs.yaml"),
        js="results/module3/m3_repo_module5_modality_paths_status.json",
        flag="results/module3/m3_repo_module5_modality_paths_status.flag",
        m5mod_ps_js="results/module5/m5_modality_paths_status.json",
        m5mod_ps_f="results/module5/m5_modality_paths_status.flag",
        m5mod_stub_js="results/module5/m5_modality_integration_stub.json",
        m5mod_stub_f="results/module5/m5_modality_integration_stub.flag",
        m3rml_stub_js="results/module3/m3_repo_module5_lincs_connectivity_integration_stub.json",
        m3rml_stub_f="results/module3/m3_repo_module5_lincs_connectivity_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module5_modality_integration_stub.json",
        out_f="results/module3/m3_repo_module5_modality_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module5_modality_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_module5_srges_output_paths_status:
    """Outline M3: results/module5 m5_srges_output path-status + integration stub JSON/flag presence."""
    input:
        m3r5socfg=str(_ROOT / "config" / "m3_repo_module5_srges_output_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module5_srges_output_paths_status.json",
        flag="results/module3/m3_repo_module5_srges_output_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module5_srges_output_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module5_srges_output_integration_stub:
    """Outline M3: M5 sRGES output outline checklist (echoes m5_srges_output_integration_stub, M5 LINCS M3 slice)."""
    input:
        m3r5socfg=str(_ROOT / "config" / "m3_repo_module5_srges_output_outline_inputs.yaml"),
        js="results/module3/m3_repo_module5_srges_output_paths_status.json",
        flag="results/module3/m3_repo_module5_srges_output_paths_status.flag",
        m5so_ps_js="results/module5/m5_srges_output_paths_status.json",
        m5so_ps_f="results/module5/m5_srges_output_paths_status.flag",
        m5so_stub_js="results/module5/m5_srges_output_integration_stub.json",
        m5so_stub_f="results/module5/m5_srges_output_integration_stub.flag",
        m3rml_stub_js="results/module3/m3_repo_module5_lincs_connectivity_integration_stub.json",
        m3rml_stub_f="results/module3/m3_repo_module5_lincs_connectivity_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module5_srges_output_integration_stub.json",
        out_f="results/module3/m3_repo_module5_srges_output_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module5_srges_output_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_module5_lincs_connectivity_mirror_paths_status:
    """Outline M3: results/module5 m5_lincs_connectivity_mirror path-status + integration stub JSON/flag presence."""
    input:
        m3r5lcmcfg=str(_ROOT / "config" / "m3_repo_module5_lincs_connectivity_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module5_lincs_connectivity_mirror_paths_status.json",
        flag="results/module3/m3_repo_module5_lincs_connectivity_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "m3_repo_module5_lincs_connectivity_mirror_paths_status.py"),
            ],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module5_lincs_connectivity_mirror_integration_stub:
    """Outline M3: M5 LINCS connectivity mirror checklist (echoes m5 mirror stub, L1000-data + LINCS M3 slices)."""
    input:
        m3r5lcmcfg=str(_ROOT / "config" / "m3_repo_module5_lincs_connectivity_mirror_outline_inputs.yaml"),
        js="results/module3/m3_repo_module5_lincs_connectivity_mirror_paths_status.json",
        flag="results/module3/m3_repo_module5_lincs_connectivity_mirror_paths_status.flag",
        m5lcm_ps_js="results/module5/m5_lincs_connectivity_mirror_paths_status.json",
        m5lcm_ps_f="results/module5/m5_lincs_connectivity_mirror_paths_status.flag",
        m5lcm_stub_js="results/module5/m5_lincs_connectivity_mirror_integration_stub.json",
        m5lcm_stub_f="results/module5/m5_lincs_connectivity_mirror_integration_stub.flag",
        m3r5l1_stub_js="results/module3/m3_repo_module5_l1000_data_integration_stub.json",
        m3r5l1_stub_f="results/module3/m3_repo_module5_l1000_data_integration_stub.flag",
        m3rml_stub_js="results/module3/m3_repo_module5_lincs_connectivity_integration_stub.json",
        m3rml_stub_f="results/module3/m3_repo_module5_lincs_connectivity_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module5_lincs_connectivity_mirror_integration_stub.json",
        out_f="results/module3/m3_repo_module5_lincs_connectivity_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "m3_repo_module5_lincs_connectivity_mirror_integration_stub.py"),
            ],
            cwd=str(_ROOT),
        )


rule m3_repo_module4_hub_gsea_paths_status:
    """Outline M3: Module 4 WGCNA hub, GSEA prerank, stratified STRING provenance under results/module4."""
    input:
        m3r4hcfg=str(_ROOT / "config" / "m3_repo_module4_hub_gsea_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module4_hub_gsea_paths_status.json",
        flag="results/module3/m3_repo_module4_hub_gsea_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module4_hub_gsea_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module4_hub_gsea_integration_stub:
    """Outline M3: M4 hub + GSEA bundle checklist (echoes TOIL TPM, bulk DEA repo stubs, m4_gsea_mirror stub)."""
    input:
        m3r4hcfg=str(_ROOT / "config" / "m3_repo_module4_hub_gsea_outline_inputs.yaml"),
        js="results/module3/m3_repo_module4_hub_gsea_paths_status.json",
        flag="results/module3/m3_repo_module4_hub_gsea_paths_status.flag",
        m3rtb_stub_js="results/module3/m3_repo_toil_bulk_expression_integration_stub.json",
        m3rtb_stub_f="results/module3/m3_repo_toil_bulk_expression_integration_stub.flag",
        m3bwo_stub_js="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.json",
        m3bwo_stub_f="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.flag",
        m3rr3_stub_js="results/module3/m3_repo_recount3_bulk_dea_integration_stub.json",
        m3rr3_stub_f="results/module3/m3_repo_recount3_bulk_dea_integration_stub.flag",
        m3rsb_stub_js="results/module3/m3_repo_stratified_bulk_dea_integration_stub.json",
        m3rsb_stub_f="results/module3/m3_repo_stratified_bulk_dea_integration_stub.flag",
        m4gsea_stub_js="results/module4/m4_gsea_mirror_integration_stub.json",
        m4gsea_stub_f="results/module4/m4_gsea_mirror_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module4_hub_gsea_integration_stub.json",
        out_f="results/module3/m3_repo_module4_hub_gsea_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module4_hub_gsea_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_module4_network_paths_status:
    """Outline M3: results/module4 m4_network path-status + integration stub JSON/flag presence."""
    input:
        m3r4ncfg=str(_ROOT / "config" / "m3_repo_module4_network_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module4_network_paths_status.json",
        flag="results/module3/m3_repo_module4_network_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module4_network_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module4_network_integration_stub:
    """Outline M3: M4 network outline checklist (echoes m4_network, hub/GSEA M3 slice, GSEA mirror stub)."""
    input:
        m3r4ncfg=str(_ROOT / "config" / "m3_repo_module4_network_outline_inputs.yaml"),
        js="results/module3/m3_repo_module4_network_paths_status.json",
        flag="results/module3/m3_repo_module4_network_paths_status.flag",
        m4net_js="results/module4/m4_network_paths_status.json",
        m4net_f="results/module4/m4_network_paths_status.flag",
        m4net_stub_js="results/module4/m4_network_integration_stub.json",
        m4net_stub_f="results/module4/m4_network_integration_stub.flag",
        m3r4h_stub_js="results/module3/m3_repo_module4_hub_gsea_integration_stub.json",
        m3r4h_stub_f="results/module3/m3_repo_module4_hub_gsea_integration_stub.flag",
        m4gsm_stub_js="results/module4/m4_gsea_mirror_integration_stub.json",
        m4gsm_stub_f="results/module4/m4_gsea_mirror_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module4_network_integration_stub.json",
        out_f="results/module3/m3_repo_module4_network_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module4_network_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_module4_string_cache_paths_status:
    """Outline M3: results/module4 m4_string_cache path-status + integration stub JSON/flag presence."""
    input:
        m3r4sccfg=str(_ROOT / "config" / "m3_repo_module4_string_cache_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module4_string_cache_paths_status.json",
        flag="results/module3/m3_repo_module4_string_cache_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module4_string_cache_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module4_string_cache_integration_stub:
    """Outline M3: M4 STRING cache outline checklist (echoes m4_string_cache, m4_network, M3 network slice)."""
    input:
        m3r4sccfg=str(_ROOT / "config" / "m3_repo_module4_string_cache_outline_inputs.yaml"),
        js="results/module3/m3_repo_module4_string_cache_paths_status.json",
        flag="results/module3/m3_repo_module4_string_cache_paths_status.flag",
        m4str_js="results/module4/m4_string_cache_paths_status.json",
        m4str_f="results/module4/m4_string_cache_paths_status.flag",
        m4str_stub_js="results/module4/m4_string_cache_integration_stub.json",
        m4str_stub_f="results/module4/m4_string_cache_integration_stub.flag",
        m4net_stub_js="results/module4/m4_network_integration_stub.json",
        m4net_stub_f="results/module4/m4_network_integration_stub.flag",
        m3r4n_stub_js="results/module3/m3_repo_module4_network_integration_stub.json",
        m3r4n_stub_f="results/module3/m3_repo_module4_network_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module4_string_cache_integration_stub.json",
        out_f="results/module3/m3_repo_module4_string_cache_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module4_string_cache_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_module4_pathway_database_mirror_paths_status:
    """Outline M3: results/module4 m4_pathway_database_mirror path-status + integration stub JSON/flag presence."""
    input:
        m3r4pwcfg=str(_ROOT / "config" / "m3_repo_module4_pathway_database_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module4_pathway_database_mirror_paths_status.json",
        flag="results/module3/m3_repo_module4_pathway_database_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "m3_repo_module4_pathway_database_mirror_paths_status.py"),
            ],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module4_pathway_database_mirror_integration_stub:
    """Outline M3: M4 KEGG/Reactome mirror outline checklist (echoes m4 pathway stub, GSEA mirror, hub/GSEA M3)."""
    input:
        m3r4pwcfg=str(_ROOT / "config" / "m3_repo_module4_pathway_database_mirror_outline_inputs.yaml"),
        js="results/module3/m3_repo_module4_pathway_database_mirror_paths_status.json",
        flag="results/module3/m3_repo_module4_pathway_database_mirror_paths_status.flag",
        m4pw_js="results/module4/m4_pathway_database_mirror_paths_status.json",
        m4pw_f="results/module4/m4_pathway_database_mirror_paths_status.flag",
        m4pw_stub_js="results/module4/m4_pathway_database_mirror_integration_stub.json",
        m4pw_stub_f="results/module4/m4_pathway_database_mirror_integration_stub.flag",
        m4gsm_stub_js="results/module4/m4_gsea_mirror_integration_stub.json",
        m4gsm_stub_f="results/module4/m4_gsea_mirror_integration_stub.flag",
        m3r4h_stub_js="results/module3/m3_repo_module4_hub_gsea_integration_stub.json",
        m3r4h_stub_f="results/module3/m3_repo_module4_hub_gsea_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module4_pathway_database_mirror_integration_stub.json",
        out_f="results/module3/m3_repo_module4_pathway_database_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "m3_repo_module4_pathway_database_mirror_integration_stub.py"),
            ],
            cwd=str(_ROOT),
        )


rule m3_repo_module4_gsea_mirror_paths_status:
    """Outline M3: results/module4 m4_gsea_mirror path-status + integration stub JSON/flag presence."""
    input:
        m3r4gmcfg=str(_ROOT / "config" / "m3_repo_module4_gsea_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module4_gsea_mirror_paths_status.json",
        flag="results/module3/m3_repo_module4_gsea_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module4_gsea_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module4_gsea_mirror_integration_stub:
    """Outline M3: M4 GSEA mirror outline checklist (echoes m4 GSEA stub, hub/GSEA M3, pathway M3 slice)."""
    input:
        m3r4gmcfg=str(_ROOT / "config" / "m3_repo_module4_gsea_mirror_outline_inputs.yaml"),
        js="results/module3/m3_repo_module4_gsea_mirror_paths_status.json",
        flag="results/module3/m3_repo_module4_gsea_mirror_paths_status.flag",
        m4gsea_js="results/module4/m4_gsea_mirror_paths_status.json",
        m4gsea_f="results/module4/m4_gsea_mirror_paths_status.flag",
        m4gsea_stub_js="results/module4/m4_gsea_mirror_integration_stub.json",
        m4gsea_stub_f="results/module4/m4_gsea_mirror_integration_stub.flag",
        m3r4h_stub_js="results/module3/m3_repo_module4_hub_gsea_integration_stub.json",
        m3r4h_stub_f="results/module3/m3_repo_module4_hub_gsea_integration_stub.flag",
        m3r4pw_stub_js="results/module3/m3_repo_module4_pathway_database_mirror_integration_stub.json",
        m3r4pw_stub_f="results/module3/m3_repo_module4_pathway_database_mirror_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module4_gsea_mirror_integration_stub.json",
        out_f="results/module3/m3_repo_module4_gsea_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module4_gsea_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_module7_gts_stub_paths_status:
    """Outline M3: Module 7 GTS candidate stub TSVs, provenance, stratified tables, validation stub under results/module7."""
    input:
        m3r7gcfg=str(_ROOT / "config" / "m3_repo_module7_gts_stub_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module7_gts_stub_paths_status.json",
        flag="results/module3/m3_repo_module7_gts_stub_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module7_gts_stub_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module7_gts_stub_integration_stub:
    """Outline M3: M7 GTS stub inventory checklist (echoes bulk DEA repo stubs + gts_validation_integration_stub)."""
    input:
        m3r7gcfg=str(_ROOT / "config" / "m3_repo_module7_gts_stub_outline_inputs.yaml"),
        js="results/module3/m3_repo_module7_gts_stub_paths_status.json",
        flag="results/module3/m3_repo_module7_gts_stub_paths_status.flag",
        m3bwo_stub_js="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.json",
        m3bwo_stub_f="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.flag",
        m3rr3_stub_js="results/module3/m3_repo_recount3_bulk_dea_integration_stub.json",
        m3rr3_stub_f="results/module3/m3_repo_recount3_bulk_dea_integration_stub.flag",
        m3rsb_stub_js="results/module3/m3_repo_stratified_bulk_dea_integration_stub.json",
        m3rsb_stub_f="results/module3/m3_repo_stratified_bulk_dea_integration_stub.flag",
        gts_val_js="results/module7/gts_validation_integration_stub.json",
        gts_val_f="results/module7/gts_validation_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module7_gts_stub_integration_stub.json",
        out_f="results/module3/m3_repo_module7_gts_stub_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module7_gts_stub_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_module7_validation_paths_status:
    """Outline M3: results/module7 m7_validation path-status + integration stub JSON/flag presence."""
    input:
        m3r7valcfg=str(_ROOT / "config" / "m3_repo_module7_validation_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module7_validation_paths_status.json",
        flag="results/module3/m3_repo_module7_validation_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module7_validation_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module7_validation_integration_stub:
    """Outline M3: M7 validation outline checklist (echoes m7_validation_integration_stub, M7 GTS stub M3 slice)."""
    input:
        m3r7valcfg=str(_ROOT / "config" / "m3_repo_module7_validation_outline_inputs.yaml"),
        js="results/module3/m3_repo_module7_validation_paths_status.json",
        flag="results/module3/m3_repo_module7_validation_paths_status.flag",
        m7val_ps_js="results/module7/m7_validation_paths_status.json",
        m7val_ps_f="results/module7/m7_validation_paths_status.flag",
        m7val_stub_js="results/module7/m7_validation_integration_stub.json",
        m7val_stub_f="results/module7/m7_validation_integration_stub.flag",
        m3r7g_stub_js="results/module3/m3_repo_module7_gts_stub_integration_stub.json",
        m3r7g_stub_f="results/module3/m3_repo_module7_gts_stub_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module7_validation_integration_stub.json",
        out_f="results/module3/m3_repo_module7_validation_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module7_validation_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_module7_gts_external_score_mirror_paths_status:
    """Outline M3: results/module7 m7_gts_external_score_mirror path-status + integration stub JSON/flag presence."""
    input:
        m3r7gescfg=str(_ROOT / "config" / "m3_repo_module7_gts_external_score_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module7_gts_external_score_mirror_paths_status.json",
        flag="results/module3/m3_repo_module7_gts_external_score_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "m3_repo_module7_gts_external_score_mirror_paths_status.py"),
            ],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module7_gts_external_score_mirror_integration_stub:
    """Outline M3: M7 external score mirror checklist (echoes m7 stub, M7 GTS + validation M3 slices)."""
    input:
        m3r7gescfg=str(_ROOT / "config" / "m3_repo_module7_gts_external_score_mirror_outline_inputs.yaml"),
        js="results/module3/m3_repo_module7_gts_external_score_mirror_paths_status.json",
        flag="results/module3/m3_repo_module7_gts_external_score_mirror_paths_status.flag",
        m7ges_ps_js="results/module7/m7_gts_external_score_mirror_paths_status.json",
        m7ges_ps_f="results/module7/m7_gts_external_score_mirror_paths_status.flag",
        m7ges_stub_js="results/module7/m7_gts_external_score_mirror_integration_stub.json",
        m7ges_stub_f="results/module7/m7_gts_external_score_mirror_integration_stub.flag",
        m3r7g_stub_js="results/module3/m3_repo_module7_gts_stub_integration_stub.json",
        m3r7g_stub_f="results/module3/m3_repo_module7_gts_stub_integration_stub.flag",
        m3r7v_stub_js="results/module3/m3_repo_module7_validation_integration_stub.json",
        m3r7v_stub_f="results/module3/m3_repo_module7_validation_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module7_gts_external_score_mirror_integration_stub.json",
        out_f="results/module3/m3_repo_module7_gts_external_score_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "m3_repo_module7_gts_external_score_mirror_integration_stub.py"),
            ],
            cwd=str(_ROOT),
        )


rule m3_repo_module6_structure_bridge_paths_status:
    """Outline M3: Module 6 structure druggability bridge TSVs and structure_admet stub under results/module6."""
    input:
        m3r6scfg=str(_ROOT / "config" / "m3_repo_module6_structure_bridge_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module6_structure_bridge_paths_status.json",
        flag="results/module3/m3_repo_module6_structure_bridge_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module6_structure_bridge_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module6_structure_bridge_integration_stub:
    """Outline M3: M6 bridge inventory checklist (echoes bulk DEA repo stubs + structure_admet_integration_stub)."""
    input:
        m3r6scfg=str(_ROOT / "config" / "m3_repo_module6_structure_bridge_outline_inputs.yaml"),
        js="results/module3/m3_repo_module6_structure_bridge_paths_status.json",
        flag="results/module3/m3_repo_module6_structure_bridge_paths_status.flag",
        m3bwo_stub_js="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.json",
        m3bwo_stub_f="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.flag",
        m3rr3_stub_js="results/module3/m3_repo_recount3_bulk_dea_integration_stub.json",
        m3rr3_stub_f="results/module3/m3_repo_recount3_bulk_dea_integration_stub.flag",
        m3rsb_stub_js="results/module3/m3_repo_stratified_bulk_dea_integration_stub.json",
        m3rsb_stub_f="results/module3/m3_repo_stratified_bulk_dea_integration_stub.flag",
        m6_admet_js="results/module6/structure_admet_integration_stub.json",
        m6_admet_f="results/module6/structure_admet_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module6_structure_bridge_integration_stub.json",
        out_f="results/module3/m3_repo_module6_structure_bridge_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module6_structure_bridge_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_module6_structure_tooling_paths_status:
    """Outline M3: results/module6 structure tooling paths + structure_admet stub JSON/flag presence."""
    input:
        m3r6toolcfg=str(_ROOT / "config" / "m3_repo_module6_structure_tooling_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module6_structure_tooling_paths_status.json",
        flag="results/module3/m3_repo_module6_structure_tooling_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module6_structure_tooling_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module6_structure_tooling_integration_stub:
    """Outline M3: M6 tooling + ADMET outline checklist (echoes structure_admet, M6 bridge M3 slice)."""
    input:
        m3r6toolcfg=str(_ROOT / "config" / "m3_repo_module6_structure_tooling_outline_inputs.yaml"),
        js="results/module3/m3_repo_module6_structure_tooling_paths_status.json",
        flag="results/module3/m3_repo_module6_structure_tooling_paths_status.flag",
        m6tool_js="results/module6/module6_structure_tooling_paths_status.json",
        m6tool_f="results/module6/module6_structure_tooling_paths_status.flag",
        m6admet_js="results/module6/structure_admet_integration_stub.json",
        m6admet_f="results/module6/structure_admet_integration_stub.flag",
        m3r6s_stub_js="results/module3/m3_repo_module6_structure_bridge_integration_stub.json",
        m3r6s_stub_f="results/module3/m3_repo_module6_structure_bridge_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module6_structure_tooling_integration_stub.json",
        out_f="results/module3/m3_repo_module6_structure_tooling_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module6_structure_tooling_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_tooling_vendor_paths_status:
    """Outline M3: results/tooling vendor_tooling path status + integration stub JSON/flag presence."""
    input:
        m3rtvcfg=str(_ROOT / "config" / "m3_repo_tooling_vendor_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_tooling_vendor_paths_status.json",
        flag="results/module3/m3_repo_tooling_vendor_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_tooling_vendor_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_tooling_vendor_integration_stub:
    """Outline M3: tooling vendor artifact checklist (echoes vendor_tooling, scRNA, Cell Ranger outline stubs)."""
    input:
        m3rtvcfg=str(_ROOT / "config" / "m3_repo_tooling_vendor_outline_inputs.yaml"),
        js="results/module3/m3_repo_tooling_vendor_paths_status.json",
        flag="results/module3/m3_repo_tooling_vendor_paths_status.flag",
        vtool_js="results/tooling/vendor_tooling_paths_status.json",
        vtool_f="results/tooling/vendor_tooling_paths_status.flag",
        vtool_stub_js="results/tooling/vendor_tooling_integration_stub.json",
        vtool_stub_f="results/tooling/vendor_tooling_integration_stub.flag",
        scrna_js="results/module3/scrna_spatial_integration_stub.json",
        scrna_f="results/module3/scrna_spatial_integration_stub.flag",
        m3cr_stub_js="results/module3/m3_cellranger_output_integration_stub.json",
        m3cr_stub_f="results/module3/m3_cellranger_output_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_tooling_vendor_integration_stub.json",
        out_f="results/module3/m3_repo_tooling_vendor_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_tooling_vendor_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_module6_docking_output_paths_status:
    """Outline M3: results/module6 m6_docking_output path-status + integration stub JSON/flag presence."""
    input:
        m3r6dcfg=str(_ROOT / "config" / "m3_repo_module6_docking_output_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module6_docking_output_paths_status.json",
        flag="results/module3/m3_repo_module6_docking_output_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module6_docking_output_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module6_docking_output_integration_stub:
    """Outline M3: M6 docking output outline checklist (echoes m6_docking_output, M6 bridge M3 slice, ADMET stub)."""
    input:
        m3r6dcfg=str(_ROOT / "config" / "m3_repo_module6_docking_output_outline_inputs.yaml"),
        js="results/module3/m3_repo_module6_docking_output_paths_status.json",
        flag="results/module3/m3_repo_module6_docking_output_paths_status.flag",
        dock_js="results/module6/m6_docking_output_paths_status.json",
        dock_f="results/module6/m6_docking_output_paths_status.flag",
        dock_stub_js="results/module6/m6_docking_output_integration_stub.json",
        dock_stub_f="results/module6/m6_docking_output_integration_stub.flag",
        m3r6s_stub_js="results/module3/m3_repo_module6_structure_bridge_integration_stub.json",
        m3r6s_stub_f="results/module3/m3_repo_module6_structure_bridge_integration_stub.flag",
        m6_admet_js="results/module6/structure_admet_integration_stub.json",
        m6_admet_f="results/module6/structure_admet_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module6_docking_output_integration_stub.json",
        out_f="results/module3/m3_repo_module6_docking_output_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module6_docking_output_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_module6_toxicity_paths_status:
    """Outline M3: results/module6 m6_toxicity path-status + integration stub JSON/flag presence."""
    input:
        m3r6tcfg=str(_ROOT / "config" / "m3_repo_module6_toxicity_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module6_toxicity_paths_status.json",
        flag="results/module3/m3_repo_module6_toxicity_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module6_toxicity_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module6_toxicity_integration_stub:
    """Outline M3: M6 toxicity outline checklist (echoes m6_toxicity, docking-output M3 slice, ADMET stub)."""
    input:
        m3r6tcfg=str(_ROOT / "config" / "m3_repo_module6_toxicity_outline_inputs.yaml"),
        js="results/module3/m3_repo_module6_toxicity_paths_status.json",
        flag="results/module3/m3_repo_module6_toxicity_paths_status.flag",
        tox_js="results/module6/m6_toxicity_paths_status.json",
        tox_f="results/module6/m6_toxicity_paths_status.flag",
        tox_stub_js="results/module6/m6_toxicity_integration_stub.json",
        tox_stub_f="results/module6/m6_toxicity_integration_stub.flag",
        m3r6d_stub_js="results/module3/m3_repo_module6_docking_output_integration_stub.json",
        m3r6d_stub_f="results/module3/m3_repo_module6_docking_output_integration_stub.flag",
        m6_admet_js="results/module6/structure_admet_integration_stub.json",
        m6_admet_f="results/module6/structure_admet_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module6_toxicity_integration_stub.json",
        out_f="results/module3/m3_repo_module6_toxicity_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_module6_toxicity_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_module6_compound_library_mirror_paths_status:
    """Outline M3: results/module6 m6_compound_library_mirror path-status + integration stub JSON/flag presence."""
    input:
        m3r6clmcfg=str(_ROOT / "config" / "m3_repo_module6_compound_library_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_module6_compound_library_mirror_paths_status.json",
        flag="results/module3/m3_repo_module6_compound_library_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "m3_repo_module6_compound_library_mirror_paths_status.py"),
            ],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_module6_compound_library_mirror_integration_stub:
    """Outline M3: M6 compound library mirror outline checklist (echoes m6 stub, docking M3 slice, ADMET)."""
    input:
        m3r6clmcfg=str(_ROOT / "config" / "m3_repo_module6_compound_library_mirror_outline_inputs.yaml"),
        js="results/module3/m3_repo_module6_compound_library_mirror_paths_status.json",
        flag="results/module3/m3_repo_module6_compound_library_mirror_paths_status.flag",
        clm_js="results/module6/m6_compound_library_mirror_paths_status.json",
        clm_f="results/module6/m6_compound_library_mirror_paths_status.flag",
        clm_stub_js="results/module6/m6_compound_library_mirror_integration_stub.json",
        clm_stub_f="results/module6/m6_compound_library_mirror_integration_stub.flag",
        m3r6d_stub_js="results/module3/m3_repo_module6_docking_output_integration_stub.json",
        m3r6d_stub_f="results/module3/m3_repo_module6_docking_output_integration_stub.flag",
        m6_admet_js="results/module6/structure_admet_integration_stub.json",
        m6_admet_f="results/module6/structure_admet_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_module6_compound_library_mirror_integration_stub.json",
        out_f="results/module3/m3_repo_module6_compound_library_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "m3_repo_module6_compound_library_mirror_integration_stub.py"),
            ],
            cwd=str(_ROOT),
        )


rule m3_export_manifest:
    """Module 3: JSON inventory of bulk DEA, recount3, join provenance, and M3 path-status artifacts."""
    input:
        writer=str(_ROOT / "scripts" / "write_module3_export_manifest.py"),
        manifest_opt=str(_ROOT / "scripts" / "manifest_optional.py"),
        m3cfg=str(_ROOT / "config" / "module3_inputs.yaml"),
        cohort="results/module3/cohort_design_summary.json",
        cross="results/module3/toil_welch_vs_recount3_bulk_effect_correlation.json",
        r3conc="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_vs_edger_concordance.json",
        r3_deseq2_tsv="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_results.tsv",
        r3_edger_qlf_tsv="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_qlf_results.tsv",
        r3_deseq2_prv="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_provenance.json",
        r3_edger_prv="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_provenance.json",
        r3_counts_pq="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/recount3_de_counts_matrix.parquet",
        r3_sm_meta="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/recount3_de_sample_meta.tsv",
        deastr="results/module3/dea_string_export_provenance.json",
        strat="results/module3/stratified_dea_integration.flag",
        scrna_stub_js="results/module3/scrna_spatial_integration_stub.json",
        scrna_stub_f="results/module3/scrna_spatial_integration_stub.flag",
        m3pub_stat_js="results/module3/module3_public_inputs_status.json",
        m3pub_stat_fl="results/module3/module3_public_inputs_status.flag",
        m3scwf_js="results/module3/module3_sc_workflow_paths_status.json",
        m3scwf_fl="results/module3/module3_sc_workflow_paths_status.flag",
        m3rss_js="results/module3/m3_repo_scrna_spatial_paths_status.json",
        m3rss_f="results/module3/m3_repo_scrna_spatial_paths_status.flag",
        m3rss_stub_js="results/module3/m3_repo_scrna_spatial_integration_stub.json",
        m3rss_stub_f="results/module3/m3_repo_scrna_spatial_integration_stub.flag",
        m3rpi_js="results/module3/m3_repo_public_inputs_paths_status.json",
        m3rpi_f="results/module3/m3_repo_public_inputs_paths_status.flag",
        m3rpi_stub_js="results/module3/m3_repo_public_inputs_integration_stub.json",
        m3rpi_stub_f="results/module3/m3_repo_public_inputs_integration_stub.flag",
        m3rsw_js="results/module3/m3_repo_sc_workflow_paths_status.json",
        m3rsw_f="results/module3/m3_repo_sc_workflow_paths_status.flag",
        m3rsw_stub_js="results/module3/m3_repo_sc_workflow_integration_stub.json",
        m3rsw_stub_f="results/module3/m3_repo_sc_workflow_integration_stub.flag",
        m3dec_js="results/module3/m3_deconvolution_paths_status.json",
        m3dec_f="results/module3/m3_deconvolution_paths_status.flag",
        m3dec_stub_js="results/module3/m3_deconvolution_integration_stub.json",
        m3dec_stub_f="results/module3/m3_deconvolution_integration_stub.flag",
        m3cr_js="results/module3/m3_cellranger_output_paths_status.json",
        m3cr_f="results/module3/m3_cellranger_output_paths_status.flag",
        m3cr_stub_js="results/module3/m3_cellranger_output_integration_stub.json",
        m3cr_stub_f="results/module3/m3_cellranger_output_integration_stub.flag",
        m3rdec_js="results/module3/m3_repo_deconvolution_paths_status.json",
        m3rdec_f="results/module3/m3_repo_deconvolution_paths_status.flag",
        m3rdec_stub_js="results/module3/m3_repo_deconvolution_integration_stub.json",
        m3rdec_stub_f="results/module3/m3_repo_deconvolution_integration_stub.flag",
        m3rcr_js="results/module3/m3_repo_cellranger_output_paths_status.json",
        m3rcr_f="results/module3/m3_repo_cellranger_output_paths_status.flag",
        m3rcr_stub_js="results/module3/m3_repo_cellranger_output_integration_stub.json",
        m3rcr_stub_f="results/module3/m3_repo_cellranger_output_integration_stub.flag",
        m3ds_js="results/module3/m3_dryad_sra_paths_status.json",
        m3ds_f="results/module3/m3_dryad_sra_paths_status.flag",
        m3ds_stub_js="results/module3/m3_dryad_sra_integration_stub.json",
        m3ds_stub_f="results/module3/m3_dryad_sra_integration_stub.flag",
        m3gpm_js="results/module3/m3_geo_pipelines_mirror_paths_status.json",
        m3gpm_f="results/module3/m3_geo_pipelines_mirror_paths_status.flag",
        m3gpm_stub_js="results/module3/m3_geo_pipelines_mirror_integration_stub.json",
        m3gpm_stub_f="results/module3/m3_geo_pipelines_mirror_integration_stub.flag",
        m3tcr_js="results/module3/m3_tcga_recount_lincs_mirror_paths_status.json",
        m3tcr_f="results/module3/m3_tcga_recount_lincs_mirror_paths_status.flag",
        m3tcr_stub_js="results/module3/m3_tcga_recount_lincs_mirror_integration_stub.json",
        m3tcr_stub_f="results/module3/m3_tcga_recount_lincs_mirror_integration_stub.flag",
        m3rds_js="results/module3/m3_repo_dryad_sra_paths_status.json",
        m3rds_f="results/module3/m3_repo_dryad_sra_paths_status.flag",
        m3rds_stub_js="results/module3/m3_repo_dryad_sra_integration_stub.json",
        m3rds_stub_f="results/module3/m3_repo_dryad_sra_integration_stub.flag",
        m3rgeo_js="results/module3/m3_repo_geo_pipelines_mirror_paths_status.json",
        m3rgeo_f="results/module3/m3_repo_geo_pipelines_mirror_paths_status.flag",
        m3rgeo_stub_js="results/module3/m3_repo_geo_pipelines_mirror_integration_stub.json",
        m3rgeo_stub_f="results/module3/m3_repo_geo_pipelines_mirror_integration_stub.flag",
        m3rtcl_js="results/module3/m3_repo_tcga_recount_lincs_mirror_paths_status.json",
        m3rtcl_f="results/module3/m3_repo_tcga_recount_lincs_mirror_paths_status.flag",
        m3rtcl_stub_js="results/module3/m3_repo_tcga_recount_lincs_mirror_integration_stub.json",
        m3rtcl_stub_f="results/module3/m3_repo_tcga_recount_lincs_mirror_integration_stub.flag",
        m3rbr_gmt_c2="references/verhaak_msigdb_c2_cgp_2024.1.Hs.gmt",
        m3rbr_gmt_c4="references/verhaak_msigdb_c4_cgn_2024.1.Hs.gmt",
        m3rbr_centroid_tpl="references/verhaak_centroids_user_template.tsv",
        m3rbr_drivers_yaml="references/gbm_known_drivers_outline.yaml",
        m3rbr_js="results/module3/m3_repo_bundled_references_paths_status.json",
        m3rbr_f="results/module3/m3_repo_bundled_references_paths_status.flag",
        m3rbr_stub_js="results/module3/m3_repo_bundled_references_integration_stub.json",
        m3rbr_stub_f="results/module3/m3_repo_bundled_references_integration_stub.flag",
        m3rgm_js="results/module3/m3_repo_gdc_expression_matrix_paths_status.json",
        m3rgm_f="results/module3/m3_repo_gdc_expression_matrix_paths_status.flag",
        m3rgm_stub_js="results/module3/m3_repo_gdc_expression_matrix_integration_stub.json",
        m3rgm_stub_f="results/module3/m3_repo_gdc_expression_matrix_integration_stub.flag",
        m2gdc_tpm="results/module2/tcga_gbm_star_tpm_matrix.parquet",
        m2gdc_counts="results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet",
        m2gdc_meta="results/module2/tcga_gbm_sample_meta.tsv",
        m2gdc_qc="results/module2/gdc_counts_matrix_qc.json",
        m2gdc_cohort_sum="results/module2/gdc_counts_cohort_summary.json",
        m3toil_tpm="results/module3/toil_gbm_vs_brain_tpm.parquet",
        m3toil_samples="results/module3/toil_gbm_vs_brain_samples.tsv",
        m3rtb_js="results/module3/m3_repo_toil_bulk_expression_paths_status.json",
        m3rtb_f="results/module3/m3_repo_toil_bulk_expression_paths_status.flag",
        m3rtb_stub_js="results/module3/m3_repo_toil_bulk_expression_integration_stub.json",
        m3rtb_stub_f="results/module3/m3_repo_toil_bulk_expression_integration_stub.flag",
        m3rr3_js="results/module3/m3_repo_recount3_bulk_dea_paths_status.json",
        m3rr3_f="results/module3/m3_repo_recount3_bulk_dea_paths_status.flag",
        m3rr3_stub_js="results/module3/m3_repo_recount3_bulk_dea_integration_stub.json",
        m3rr3_stub_f="results/module3/m3_repo_recount3_bulk_dea_integration_stub.flag",
        m3bwo_welch_tsv="results/module3/dea_gbm_vs_gtex_brain.tsv",
        m3bwo_ols_tsv="results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv",
        m3bwo_welch_prv="results/module3/dea_gbm_vs_gtex_brain_provenance.json",
        m3bwo_ols_prv="results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate_provenance.json",
        m3bwo_js="results/module3/m3_repo_bulk_welch_ols_dea_paths_status.json",
        m3bwo_f="results/module3/m3_repo_bulk_welch_ols_dea_paths_status.flag",
        m3bwo_stub_js="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.json",
        m3bwo_stub_f="results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.flag",
        m3tvr_js="results/module3/m3_repo_toil_vs_recount3_correlation_paths_status.json",
        m3tvr_f="results/module3/m3_repo_toil_vs_recount3_correlation_paths_status.flag",
        m3tvr_stub_js="results/module3/m3_repo_toil_vs_recount3_correlation_integration_stub.json",
        m3tvr_stub_f="results/module3/m3_repo_toil_vs_recount3_correlation_integration_stub.flag",
        m3rsb_welch_sum="results/module3/stratified_dea/summary.tsv",
        m3rsb_ols_sum="results/module3/stratified_ols_dea/summary.tsv",
        m3rsb_welch_prv="results/module3/stratified_dea/stratified_dea_provenance.json",
        m3rsb_ols_prv="results/module3/stratified_ols_dea/stratified_ols_dea_provenance.json",
        m3rsb_int_prv="results/module3/stratified_dea_integration_provenance.json",
        m3rsb_odrv_fl="results/module3/stratified_integrated_outline_drivers.flag",
        m3rsb_js="results/module3/m3_repo_stratified_bulk_dea_paths_status.json",
        m3rsb_f="results/module3/m3_repo_stratified_bulk_dea_paths_status.flag",
        m3rsb_stub_js="results/module3/m3_repo_stratified_bulk_dea_integration_stub.json",
        m3rsb_stub_f="results/module3/m3_repo_stratified_bulk_dea_integration_stub.flag",
        m3rcv_scores_tsv="results/module3/tcga_gbm_verhaak_subtype_scores.tsv",
        m3rcv_mean_tpm_tsv="results/module3/mean_log_tpm_by_verhaak_subtype.tsv",
        m3rcv_subtype_summary="results/module3/tcga_gbm_verhaak_subtype_summary.json",
        m3rcv_mean_tpm_prov="results/module3/mean_log_tpm_by_verhaak_subtype_provenance.json",
        m3rcv_js="results/module3/m3_repo_cohort_verhaak_subtype_paths_status.json",
        m3rcv_f="results/module3/m3_repo_cohort_verhaak_subtype_paths_status.flag",
        m3rcv_stub_js="results/module3/m3_repo_cohort_verhaak_subtype_integration_stub.json",
        m3rcv_stub_f="results/module3/m3_repo_cohort_verhaak_subtype_integration_stub.flag",
        m3bj_dm_cr_prv="results/module3/depmap_crispr_join_provenance.json",
        m3bj_dm_so_prv="results/module3/depmap_somatic_join_provenance.json",
        m3bj_tcga_maf_ly_prv="results/module3/tcga_maf_layer_provenance.json",
        m3bj_tcga_maf_j_prv="results/module3/tcga_maf_join_provenance.json",
        m3bj_mutsig_prv="results/module3/mutsig_join_provenance.json",
        m3rbj_js="results/module3/m3_repo_bulk_join_provenance_paths_status.json",
        m3rbj_f="results/module3/m3_repo_bulk_join_provenance_paths_status.flag",
        m3rbj_stub_js="results/module3/m3_repo_bulk_join_provenance_integration_stub.json",
        m3rbj_stub_f="results/module3/m3_repo_bulk_join_provenance_integration_stub.flag",
        m3rgs_d2_pr_tsv="results/module3/deseq2_tcga_gbm/primary_vs_recurrent/deseq2_results.tsv",
        m3rgs_d2_psn_tsv="results/module3/deseq2_tcga_gbm/primary_vs_solid_tissue_normal/deseq2_results.tsv",
        m3rgs_ed_pr_tsv="results/module3/edger_tcga_gbm/primary_vs_recurrent/edger_qlf_results.tsv",
        m3rgs_ed_psn_tsv="results/module3/edger_tcga_gbm/primary_vs_solid_tissue_normal/edger_qlf_results.tsv",
        m3rgs_d2_pr_prv="results/module3/deseq2_tcga_gbm/primary_vs_recurrent/deseq2_provenance.json",
        m3rgs_d2_psn_prv="results/module3/deseq2_tcga_gbm/primary_vs_solid_tissue_normal/deseq2_provenance.json",
        m3rgs_ed_pr_prv="results/module3/edger_tcga_gbm/primary_vs_recurrent/edger_provenance.json",
        m3rgs_ed_psn_prv="results/module3/edger_tcga_gbm/primary_vs_solid_tissue_normal/edger_provenance.json",
        m3rgs_js="results/module3/m3_repo_gdc_star_tcga_gbm_dea_paths_status.json",
        m3rgs_f="results/module3/m3_repo_gdc_star_tcga_gbm_dea_paths_status.flag",
        m3rgs_stub_js="results/module3/m3_repo_gdc_star_tcga_gbm_dea_integration_stub.json",
        m3rgs_stub_f="results/module3/m3_repo_gdc_star_tcga_gbm_dea_integration_stub.flag",
        m5lc_sig_w="results/module5/lincs_disease_signature_welch_entrez.tsv",
        m5lc_sig_o="results/module5/lincs_disease_signature_ols_entrez.tsv",
        m5lc_sig_r3py="results/module5/lincs_disease_signature_recount3_pydeseq2_entrez.tsv",
        m5lc_sig_r3ed="results/module5/lincs_disease_signature_recount3_edger_entrez.tsv",
        m5lc_sig_prov="results/module5/lincs_disease_signature_provenance.json",
        m5lc_sig_fl="results/module5/lincs_disease_signature.flag",
        m5lc_strat_fl="results/module5/lincs_stratified_signature.flag",
        m5lc_sw_cl="results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Classical_entrez.tsv",
        m5lc_sw_me="results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Mesenchymal_entrez.tsv",
        m5lc_sw_ne="results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Neural_entrez.tsv",
        m5lc_sw_pr="results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Proneural_entrez.tsv",
        m5lc_so_cl="results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Classical_entrez.tsv",
        m5lc_so_me="results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Mesenchymal_entrez.tsv",
        m5lc_so_ne="results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Neural_entrez.tsv",
        m5lc_so_pr="results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Proneural_entrez.tsv",
        m5lc_cmap="results/module5/cmap_tooling_scan.json",
        m5lc_conn="results/module5/lincs_connectivity_readiness.json",
        m5lc_pack="results/module5/lincs_signature_pack.json",
        m5lc_srges="results/module5/srges_integration_stub.json",
        m3rml_js="results/module3/m3_repo_module5_lincs_connectivity_paths_status.json",
        m3rml_f="results/module3/m3_repo_module5_lincs_connectivity_paths_status.flag",
        m3rml_stub_js="results/module3/m3_repo_module5_lincs_connectivity_integration_stub.json",
        m3rml_stub_f="results/module3/m3_repo_module5_lincs_connectivity_integration_stub.flag",
        m5l1_ps_js="results/module5/m5_l1000_data_paths_status.json",
        m5l1_ps_fl="results/module5/m5_l1000_data_paths_status.flag",
        m5l1_st_js="results/module5/m5_l1000_data_integration_stub.json",
        m5l1_st_fl="results/module5/m5_l1000_data_integration_stub.flag",
        m3r5l1_js="results/module3/m3_repo_module5_l1000_data_paths_status.json",
        m3r5l1_f="results/module3/m3_repo_module5_l1000_data_paths_status.flag",
        m3r5l1_stub_js="results/module3/m3_repo_module5_l1000_data_integration_stub.json",
        m3r5l1_stub_f="results/module3/m3_repo_module5_l1000_data_integration_stub.flag",
        m5mo_ps_js="results/module5/m5_modality_paths_status.json",
        m5mo_ps_fl="results/module5/m5_modality_paths_status.flag",
        m5mo_st_js="results/module5/m5_modality_integration_stub.json",
        m5mo_st_fl="results/module5/m5_modality_integration_stub.flag",
        m3r5mo_js="results/module3/m3_repo_module5_modality_paths_status.json",
        m3r5mo_f="results/module3/m3_repo_module5_modality_paths_status.flag",
        m3r5mo_stub_js="results/module3/m3_repo_module5_modality_integration_stub.json",
        m3r5mo_stub_f="results/module3/m3_repo_module5_modality_integration_stub.flag",
        m5so_ps_js="results/module5/m5_srges_output_paths_status.json",
        m5so_ps_fl="results/module5/m5_srges_output_paths_status.flag",
        m5so_st_js="results/module5/m5_srges_output_integration_stub.json",
        m5so_st_fl="results/module5/m5_srges_output_integration_stub.flag",
        m3r5so_js="results/module3/m3_repo_module5_srges_output_paths_status.json",
        m3r5so_f="results/module3/m3_repo_module5_srges_output_paths_status.flag",
        m3r5so_stub_js="results/module3/m3_repo_module5_srges_output_integration_stub.json",
        m3r5so_stub_f="results/module3/m3_repo_module5_srges_output_integration_stub.flag",
        m5lcm_ps_js="results/module5/m5_lincs_connectivity_mirror_paths_status.json",
        m5lcm_ps_fl="results/module5/m5_lincs_connectivity_mirror_paths_status.flag",
        m5lcm_st_js="results/module5/m5_lincs_connectivity_mirror_integration_stub.json",
        m5lcm_st_fl="results/module5/m5_lincs_connectivity_mirror_integration_stub.flag",
        m3r5lcm_js="results/module3/m3_repo_module5_lincs_connectivity_mirror_paths_status.json",
        m3r5lcm_f="results/module3/m3_repo_module5_lincs_connectivity_mirror_paths_status.flag",
        m3r5lcm_stub_js="results/module3/m3_repo_module5_lincs_connectivity_mirror_integration_stub.json",
        m3r5lcm_stub_f="results/module3/m3_repo_module5_lincs_connectivity_mirror_integration_stub.flag",
        m4hg_we_pq="results/module4/wgcna_hub_expr_subset.parquet",
        m4hg_we_lt="results/module4/wgcna_hub_expr_subset_long.tsv",
        m4hg_we_prv="results/module4/wgcna_hub_expr_subset_provenance.json",
        m4hg_r3_pq="results/module4/wgcna_hub_expr_subset_recount3_only.parquet",
        m4hg_r3_lt="results/module4/wgcna_hub_expr_subset_recount3_only_long.tsv",
        m4hg_r3_prv="results/module4/wgcna_hub_expr_subset_recount3_only_provenance.json",
        m4hg_st_tsv="results/module4/wgcna_hub_sample_traits.tsv",
        m4hg_st_prv="results/module4/wgcna_hub_sample_traits_provenance.json",
        m4hg_st3_tsv="results/module4/wgcna_hub_sample_traits_recount3_only.tsv",
        m4hg_st3_prv="results/module4/wgcna_hub_sample_traits_recount3_only_provenance.json",
        m4hg_ovl="results/module4/wgcna_hub_gene_overlap_summary.json",
        m4hg_ssp="results/module4/stratified_string_export_provenance.json",
        m4hg_rn_w="results/module4/gsea/dea_welch_signed_neg_log10_p.rnk",
        m4hg_rn_o="results/module4/gsea/dea_ols_signed_neg_log10_p.rnk",
        m4hg_rn_rp="results/module4/gsea/recount3_pydeseq2_signed_neg_log10_p.rnk",
        m4hg_rn_re="results/module4/gsea/recount3_edger_signed_neg_log10_p.rnk",
        m4hg_rn_prv="results/module4/gsea_prerank_export_provenance.json",
        m4hg_rn_sfl="results/module4/gsea_stratified_prerank.flag",
        m4hg_rsw_cl="results/module4/gsea/stratified/welch_integrated/dea_welch_subtype_Classical_signed_neg_log10_p.rnk",
        m4hg_rsw_me="results/module4/gsea/stratified/welch_integrated/dea_welch_subtype_Mesenchymal_signed_neg_log10_p.rnk",
        m4hg_rsw_ne="results/module4/gsea/stratified/welch_integrated/dea_welch_subtype_Neural_signed_neg_log10_p.rnk",
        m4hg_rsw_pr="results/module4/gsea/stratified/welch_integrated/dea_welch_subtype_Proneural_signed_neg_log10_p.rnk",
        m4hg_rso_cl="results/module4/gsea/stratified/ols_integrated/dea_ols_subtype_Classical_signed_neg_log10_p.rnk",
        m4hg_rso_me="results/module4/gsea/stratified/ols_integrated/dea_ols_subtype_Mesenchymal_signed_neg_log10_p.rnk",
        m4hg_rso_ne="results/module4/gsea/stratified/ols_integrated/dea_ols_subtype_Neural_signed_neg_log10_p.rnk",
        m4hg_rso_pr="results/module4/gsea/stratified/ols_integrated/dea_ols_subtype_Proneural_signed_neg_log10_p.rnk",
        m3r4h_js="results/module3/m3_repo_module4_hub_gsea_paths_status.json",
        m3r4h_f="results/module3/m3_repo_module4_hub_gsea_paths_status.flag",
        m3r4h_stub_js="results/module3/m3_repo_module4_hub_gsea_integration_stub.json",
        m3r4h_stub_f="results/module3/m3_repo_module4_hub_gsea_integration_stub.flag",
        m4n_ps_js="results/module4/m4_network_paths_status.json",
        m4n_ps_fl="results/module4/m4_network_paths_status.flag",
        m4n_st_js="results/module4/m4_network_integration_stub.json",
        m4n_st_fl="results/module4/m4_network_integration_stub.flag",
        m3r4n_js="results/module3/m3_repo_module4_network_paths_status.json",
        m3r4n_f="results/module3/m3_repo_module4_network_paths_status.flag",
        m3r4n_stub_js="results/module3/m3_repo_module4_network_integration_stub.json",
        m3r4n_stub_f="results/module3/m3_repo_module4_network_integration_stub.flag",
        m4stc_ps_js="results/module4/m4_string_cache_paths_status.json",
        m4stc_ps_fl="results/module4/m4_string_cache_paths_status.flag",
        m4stc_st_js="results/module4/m4_string_cache_integration_stub.json",
        m4stc_st_fl="results/module4/m4_string_cache_integration_stub.flag",
        m3r4sc_js="results/module3/m3_repo_module4_string_cache_paths_status.json",
        m3r4sc_f="results/module3/m3_repo_module4_string_cache_paths_status.flag",
        m3r4sc_stub_js="results/module3/m3_repo_module4_string_cache_integration_stub.json",
        m3r4sc_stub_f="results/module3/m3_repo_module4_string_cache_integration_stub.flag",
        m4pwdm_ps_js="results/module4/m4_pathway_database_mirror_paths_status.json",
        m4pwdm_ps_fl="results/module4/m4_pathway_database_mirror_paths_status.flag",
        m4pwdm_st_js="results/module4/m4_pathway_database_mirror_integration_stub.json",
        m4pwdm_st_fl="results/module4/m4_pathway_database_mirror_integration_stub.flag",
        m3r4pw_js="results/module3/m3_repo_module4_pathway_database_mirror_paths_status.json",
        m3r4pw_f="results/module3/m3_repo_module4_pathway_database_mirror_paths_status.flag",
        m3r4pw_stub_js="results/module3/m3_repo_module4_pathway_database_mirror_integration_stub.json",
        m3r4pw_stub_f="results/module3/m3_repo_module4_pathway_database_mirror_integration_stub.flag",
        m4gsm_ps_js="results/module4/m4_gsea_mirror_paths_status.json",
        m4gsm_ps_fl="results/module4/m4_gsea_mirror_paths_status.flag",
        m4gsm_st_js="results/module4/m4_gsea_mirror_integration_stub.json",
        m4gsm_st_fl="results/module4/m4_gsea_mirror_integration_stub.flag",
        m3r4gm_js="results/module3/m3_repo_module4_gsea_mirror_paths_status.json",
        m3r4gm_f="results/module3/m3_repo_module4_gsea_mirror_paths_status.flag",
        m3r4gm_stub_js="results/module3/m3_repo_module4_gsea_mirror_integration_stub.json",
        m3r4gm_stub_f="results/module3/m3_repo_module4_gsea_mirror_integration_stub.flag",
        m7g_welch="results/module7/gts_candidate_table_welch_stub.tsv",
        m7g_t1_welch="results/module7/glioma_target_tier1_welch.tsv",
        m7g_ols="results/module7/gts_candidate_table_ols_stub.tsv",
        m7g_r3py="results/module7/gts_candidate_table_recount3_pydeseq2_stub.tsv",
        m7g_r3ed="results/module7/gts_candidate_table_recount3_edger_stub.tsv",
        m7g_prov="results/module7/gts_candidate_stub_provenance.json",
        m7g_fl="results/module7/gts_candidate_stub.flag",
        m7g_sfl="results/module7/gts_stratified_candidate_stub.flag",
        m7g_sw_cl="results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Classical_gts_stub.tsv",
        m7g_sw_me="results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Mesenchymal_gts_stub.tsv",
        m7g_sw_ne="results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Neural_gts_stub.tsv",
        m7g_sw_pr="results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Proneural_gts_stub.tsv",
        m7g_so_cl="results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Classical_gts_stub.tsv",
        m7g_so_me="results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Mesenchymal_gts_stub.tsv",
        m7g_so_ne="results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Neural_gts_stub.tsv",
        m7g_so_pr="results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Proneural_gts_stub.tsv",
        m7g_val_js="results/module7/gts_validation_integration_stub.json",
        m7g_val_fl="results/module7/gts_validation_integration_stub.flag",
        m3r7g_js="results/module3/m3_repo_module7_gts_stub_paths_status.json",
        m3r7g_f="results/module3/m3_repo_module7_gts_stub_paths_status.flag",
        m3r7g_stub_js="results/module3/m3_repo_module7_gts_stub_integration_stub.json",
        m3r7g_stub_f="results/module3/m3_repo_module7_gts_stub_integration_stub.flag",
        m7val_ps_js="results/module7/m7_validation_paths_status.json",
        m7val_ps_fl="results/module7/m7_validation_paths_status.flag",
        m7val_st_js="results/module7/m7_validation_integration_stub.json",
        m7val_st_fl="results/module7/m7_validation_integration_stub.flag",
        m3r7v_js="results/module3/m3_repo_module7_validation_paths_status.json",
        m3r7v_f="results/module3/m3_repo_module7_validation_paths_status.flag",
        m3r7v_stub_js="results/module3/m3_repo_module7_validation_integration_stub.json",
        m3r7v_stub_f="results/module3/m3_repo_module7_validation_integration_stub.flag",
        m7gext_ps_js="results/module7/m7_gts_external_score_mirror_paths_status.json",
        m7gext_ps_fl="results/module7/m7_gts_external_score_mirror_paths_status.flag",
        m7gext_st_js="results/module7/m7_gts_external_score_mirror_integration_stub.json",
        m7gext_st_fl="results/module7/m7_gts_external_score_mirror_integration_stub.flag",
        m3r7ges_js="results/module3/m3_repo_module7_gts_external_score_mirror_paths_status.json",
        m3r7ges_f="results/module3/m3_repo_module7_gts_external_score_mirror_paths_status.flag",
        m3r7ges_stub_js="results/module3/m3_repo_module7_gts_external_score_mirror_integration_stub.json",
        m3r7ges_stub_f="results/module3/m3_repo_module7_gts_external_score_mirror_integration_stub.flag",
        m6br_welch="results/module6/structure_druggability_bridge_welch.tsv",
        m6br_ols="results/module6/structure_druggability_bridge_ols.tsv",
        m6br_r3py="results/module6/structure_druggability_bridge_recount3_pydeseq2.tsv",
        m6br_r3ed="results/module6/structure_druggability_bridge_recount3_edger.tsv",
        m6br_prov="results/module6/structure_druggability_bridge_provenance.json",
        m6br_fl="results/module6/structure_druggability_bridge.flag",
        m6br_sfl="results/module6/structure_druggability_bridge_stratified.flag",
        m6br_sw_cl="results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Classical_structure_bridge.tsv",
        m6br_sw_me="results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Mesenchymal_structure_bridge.tsv",
        m6br_sw_ne="results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Neural_structure_bridge.tsv",
        m6br_sw_pr="results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Proneural_structure_bridge.tsv",
        m6br_so_cl="results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Classical_structure_bridge.tsv",
        m6br_so_me="results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Mesenchymal_structure_bridge.tsv",
        m6br_so_ne="results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Neural_structure_bridge.tsv",
        m6br_so_pr="results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Proneural_structure_bridge.tsv",
        m6br_admet_js="results/module6/structure_admet_integration_stub.json",
        m6br_admet_f="results/module6/structure_admet_integration_stub.flag",
        m3r6s_js="results/module3/m3_repo_module6_structure_bridge_paths_status.json",
        m3r6s_f="results/module3/m3_repo_module6_structure_bridge_paths_status.flag",
        m3r6s_stub_js="results/module3/m3_repo_module6_structure_bridge_integration_stub.json",
        m3r6s_stub_f="results/module3/m3_repo_module6_structure_bridge_integration_stub.flag",
        m6stool_ps_js="results/module6/module6_structure_tooling_paths_status.json",
        m6stool_ps_fl="results/module6/module6_structure_tooling_paths_status.flag",
        m3r6tool_js="results/module3/m3_repo_module6_structure_tooling_paths_status.json",
        m3r6tool_f="results/module3/m3_repo_module6_structure_tooling_paths_status.flag",
        m3r6tool_stub_js="results/module3/m3_repo_module6_structure_tooling_integration_stub.json",
        m3r6tool_stub_f="results/module3/m3_repo_module6_structure_tooling_integration_stub.flag",
        m3tv_paths_js="results/tooling/vendor_tooling_paths_status.json",
        m3tv_paths_fl="results/tooling/vendor_tooling_paths_status.flag",
        m3tv_stub_js="results/tooling/vendor_tooling_integration_stub.json",
        m3tv_stub_fl="results/tooling/vendor_tooling_integration_stub.flag",
        m3rtv_js="results/module3/m3_repo_tooling_vendor_paths_status.json",
        m3rtv_f="results/module3/m3_repo_tooling_vendor_paths_status.flag",
        m3rtv_stub_js="results/module3/m3_repo_tooling_vendor_integration_stub.json",
        m3rtv_stub_f="results/module3/m3_repo_tooling_vendor_integration_stub.flag",
        m6dock_ps_js="results/module6/m6_docking_output_paths_status.json",
        m6dock_ps_fl="results/module6/m6_docking_output_paths_status.flag",
        m6dock_st_js="results/module6/m6_docking_output_integration_stub.json",
        m6dock_st_fl="results/module6/m6_docking_output_integration_stub.flag",
        m3r6d_js="results/module3/m3_repo_module6_docking_output_paths_status.json",
        m3r6d_f="results/module3/m3_repo_module6_docking_output_paths_status.flag",
        m3r6d_stub_js="results/module3/m3_repo_module6_docking_output_integration_stub.json",
        m3r6d_stub_f="results/module3/m3_repo_module6_docking_output_integration_stub.flag",
        m6tox_ps_js="results/module6/m6_toxicity_paths_status.json",
        m6tox_ps_fl="results/module6/m6_toxicity_paths_status.flag",
        m6tox_st_js="results/module6/m6_toxicity_integration_stub.json",
        m6tox_st_fl="results/module6/m6_toxicity_integration_stub.flag",
        m3r6t_js="results/module3/m3_repo_module6_toxicity_paths_status.json",
        m3r6t_f="results/module3/m3_repo_module6_toxicity_paths_status.flag",
        m3r6t_stub_js="results/module3/m3_repo_module6_toxicity_integration_stub.json",
        m3r6t_stub_f="results/module3/m3_repo_module6_toxicity_integration_stub.flag",
        m6clm_ps_js="results/module6/m6_compound_library_mirror_paths_status.json",
        m6clm_ps_fl="results/module6/m6_compound_library_mirror_paths_status.flag",
        m6clm_st_js="results/module6/m6_compound_library_mirror_integration_stub.json",
        m6clm_st_fl="results/module6/m6_compound_library_mirror_integration_stub.flag",
        m3r6clm_js="results/module3/m3_repo_module6_compound_library_mirror_paths_status.json",
        m3r6clm_f="results/module3/m3_repo_module6_compound_library_mirror_paths_status.flag",
        m3r6clm_stub_js="results/module3/m3_repo_module6_compound_library_mirror_integration_stub.json",
        m3r6clm_stub_f="results/module3/m3_repo_module6_compound_library_mirror_integration_stub.flag",
        maf_stub_js="results/module3/maf_annotation_integration_stub.json",
        maf_stub_f="results/module3/maf_annotation_integration_stub.flag",
        m3r2maf_js="results/module3/m3_repo_m2_maf_annotation_paths_status.json",
        m3r2maf_f="results/module3/m3_repo_m2_maf_annotation_paths_status.flag",
        m3r2maf_stub_js="results/module3/m3_repo_m2_maf_annotation_integration_stub.json",
        m3r2maf_stub_f="results/module3/m3_repo_m2_maf_annotation_integration_stub.flag",
        m2va_js="results/module3/m2_2_variant_annotation_paths_status.json",
        m2va_f="results/module3/m2_2_variant_annotation_paths_status.flag",
        m2va_stub_js="results/module3/m2_2_variant_annotation_integration_stub.json",
        m2va_stub_f="results/module3/m2_2_variant_annotation_integration_stub.flag",
        m2dm_js="results/module3/m2_2_depmap_mirror_paths_status.json",
        m2dm_f="results/module3/m2_2_depmap_mirror_paths_status.flag",
        m2dm_stub_js="results/module3/m2_2_depmap_mirror_integration_stub.json",
        m2dm_stub_f="results/module3/m2_2_depmap_mirror_integration_stub.flag",
        m2mm_js="results/module3/m2_2_maf_mutsig_mirror_paths_status.json",
        m2mm_f="results/module3/m2_2_maf_mutsig_mirror_paths_status.flag",
        m2mm_stub_js="results/module3/m2_2_maf_mutsig_mirror_integration_stub.json",
        m2mm_stub_f="results/module3/m2_2_maf_mutsig_mirror_integration_stub.flag",
        m2odm_js="results/module3/m2_2_outline_driver_mirror_paths_status.json",
        m2odm_f="results/module3/m2_2_outline_driver_mirror_paths_status.flag",
        m2odm_stub_js="results/module3/m2_2_outline_driver_mirror_integration_stub.json",
        m2odm_stub_f="results/module3/m2_2_outline_driver_mirror_integration_stub.flag",
        cptac_js="results/module3/m2_cptac_methylation_paths_status.json",
        cptac_f="results/module3/m2_cptac_methylation_paths_status.flag",
        cptac_stub_js="results/module3/m2_cptac_methylation_integration_stub.json",
        cptac_stub_f="results/module3/m2_cptac_methylation_integration_stub.flag",
        m2sp_js="results/module3/m2_1_star_pairing_paths_status.json",
        m2sp_f="results/module3/m2_1_star_pairing_paths_status.flag",
        m2sp_stub_js="results/module3/m2_1_star_pairing_integration_stub.json",
        m2sp_stub_f="results/module3/m2_1_star_pairing_integration_stub.flag",
        m2r3_js="results/module3/m2_1_recount3_mirror_paths_status.json",
        m2r3_f="results/module3/m2_1_recount3_mirror_paths_status.flag",
        m2r3_stub_js="results/module3/m2_1_recount3_mirror_integration_stub.json",
        m2r3_stub_f="results/module3/m2_1_recount3_mirror_integration_stub.flag",
        m2tx_js="results/module3/m2_1_toil_xena_hub_paths_status.json",
        m2tx_f="results/module3/m2_1_toil_xena_hub_paths_status.flag",
        m2tx_stub_js="results/module3/m2_1_toil_xena_hub_integration_stub.json",
        m2tx_stub_f="results/module3/m2_1_toil_xena_hub_integration_stub.flag",
        movics_js="results/module3/m2_movics_paths_status.json",
        movics_f="results/module3/m2_movics_paths_status.flag",
        movics_stub_js="results/module3/m2_movics_integration_stub.json",
        movics_stub_f="results/module3/m2_movics_integration_stub.flag",
        m2itm_js="results/module3/m2_3_immune_tme_mirror_paths_status.json",
        m2itm_f="results/module3/m2_3_immune_tme_mirror_paths_status.flag",
        m2itm_stub_js="results/module3/m2_3_immune_tme_mirror_integration_stub.json",
        m2itm_stub_f="results/module3/m2_3_immune_tme_mirror_integration_stub.flag",
        m3r2cptac_js="results/module3/m3_repo_m2_cptac_methylation_paths_status.json",
        m3r2cptac_f="results/module3/m3_repo_m2_cptac_methylation_paths_status.flag",
        m3r2cptac_stub_js="results/module3/m3_repo_m2_cptac_methylation_integration_stub.json",
        m3r2cptac_stub_f="results/module3/m3_repo_m2_cptac_methylation_integration_stub.flag",
        m3r2rsp_js="results/module3/m3_repo_m2_1_star_pairing_paths_status.json",
        m3r2rsp_f="results/module3/m3_repo_m2_1_star_pairing_paths_status.flag",
        m3r2rsp_stub_js="results/module3/m3_repo_m2_1_star_pairing_integration_stub.json",
        m3r2rsp_stub_f="results/module3/m3_repo_m2_1_star_pairing_integration_stub.flag",
        m3r2rr3_js="results/module3/m3_repo_m2_1_recount3_mirror_paths_status.json",
        m3r2rr3_f="results/module3/m3_repo_m2_1_recount3_mirror_paths_status.flag",
        m3r2rr3_stub_js="results/module3/m3_repo_m2_1_recount3_mirror_integration_stub.json",
        m3r2rr3_stub_f="results/module3/m3_repo_m2_1_recount3_mirror_integration_stub.flag",
        m3r2rtx_js="results/module3/m3_repo_m2_1_toil_xena_hub_paths_status.json",
        m3r2rtx_f="results/module3/m3_repo_m2_1_toil_xena_hub_paths_status.flag",
        m3r2rtx_stub_js="results/module3/m3_repo_m2_1_toil_xena_hub_integration_stub.json",
        m3r2rtx_stub_f="results/module3/m3_repo_m2_1_toil_xena_hub_integration_stub.flag",
        m3r2rmv_js="results/module3/m3_repo_m2_movics_paths_status.json",
        m3r2rmv_f="results/module3/m3_repo_m2_movics_paths_status.flag",
        m3r2rmv_stub_js="results/module3/m3_repo_m2_movics_integration_stub.json",
        m3r2rmv_stub_f="results/module3/m3_repo_m2_movics_integration_stub.flag",
        m3r2ritm_js="results/module3/m3_repo_m2_3_immune_tme_mirror_paths_status.json",
        m3r2ritm_f="results/module3/m3_repo_m2_3_immune_tme_mirror_paths_status.flag",
        m3r2ritm_stub_js="results/module3/m3_repo_m2_3_immune_tme_mirror_integration_stub.json",
        m3r2ritm_stub_f="results/module3/m3_repo_m2_3_immune_tme_mirror_integration_stub.flag",
        m3r2rva_js="results/module3/m3_repo_m2_2_variant_annotation_paths_status.json",
        m3r2rva_f="results/module3/m3_repo_m2_2_variant_annotation_paths_status.flag",
        m3r2rva_stub_js="results/module3/m3_repo_m2_2_variant_annotation_integration_stub.json",
        m3r2rva_stub_f="results/module3/m3_repo_m2_2_variant_annotation_integration_stub.flag",
        m3r2rdm_js="results/module3/m3_repo_m2_2_depmap_mirror_paths_status.json",
        m3r2rdm_f="results/module3/m3_repo_m2_2_depmap_mirror_paths_status.flag",
        m3r2rdm_stub_js="results/module3/m3_repo_m2_2_depmap_mirror_integration_stub.json",
        m3r2rdm_stub_f="results/module3/m3_repo_m2_2_depmap_mirror_integration_stub.flag",
        m3r2rmm_js="results/module3/m3_repo_m2_2_maf_mutsig_mirror_paths_status.json",
        m3r2rmm_f="results/module3/m3_repo_m2_2_maf_mutsig_mirror_paths_status.flag",
        m3r2rmm_stub_js="results/module3/m3_repo_m2_2_maf_mutsig_mirror_integration_stub.json",
        m3r2rmm_stub_f="results/module3/m3_repo_m2_2_maf_mutsig_mirror_integration_stub.flag",
        m3r2rodm_js="results/module3/m3_repo_m2_2_outline_driver_mirror_paths_status.json",
        m3r2rodm_f="results/module3/m3_repo_m2_2_outline_driver_mirror_paths_status.flag",
        m3r2rodm_stub_js="results/module3/m3_repo_m2_2_outline_driver_mirror_integration_stub.json",
        m3r2rodm_stub_f="results/module3/m3_repo_m2_2_outline_driver_mirror_integration_stub.flag",
        m1_outline_js="results/module3/m1_outline_paths_status.json",
        m1_outline_f="results/module3/m1_outline_paths_status.flag",
        m1_outline_stub_js="results/module3/m1_outline_integration_stub.json",
        m1_outline_stub_f="results/module3/m1_outline_integration_stub.flag",
        m1_harm_js="results/module3/m1_harmony_batch_paths_status.json",
        m1_harm_f="results/module3/m1_harmony_batch_paths_status.flag",
        m1_harm_stub_js="results/module3/m1_harmony_batch_integration_stub.json",
        m1_harm_stub_f="results/module3/m1_harmony_batch_integration_stub.flag",
        m1rg_js="results/module3/m1_reference_gdc_paths_status.json",
        m1rg_f="results/module3/m1_reference_gdc_paths_status.flag",
        m1rg_stub_js="results/module3/m1_reference_gdc_integration_stub.json",
        m1rg_stub_f="results/module3/m1_reference_gdc_integration_stub.flag",
        m1bcm_js="results/module3/m1_batch_correction_mirror_paths_status.json",
        m1bcm_f="results/module3/m1_batch_correction_mirror_paths_status.flag",
        m1bcm_stub_js="results/module3/m1_batch_correction_mirror_integration_stub.json",
        m1bcm_stub_f="results/module3/m1_batch_correction_mirror_integration_stub.flag",
        m3r1mo_js="results/module3/m3_repo_m1_outline_paths_status.json",
        m3r1mo_f="results/module3/m3_repo_m1_outline_paths_status.flag",
        m3r1mo_stub_js="results/module3/m3_repo_m1_outline_integration_stub.json",
        m3r1mo_stub_f="results/module3/m3_repo_m1_outline_integration_stub.flag",
        m3r1mhb_js="results/module3/m3_repo_m1_harmony_batch_paths_status.json",
        m3r1mhb_f="results/module3/m3_repo_m1_harmony_batch_paths_status.flag",
        m3r1mhb_stub_js="results/module3/m3_repo_m1_harmony_batch_integration_stub.json",
        m3r1mhb_stub_f="results/module3/m3_repo_m1_harmony_batch_integration_stub.flag",
        m3r1mrg_js="results/module3/m3_repo_m1_reference_gdc_paths_status.json",
        m3r1mrg_f="results/module3/m3_repo_m1_reference_gdc_paths_status.flag",
        m3r1mrg_stub_js="results/module3/m3_repo_m1_reference_gdc_integration_stub.json",
        m3r1mrg_stub_f="results/module3/m3_repo_m1_reference_gdc_integration_stub.flag",
        m3r1mbcm_js="results/module3/m3_repo_m1_batch_correction_mirror_paths_status.json",
        m3r1mbcm_f="results/module3/m3_repo_m1_batch_correction_mirror_paths_status.flag",
        m3r1mbcm_stub_js="results/module3/m3_repo_m1_batch_correction_mirror_integration_stub.json",
        m3r1mbcm_stub_f="results/module3/m3_repo_m1_batch_correction_mirror_integration_stub.flag",
    output:
        "results/module3/module3_export_manifest.json",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "write_module3_export_manifest.py")],
            cwd=str(_ROOT),
        )


rule m5_data_paths_status:
    """Outline M5 prep: record LINCS / cmapPy path presence under data_root (non-fatal if missing)."""
    input:
        m5cfg=str(_ROOT / "config" / "module5_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module5/module5_data_paths_status.json",
        flag="results/module5/module5_data_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module5_data_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m5_lincs_disease_signature:
    """Outline M5 prep: Entrez-level DEA signature TSVs for LINCS/cmapPy connectivity (not sRGES execution)."""
    input:
        welch="results/module3/dea_gbm_vs_gtex_brain.tsv",
        ols="results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv",
        recount3_py="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_results.tsv",
        recount3_ed="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_qlf_results.tsv",
        strat_int="results/module3/stratified_dea_integration.flag",
        hgnc=str(DATA_ROOT / "references" / "hgnc_complete_set.txt"),
        m5cfg=str(_ROOT / "config" / "module5_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        w="results/module5/lincs_disease_signature_welch_entrez.tsv",
        o="results/module5/lincs_disease_signature_ols_entrez.tsv",
        r3_py="results/module5/lincs_disease_signature_recount3_pydeseq2_entrez.tsv",
        r3_ed="results/module5/lincs_disease_signature_recount3_edger_entrez.tsv",
        js="results/module5/lincs_disease_signature_provenance.json",
        flag="results/module5/lincs_disease_signature.flag",
        strat_flag="results/module5/lincs_stratified_signature.flag",
        sw_c="results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Classical_entrez.tsv",
        sw_m="results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Mesenchymal_entrez.tsv",
        sw_n="results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Neural_entrez.tsv",
        sw_p="results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Proneural_entrez.tsv",
        so_c="results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Classical_entrez.tsv",
        so_m="results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Mesenchymal_entrez.tsv",
        so_n="results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Neural_entrez.tsv",
        so_p="results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Proneural_entrez.tsv",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "export_module5_lincs_disease_signature.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m5_cmap_tooling_scan:
    """Outline M5 prep: cmapPy import probe + path-check digest (after data paths + Entrez signature provenance)."""
    input:
        dp="results/module5/module5_data_paths_status.json",
        lincs_js="results/module5/lincs_disease_signature_provenance.json",
        m5cfg=str(_ROOT / "config" / "module5_inputs.yaml"),
    output:
        js="results/module5/cmap_tooling_scan.json",
        flag="results/module5/cmap_tooling_scan.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module5_cmap_tooling_scan.py")],
            cwd=str(_ROOT),
        )


rule m5_lincs_connectivity_readiness:
    """Outline M5: single JSON merging path status, cmap scan, and on-disk Entrez signature checks (no sRGES run)."""
    input:
        m5cfg=str(_ROOT / "config" / "module5_inputs.yaml"),
        dp="results/module5/module5_data_paths_status.json",
        cmap_js="results/module5/cmap_tooling_scan.json",
        cmap_f="results/module5/cmap_tooling_scan.flag",
        lincs_js="results/module5/lincs_disease_signature_provenance.json",
    output:
        js="results/module5/lincs_connectivity_readiness.json",
        flag="results/module5/lincs_connectivity_readiness.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module5_lincs_connectivity_readiness.py")],
            cwd=str(_ROOT),
        )


rule m5_lincs_signature_pack:
    """Outline M5: JSON catalog of global + stratified Entrez signature paths (from lincs_disease_signature provenance)."""
    input:
        lincs_js="results/module5/lincs_disease_signature_provenance.json",
        m5cfg=str(_ROOT / "config" / "module5_inputs.yaml"),
    output:
        js="results/module5/lincs_signature_pack.json",
        flag="results/module5/lincs_signature_pack.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "export_module5_lincs_signature_pack.py")],
            cwd=str(_ROOT),
        )


rule m5_srges_run:
    """Outline M5: compound ranks vs Entrez signature from real perturbation_tsv under data_root (optional rule all)."""
    input:
        sig_w="results/module5/lincs_disease_signature_welch_entrez.tsv",
        pack_js="results/module5/lincs_signature_pack.json",
        pack_f="results/module5/lincs_signature_pack.flag",
        m5srgescfg=str(_ROOT / "config" / "m5_srges.yaml"),
        m5cfg=str(_ROOT / "config" / "module5_inputs.yaml"),
        pert_tsv=lambda wildcards: _m5_srges_perturbation_tsv_path(),
    output:
        rank="results/module5/m5_srges_compound_ranks.tsv",
        prov="results/module5/m5_srges_run_provenance.json",
        flag="results/module5/m5_srges_run.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "run_m5_srges.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m5_srges_integration_stub:
    """Outline M5: sRGES/L1000 gap checklist (reads m5_srges_run provenance when GLIOMA_TARGET_INCLUDE_M5_SRGES_RUN built it)."""
    input:
        m5cfg=str(_ROOT / "config" / "module5_inputs.yaml"),
        dp="results/module5/module5_data_paths_status.json",
        ready_js="results/module5/lincs_connectivity_readiness.json",
        ready_f="results/module5/lincs_connectivity_readiness.flag",
        pack_js="results/module5/lincs_signature_pack.json",
        pack_f="results/module5/lincs_signature_pack.flag",
    output:
        js="results/module5/srges_integration_stub.json",
        flag="results/module5/srges_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module5_srges_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m5_modality_paths_status:
    """Outline M5: TMZ / CAR-T optional staging paths under data_root (presence only)."""
    input:
        m5modcfg=str(_ROOT / "config" / "m5_modality_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module5/m5_modality_paths_status.json",
        flag="results/module5/m5_modality_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module5_modality_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m5_modality_integration_stub:
    """Outline M5: TMZ sensitization + CAR-T surface funnel gap checklist (echoes sRGES stub when present)."""
    input:
        m5modcfg=str(_ROOT / "config" / "m5_modality_outline_inputs.yaml"),
        js="results/module5/m5_modality_paths_status.json",
        flag="results/module5/m5_modality_paths_status.flag",
        srges_js="results/module5/srges_integration_stub.json",
        srges_f="results/module5/srges_integration_stub.flag",
    output:
        out_js="results/module5/m5_modality_integration_stub.json",
        out_f="results/module5/m5_modality_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module5_modality_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m5_l1000_data_paths_status:
    """Outline M5: L1000 GCTX / CLUE / cmap reference optional staging paths under data_root."""
    input:
        m5l1cfg=str(_ROOT / "config" / "m5_l1000_data_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module5/m5_l1000_data_paths_status.json",
        flag="results/module5/m5_l1000_data_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module5_l1000_data_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m5_l1000_data_integration_stub:
    """Outline M5: L1000 data staging gap checklist (after sRGES / connectivity gap stub)."""
    input:
        m5l1cfg=str(_ROOT / "config" / "m5_l1000_data_outline_inputs.yaml"),
        js="results/module5/m5_l1000_data_paths_status.json",
        flag="results/module5/m5_l1000_data_paths_status.flag",
        srges_js="results/module5/srges_integration_stub.json",
        srges_f="results/module5/srges_integration_stub.flag",
    output:
        out_js="results/module5/m5_l1000_data_integration_stub.json",
        out_f="results/module5/m5_l1000_data_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module5_l1000_data_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m5_srges_output_paths_status:
    """Outline M5 supplement: optional sRGES rank / compound prior / pathway projection export dirs under data_root."""
    input:
        m5socfg=str(_ROOT / "config" / "m5_srges_output_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module5/m5_srges_output_paths_status.json",
        flag="results/module5/m5_srges_output_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m5_srges_output_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m5_srges_output_integration_stub:
    """Outline M5 supplement: sRGES output staging checklist (echoes srges_integration_stub; optional L1000 paths read in script)."""
    input:
        m5socfg=str(_ROOT / "config" / "m5_srges_output_outline_inputs.yaml"),
        js="results/module5/m5_srges_output_paths_status.json",
        flag="results/module5/m5_srges_output_paths_status.flag",
        srges_js="results/module5/srges_integration_stub.json",
        srges_f="results/module5/srges_integration_stub.flag",
    output:
        out_js="results/module5/m5_srges_output_integration_stub.json",
        out_f="results/module5/m5_srges_output_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m5_srges_output_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m5_lincs_connectivity_mirror_paths_status:
    """Outline M5 optional cmap or CLUE connectivity query result mirrors under data_root/lincs (presence only)."""
    input:
        m5lcmcfg=str(_ROOT / "config" / "m5_lincs_connectivity_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module5/m5_lincs_connectivity_mirror_paths_status.json",
        flag="results/module5/m5_lincs_connectivity_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m5_lincs_connectivity_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m5_lincs_connectivity_mirror_integration_stub:
    """Outline M5 connectivity mirror checklist (L1000 data stub echo; optional lincs_connectivity_readiness on disk)."""
    input:
        m5lcmcfg=str(_ROOT / "config" / "m5_lincs_connectivity_mirror_outline_inputs.yaml"),
        js="results/module5/m5_lincs_connectivity_mirror_paths_status.json",
        flag="results/module5/m5_lincs_connectivity_mirror_paths_status.flag",
        l1_stub_js="results/module5/m5_l1000_data_integration_stub.json",
        l1_stub_f="results/module5/m5_l1000_data_integration_stub.flag",
    output:
        out_js="results/module5/m5_lincs_connectivity_mirror_integration_stub.json",
        out_f="results/module5/m5_lincs_connectivity_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m5_lincs_connectivity_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m5_export_manifest:
    """Outline M5: JSON inventory of path-status + LINCS Entrez signature outputs."""
    input:
        writer=str(_ROOT / "scripts" / "write_module5_export_manifest.py"),
        manifest_opt=str(_ROOT / "scripts" / "manifest_optional.py"),
        m5cfg=str(_ROOT / "config" / "module5_inputs.yaml"),
        dp="results/module5/module5_data_paths_status.json",
        cmap_js="results/module5/cmap_tooling_scan.json",
        cmap_f="results/module5/cmap_tooling_scan.flag",
        lincs_js="results/module5/lincs_disease_signature_provenance.json",
        lincs_f="results/module5/lincs_disease_signature.flag",
        lincs_sf="results/module5/lincs_stratified_signature.flag",
        m5lc_sig_w="results/module5/lincs_disease_signature_welch_entrez.tsv",
        m5lc_sig_o="results/module5/lincs_disease_signature_ols_entrez.tsv",
        m5lc_sig_r3py="results/module5/lincs_disease_signature_recount3_pydeseq2_entrez.tsv",
        m5lc_sig_r3ed="results/module5/lincs_disease_signature_recount3_edger_entrez.tsv",
        m5lc_sw_cl="results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Classical_entrez.tsv",
        m5lc_sw_me="results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Mesenchymal_entrez.tsv",
        m5lc_sw_ne="results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Neural_entrez.tsv",
        m5lc_sw_pr="results/module5/lincs_disease_signature/stratified/welch_integrated/dea_welch_subtype_Proneural_entrez.tsv",
        m5lc_so_cl="results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Classical_entrez.tsv",
        m5lc_so_me="results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Mesenchymal_entrez.tsv",
        m5lc_so_ne="results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Neural_entrez.tsv",
        m5lc_so_pr="results/module5/lincs_disease_signature/stratified/ols_integrated/dea_ols_subtype_Proneural_entrez.tsv",
        readiness_js="results/module5/lincs_connectivity_readiness.json",
        readiness_f="results/module5/lincs_connectivity_readiness.flag",
        pack_js="results/module5/lincs_signature_pack.json",
        pack_f="results/module5/lincs_signature_pack.flag",
        srges_js="results/module5/srges_integration_stub.json",
        srges_f="results/module5/srges_integration_stub.flag",
        mod_js="results/module5/m5_modality_paths_status.json",
        mod_f="results/module5/m5_modality_paths_status.flag",
        mod_stub_js="results/module5/m5_modality_integration_stub.json",
        mod_stub_f="results/module5/m5_modality_integration_stub.flag",
        l1_js="results/module5/m5_l1000_data_paths_status.json",
        l1_f="results/module5/m5_l1000_data_paths_status.flag",
        l1_stub_js="results/module5/m5_l1000_data_integration_stub.json",
        l1_stub_f="results/module5/m5_l1000_data_integration_stub.flag",
        m5so_js="results/module5/m5_srges_output_paths_status.json",
        m5so_f="results/module5/m5_srges_output_paths_status.flag",
        m5so_stub_js="results/module5/m5_srges_output_integration_stub.json",
        m5so_stub_f="results/module5/m5_srges_output_integration_stub.flag",
        m5lcm_js="results/module5/m5_lincs_connectivity_mirror_paths_status.json",
        m5lcm_f="results/module5/m5_lincs_connectivity_mirror_paths_status.flag",
        m5lcm_stub_js="results/module5/m5_lincs_connectivity_mirror_integration_stub.json",
        m5lcm_stub_f="results/module5/m5_lincs_connectivity_mirror_integration_stub.flag",
    output:
        "results/module5/module5_export_manifest.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "write_module5_export_manifest.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule dea_gbm_vs_gtex_brain:
    """Outline M2 §2.1: Welch tumor vs pooled normals + outline reporting flags; see docs/DEA_METHODOLOGY.md."""
    input:
        expr="results/module3/toil_gbm_vs_brain_tpm.parquet",
        samples="results/module3/toil_gbm_vs_brain_samples.tsv",
    output:
        "results/module3/dea_gbm_vs_gtex_brain.tsv",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "dea_tumor_vs_normal.py")],
            cwd=str(_ROOT),
        )


rule dea_gbm_vs_gtex_brain_ols_region:
    """Outline M2 §2.1 (preferred estimand): OLS tumor vs ref GTEx region + region dummies; outline flags."""
    input:
        expr="results/module3/toil_gbm_vs_brain_tpm.parquet",
        samples="results/module3/toil_gbm_vs_brain_samples.tsv",
    output:
        "results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "dea_ols_gtex_region_covariate.py")],
            cwd=str(_ROOT),
        )


rule m2_outline_driver_flags:
    """Outline M2.2: outline driver flag on primary + DepMap/MAF/MutSig DEA tables; integrated stratified tables after m2_stratified_dea_integration."""
    input:
        welch="results/module3/dea_gbm_vs_gtex_brain.tsv",
        ols="results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv",
        cr_w="results/module3/dea_gbm_vs_gtex_brain_depmap_crispr.tsv",
        cr_o="results/module3/dea_gbm_vs_gtex_brain_ols_depmap_crispr.tsv",
        so_w="results/module3/dea_gbm_vs_gtex_brain_depmap_somatic.tsv",
        so_o="results/module3/dea_gbm_vs_gtex_brain_ols_depmap_somatic.tsv",
        maf_w="results/module3/dea_gbm_vs_gtex_brain_tcga_maf.tsv",
        maf_o="results/module3/dea_gbm_vs_gtex_brain_ols_tcga_maf.tsv",
        mu_w="results/module3/dea_gbm_vs_gtex_brain_mutsig.tsv",
        mu_o="results/module3/dea_gbm_vs_gtex_brain_ols_mutsig.tsv",
        r3_d2="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_results.tsv",
        r3_ed="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_qlf_results.tsv",
        r3_d2_cr="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_depmap_crispr.tsv",
        r3_ed_cr="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_depmap_crispr.tsv",
        r3_d2_so="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_depmap_somatic.tsv",
        r3_ed_so="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_depmap_somatic.tsv",
        r3_d2_maf="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_tcga_maf.tsv",
        r3_ed_maf="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_tcga_maf.tsv",
        r3_d2_mu="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_mutsig.tsv",
        r3_ed_mu="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_mutsig.tsv",
        strat_int="results/module3/stratified_dea_integration.flag",
        sym=str(_ROOT / "references" / "gbm_known_drivers_outline.yaml"),
        integ=str(_ROOT / "config" / "module2_integration.yaml"),
    output:
        w="results/module3/dea_gbm_vs_gtex_brain_outline_drivers.tsv",
        o="results/module3/dea_gbm_vs_gtex_brain_ols_outline_drivers.tsv",
        cr_w_out="results/module3/dea_gbm_vs_gtex_brain_depmap_crispr_outline_drivers.tsv",
        cr_o_out="results/module3/dea_gbm_vs_gtex_brain_ols_depmap_crispr_outline_drivers.tsv",
        so_w_out="results/module3/dea_gbm_vs_gtex_brain_depmap_somatic_outline_drivers.tsv",
        so_o_out="results/module3/dea_gbm_vs_gtex_brain_ols_depmap_somatic_outline_drivers.tsv",
        maf_w_out="results/module3/dea_gbm_vs_gtex_brain_tcga_maf_outline_drivers.tsv",
        maf_o_out="results/module3/dea_gbm_vs_gtex_brain_ols_tcga_maf_outline_drivers.tsv",
        mu_w_out="results/module3/dea_gbm_vs_gtex_brain_mutsig_outline_drivers.tsv",
        mu_o_out="results/module3/dea_gbm_vs_gtex_brain_ols_mutsig_outline_drivers.tsv",
        r3_d2_out="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_outline_drivers.tsv",
        r3_ed_out="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_outline_drivers.tsv",
        r3_d2_cr_out="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_depmap_crispr_outline_drivers.tsv",
        r3_ed_cr_out="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_depmap_crispr_outline_drivers.tsv",
        r3_d2_so_out="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_depmap_somatic_outline_drivers.tsv",
        r3_ed_so_out="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_depmap_somatic_outline_drivers.tsv",
        r3_d2_maf_out="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_tcga_maf_outline_drivers.tsv",
        r3_ed_maf_out="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_tcga_maf_outline_drivers.tsv",
        r3_d2_mu_out="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_mutsig_outline_drivers.tsv",
        r3_ed_mu_out="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_mutsig_outline_drivers.tsv",
        strat_flag="results/module3/stratified_integrated_outline_drivers.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "join_dea_outline_driver_flags.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m7_gts_candidate_stub:
    """Outline M7 stub: ranked candidate table (DEA + DepMap CRISPR + outline flags, evidence tiers)."""
    input:
        cr_w="results/module3/dea_gbm_vs_gtex_brain_depmap_crispr_outline_drivers.tsv",
        cr_o="results/module3/dea_gbm_vs_gtex_brain_ols_depmap_crispr_outline_drivers.tsv",
        r3_py_cr="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_depmap_crispr_outline_drivers.tsv",
        r3_ed_cr="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_depmap_crispr_outline_drivers.tsv",
        strat_int="results/module3/stratified_dea_integration.flag",
        str_w="results/module3/dea_welch_string_m21_depmap_crispr_median_lte_minus0p5.txt",
        str_o="results/module3/dea_ols_string_m21_depmap_crispr_median_lte_minus0p5.txt",
        str_r3py="results/module3/dea_recount3_pydeseq2_string_depmap_crispr_median_lte_minus0p5.txt",
        str_r3ed="results/module3/dea_recount3_edger_string_depmap_crispr_median_lte_minus0p5.txt",
        str_sw_c="results/module4/stratified_string/welch_integrated_m21_depmap/dea_welch_subtype_Classical_string_m21_depmap_crispr_median_lte_minus0p5.txt",
        str_sw_m="results/module4/stratified_string/welch_integrated_m21_depmap/dea_welch_subtype_Mesenchymal_string_m21_depmap_crispr_median_lte_minus0p5.txt",
        str_sw_n="results/module4/stratified_string/welch_integrated_m21_depmap/dea_welch_subtype_Neural_string_m21_depmap_crispr_median_lte_minus0p5.txt",
        str_sw_p="results/module4/stratified_string/welch_integrated_m21_depmap/dea_welch_subtype_Proneural_string_m21_depmap_crispr_median_lte_minus0p5.txt",
        str_so_c="results/module4/stratified_string/ols_integrated_m21_depmap/dea_ols_subtype_Classical_string_m21_depmap_crispr_median_lte_minus0p5.txt",
        str_so_m="results/module4/stratified_string/ols_integrated_m21_depmap/dea_ols_subtype_Mesenchymal_string_m21_depmap_crispr_median_lte_minus0p5.txt",
        str_so_n="results/module4/stratified_string/ols_integrated_m21_depmap/dea_ols_subtype_Neural_string_m21_depmap_crispr_median_lte_minus0p5.txt",
        str_so_p="results/module4/stratified_string/ols_integrated_m21_depmap/dea_ols_subtype_Proneural_string_m21_depmap_crispr_median_lte_minus0p5.txt",
        hgnc=str(DATA_ROOT / "references" / "hgnc_complete_set.txt"),
        m7cfg=str(_ROOT / "config" / "module7_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        w="results/module7/gts_candidate_table_welch_stub.tsv",
        t1_welch="results/module7/glioma_target_tier1_welch.tsv",
        o="results/module7/gts_candidate_table_ols_stub.tsv",
        r3_py="results/module7/gts_candidate_table_recount3_pydeseq2_stub.tsv",
        r3_ed="results/module7/gts_candidate_table_recount3_edger_stub.tsv",
        js="results/module7/gts_candidate_stub_provenance.json",
        flag="results/module7/gts_candidate_stub.flag",
        strat_flag="results/module7/gts_stratified_candidate_stub.flag",
        sw_c="results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Classical_gts_stub.tsv",
        sw_m="results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Mesenchymal_gts_stub.tsv",
        sw_n="results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Neural_gts_stub.tsv",
        sw_p="results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Proneural_gts_stub.tsv",
        so_c="results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Classical_gts_stub.tsv",
        so_m="results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Mesenchymal_gts_stub.tsv",
        so_n="results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Neural_gts_stub.tsv",
        so_p="results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Proneural_gts_stub.tsv",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "export_gts_candidate_table.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m7_visualize_gts_results:
    """
    Module 7: UHD matplotlib composite + six panel PNGs + PDF from tier-1 and full Welch GTS tables.
    Requires matplotlib (pip install -r requirements-dev.txt). Optional rule all: GLIOMA_TARGET_INCLUDE_M7_VIZ=1
    """
    input:
        t1="results/module7/glioma_target_tier1_welch.tsv",
        full="results/module7/gts_candidate_table_welch_stub.tsv",
        py=str(_ROOT / "scripts" / "visualize_glioma_target_results.py"),
    output:
        png="results/module7/glioma_target_results_uhd.png",
        pdf="results/module7/glioma_target_results_uhd.pdf",
        p01="results/module7/glioma_target_panels/01_tier1_ranked_bars.png",
        p02="results/module7/glioma_target_panels/02_E_M_landscape.png",
        p03="results/module7/glioma_target_panels/03_cohort_hexbin_context.png",
        p04="results/module7/glioma_target_panels/04_subscore_heatmap.png",
        p05="results/module7/glioma_target_panels/05_score_distribution.png",
        p06="results/module7/glioma_target_panels/06_subscore_violin.png",
        done="results/module7/glioma_target_visualization.flag",
    run:
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "visualize_glioma_target_results.py"),
                "--dpi",
                "400",
                "--output",
                "results/module7/glioma_target_results_uhd.png",
                "--output-pdf",
                "results/module7/glioma_target_results_uhd.pdf",
                "--panel-dir",
                "results/module7/glioma_target_panels",
            ],
            cwd=str(_ROOT),
        )
        Path(output.done).parent.mkdir(parents=True, exist_ok=True)
        Path(output.done).write_text("ok\n", encoding="utf-8")


rule m7_export_glioma_results_docx:
    """
    Module 7: Word report from tier-1 TSV (embeds pipeline index summary if results/pipeline_results_index.json exists).
    Requires python-docx (pip install -r requirements-dev.txt). Optional rule all: GLIOMA_TARGET_INCLUDE_M7_DOCX=1
    """
    input:
        t1="results/module7/glioma_target_tier1_welch.tsv",
        py=str(_ROOT / "scripts" / "export_glioma_target_results_docx.py"),
    output:
        docx="results/module7/glioma_target_results_report.docx",
    run:
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "export_glioma_target_results_docx.py"),
                "--tier1-tsv",
                "results/module7/glioma_target_tier1_welch.tsv",
                "--pipeline-index",
                "results/pipeline_results_index.json",
                "--output",
                "results/module7/glioma_target_results_report.docx",
            ],
            cwd=str(_ROOT),
        )


rule m7_glioma_target_deliverables:
    """
    Module 7: single Snakemake target for human-facing outputs (UHD figures + Word report).
    Pulls in m7_visualize_gts_results and m7_export_glioma_results_docx.
    Optional rule all: GLIOMA_TARGET_INCLUDE_M7_DELIVERABLES=1 (requires matplotlib + python-docx).
    Or run explicitly: snakemake m7_glioma_target_deliverables -c1
    """
    input:
        done="results/module7/glioma_target_visualization.flag",
        docx="results/module7/glioma_target_results_report.docx",
    output:
        flag="results/module7/glioma_target_deliverables.flag",
    run:
        Path(output.flag).parent.mkdir(parents=True, exist_ok=True)
        Path(output.flag).write_text(
            "m7_visualize_gts_results + m7_export_glioma_results_docx\n", encoding="utf-8"
        )


rule m7_gts_validation_integration_stub:
    """Outline M7: full GTS / validation gap checklist (reads GTS stub provenance; no new scores)."""
    input:
        m7cfg=str(_ROOT / "config" / "module7_inputs.yaml"),
        js="results/module7/gts_candidate_stub_provenance.json",
        flag="results/module7/gts_candidate_stub.flag",
        strat_flag="results/module7/gts_stratified_candidate_stub.flag",
        w="results/module7/gts_candidate_table_welch_stub.tsv",
    output:
        out_js="results/module7/gts_validation_integration_stub.json",
        out_f="results/module7/gts_validation_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module7_gts_validation_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m7_validation_paths_status:
    """Outline M7: optional external validation / benchmark staging paths under data_root."""
    input:
        m7valcfg=str(_ROOT / "config" / "m7_validation_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module7/m7_validation_paths_status.json",
        flag="results/module7/m7_validation_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module7_validation_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m7_validation_integration_stub:
    """Outline M7: validation / benchmark staging gap checklist (after GTS validation stub)."""
    input:
        m7valcfg=str(_ROOT / "config" / "m7_validation_outline_inputs.yaml"),
        js="results/module7/m7_validation_paths_status.json",
        flag="results/module7/m7_validation_paths_status.flag",
        val_js="results/module7/gts_validation_integration_stub.json",
        val_f="results/module7/gts_validation_integration_stub.flag",
    output:
        out_js="results/module7/m7_validation_integration_stub.json",
        out_f="results/module7/m7_validation_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module7_validation_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m7_gts_external_score_mirror_paths_status:
    """Outline M7 optional external GTS-like or prioritization score mirrors under data_root/gts_external (presence only)."""
    input:
        m7gtsmcfg=str(_ROOT / "config" / "m7_gts_external_score_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module7/m7_gts_external_score_mirror_paths_status.json",
        flag="results/module7/m7_gts_external_score_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m7_gts_external_score_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m7_gts_external_score_mirror_integration_stub:
    """Outline M7 external score mirror checklist (GTS validation stub echo; optional validation stub on disk)."""
    input:
        m7gtsmcfg=str(_ROOT / "config" / "m7_gts_external_score_mirror_outline_inputs.yaml"),
        js="results/module7/m7_gts_external_score_mirror_paths_status.json",
        flag="results/module7/m7_gts_external_score_mirror_paths_status.flag",
        gts_val_js="results/module7/gts_validation_integration_stub.json",
        gts_val_f="results/module7/gts_validation_integration_stub.flag",
    output:
        out_js="results/module7/m7_gts_external_score_mirror_integration_stub.json",
        out_f="results/module7/m7_gts_external_score_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m7_gts_external_score_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m7_export_manifest:
    """
    Outline M7: JSON inventory of GTS stub tables (global + stratified) and flags.
    write_module7_export_manifest.py also records optional viz/docx/deliverables paths when present:
    results/module7/glioma_target_results_uhd.png
    results/module7/glioma_target_results_uhd.pdf
    results/module7/glioma_target_visualization.flag
    results/module7/glioma_target_results_report.docx
    results/module7/glioma_target_deliverables.flag
    results/module7/glioma_target_panels
    """
    input:
        writer=str(_ROOT / "scripts" / "write_module7_export_manifest.py"),
        manifest_opt=str(_ROOT / "scripts" / "manifest_optional.py"),
        m7cfg=str(_ROOT / "config" / "module7_inputs.yaml"),
        m7g_welch="results/module7/gts_candidate_table_welch_stub.tsv",
        m7g_t1_welch="results/module7/glioma_target_tier1_welch.tsv",
        m7g_ols="results/module7/gts_candidate_table_ols_stub.tsv",
        m7g_r3py="results/module7/gts_candidate_table_recount3_pydeseq2_stub.tsv",
        m7g_r3ed="results/module7/gts_candidate_table_recount3_edger_stub.tsv",
        m7g_prov="results/module7/gts_candidate_stub_provenance.json",
        m7g_fl="results/module7/gts_candidate_stub.flag",
        m7g_sfl="results/module7/gts_stratified_candidate_stub.flag",
        m7g_sw_cl="results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Classical_gts_stub.tsv",
        m7g_sw_me="results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Mesenchymal_gts_stub.tsv",
        m7g_sw_ne="results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Neural_gts_stub.tsv",
        m7g_sw_pr="results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Proneural_gts_stub.tsv",
        m7g_so_cl="results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Classical_gts_stub.tsv",
        m7g_so_me="results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Mesenchymal_gts_stub.tsv",
        m7g_so_ne="results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Neural_gts_stub.tsv",
        m7g_so_pr="results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Proneural_gts_stub.tsv",
        m7g_val_js="results/module7/gts_validation_integration_stub.json",
        m7g_val_fl="results/module7/gts_validation_integration_stub.flag",
        m7val_js="results/module7/m7_validation_paths_status.json",
        m7val_f="results/module7/m7_validation_paths_status.flag",
        m7val_stub_js="results/module7/m7_validation_integration_stub.json",
        m7val_stub_f="results/module7/m7_validation_integration_stub.flag",
        m7gtsm_js="results/module7/m7_gts_external_score_mirror_paths_status.json",
        m7gtsm_f="results/module7/m7_gts_external_score_mirror_paths_status.flag",
        m7gtsm_stub_js="results/module7/m7_gts_external_score_mirror_integration_stub.json",
        m7gtsm_stub_f="results/module7/m7_gts_external_score_mirror_integration_stub.flag",
    output:
        "results/module7/module7_export_manifest.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "write_module7_export_manifest.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m6_structure_tooling_paths_status:
    """Outline M6 prep: optional pocket/docking tool paths under data_root (presence only)."""
    input:
        m6cfg=str(_ROOT / "config" / "module6_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module6/module6_structure_tooling_paths_status.json",
        flag="results/module6/module6_structure_tooling_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module6_structure_tooling_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m6_structure_druggability_bridge:
    """Outline M6 stub: GTS tier-filtered table + HGNC UniProt + AlphaFold DB URLs (no pocket/toxicity scoring)."""
    input:
        gts_w="results/module7/gts_candidate_table_welch_stub.tsv",
        gts_o="results/module7/gts_candidate_table_ols_stub.tsv",
        gts_r3_py="results/module7/gts_candidate_table_recount3_pydeseq2_stub.tsv",
        gts_r3_ed="results/module7/gts_candidate_table_recount3_edger_stub.tsv",
        gts_sf="results/module7/gts_stratified_candidate_stub.flag",
        sw_c="results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Classical_gts_stub.tsv",
        sw_m="results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Mesenchymal_gts_stub.tsv",
        sw_n="results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Neural_gts_stub.tsv",
        sw_p="results/module7/gts_candidate_stratified/welch_integrated/dea_welch_subtype_Proneural_gts_stub.tsv",
        so_c="results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Classical_gts_stub.tsv",
        so_m="results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Mesenchymal_gts_stub.tsv",
        so_n="results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Neural_gts_stub.tsv",
        so_p="results/module7/gts_candidate_stratified/ols_integrated/dea_ols_subtype_Proneural_gts_stub.tsv",
        hgnc=str(DATA_ROOT / "references" / "hgnc_complete_set.txt"),
        m6cfg=str(_ROOT / "config" / "module6_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        w="results/module6/structure_druggability_bridge_welch.tsv",
        o="results/module6/structure_druggability_bridge_ols.tsv",
        r3_py="results/module6/structure_druggability_bridge_recount3_pydeseq2.tsv",
        r3_ed="results/module6/structure_druggability_bridge_recount3_edger.tsv",
        js="results/module6/structure_druggability_bridge_provenance.json",
        flag="results/module6/structure_druggability_bridge.flag",
        strat_flag="results/module6/structure_druggability_bridge_stratified.flag",
        m6_sw_c="results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Classical_structure_bridge.tsv",
        m6_sw_m="results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Mesenchymal_structure_bridge.tsv",
        m6_sw_n="results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Neural_structure_bridge.tsv",
        m6_sw_p="results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Proneural_structure_bridge.tsv",
        m6_so_c="results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Classical_structure_bridge.tsv",
        m6_so_m="results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Mesenchymal_structure_bridge.tsv",
        m6_so_n="results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Neural_structure_bridge.tsv",
        m6_so_p="results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Proneural_structure_bridge.tsv",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "export_module6_structure_druggability_bridge.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m6_structure_admet_integration_stub:
    """Outline M6: pocket/ADMET/docking gap checklist (tooling paths + bridge provenance; no scoring)."""
    input:
        m6cfg=str(_ROOT / "config" / "module6_inputs.yaml"),
        tool_js="results/module6/module6_structure_tooling_paths_status.json",
        tool_f="results/module6/module6_structure_tooling_paths_status.flag",
        bridge_js="results/module6/structure_druggability_bridge_provenance.json",
        bridge_f="results/module6/structure_druggability_bridge.flag",
        bridge_sf="results/module6/structure_druggability_bridge_stratified.flag",
    output:
        js="results/module6/structure_admet_integration_stub.json",
        flag="results/module6/structure_admet_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module6_structure_admet_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m6_toxicity_paths_status:
    """Outline M6: CNS / off-tumor / organ toxicity optional staging paths under data_root."""
    input:
        m6toxcfg=str(_ROOT / "config" / "m6_toxicity_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module6/m6_toxicity_paths_status.json",
        flag="results/module6/m6_toxicity_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module6_toxicity_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m6_toxicity_integration_stub:
    """Outline M6: toxicity staging gap checklist (after structure/ADMET gap stub)."""
    input:
        m6toxcfg=str(_ROOT / "config" / "m6_toxicity_outline_inputs.yaml"),
        js="results/module6/m6_toxicity_paths_status.json",
        flag="results/module6/m6_toxicity_paths_status.flag",
        admet_js="results/module6/structure_admet_integration_stub.json",
        admet_f="results/module6/structure_admet_integration_stub.flag",
    output:
        out_js="results/module6/m6_toxicity_integration_stub.json",
        out_f="results/module6/m6_toxicity_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module6_toxicity_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m6_docking_output_paths_status:
    """Outline M6 supplement: optional GNINA/Glide/batch docking output dirs under data_root."""
    input:
        m6dockcfg=str(_ROOT / "config" / "m6_docking_output_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module6/m6_docking_output_paths_status.json",
        flag="results/module6/m6_docking_output_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m6_docking_output_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m6_docking_output_integration_stub:
    """Outline M6 supplement: docking run output staging checklist (echoes structure_admet stub)."""
    input:
        m6dockcfg=str(_ROOT / "config" / "m6_docking_output_outline_inputs.yaml"),
        js="results/module6/m6_docking_output_paths_status.json",
        flag="results/module6/m6_docking_output_paths_status.flag",
        admet_js="results/module6/structure_admet_integration_stub.json",
        admet_f="results/module6/structure_admet_integration_stub.flag",
    output:
        out_js="results/module6/m6_docking_output_integration_stub.json",
        out_f="results/module6/m6_docking_output_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m6_docking_output_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m6_compound_library_mirror_paths_status:
    """Outline M6 optional ChEMBL, PubChem, or docking-ready ligand mirrors under data_root/compounds (presence only)."""
    input:
        m6clmcfg=str(_ROOT / "config" / "m6_compound_library_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module6/m6_compound_library_mirror_paths_status.json",
        flag="results/module6/m6_compound_library_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m6_compound_library_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m6_compound_library_mirror_integration_stub:
    """Outline M6 ligand library mirror checklist (structure or ADMET gap stub echo)."""
    input:
        m6clmcfg=str(_ROOT / "config" / "m6_compound_library_mirror_outline_inputs.yaml"),
        js="results/module6/m6_compound_library_mirror_paths_status.json",
        flag="results/module6/m6_compound_library_mirror_paths_status.flag",
        admet_js="results/module6/structure_admet_integration_stub.json",
        admet_f="results/module6/structure_admet_integration_stub.flag",
    output:
        out_js="results/module6/m6_compound_library_mirror_integration_stub.json",
        out_f="results/module6/m6_compound_library_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m6_compound_library_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m6_export_manifest:
    """Outline M6: JSON inventory of tooling path status + structure bridge outputs."""
    input:
        writer=str(_ROOT / "scripts" / "write_module6_export_manifest.py"),
        manifest_opt=str(_ROOT / "scripts" / "manifest_optional.py"),
        m6cfg=str(_ROOT / "config" / "module6_inputs.yaml"),
        tool_js="results/module6/module6_structure_tooling_paths_status.json",
        tool_f="results/module6/module6_structure_tooling_paths_status.flag",
        bridge_js="results/module6/structure_druggability_bridge_provenance.json",
        bridge_f="results/module6/structure_druggability_bridge.flag",
        bridge_sf="results/module6/structure_druggability_bridge_stratified.flag",
        m6br_welch="results/module6/structure_druggability_bridge_welch.tsv",
        m6br_ols="results/module6/structure_druggability_bridge_ols.tsv",
        m6br_r3py="results/module6/structure_druggability_bridge_recount3_pydeseq2.tsv",
        m6br_r3ed="results/module6/structure_druggability_bridge_recount3_edger.tsv",
        m6br_sw_cl="results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Classical_structure_bridge.tsv",
        m6br_sw_me="results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Mesenchymal_structure_bridge.tsv",
        m6br_sw_ne="results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Neural_structure_bridge.tsv",
        m6br_sw_pr="results/module6/structure_druggability_bridge_stratified/welch_integrated/dea_welch_subtype_Proneural_structure_bridge.tsv",
        m6br_so_cl="results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Classical_structure_bridge.tsv",
        m6br_so_me="results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Mesenchymal_structure_bridge.tsv",
        m6br_so_ne="results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Neural_structure_bridge.tsv",
        m6br_so_pr="results/module6/structure_druggability_bridge_stratified/ols_integrated/dea_ols_subtype_Proneural_structure_bridge.tsv",
        admet_js="results/module6/structure_admet_integration_stub.json",
        admet_f="results/module6/structure_admet_integration_stub.flag",
        tox_js="results/module6/m6_toxicity_paths_status.json",
        tox_f="results/module6/m6_toxicity_paths_status.flag",
        tox_stub_js="results/module6/m6_toxicity_integration_stub.json",
        tox_stub_f="results/module6/m6_toxicity_integration_stub.flag",
        dock_js="results/module6/m6_docking_output_paths_status.json",
        dock_f="results/module6/m6_docking_output_paths_status.flag",
        dock_stub_js="results/module6/m6_docking_output_integration_stub.json",
        dock_stub_f="results/module6/m6_docking_output_integration_stub.flag",
        m6clm_js="results/module6/m6_compound_library_mirror_paths_status.json",
        m6clm_f="results/module6/m6_compound_library_mirror_paths_status.flag",
        m6clm_stub_js="results/module6/m6_compound_library_mirror_integration_stub.json",
        m6clm_stub_f="results/module6/m6_compound_library_mirror_integration_stub.flag",
    output:
        "results/module6/module6_export_manifest.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "write_module6_export_manifest.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule pipeline_results_index:
    """Cross-module: merge M3–M7 export manifests + provenance paths; fresh exists/size/mtime per path.
    Optional gate: env GLIOMA_TARGET_PIPELINE_INDEX_STRICT=1/true/yes/on in run: fails on required missing paths
    (use 0/false/no/off to disable). Summary then includes strict_triggers ["env"] (write_pipeline_results_index.py)."""
    input:
        idx_script=str(_ROOT / "scripts" / "write_pipeline_results_index.py"),
        m3="results/module3/module3_export_manifest.json",
        m4="results/module4/module4_export_manifest.json",
        m5="results/module5/module5_export_manifest.json",
        m6="results/module6/module6_export_manifest.json",
        m7="results/module7/module7_export_manifest.json",
        m3_r3_deseq2_prv="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_provenance.json",
        m3_dea_string_prv="results/module3/dea_string_export_provenance.json",
        m4_wgcna_hub_prv="results/module4/wgcna_hub_expr_subset_provenance.json",
        m4_wgcna_hub_r3_prv="results/module4/wgcna_hub_expr_subset_recount3_only_provenance.json",
        m4_wgcna_overlap_js="results/module4/wgcna_hub_gene_overlap_summary.json",
        gsea_js="results/module4/gsea_prerank_export_provenance.json",
        lincs_js="results/module5/lincs_disease_signature_provenance.json",
        m6_js="results/module6/structure_druggability_bridge_provenance.json",
        m7_js="results/module7/gts_candidate_stub_provenance.json",
        inv=str(_ROOT / "config" / "pipeline_inventory.yaml"),
    output:
        "results/pipeline_results_index.json",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "write_pipeline_results_index.py")],
            cwd=str(_ROOT),
        )


rule m2_mean_expression_by_subtype:
    """Outline M2/4 bridge: per-gene mean hub log expression per Verhaak subtype (≥ min samples)."""
    input:
        expr="results/module3/toil_gbm_vs_brain_tpm.parquet",
        subtypes="results/module3/tcga_gbm_verhaak_subtype_scores.tsv",
        integ=str(_ROOT / "config" / "module2_integration.yaml"),
    output:
        tsv="results/module3/mean_log_tpm_by_verhaak_subtype.tsv",
        js="results/module3/mean_log_tpm_by_verhaak_subtype_provenance.json",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "mean_expression_by_verhaak_subtype.py")],
            cwd=str(_ROOT),
        )


rule m2_dea_string_export:
    """Outline M4 prep: HGNC symbol lists for STRING (Welch/OLS + recount3 PyDESeq2/edgeR FDR, M2.1, |LFC|, DepMap CRISPR gates)."""
    input:
        welch="results/module3/dea_gbm_vs_gtex_brain.tsv",
        ols="results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv",
        welch_dm="results/module3/dea_gbm_vs_gtex_brain_depmap_crispr.tsv",
        ols_dm="results/module3/dea_gbm_vs_gtex_brain_ols_depmap_crispr.tsv",
        recount3_py="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_results.tsv",
        recount3_ed="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_qlf_results.tsv",
        recount3_py_dm="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_depmap_crispr.tsv",
        recount3_ed_dm="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_depmap_crispr.tsv",
        hgnc=str(DATA_ROOT / "references" / "hgnc_complete_set.txt"),
        integ=str(_ROOT / "config" / "module2_integration.yaml"),
    output:
        fdr="results/module3/dea_welch_fdr05_symbols_for_string.txt",
        m21w="results/module3/dea_welch_string_m21_high_confidence.txt",
        lfc="results/module3/dea_welch_string_fdr_lfc_ge_1p5.txt",
        m21o="results/module3/dea_ols_string_m21_high_confidence.txt",
        dm_w="results/module3/dea_welch_string_m21_depmap_crispr_median_lte_minus0p5.txt",
        dm_o="results/module3/dea_ols_string_m21_depmap_crispr_median_lte_minus0p5.txt",
        r3_py="results/module3/dea_recount3_pydeseq2_string_fdr05.txt",
        r3_ed="results/module3/dea_recount3_edger_string_fdr05.txt",
        r3_py_dm="results/module3/dea_recount3_pydeseq2_string_depmap_crispr_median_lte_minus0p5.txt",
        r3_ed_dm="results/module3/dea_recount3_edger_string_depmap_crispr_median_lte_minus0p5.txt",
        js="results/module3/dea_string_export_provenance.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "export_dea_string_gene_list.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m4_recount3_depmap_string_consensus:
    """WGCNA prep: symbols in both recount3 DepMap-gated STRING lists (PyDESeq2 ∩ edgeR count-based DE)."""
    input:
        py="results/module3/dea_recount3_pydeseq2_string_depmap_crispr_median_lte_minus0p5.txt",
        ed="results/module3/dea_recount3_edger_string_depmap_crispr_median_lte_minus0p5.txt",
    output:
        txt="results/module3/dea_recount3_depmap_crispr_consensus_string.txt",
    run:
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "intersect_symbol_lists.py"),
                str(output.txt),
                str(input.py),
                str(input.ed),
            ],
            cwd=str(_ROOT),
        )


rule m4_wgcna_hub_expr_subset:
    """Outline M4.1: subset hub TPM matrix to STRING/DEA gene lists for WGCNA (tumor samples default)."""
    input:
        expr="results/module3/toil_gbm_vs_brain_tpm.parquet",
        samples="results/module3/toil_gbm_vs_brain_samples.tsv",
        hgnc=str(DATA_ROOT / "references" / "hgnc_complete_set.txt"),
        integ=str(_ROOT / "config" / "module2_integration.yaml"),
        gene_lists=_wgcna_symbol_list_input_paths,
    output:
        pq="results/module4/wgcna_hub_expr_subset.parquet",
        long="results/module4/wgcna_hub_expr_subset_long.tsv",
        js="results/module4/wgcna_hub_expr_subset_provenance.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "export_wgcna_hub_subset.py"),
                "--config-block",
                "wgcna_hub_subset",
            ],
            cwd=str(_ROOT),
            env=env,
        )


rule m4_wgcna_hub_expr_subset_recount3_only:
    """M4.1 alternate hub: TOIL TPM × tumor samples, genes from recount3 DepMap consensus only (no M2.1)."""
    input:
        expr="results/module3/toil_gbm_vs_brain_tpm.parquet",
        samples="results/module3/toil_gbm_vs_brain_samples.tsv",
        hgnc=str(DATA_ROOT / "references" / "hgnc_complete_set.txt"),
        integ=str(_ROOT / "config" / "module2_integration.yaml"),
        gene_lists=_wgcna_symbol_list_input_paths_recount3_only,
    output:
        pq="results/module4/wgcna_hub_expr_subset_recount3_only.parquet",
        long="results/module4/wgcna_hub_expr_subset_recount3_only_long.tsv",
        js="results/module4/wgcna_hub_expr_subset_recount3_only_provenance.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "export_wgcna_hub_subset.py"),
                "--config-block",
                "wgcna_hub_subset_recount3_only",
            ],
            cwd=str(_ROOT),
            env=env,
        )


rule m4_wgcna_sample_traits:
    """Outline M4.1: sample trait table (Verhaak + manifest) aligned to WGCNA hub subset columns."""
    input:
        samples="results/module3/toil_gbm_vs_brain_samples.tsv",
        scores="results/module3/tcga_gbm_verhaak_subtype_scores.tsv",
        subset_pq="results/module4/wgcna_hub_expr_subset.parquet",
        expr="results/module3/toil_gbm_vs_brain_tpm.parquet",
        integ=str(_ROOT / "config" / "module2_integration.yaml"),
    output:
        tsv="results/module4/wgcna_hub_sample_traits.tsv",
        js="results/module4/wgcna_hub_sample_traits_provenance.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "export_wgcna_sample_traits.py"),
                "--config-block",
                "wgcna_sample_traits",
            ],
            cwd=str(_ROOT),
            env=env,
        )


rule m4_wgcna_sample_traits_recount3_only:
    """M4.1: sample traits aligned to recount3-only WGCNA TPM subset columns."""
    input:
        samples="results/module3/toil_gbm_vs_brain_samples.tsv",
        scores="results/module3/tcga_gbm_verhaak_subtype_scores.tsv",
        subset_pq="results/module4/wgcna_hub_expr_subset_recount3_only.parquet",
        expr="results/module3/toil_gbm_vs_brain_tpm.parquet",
        integ=str(_ROOT / "config" / "module2_integration.yaml"),
    output:
        tsv="results/module4/wgcna_hub_sample_traits_recount3_only.tsv",
        js="results/module4/wgcna_hub_sample_traits_recount3_only_provenance.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "export_wgcna_sample_traits.py"),
                "--config-block",
                "wgcna_sample_traits_recount3_only",
            ],
            cwd=str(_ROOT),
            env=env,
        )


rule m4_wgcna_hub_gene_overlap_summary:
    """M4.1 QC: gene_id overlap stats between integrated WGCNA hub and recount3-only hub."""
    input:
        integrated="results/module4/wgcna_hub_expr_subset.parquet",
        recount3_only="results/module4/wgcna_hub_expr_subset_recount3_only.parquet",
    output:
        "results/module4/wgcna_hub_gene_overlap_summary.json",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "summarize_wgcna_hub_gene_overlap.py")],
            cwd=str(_ROOT),
        )


rule m4_gsea_prerank_export:
    """Outline M4/5 prep: GSEA .rnk from global Welch/OLS DEA + recount3 PyDESeq2/edgeR + integrated stratified Welch/OLS."""
    input:
        welch="results/module3/dea_gbm_vs_gtex_brain.tsv",
        ols="results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv",
        recount3_py="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_results.tsv",
        recount3_ed="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_qlf_results.tsv",
        strat_int="results/module3/stratified_dea_integration.flag",
        hgnc=str(DATA_ROOT / "references" / "hgnc_complete_set.txt"),
        integ=str(_ROOT / "config" / "module2_integration.yaml"),
    output:
        rnk_w="results/module4/gsea/dea_welch_signed_neg_log10_p.rnk",
        rnk_o="results/module4/gsea/dea_ols_signed_neg_log10_p.rnk",
        rnk_r3_py="results/module4/gsea/recount3_pydeseq2_signed_neg_log10_p.rnk",
        rnk_r3_ed="results/module4/gsea/recount3_edger_signed_neg_log10_p.rnk",
        js="results/module4/gsea_prerank_export_provenance.json",
        strat_flag="results/module4/gsea_stratified_prerank.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "export_dea_gsea_prerank_rnk.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m4_stratified_string_export:
    """Outline M2.3 / M4: per-subtype HGNC lists from integrated stratified Welch/OLS DEA (M2.1 screen)."""
    input:
        flag="results/module3/stratified_dea_integration.flag",
        hgnc=str(DATA_ROOT / "references" / "hgnc_complete_set.txt"),
        integ=str(_ROOT / "config" / "module2_integration.yaml"),
    output:
        "results/module4/stratified_string_export_provenance.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "export_stratified_dea_string_lists.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m4_network_paths_status:
    """Outline M4: optional WGCNA / SCENIC+ / BioGRID / SLAYER staging paths under data_root."""
    input:
        m4netcfg=str(_ROOT / "config" / "m4_network_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module4/m4_network_paths_status.json",
        flag="results/module4/m4_network_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module4_network_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m4_network_integration_stub:
    """Outline M4: GRN / co-expression gap checklist (echoes hub overlap + STRING provenance when on disk)."""
    input:
        m4netcfg=str(_ROOT / "config" / "m4_network_outline_inputs.yaml"),
        js="results/module4/m4_network_paths_status.json",
        flag="results/module4/m4_network_paths_status.flag",
    output:
        out_js="results/module4/m4_network_integration_stub.json",
        out_f="results/module4/m4_network_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module4_network_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m4_string_cache_paths_status:
    """Outline M4: STRING API / offline PPI cache optional staging paths under data_root."""
    input:
        m4strcfg=str(_ROOT / "config" / "m4_string_cache_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module4/m4_string_cache_paths_status.json",
        flag="results/module4/m4_string_cache_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module4_string_cache_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m4_string_cache_integration_stub:
    """Outline M4: STRING cache / offline PPI gap checklist (after M4 network integration stub)."""
    input:
        m4strcfg=str(_ROOT / "config" / "m4_string_cache_outline_inputs.yaml"),
        js="results/module4/m4_string_cache_paths_status.json",
        flag="results/module4/m4_string_cache_paths_status.flag",
        m4net_stub_js="results/module4/m4_network_integration_stub.json",
        m4net_stub_f="results/module4/m4_network_integration_stub.flag",
    output:
        out_js="results/module4/m4_string_cache_integration_stub.json",
        out_f="results/module4/m4_string_cache_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module4_string_cache_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m4_gsea_mirror_paths_status:
    """Outline M4: optional MSigDB GMT and GSEA or fgsea output mirrors under data_root/gsea (presence only)."""
    input:
        m4gsmcfg=str(_ROOT / "config" / "m4_gsea_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module4/m4_gsea_mirror_paths_status.json",
        flag="results/module4/m4_gsea_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m4_gsea_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m4_gsea_mirror_integration_stub:
    """Outline M4: GSEA or MSigDB mirror checklist (STRING cache stub echo; gsea_prerank provenance path)."""
    input:
        m4gsmcfg=str(_ROOT / "config" / "m4_gsea_mirror_outline_inputs.yaml"),
        js="results/module4/m4_gsea_mirror_paths_status.json",
        flag="results/module4/m4_gsea_mirror_paths_status.flag",
        m4str_stub_js="results/module4/m4_string_cache_integration_stub.json",
        m4str_stub_f="results/module4/m4_string_cache_integration_stub.flag",
        m2int=str(_ROOT / "config" / "module2_integration.yaml"),
    output:
        out_js="results/module4/m4_gsea_mirror_integration_stub.json",
        out_f="results/module4/m4_gsea_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m4_gsea_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m4_pathway_database_mirror_paths_status:
    """Outline M4: optional KEGG and Reactome pathway mirrors under data_root/pathways (presence only)."""
    input:
        m4pdbcfg=str(_ROOT / "config" / "m4_pathway_database_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module4/m4_pathway_database_mirror_paths_status.json",
        flag="results/module4/m4_pathway_database_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m4_pathway_database_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m4_pathway_database_mirror_integration_stub:
    """Outline M4: KEGG and Reactome mirror checklist (after GSEA mirror integration stub)."""
    input:
        m4pdbcfg=str(_ROOT / "config" / "m4_pathway_database_mirror_outline_inputs.yaml"),
        js="results/module4/m4_pathway_database_mirror_paths_status.json",
        flag="results/module4/m4_pathway_database_mirror_paths_status.flag",
        m4gsm_stub_js="results/module4/m4_gsea_mirror_integration_stub.json",
        m4gsm_stub_f="results/module4/m4_gsea_mirror_integration_stub.flag",
    output:
        out_js="results/module4/m4_pathway_database_mirror_integration_stub.json",
        out_f="results/module4/m4_pathway_database_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m4_pathway_database_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m4_export_manifest:
    """Outline M4: single JSON inventory of STRING lists, WGCNA exports, subtype means (paths, sizes)."""
    input:
        writer=str(_ROOT / "scripts" / "write_module4_export_manifest.py"),
        manifest_opt=str(_ROOT / "scripts" / "manifest_optional.py"),
        integ=str(_ROOT / "config" / "module2_integration.yaml"),
        str_prov="results/module3/dea_string_export_provenance.json",
        strat_prov="results/module4/stratified_string_export_provenance.json",
        gsea_w="results/module4/gsea/dea_welch_signed_neg_log10_p.rnk",
        gsea_o="results/module4/gsea/dea_ols_signed_neg_log10_p.rnk",
        gsea_r3_py="results/module4/gsea/recount3_pydeseq2_signed_neg_log10_p.rnk",
        gsea_r3_ed="results/module4/gsea/recount3_edger_signed_neg_log10_p.rnk",
        gsea_js="results/module4/gsea_prerank_export_provenance.json",
        gsea_strat_flag="results/module4/gsea_stratified_prerank.flag",
        gsea_rsw_cl="results/module4/gsea/stratified/welch_integrated/dea_welch_subtype_Classical_signed_neg_log10_p.rnk",
        gsea_rsw_me="results/module4/gsea/stratified/welch_integrated/dea_welch_subtype_Mesenchymal_signed_neg_log10_p.rnk",
        gsea_rsw_ne="results/module4/gsea/stratified/welch_integrated/dea_welch_subtype_Neural_signed_neg_log10_p.rnk",
        gsea_rsw_pr="results/module4/gsea/stratified/welch_integrated/dea_welch_subtype_Proneural_signed_neg_log10_p.rnk",
        gsea_rso_cl="results/module4/gsea/stratified/ols_integrated/dea_ols_subtype_Classical_signed_neg_log10_p.rnk",
        gsea_rso_me="results/module4/gsea/stratified/ols_integrated/dea_ols_subtype_Mesenchymal_signed_neg_log10_p.rnk",
        gsea_rso_ne="results/module4/gsea/stratified/ols_integrated/dea_ols_subtype_Neural_signed_neg_log10_p.rnk",
        gsea_rso_pr="results/module4/gsea/stratified/ols_integrated/dea_ols_subtype_Proneural_signed_neg_log10_p.rnk",
        wgcna_pq="results/module4/wgcna_hub_expr_subset.parquet",
        wgcna_long="results/module4/wgcna_hub_expr_subset_long.tsv",
        wgcna_js="results/module4/wgcna_hub_expr_subset_provenance.json",
        wgcna_r3_pq="results/module4/wgcna_hub_expr_subset_recount3_only.parquet",
        wgcna_r3_long="results/module4/wgcna_hub_expr_subset_recount3_only_long.tsv",
        wgcna_r3_js="results/module4/wgcna_hub_expr_subset_recount3_only_provenance.json",
        traits="results/module4/wgcna_hub_sample_traits.tsv",
        traits_js="results/module4/wgcna_hub_sample_traits_provenance.json",
        traits_r3="results/module4/wgcna_hub_sample_traits_recount3_only.tsv",
        traits_r3_js="results/module4/wgcna_hub_sample_traits_recount3_only_provenance.json",
        wgcna_overlap="results/module4/wgcna_hub_gene_overlap_summary.json",
        mean_subtype="results/module3/mean_log_tpm_by_verhaak_subtype.tsv",
        m4sa_prov="results/module4/string_api/string_api_fetch_provenance.json",
        m4sa_welch="results/module4/string_api/welch_m21_high_confidence_network.json",
        m4sa_ols="results/module4/string_api/ols_m21_high_confidence_network.json",
        m4sa_r3="results/module4/string_api/recount3_depmap_crispr_consensus_network.json",
        m4net_js="results/module4/m4_network_paths_status.json",
        m4net_f="results/module4/m4_network_paths_status.flag",
        m4net_stub_js="results/module4/m4_network_integration_stub.json",
        m4net_stub_f="results/module4/m4_network_integration_stub.flag",
        m4str_js="results/module4/m4_string_cache_paths_status.json",
        m4str_f="results/module4/m4_string_cache_paths_status.flag",
        m4str_stub_js="results/module4/m4_string_cache_integration_stub.json",
        m4str_stub_f="results/module4/m4_string_cache_integration_stub.flag",
        m4gsm_js="results/module4/m4_gsea_mirror_paths_status.json",
        m4gsm_f="results/module4/m4_gsea_mirror_paths_status.flag",
        m4gsm_stub_js="results/module4/m4_gsea_mirror_integration_stub.json",
        m4gsm_stub_f="results/module4/m4_gsea_mirror_integration_stub.flag",
        m4pdb_js="results/module4/m4_pathway_database_mirror_paths_status.json",
        m4pdb_f="results/module4/m4_pathway_database_mirror_paths_status.flag",
        m4pdb_stub_js="results/module4/m4_pathway_database_mirror_integration_stub.json",
        m4pdb_stub_f="results/module4/m4_pathway_database_mirror_integration_stub.flag",
        archs4_h5_js="results/module4/archs4_recount_h5_summary.json",
        archs4_drv_js="results/module4/archs4_outline_driver_expression_context.json",
        m4_supp_plan="results/module4/m4_supplementary_open_enrichment_plan.json",
        m4_cp_plan="results/module4/m4_clusterprofiler_supplementary_plan.json",
        m4_fgsea_tsv="results/module4/gsea/fgsea_supplementary_pathways_results.tsv",
        m4_cp_tsv="results/module4/gsea/clusterprofiler_supplementary_enricher.tsv",
    output:
        "results/module4/module4_export_manifest.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "write_module4_export_manifest.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_verhaak_subtypes:
    """Outline M2 §2.3: Verhaak subtype calls via MSigDB 2024.1.Hs gene sets (bundled GMT) or compact YAML (config)."""
    input:
        expr="results/module3/toil_gbm_vs_brain_tpm.parquet",
        samples="results/module3/toil_gbm_vs_brain_samples.tsv",
        hgnc=str(DATA_ROOT / "references" / "hgnc_complete_set.txt"),
        gmt=str(_ROOT / "references" / "verhaak_msigdb_c2_cgp_2024.1.Hs.gmt"),
        compact_sig=str(_ROOT / "config" / "gbm_verhaak_signatures.yaml"),
        integ=str(_ROOT / "config" / "module2_integration.yaml"),
    output:
        tsv="results/module3/tcga_gbm_verhaak_subtype_scores.tsv",
        js="results/module3/tcga_gbm_verhaak_subtype_summary.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "score_gbm_verhaak_subtypes.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_depmap_join_dea:
    """Outline M2 §2.2 / M4: median DepMap CRISPR gene effect across GBM models, joined to DEA tables."""
    input:
        dea_ols="results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv",
        dea_welch="results/module3/dea_gbm_vs_gtex_brain.tsv",
    output:
        ols="results/module3/dea_gbm_vs_gtex_brain_ols_depmap_crispr.tsv",
        welch="results/module3/dea_gbm_vs_gtex_brain_depmap_crispr.tsv",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "join_dea_depmap_crispr.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m4_join_dea_archs4_expression:
    """ARCHS4/recount HDF5 cohort marginals (GTEx + TCGA) joined to DEA via HGNC symbol (config/module2_integration.yaml)."""
    input:
        dea_ols="results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv",
        dea_welch="results/module3/dea_gbm_vs_gtex_brain.tsv",
        r3_d2="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_results.tsv",
        r3_ed="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_qlf_results.tsv",
        integ=str(_ROOT / "config" / "module2_integration.yaml"),
    output:
        ols="results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate_archs4.tsv",
        welch="results/module3/dea_gbm_vs_gtex_brain_archs4.tsv",
        r3_d2_out="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_archs4.tsv",
        r3_ed_out="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_archs4.tsv",
        prov="results/module3/dea_archs4_join_provenance.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "join_dea_archs4_expression.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_stratified_dea_by_subtype:
    """Outline M2 §2.3: Welch DEA per Verhaak subtype vs pooled GTEx normals (config/stratified_dea.yaml)."""
    input:
        expr="results/module3/toil_gbm_vs_brain_tpm.parquet",
        samples="results/module3/toil_gbm_vs_brain_samples.tsv",
        subtypes="results/module3/tcga_gbm_verhaak_subtype_scores.tsv",
        dea_cfg=str(_ROOT / "config" / "dea_tumor_normal.yaml"),
        strat_cfg=str(_ROOT / "config" / "stratified_dea.yaml"),
    output:
        "results/module3/stratified_dea/summary.tsv",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "dea_stratified_by_subtype.py")],
            cwd=str(_ROOT),
        )


rule m2_stratified_ols_by_subtype:
    """Outline M2 §2.3: OLS tumor coefficient per Verhaak subtype vs ref GTEx region + region dummies."""
    input:
        expr="results/module3/toil_gbm_vs_brain_tpm.parquet",
        samples="results/module3/toil_gbm_vs_brain_samples.tsv",
        subtypes="results/module3/tcga_gbm_verhaak_subtype_scores.tsv",
        dea_cfg=str(_ROOT / "config" / "dea_tumor_normal.yaml"),
        strat_cfg=str(_ROOT / "config" / "stratified_dea.yaml"),
    output:
        "results/module3/stratified_ols_dea/summary.tsv",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "dea_stratified_ols_by_subtype.py")],
            cwd=str(_ROOT),
        )


rule m2_mutsig_join_dea:
    """Outline M2 §2.2: optional MutSig gene table columns on Welch + OLS DEA (config/mutsig_merge.yaml)."""
    input:
        dea_welch="results/module3/dea_gbm_vs_gtex_brain.tsv",
        dea_ols="results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv",
        cfg=str(_ROOT / "config" / "mutsig_merge.yaml"),
    output:
        welch="results/module3/dea_gbm_vs_gtex_brain_mutsig.tsv",
        ols="results/module3/dea_gbm_vs_gtex_brain_ols_mutsig.tsv",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "join_dea_mutsig.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_stratified_dea_integration:
    """Outline M2 §2.2–2.3: DepMap + MAF + MutSig columns on stratified Welch/OLS DEA (*/integrated/)."""
    input:
        wsum="results/module3/stratified_dea/summary.tsv",
        osum="results/module3/stratified_ols_dea/summary.tsv",
        somatic_sum="results/module3/depmap_gbm_somatic_by_gene.tsv",
        maf_sum="results/module3/tcga_gbm_maf_gene_summary.tsv",
        mut_w="results/module3/dea_gbm_vs_gtex_brain_mutsig.tsv",
        mut_o="results/module3/dea_gbm_vs_gtex_brain_ols_mutsig.tsv",
        integ=str(_ROOT / "config" / "module2_integration.yaml"),
    output:
        "results/module3/stratified_dea_integration.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "join_stratified_dea_integration.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_depmap_somatic_join_dea:
    """Outline M2 §2.2: DepMap somatic mutation burden (GBM lines) joined to DEA; gene-level summary TSV."""
    input:
        dea_ols="results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv",
        dea_welch="results/module3/dea_gbm_vs_gtex_brain.tsv",
        recount3_deseq2="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_results.tsv",
        recount3_edger="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_qlf_results.tsv",
    output:
        ols="results/module3/dea_gbm_vs_gtex_brain_ols_depmap_somatic.tsv",
        welch="results/module3/dea_gbm_vs_gtex_brain_depmap_somatic.tsv",
        genes="results/module3/depmap_gbm_somatic_by_gene.tsv",
        recount3_deseq2="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_depmap_somatic.tsv",
        recount3_edger="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_depmap_somatic.tsv",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "join_dea_depmap_somatic.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_tcga_maf_gene_summary:
    """Outline M2 §2.2: optional TCGA MAF → cohort gene summary (empty if maf_glob unset)."""
    output:
        tsv="results/module3/tcga_gbm_maf_gene_summary.tsv",
        prov="results/module3/tcga_maf_layer_provenance.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "tcga_maf_gene_cohort_summary.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_maf_genes_clinvar_annotate:
    """
    M2.2 (chosen): ClinVar gene_specific_summary.txt joined to MAF cohort gene summary via HGNC symbol.
    Caches ClinVar under data_root/references/clinvar/ (first run downloads from NCBI).
    """
    input:
        maf="results/module3/tcga_gbm_maf_gene_summary.tsv",
        cfg=str(_ROOT / "config" / "m2_2_clinvar_gene_annotation.yaml"),
        py=str(_ROOT / "scripts" / "annotate_maf_genes_clinvar.py"),
    output:
        tsv="results/module3/m2_2_clinvar/maf_genes_with_clinvar_gene_summary.tsv",
        prov="results/module3/m2_2_clinvar/clinvar_gene_annotation_provenance.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "annotate_maf_genes_clinvar.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_3_movics_vs_consensus_report:
    """M2.3: JSON contrast — MOVICS (stub) vs Monti-style consensus clustering implemented in-repo."""
    input:
        mov=str(_ROOT / "config" / "m2_movics_inputs.yaml"),
        cons=str(_ROOT / "config" / "m2_3_consensus_clustering.yaml"),
        py=str(_ROOT / "scripts" / "m2_3_movics_vs_consensus_report.py"),
    output:
        js="results/module3/m2_3_movics_vs_consensus_method_contrast.json",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_3_movics_vs_consensus_report.py")],
            cwd=str(_ROOT),
        )


rule m2_3_consensus_star_primary:
    """M2.3: Consensus clustering on GDC STAR counts (Primary Tumor); sklearn + scipy."""
    input:
        counts="results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet",
        meta="results/module2/tcga_gbm_sample_meta.tsv",
        cfg=str(_ROOT / "config" / "m2_3_consensus_clustering.yaml"),
        py=str(_ROOT / "scripts" / "m2_3_consensus_kmeans_star_primary.py"),
    output:
        tsv="results/module3/m2_3_consensus_star_primary/consensus_sample_clusters.tsv",
        prov="results/module3/m2_3_consensus_star_primary/consensus_provenance.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_3_consensus_kmeans_star_primary.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_movics_intnmf_tcga_gbm:
    """
    M2.3: MOVICS::getIntNMF on two matched layers — log2(TPM+1) and log2(counts+1), same genes × Primary Tumor samples.
    Rscript is resolved like edgeR (registry / config/rscript_local.yaml); R need not be on PATH.
    Install: python scripts/install_r_movics_dependencies.py; ad-hoc R: powershell -File scripts/run_rscript.ps1 ...
    Optional rule all: set GLIOMA_TARGET_INCLUDE_MOVICS=1
    """
    input:
        tpm="results/module2/tcga_gbm_star_tpm_matrix.parquet",
        cnt="results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet",
        meta="results/module2/tcga_gbm_sample_meta.tsv",
        cfg=str(_ROOT / "config" / "m2_movics_run.yaml"),
        r=str(_ROOT / "scripts" / "m2_movics_intnmf_tcga_gbm.R"),
    output:
        tsv="results/module3/m2_movics_intnmf/movics_intnmf_clusters.tsv",
        prov="results/module3/m2_movics_intnmf/movics_intnmf_provenance.json",
    run:
        subprocess.check_call(
            [
                _rscript_exe(),
                str(_ROOT / "scripts" / "m2_movics_intnmf_tcga_gbm.R"),
                str(_ROOT / "config" / "m2_movics_run.yaml"),
            ],
            cwd=str(_ROOT),
        )


rule m2_movics_intnmf_depmap_mae:
    """
    M2.3: MOVICS::getIntNMF on DepMap-derived MAE — expression + CN + mutation (three views, .tsv.gz under data_root).
    Run fetch_movics_staging_data first (DepMap CSVs required). Rscript via _rscript_exe(); set GLIOMA_TARGET_DATA_ROOT if needed.
    Optional rule all: GLIOMA_TARGET_INCLUDE_MOVICS_DEPMAP_MAE=1
    """
    input:
        expr=lambda w: _depmap_mae_gz_paths()[0],
        cn=lambda w: _depmap_mae_gz_paths()[1],
        mut=lambda w: _depmap_mae_gz_paths()[2],
        fetch_cfg=str(_ROOT / "config" / "m2_movics_data_fetch.yaml"),
        run_cfg=str(_ROOT / "config" / "m2_movics_depmap_mae_run.yaml"),
        r=str(_ROOT / "scripts" / "m2_movics_intnmf_depmap_mae.R"),
    output:
        tsv="results/module3/m2_movics_intnmf_depmap_mae/movics_depmap_mae_clusters.tsv",
        prov="results/module3/m2_movics_intnmf_depmap_mae/movics_depmap_mae_provenance.json",
    run:
        subprocess.check_call(
            [
                _rscript_exe(),
                str(_ROOT / "scripts" / "m2_movics_intnmf_depmap_mae.R"),
                str(_ROOT / "config" / "m2_movics_depmap_mae_run.yaml"),
            ],
            cwd=str(_ROOT),
            env={**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)},
        )


rule m2_movics_depmap_intnmf_characterize:
    """
    Interpret DepMap IntNMF clusters: join Model.csv (lineage/subtype), mutation burden, optional CRISPR row means.
    Run after m2_movics_intnmf_depmap_mae; requires DepMap release under data_root/depmap/ (Model.csv + optional CRISPRGeneEffect.csv).
    """
    input:
        clusters="results/module3/m2_movics_intnmf_depmap_mae/movics_depmap_mae_clusters.tsv",
        model_csv=_depmap_model_csv,
        py=str(_ROOT / "scripts" / "m2_depmap_intnmf_cluster_summary.py"),
    output:
        ann="results/module3/m2_movics_intnmf_depmap_mae/cluster_model_annotations.tsv",
        summ="results/module3/m2_movics_intnmf_depmap_mae/cluster_summary.json",
    run:
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "m2_depmap_intnmf_cluster_summary.py"),
                "--clusters",
                input.clusters,
                "--out-annotations",
                output.ann,
                "--out-summary",
                output.summ,
            ],
            cwd=str(_ROOT),
            env={**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)},
        )


rule fetch_movics_staging_data:
    """
    Populate MOVICS path-check dirs under data_root: DepMap-derived multi-omics matrices (omics/multi_omics_mae/),
    optional CGGA HTTP downloads (config m2_movics_data_fetch.yaml cgga_http), CBTTC access readme.
    Requires DepMap CSVs from download_all_required.py. Report: results/module3/movics_staging_fetch_report.json
    """
    input:
        cfg=str(_ROOT / "config" / "m2_movics_data_fetch.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
        py=str(_ROOT / "scripts" / "fetch_movics_staging_data.py"),
    output:
        rep="results/module3/movics_staging_fetch_report.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "fetch_movics_staging_data.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_gse57872_scanpy_qc_cluster:
    """
    M3: GSE57872-oriented Scanpy QC + Leiden clustering. Resolves .h5ad / counts under data_root (see config/m3_gse57872_scanpy.yaml).
    Requires: pip install scanpy anndata (requirements-optional.txt).
    """
    input:
        cfg=str(_ROOT / "config" / "m3_gse57872_scanpy.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
        py=str(_ROOT / "scripts" / "m3_scrna_scanpy_qc_cluster.py"),
    output:
        obs="results/module3/scrna_gse57872_scanpy/obs_qc_leiden.tsv",
        met="results/module3/scrna_gse57872_scanpy/qc_cluster_metrics.json",
        runp="results/module3/scrna_gse57872_scanpy/run_provenance.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_scrna_scanpy_qc_cluster.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_tcga_maf_join_dea:
    """Outline M2 §2.2: join TCGA MAF gene summary columns onto Welch + OLS DEA tables."""
    input:
        dea_ols="results/module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv",
        dea_welch="results/module3/dea_gbm_vs_gtex_brain.tsv",
        recount3_deseq2="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_results.tsv",
        recount3_edger="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_qlf_results.tsv",
        maf_sum="results/module3/tcga_gbm_maf_gene_summary.tsv",
    output:
        ols="results/module3/dea_gbm_vs_gtex_brain_ols_tcga_maf.tsv",
        welch="results/module3/dea_gbm_vs_gtex_brain_tcga_maf.tsv",
        recount3_deseq2="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_tcga_maf.tsv",
        recount3_edger="results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_tcga_maf.tsv",
        join_prov="results/module3/tcga_maf_join_provenance.json",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "join_dea_tcga_maf.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_cptac_methylation_paths_status:
    """Outline M2.1: CPTAC / methylation roots under data_root (presence only)."""
    input:
        m2cm=str(_ROOT / "config" / "m2_cptac_methylation_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m2_cptac_methylation_paths_status.json",
        flag="results/module3/m2_cptac_methylation_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module2_cptac_methylation_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_cptac_methylation_integration_stub:
    """Outline M2.1: CPTAC concordance + methylation silencing gap checklist (no matrix reads)."""
    input:
        m2cm=str(_ROOT / "config" / "m2_cptac_methylation_inputs.yaml"),
        js="results/module3/m2_cptac_methylation_paths_status.json",
        flag="results/module3/m2_cptac_methylation_paths_status.flag",
    output:
        out_js="results/module3/m2_cptac_methylation_integration_stub.json",
        out_f="results/module3/m2_cptac_methylation_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module2_cptac_methylation_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m2_1_star_pairing_paths_status:
    """Outline M2.1: optional GDC/GTEx STAR count mirrors + pairing maps under data_root (presence only)."""
    input:
        m2sp=str(_ROOT / "config" / "m2_1_star_pairing_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m2_1_star_pairing_paths_status.json",
        flag="results/module3/m2_1_star_pairing_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_1_star_pairing_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_1_star_pairing_integration_stub:
    """Outline M2.1: true paired STAR bulk DEA gap checklist (echoes recount3 workaround when on disk)."""
    input:
        m2sp=str(_ROOT / "config" / "m2_1_star_pairing_outline_inputs.yaml"),
        js="results/module3/m2_1_star_pairing_paths_status.json",
        flag="results/module3/m2_1_star_pairing_paths_status.flag",
    output:
        out_js="results/module3/m2_1_star_pairing_integration_stub.json",
        out_f="results/module3/m2_1_star_pairing_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_1_star_pairing_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m2_1_recount3_mirror_paths_status:
    """Outline M2.1: optional recount3 RSE/cache/manifest/mirror trees under data_root (presence only)."""
    input:
        m2r3=str(_ROOT / "config" / "m2_1_recount3_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m2_1_recount3_mirror_paths_status.json",
        flag="results/module3/m2_1_recount3_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_1_recount3_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_1_recount3_mirror_integration_stub:
    """Outline M2.1: recount3 local mirror checklist (after STAR pairing stub; echoes recount3 DEA when on disk)."""
    input:
        m2r3=str(_ROOT / "config" / "m2_1_recount3_mirror_outline_inputs.yaml"),
        js="results/module3/m2_1_recount3_mirror_paths_status.json",
        flag="results/module3/m2_1_recount3_mirror_paths_status.flag",
        m2sp_stub_js="results/module3/m2_1_star_pairing_integration_stub.json",
        m2sp_stub_f="results/module3/m2_1_star_pairing_integration_stub.flag",
    output:
        out_js="results/module3/m2_1_recount3_mirror_integration_stub.json",
        out_f="results/module3/m2_1_recount3_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_1_recount3_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m2_1_toil_xena_hub_paths_status:
    """Outline M2.1: optional TOIL / UCSC Xena hub files under data_root/gtex/xena_toil (presence only)."""
    input:
        m2tx=str(_ROOT / "config" / "m2_1_toil_xena_hub_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m2_1_toil_xena_hub_paths_status.json",
        flag="results/module3/m2_1_toil_xena_hub_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_1_toil_xena_hub_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_1_toil_xena_hub_integration_stub:
    """Outline M2.1: TOIL/Xena hub staging checklist (after M1 outline stub; Welch DEA provenance echo)."""
    input:
        m2tx=str(_ROOT / "config" / "m2_1_toil_xena_hub_outline_inputs.yaml"),
        js="results/module3/m2_1_toil_xena_hub_paths_status.json",
        flag="results/module3/m2_1_toil_xena_hub_paths_status.flag",
        m1_outline_stub_js="results/module3/m1_outline_integration_stub.json",
        m1_outline_stub_f="results/module3/m1_outline_integration_stub.flag",
    output:
        out_js="results/module3/m2_1_toil_xena_hub_integration_stub.json",
        out_f="results/module3/m2_1_toil_xena_hub_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_1_toil_xena_hub_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m2_movics_paths_status:
    """Outline M2.3: external cohort / multi-omics staging paths under data_root (presence only)."""
    input:
        m2mv=str(_ROOT / "config" / "m2_movics_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m2_movics_paths_status.json",
        flag="results/module3/m2_movics_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module2_movics_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_movics_integration_stub:
    """Outline M2.3: MOVICS / consensus clustering gap checklist (Verhaak + paths echo; no R)."""
    input:
        m2mv=str(_ROOT / "config" / "m2_movics_inputs.yaml"),
        js="results/module3/m2_movics_paths_status.json",
        flag="results/module3/m2_movics_paths_status.flag",
        verhaak="results/module3/tcga_gbm_verhaak_subtype_summary.json",
        strat_int="results/module3/stratified_dea_integration.flag",
    output:
        out_js="results/module3/m2_movics_integration_stub.json",
        out_f="results/module3/m2_movics_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module2_movics_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m2_3_immune_tme_mirror_paths_status:
    """Outline M2.3 optional immune signature and TME reference mirrors under data_root/immune_oncology (presence only)."""
    input:
        m2itmcfg=str(_ROOT / "config" / "m2_3_immune_tme_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m2_3_immune_tme_mirror_paths_status.json",
        flag="results/module3/m2_3_immune_tme_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_3_immune_tme_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_3_immune_tme_mirror_integration_stub:
    """Outline M2.3 immune or TME mirror checklist (MOVICS stub echo; optional Verhaak summary on disk)."""
    input:
        m2itmcfg=str(_ROOT / "config" / "m2_3_immune_tme_mirror_outline_inputs.yaml"),
        js="results/module3/m2_3_immune_tme_mirror_paths_status.json",
        flag="results/module3/m2_3_immune_tme_mirror_paths_status.flag",
        movics_stub_js="results/module3/m2_movics_integration_stub.json",
        movics_stub_f="results/module3/m2_movics_integration_stub.flag",
    output:
        out_js="results/module3/m2_3_immune_tme_mirror_integration_stub.json",
        out_f="results/module3/m2_3_immune_tme_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_3_immune_tme_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m2_maf_annotation_integration_stub:
    """Outline M2.2: OncoKB/ClinVar gap checklist (reads MAF layer + join provenance; no annotation API)."""
    input:
        mcfg=str(_ROOT / "config" / "tcga_mutation_layer.yaml"),
        layer_prov="results/module3/tcga_maf_layer_provenance.json",
        maf_sum="results/module3/tcga_gbm_maf_gene_summary.tsv",
        join_prov="results/module3/tcga_maf_join_provenance.json",
        welch_maf="results/module3/dea_gbm_vs_gtex_brain_tcga_maf.tsv",
    output:
        js="results/module3/maf_annotation_integration_stub.json",
        flag="results/module3/maf_annotation_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "module2_maf_annotation_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_m2_maf_annotation_paths_status:
    """Outline M2.2: M3 manifest slice — maf_annotation_integration_stub JSON/flag under results/module3."""
    input:
        m3r2maf_cfg=str(_ROOT / "config" / "m3_repo_m2_maf_annotation_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_m2_maf_annotation_paths_status.json",
        flag="results/module3/m3_repo_m2_maf_annotation_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_maf_annotation_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_m2_maf_annotation_integration_stub:
    """Outline M2.2: MAF annotation stub repo manifest slice (echoes maf_annotation_integration_stub JSON/flag)."""
    input:
        m3r2maf_cfg=str(_ROOT / "config" / "m3_repo_m2_maf_annotation_outline_inputs.yaml"),
        r_js="results/module3/m3_repo_m2_maf_annotation_paths_status.json",
        r_f="results/module3/m3_repo_m2_maf_annotation_paths_status.flag",
        maf_stub_js="results/module3/maf_annotation_integration_stub.json",
        maf_stub_f="results/module3/maf_annotation_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_m2_maf_annotation_integration_stub.json",
        out_f="results/module3/m3_repo_m2_maf_annotation_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_maf_annotation_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m2_2_variant_annotation_paths_status:
    """Outline M2.2: optional VEP / OncoKB / ClinVar cache dirs under data_root (presence only)."""
    input:
        m2vacfg=str(_ROOT / "config" / "m2_2_variant_annotation_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m2_2_variant_annotation_paths_status.json",
        flag="results/module3/m2_2_variant_annotation_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_2_variant_annotation_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_2_variant_annotation_integration_stub:
    """Outline M2.2: variant annotation cache checklist (echoes maf_annotation_integration_stub)."""
    input:
        m2vacfg=str(_ROOT / "config" / "m2_2_variant_annotation_outline_inputs.yaml"),
        js="results/module3/m2_2_variant_annotation_paths_status.json",
        flag="results/module3/m2_2_variant_annotation_paths_status.flag",
        maf_stub_js="results/module3/maf_annotation_integration_stub.json",
        maf_stub_f="results/module3/maf_annotation_integration_stub.flag",
    output:
        out_js="results/module3/m2_2_variant_annotation_integration_stub.json",
        out_f="results/module3/m2_2_variant_annotation_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_2_variant_annotation_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m2_2_depmap_mirror_paths_status:
    """Outline M2.2: optional DepMap CRISPR/omics/model mirrors under data_root/depmap (presence only)."""
    input:
        m2dmcfg=str(_ROOT / "config" / "m2_2_depmap_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m2_2_depmap_mirror_paths_status.json",
        flag="results/module3/m2_2_depmap_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_2_depmap_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_2_depmap_mirror_integration_stub:
    """Outline M2.2: DepMap mirror checklist (after MAF annotation stub; echoes join provenance when on disk)."""
    input:
        m2dmcfg=str(_ROOT / "config" / "m2_2_depmap_mirror_outline_inputs.yaml"),
        js="results/module3/m2_2_depmap_mirror_paths_status.json",
        flag="results/module3/m2_2_depmap_mirror_paths_status.flag",
        maf_stub_js="results/module3/maf_annotation_integration_stub.json",
        maf_stub_f="results/module3/maf_annotation_integration_stub.flag",
    output:
        out_js="results/module3/m2_2_depmap_mirror_integration_stub.json",
        out_f="results/module3/m2_2_depmap_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_2_depmap_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m2_2_maf_mutsig_mirror_paths_status:
    """Outline M2.2: optional TCGA MAF + MutSig gene-level mirrors under data_root/mutations (presence only)."""
    input:
        m2mmcfg=str(_ROOT / "config" / "m2_2_maf_mutsig_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m2_2_maf_mutsig_mirror_paths_status.json",
        flag="results/module3/m2_2_maf_mutsig_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_2_maf_mutsig_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_2_maf_mutsig_mirror_integration_stub:
    """Outline M2.2: MAF + MutSig mirror checklist (MAF stub echo; optional layer/join provenance on disk)."""
    input:
        m2mmcfg=str(_ROOT / "config" / "m2_2_maf_mutsig_mirror_outline_inputs.yaml"),
        js="results/module3/m2_2_maf_mutsig_mirror_paths_status.json",
        flag="results/module3/m2_2_maf_mutsig_mirror_paths_status.flag",
        maf_stub_js="results/module3/maf_annotation_integration_stub.json",
        maf_stub_f="results/module3/maf_annotation_integration_stub.flag",
    output:
        out_js="results/module3/m2_2_maf_mutsig_mirror_integration_stub.json",
        out_f="results/module3/m2_2_maf_mutsig_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_2_maf_mutsig_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m2_2_outline_driver_mirror_paths_status:
    """Outline M2.2: optional extended driver panel mirrors under data_root/drivers (presence only)."""
    input:
        m2odmcfg=str(_ROOT / "config" / "m2_2_outline_driver_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m2_2_outline_driver_mirror_paths_status.json",
        flag="results/module3/m2_2_outline_driver_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_2_outline_driver_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m2_2_outline_driver_mirror_integration_stub:
    """Outline M2.2: driver list mirror checklist (MAF stub echo; outline_driver_flags symbols_yaml path)."""
    input:
        m2odmcfg=str(_ROOT / "config" / "m2_2_outline_driver_mirror_outline_inputs.yaml"),
        js="results/module3/m2_2_outline_driver_mirror_paths_status.json",
        flag="results/module3/m2_2_outline_driver_mirror_paths_status.flag",
        maf_stub_js="results/module3/maf_annotation_integration_stub.json",
        maf_stub_f="results/module3/maf_annotation_integration_stub.flag",
        m2int=str(_ROOT / "config" / "module2_integration.yaml"),
    output:
        out_js="results/module3/m2_2_outline_driver_mirror_integration_stub.json",
        out_f="results/module3/m2_2_outline_driver_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m2_2_outline_driver_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )




rule m3_repo_m2_cptac_methylation_paths_status:
    """Outline M2: M3 manifest slice — m2_cptac_methylation quartet presence under results/module3."""
    input:
        m3r2cptac_cfg=str(_ROOT / "config" / "m3_repo_m2_cptac_methylation_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_m2_cptac_methylation_paths_status.json",
        flag="results/module3/m3_repo_m2_cptac_methylation_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_cptac_methylation_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_m2_cptac_methylation_integration_stub:
    """Outline M2: CPTAC/methylation repo manifest slice (echoes integration stub + paths_status JSON)."""
    input:
        m3r2cptac_cfg=str(_ROOT / "config" / "m3_repo_m2_cptac_methylation_outline_inputs.yaml"),
        r_js="results/module3/m3_repo_m2_cptac_methylation_paths_status.json",
        r_f="results/module3/m3_repo_m2_cptac_methylation_paths_status.flag",
        b_js="results/module3/m2_cptac_methylation_paths_status.json",
        b_f="results/module3/m2_cptac_methylation_paths_status.flag",
        b_stub_js="results/module3/m2_cptac_methylation_integration_stub.json",
        b_stub_f="results/module3/m2_cptac_methylation_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_m2_cptac_methylation_integration_stub.json",
        out_f="results/module3/m3_repo_m2_cptac_methylation_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_cptac_methylation_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_m2_1_star_pairing_paths_status:
    """Outline M2: M3 manifest slice — m2_1_star_pairing quartet presence under results/module3."""
    input:
        m3r2sp_cfg=str(_ROOT / "config" / "m3_repo_m2_1_star_pairing_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_m2_1_star_pairing_paths_status.json",
        flag="results/module3/m3_repo_m2_1_star_pairing_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_1_star_pairing_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_m2_1_star_pairing_integration_stub:
    """Outline M2: STAR pairing repo manifest slice."""
    input:
        m3r2sp_cfg=str(_ROOT / "config" / "m3_repo_m2_1_star_pairing_outline_inputs.yaml"),
        r_js="results/module3/m3_repo_m2_1_star_pairing_paths_status.json",
        r_f="results/module3/m3_repo_m2_1_star_pairing_paths_status.flag",
        b_js="results/module3/m2_1_star_pairing_paths_status.json",
        b_f="results/module3/m2_1_star_pairing_paths_status.flag",
        b_stub_js="results/module3/m2_1_star_pairing_integration_stub.json",
        b_stub_f="results/module3/m2_1_star_pairing_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_m2_1_star_pairing_integration_stub.json",
        out_f="results/module3/m3_repo_m2_1_star_pairing_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_1_star_pairing_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_m2_1_recount3_mirror_paths_status:
    """Outline M2: M3 manifest slice — m2_1_recount3_mirror quartet presence under results/module3."""
    input:
        m3r2r3_cfg=str(_ROOT / "config" / "m3_repo_m2_1_recount3_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_m2_1_recount3_mirror_paths_status.json",
        flag="results/module3/m3_repo_m2_1_recount3_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_1_recount3_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_m2_1_recount3_mirror_integration_stub:
    """Outline M2: recount3 mirror repo manifest slice (echoes recount3 + STAR pairing stubs)."""
    input:
        m3r2r3_cfg=str(_ROOT / "config" / "m3_repo_m2_1_recount3_mirror_outline_inputs.yaml"),
        r_js="results/module3/m3_repo_m2_1_recount3_mirror_paths_status.json",
        r_f="results/module3/m3_repo_m2_1_recount3_mirror_paths_status.flag",
        b_js="results/module3/m2_1_recount3_mirror_paths_status.json",
        b_f="results/module3/m2_1_recount3_mirror_paths_status.flag",
        b_stub_js="results/module3/m2_1_recount3_mirror_integration_stub.json",
        b_stub_f="results/module3/m2_1_recount3_mirror_integration_stub.flag",
        sp_stub_js="results/module3/m2_1_star_pairing_integration_stub.json",
        sp_stub_f="results/module3/m2_1_star_pairing_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_m2_1_recount3_mirror_integration_stub.json",
        out_f="results/module3/m3_repo_m2_1_recount3_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_1_recount3_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_m2_1_toil_xena_hub_paths_status:
    """Outline M2: M3 manifest slice — m2_1_toil_xena_hub quartet presence under results/module3."""
    input:
        m3r2tx_cfg=str(_ROOT / "config" / "m3_repo_m2_1_toil_xena_hub_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_m2_1_toil_xena_hub_paths_status.json",
        flag="results/module3/m3_repo_m2_1_toil_xena_hub_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_1_toil_xena_hub_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_m2_1_toil_xena_hub_integration_stub:
    """Outline M2: TOIL/Xena hub repo manifest slice (echoes TOIL stub + M1 outline stub)."""
    input:
        m3r2tx_cfg=str(_ROOT / "config" / "m3_repo_m2_1_toil_xena_hub_outline_inputs.yaml"),
        r_js="results/module3/m3_repo_m2_1_toil_xena_hub_paths_status.json",
        r_f="results/module3/m3_repo_m2_1_toil_xena_hub_paths_status.flag",
        b_js="results/module3/m2_1_toil_xena_hub_paths_status.json",
        b_f="results/module3/m2_1_toil_xena_hub_paths_status.flag",
        b_stub_js="results/module3/m2_1_toil_xena_hub_integration_stub.json",
        b_stub_f="results/module3/m2_1_toil_xena_hub_integration_stub.flag",
        m1o_stub_js="results/module3/m1_outline_integration_stub.json",
        m1o_stub_f="results/module3/m1_outline_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_m2_1_toil_xena_hub_integration_stub.json",
        out_f="results/module3/m3_repo_m2_1_toil_xena_hub_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_1_toil_xena_hub_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_m2_movics_paths_status:
    """Outline M2: M3 manifest slice — m2_movics quartet presence under results/module3."""
    input:
        m3r2mv_cfg=str(_ROOT / "config" / "m3_repo_m2_movics_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_m2_movics_paths_status.json",
        flag="results/module3/m3_repo_m2_movics_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_movics_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_m2_movics_integration_stub:
    """Outline M2: MOVICS repo manifest slice."""
    input:
        m3r2mv_cfg=str(_ROOT / "config" / "m3_repo_m2_movics_outline_inputs.yaml"),
        r_js="results/module3/m3_repo_m2_movics_paths_status.json",
        r_f="results/module3/m3_repo_m2_movics_paths_status.flag",
        b_js="results/module3/m2_movics_paths_status.json",
        b_f="results/module3/m2_movics_paths_status.flag",
        b_stub_js="results/module3/m2_movics_integration_stub.json",
        b_stub_f="results/module3/m2_movics_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_m2_movics_integration_stub.json",
        out_f="results/module3/m3_repo_m2_movics_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_movics_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_m2_3_immune_tme_mirror_paths_status:
    """Outline M2: M3 manifest slice — m2_3_immune_tme_mirror quartet presence under results/module3."""
    input:
        m3r2itm_cfg=str(_ROOT / "config" / "m3_repo_m2_3_immune_tme_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_m2_3_immune_tme_mirror_paths_status.json",
        flag="results/module3/m3_repo_m2_3_immune_tme_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_3_immune_tme_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_m2_3_immune_tme_mirror_integration_stub:
    """Outline M2: immune/TME mirror repo manifest slice (echoes immune/TME + MOVICS stubs)."""
    input:
        m3r2itm_cfg=str(_ROOT / "config" / "m3_repo_m2_3_immune_tme_mirror_outline_inputs.yaml"),
        r_js="results/module3/m3_repo_m2_3_immune_tme_mirror_paths_status.json",
        r_f="results/module3/m3_repo_m2_3_immune_tme_mirror_paths_status.flag",
        b_js="results/module3/m2_3_immune_tme_mirror_paths_status.json",
        b_f="results/module3/m2_3_immune_tme_mirror_paths_status.flag",
        b_stub_js="results/module3/m2_3_immune_tme_mirror_integration_stub.json",
        b_stub_f="results/module3/m2_3_immune_tme_mirror_integration_stub.flag",
        mv_stub_js="results/module3/m2_movics_integration_stub.json",
        mv_stub_f="results/module3/m2_movics_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_m2_3_immune_tme_mirror_integration_stub.json",
        out_f="results/module3/m3_repo_m2_3_immune_tme_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_3_immune_tme_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_m2_2_variant_annotation_paths_status:
    """Outline M2: M3 manifest slice — m2_2_variant_annotation quartet presence under results/module3."""
    input:
        m3r2va_cfg=str(_ROOT / "config" / "m3_repo_m2_2_variant_annotation_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_m2_2_variant_annotation_paths_status.json",
        flag="results/module3/m3_repo_m2_2_variant_annotation_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_2_variant_annotation_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_m2_2_variant_annotation_integration_stub:
    """Outline M2: variant annotation repo manifest slice (echoes variant + maf_annotation stubs)."""
    input:
        m3r2va_cfg=str(_ROOT / "config" / "m3_repo_m2_2_variant_annotation_outline_inputs.yaml"),
        r_js="results/module3/m3_repo_m2_2_variant_annotation_paths_status.json",
        r_f="results/module3/m3_repo_m2_2_variant_annotation_paths_status.flag",
        b_js="results/module3/m2_2_variant_annotation_paths_status.json",
        b_f="results/module3/m2_2_variant_annotation_paths_status.flag",
        b_stub_js="results/module3/m2_2_variant_annotation_integration_stub.json",
        b_stub_f="results/module3/m2_2_variant_annotation_integration_stub.flag",
        maf_stub_js="results/module3/maf_annotation_integration_stub.json",
        maf_stub_f="results/module3/maf_annotation_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_m2_2_variant_annotation_integration_stub.json",
        out_f="results/module3/m3_repo_m2_2_variant_annotation_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_2_variant_annotation_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_m2_2_depmap_mirror_paths_status:
    """Outline M2: M3 manifest slice — m2_2_depmap_mirror quartet presence under results/module3."""
    input:
        m3r2dm_cfg=str(_ROOT / "config" / "m3_repo_m2_2_depmap_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_m2_2_depmap_mirror_paths_status.json",
        flag="results/module3/m3_repo_m2_2_depmap_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_2_depmap_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_m2_2_depmap_mirror_integration_stub:
    """Outline M2: DepMap mirror repo manifest slice."""
    input:
        m3r2dm_cfg=str(_ROOT / "config" / "m3_repo_m2_2_depmap_mirror_outline_inputs.yaml"),
        r_js="results/module3/m3_repo_m2_2_depmap_mirror_paths_status.json",
        r_f="results/module3/m3_repo_m2_2_depmap_mirror_paths_status.flag",
        b_js="results/module3/m2_2_depmap_mirror_paths_status.json",
        b_f="results/module3/m2_2_depmap_mirror_paths_status.flag",
        b_stub_js="results/module3/m2_2_depmap_mirror_integration_stub.json",
        b_stub_f="results/module3/m2_2_depmap_mirror_integration_stub.flag",
        maf_stub_js="results/module3/maf_annotation_integration_stub.json",
        maf_stub_f="results/module3/maf_annotation_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_m2_2_depmap_mirror_integration_stub.json",
        out_f="results/module3/m3_repo_m2_2_depmap_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_2_depmap_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_m2_2_maf_mutsig_mirror_paths_status:
    """Outline M2: M3 manifest slice — m2_2_maf_mutsig_mirror quartet presence under results/module3."""
    input:
        m3r2mm_cfg=str(_ROOT / "config" / "m3_repo_m2_2_maf_mutsig_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_m2_2_maf_mutsig_mirror_paths_status.json",
        flag="results/module3/m3_repo_m2_2_maf_mutsig_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_2_maf_mutsig_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_m2_2_maf_mutsig_mirror_integration_stub:
    """Outline M2: MAF/MutSig mirror repo manifest slice."""
    input:
        m3r2mm_cfg=str(_ROOT / "config" / "m3_repo_m2_2_maf_mutsig_mirror_outline_inputs.yaml"),
        r_js="results/module3/m3_repo_m2_2_maf_mutsig_mirror_paths_status.json",
        r_f="results/module3/m3_repo_m2_2_maf_mutsig_mirror_paths_status.flag",
        b_js="results/module3/m2_2_maf_mutsig_mirror_paths_status.json",
        b_f="results/module3/m2_2_maf_mutsig_mirror_paths_status.flag",
        b_stub_js="results/module3/m2_2_maf_mutsig_mirror_integration_stub.json",
        b_stub_f="results/module3/m2_2_maf_mutsig_mirror_integration_stub.flag",
        maf_stub_js="results/module3/maf_annotation_integration_stub.json",
        maf_stub_f="results/module3/maf_annotation_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_m2_2_maf_mutsig_mirror_integration_stub.json",
        out_f="results/module3/m3_repo_m2_2_maf_mutsig_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_2_maf_mutsig_mirror_integration_stub.py")],
            cwd=str(_ROOT),
        )


rule m3_repo_m2_2_outline_driver_mirror_paths_status:
    """Outline M2: M3 manifest slice — m2_2_outline_driver_mirror quartet presence under results/module3."""
    input:
        m3r2odm_cfg=str(_ROOT / "config" / "m3_repo_m2_2_outline_driver_mirror_outline_inputs.yaml"),
        ds=str(_ROOT / "config" / "data_sources.yaml"),
    output:
        js="results/module3/m3_repo_m2_2_outline_driver_mirror_paths_status.json",
        flag="results/module3/m3_repo_m2_2_outline_driver_mirror_paths_status.flag",
    run:
        env = {**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(DATA_ROOT)}
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "m3_repo_m2_2_outline_driver_mirror_paths_status.py")],
            cwd=str(_ROOT),
            env=env,
        )


rule m3_repo_m2_2_outline_driver_mirror_integration_stub:
    """Outline M2: outline driver mirror repo manifest slice."""
    input:
        m3r2odm_cfg=str(_ROOT / "config" / "m3_repo_m2_2_outline_driver_mirror_outline_inputs.yaml"),
        r_js="results/module3/m3_repo_m2_2_outline_driver_mirror_paths_status.json",
        r_f="results/module3/m3_repo_m2_2_outline_driver_mirror_paths_status.flag",
        b_js="results/module3/m2_2_outline_driver_mirror_paths_status.json",
        b_f="results/module3/m2_2_outline_driver_mirror_paths_status.flag",
        b_stub_js="results/module3/m2_2_outline_driver_mirror_integration_stub.json",
        b_stub_f="results/module3/m2_2_outline_driver_mirror_integration_stub.flag",
        maf_stub_js="results/module3/maf_annotation_integration_stub.json",
        maf_stub_f="results/module3/maf_annotation_integration_stub.flag",
    output:
        out_js="results/module3/m3_repo_m2_2_outline_driver_mirror_integration_stub.json",
        out_f="results/module3/m3_repo_m2_2_outline_driver_mirror_integration_stub.flag",
    run:
        subprocess.check_call(
            [
                sys.executable,
                str(_ROOT / "scripts" / "m3_repo_m2_2_outline_driver_mirror_integration_stub.py"),
            ],
            cwd=str(_ROOT),
        )

rule pipeline_planned_extensions_report:
    """Registry of outline planned capabilities beyond current Snakemake scope (honest status JSON)."""
    input:
        ext=str(_ROOT / "config" / "pipeline_planned_extensions.yaml"),
    output:
        "results/pipeline_planned_extensions_report.json",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "report_pipeline_planned_extensions.py")],
            cwd=str(_ROOT),
        )


rule m4_string_api_network:
    """Optional STRING-DB HTTP API: interaction edges for M21 + recount3 DepMap-consensus STRING lists (requires internet)."""
    input:
        welch_syms="results/module3/dea_welch_string_m21_high_confidence.txt",
        ols_syms="results/module3/dea_ols_string_m21_high_confidence.txt",
        r3_syms="results/module3/dea_recount3_depmap_crispr_consensus_string.txt",
        integ=str(_ROOT / "config" / "module2_integration.yaml"),
    output:
        wn="results/module4/string_api/welch_m21_high_confidence_network.json",
        on="results/module4/string_api/ols_m21_high_confidence_network.json",
        r3="results/module4/string_api/recount3_depmap_crispr_consensus_network.json",
        prov="results/module4/string_api/string_api_fetch_provenance.json",
    run:
        subprocess.check_call(
            [sys.executable, str(_ROOT / "scripts" / "fetch_string_network_api.py")],
            cwd=str(_ROOT),
        )
