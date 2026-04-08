#!/usr/bin/env python3
"""
Outline Module 2 §2.2: summarize DepMap OmicsSomaticMutations for GBM cell lines and join to DEA tables.

Counts distinct GBM models with HIGH/MODERATE VEP-impact calls per gene (Ensembl when available).
MutSig2CV itself is not run — this is a practical mutation-landscape layer from DepMap WES calls.
See config/module2_integration.yaml — depmap_somatic_join
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from depmap_shared import detect_gbm_models, extend_dea_pairs_paths, latest_depmap_dir


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


def load_hgnc_symbol_to_ensg(hgnc_path: Path) -> dict[str, str]:
    df = pd.read_csv(hgnc_path, sep="\t", dtype=str, low_memory=False)
    out: dict[str, str] = {}
    for _, row in df.iterrows():
        sym = str(row.get("symbol", "") or "").strip()
        eid = str(row.get("ensembl_gene_id", "") or "").strip()
        if sym and eid:
            out[sym.upper()] = ensg_base(eid)
    return out


def gene_row_key(
    row: pd.Series,
    sym_to_ensg: dict[str, str],
) -> str | None:
    e = str(row.get("EnsemblGeneID", "") or "").strip()
    if e.startswith("ENSG"):
        return ensg_base(e)
    sym = str(row.get("HugoSymbol", "") or "").strip().upper()
    return sym_to_ensg.get(sym)


def write_na_dea(paths: list[tuple[Path, Path]], reason: str) -> None:
    rr = repo_root()
    for dea_p, out_p in paths:
        if not dea_p.is_file():
            continue
        dea = pd.read_csv(dea_p, sep="\t")
        dea["depmap_somatic_n_gbm_models"] = 0
        dea["depmap_somatic_n_variant_calls"] = 0
        dea["depmap_somatic_total_gbm_lines"] = 0
        out_p.parent.mkdir(parents=True, exist_ok=True)
        dea.to_csv(out_p, sep="\t", index=False)
        print(f"Wrote {out_p} (somatic skipped: {reason})")
    (rr / "results" / "module3" / "depmap_somatic_join_provenance.json").write_text(
        json.dumps({"status": "skipped", "reason": reason}, indent=2),
        encoding="utf-8",
    )


def join_dea(dea_path: Path, out_path: Path, by_gene: pd.DataFrame, n_lines: int) -> None:
    dea = pd.read_csv(dea_path, sep="\t")
    dea["_ensg"] = dea["gene_id"].map(ensg_base)
    hit = by_gene.reindex(dea["_ensg"])
    dea["depmap_somatic_n_gbm_models"] = hit["n_gbm_models_mutated"].fillna(0).astype(int).to_numpy()
    dea["depmap_somatic_n_variant_calls"] = hit["n_variant_calls"].fillna(0).astype(int).to_numpy()
    dea["depmap_somatic_total_gbm_lines"] = n_lines
    dea = dea.drop(columns=["_ensg"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dea.to_csv(out_path, sep="\t", index=False)
    nz = (dea["depmap_somatic_n_gbm_models"] > 0).sum()
    print(f"Wrote {out_path} genes with >=1 mutated GBM line: {nz}")


def main() -> int:
    cfg = load_integration_cfg()
    sm = cfg.get("depmap_somatic_join") or {}
    root = data_root()
    rr = repo_root()
    hgnc_path = Path(
        str(sm.get("hgnc_tsv", "{data_root}/references/hgnc_complete_set.txt"))
        .replace("{data_root}", str(root))
        .replace("/", os.sep)
    )
    paths = extend_dea_pairs_paths(rr, sm)

    try:
        rel = latest_depmap_dir(root)
    except FileNotFoundError as e:
        print(f"WARNING: {e}", file=sys.stderr)
        write_na_dea(paths, str(e))
        return 0

    mut_path = rel / sm.get("omics_somatic_csv", "OmicsSomaticMutations.csv")
    model_path = rel / sm.get("model_csv", "Model.csv")
    if not mut_path.is_file() or not model_path.is_file():
        write_na_dea(paths, "missing OmicsSomaticMutations.csv or Model.csv")
        return 0
    if not hgnc_path.is_file():
        write_na_dea(paths, "missing HGNC")
        return 0

    primary = str(sm.get("oncotree_primary_contains", "Glioblastoma"))
    lineage_fb = sm.get("oncotree_lineage_fallback")
    lineage_fb = str(lineage_fb) if lineage_fb else None
    gbm_models = detect_gbm_models(model_path, primary, lineage_fb)
    if not gbm_models:
        write_na_dea(paths, "no GBM models")
        return 0
    gbm_set = set(gbm_models)

    impacts = sm.get("vep_impacts", ["HIGH", "MODERATE"])
    impacts = set(str(x).upper() for x in impacts)

    sym_to_ensg = load_hgnc_symbol_to_ensg(hgnc_path)
    models_by_gene: dict[str, set[str]] = defaultdict(set)
    calls_by_gene: dict[str, int] = defaultdict(int)

    want_cols = ["ModelID", "HugoSymbol", "EnsemblGeneID", "VepImpact"]
    hdr = pd.read_csv(mut_path, nrows=0)
    usecols = [c for c in want_cols if c in hdr.columns]
    if "ModelID" not in usecols:
        write_na_dea(paths, "OmicsSomaticMutations missing ModelID column")
        return 0

    chunksize = int(sm.get("read_chunksize", 200000))
    for chunk in pd.read_csv(
        mut_path,
        usecols=usecols,
        chunksize=chunksize,
        low_memory=False,
    ):
        chunk = chunk[chunk["ModelID"].astype(str).isin(gbm_set)]
        if chunk.empty:
            continue
        if "VepImpact" in chunk.columns:
            imp = chunk["VepImpact"].astype(str).str.upper()
            chunk = chunk[imp.isin(impacts)]
        if chunk.empty:
            continue
        for _, row in chunk.iterrows():
            gid = gene_row_key(row, sym_to_ensg)
            if not gid:
                continue
            models_by_gene[gid].add(str(row["ModelID"]))
            calls_by_gene[gid] += 1

    rows = [(g, len(models_by_gene[g]), calls_by_gene[g]) for g in sorted(models_by_gene.keys())]
    by_gene = pd.DataFrame(
        rows,
        columns=["gene_id", "n_gbm_models_mutated", "n_variant_calls"],
    ).set_index("gene_id")
    summ_path = rr / sm.get("gene_summary_tsv", "results/module3/depmap_gbm_somatic_by_gene.tsv")
    summ_path.parent.mkdir(parents=True, exist_ok=True)
    by_gene.reset_index().sort_values("n_gbm_models_mutated", ascending=False).to_csv(
        summ_path, sep="\t", index=False
    )
    print(f"Wrote {summ_path} n_genes={len(by_gene)}")

    prov = {
        "status": "ok",
        "depmap_release_dir": str(rel),
        "n_gbm_models": len(gbm_models),
        "vep_impacts": list(impacts),
        "n_genes_with_calls": int(len(by_gene)),
    }
    (rr / "results" / "module3" / "depmap_somatic_join_provenance.json").write_text(
        json.dumps(prov, indent=2),
        encoding="utf-8",
    )

    for dea_p, out_p in paths:
        if not dea_p.is_file():
            print(f"SKIP {dea_p}", file=sys.stderr)
            continue
        join_dea(dea_p, out_p, by_gene, len(gbm_models))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
