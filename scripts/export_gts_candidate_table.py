#!/usr/bin/env python3
"""
Module 7: therapeutic candidate tables from DEA + DepMap CRISPR + outline flags.

- gts_evidence_tier (1–4): discrete screen from strong DE + DepMap dependency threshold.
- glioma_target_score / glioma_target_tier: GLIOMA-TARGET composite v1.1 (outline §7.1 subset)
  from config/glioma_target_score.yaml — weighted percentile ranks for E, M, and (v1.1) D (HGNC
  UniProt proxy) + N (STRING export list). S/T reserved at weight 0 until wired.

Welch jobs use outline_m21_high_confidence_screen when present; OLS jobs fall back to
FDR + |effect| >= abs_effect_min from config.
Adjusted p/FDR: uses padj_bh if present, else padj (PyDESeq2), else FDR (edgeR).
Optional stratified_glob_jobs write under results/module7/gts_candidate_stratified/{job_tag}/.

Config: config/module7_inputs.yaml — gts_candidate_stub; config/glioma_target_score.yaml — weights.
"""

from __future__ import annotations

import json
import os
import re
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


def load_m7_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module7_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def resolve_template(s: str, dr: Path) -> str:
    return str(s).replace("{data_root}", str(dr)).replace("/", os.sep)


def load_ensg_to_symbol(hgnc_path: Path) -> dict[str, str]:
    hg = pd.read_csv(hgnc_path, sep="\t", dtype=str, low_memory=False)
    if "ensembl_gene_id" not in hg.columns or "symbol" not in hg.columns:
        raise ValueError(f"HGNC missing ensembl_gene_id or symbol: {hgnc_path}")
    out: dict[str, str] = {}
    for _, row in hg.iterrows():
        eid = str(row.get("ensembl_gene_id", "") or "").strip()
        sym = str(row.get("symbol", "") or "").strip()
        if not eid.startswith("ENSG") or not sym:
            continue
        base = ensg_base(eid)
        if base not in out:
            out[base] = sym
    return out


def rel_to_repo(rr: Path, p: Path) -> str:
    try:
        return p.resolve().relative_to(rr.resolve()).as_posix()
    except ValueError:
        return str(p.as_posix())


def primary_uniprot(raw: str | float | None) -> str | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    if not s:
        return None
    for part in re.split(r"[,;\s|]+", s):
        p = part.strip()
        if p:
            return p
    return None


def load_symbol_uniprot_score(hgnc_path: Path) -> dict[str, float]:
    """1.0 if HGNC lists a primary UniProt ID for the symbol; else 0.0 (aligned with Module 6 bridge)."""
    df = pd.read_csv(hgnc_path, sep="\t", dtype=str, low_memory=False)
    if "symbol" not in df.columns or "uniprot_ids" not in df.columns:
        raise ValueError(f"HGNC missing symbol/uniprot_ids: {hgnc_path}")
    out: dict[str, float] = {}
    for _, row in df.iterrows():
        sym = str(row.get("symbol", "") or "").strip()
        if not sym or sym in out:
            continue
        up = primary_uniprot(row.get("uniprot_ids"))
        out[sym] = 1.0 if up else 0.0
    return out


def load_string_symbol_set(path: Path) -> set[str] | None:
    if not path.is_file():
        return None
    syms: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.split("#", 1)[0].strip()
        if s:
            syms.add(s)
    return syms


def load_glioma_target_score_cfg(rr: Path, m7_cfg: dict[str, Any]) -> dict[str, Any]:
    rel = str(m7_cfg.get("glioma_target_score_config") or "config/glioma_target_score.yaml").strip()
    p = rr / rel.replace("/", os.sep)
    if not p.is_file():
        return {"_missing_path": str(p.resolve())}
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else {}


