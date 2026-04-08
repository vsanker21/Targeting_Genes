#!/usr/bin/env python3
"""
Join ARCHS4/recount HDF5 cohort-wide gene summaries onto DEA tables (HGNC symbol match).

Adds per-row columns (Maayan gtex_matrix.h5 / tcga_matrix.h5 gene-level counts):
  archs4_gtex_mean_raw, archs4_gtex_mean_log1p, archs4_gtex_n_samples
  archs4_tcga_mean_raw, archs4_tcga_mean_log1p, archs4_tcga_n_samples

DEA rows use Ensembl gene_id (with or without version); HGNC maps to approved symbol.
ARCHS4 meta/genes are HGNC symbols. Expression may be samples×genes or genes×samples
(aligned to meta/genes length).

Not a substitute for DEA: these are reference cohort marginals for interpretation.
See config/module2_integration.yaml → archs4_expression_join.
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
from depmap_shared import extend_dea_pairs_paths


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def ensg_base(gene_id: str) -> str:
    s = str(gene_id).strip()
    if "." in s and s.startswith("ENSG"):
        return s.split(".", 1)[0]
    return s


def load_integration_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module2_integration.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def load_ensg_to_symbol(hgnc_path: Path, wanted_ensg: set[str]) -> dict[str, str]:
    hg = pd.read_csv(hgnc_path, sep="\t", dtype=str, low_memory=False)
    if "ensembl_gene_id" not in hg.columns or "symbol" not in hg.columns:
        raise ValueError(f"HGNC missing ensembl_gene_id or symbol: {hgnc_path}")
    out: dict[str, str] = {}
    for _, row in hg.iterrows():
        eid = str(row.get("ensembl_gene_id", "") or "").strip()
        sym = str(row.get("symbol", "") or "").strip()
        if not eid or not sym:
            continue
        base = ensg_base(eid)
        if base in wanted_ensg:
            out[base] = sym
    return out


def _symbol_stats_from_h5(
    h5_path: Path,
    symbols: list[str],
    chunk: int = 512,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Mean raw count and mean log1p(count) across all samples for each HGNC symbol in the matrix.
    Returns DataFrame indexed by symbol; meta dict for provenance.
    """
    try:
        import h5py
    except ImportError:
        return (
            pd.DataFrame(columns=["mean_raw", "mean_log1p"]),
            {"error": "h5py_not_installed", "path": str(h5_path)},
        )
    if not h5_path.is_file():
        return (
            pd.DataFrame(columns=["mean_raw", "mean_log1p"]),
            {"error": "missing_file", "path": str(h5_path)},
        )

    rows: list[tuple[str, float, float]] = []
    meta: dict[str, Any] = {"path": str(h5_path)}
    try:
        with h5py.File(h5_path, "r") as h5:
            if "meta/genes" not in h5 or "data/expression" not in h5:
                meta["error"] = "missing_meta_genes_or_data_expression"
                return pd.DataFrame(columns=["mean_raw", "mean_log1p"]), meta
            genes_raw = h5["meta/genes"][:]
            genes = [
                g.decode("utf-8", "replace") if isinstance(g, (bytes, bytearray)) else str(g) for g in genes_raw
            ]
            expr = h5["data/expression"]
            if len(expr.shape) != 2:
                meta["error"] = f"unexpected_shape_{expr.shape}"
                return pd.DataFrame(columns=["mean_raw", "mean_log1p"]), meta
            n0, n1 = expr.shape
            if n1 == len(genes):
                gene_axis = "columns"
                n_samples, n_genes = n0, n1
            elif n0 == len(genes):
                gene_axis = "rows"
                n_genes, n_samples = n0, n1
            else:
                meta["error"] = f"cannot_align_genes shape={expr.shape} meta_genes={len(genes)}"
                return pd.DataFrame(columns=["mean_raw", "mean_log1p"]), meta

            g2i = {g: i for i, g in enumerate(genes)}
            indices: list[int] = []
            sym_order: list[str] = []
            for s in symbols:
                i = g2i.get(s)
                if i is not None:
                    indices.append(i)
                    sym_order.append(s)
            meta.update(
                {
                    "gene_axis": gene_axis,
                    "n_samples": int(n_samples),
                    "n_genes_matrix": int(n_genes),
                    "n_symbols_requested": len(set(symbols)),
                    "n_symbols_matched": len(indices),
                }
            )
            if not indices:
                return pd.DataFrame(columns=["mean_raw", "mean_log1p"]), meta

            for start in range(0, len(indices), chunk):
                batch_idx = indices[start : start + chunk]
                batch_sym = sym_order[start : start + chunk]
                # h5py requires increasing dataset indices for fancy indexing
                order = sorted(range(len(batch_idx)), key=lambda i: batch_idx[i])
                sorted_idx = [batch_idx[i] for i in order]
                sorted_sym = [batch_sym[i] for i in order]
                if gene_axis == "columns":
                    block = np.asarray(expr[:, sorted_idx], dtype=np.float64)
                else:
                    block = np.asarray(expr[sorted_idx, :], dtype=np.float64).T
                for j, sym in enumerate(sorted_sym):
                    arr = block[:, j]
                    arr = arr[np.isfinite(arr)]
                    if arr.size == 0:
                        continue
                    arr = np.maximum(arr, 0.0)
                    log1p = np.log1p(arr)
                    rows.append((sym, float(np.mean(arr)), float(np.mean(log1p))))
    except OSError as e:
        meta["error"] = str(e)
        return pd.DataFrame(columns=["mean_raw", "mean_log1p"]), meta

    if not rows:
        return pd.DataFrame(columns=["mean_raw", "mean_log1p"]), meta
    df = pd.DataFrame(rows, columns=["symbol", "mean_raw", "mean_log1p"]).set_index("symbol")
    return df, meta


