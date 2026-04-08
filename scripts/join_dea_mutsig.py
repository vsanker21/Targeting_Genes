#!/usr/bin/env python3
"""
Thin join of MutSig gene tables (e.g. sig_genes.txt from MutSig2CV) onto DEA TSVs.

Maps Hugo symbols to Ensembl via HGNC; left-joins so DEA rows stay complete. Configure paths in
config/mutsig_merge.yaml (mutsig_gene_tsv empty → NaN mutsig columns, provenance status skipped).
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


def load_cfg() -> dict[str, Any]:
    rr = repo_root()
    dr = data_root()
    p = rr / "config" / "mutsig_merge.yaml"
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    raw = dict(raw)
    hg = str(raw.get("hgnc_tsv", "")).replace("{data_root}", str(dr)).replace("/", os.sep)
    raw["hgnc_tsv"] = Path(hg)
    mpath = str(raw.get("mutsig_gene_tsv", "") or "").strip()
    if mpath:
        mp = Path(mpath.replace("/", os.sep))
        if mp.is_absolute():
            raw["mutsig_gene_tsv"] = mp
        else:
            cand_dr = dr / mp
            cand_rr = rr / mp
            raw["mutsig_gene_tsv"] = cand_dr if cand_dr.is_file() else (cand_rr if cand_rr.is_file() else cand_dr)
    else:
        raw["mutsig_gene_tsv"] = None
    return raw


def load_hgnc_symbol_to_ensg(hgnc_path: Path) -> dict[str, str]:
    df = pd.read_csv(hgnc_path, sep="\t", dtype=str, low_memory=False)
    out: dict[str, str] = {}
    for _, row in df.iterrows():
        sym = str(row.get("symbol", "") or "").strip().upper()
        eid = str(row.get("ensembl_gene_id", "") or "").strip()
        if sym and eid:
            out[sym] = ensg_base(eid)
    return out


def read_mutsig_table(cfg: dict[str, Any]) -> pd.DataFrame | None:
    path = cfg["mutsig_gene_tsv"]
    if path is None or not path.is_file():
        return None
    ws = bool(cfg.get("whitespace_split", False))
    try:
        if ws:
            df = pd.read_csv(path, sep=r"\s+", engine="python", comment="#", dtype=str)
        else:
            df = pd.read_csv(path, sep="\t", comment="#", low_memory=False)
    except Exception as e:
        print(f"Failed to read MutSig table {path}: {e}", file=sys.stderr)
        return None
    return df


def build_mutsig_by_ensg(df: pd.DataFrame, cfg: dict[str, Any], sym_to_ensg: dict[str, str]) -> pd.DataFrame:
    gcol = str(cfg.get("gene_column", "gene"))
    if gcol not in df.columns:
        alt = [c for c in df.columns if c.lower() in ("gene", "hugo_symbol", "genesymbol")]
        if not alt:
            raise ValueError(f"gene column {gcol!r} not in MutSig columns: {df.columns.tolist()}")
        gcol = alt[0]

    qcol = str(cfg.get("q_value_column", "q") or "")
    pcol = str(cfg.get("p_value_column", "p") or "")
    rcol = str(cfg.get("rank_column", "") or "")

    tmp = pd.DataFrame(
        {
            "_sym": df[gcol].astype(str).str.strip().str.upper(),
        },
        index=df.index,
    )
    tmp["_ensg"] = tmp["_sym"].map(sym_to_ensg)
    tmp = tmp.dropna(subset=["_ensg"])
    if qcol and qcol in df.columns:
        tmp["mutsig_q"] = pd.to_numeric(df.loc[tmp.index, qcol], errors="coerce")
    else:
        tmp["mutsig_q"] = np.nan
    if pcol and pcol in df.columns:
        tmp["mutsig_p"] = pd.to_numeric(df.loc[tmp.index, pcol], errors="coerce")
    else:
        tmp["mutsig_p"] = np.nan
    if rcol and rcol in df.columns:
        tmp["mutsig_rank"] = pd.to_numeric(df.loc[tmp.index, rcol], errors="coerce")
    else:
        tmp["mutsig_rank"] = np.nan

    agg = tmp.groupby("_ensg").agg(
        mutsig_q=("mutsig_q", "min"),
        mutsig_p=("mutsig_p", "min"),
        mutsig_rank=("mutsig_rank", "min"),
    )
    return agg


def join_dea(dea_path: Path, out_path: Path, by_ensg: pd.DataFrame | None, status: str) -> None:
    dea = pd.read_csv(dea_path, sep="\t", low_memory=False)
    dea["_ensg"] = dea["gene_id"].map(ensg_base)
    if by_ensg is None or by_ensg.empty:
        dea["mutsig_q"] = np.nan
        dea["mutsig_p"] = np.nan
        dea["mutsig_rank"] = np.nan
    else:
        hit = by_ensg.reindex(dea["_ensg"])
        dea["mutsig_q"] = hit["mutsig_q"].to_numpy()
        dea["mutsig_p"] = hit["mutsig_p"].to_numpy()
        dea["mutsig_rank"] = hit["mutsig_rank"].to_numpy()
    dea = dea.drop(columns=["_ensg"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    dea.to_csv(out_path, sep="\t", index=False)
    print(f"Wrote {out_path} (mutsig {status})")


def main() -> int:
    rr = repo_root()
    cfg = load_cfg()
    prov_path = rr / "results" / "module3" / "mutsig_join_provenance.json"
    prov_path.parent.mkdir(parents=True, exist_ok=True)

    sym_to_ensg: dict[str, str] = {}
    by_ensg: pd.DataFrame | None = None
    status = "skipped"
    detail: dict[str, Any] = {"mutsig_gene_tsv": str(cfg["mutsig_gene_tsv"]) if cfg["mutsig_gene_tsv"] else ""}

    mut_df = read_mutsig_table(cfg)
    hgnc_path = cfg["hgnc_tsv"]
    if mut_df is not None and mut_df.shape[0] > 0:
        if not hgnc_path.is_file():
            print(f"Missing HGNC for MutSig join: {hgnc_path}", file=sys.stderr)
            return 2
        sym_to_ensg = load_hgnc_symbol_to_ensg(hgnc_path)
        try:
            by_ensg = build_mutsig_by_ensg(mut_df, cfg, sym_to_ensg)
            status = "ok"
            detail["n_mutsig_genes_mapped"] = len(by_ensg)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 3
    else:
        detail["reason"] = "mutsig_gene_tsv missing, empty, or unreadable"

    pairs: list[tuple[Path, Path]] = [
        (rr / str(cfg["dea_welch_tsv"]), rr / str(cfg["output_welch_tsv"])),
        (rr / str(cfg["dea_ols_tsv"]), rr / str(cfg["output_ols_tsv"])),
    ]
    for pair in cfg.get("extra_dea_pairs") or []:
        if not isinstance(pair, dict):
            continue
        inp = pair.get("input") or pair.get("dea_tsv")
        outp = pair.get("output")
        if inp and outp:
            pairs.append((rr / str(inp), rr / str(outp)))
    for inp, outp in pairs:
        if not inp.is_file():
            print(f"Skip missing DEA input: {inp}", file=sys.stderr)
            continue
        join_dea(inp, outp, by_ensg, status)

    prov_path.write_text(
        json.dumps({"status": status, **detail}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {prov_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
