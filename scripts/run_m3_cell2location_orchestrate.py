#!/usr/bin/env python3
"""
Cell2location orchestrator: validate h5ad inputs; optional full training (config-driven).

When ``training.enabled`` is true in config/m3_deconvolution_cell2location_inputs.yaml:
  1. Optional ``training.harmonize_var_names`` (strip version suffix / uppercase) on both AnnData objects.
  2. RegressionModel on reference scRNA (signatures per label).
  3. Intersect genes with spatial AnnData.
  4. Cell2location spatial model + export_posterior.
  5. Write result h5ad + mean abundance TSV under results/.

After ``RegressionModel.export_posterior``, training failures may record ``signature_extract_diagnostic`` /
``signature_extract_error`` or ``gene_intersection_diagnostic`` in ``cell2location_run_provenance.json``;
``module3_deconvolution_integration_stub`` surfaces checklist flags and follow-up text for those cases.

Spatial mapping API: https://cell2location.readthedocs.io/en/latest/cell2location.html  
Regression / signatures tutorial: https://cell2location.readthedocs.io/en/latest/notebooks/cell2location_tutorial.html
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
import re
from pathlib import Path
from typing import Any

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def cell2location_config_path() -> Path:
    """Path to YAML for this run (``GLIOMA_TARGET_M3_CELL2LOCATION_CONFIG`` or default under ``config/``)."""
    rr = repo_root()
    alt = os.environ.get("GLIOMA_TARGET_M3_CELL2LOCATION_CONFIG", "").strip()
    if not alt:
        return rr / "config" / "m3_deconvolution_cell2location_inputs.yaml"
    p = Path(alt)
    return p.resolve() if p.is_absolute() else (rr / p).resolve()


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def _train_block(blk: dict[str, Any]) -> dict[str, Any]:
    return blk.get("training") or {}


def _ensure_batch_column(adata: Any, batch_key: str | None) -> tuple[Any, str]:
    """Return (adata, batch_key). Adds a dummy batch if batch_key is None."""
    if batch_key:
        if batch_key not in adata.obs.columns:
            raise SystemExit(f"reference_batch_key {batch_key!r} not in reference AnnData.obs")
        return adata, batch_key
    adata = adata.copy()
    adata.obs["_c2l_batch"] = "batch0"
    return adata, "_c2l_batch"


def _coerce_name_sequence(val: Any) -> list[str] | None:
    if val is None:
        return None
    if hasattr(val, "tolist"):
        val = val.tolist()
    if isinstance(val, (list, tuple)):
        out = [str(x) for x in val]
        return out if out else None
    return None


def _mod_factor_names(adata_ref: Any) -> list[str] | None:
    """Cell-type / factor labels from ``uns['mod']`` or top-level ``uns`` (scvi/cell2location variants)."""
    mod_rec = adata_ref.uns.get("mod")
    if isinstance(mod_rec, dict):
        for key in ("factor_names", "factor_names_"):
            out = _coerce_name_sequence(mod_rec.get(key))
            if out:
                return out
    for top_key in ("factor_names", "regressor_factor_names"):
        out = _coerce_name_sequence(adata_ref.uns.get(top_key))
        if out:
            return out
    return None


def _varm_to_dense_df(
    adata_ref: Any, key: str, factor_names: list[str]
) -> Any:
    """varm[key] -> DataFrame (genes × K), with optional transpose if stored as (K, genes)."""
    import numpy as np
    import pandas as pd

    mat = adata_ref.varm[key]
    if hasattr(mat, "toarray"):
        mat = mat.toarray()
    if hasattr(mat, "A"):
        mat = mat.A
    arr = np.asarray(mat, dtype=float)
    if arr.ndim != 2:
        raise RuntimeError(f"varm[{key!r}] is not 2D (shape={arr.shape}).")
    n_genes = adata_ref.n_vars
    k = len(factor_names)
    if arr.shape[0] == n_genes and arr.shape[1] == k:
        pass
    elif arr.shape[0] == k and arr.shape[1] == n_genes:
        arr = arr.T
    else:
        raise RuntimeError(
            f"varm[{key!r}] shape {arr.shape} does not match n_vars={n_genes} and n_factors={k} "
            "(even after transpose)."
        )
    return pd.DataFrame(arr, index=adata_ref.var_names.astype(str), columns=factor_names)


def _infer_n_factors_from_varm(mat: Any, n_genes: int) -> int | None:
    import numpy as np

    m = mat.toarray() if hasattr(mat, "toarray") else mat
    arr = np.asarray(m, dtype=float)
    if arr.ndim != 2:
        return None
    if arr.shape[0] == n_genes:
        return int(arr.shape[1])
    if arr.shape[1] == n_genes:
        return int(arr.shape[0])
    return None


def _try_extract_q05_signatures(adata_ref: Any, factor_names: list[str] | None) -> Any:
    """Posterior q05 summaries in .var or .varm; returns DataFrame or None."""
    qpref = "q05_per_cluster_mu_fg_"
    if factor_names:
        qcols = [f"{qpref}{fn}" for fn in factor_names]
        if all(c in adata_ref.var.columns for c in qcols):
            df = adata_ref.var[qcols].copy()
            df.columns = factor_names
            return df
        by_suffix = {str(c)[len(qpref) :]: c for c in adata_ref.var.columns if str(c).startswith(qpref)}
        ordered = [by_suffix.get(fn) for fn in factor_names]
        if all(ordered):
            df = adata_ref.var[list(ordered)].copy()
            df.columns = factor_names
            return df
        pat_int = re.compile(r"^q05_per_cluster_mu_fg_(\d+)$")
        indexed: list[tuple[int, str]] = []
        for c in adata_ref.var.columns:
            m = pat_int.match(str(c))
            if m:
                indexed.append((int(m.group(1)), str(c)))
        indexed.sort(key=lambda x: x[0])
        if indexed and len(indexed) == len(factor_names):
            cols = [c for _, c in indexed]
            df = adata_ref.var[cols].copy()
            df.columns = factor_names
            return df
    else:
        pat_int = re.compile(r"^q05_per_cluster_mu_fg_(\d+)$")
        indexed = []
        for c in adata_ref.var.columns:
            m = pat_int.match(str(c))
            if m:
                indexed.append((int(m.group(1)), str(c)))
        indexed.sort(key=lambda x: x[0])
        if indexed:
            cols = [c for _, c in indexed]
            fn = [str(i) for i, _ in indexed]
            df = adata_ref.var[cols].copy()
            df.columns = fn
            return df
    qkey = "q05_per_cluster_mu_fg"
    if qkey in adata_ref.varm:
        fn = factor_names
        if not fn:
            k = _infer_n_factors_from_varm(adata_ref.varm[qkey], adata_ref.n_vars)
            if k is None:
                return None
            fn = [str(i) for i in range(k)]
        try:
            return _varm_to_dense_df(adata_ref, qkey, fn)
        except RuntimeError:
            pass
    for vk in sorted(adata_ref.varm.keys()):
        sk = str(vk)
        if sk == qkey or not sk.startswith("q05_per_cluster_mu_fg"):
            continue
        fn = factor_names
        if not fn:
            k = _infer_n_factors_from_varm(adata_ref.varm[vk], adata_ref.n_vars)
            if k is None:
                continue
            fn = [str(i) for i in range(k)]
        try:
            return _varm_to_dense_df(adata_ref, str(vk), fn)
        except RuntimeError:
            continue
    return None


_CANONICAL_MEANS_VARM_KEYS: frozenset[str] = frozenset(
    {"means_per_cluster_mu_fg", "means_per_cluster_mu_fg_f"}
)


def _extract_means_var_columns_without_factor_list(adata_ref: Any) -> Any:
    """Collect every ``means_per_cluster_mu_fg_*`` column when no factor-name list is available."""
    pref = "means_per_cluster_mu_fg_"
    pc_cols = [c for c in adata_ref.var.columns if str(c).startswith(pref)]
    if not pc_cols:
        return None
    pat_int = re.compile(r"^means_per_cluster_mu_fg_(\d+)$")
    indexed: list[tuple[int, str]] = []
    all_int = True
    for c in pc_cols:
        m = pat_int.match(str(c))
        if m:
            indexed.append((int(m.group(1)), str(c)))
        else:
            all_int = False
            break
    if all_int and indexed:
        indexed.sort(key=lambda x: x[0])
        cols = [c for _, c in indexed]
    else:
        cols = sorted(pc_cols, key=str)
    suf = [str(c)[len(pref) :] for c in cols]
    df = adata_ref.var[cols].copy()
    df.columns = suf
    return df


def _try_varm_means_extra_keys(adata_ref: Any, factor_names: list[str] | None) -> Any:
    """Non-canonical ``varm`` keys such as ``means_per_cluster_mu_fg_*`` suffix variants (arrays only)."""
    import pandas as pd

    if factor_names:
        return None
    for vk in sorted(adata_ref.varm.keys()):
        sk = str(vk)
        if not sk.startswith("means_per_cluster_mu_fg") or sk in _CANONICAL_MEANS_VARM_KEYS:
            continue
        val = adata_ref.varm[vk]
        if isinstance(val, pd.DataFrame):
            continue
        k = _infer_n_factors_from_varm(val, adata_ref.n_vars)
        if k is None:
            continue
        fn = [str(i) for i in range(k)]
        try:
            return _varm_to_dense_df(adata_ref, str(vk), fn)
        except RuntimeError:
            continue
    return None


def _try_varm_means_dataframe(adata_ref: Any, factor_names: list[str] | None) -> Any:
    """Some pipelines store a genes × K ``pandas.DataFrame`` in ``varm``."""
    import pandas as pd

    for vk in sorted(adata_ref.varm.keys()):
        val = adata_ref.varm[vk]
        if not isinstance(val, pd.DataFrame):
            continue
        if val.shape[0] != adata_ref.n_vars:
            continue
        sk = str(vk)
        if not (
            "means_per_cluster" in sk
            or "per_cluster_mu" in sk
            or "mu_fg" in sk
            or "regression" in sk.lower()
        ):
            continue
        if factor_names is not None and val.shape[1] == len(factor_names):
            out = val.copy()
            out.columns = factor_names
            out.index = adata_ref.var_names.astype(str)
            return out
        if not factor_names and val.shape[1] > 0:
            out = val.copy()
            out.index = adata_ref.var_names.astype(str)
            return out
    return None


def _try_uns_means_matrix(adata_ref: Any, factor_names: list[str] | None) -> Any:
    """Rare: posterior mean matrix stashed under ``uns`` (2D, one axis matches ``n_vars``)."""
    import numpy as np
    import pandas as pd

    for uk in sorted(adata_ref.uns.keys()):
        sk = str(uk)
        if "means_per_cluster_mu_fg" not in sk and "per_cluster_mu_fg" not in sk.lower():
            continue
        if sk == "mod" or sk.startswith("_scvi"):
            continue
        val = adata_ref.uns[uk]
        if isinstance(val, (dict, list, str, bytes)):
            continue
        try:
            arr = np.asarray(val, dtype=float)
        except (TypeError, ValueError):
            continue
        if arr.ndim != 2:
            continue
        n = adata_ref.n_vars
        if arr.shape[0] == n:
            kdim = arr.shape[1]
        elif arr.shape[1] == n:
            arr = arr.T
            kdim = arr.shape[1]
        else:
            continue
        fn = factor_names if factor_names is not None else [str(i) for i in range(kdim)]
        if len(fn) != kdim:
            continue
        return pd.DataFrame(arr, index=adata_ref.var_names.astype(str), columns=fn)
    return None


def _signature_extract_diagnostic_snapshot(adata_ref: Any) -> dict[str, Any]:
    """Structured hint for failures; keep JSON-serializable and bounded."""
    layer_keys: list[str] = []
    try:
        layer_keys = sorted(str(k) for k in adata_ref.layers.keys())
    except Exception:
        pass
    uns_guess = [
        str(k)
        for k in adata_ref.uns.keys()
        if isinstance(k, str)
        and (
            "per_cluster" in k.lower()
            or "means_per_cluster" in k
            or "mu_fg" in k.lower()
            or "regression" in k.lower()
        )
    ][:40]
    return {
        "uns_mod_keys": sorted((adata_ref.uns.get("mod") or {}).keys())
        if isinstance(adata_ref.uns.get("mod"), dict)
        else None,
        "uns_top_factor_keys": [k for k in ("factor_names", "regressor_factor_names") if k in adata_ref.uns],
        "var_prefix_means": [
            str(c) for c in adata_ref.var.columns if str(c).startswith("means_per_cluster")
        ][:25],
        "var_prefix_q05": [
            str(c) for c in adata_ref.var.columns if str(c).startswith("q05_per_cluster")
        ][:25],
        "varm_keys": sorted(str(k) for k in adata_ref.varm.keys()),
        "layer_keys_sample": layer_keys[:40],
        "uns_keys_per_cluster_guess": sorted(uns_guess),
    }


def _extract_signature_df(adata_ref: Any, *, prefer_q05: bool = False) -> Any:
    """
    Build ``cell_state_df`` (genes × cell types) after ``RegressionModel.export_posterior``.

    cell2location/scvi-tools versions differ: means may live in ``.var`` columns, ``.varm`` arrays,
    with factor names or integer suffixes. See:
    https://cell2location.readthedocs.io/en/latest/notebooks/cell2location_tutorial.html

    ``prefer_q05``: when True, try q05 summaries before means (config ``training.signature_summary: q05``).
    """
    factor_names = _mod_factor_names(adata_ref)
    pref = "means_per_cluster_mu_fg_"

    if prefer_q05:
        qdf = _try_extract_q05_signatures(adata_ref, factor_names)
        if qdf is not None:
            return qdf

    # --- A) .var columns: one column per factor name (exact match)
    if factor_names:
        cols = [f"{pref}{fn}" for fn in factor_names]
        if all(c in adata_ref.var.columns for c in cols):
            df = adata_ref.var[cols].copy()
            df.columns = factor_names
            return df

    # --- B) .var columns: map factor_names to any column whose suffix matches (sanitized names)
    if factor_names:
        by_suffix = {str(c)[len(pref) :]: c for c in adata_ref.var.columns if str(c).startswith(pref)}
        ordered = [by_suffix.get(fn) for fn in factor_names]
        if all(ordered):
            df = adata_ref.var[list(ordered)].copy()
            df.columns = factor_names
            return df

    # --- C) .var columns: integer suffix means_per_cluster_mu_fg_0, _1, ... in order
    if factor_names:
        pat = re.compile(r"^means_per_cluster_mu_fg_(\d+)$")
        indexed: list[tuple[int, str]] = []
        for c in adata_ref.var.columns:
            m = pat.match(str(c))
            if m:
                indexed.append((int(m.group(1)), str(c)))
        indexed.sort(key=lambda x: x[0])
        if indexed and len(indexed) == len(factor_names):
            cols = [c for _, c in indexed]
            df = adata_ref.var[cols].copy()
            df.columns = factor_names
            return df

    # --- C2) .var columns: all means_per_cluster_mu_fg_* when no factor list (numeric order or lex)
    if not factor_names:
        df_nf = _extract_means_var_columns_without_factor_list(adata_ref)
        if df_nf is not None:
            return df_nf

    # --- D) .varm: means_per_cluster_mu_fg (and transpose if needed)
    orig_fn = factor_names
    for vkey in ("means_per_cluster_mu_fg", "means_per_cluster_mu_fg_f"):
        if vkey not in adata_ref.varm:
            continue
        fn = orig_fn
        if not fn:
            k = _infer_n_factors_from_varm(adata_ref.varm[vkey], adata_ref.n_vars)
            if k is None:
                continue
            fn = [str(i) for i in range(k)]
        try:
            return _varm_to_dense_df(adata_ref, vkey, fn)
        except RuntimeError:
            continue

    # --- E) Any varm key starting with means_per_cluster_mu_fg (single matrix)
    if factor_names:
        for vk in sorted(adata_ref.varm.keys()):
            if str(vk).startswith("means_per_cluster_mu_fg"):
                try:
                    return _varm_to_dense_df(adata_ref, str(vk), factor_names)
                except RuntimeError:
                    continue

    # --- E2) Extra varm array keys (only without factor list; with list, E above covers all prefixes)
    df_x = _try_varm_means_extra_keys(adata_ref, factor_names)
    if df_x is not None:
        return df_x

    # --- E3) varm DataFrame (genes × K)
    df_vm = _try_varm_means_dataframe(adata_ref, factor_names)
    if df_vm is not None:
        return df_vm

    # --- E4) uns 2D matrix
    df_uns = _try_uns_means_matrix(adata_ref, factor_names)
    if df_uns is not None:
        return df_uns

    # --- F) Fallback: q05 posterior if means absent (still valid positive-ish signatures)
    qdf = _try_extract_q05_signatures(adata_ref, factor_names)
    if qdf is not None:
        return qdf

    tried = _signature_extract_diagnostic_snapshot(adata_ref)
    raise RuntimeError(
        "Could not extract RegressionModel signatures into a gene × cell-type DataFrame. "
        "Tried: .var columns means_per_cluster_mu_fg_*; .varm arrays (canonical and extra keys); "
        ".varm DataFrame (genes × K); uns 2D arrays whose key matches *per_cluster_mu_fg*; "
        "q05 analogs; uns['mod'] / uns['factor_names'] for column alignment. "
        f"Diagnostic snapshot: {json.dumps(tried, default=str)}"
    )


def _harmonize_var_names_adata(adata: Any, hb: dict[str, Any]) -> Any:
    """Copy adata with normalized ``var_names`` for cross-modal gene matching (e.g. Ensembl versions)."""
    if not hb.get("enabled"):
        return adata
    adata = adata.copy()
    names = [str(x) for x in adata.var_names.astype(str)]
    if hb.get("strip_version_suffix"):
        names = [n.split(".")[0] for n in names]
    if hb.get("uppercase"):
        names = [n.upper() for n in names]
    adata.var_names = names
    adata.var_names_make_unique()
    return adata


def _intersect_spatial_and_signatures(
    spat_adata: Any, sig_df: Any, *, min_shared_genes: int = 10
) -> tuple[Any, Any]:
    """Subset spatial AnnData and signature matrix to shared genes (spatial var order)."""
    sp_names = spat_adata.var_names.astype(str).tolist()
    sig_ix = set(sig_df.index.astype(str))
    shared = [g for g in sp_names if g in sig_ix]
    if len(shared) < min_shared_genes:
        raise RuntimeError(
            f"Too few shared genes between spatial and signatures ({len(shared)}); "
            f"need at least {min_shared_genes} (set training.min_shared_genes in config)."
        )
    spat_sub = spat_adata[:, shared].copy()
    sig_sub = sig_df.loc[shared].copy()
    return spat_sub, sig_sub


def _pick_abundance_obsm(adata_spatial: Any, n_cell_types: int) -> tuple[str, Any]:
    import numpy as np

    preferred = (
        "means_cell_abundance_w_sf",
        "q05_cell_abundance_w_sf",
        "q95_cell_abundance_w_sf",
        "means",
    )
    for name in preferred:
        if name not in adata_spatial.obsm:
            continue
        m = adata_spatial.obsm[name]
        arr = m.values if hasattr(m, "values") else m
        sh = np.asarray(arr).shape
        if len(sh) == 2 and sh[1] == n_cell_types:
            return name, m
    for k, m in adata_spatial.obsm.items():
        arr = m.values if hasattr(m, "values") else m
        sh = np.asarray(arr).shape
        if len(sh) == 2 and sh[1] == n_cell_types:
            return str(k), m
    keys = list(adata_spatial.obsm.keys())
    raise RuntimeError(
        f"No suitable cell abundance matrix in obsm (need 2D, {n_cell_types} columns). Keys: {keys}"
    )


def _run_training_path(
    *,
    rr: Path,
    ref: Any,
    spat: Any,
    blk: dict[str, Any],
    train_cfg: dict[str, Any],
    prov: dict[str, Any],
) -> int:
    import pandas as pd
    from cell2location.models import Cell2location, RegressionModel

    hb = train_cfg.get("harmonize_var_names") or {}
    if hb.get("enabled"):
        ref = _harmonize_var_names_adata(ref, hb)
        spat = _harmonize_var_names_adata(spat, hb)

    labels_key = train_cfg.get("reference_labels_key")
    if not labels_key:
        print("training.enabled requires reference_labels_key", file=sys.stderr)
        return 1
    if labels_key not in ref.obs.columns:
        print(f"reference_labels_key {labels_key!r} not in reference.obs", file=sys.stderr)
        return 1

    ref_layer = train_cfg.get("reference_counts_layer") or None
    spat_layer = train_cfg.get("spatial_counts_layer") or None
    ref_bkey_in = train_cfg.get("reference_batch_key") or None
    spat_bkey = train_cfg.get("spatial_batch_key") or None

    ref_work, batch_key = _ensure_batch_column(ref, ref_bkey_in)

    reg_epochs = int(train_cfg.get("regression_max_epochs", 250))
    reg_bs = int(train_cfg.get("regression_batch_size", 2500))
    reg_bs = max(1, min(reg_bs, ref_work.n_obs))
    reg_lr = float(train_cfg.get("regression_lr", 0.002))

    c2l_epochs = int(train_cfg.get("cell2location_max_epochs", 3000))
    c2l_bs = train_cfg.get("cell2location_batch_size")
    c2l_bs = int(c2l_bs) if c2l_bs is not None else None
    c2l_lr = float(train_cfg.get("cell2location_lr", 0.002))
    n_cells_loc = float(train_cfg.get("cell2location_N_cells_per_location", 8.0))
    det_alpha = float(train_cfg.get("cell2location_detection_alpha", 20.0))

    n_post = int(train_cfg.get("export_posterior_num_samples", 1000))
    post_bs = int(train_cfg.get("export_posterior_batch_size", 2048))
    use_gpu = bool(train_cfg.get("use_gpu", False))

    sample_kwargs = {"num_samples": n_post, "batch_size": post_bs, "use_gpu": use_gpu}

    sig_summary = str(train_cfg.get("signature_summary", "means")).strip().lower()
    prefer_q05 = sig_summary == "q05"
    min_shared = int(train_cfg.get("min_shared_genes", 25))
    if min_shared < 1:
        print("training.min_shared_genes must be >= 1", file=sys.stderr)
        return 1

    prov["training"] = {
        "reference_labels_key": labels_key,
        "reference_batch_key": batch_key,
        "reference_counts_layer": ref_layer,
        "spatial_counts_layer": spat_layer,
        "signature_summary": sig_summary,
        "regression_max_epochs": reg_epochs,
        "cell2location_max_epochs": c2l_epochs,
        "cell2location_N_cells_per_location": n_cells_loc,
        "cell2location_detection_alpha": det_alpha,
        "use_gpu": use_gpu,
    }
    if hb.get("enabled"):
        prov["training"]["harmonize_var_names"] = {
            k: v for k, v in hb.items() if k in ("enabled", "strip_version_suffix", "uppercase")
        }

    RegressionModel.setup_anndata(
        adata=ref_work,
        layer=ref_layer,
        batch_key=batch_key,
        labels_key=labels_key,
    )
    mod_reg = RegressionModel(ref_work)
    mod_reg.train(max_epochs=reg_epochs, batch_size=reg_bs, train_size=1.0, lr=reg_lr)
    ref_work = mod_reg.export_posterior(ref_work, sample_kwargs=sample_kwargs)

    try:
        inf_aver = _extract_signature_df(ref_work, prefer_q05=prefer_q05)
    except RuntimeError as e:
        prov["signature_extract_diagnostic"] = _signature_extract_diagnostic_snapshot(ref_work)
        prov["signature_extract_error"] = str(e)
        raise
    try:
        spat_sub, inf_aver = _intersect_spatial_and_signatures(
            spat, inf_aver, min_shared_genes=min_shared
        )
    except RuntimeError:
        sp_names = {str(x) for x in spat.var_names.astype(str)}
        sig_ix = {str(x) for x in inf_aver.index.astype(str)}
        prov["gene_intersection_diagnostic"] = {
            "n_spatial_var": int(spat.n_vars),
            "n_signature_rows": int(inf_aver.shape[0]),
            "n_shared_genes": len(sp_names & sig_ix),
            "min_shared_genes_required": int(min_shared),
        }
        raise
    prov["training"]["n_genes_shared"] = int(spat_sub.n_vars)
    prov["training"]["n_cell_types"] = int(inf_aver.shape[1])

    Cell2location.setup_anndata(
        adata=spat_sub,
        layer=spat_layer,
        batch_key=spat_bkey,
    )
    mod_sp = Cell2location(
        spat_sub,
        inf_aver,
        N_cells_per_location=n_cells_loc,
        detection_alpha=det_alpha,
    )
    train_kw: dict[str, Any] = {
        "max_epochs": c2l_epochs,
        "train_size": 1.0,
        "lr": c2l_lr,
    }
    if c2l_bs is not None:
        train_kw["batch_size"] = c2l_bs
    mod_sp.train(**train_kw)
    spat_out = mod_sp.export_posterior(spat_sub, sample_kwargs=sample_kwargs)

    obsm_key, abund = _pick_abundance_obsm(spat_out, inf_aver.shape[1])
    prov["training"]["abundance_obsm_key"] = obsm_key

    out_h5ad_rel = blk.get("output_result_h5ad", "results/module3/m3_deconvolution_cell2location/spatial_cell2location.h5ad")
    out_tsv_rel = blk.get(
        "output_abundance_tsv",
        "results/module3/m3_deconvolution_cell2location/spot_cell_abundance_means.tsv",
    )
    out_h5ad = rr / str(out_h5ad_rel).replace("/", os.sep)
    out_tsv = rr / str(out_tsv_rel).replace("/", os.sep)
    out_h5ad.parent.mkdir(parents=True, exist_ok=True)
    spat_out.write_h5ad(out_h5ad)

    df = abund.copy() if hasattr(abund, "copy") else pd.DataFrame(abund)
    df.index = spat_out.obs_names.astype(str)
    df.columns = list(inf_aver.columns)
    df.to_csv(out_tsv, sep="\t")

    prov["training"]["output_result_h5ad"] = str(out_h5ad).replace(os.sep, "/")
    prov["training"]["output_abundance_tsv"] = str(out_tsv).replace(os.sep, "/")
    prov["status"] = "trained_ok"
    return 0


def _cell2location_provenance_json(prov: dict[str, Any]) -> str:
    """Serialize provenance for ``cell2location_run_provenance.json`` (``default=str`` for numpy, etc.)."""
    return json.dumps(prov, indent=2, default=str)


def _unlink_cell2location_success_flag(out: Path) -> None:
    """Drop ``cell2location_run.flag`` so a failed run does not leave a stale Snakemake success marker."""
    p = out / "cell2location_run.flag"
    try:
        p.unlink(missing_ok=True)
    except OSError:
        pass


def _cell2location_stderr_flag_hint(out: Path) -> None:
    """Match RCTD orchestrator UX: point at provenance JSON and flag semantics."""
    print(
        "m3_cell2location: see "
        f"{out / 'cell2location_run_provenance.json'} for status; "
        "cell2location_run.flag is written only when the script exits 0.",
        file=sys.stderr,
    )


def main() -> int:
    rr = repo_root()
    dr = data_root()
    cfg_p = cell2location_config_path()
    if not cfg_p.is_file():
        print(f"Cell2location config not found: {cfg_p}", file=sys.stderr)
        return 1
    doc = yaml.safe_load(cfg_p.read_text(encoding="utf-8"))
    blk = doc.get("m3_deconvolution_cell2location") or {}
    ref_rel = blk.get("reference_h5ad")
    spat_rel = blk.get("spatial_h5ad")
    if not ref_rel or not spat_rel:
        print(
            f"{cfg_p}: m3_deconvolution_cell2location.reference_h5ad and spatial_h5ad required",
            file=sys.stderr,
        )
        return 1
    ref_p = dr / str(ref_rel).replace("/", os.sep)
    spat_p = dr / str(spat_rel).replace("/", os.sep)
    if not ref_p.is_file():
        print(f"Missing reference h5ad under data_root: {ref_p}", file=sys.stderr)
        return 1
    if not spat_p.is_file():
        print(f"Missing spatial h5ad under data_root: {spat_p}", file=sys.stderr)
        return 1

    try:
        import anndata as ad
    except ImportError as e:
        print(f"anndata required: {e}", file=sys.stderr)
        return 1

    ref = ad.read_h5ad(ref_p)
    spat = ad.read_h5ad(spat_p)
    train_cfg = _train_block(blk)
    want_train = bool(train_cfg.get("enabled", False))

    prov: dict[str, Any] = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "status": "inputs_ok",
        "artifact_kind": "m3_deconvolution_cell2location_run",
        "reference_h5ad": str(ref_p),
        "spatial_h5ad": str(spat_p),
        "n_ref_obs": int(ref.n_obs),
        "n_spatial_obs": int(spat.n_obs),
        "training_enabled": want_train,
    }

    out = rr / "results" / "module3" / "m3_deconvolution_cell2location"
    out.mkdir(parents=True, exist_ok=True)

    try:
        import cell2location
    except ImportError as e:
        prov["cell2location_import_ok"] = False
        prov["cell2location_import_error"] = str(e)
        if want_train:
            prov["status"] = "training_failed"
            _unlink_cell2location_success_flag(out)
            (out / "cell2location_run_provenance.json").write_text(
                _cell2location_provenance_json(prov), encoding="utf-8"
            )
            print(f"cell2location required for training.enabled: {e}", file=sys.stderr)
            _cell2location_stderr_flag_hint(out)
            return 1
    else:
        prov["cell2location_import_ok"] = True
        prov["cell2location_version"] = getattr(cell2location, "__version__", "unknown")

    if want_train:
        try:
            rc = _run_training_path(rr=rr, ref=ref, spat=spat, blk=blk, train_cfg=train_cfg, prov=prov)
        except Exception as e:
            prov["status"] = "training_failed"
            prov["training_error"] = f"{type(e).__name__}: {e}"
            _unlink_cell2location_success_flag(out)
            (out / "cell2location_run_provenance.json").write_text(
                _cell2location_provenance_json(prov), encoding="utf-8"
            )
            print(f"Cell2location training failed: {e}", file=sys.stderr)
            _cell2location_stderr_flag_hint(out)
            return 1
        if rc != 0:
            prov["status"] = "training_failed"
            prov.setdefault("training_error", "RegressionModel/Cell2location path exited with non-zero code (see stderr).")
            _unlink_cell2location_success_flag(out)
            (out / "cell2location_run_provenance.json").write_text(
                _cell2location_provenance_json(prov), encoding="utf-8"
            )
            print(f"m3_cell2location: training path exited with code {rc}.", file=sys.stderr)
            _cell2location_stderr_flag_hint(out)
            return rc
    else:
        prov["note"] = (
            "Inputs validated only. Set m3_deconvolution_cell2location.training.enabled: true "
            "for RegressionModel + Cell2location (conda env workflow/envs/m3_cell2location.yaml)."
        )

    (out / "cell2location_run_provenance.json").write_text(_cell2location_provenance_json(prov), encoding="utf-8")
    (out / "cell2location_run.flag").write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out / 'cell2location_run_provenance.json'} status={prov.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
