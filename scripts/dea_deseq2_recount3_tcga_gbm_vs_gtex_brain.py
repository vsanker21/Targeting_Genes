#!/usr/bin/env python3
"""
PyDESeq2: TCGA-GBM tumor vs GTEx brain normal using recount3 harmonized gene counts (GENCODE G029).

- Downloads (if missing): scripts/download_recount3_harmonized_g029.py
- Gene universe: ENSG bases present in results/module2/tcga_gbm_star_unstranded_counts_matrix.parquet
- GTEx brain matrix is streamed; max_gtex_brain_samples: int subsamples columns; null / 0 / negative / "all" uses every column (higher RAM).
- Writes recount3_de_counts_matrix.parquet + recount3_de_sample_meta.tsv (same integers as edgeR).

Requires pydeseq2 (requirements-optional.txt).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from recount3_tcga_gbm_gtex_brain_matrix import build_counts_and_coldata, load_recount3_block, write_de_matrix_assets

try:
    from pydeseq2.dds import DeseqDataSet
    from pydeseq2.ds import DeseqStats
except ImportError as e:
    print(
        "Missing pydeseq2. pip install pydeseq2  (or pip install -r requirements-optional.txt)",
        file=sys.stderr,
    )
    raise SystemExit(1) from e


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    rr = repo_root()
    block = load_recount3_block(rr)
    if not block.get("enabled", True):
        print("deseq2_recount3_tcga_gbm_vs_gtex_brain disabled")
        return 0

    try:
        counts, coldata, aux = build_counts_and_coldata(block, rr)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(str(e), file=sys.stderr)
        return 1

    out_dir = (rr / str(block["output_dir"])).resolve()
    matrix_path, meta_path = write_de_matrix_assets(out_dir, counts, coldata, block)
    print(f"Wrote {matrix_path}")
    print(f"Wrote {meta_path}")

    p2 = block.get("pydeseq2") or {}
    design = str(p2.get("design", "~condition"))
    contrast = list(p2.get("contrast", ["condition", "Tumor", "Normal"]))
    min_rep = int(p2.get("min_replicates", 2))
    g_min_total = int(block.get("gene_filter_min_total", 10))
    g_min_samp = int(block.get("gene_filter_min_samples_expressing", 5))

    n_tumor = int((coldata["condition"] == "Tumor").sum())
    n_norm = int((coldata["condition"] == "Normal").sum())
    if n_tumor < min_rep or n_norm < min_rep:
        print(f"Need >={min_rep} per group; tumor={n_tumor} normal={n_norm}", file=sys.stderr)
        return 1

    gt = counts.sum(axis=1)
    ns = (counts >= 1).sum(axis=1)
    keep = (gt >= g_min_total) & (ns >= g_min_samp)
    counts_f = counts.loc[keep].astype(int)

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

    out_tsv = out_dir / str(block.get("output_results", "deseq2_results.tsv"))
    out_prov = out_dir / str(block.get("output_provenance", "deseq2_provenance.json"))
    res.to_csv(out_tsv, sep="\t", index=False)

    base_u = str(block["recount3_base_url"]).rstrip("/")
    max_cfg = block.get("max_gtex_brain_samples")
    prov: dict[str, Any] = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "method": "PyDESeq2",
        "data_source": "recount3 (JHU IDIES mirror), GENCODE G029 gene sums",
        "contrast": contrast,
        "interpretation": "log2FC: Tumor vs Normal (recount3 harmonized counts; not GDC STAR aligner)",
        "gdc_gtex_star_note": (
            "GTEx open STAR count files are not exposed on the GDC files API facet used here; "
            "recount3 provides paired TCGA-GBM + GTEx brain RNA-seq gene counts on one annotation build."
        ),
        "gene_universe": (
            "Intersection of recount3 G029 gene rows with ENSG *base* IDs from "
            + str(block["star_counts_matrix"])
        ),
        "n_genes_tested": int(res.shape[0]),
        "n_samples_tumor": n_tumor,
        "n_samples_normal_gtex_brain": n_norm,
        "max_gtex_brain_samples_config": max_cfg,
        "max_gtex_brain_samples_effective": aux["max_gtex_brain_samples_resolved"],
        "gtex_all_columns": aux["max_gtex_brain_samples_resolved"] is None,
        "random_seed": aux["random_seed"],
        "gtex_brain_sample_columns": aux["gtex_brain_sample_columns"],
        "prepared_counts_matrix": str(matrix_path.relative_to(rr)).replace("\\", "/"),
        "prepared_sample_meta": str(meta_path.relative_to(rr)).replace("\\", "/"),
        "tcga_g029_file": str(aux["tcga_gz"]),
        "gtex_brain_g029_file": str(aux["gtex_gz"]),
        "urls": {
            "tcga": f"{base_u}/{block['tcga_gbm_g029_relpath']}",
            "gtex_brain": f"{base_u}/{block['gtex_brain_g029_relpath']}",
        },
        "design": design,
        "gene_filter_min_total": g_min_total,
        "gene_filter_min_samples_expressing": g_min_samp,
    }
    out_prov.write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(f"Wrote {out_tsv} ({res.shape[0]} genes)")
    print(f"Wrote {out_prov}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
