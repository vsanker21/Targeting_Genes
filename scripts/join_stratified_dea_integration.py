#!/usr/bin/env python3
"""
Apply the same Module 2 integration layers used on global DEA (DepMap CRISPR, DepMap somatic,
TCGA MAF summary, MutSig columns) to stratified Welch and stratified OLS tables.

Reads precomputed summaries where possible (e.g. depmap_gbm_somatic_by_gene.tsv) to avoid
re-scanning large DepMap CSVs. MutSig lookups come from merged global DEA TSVs
(dea_*_mutsig.tsv) so run m2_mutsig_join_dea first when using MutSig.

See config/module2_integration.yaml — stratified_dea_integration
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from depmap_shared import detect_gbm_models, latest_depmap_dir
from join_dea_depmap_crispr import (
    load_ensg_to_entrez,
    read_crispr_gbm_gene_aggregates,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def load_integration_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module2_integration.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def ensg_base(gene_id: str) -> str:
    s = str(gene_id).strip()
    if "." in s and s.startswith("ENSG"):
        return s.split(".", 1)[0]
    return s


def load_tcga_maf_summary(rr: Path, rel_path: str) -> pd.DataFrame:
    p = rr / rel_path
    if not p.is_file():
        return pd.DataFrame()
    return pd.read_csv(p, sep="\t", low_memory=False)


def load_somatic_by_gene(rr: Path, rel_path: str) -> tuple[pd.DataFrame, int]:
    p = rr / rel_path
    if not p.is_file():
        return pd.DataFrame(), 0
    df = pd.read_csv(p, sep="\t", low_memory=False)
    if "gene_id" not in df.columns:
        return pd.DataFrame(), 0
    df = df.assign(_ensg=df["gene_id"].map(ensg_base))
    df = df.dropna(subset=["_ensg"]).groupby("_ensg", as_index=True).agg(
        n_gbm_models_mutated=("n_gbm_models_mutated", "max"),
        n_variant_calls=("n_variant_calls", "sum"),
    )
    prov = rr / "results" / "module3" / "depmap_somatic_join_provenance.json"
    n_lines = 0
    if prov.is_file():
        try:
            meta = json.loads(prov.read_text(encoding="utf-8"))
            n_lines = int(meta.get("n_gbm_models", 0))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return df, n_lines


def load_mutsig_lookup(path: Path) -> pd.DataFrame:
    """Index: Ensembl (no version); columns mutsig_q, mutsig_p, mutsig_rank."""
    if not path.is_file():
        return pd.DataFrame()
    try:
        hdr = pd.read_csv(path, sep="\t", nrows=0)
    except Exception:
        return pd.DataFrame()
    cols = [c for c in ("gene_id", "mutsig_q", "mutsig_p", "mutsig_rank") if c in hdr.columns]
    if "gene_id" not in cols:
        return pd.DataFrame()
    d = pd.read_csv(path, sep="\t", usecols=cols, low_memory=False)
    d["_e"] = d["gene_id"].map(ensg_base)
    num_cols = [c for c in ("mutsig_q", "mutsig_p", "mutsig_rank") if c in d.columns]
    if not num_cols:
        return pd.DataFrame()
    return d.set_index("_e")[num_cols]


def apply_crispr(dea: pd.DataFrame, crispr_agg: pd.DataFrame, n_models: int) -> pd.DataFrame:
    out = dea.copy()
    e = out["gene_id"].map(ensg_base)
    if crispr_agg.empty or n_models <= 0:
        out["depmap_crispr_median_gbm"] = np.nan
        out["depmap_crispr_min_gbm"] = np.nan
        out["depmap_crispr_max_gbm"] = np.nan
    else:
        hit = crispr_agg.reindex(e)
        out["depmap_crispr_median_gbm"] = hit["median"].to_numpy()
        out["depmap_crispr_min_gbm"] = hit["min"].to_numpy()
        out["depmap_crispr_max_gbm"] = hit["max"].to_numpy()
    out["depmap_n_gbm_lines"] = int(n_models)
    return out


def apply_somatic(dea: pd.DataFrame, by_gene: pd.DataFrame, n_lines: int) -> pd.DataFrame:
    out = dea.copy()
    e = out["gene_id"].map(ensg_base)
    if by_gene.empty:
        out["depmap_somatic_n_gbm_models"] = 0
        out["depmap_somatic_n_variant_calls"] = 0
    else:
        hit = by_gene.reindex(e)
        out["depmap_somatic_n_gbm_models"] = hit["n_gbm_models_mutated"].fillna(0).astype(int).to_numpy()
        out["depmap_somatic_n_variant_calls"] = hit["n_variant_calls"].fillna(0).astype(int).to_numpy()
    out["depmap_somatic_total_gbm_lines"] = int(n_lines)
    return out


def apply_maf(dea: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    out = dea.copy()
    e = out["gene_id"].map(ensg_base)
    if summary.empty or "gene_id" not in summary.columns:
        out["tcga_maf_n_samples_mutated"] = 0
        out["tcga_maf_n_mutation_records"] = 0
    else:
        sm = summary.assign(_e=summary["gene_id"].map(ensg_base)).dropna(subset=["_e"])
        sm = sm.groupby("_e", as_index=True).agg(
            n_tcga_samples_mutated=("n_tcga_samples_mutated", "max"),
            n_mutation_records=("n_mutation_records", "sum"),
        )
        hit = sm.reindex(e)
        out["tcga_maf_n_samples_mutated"] = hit["n_tcga_samples_mutated"].fillna(0).astype(int).to_numpy()
        out["tcga_maf_n_mutation_records"] = hit["n_mutation_records"].fillna(0).astype(int).to_numpy()
    return out


def apply_mutsig(dea: pd.DataFrame, lookup: pd.DataFrame) -> pd.DataFrame:
    out = dea.copy()
    e = out["gene_id"].map(ensg_base)
    if lookup.empty:
        out["mutsig_q"] = np.nan
        out["mutsig_p"] = np.nan
        out["mutsig_rank"] = np.nan
    else:
        hit = lookup.reindex(e)
        for c in ("mutsig_q", "mutsig_p", "mutsig_rank"):
            if c in lookup.columns:
                out[c] = hit[c].to_numpy()
            else:
                out[c] = np.nan
    return out


def collect_wanted_genes(rr: Path, globs: list[str]) -> set[str]:
    wanted: set[str] = set()
    for g in globs:
        for p in rr.glob(g):
            if not p.is_file() or p.name.startswith("summary"):
                continue
            try:
                d = pd.read_csv(p, sep="\t", usecols=["gene_id"])
                wanted.update(d["gene_id"].map(ensg_base))
            except (ValueError, KeyError):
                continue
    return wanted


def build_crispr_aggregate(
    root: Path,
    rr: Path,
    dm: dict[str, Any],
    wanted: set[str],
) -> tuple[pd.DataFrame, int]:
    if not wanted:
        return pd.DataFrame(), 0
    try:
        rel = latest_depmap_dir(root)
    except FileNotFoundError:
        return pd.DataFrame(), 0
    crispr_path = rel / dm.get("crispr_gene_effect_csv", "CRISPRGeneEffect.csv")
    model_path = rel / dm.get("model_csv", "Model.csv")
    hrel = dm.get("hgnc_tsv", "{data_root}/references/hgnc_complete_set.txt")
    hgnc_path = Path(hrel.replace("{data_root}", str(root)).replace("/", os.sep))
    if not crispr_path.is_file() or not model_path.is_file() or not hgnc_path.is_file():
        return pd.DataFrame(), 0
    primary = str(dm.get("oncotree_primary_contains", "Glioblastoma"))
    lineage_fb = dm.get("oncotree_lineage_fallback")
    lineage_fb = str(lineage_fb) if lineage_fb else None
    gbm_models = detect_gbm_models(model_path, primary, lineage_fb)
    if not gbm_models:
        return pd.DataFrame(), 0
    try:
        ensg_to_ez = load_ensg_to_entrez(hgnc_path, wanted)
        agg, n_lines = read_crispr_gbm_gene_aggregates(crispr_path, gbm_models, ensg_to_ez)
        return agg, n_lines
    except Exception:
        return pd.DataFrame(), 0


def process_glob(
    rr: Path,
    pattern: str,
    out_dir: Path,
    crispr_agg: pd.DataFrame,
    crispr_n: int,
    somatic_idx: pd.DataFrame,
    somatic_n: int,
    maf_sum: pd.DataFrame,
    mutsig_lookup: pd.DataFrame,
) -> int:
    n_out = 0
    out_dir.mkdir(parents=True, exist_ok=True)
    for inp in sorted(rr.glob(pattern)):
        if not inp.is_file() or inp.name.startswith("summary"):
            continue
        dea = pd.read_csv(inp, sep="\t", low_memory=False)
        if "gene_id" not in dea.columns:
            continue
        x = apply_crispr(dea, crispr_agg, crispr_n)
        x = apply_somatic(x, somatic_idx, somatic_n)
        x = apply_maf(x, maf_sum)
        x = apply_mutsig(x, mutsig_lookup)
        outp = out_dir / inp.name
        x.to_csv(outp, sep="\t", index=False)
        print(f"Wrote {outp}")
        n_out += 1
    return n_out


def main() -> int:
    rr = repo_root()
    root = data_root()
    cfg = load_integration_cfg()
    block = cfg.get("stratified_dea_integration") or {}
    if not block.get("enabled", True):
        print("stratified_dea_integration disabled in YAML")
        return 0

    welch_glob = str(block.get("welch_glob", "results/module3/stratified_dea/dea_welch_subtype_*.tsv"))
    ols_glob = str(block.get("ols_glob", "results/module3/stratified_ols_dea/dea_ols_subtype_*.tsv"))
    welch_out = rr / block.get("welch_output_dir", "results/module3/stratified_dea/integrated")
    ols_out = rr / block.get("ols_output_dir", "results/module3/stratified_ols_dea/integrated")

    dm = cfg.get("depmap_crispr_join") or {}
    sm = cfg.get("depmap_somatic_join") or {}

    wanted = collect_wanted_genes(rr, [welch_glob, ols_glob])
    crispr_agg, crispr_n = build_crispr_aggregate(root, rr, dm, wanted)

    somatic_idx, somatic_n = load_somatic_by_gene(rr, str(sm.get("gene_summary_tsv", "results/module3/depmap_gbm_somatic_by_gene.tsv")))

    maf_cfg_path = rr / "config" / "tcga_mutation_layer.yaml"
    maf_sum = pd.DataFrame()
    if maf_cfg_path.is_file():
        mcfg = yaml.safe_load(maf_cfg_path.read_text(encoding="utf-8"))
        maf_sum = load_tcga_maf_summary(rr, str(mcfg.get("gene_summary_tsv", "results/module3/tcga_gbm_maf_gene_summary.tsv")))

    mut_welch = rr / block.get("mutsig_lookup_welch_tsv", "results/module3/dea_gbm_vs_gtex_brain_mutsig.tsv")
    mut_ols = rr / block.get("mutsig_lookup_ols_tsv", "results/module3/dea_gbm_vs_gtex_brain_ols_mutsig.tsv")

    n_w = process_glob(rr, welch_glob, welch_out, crispr_agg, crispr_n, somatic_idx, somatic_n, maf_sum, load_mutsig_lookup(mut_welch))
    n_o = process_glob(rr, ols_glob, ols_out, crispr_agg, crispr_n, somatic_idx, somatic_n, maf_sum, load_mutsig_lookup(mut_ols))

    flag = rr / block.get("done_flag", "results/module3/stratified_dea_integration.flag")
    flag.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "n_stratified_welch_integrated": n_w,
        "n_stratified_ols_integrated": n_o,
        "crispr_genes_in_aggregate": int(len(crispr_agg)),
        "crispr_n_gbm_lines": crispr_n,
        "somatic_genes_in_summary": int(len(somatic_idx)),
    }
    flag.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    prov = rr / "results" / "module3" / "stratified_dea_integration_provenance.json"
    prov.write_text(
        json.dumps(
            {
                "welch_glob": welch_glob,
                "ols_glob": ols_glob,
                "welch_output_dir": str(welch_out),
                "ols_output_dir": str(ols_out),
                "caveat": "DepMap/MAF/MutSig layers are gene-level annotations; they do not imply tumor-specific driver status without cohort-appropriate statistics (outline Module 2 section 2.2).",
                **summary,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {flag} and {prov}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