def apply_glioma_target_composite(
    out: pd.DataFrame,
    effect_col: str,
    cfg: dict[str, Any],
    *,
    symbol_uniprot: dict[str, float] | None = None,
    string_set: set[str] | None = None,
) -> pd.DataFrame:
    """Add glioma_target_score [0,1], sub-norms, and glioma_target_tier (1–4) from outline §7.2 bands."""
    if not cfg.get("enabled", True):
        return out.sort_values(["gts_evidence_tier", "gts_stub_sort_metric"], ascending=[True, False])

    if effect_col not in out.columns:
        raise ValueError(f"apply_glioma_target_composite: missing effect column {effect_col!r}")

    w = cfg.get("weights") or {}
    w_e = float(w.get("E", 0.32))
    w_m = float(w.get("M", 0.48))
    w_d = float(w.get("D", 0.0))
    w_n = float(w.get("N", 0.0))
    s = w_e + w_m + w_d + w_n
    if s <= 0:
        w_e, w_m, w_d, w_n = 0.5, 0.5, 0.0, 0.0
    else:
        w_e, w_m, w_d, w_n = w_e / s, w_m / s, w_d / s, w_n / s

    mc = cfg.get("m_components") or {}
    m_dep = float(mc.get("depmap", 0.82))
    m_drv = float(mc.get("known_driver", 0.18))
    msum = m_dep + m_drv
    if msum > 0:
        m_dep, m_drv = m_dep / msum, m_drv / msum

    ec = cfg.get("expression_components") or {}
    e_abs = float(ec.get("abs_effect_rank", 0.55))
    e_sn = float(ec.get("signed_neg_log10_p_rank", 0.45))
    esum = e_abs + e_sn
    if esum > 0:
        e_abs, e_sn = e_abs / esum, e_sn / esum

    abs_eff = pd.to_numeric(out[effect_col], errors="coerce").abs()
    r_abs = abs_eff.rank(pct=True, method="average")
    snlp = pd.to_numeric(out["signed_neglog10_p"], errors="coerce").abs()
    r_sn = snlp.rank(pct=True, method="average")
    e_norm = e_abs * r_abs + e_sn * r_sn

    dep = pd.to_numeric(out["depmap_crispr_median_gbm"], errors="coerce")
    m_dep_score = pd.Series(0.5, index=out.index, dtype=np.float64)
    ok = dep.notna()
    if ok.any():
        m_dep_score.loc[ok] = (-dep.loc[ok]).rank(pct=True, method="average")

    if "outline_m22_known_gbm_driver" in out.columns:
        drv = out["outline_m22_known_gbm_driver"].map(
            lambda x: str(x).strip().lower() in ("true", "1", "yes")
        )
    else:
        drv = pd.Series(False, index=out.index)
    m_drv_score = drv.astype(np.float64)

    m_norm = m_dep * m_dep_score + m_drv * m_drv_score

    sym = out["hgnc_symbol"].astype(str).str.strip()
    if symbol_uniprot:
        d_raw = sym.map(lambda x: float(symbol_uniprot.get(x, 0.0)))
    else:
        d_raw = pd.Series(0.5, index=out.index, dtype=np.float64)
    d_norm = d_raw.rank(pct=True, method="average")

    if string_set is not None:
        n_raw = sym.map(lambda x: 1.0 if x in string_set else 0.0)
        n_norm = n_raw.rank(pct=True, method="average")
    else:
        n_norm = pd.Series(0.5, index=out.index, dtype=np.float64)

    gts = (w_e * e_norm + w_m * m_norm + w_d * d_norm + w_n * n_norm).clip(0.0, 1.0)

    th = cfg.get("tier_thresholds") or {}
    t1 = float(th.get("tier_1_min", 0.75))
    t2 = float(th.get("tier_2_min", 0.50))
    t3 = float(th.get("tier_3_min", 0.25))

    g = gts.to_numpy(dtype=np.float64)
    tier_np = np.full(len(g), 4, dtype=np.int64)
    tier_np[g >= t3] = 3
    tier_np[g >= t2] = 2
    tier_np[g >= t1] = 1

    out = out.copy()
    out["gts_sub_E_norm"] = e_norm
    out["gts_sub_M_norm"] = m_norm
    out["gts_sub_D_norm"] = d_norm
    out["gts_sub_N_norm"] = n_norm
    out["glioma_target_score"] = gts
    out["glioma_target_tier"] = tier_np
    return out.sort_values(
        ["glioma_target_tier", "glioma_target_score", "gts_evidence_tier", "gts_stub_sort_metric"],
        ascending=[True, False, True, False],
    )


