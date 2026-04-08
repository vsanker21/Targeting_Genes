"""M2.1 / M2.2 / M2.3 / M3 scoped specs and scripts (no large downloads in default unit tests)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[1]


def test_m2_1_harmonized_count_dea_spec_matches_snakefile() -> None:
    spec = yaml.safe_load((_ROOT / "config" / "m2_1_harmonized_count_dea.yaml").read_text(encoding="utf-8"))
    sf = (_ROOT / "Snakefile").read_text(encoding="utf-8")
    assert "gdc_star_same_pipeline" in spec["strategies"]
    assert "recount3_star_universe_g029" in spec["strategies"]
    for _sk, block in spec["strategies"].items():
        for contrast in block["contrasts"]:
            rules = contrast["snakemake_rules"]
            for _role, rule_name in rules.items():
                assert f"rule {rule_name}:" in sf, f"missing rule {rule_name}"


def test_m2_movics_data_fetch_yaml_and_snakefile_rule() -> None:
    p = _ROOT / "config" / "m2_movics_data_fetch.yaml"
    assert p.is_file()
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert "depmap_gbm_mae" in doc
    assert doc["depmap_gbm_mae"].get("mutation_require_variable") is True
    assert doc["depmap_gbm_mae"].get("prioritize_outline_drivers_in_gene_universe") is True
    sf = (_ROOT / "Snakefile").read_text(encoding="utf-8")
    assert "rule fetch_movics_staging_data:" in sf
    assert "rule m2_movics_intnmf_depmap_mae:" in sf


def test_open_source_data_extensions_yaml_parses() -> None:
    p = _ROOT / "config" / "open_source_data_extensions.yaml"
    assert p.is_file()
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert "downloads" in doc
    ids = {d["id"] for d in doc["downloads"] if isinstance(d, dict) and d.get("id")}
    assert "msigdb_hallmark_hs_symbols" in ids
    by_id = {d["id"]: d for d in doc["downloads"] if isinstance(d, dict) and d.get("id")}
    assert by_id["ctd_chem_gene_ixns"].get("enabled") is True
    geo = doc.get("geo_series") or {}
    assert geo.get("enabled") is True
    assert any(str(x).startswith("GSE") for x in (geo.get("gse_ids") or []))
    assert "with-open-extensions" in (_ROOT / "scripts" / "download_all_required.py").read_text(encoding="utf-8")


def test_download_open_source_extensions_dry_run() -> None:
    r = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "download_open_source_extensions.py"), "--dry-run"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr


def test_high_value_public_datasets_yaml_parses() -> None:
    p = _ROOT / "config" / "high_value_public_datasets.yaml"
    assert p.is_file()
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert doc.get("gdsc_fitted_dose_response", {}).get("enabled") is True
    assert doc.get("gdc_tcga_gbm_methylation_beta", {}).get("enabled") is True
    dar = (_ROOT / "scripts" / "download_all_required.py").read_text(encoding="utf-8")
    assert "with-high-value-datasets" in dar


def test_download_high_value_public_datasets_dry_run() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "download_high_value_public_datasets.py"),
            "--dry-run",
            "--skip-gdc-methylation",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr


def test_supplementary_reference_resources_yaml_parses() -> None:
    p = _ROOT / "config" / "supplementary_reference_resources.yaml"
    assert p.is_file()
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert (doc.get("expression_atlas_gene_baselines") or {}).get("enabled") is True
    assert "pathwaycommons_all_hgnc_gmt" in (doc.get("pathways") or {})
    dar = (_ROOT / "scripts" / "download_all_required.py").read_text(encoding="utf-8")
    assert "with-supplementary-reference-resources" in dar
    assert "skip-supplementary-archs4" in dar
    assert "force-supplementary-archs4" in dar


def test_download_supplementary_reference_resources_dry_run() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "download_supplementary_reference_resources.py"),
            "--dry-run",
            "--skip-archs4-h5",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr


def test_download_supplementary_archs4_skip_and_force_mutually_exclusive() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "download_supplementary_reference_resources.py"),
            "--dry-run",
            "--skip-archs4-h5",
            "--force-archs4-h5",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1, r.stderr


def test_decompress_pathwaycommons_gmt_roundtrip(tmp_path: Path) -> None:
    raw = tmp_path / "tiny.gmt"
    raw.write_text("PATHWAY\turl\ta\tb\n", encoding="utf-8")
    gz = tmp_path / "tiny.gmt.gz"
    import gzip

    with gzip.open(gz, "wt", encoding="utf-8", newline="") as f:
        f.write(raw.read_text(encoding="utf-8"))
    out = tmp_path / "out.gmt"
    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "decompress_pathwaycommons_gmt.py"),
            "--gz",
            str(gz),
            "--out",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert out.read_text(encoding="utf-8") == raw.read_text(encoding="utf-8")


def test_supplementary_reference_resources_paths_status_runs(tmp_path: Path) -> None:
    empty = tmp_path / "data"
    empty.mkdir()
    r = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "supplementary_reference_resources_paths_status.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "GLIOMA_TARGET_DATA_ROOT": str(empty)},
    )
    assert r.returncode == 0, r.stderr
    out = _ROOT / "results" / "module3" / "supplementary_reference_resources_paths_status.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("artifact_kind") == "supplementary_reference_resources_paths_status"
    assert doc.get("n_checks") == 10


def test_join_dea_archs4_symbol_stats_gene_axis_columns_and_rows(tmp_path: Path) -> None:
    """ARCHS4 join: samples×genes vs genes×samples alignment matches archs4_outline_driver_expression_context."""
    h5py = pytest.importorskip("h5py")
    import numpy as np

    jp = _ROOT / "scripts" / "join_dea_archs4_expression.py"
    spec = importlib.util.spec_from_file_location("join_dea_archs4_expression", jp)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    p_col = tmp_path / "archs4_samples_x_genes.h5"
    with h5py.File(p_col, "w") as f:
        f.create_dataset("meta/genes", data=np.array([b"AAA", b"BBB"], dtype="S3"))
        f.create_dataset(
            "data/expression",
            data=np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float32),
        )
    df_c, m_c = mod._symbol_stats_from_h5(p_col, ["AAA", "BBB"])
    assert m_c.get("gene_axis") == "columns"
    assert df_c.loc["AAA", "mean_raw"] == pytest.approx(3.0)
    assert df_c.loc["BBB", "mean_raw"] == pytest.approx(4.0)

    p_row = tmp_path / "archs4_genes_x_samples.h5"
    with h5py.File(p_row, "w") as f:
        f.create_dataset("meta/genes", data=np.array([b"AAA", b"BBB"], dtype="S3"))
        f.create_dataset(
            "data/expression",
            data=np.array([[1.0, 3.0, 5.0], [2.0, 4.0, 6.0]], dtype=np.float32),
        )
    df_r, m_r = mod._symbol_stats_from_h5(p_row, ["AAA"])
    assert m_r.get("gene_axis") == "rows"
    assert df_r.loc["AAA", "mean_raw"] == pytest.approx(3.0)


def test_rscript_resolve_returns_path_when_r_available() -> None:
    rs = _ROOT / "scripts" / "rscript_resolve.py"
    spec = importlib.util.spec_from_file_location("rscript_resolve", rs)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        exe = mod.resolve_rscript(_ROOT)
    except FileNotFoundError:
        pytest.skip("Rscript not configured (PATH, R_HOME, registry, or config/rscript)")
    assert isinstance(exe, str) and len(exe) > 0
    assert "Rscript" in exe or exe.endswith("Rscript") or exe.endswith("Rscript.exe")


def test_drugcentral_postgres_load_status_skips_without_env() -> None:
    env = {k: v for k, v in os.environ.items() if k != "GLIOMA_TARGET_DRUGCENTRAL_LOAD"}
    env.pop("GLIOMA_TARGET_DRUGCENTRAL_LOAD", None)
    r = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "drugcentral_postgres_load_status.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 0, r.stderr
    out = _ROOT / "results" / "module4" / "drugcentral_postgres_load_status.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("status") == "skipped"


def test_sync_wikipathways_gmt_url_parses_single_quoted_index_html() -> None:
    p = _ROOT / "scripts" / "sync_wikipathways_gmt_url.py"
    spec = importlib.util.spec_from_file_location("sync_wikipathways_gmt_url", p)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    html = (
        "<tr><td><a href='./wikipathways-20260310-gmt-Homo_sapiens.gmt'>gmt</a></td></tr>"
        '<tr><td><a href="wikipathways-20250101-gmt-Homo_sapiens.gmt">old</a></td></tr>'
    )
    url, fn = mod._latest_gmt_url(html)
    assert fn == "wikipathways-20260310-gmt-Homo_sapiens.gmt"
    assert url.endswith(fn)


def test_fetch_clue_api_subset_exits_1_without_key() -> None:
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper() not in ("CLUE_API_KEY", "CLUE_API_TOKEN_FILE", "USER_KEY")
    }
    for k in ("CLUE_API_KEY", "CLUE_API_TOKEN_FILE", "user_key"):
        env.pop(k, None)
    r = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "fetch_clue_api_subset.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    assert r.returncode == 1, r.stdout
    assert "CLUE" in (r.stderr + r.stdout)


def test_write_min_movics_mae_fixtures_creates_gz_trio(tmp_path: Path) -> None:
    dr = tmp_path / "synth_data"
    r = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "write_min_movics_mae_fixtures.py"), str(dr)],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    mae = dr / "omics" / "multi_omics_mae"
    for name in (
        "depmap_gbm_expression_logtpm.tsv.gz",
        "depmap_gbm_cnv_log2.tsv.gz",
        "depmap_gbm_mutation_binary.tsv.gz",
    ):
        assert (mae / name).is_file()
    model = dr / "depmap" / "000_synthetic_mae_fixture" / "Model.csv"
    assert model.is_file()
    assert (model.parent / "CRISPRGeneEffect.csv").is_file()


def test_m2_movics_depmap_mae_run_yaml_parses() -> None:
    p = _ROOT / "config" / "m2_movics_depmap_mae_run.yaml"
    assert p.is_file()
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert "movics_intnmf_depmap_mae" in doc
    blk = doc["movics_intnmf_depmap_mae"]
    assert blk.get("max_genes", 0) >= 50
    assert "m2_movics_intnmf_depmap_mae" in blk.get("output_clusters_tsv", "")


def test_m2_3_movics_vs_consensus_report_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config").mkdir()
    shutil_src = _ROOT / "config"
    for name in ("m2_movics_inputs.yaml", "m2_3_consensus_clustering.yaml", "m2_movics_data_fetch.yaml"):
        (tmp_path / "config" / name).write_text((shutil_src / name).read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    import shutil

    shutil.copy(_ROOT / "scripts" / "m2_3_movics_vs_consensus_report.py", tmp_path / "scripts" / "m2_3_movics_vs_consensus_report.py")
    r = subprocess.run([sys.executable, "scripts/m2_3_movics_vs_consensus_report.py"], cwd=str(tmp_path), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = tmp_path / "results/module3/m2_3_movics_vs_consensus_method_contrast.json"
    assert out.is_file()
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert "movics_side" in doc and "simpler_method_side" in doc
    assert doc["movics_side"].get("snakemake_rule") == "m2_movics_intnmf_tcga_gbm"
    pms = doc["movics_side"].get("programmatic_multi_omic_staging") or {}
    assert pms.get("snakemake_rule") == "fetch_movics_staging_data"
    assert "omics/multi_omics_mae" in (pms.get("depmap_mae_under_data_root") or "")
    tvd = doc["movics_side"].get("intnmf_three_view_depmap") or {}
    assert tvd.get("snakemake_rule") == "m2_movics_intnmf_depmap_mae"
    assert tvd.get("characterize_rule") == "m2_movics_depmap_intnmf_characterize"
    assert tvd.get("run_config") == "config/m2_movics_depmap_mae_run.yaml"
    assert tvd.get("tcga_vs_depmap_intnmf_interpretation")
    assert tvd.get("depmap_mutation_gene_curation")


def test_m2_2_clinvar_join_offline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Local ClinVar snippet + toy MAF + HGNC subset; no FTP call."""
    import shutil

    rr = tmp_path / "repo"
    rr.mkdir()
    (rr / "config").mkdir(parents=True)
    # tree: repo/config, repo/scripts
    (rr / "scripts").mkdir(parents=True)
    shutil.copy(_ROOT / "scripts" / "annotate_maf_genes_clinvar.py", rr / "scripts" / "annotate_maf_genes_clinvar.py")
    (rr / "config" / "data_sources.yaml").write_text(
        yaml.dump({"data_root": str(tmp_path / "data")}), encoding="utf-8"
    )
    dr = tmp_path / "data"
    clin = dr / "references/clinvar"
    clin.mkdir(parents=True)
    clin_file = clin / "gene_specific_summary.txt"
    clin_file.write_text(
        "#Overview\n#Symbol\tGeneID\tTotal_submissions\nTP53\t7157\t999\nNOTINGENE\t1\t1\n",
        encoding="utf-8",
    )
    hgnc = dr / "references/hgnc_complete_set.txt"
    hgnc.write_text(
        "symbol\tensembl_gene_id\nTP53\tENSG00000141510\n",
        encoding="utf-8",
    )
    (rr / "config" / "m2_2_clinvar_gene_annotation.yaml").write_text(
        yaml.dump(
            {
                "clinvar": {
                    "tab_delimited_url": "https://example.invalid/do-not-fetch",
                    "cache_relative": "references/clinvar/gene_specific_summary.txt",
                },
                "hgnc_tsv": "{data_root}/references/hgnc_complete_set.txt",
                "maf_gene_summary_tsv": "results/module3/tcga_gbm_maf_gene_summary.tsv",
                "output_tsv": "results/module3/m2_2_clinvar/out.tsv",
                "provenance_json": "results/module3/m2_2_clinvar/prov.json",
            }
        ),
        encoding="utf-8",
    )
    maf_dir = rr / "results/module3"
    maf_dir.mkdir(parents=True)
    pd.DataFrame(
        [{"gene_id": "ENSG00000141510.17", "n_tcga_samples_mutated": "3", "n_mutation_records": "5"}]
    ).to_csv(maf_dir / "tcga_gbm_maf_gene_summary.tsv", sep="\t", index=False)

    monkeypatch.chdir(rr)
    monkeypatch.setenv("GLIOMA_TARGET_DATA_ROOT", str(dr))
    # Point script's repo_root: it uses parents[1] of script → rr/scripts → parent is rr — wrong, script is in rr/scripts so parent is rr. Good.
    r = subprocess.run([sys.executable, str(rr / "scripts" / "annotate_maf_genes_clinvar.py")], cwd=str(rr), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out_tsv = rr / "results/module3/m2_2_clinvar/out.tsv"
    df = pd.read_csv(out_tsv, sep="\t")
    assert "GeneID" in df.columns
    assert df.loc[0, "GeneID"] == 7157 or str(df.loc[0, "GeneID"]) == "7157"


def test_m2_3_consensus_on_toy_parquet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    rr = tmp_path / "repo"
    (rr / "config").mkdir(parents=True)
    (rr / "scripts").mkdir(parents=True)
    shutil.copy(_ROOT / "scripts" / "m2_3_consensus_kmeans_star_primary.py", rr / "scripts" / "m2_3_consensus_kmeans_star_primary.py")
    n_samp = 25
    genes = [f"ENSG{i:011d}.1" for i in range(400)]
    rng = __import__("numpy").random.default_rng(1)
    mat = rng.poisson(5, size=(len(genes), n_samp))
    df = pd.DataFrame(mat, index=genes, columns=[f"SAMPLE_{i}" for i in range(n_samp)])
    counts_path = rr / "results/module2/counts.parquet"
    counts_path.parent.mkdir(parents=True)
    df.to_parquet(counts_path)
    meta_path = rr / "results/module2/meta.tsv"
    pd.DataFrame(
        {
            "column_name": [f"SAMPLE_{i}" for i in range(n_samp)],
            "sample_type": ["Primary Tumor"] * n_samp,
        }
    ).to_csv(meta_path, sep="\t", index=False)
    cfg = yaml.safe_load((_ROOT / "config" / "m2_3_consensus_clustering.yaml").read_text(encoding="utf-8"))
    cfg["consensus_star_primary"]["counts_matrix"] = "results/module2/counts.parquet"
    cfg["consensus_star_primary"]["sample_meta"] = "results/module2/meta.tsv"
    cfg["consensus_star_primary"]["n_kmeans_runs"] = 8
    cfg["consensus_star_primary"]["k_max"] = 4
    cfg["consensus_star_primary"]["output_dir"] = "results/module3/m2_3_consensus_star_primary"
    (rr / "config" / "m2_3_consensus_clustering.yaml").write_text(yaml.dump(cfg), encoding="utf-8")
    monkeypatch.chdir(rr)
    r = subprocess.run([sys.executable, str(rr / "scripts" / "m2_3_consensus_kmeans_star_primary.py")], cwd=str(rr), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    prov = json.loads((rr / "results/module3/m2_3_consensus_star_primary/consensus_provenance.json").read_text(encoding="utf-8"))
    assert prov["status"] == "ok"


@pytest.mark.integration
def test_m3_scanpy_exits_when_no_input_under_data_root(tmp_path: Path) -> None:
    pytest.importorskip("scanpy")
    r = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "m3_scrna_scanpy_qc_cluster.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(_ROOT), "GLIOMA_TARGET_DATA_ROOT": str(tmp_path)},
    )
    assert r.returncode == 3, r.stderr
