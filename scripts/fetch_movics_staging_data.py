#!/usr/bin/env python3
"""
Populate MOVICS / multi-omics staging paths under data_root (see config/m2_movics_inputs.yaml).

  1) DepMap (programmatic): GBM-related cell lines -> expression + CN + binary mutation matrices
     under {data_root}/omics/multi_omics_mae/  (requires prior download_all_required DepMap phase).
  2) CGGA (optional): HTTP GET each URL listed in config/m2_movics_data_fetch.yaml -> cohorts/cgga_expression/
  3) CBTTC: writes cohorts/cbttc/ACCESS_NOTES.md (controlled access; no open bulk URL here).

CGGA bulk files are portal-hosted; paste fresh links into m2_movics_data_fetch.yaml cgga_http when needed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

# Repo imports
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from depmap_shared import detect_gbm_models, latest_depmap_dir  # noqa: E402

try:
    from download_external_datasets import HTTP_TIMEOUT, USER_AGENT
except ImportError:
    USER_AGENT = "Mozilla/5.0 (compatible; GLIOMA-TARGET/1.0)"
    HTTP_TIMEOUT = 600


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def _http_get_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        dest.write_bytes(r.read())


def _find_col(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


EXPR_META_COLS = frozenset(
    {
        "Unnamed: 0",
        "SequencingID",
        "ModelID",
        "IsDefaultEntryForModel",
        "ModelConditionID",
        "IsDefaultEntryForMC",
    }
)


def _load_outline_driver_symbols(rr: Path, block: dict[str, Any]) -> list[str]:
    rel = str(block.get("mutation_outline_drivers_yaml") or "references/gbm_known_drivers_outline.yaml")
    p = rr / rel.replace("/", os.sep)
    if not p.is_file():
        return []
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    syms = doc.get("gene_symbols") or doc.get("symbols") or []
    return [str(s).strip() for s in syms if s and str(s).strip()]


def _gene_index_for_mae(
    variances: pd.Series,
    common_gene_universe: pd.Index,
    max_genes: int,
    block: dict[str, Any],
    rr: Path,
) -> pd.Index:
    """Rank genes: optional GBM outline drivers first, then expression variance (within expr∩CN universe)."""
    cap = min(int(max_genes), len(common_gene_universe))
    v = variances.reindex(common_gene_universe).fillna(0)
    if not block.get("prioritize_outline_drivers_in_gene_universe", True):
        return v.nlargest(cap).index
    drivers = [s for s in _load_outline_driver_symbols(rr, block) if s in common_gene_universe]
    dset = set(drivers)
    rest = v.index.difference(dset)
    rest_sorted = v.loc[rest].sort_values(ascending=False).index.tolist()
    top_list: list[str] = []
    for s in drivers:
        if s not in top_list:
            top_list.append(s)
        if len(top_list) >= cap:
            return pd.Index(top_list[:cap])
    for s in rest_sorted:
        if s not in top_list:
            top_list.append(s)
        if len(top_list) >= cap:
            break
    return pd.Index(top_list[:cap])


def _strip_depmap_gene_label(s: str) -> str:
    """TSPAN6 (7105) -> TSPAN6 for matching mutation HugoSymbol."""
    t = str(s).strip()
    if " (" in t and t.endswith(")"):
        return t.rsplit(" (", 1)[0].strip()
    return t


def _read_expression_models_by_genes(
    path: Path, gbm_set: set[str], chunksize: int = 200
) -> pd.DataFrame:
    """Rows = ModelID, columns = DepMap gene labels; one row per model (default entry only)."""
    chunks: list[pd.DataFrame] = []
    for chunk in pd.read_csv(path, chunksize=chunksize, low_memory=False):
        if "ModelID" not in chunk.columns:
            continue
        if "IsDefaultEntryForModel" in chunk.columns:
            d = chunk["IsDefaultEntryForModel"].astype(str).str.strip()
            chunk = chunk.loc[d.str.upper().isin(("YES", "TRUE", "1"))]
        sub = chunk.loc[chunk["ModelID"].astype(str).isin(gbm_set)]
        if sub.empty:
            continue
        gcols = [c for c in sub.columns if c not in EXPR_META_COLS]
        chunks.append(sub.set_index("ModelID")[gcols])
    if not chunks:
        return pd.DataFrame()
    out = pd.concat(chunks, axis=0)
    return out.groupby(out.index).mean(numeric_only=True)


def _read_cn_genes_by_models(path: Path, gbm_set: set[str], chunksize: int = 150) -> pd.DataFrame:
    """PortalOmicsCNGeneLog2: first column is ModelID (often 'Unnamed: 0'); rows = models, cols = genes."""
    chunks: list[pd.DataFrame] = []
    for chunk in pd.read_csv(path, chunksize=chunksize, low_memory=False):
        id_col = chunk.columns[0]
        chunk = chunk.rename(columns={id_col: "ModelID"})
        sub = chunk.loc[chunk["ModelID"].astype(str).isin(gbm_set)]
        if sub.empty:
            continue
        gcols = [c for c in sub.columns if c != "ModelID"]
        chunks.append(sub.set_index("ModelID")[gcols])
    if not chunks:
        return pd.DataFrame()
    out = pd.concat(chunks, axis=0)
    return out.groupby(out.index).mean(numeric_only=True)


def build_depmap_mae(dr: Path, block: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"status": "skipped", "component": "depmap_gbm_mae"}
    if not block.get("enabled", True):
        out["reason"] = "disabled_in_config"
        return out

    try:
        rel = latest_depmap_dir(dr)
    except FileNotFoundError as e:
        out["reason"] = str(e)
        return out

    model_csv = rel / "Model.csv"
    if not model_csv.is_file():
        out["reason"] = "missing_Model.csv"
        return out

    prim = str(block.get("oncotree_primary_substr", "Glioblastoma"))
    fb = block.get("oncotree_lineage_fallback")
    gbm = detect_gbm_models(model_csv, prim, str(fb) if fb else None)
    gbm_set = set(gbm)
    if not gbm_set:
        out["reason"] = "zero_gbm_models"
        return out

    expr_name = "OmicsExpressionTPMLogp1HumanProteinCodingGenes.csv"
    cn_name = "PortalOmicsCNGeneLog2.csv"
    mut_name = "OmicsSomaticMutations.csv"
    expr_p = rel / expr_name
    cn_p = rel / cn_name
    mut_p = rel / mut_name
    missing = [n for n, p in [(expr_name, expr_p), (cn_name, cn_p), (mut_name, mut_p)] if not p.is_file()]
    if missing:
        out["reason"] = f"missing_depmap_files:{','.join(missing)}"
        return out

    fnames = block.get("filenames") or {}
    out_rel = str(block.get("out_dir", "omics/multi_omics_mae"))
    mae_root = dr / out_rel.replace("/", os.sep)
    mae_root.mkdir(parents=True, exist_ok=True)

    max_genes = int(block.get("max_genes", 3000) or 3000)

    expr_models = _read_expression_models_by_genes(expr_p, gbm_set)
    if expr_models.empty:
        out["reason"] = "expression_empty_after_filter"
        return out
    expr_g = expr_models.T
    expr_g.index = [_strip_depmap_gene_label(str(x)) for x in expr_g.index]
    expr_g = expr_g.groupby(expr_g.index).mean(numeric_only=True)
    variances = expr_g.var(axis=1, numeric_only=True).fillna(0)

    cn_models = _read_cn_genes_by_models(cn_p, gbm_set)
    if cn_models.empty:
        out["reason"] = "cn_empty_after_filter"
        return out
    cn_g = cn_models.T
    cn_g.index = [_strip_depmap_gene_label(str(x)) for x in cn_g.index]
    cn_df = cn_g.groupby(cn_g.index).mean(numeric_only=True)
    common_gene_universe = expr_g.index.intersection(cn_df.index)
    common_models = expr_g.columns.intersection(cn_df.columns)
    if len(common_gene_universe) < 50 or len(common_models) < 3:
        out["reason"] = "insufficient_gene_or_model_overlap_expr_cn"
        out["n_genes"] = int(len(common_gene_universe))
        out["n_models"] = int(len(common_models))
        return out

    rr = repo_root()
    top_ix = _gene_index_for_mae(variances, common_gene_universe, max_genes, block, rr)
    expr_sub = expr_g.loc[top_ix, common_models]
    cn_sub = cn_df.loc[top_ix, common_models]
    common_genes = expr_sub.index

    sym_col = None
    for chunk in pd.read_csv(mut_p, chunksize=5000, low_memory=False):
        sym_col = _find_col(chunk, ("HugoSymbol", "Hugo_Symbol", "Gene", "gene_symbol"))
        mod_col = _find_col(chunk, ("ModelID", "model_id"))
        break
    if not sym_col:
        out["reason"] = "mutation_file_missing_gene_column"
        return out

    mut_chunks: list[pd.DataFrame] = []
    for chunk in pd.read_csv(mut_p, chunksize=50_000, low_memory=False):
        mod_col = _find_col(chunk, ("ModelID", "model_id"))
        if not mod_col:
            continue
        sub = chunk.loc[chunk[mod_col].astype(str).isin(gbm_set), [mod_col, sym_col]].copy()
        sub.columns = ["ModelID", "gene"]
        sub = sub.dropna()
        if not sub.empty:
            mut_chunks.append(sub)
    if not mut_chunks:
        mut_wide = pd.DataFrame(0, index=common_genes, columns=common_models)
    else:
        mut_long = pd.concat(mut_chunks, ignore_index=True)
        mut_long["gene"] = mut_long["gene"].astype(str)
        mut_long = mut_long[mut_long["gene"].isin(common_genes)]
        mut_long["hit"] = 1
        mut_wide = mut_long.pivot_table(
            index="gene",
            columns="ModelID",
            values="hit",
            aggfunc="max",
            fill_value=0,
        )
        mut_wide = mut_wide.reindex(index=common_genes).reindex(columns=common_models, fill_value=0)

    mut_filter_note: str | None = None
    if block.get("mutation_require_variable", True):
        n_mod = mut_wide.shape[1]
        row_sums = mut_wide.sum(axis=1)
        var_mask = (row_sums > 0) & (row_sums < n_mod)
        genes_var = mut_wide.index[var_mask]
        min_v = int(block.get("mutation_variable_min_genes", 50) or 50)
        if len(genes_var) >= min_v:
            expr_sub = expr_sub.loc[genes_var]
            cn_sub = cn_sub.loc[genes_var]
            mut_wide = mut_wide.loc[genes_var]
            mut_filter_note = f"mutation_rows_variable_across_models:{len(genes_var)}"
        else:
            mut_filter_note = (
                f"mutation_require_variable_relaxed(variable={len(genes_var)}<{min_v})"
            )

    exp_path = mae_root / str(fnames.get("expression_gz", "depmap_gbm_expression_logtpm.tsv.gz"))
    cn_path = mae_root / str(fnames.get("copy_number_gz", "depmap_gbm_cnv_log2.tsv.gz"))
    mut_path = mae_root / str(fnames.get("mutation_binary_gz", "depmap_gbm_mutation_binary.tsv.gz"))
    man_path = mae_root / str(fnames.get("sample_manifest", "depmap_gbm_sample_manifest.tsv"))

    expr_sub.to_csv(exp_path, sep="\t", compression="gzip")
    cn_sub.to_csv(cn_path, sep="\t", compression="gzip")
    mut_wide.fillna(0).astype(int).to_csv(mut_path, sep="\t", compression="gzip")

    pd.DataFrame({"ModelID": list(common_models), "cohort": "DepMap_GBM_related"}).to_csv(
        man_path, sep="\t", index=False
    )

    prov_path = mae_root / "depmap_mae_provenance.json"
    prov = {
        "status": "ok",
        "depmap_release_dir": str(rel),
        "n_models": int(len(common_models)),
        "n_genes": int(len(expr_sub.index)),
        "files": {
            "expression": str(exp_path.relative_to(dr)),
            "copy_number": str(cn_path.relative_to(dr)),
            "mutation_binary": str(mut_path.relative_to(dr)),
            "sample_manifest": str(man_path.relative_to(dr)),
        },
        "note": (
            "Rows=gene symbols (HGNC); columns=ModelID. MOVICS three-view IntNMF: snakemake m2_movics_intnmf_depmap_mae "
            "(Gaussian expr + CN after row-min shift + binomial mutation)."
        ),
    }
    if block.get("prioritize_outline_drivers_in_gene_universe", True):
        nd = len([s for s in _load_outline_driver_symbols(rr, block) if s in common_gene_universe])
        prov["outline_drivers_in_expr_cn_universe"] = int(nd)
        prov["prioritize_outline_drivers_in_gene_universe"] = True
    if mut_filter_note:
        prov["mutation_matrix_filter"] = mut_filter_note
    prov_path.write_text(json.dumps(prov, indent=2), encoding="utf-8")

    return {
        "status": "ok",
        "component": "depmap_gbm_mae",
        "n_models": int(len(common_models)),
        "n_genes": int(len(expr_sub.index)),
        "depmap_release": rel.name,
    }


def fetch_cgga(dr: Path, items: list[Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"status": "ok", "component": "cgga_http", "downloads": []}
    base = dr / "cohorts" / "cgga_expression"
    if not items:
        out["status"] = "skipped"
        out["reason"] = "no_urls_in_config_add_to_m2_movics_data_fetch.yaml"
        return out
    base.mkdir(parents=True, exist_ok=True)
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "") or "").strip()
        fname = str(item.get("filename", "") or "").strip() or "download.bin"
        name = str(item.get("name", fname))
        if not url:
            continue
        dest = base / fname
        try:
            _http_get_file(url, dest)
            out["downloads"].append({"name": name, "path": str(dest), "url": url, "bytes": dest.stat().st_size})
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
            out["downloads"].append({"name": name, "url": url, "error": str(e)})
            out["status"] = "partial_or_failed"
    return out


def write_cbttc_readme(dr: Path, block: dict[str, Any]) -> dict[str, Any]:
    if not block.get("write_readme", True):
        return {"status": "skipped", "component": "cbttc"}
    fn = str(block.get("readme_filename", "ACCESS_NOTES.md"))
    d = dr / "cohorts" / "cbttc"
    d.mkdir(parents=True, exist_ok=True)
    text = """# CBTTC / Pediatric brain tumor data (manual / controlled)

