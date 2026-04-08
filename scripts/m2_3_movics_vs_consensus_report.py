#!/usr/bin/env python3
"""M2.3: Written contrast — MOVICS (not run) vs in-repo Monti-style consensus (see m2_3_consensus_star_primary)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    rr = repo_root()
    mov = yaml.safe_load((rr / "config" / "m2_movics_inputs.yaml").read_text(encoding="utf-8"))
    cons = yaml.safe_load((rr / "config" / "m2_3_consensus_clustering.yaml").read_text(encoding="utf-8"))
    fetch_cfg_path = rr / "config" / "m2_movics_data_fetch.yaml"
    fetch_block: dict = {}
    if fetch_cfg_path.is_file():
        fetch_block = yaml.safe_load(fetch_cfg_path.read_text(encoding="utf-8")) or {}
    out = rr / cons["method_contrast_report_json"]
    out.parent.mkdir(parents=True, exist_ok=True)

    depmap_mae = fetch_block.get("depmap_gbm_mae") or {}
    out_dir = str(depmap_mae.get("out_dir", "omics/multi_omics_mae"))

    report = {
        "movics_side": {
            "description": "MOVICS (R) multi-omic integrative clustering and subtype discovery.",
            "in_repo_status": (
                "Executable paths: MOVICS::getIntNMF on TCGA TPM + counts (m2_movics_run.yaml) and optional "
                "three-view IntNMF on DepMap-staged omics/multi_omics_mae/*.tsv.gz (m2_movics_depmap_mae_run.yaml)."
            ),
            "snakemake_rule": "m2_movics_intnmf_tcga_gbm",
            "run_config": "config/m2_movics_run.yaml",
            "intnmf_three_view_depmap": {
                "snakemake_rule": "m2_movics_intnmf_depmap_mae",
                "run_config": "config/m2_movics_depmap_mae_run.yaml",
                "matrix_layout_config": "config/m2_movics_data_fetch.yaml",
                "mutation_matrix_filter_config": (
                    "config/m2_movics_data_fetch.yaml depmap_gbm_mae.mutation_require_variable "
                    "(variable binary rows for MOVICS binomial layer)"
                ),
                "characterize_rule": "m2_movics_depmap_intnmf_characterize",
                "characterize_outputs": {
                    "cluster_model_annotations_tsv": (
                        "results/module3/m2_movics_intnmf_depmap_mae/cluster_model_annotations.tsv"
                    ),
                    "cluster_summary_json": "results/module3/m2_movics_intnmf_depmap_mae/cluster_summary.json",
                },
                "outputs": {
                    "clusters_tsv": "results/module3/m2_movics_intnmf_depmap_mae/movics_depmap_mae_clusters.tsv",
                    "provenance_json": "results/module3/m2_movics_intnmf_depmap_mae/movics_depmap_mae_provenance.json",
                },
                "optional_rule_all_env": "GLIOMA_TARGET_INCLUDE_MOVICS_DEPMAP_MAE=1",
                "note": "Requires fetch_movics_staging_data with DepMap CSVs; cell-line ModelIDs, not TCGA.",
                "tcga_vs_depmap_intnmf_interpretation": (
                    "Rules m2_movics_intnmf_tcga_gbm (TCGA primary-tumor GDC STAR) and "
                    "m2_movics_intnmf_depmap_mae (DepMap cell lines) produce separate cluster label spaces. "
                    "Do not merge or compare cluster IDs across cohorts. Any side-by-side figure is illustrative "
                    "or explicitly comparative (e.g. methods schematic), not a claim of shared subtypes."
                ),
                "depmap_mutation_gene_curation": (
                    "Staging uses references/gbm_known_drivers_outline.yaml first in the MAE gene universe "
                    "(config depmap_gbm_mae.prioritize_outline_drivers_in_gene_universe) plus variable-binary "
                    "mutation filtering to support MOVICS binomial view; see depmap_mae_provenance.json."
                ),
            },
            "install": "python scripts/install_r_movics_dependencies.py",
            "optional_rule_all_env": "GLIOMA_TARGET_INCLUDE_MOVICS=1",
            "path_checks_config": "config/m2_movics_inputs.yaml",
            "path_status_json": mov.get("movics_path_checks", {}).get("output_json"),
            "stub_json": mov.get("movics_integration_stub", {}).get("output_json"),
            "programmatic_multi_omic_staging": {
                "fetch_config": "config/m2_movics_data_fetch.yaml",
                "fetch_script": "scripts/fetch_movics_staging_data.py",
                "snakemake_rule": "fetch_movics_staging_data",
                "fetch_report_json": "results/module3/movics_staging_fetch_report.json",
                "depmap_mae_under_data_root": out_dir,
                "cgga_urls_key": "cgga_http",
                "note": (
                    "DepMap-derived expression + CN + mutation matrices land under data_root/"
                    + out_dir.replace("\\", "/")
                    + " after fetch; add CGGA portal URLs to cgga_http for cohorts/cgga_expression/."
                ),
            },
        },
        "simpler_method_side": {
            "name": cons["consensus_star_primary"]["method_name"],
            "description": cons["consensus_star_primary"]["movics_reference_note"],
            "config": "config/m2_3_consensus_clustering.yaml",
            "snakemake_rule": "m2_3_consensus_star_primary",
            "script": "scripts/m2_3_consensus_kmeans_star_primary.py",
            "outputs": {
                "clusters_tsv": f"{cons['consensus_star_primary']['output_dir']}/consensus_sample_clusters.tsv",
                "provenance_json": f"{cons['consensus_star_primary']['output_dir']}/consensus_provenance.json",
            },
        },
        "comparison_summary": (
            "MOVICS is designed for multiple matched omics matrices and model-based consensus; "
            "the simpler method is a transparent baseline—consensus clustering on one harmonized "
            "expression matrix (GDC STAR) for Primary Tumor samples."
        ),
    }
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