def _dea_gene_column(dea: pd.DataFrame) -> str:
    if "gene_id" in dea.columns:
        return "gene_id"
    if "gene" in dea.columns:
        return "gene"
    raise ValueError("DEA table needs gene_id or gene column")


def write_archs4_na_outputs(paths: list[tuple[Path, Path]], reason: str) -> None:
    rr = repo_root()
    na_cols = [
        "archs4_gtex_mean_raw",
        "archs4_gtex_mean_log1p",
        "archs4_gtex_n_samples",
        "archs4_tcga_mean_raw",
        "archs4_tcga_mean_log1p",
        "archs4_tcga_n_samples",
    ]
    for dea_p, out_p in paths:
        if not dea_p.is_file():
            continue
        dea = pd.read_csv(dea_p, sep="\t")
        for c in na_cols:
            dea[c] = np.nan
        dea["archs4_gtex_n_samples"] = 0
        dea["archs4_tcga_n_samples"] = 0
        out_p.parent.mkdir(parents=True, exist_ok=True)
        dea.to_csv(out_p, sep="\t", index=False)
        print(f"Wrote {out_p} (ARCHS4 unavailable: {reason})")
    prov = {"status": "skipped", "reason": reason}
    (rr / "results" / "module3" / "dea_archs4_join_provenance.json").write_text(
        json.dumps(prov, indent=2),
        encoding="utf-8",
    )