Open bulk download is not wired in this repository. Typical access paths:

- **Pediatric Brain Tumor Atlas** / **CBTTC** via institutional access or portal registration.
- Study-specific **dbGaP** or **Kids First** manifests where applicable.

After you obtain files, place expression / copy-number / mutation tables under this directory
(or subfolders) and point a custom MOVICS config or R script at those paths.

See also: config/m2_movics_inputs.yaml (path check `cohorts/cbttc`).
"""
    (d / fn).write_text(text, encoding="utf-8")
    return {"status": "ok", "component": "cbttc", "path": str(d / fn)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--skip-depmap",
        action="store_true",
        help="Skip DepMap-derived multi_omics_mae matrices.",
    )
    ap.add_argument("--skip-cgga", action="store_true", help="Skip configured CGGA HTTP downloads.")
    ap.add_argument("--skip-cbttc", action="store_true", help="Skip CBTTC README scaffold.")
    args = ap.parse_args()

    rr = repo_root()
    dr = data_root()
    cfg_path = rr / "config" / "m2_movics_data_fetch.yaml"
    if not cfg_path.is_file():
        print(f"Missing {cfg_path}", file=sys.stderr)
        return 1
    doc = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))

    report: dict[str, Any] = {"data_root": str(dr.resolve()), "components": []}

    if not args.skip_depmap:
        report["components"].append(build_depmap_mae(dr, doc.get("depmap_gbm_mae") or {}))

    if not args.skip_cgga:
        report["components"].append(fetch_cgga(dr, list(doc.get("cgga_http") or [])))

    if not args.skip_cbttc:
        report["components"].append(write_cbttc_readme(dr, doc.get("cbttc") or {}))

    out_path = rr / "results" / "module3" / "movics_staging_fetch_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Wrote {out_path}")

    bad = [c for c in report["components"] if c.get("status") not in ("ok", "skipped")]
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
