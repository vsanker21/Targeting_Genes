#!/usr/bin/env python3
"""
Outline Module 2 §2.3: Verhaak-class subtype labels on TOIL TCGA-GBM tumors (rank-based scoring).

Default: MSigDB 2024.1.Hs c2.cgp Verhaak gene sets (bundled GMT under references/).
Alternative: compact symbol lists in config/gbm_verhaak_signatures.yaml (gene_set_source: compact_yaml).
Optional: assignment_method centroid_cosine + references/verhaak_centroids_user_template.tsv (fill with
published Verhaak 2010 / MOVICS-derived centroids; template is header-only).

MOVICS multi-omics consensus is not implemented here — use R/MOVICS for that tier.
See config/module2_integration.yaml — subtype_scoring
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
from scipy.stats import rankdata


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def load_integration_cfg() -> dict[str, Any]:
    rr = repo_root()
    p = rr / "config" / "module2_integration.yaml"
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    st = raw.get("subtype_scoring") or {}
    hg = st.get("hgnc_tsv", "")
    st = dict(st)
    st["hgnc_tsv"] = Path(hg.replace("{data_root}", str(data_root())).replace("/", os.sep))
    cp = str(st.get("centroid_profile_tsv", "") or "").strip()
    st["centroid_profile_tsv"] = (rr / cp.replace("/", os.sep)) if cp else None
    return st


def load_centroid_numeric(path: Path) -> tuple[pd.DataFrame, list[str]]:
    raw = pd.read_csv(path, sep="\t", dtype=str, low_memory=False)
    if "gene_id" not in raw.columns:
        raise ValueError("centroid TSV must include a gene_id column (Ensembl)")
    raw = raw.copy()
    raw["_g"] = raw["gene_id"].map(lambda x: ensg_base(str(x).strip()))
    raw = raw.dropna(subset=["_g"]).drop_duplicates(subset=["_g"], keep="first")
    raw = raw.drop(columns=["gene_id"]).set_index("_g")
    st_cols: list[str] = []
    for c in raw.columns:
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
        if np.isfinite(raw[c].to_numpy(dtype=float)).any():
            st_cols.append(c)
    return raw[st_cols], st_cols


def top_score_margin_and_runner_up(M: np.ndarray, names: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """
    Per row: difference between best and second-best finite scores; name of runner-up subtype.
    Used for assignment confidence (rank-mean or cosine); same units as input scores.
    """
    n, k = M.shape
    margins = np.full(n, np.nan, dtype=np.float64)
    runners = np.empty(n, dtype=object)
    runners[:] = ""
    for j in range(n):
        row = M[j, :].astype(np.float64)
        pairs: list[tuple[float, int]] = []
        for i in range(k):
            if np.isfinite(row[i]):
                pairs.append((float(row[i]), i))
        if len(pairs) < 2:
            continue
        pairs.sort(key=lambda x: -x[0])
        margins[j] = pairs[0][0] - pairs[1][0]
        runners[j] = names[pairs[1][1]]
    return margins, runners


def cosine_assign_sample_expr(
    expr_genes_x_samples: np.ndarray,
    centroid_genes_x_subtypes: np.ndarray,
) -> np.ndarray:
    """Rows genes, cols samples / subtype profiles → similarity matrix samples × subtypes."""
    n_s = expr_genes_x_samples.shape[1]
    k = centroid_genes_x_subtypes.shape[1]
    sims = np.full((n_s, k), np.nan, dtype=np.float64)
    for j in range(n_s):
        v = expr_genes_x_samples[:, j].astype(np.float64)
        if not np.isfinite(v).all():
            med = np.nanmedian(v)
            v = np.nan_to_num(v, nan=med if np.isfinite(med) else 0.0)
        vz = (v - np.mean(v)) / (np.std(v) + 1e-8)
        nv = np.linalg.norm(vz)
        if nv < 1e-12:
            continue
        for kidx in range(k):
            c = centroid_genes_x_subtypes[:, kidx].astype(np.float64)
            cz = (c - np.mean(c)) / (np.std(c) + 1e-8)
            nc = np.linalg.norm(cz)
            if nc < 1e-12:
                continue
            sims[j, kidx] = float(np.dot(vz, cz) / (nv * nc))
    return sims


def ensg_base(gene_id: str) -> str:
    s = str(gene_id).strip()
    if "." in s and s.startswith("ENSG"):
        return s.split(".", 1)[0]
    return s


# MSigDB C2 CGP gene set names → short labels (2024.1.Hs GMT bundled under references/)
MSIGDB_VERHAAK_TO_LABEL: dict[str, str] = {
    "VERHAAK_GLIOBLASTOMA_CLASSICAL": "Classical",
    "VERHAAK_GLIOBLASTOMA_MESENCHYMAL": "Mesenchymal",
    "VERHAAK_GLIOBLASTOMA_NEURAL": "Neural",
    "VERHAAK_GLIOBLASTOMA_PRONEURAL": "Proneural",
}


def parse_msigdb_gmt(path: Path) -> dict[str, list[str]]:
    sets: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        sets[parts[0]] = [g.strip() for g in parts[2:] if g.strip()]
    return sets


def load_hgnc_symbol_to_ensg(hgnc_path: Path) -> dict[str, str]:
    df = pd.read_csv(hgnc_path, sep="\t", dtype=str, low_memory=False)
    if "symbol" not in df.columns or "ensembl_gene_id" not in df.columns:
        raise ValueError(f"Unexpected HGNC columns: {df.columns.tolist()}")
    out: dict[str, str] = {}
    for _, row in df.iterrows():
        sym = str(row["symbol"]).strip()
        eid = str(row["ensembl_gene_id"]).strip()
        if sym and eid and sym not in out:
            out[sym.upper()] = ensg_base(eid)
    return out


def main() -> int:
    st = load_integration_cfg()
    rr = repo_root()
    method = str(st.get("assignment_method", "rank_aggregate")).lower().strip()
    source = str(st.get("gene_set_source", "msigdb_gmt")).lower().strip()
    expr_path = rr / st["expression_parquet"]
    sample_path = rr / st["sample_table"]
    hgnc_path = st["hgnc_tsv"]
    out_tsv = rr / st["output_scores"]
    out_json = rr / st["output_summary_json"]

    if not expr_path.is_file() or not sample_path.is_file():
        print("Missing expression parquet or sample table.", file=sys.stderr)
        return 1

    meta = pd.read_csv(sample_path, sep="\t")
    meta["sample_id"] = meta["sample_id"].astype(str)
    tumor_ids = meta.loc[meta["group"] == "tumor", "sample_id"].tolist()
    if not tumor_ids:
        print("No tumor samples in manifest.", file=sys.stderr)
        return 3

    if method not in ("rank_aggregate", "centroid_cosine"):
        print(
            f"Unknown assignment_method: {method} (use rank_aggregate or centroid_cosine)",
            file=sys.stderr,
        )
        return 2

    if method == "centroid_cosine":
        cpath = st.get("centroid_profile_tsv")
        if cpath is None or not cpath.is_file():
            print("centroid_cosine requires an existing centroid_profile_tsv file with data rows.", file=sys.stderr)
            return 2
        try:
            c_df, st_cols = load_centroid_numeric(cpath)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2
        if len(st_cols) < 2:
            print("Centroid TSV needs ≥2 numeric subtype columns with values.", file=sys.stderr)
            return 2
        df = pd.read_parquet(expr_path, columns=tumor_ids)
        df.index = df.index.map(lambda x: ensg_base(str(x)))
        df = df.groupby(df.index).median()
        if not np.isfinite(df.to_numpy(dtype=np.float64)).all():
            arr = df.to_numpy(dtype=np.float64)
            col_med = np.nanmedian(arr, axis=0)
            col_med = np.where(np.isfinite(col_med), col_med, 0.0)
            ind = ~np.isfinite(arr)
            arr[ind] = np.take(col_med, np.where(ind)[1])
            df = pd.DataFrame(arr, index=df.index, columns=df.columns)
        common = sorted(set(df.index).intersection(c_df.index))
        if len(common) < 8:
            print(f"Too few centroid genes in matrix: {len(common)}", file=sys.stderr)
            return 4
        v_mat = df.loc[common, tumor_ids].to_numpy(dtype=np.float64)
        c_mat = c_df.loc[common, st_cols].to_numpy(dtype=np.float64)
        sims = cosine_assign_sample_expr(v_mat, c_mat)
        names = st_cols
        m_eff = np.where(np.isfinite(sims), sims, -np.inf)
        winners = np.argmax(m_eff, axis=1)
        row_ok = np.isfinite(sims).any(axis=1)
        assigned = [names[i] if row_ok[j] else "Unassigned" for j, i in enumerate(winners)]
        mar, run_up = top_score_margin_and_runner_up(m_eff, names)
        out = pd.DataFrame(
            {
                "sample_id": tumor_ids,
                "verhaak_subtype_call": assigned,
                "assignment_score_margin": mar,
                "verhaak_subtype_runner_up": run_up,
            }
        )
        for i, name in enumerate(names):
            out[f"centroid_cosine_{name}"] = sims[:, i]
        out_tsv.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(out_tsv, sep="\t", index=False)
        counts = out["verhaak_subtype_call"].value_counts().to_dict()
        assigned_m = out.loc[out["verhaak_subtype_call"] != "Unassigned", "assignment_score_margin"]
        summ = {
            "n_tumor_samples": len(tumor_ids),
            "subtype_counts": counts,
            "assignment_method": "centroid_cosine",
            "n_genes_centroid_intersection": len(common),
            "centroid_profile_tsv": str(cpath),
            "centroid_subtype_columns": names,
            "assignment_score_margin_mean_among_assigned": float(assigned_m.mean())
            if len(assigned_m) > 0
            else None,
            "assignment_score_margin_median_among_assigned": float(assigned_m.median())
            if len(assigned_m) > 0
            else None,
            "interpretation": "assignment_score_margin is top-minus-second cosine similarity; low values indicate ambiguous calls.",
        }
        out_json.write_text(json.dumps(summ, indent=2), encoding="utf-8")
        print(f"Wrote {out_tsv} and {out_json}")
        return 0

    if not hgnc_path.is_file():
        print(f"Missing HGNC file: {hgnc_path}", file=sys.stderr)
        return 2

    sym_map = load_hgnc_symbol_to_ensg(hgnc_path)
    subtype_to_ensg: dict[str, list[str]] = {}
    subtypes_meta: dict[str, Any] = {}

    if source == "msigdb_gmt":
        gmt_path = rr / st.get("msigdb_gmt", "references/verhaak_msigdb_c2_cgp_2024.1.Hs.gmt")
        if not gmt_path.is_file():
            print(f"Missing MSigDB GMT: {gmt_path}", file=sys.stderr)
            return 2
        gmt_sets = parse_msigdb_gmt(gmt_path)
        for msig_name, label in MSIGDB_VERHAAK_TO_LABEL.items():
            genes = gmt_sets.get(msig_name, [])
            ens = []
            for g in genes:
                e = sym_map.get(str(g).strip().upper())
                if e:
                    ens.append(e)
            subtype_to_ensg[label] = ens
        subtypes_meta = {
            "gene_set_source": "msigdb_gmt",
            "msigdb_gmt": str(gmt_path),
            "msigdb_release_note": "MSigDB 2024.1.Hs c2.cgp symbols (Verhaak et al.)",
            "assignment_method": "rank_aggregate",
        }
    elif source == "compact_yaml":
        sig_path = rr / st.get("signatures_yaml", "config/gbm_verhaak_signatures.yaml")
        if not sig_path.is_file():
            print(f"Missing compact YAML: {sig_path}", file=sys.stderr)
            return 2
        sig_yaml = yaml.safe_load(sig_path.read_text(encoding="utf-8"))
        subtypes: dict[str, list[str]] = sig_yaml.get("subtypes") or {}
        for st_name, genes in subtypes.items():
            ens = []
            for g in genes:
                e = sym_map.get(str(g).strip().upper())
                if e:
                    ens.append(e)
            subtype_to_ensg[st_name] = ens
        subtypes_meta = {
            "gene_set_source": "compact_yaml",
            "signatures_yaml": str(sig_path),
            "assignment_method": "rank_aggregate",
        }
    else:
        print(f"Unknown gene_set_source: {source}", file=sys.stderr)
        return 2

    df = pd.read_parquet(expr_path, columns=tumor_ids)
    df.index = df.index.map(lambda x: ensg_base(str(x)))
    # average duplicate Ensembl rows if any
    df = df.groupby(df.index).median()

    union_ensg: set[str] = set()
    for ens in subtype_to_ensg.values():
        union_ensg.update(ens)

    genes_use = sorted(union_ensg.intersection(df.index))
    if len(genes_use) < 8:
        print(f"Too few signature genes in matrix: {len(genes_use)}", file=sys.stderr)
        return 4

    X = df.loc[genes_use, tumor_ids].to_numpy(dtype=np.float64)
    if not np.isfinite(X).all():
        col_med = np.nanmedian(X, axis=0)
        col_med = np.where(np.isfinite(col_med), col_med, 0.0)
        ind = ~np.isfinite(X)
        X[ind] = np.take(col_med, np.where(ind)[1])
    R = rankdata(X, axis=0)

    gene_to_row = {g: i for i, g in enumerate(genes_use)}
    score_cols: dict[str, np.ndarray] = {}
    for st_name, ens_list in subtype_to_ensg.items():
        rows = [gene_to_row[e] for e in ens_list if e in gene_to_row]
        if not rows:
            score_cols[st_name] = np.full(len(tumor_ids), -np.inf)
            continue
        score_cols[st_name] = R[rows, :].mean(axis=0)

    names = sorted(score_cols.keys())
    M = np.column_stack([score_cols[k] for k in names])
    M_eff = np.where(np.isfinite(M), M, -np.inf)
    winners = np.argmax(M_eff, axis=1)
    row_ok = np.isfinite(M).any(axis=1)
    assigned = [names[i] if row_ok[j] else "Unassigned" for j, i in enumerate(winners)]
    mar, run_up = top_score_margin_and_runner_up(M_eff, names)

    out = pd.DataFrame(
        {
            "sample_id": tumor_ids,
            "verhaak_subtype_call": assigned,
            "assignment_score_margin": mar,
            "verhaak_subtype_runner_up": run_up,
        }
    )
    for st_name in names:
        out[f"rank_score_{st_name}"] = score_cols[st_name]

    out_tsv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_tsv, sep="\t", index=False)

    counts = out["verhaak_subtype_call"].value_counts().to_dict()
    assigned_m = out.loc[out["verhaak_subtype_call"] != "Unassigned", "assignment_score_margin"]
    summ = {
        "n_tumor_samples": len(tumor_ids),
        "subtype_counts": counts,
        "signature_genes_in_matrix": len(genes_use),
        "subtypes_defined": list(subtype_to_ensg.keys()),
        "genes_per_subtype_matched": {k: len(v) for k, v in subtype_to_ensg.items()},
        "assignment_score_margin_mean_among_assigned": float(assigned_m.mean())
        if len(assigned_m) > 0
        else None,
        "assignment_score_margin_median_among_assigned": float(assigned_m.median())
        if len(assigned_m) > 0
        else None,
        "interpretation": "assignment_score_margin is mean rank-of-signature-genes difference (top vs runner-up subtype); scale depends on cohort n; small margins indicate ambiguous calls.",
        **subtypes_meta,
    }
    if "assignment_method" not in summ:
        summ["assignment_method"] = "rank_aggregate"
    out_json.write_text(json.dumps(summ, indent=2), encoding="utf-8")
    print(f"Wrote {out_tsv} and {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