def join_one_dea(
    dea_path: Path,
    out_path: Path,
    ensg_to_sym: dict[str, str],
    gtex_df: pd.DataFrame,
    tcga_df: pd.DataFrame,
    gtex_meta: dict[str, Any],
    tcga_meta: dict[str, Any],
) -> None:
    dea = pd.read_csv(dea_path, sep="\t")
    gcol = _dea_gene_column(dea)
    dea["_ensg"] = dea[gcol].map(ensg_base)
    dea["_sym"] = dea["_ensg"].map(ensg_to_sym)

    def attach(prefix: str, statdf: pd.DataFrame, meta: dict[str, Any]) -> None:
        hit = statdf.reindex(dea["_sym"])
        dea[f"{prefix}_mean_raw"] = hit["mean_raw"].to_numpy()
        dea[f"{prefix}_mean_log1p"] = hit["mean_log1p"].to_numpy()
        n = int(meta.get("n_samples") or 0) if meta.get("error") is None else 0
        dea[f"{prefix}_n_samples"] = np.where(hit["mean_raw"].notna(), n, 0).astype(np.int64)

    attach("archs4_gtex", gtex_df, gtex_meta)
    attach("archs4_tcga", tcga_df, tcga_meta)
    dea = dea.drop(columns=["_ensg", "_sym"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dea.to_csv(out_path, sep="\t", index=False)
    n_ok = dea["archs4_gtex_mean_log1p"].notna().sum()
    print(f"Wrote {out_path} rows={len(dea)} with ARCHS4 GTEx log1p mean for {n_ok} genes")


def main() -> int:
    cfg = load_integration_cfg()
    blk = cfg.get("archs4_expression_join") or {}
    if not blk.get("enabled", True):
        print("archs4_expression_join disabled in module2_integration.yaml", file=sys.stderr)
        return 0

    root = data_root()
    rr = repo_root()
    paths = extend_dea_pairs_paths(rr, blk)

    hrel = blk.get("hgnc_tsv", "{data_root}/references/hgnc_complete_set.txt")
    hgnc_path = Path(hrel.replace("{data_root}", str(root)).replace("/", os.sep))
    if not hgnc_path.is_file():
        print(f"WARNING: Missing HGNC at {hgnc_path}", file=sys.stderr)
        write_archs4_na_outputs(paths, "missing HGNC TSV")
        return 0

    adir = blk.get("archs4_dir", "{data_root}/references/archs4_recount")
    base = Path(adir.replace("{data_root}", str(root)).replace("/", os.sep))
    gtex_p = base / str(blk.get("gtex_h5", "gtex_matrix.h5"))
    tcga_p = base / str(blk.get("tcga_h5", "tcga_matrix.h5"))

    try:
        import h5py  # noqa: F401
    except ImportError:
        print("WARNING: h5py not installed", file=sys.stderr)
        write_archs4_na_outputs(paths, "h5py_not_installed")
        return 0

    if not gtex_p.is_file() and not tcga_p.is_file():
        print(f"WARNING: No ARCHS4 HDF5 under {base}", file=sys.stderr)
        write_archs4_na_outputs(paths, "missing gtex_matrix.h5 and tcga_matrix.h5")
        return 0

    wanted: set[str] = set()
    for dea_p, _ in paths:
        if not dea_p.is_file():
            continue
        gcol = "gene_id" if "gene_id" in pd.read_csv(dea_p, sep="\t", nrows=0).columns else "gene"
        d = pd.read_csv(dea_p, sep="\t", usecols=[gcol])
        wanted.update(d[gcol].map(ensg_base))

    if not wanted:
        print("No DEA tables found.", file=sys.stderr)
        return 3
    if not any(p[0].is_file() for p in paths):
        print("No DEA input files on disk.", file=sys.stderr)
        return 3

    try:
        ensg_to_sym = load_ensg_to_symbol(hgnc_path, wanted)
    except Exception as e:
        print(f"WARNING: HGNC load failed: {e}", file=sys.stderr)
        write_archs4_na_outputs(paths, f"hgnc_error: {e}")
        return 0

    symbols_needed = sorted({ensg_to_sym[e] for e in wanted if e in ensg_to_sym})
    gtex_df, gtex_meta = _symbol_stats_from_h5(gtex_p, symbols_needed)
    tcga_df, tcga_meta = _symbol_stats_from_h5(tcga_p, symbols_needed)

    prov = {
        "status": "ok",
        "note": "Cohort-wide mean raw count and mean log1p(count) per gene; not sample-matched to TCGA DEA.",
        "n_dea_ensembl_with_symbol": len(ensg_to_sym),
        "gtex": gtex_meta,
        "tcga": tcga_meta,
    }
    (rr / "results" / "module3" / "dea_archs4_join_provenance.json").write_text(
        json.dumps(prov, indent=2),
        encoding="utf-8",
    )

    for dea_p, out_p in paths:
        if not dea_p.is_file():
            print(f"SKIP missing DEA {dea_p}", file=sys.stderr)
            continue
        join_one_dea(dea_p, out_p, ensg_to_sym, gtex_df, tcga_df, gtex_meta, tcga_meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