def _resolve_fdr_column(dea: pd.DataFrame) -> str:
    for c in ("padj_bh", "padj", "FDR"):
        if c in dea.columns:
            return c
    raise ValueError(
        "DEA missing adjusted p / FDR column (expected one of: padj_bh, padj, FDR)"
    )


def build_table(
    dea: pd.DataFrame,
    *,
    effect_col: str,
    p_col: str,
    p_floor: float,
    fdr_max: float,
    abs_eff_min: float,
    dep_col: str,
    dep_thresh: float,
    ensg_sym: dict[str, str],
    gts_score_cfg: dict[str, Any],
    symbol_uniprot: dict[str, float],
    string_set: set[str] | None,
) -> pd.DataFrame:
    fdr_src = _resolve_fdr_column(dea)
    need = ["gene_id", effect_col, p_col]
    for c in need:
        if c not in dea.columns:
            raise ValueError(f"DEA missing column {c!r}")

    eff = pd.to_numeric(dea[effect_col], errors="coerce")
    pv = pd.to_numeric(dea[p_col], errors="coerce").clip(lower=p_floor, upper=1.0)
    padj = pd.to_numeric(dea[fdr_src], errors="coerce")
    with np.errstate(divide="ignore"):
        neglog = -np.log10(pv.to_numpy(dtype=np.float64))
    sgn = np.sign(eff.to_numpy(dtype=np.float64))
    signed_nl = sgn * neglog

    has_m21 = "outline_m21_high_confidence_screen" in dea.columns
    if has_m21:
        m21 = dea["outline_m21_high_confidence_screen"].map(
            lambda x: str(x).strip().lower() in ("true", "1", "yes")
        )
    else:
        m21 = pd.Series(False, index=dea.index)

    has_driver = "outline_m22_known_gbm_driver" in dea.columns
    driver = (
        dea["outline_m22_known_gbm_driver"].map(lambda x: str(x).strip().lower() in ("true", "1", "yes"))
        if has_driver
        else pd.Series(False, index=dea.index)
    )

    if dep_col in dea.columns:
        dep = pd.to_numeric(dea[dep_col], errors="coerce")
    else:
        dep = pd.Series(np.nan, index=dea.index)

    strong_ols = (padj <= fdr_max) & (eff.abs() >= abs_eff_min)
    strong = m21 | strong_ols

    dep_arr = dep.to_numpy(dtype=np.float64)
    dep_hit = np.isfinite(dep_arr) & (dep_arr <= dep_thresh)

    s = strong.to_numpy(dtype=bool)
    p_ok = (padj <= fdr_max).fillna(False).to_numpy(dtype=bool)
    tier = np.full(len(dea), 4, dtype=np.int64)
    tier[np.logical_and(~s, p_ok)] = 3
    tier[s] = 2
    tier[np.logical_and(s, dep_hit)] = 1

    rows = []
    for i, gid in enumerate(dea["gene_id"].astype(str)):
        base = ensg_base(gid)
        sym = ensg_sym.get(base)
        if not sym:
            continue
        sn = signed_nl[i]
        if not np.isfinite(sn):
            continue
        row: dict[str, Any] = {
            "hgnc_symbol": sym,
            "gene_id": gid,
            "gts_evidence_tier": int(tier[i]),
            "gts_stub_sort_metric": float(abs(sn) + (2.0 if driver.iloc[i] else 0.0) + (1.0 if tier[i] == 1 else 0.0)),
            "signed_neglog10_p": float(sn),
            "padj_bh": float(padj.iloc[i]) if pd.notna(padj.iloc[i]) else np.nan,
            effect_col: float(eff.iloc[i]) if pd.notna(eff.iloc[i]) else np.nan,
            "depmap_crispr_median_gbm": float(dep.iloc[i]) if pd.notna(dep.iloc[i]) else np.nan,
            "outline_m21_high_confidence_screen": bool(m21.iloc[i]) if has_m21 else False,
            "outline_m22_known_gbm_driver": bool(driver.iloc[i]) if has_driver else False,
        }
        if "stratify_subtype" in dea.columns:
            row["stratify_subtype"] = str(dea["stratify_subtype"].iloc[i]).strip()
        rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        raise RuntimeError("No rows after HGNC symbol filter")
    out = out.sort_values(["gts_evidence_tier", "gts_stub_sort_metric"], ascending=[True, False])
    return apply_glioma_target_composite(
        out,
        effect_col,
        gts_score_cfg,
        symbol_uniprot=symbol_uniprot,
        string_set=string_set,
    )


