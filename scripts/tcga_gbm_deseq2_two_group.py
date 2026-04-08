#!/usr/bin/env python3
"""
Shared PyDESeq2 runner for TCGA-GBM GDC STAR counts: two-sample-type contrasts from config/deseq2_tcga_gbm.yaml.

Blocks:
  - deseq2_tcga_primary_vs_recurrent (Primary Tumor vs Recurrent Tumor)
  - deseq2_tcga_primary_vs_solid_normal (Primary Tumor vs Solid Tissue Normal; n_normal is tiny)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

try:
    from pydeseq2.dds import DeseqDataSet
    from pydeseq2.ds import DeseqStats
except ImportError as e:
    print(
        "Missing pydeseq2. Install: pip install pydeseq2  (or pip install -r requirements-optional.txt)",
        file=sys.stderr,
    )
    raise SystemExit(1) from e


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_pair(block: dict[str, Any]) -> tuple[str, str, dict[str, str], str]:
    """Return (label_a, label_b, cond_map, analysis_tag)."""
    p_lab = str(block["primary_label"])
    if "normal_label" in block:
        o_lab = str(block["normal_label"])
        cmap = {
            p_lab: str(block["condition_primary"]),
            o_lab: str(block["condition_normal"]),
        }
        return p_lab, o_lab, cmap, "primary_vs_solid_tissue_normal"
    if "recurrent_label" in block:
        r_lab = str(block["recurrent_label"])
        cmap = {
            p_lab: str(block["condition_primary"]),
            r_lab: str(block["condition_recurrent"]),
        }
        return p_lab, r_lab, cmap, "primary_vs_recurrent"
    raise ValueError(
        "YAML block must define either (normal_label, condition_normal) or "
        "(recurrent_label, condition_recurrent) alongside primary_label / condition_primary."
    )


def main(block_key: str) -> int:
    rr = repo_root()
    cfg_path = rr / "config" / "deseq2_tcga_gbm.yaml"
    doc = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    block = doc.get(block_key) or {}
    if not block.get("enabled", True):
        print(f"{block_key} disabled")
        return 0

    lab_a, lab_b, cond_map, tag = _resolve_pair(block)

    counts_path = rr / str(block["counts_matrix"]).replace("/", os.sep)
    meta_path = rr / str(block["sample_meta"]).replace("/", os.sep)
    out_dir = rr / str(block["output_dir"]).replace("/", os.sep)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_tsv = out_dir / str(block.get("output_results", "deseq2_results.tsv"))
    out_prov = out_dir / str(block.get("output_provenance", "deseq2_provenance.json"))

    col_meta = str(block.get("meta_column_matrix", "column_name"))
    st_col = str(block.get("sample_type_col", "sample_type"))

    p2 = block.get("pydeseq2") or {}
    design = str(p2.get("design", "~condition"))
    contrast = list(p2["contrast"])
    min_rep = int(p2.get("min_replicates", 2))

    g_min_total = int(block.get("gene_filter_min_total", 10))
    g_min_samp = int(block.get("gene_filter_min_samples_expressing", 5))

    if not counts_path.is_file():
        print(f"Missing counts matrix: {counts_path}", file=sys.stderr)
        return 1
    if not meta_path.is_file():
        print(f"Missing sample meta: {meta_path}", file=sys.stderr)
        return 1

    mat = pd.read_parquet(counts_path)
    if mat.columns.name != "sample":
        mat.columns.name = "sample"
    meta = pd.read_csv(meta_path, sep="\t")
    if col_meta not in meta.columns or st_col not in meta.columns:
        print("Meta must include meta_column_matrix and sample_type_col", file=sys.stderr)
        return 1

    meta = meta[meta[st_col].isin([lab_a, lab_b])].copy()
    if meta.empty:
        print("No samples in meta after filter for the two sample types.", file=sys.stderr)
        return 1

    meta["condition"] = meta[st_col].map(cond_map)
    if meta["condition"].isna().any():
        print("Unmapped sample_type rows present.", file=sys.stderr)
        return 1

    sid_groups = meta.groupby("sample_submitter_id", sort=False)
    new_mat_cols: dict[str, pd.Series] = {}
    cold_rows: list[dict[str, Any]] = []
    for sid, g in sid_groups:
        cnames = [c for c in g[col_meta].astype(str).tolist() if c in mat.columns]
        if not cnames:
            continue
        if len(cnames) == 1:
            new_mat_cols[str(sid)] = mat[cnames[0]].astype(int)
        else:
            new_mat_cols[str(sid)] = mat[cnames].sum(axis=1).astype(int)
        ucond = g["condition"].unique().tolist()
        if len(ucond) != 1:
            print(f"Ambiguous conditions for {sid}: {ucond}", file=sys.stderr)
            return 1
        cold_rows.append({"sample_id": str(sid), "condition": ucond[0]})

    counts = pd.DataFrame(new_mat_cols)
    counts.index = mat.index
    counts.index.name = "gene_id"
    coldata = pd.DataFrame(cold_rows).set_index("sample_id")

    common = [c for c in counts.columns if c in coldata.index]
    counts = counts[common]
    coldata = coldata.loc[common]

    cvals = list(cond_map.values())
    n_by_cond = {c: int((coldata["condition"] == c).sum()) for c in cvals}
    if any(n_by_cond[c] < min_rep for c in cvals):
        print(
            f"Need >={min_rep} samples per group; counts per condition: {n_by_cond}",
            file=sys.stderr,
        )
        return 1

    gt = counts.sum(axis=1)
    ns = (counts >= 1).sum(axis=1)
    keep = (gt >= g_min_total) & (ns >= g_min_samp)
    counts_f = counts.loc[keep].astype(int)
    if counts_f.shape[0] < 50:
        print(
            f"Very few genes after filter ({counts_f.shape[0]}); relax gene_filter_* in yaml if needed.",
            file=sys.stderr,
        )

    cts = counts_f.T
    dds = DeseqDataSet(
        counts=cts,
        metadata=coldata,
        design=design,
        min_replicates=min_rep,
        quiet=True,
    )
    dds.deseq2()
    stat = DeseqStats(dds, contrast=contrast, quiet=True)
    stat.summary()
    res = stat.results_df.copy()
    res.insert(0, "gene_id", counts_f.index)

    res.to_csv(out_tsv, sep="\t", index=False)

    prov: dict[str, Any] = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "yaml_block": block_key,
        "analysis_tag": tag,
        "method": "PyDESeq2",
        "contrast": contrast,
        "interpretation": "log2FC: second level vs third in contrast (PyDESeq2 convention)",
        "samples_per_condition": n_by_cond,
        "n_genes_tested": int(res.shape[0]),
        "counts_source": str(counts_path.relative_to(rr)).replace("\\", "/"),
        "design": design,
        "gene_filter_min_total": g_min_total,
        "gene_filter_min_samples_expressing": g_min_samp,
    }

    if tag == "primary_vs_recurrent":
        prov["interpretation"] = "log2FC: second level vs third in contrast (Recurrent vs Primary)"
        prov["n_samples_primary"] = n_by_cond[str(block["condition_primary"])]
        prov["n_samples_recurrent"] = n_by_cond[str(block["condition_recurrent"])]

    if tag == "primary_vs_solid_tissue_normal":
        prov["interpretation"] = "log2FC: second level vs third in contrast (Primary Tumor vs Solid Tissue Normal)"
        prov["n_samples_primary_tumor"] = n_by_cond[str(block["condition_primary"])]
        prov["n_samples_solid_tissue_normal"] = n_by_cond[str(block["condition_normal"])]
        prov["caveats"] = [
            "Only five TCGA-GBM Solid Tissue Normal aliquots in this STAR matrix — extremely low power and unstable variance.",
            "Solid Tissue Normal is adjacent/surgical brain, not population-matched reference tissue; paired cases may share patient background with some primaries.",
            "This contrast completes a same-pipeline STAR tumor-vs-TCGA-normal stub only; it is not a substitute for tumor vs GTEx (or other broad normal) on harmonized counts.",
        ]
        prov["estimand_note"] = (
            "Bulk log2 fold change (Primary Tumor / Solid Tissue Normal) on GDC STAR unstranded integer counts; interpret as exploratory."
        )

    out_prov.write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(f"Wrote {out_tsv} ({res.shape[0]} genes)")
    print(f"Wrote {out_prov}")
    return 0
