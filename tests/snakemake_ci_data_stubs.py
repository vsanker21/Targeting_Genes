"""Minimal files under a temp GLIOMA_TARGET_DATA_ROOT so Snakemake --dry-run can resolve common edges on CI."""

from __future__ import annotations

from pathlib import Path

# Inputs for rule toil_gbm_brain_tpm (Snakemake 8+ validates paths during DAG build).
_TOIL_GTEX_REL = (
    ("gtex", "xena_toil", "TcgaTargetGtex_rsem_gene_tpm.gz"),
    ("gtex", "xena_toil", "TcgaTargetGTEX_phenotype.txt.gz"),
)


def touch_toil_gtex_placeholder_inputs(data_root: Path) -> None:
    """Create empty placeholder files (existence-only for dry-run input checks)."""
    for parts in _TOIL_GTEX_REL:
        p = data_root.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"")


def touch_gdc_open_star_manifest_placeholder(data_root: Path) -> None:
    """Minimal manifest JSON so dry-run input checks for tcga_gbm_tpm_matrix pass."""
    p = data_root / "gdc" / "tcga_gbm_open_star_counts" / "gdc_files_manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("[]\n", encoding="utf-8")


def prepare_data_root_for_pipeline_dry_run(data_root: Path) -> None:
    """TOIL placeholders + GDC manifest — common DATA_ROOT edges for manifest/index dry-runs."""
    touch_toil_gtex_placeholder_inputs(data_root)
    touch_gdc_open_star_manifest_placeholder(data_root)


def touch_data_layout_ok_flag(repo_root: Path) -> None:
    """Stub results/data_layout_ok.flag (input to tcga_gbm_tpm_matrix) when verify_data_layout did not run."""
    p = repo_root / "results" / "data_layout_ok.flag"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("ci_dry_run_stub\n", encoding="utf-8")