def main() -> int:
    rr = repo_root()
    dr = data_root()
    cfg = load_m7_cfg()
    gts_score_cfg = load_glioma_target_score_cfg(rr, cfg)
    if gts_score_cfg.get("_missing_path"):
        print(f"ERROR: missing {gts_score_cfg['_missing_path']}", file=sys.stderr)
        return 1
    block = cfg.get("gts_candidate_stub") or {}
    if not block.get("enabled", True):
        print("gts_candidate_stub disabled")
        return 0

    hgnc_path = Path(resolve_template(block.get("hgnc_tsv", "{data_root}/references/hgnc_complete_set.txt"), dr))
    if not hgnc_path.is_file():
        print(f"Missing HGNC {hgnc_path}", file=sys.stderr)
        return 1

    p_floor = float(block.get("pvalue_floor", 1e-300))
    fdr_max = float(block.get("fdr_max", 0.05))
    abs_eff_min = float(block.get("abs_effect_min", 1.5))
    dep_col = str(block.get("depmap_crispr_col", "depmap_crispr_median_gbm"))
    dep_thresh = float(block.get("depmap_dependency_at_or_below", -0.5))
    jobs = list(block.get("jobs") or [])
    sglobs = list(block.get("stratified_glob_jobs") or [])
    if not jobs and not sglobs:
        print("gts_candidate_stub: need jobs and/or stratified_glob_jobs", file=sys.stderr)
        return 1

    ensg_sym = load_ensg_to_symbol(hgnc_path)
    try:
        symbol_uniprot = load_symbol_uniprot_score(hgnc_path)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    summaries: list[dict[str, Any]] = []
    strat_summaries: list[dict[str, Any]] = []

    for job in jobs:
        tag = str(job.get("tag", "")).strip()
        dea_rel = str(job.get("dea_tsv", "")).strip()
        eff_col = str(job.get("effect_col", "")).strip()
        p_col = str(job.get("p_col", "pvalue")).strip()
        out_rel = str(job.get("output_tsv", "")).strip()
        if not tag or not dea_rel or not eff_col or not out_rel:
            print(f"skip incomplete job {job}", file=sys.stderr)
            continue
        dea_path = rr / dea_rel.replace("/", os.sep)
        if not dea_path.is_file():
            print(f"Missing {dea_path}", file=sys.stderr)
            return 1
        dea = pd.read_csv(dea_path, sep="\t", low_memory=False)
        str_rel = str(job.get("string_symbol_list_txt") or "").strip()
        str_set = load_string_symbol_set(rr / str_rel.replace("/", os.sep)) if str_rel else None
        tab = build_table(
            dea,
            effect_col=eff_col,
            p_col=p_col,
            p_floor=p_floor,
            fdr_max=fdr_max,
            abs_eff_min=abs_eff_min,
            dep_col=dep_col,
            dep_thresh=dep_thresh,
            ensg_sym=ensg_sym,
            gts_score_cfg=gts_score_cfg,
            symbol_uniprot=symbol_uniprot,
            string_set=str_set,
        )
        out_path = rr / out_rel.replace("/", os.sep)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tab.to_csv(out_path, sep="\t", index=False)
        print(f"Wrote {out_path} rows={len(tab)} tag={tag}")
        tc = tab.groupby("gts_evidence_tier").size().astype(int)
        gtc = (
            tab.groupby("glioma_target_tier").size().astype(int)
            if "glioma_target_tier" in tab.columns
            else pd.Series(dtype=int)
        )
        sum_row: dict[str, Any] = {
            "tag": tag,
            "output": rel_to_repo(rr, out_path),
            "input": rel_to_repo(rr, dea_path),
            "string_symbol_list_txt": str_rel or None,
            "n_rows": int(len(tab)),
            "has_m21_column": "outline_m21_high_confidence_screen" in dea.columns,
            "tier_counts": {str(k): int(v) for k, v in tc.items()},
            "glioma_target_tier_counts": {str(k): int(v) for k, v in gtc.items()},
            "glioma_target_score_top": float(tab["glioma_target_score"].iloc[0])
            if "glioma_target_score" in tab.columns and len(tab)
            else None,
        }
        if tag == "welch_depmap_outline":
            t1_rel = str(block.get("welch_tier1_output_tsv") or "").strip()
            if not t1_rel:
                t1_rel = "results/module7/glioma_target_tier1_welch.tsv"
            t1_path = rr / t1_rel.replace("/", os.sep)
            t1_path.parent.mkdir(parents=True, exist_ok=True)
            if "glioma_target_tier" in tab.columns:
                t1 = tab.loc[pd.to_numeric(tab["glioma_target_tier"], errors="coerce") == 1].copy()
            else:
                t1 = tab.iloc[0:0].copy()
            t1.to_csv(t1_path, sep="\t", index=False)
            print(f"Wrote {t1_path} rows={len(t1)} welch_tier1")
            sum_row["tier1_output"] = rel_to_repo(rr, t1_path)
            sum_row["n_tier1_rows"] = int(len(t1))
        summaries.append(sum_row)

    gts_strat_base = rr / "results/module7/gts_candidate_stratified"
    suf = str(block.get("stratified_output_suffix", "_gts_stub.tsv"))

    for sjob in sglobs:
        tag = str(sjob.get("job_tag", "stratified")).strip() or "stratified"
        glob_pat = str(sjob.get("glob_input", "")).strip()
        eff_col = str(sjob.get("effect_col", "delta_log2_expression"))
        p_col = str(sjob.get("p_col", "pvalue"))
        str_tpl = str(sjob.get("stratified_string_list_template") or "").strip()
        if not glob_pat:
            print(f"SKIP stratified job_tag={tag}: empty glob_input", file=sys.stderr)
            continue
        subdir = gts_strat_base / tag
        for path in sorted(rr.glob(glob_pat)):
            if not path.is_file() or "summary" in path.name.lower():
                continue
            if "_outline_drivers" in path.name:
                continue
            key = f"{tag}:{path.stem}"
            try:
                dea = pd.read_csv(path, sep="\t", low_memory=False)
                str_set: set[str] | None = None
                if str_tpl:
                    rel = str_tpl.replace("{stem}", path.stem)
                    str_set = load_string_symbol_set(rr / rel.replace("/", os.sep))
                tab = build_table(
                    dea,
                    effect_col=eff_col,
                    p_col=p_col,
                    p_floor=p_floor,
                    fdr_max=fdr_max,
                    abs_eff_min=abs_eff_min,
                    dep_col=dep_col,
                    dep_thresh=dep_thresh,
                    ensg_sym=ensg_sym,
                    gts_score_cfg=gts_score_cfg,
                    symbol_uniprot=symbol_uniprot,
                    string_set=str_set,
                )
            except (RuntimeError, ValueError) as e:
                print(f"SKIP {key}: {e}", file=sys.stderr)
                strat_summaries.append(
                    {
                        "job_tag": tag,
                        "input": rel_to_repo(rr, path),
                        "status": "skipped",
                        "reason": str(e),
                    }
                )
                continue
            out_name = f"{path.stem}{suf}" if suf.startswith("_") else f"{path.stem}_{suf}"
            out_path = subdir / out_name
            out_path.parent.mkdir(parents=True, exist_ok=True)
            tab.to_csv(out_path, sep="\t", index=False)
            print(f"Wrote {out_path} rows={len(tab)} stratified {key}")
            tc = tab.groupby("gts_evidence_tier").size().astype(int)
            strat_summaries.append(
                {
                    "job_tag": tag,
                    "input": rel_to_repo(rr, path),
                    "status": "ok",
                    "output": rel_to_repo(rr, out_path),
                    "stratified_string_list_template": str_tpl or None,
                    "n_rows": int(len(tab)),
                    "has_m21_column": "outline_m21_high_confidence_screen" in dea.columns,
                    "tier_counts": {str(k): int(v) for k, v in tc.items()},
                }
            )

    prov_path = rr / str(block.get("provenance_json", "results/module7/gts_candidate_stub_provenance.json")).replace(
        "/", os.sep
    )
    prov_path.parent.mkdir(parents=True, exist_ok=True)
    gts_path = rr / str(cfg.get("glioma_target_score_config") or "config/glioma_target_score.yaml").replace(
        "/", os.sep
    )
    doc = {
        "outline_module": 7,
        "stub": True,
        "metric": "gts_evidence_tier: 1 = (M21 or FDR+|effect|) + DepMap median <= threshold; 2 = M21/FDR+|effect|; 3 = FDR; 4 = other finite-p genes with symbol.",
        "gts_score": {
            "version": gts_score_cfg.get("version"),
            "enabled": bool(gts_score_cfg.get("enabled", True)),
            "config_path": rel_to_repo(rr, gts_path) if gts_path.is_file() else None,
            "formula": (
                "glioma_target_score = wE*E_norm + wM*M_norm + wD*D_norm + wN*N_norm; "
                "M_norm = m_dep*rank_pct(-depmap_CRISPR_median)+m_drv*I(known_driver); "
                "E_norm from |effect| and |signed_neglog10_p| ranks; "
                "D_norm = rank_pct(HGNC primary UniProt present); "
                "N_norm = rank_pct(in STRING export list for this engine). S/T weight 0."
            ),
            "weights": gts_score_cfg.get("weights"),
            "tier_thresholds": gts_score_cfg.get("tier_thresholds"),
        },
        "note_stratified": "Subtype tables inherit stratified DEA non-independence caveats.",
        "thresholds": {
            "fdr_max": fdr_max,
            "abs_effect_min": abs_eff_min,
            "depmap_dependency_at_or_below": dep_thresh,
            "depmap_column": dep_col,
            "pvalue_floor": p_floor,
        },
        "jobs": summaries,
        "stratified_jobs": strat_summaries,
    }
    prov_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"Wrote {prov_path}")

    flag_path = rr / str(block.get("done_flag", "results/module7/gts_candidate_stub.flag")).replace("/", os.sep)
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    flag_path.write_text("ok\n", encoding="utf-8")

    strat_flag_path = rr / str(
        block.get("stratified_done_flag", "results/module7/gts_stratified_candidate_stub.flag")
    ).replace("/", os.sep)
    strat_flag_path.parent.mkdir(parents=True, exist_ok=True)
    strat_flag_path.write_text("ok\n" if sglobs else "no_stratified_glob_jobs\n", encoding="utf-8")
    print(f"Wrote {strat_flag_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
