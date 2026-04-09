"""Minimal files under a temp GLIOMA_TARGET_DATA_ROOT so Snakemake --dry-run can resolve common edges on CI."""

from __future__ import annotations

import os
from pathlib import Path


def _ci_like_env() -> bool:
    """
    True in automation (GitHub Actions, GitLab, etc.).

    Rewrites stub files even if they already exist so Linux runners never keep broken/empty
    artifacts from a previous step. GitHub sets GITHUB_ACTIONS=true and CI=true.
    """
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        return True
    return os.environ.get("CI", "").lower() in ("true", "1", "yes")

# Inputs for rule toil_gbm_brain_tpm (Snakemake 8+ validates paths during DAG build).
_TOIL_GTEX_REL = (
    ("gtex", "xena_toil", "TcgaTargetGtex_rsem_gene_tpm.gz"),
    ("gtex", "xena_toil", "TcgaTargetGTEX_phenotype.txt.gz"),
)


def touch_toil_gtex_placeholder_inputs(data_root: Path) -> None:
    """Create empty placeholder files (existence-only for dry-run input checks)."""
    root = data_root.resolve()
    force = _ci_like_env()
    for parts in _TOIL_GTEX_REL:
        p = root.joinpath(*parts)
        if p.is_file() and not force:
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"")


def touch_gdc_open_star_manifest_placeholder(data_root: Path) -> None:
    """Minimal manifest JSON so dry-run input checks for tcga_gbm_tpm_matrix pass."""
    root = data_root.resolve()
    p = root / "gdc" / "tcga_gbm_open_star_counts" / "gdc_files_manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.is_file() and not _ci_like_env():
        return
    p.write_text("[]\n", encoding="utf-8")


def touch_hgnc_placeholder(data_root: Path) -> None:
    """Minimal HGNC slice (m2_dea_string_export, m2_verhaak_subtypes, …) — existence-only for dry-run."""
    root = data_root.resolve()
    p = root / "references" / "hgnc_complete_set.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.is_file() and not _ci_like_env():
        return
    p.write_text("symbol\nSTUBGENE\n", encoding="utf-8")


# Relative to repo results/ — DEA + recount3 edges through m2_outline_driver_flags (manifest DAG dry-run).
_PIPELINE_DRY_RUN_REPO_REL_FILES = (
    "module3/dea_gbm_vs_gtex_brain.tsv",
    "module3/dea_gbm_vs_gtex_brain_ols_region_covariate.tsv",
    "module3/dea_gbm_vs_gtex_brain_depmap_crispr.tsv",
    "module3/dea_gbm_vs_gtex_brain_ols_depmap_crispr.tsv",
    "module3/dea_gbm_vs_gtex_brain_depmap_somatic.tsv",
    "module3/dea_gbm_vs_gtex_brain_ols_depmap_somatic.tsv",
    "module3/dea_gbm_vs_gtex_brain_tcga_maf.tsv",
    "module3/dea_gbm_vs_gtex_brain_ols_tcga_maf.tsv",
    "module3/dea_gbm_vs_gtex_brain_mutsig.tsv",
    "module3/dea_gbm_vs_gtex_brain_ols_mutsig.tsv",
    "module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_results.tsv",
    "module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_qlf_results.tsv",
    "module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_depmap_crispr.tsv",
    "module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_depmap_crispr.tsv",
    "module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_depmap_somatic.tsv",
    "module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_depmap_somatic.tsv",
    "module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_tcga_maf.tsv",
    "module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_tcga_maf.tsv",
    "module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_mutsig.tsv",
    "module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_mutsig.tsv",
    "module3/stratified_dea_integration.flag",
    "module3/toil_gbm_vs_brain_tpm.parquet",
    "module3/toil_gbm_vs_brain_samples.tsv",
    # m4_recount3_depmap_string_consensus → m4_wgcna_hub_expr_subset (config/module2_integration.yaml wgcna_hub_subset.symbol_list_paths)
    "module3/dea_recount3_pydeseq2_string_depmap_crispr_median_lte_minus0p5.txt",
    "module3/dea_recount3_edger_string_depmap_crispr_median_lte_minus0p5.txt",
    "module3/dea_recount3_depmap_crispr_consensus_string.txt",
    "module3/dea_welch_string_m21_high_confidence.txt",
    "module3/dea_ols_string_m21_high_confidence.txt",
    # m7_gts_candidate_stub: global + stratified STRING/DepMap lists (no upstream Snakefile producers on default DAG)
    "module3/dea_welch_string_m21_depmap_crispr_median_lte_minus0p5.txt",
    "module3/dea_ols_string_m21_depmap_crispr_median_lte_minus0p5.txt",
    "module4/stratified_string/welch_integrated_m21_depmap/dea_welch_subtype_Classical_string_m21_depmap_crispr_median_lte_minus0p5.txt",
    "module4/stratified_string/welch_integrated_m21_depmap/dea_welch_subtype_Mesenchymal_string_m21_depmap_crispr_median_lte_minus0p5.txt",
    "module4/stratified_string/welch_integrated_m21_depmap/dea_welch_subtype_Neural_string_m21_depmap_crispr_median_lte_minus0p5.txt",
    "module4/stratified_string/welch_integrated_m21_depmap/dea_welch_subtype_Proneural_string_m21_depmap_crispr_median_lte_minus0p5.txt",
    "module4/stratified_string/ols_integrated_m21_depmap/dea_ols_subtype_Classical_string_m21_depmap_crispr_median_lte_minus0p5.txt",
    "module4/stratified_string/ols_integrated_m21_depmap/dea_ols_subtype_Mesenchymal_string_m21_depmap_crispr_median_lte_minus0p5.txt",
    "module4/stratified_string/ols_integrated_m21_depmap/dea_ols_subtype_Neural_string_m21_depmap_crispr_median_lte_minus0p5.txt",
    "module4/stratified_string/ols_integrated_m21_depmap/dea_ols_subtype_Proneural_string_m21_depmap_crispr_median_lte_minus0p5.txt",
)


def assert_pipeline_dry_run_repo_placeholders(repo_root: Path) -> None:
    """
    After touch_pipeline_dry_run_repo_placeholders: verify every stub path exists (non-empty file).

    Fails fast with a clear pytest error if stubs were skipped or the working tree differs from CI.
    """
    results = (repo_root / "results").resolve()
    missing: list[str] = []
    empty: list[str] = []
    for rel in _PIPELINE_DRY_RUN_REPO_REL_FILES:
        p = results.joinpath(*rel.split("/"))
        if not p.is_file():
            missing.append(rel)
            continue
        if p.stat().st_size <= 0:
            empty.append(rel)
    assert not missing, f"missing pipeline dry-run stub files under {results}: {missing}"
    assert not empty, f"empty pipeline dry-run stub files under {results}: {empty}"


def touch_pipeline_dry_run_repo_placeholders(repo_root: Path) -> list[Path]:
    """
    Create placeholder files under results/ for Snakemake --dry-run to the export manifests.

    Locally: only create files that are missing (skip if you already have real outputs).
    On GitHub Actions (GITHUB_ACTIONS=true): always (re)write stubs so a stale or empty checkout
    cannot leave Snakemake thinking inputs are missing.

    Returns paths written in this call; callers should unlink them in teardown.
    """
    results = (repo_root / "results").resolve()
    written: list[Path] = []
    tsv_stub = "gene\tlog2FoldChange\tpvalue\tpadj\nx\t0.0\t0.5\t0.9\n"
    txt_gene_stub = "STUBGENE\n"
    force = _ci_like_env()
    for rel in _PIPELINE_DRY_RUN_REPO_REL_FILES:
        p = results.joinpath(*rel.split("/"))
        if p.is_dir():
            raise NotADirectoryError(f"expected a file for dry-run stub, got directory: {p}")
        if p.is_file() and not force:
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix == ".parquet":
            p.write_bytes(b"\0")  # non-empty; some stacks treat 0-byte oddly
        elif p.suffix == ".flag":
            p.write_text("ci_stub\n", encoding="utf-8")
        elif p.suffix == ".txt":
            p.write_text(txt_gene_stub, encoding="utf-8")
        else:
            p.write_text(tsv_stub, encoding="utf-8")
        written.append(p)
    return written


def prepare_data_root_for_pipeline_dry_run(data_root: Path) -> None:
    """TOIL + GDC + HGNC under DATA_ROOT — common edges for manifest/index dry-runs."""
    touch_toil_gtex_placeholder_inputs(data_root)
    touch_gdc_open_star_manifest_placeholder(data_root)
    touch_hgnc_placeholder(data_root)


def touch_data_layout_ok_flag(repo_root: Path) -> None:
    """Stub results/data_layout_ok.flag (input to tcga_gbm_tpm_matrix) when verify_data_layout did not run."""
    p = repo_root / "results" / "data_layout_ok.flag"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("ci_dry_run_stub\n", encoding="utf-8")
