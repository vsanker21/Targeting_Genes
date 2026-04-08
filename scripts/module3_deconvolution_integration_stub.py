#!/usr/bin/env python3
"""
Outline M3: spatial deconvolution + cell-state DE staging gap checklist.

Reads m3_deconvolution_paths_status.json and echoes scrna_spatial_integration_stub when present.
Optionally echoes provenance from real NNLS / RCTD / Cell2location runs when those JSON files exist.

Config: config/m3_deconvolution_outline_inputs.yaml — m3_deconvolution_integration_stub
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "m3_deconvolution_outline_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _read_json(rr: Path, rel: str) -> dict[str, Any] | None:
    p = rr / rel.replace("/", os.sep)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _group(paths_doc: dict[str, Any], gid: str) -> dict[str, Any] | None:
    for g in paths_doc.get("groups") or []:
        if str(g.get("id")) == gid:
            return g
    return None


def cell2location_provenance_useful(c2l: dict[str, Any] | None) -> bool:
    """True when Cell2location orchestrator left a successful validate-only or trained run."""
    if not c2l:
        return False
    return str(c2l.get("status", "")).lower() in ("inputs_ok", "trained_ok")


def cell2location_provenance_trained(c2l: dict[str, Any] | None) -> bool:
    return bool(c2l and str(c2l.get("status", "")).lower() == "trained_ok")


def cell2location_training_output_paths_in_provenance(c2l: dict[str, Any] | None) -> bool:
    """True when ``trained_ok`` and provenance lists non-empty ``training.output_*`` paths."""
    if not cell2location_provenance_trained(c2l):
        return False
    tr = c2l.get("training")
    if not isinstance(tr, dict):
        return False
    h5 = str(tr.get("output_result_h5ad") or "").strip()
    tsv = str(tr.get("output_abundance_tsv") or "").strip()
    return bool(h5) and bool(tsv)


def cell2location_has_signature_extract_diagnostic(c2l: dict[str, Any] | None) -> bool:
    """True when orchestrator recorded ``signature_extract_diagnostic`` (training layout hint)."""
    if not c2l:
        return False
    d = c2l.get("signature_extract_diagnostic")
    return isinstance(d, dict) and bool(d)


def cell2location_has_gene_intersection_diagnostic(c2l: dict[str, Any] | None) -> bool:
    """True when orchestrator recorded ``gene_intersection_diagnostic`` (spatial vs signature overlap)."""
    if not c2l:
        return False
    d = c2l.get("gene_intersection_diagnostic")
    if not isinstance(d, dict):
        return False
    return any(k in d for k in ("n_shared_genes", "min_shared_genes_required"))


def rctd_provenance_present(rctd: dict[str, Any] | None) -> bool:
    return bool(rctd)


def rctd_rds_loads_ok(rctd: dict[str, Any] | None) -> bool:
    if not rctd:
        return False
    return bool(rctd.get("ref_load_ok")) and bool(rctd.get("spatial_load_ok"))


def rctd_create_succeeded(rctd: dict[str, Any] | None) -> bool:
    """True when ``create.RCTD`` succeeded (prefers ``status: ok`` when present)."""
    if not rctd:
        return False
    if "status" in rctd:
        return str(rctd.get("status", "")).strip().lower() == "ok"
    return rctd.get("rctd_create_ok") is True


def _cell2location_signature_diagnostic_followup_lines(c2l: dict[str, Any]) -> list[str]:
    """One-line summary of signature_extract_diagnostic (full dict stays in provenance JSON)."""
    diag = c2l.get("signature_extract_diagnostic")
    if not isinstance(diag, dict) or not diag:
        return []
    varm = diag.get("varm_keys")
    varm_list = varm if isinstance(varm, list) else []
    varm_show = [str(x) for x in varm_list[:10]]
    varm_tail = " …" if len(varm_list) > len(varm_show) else ""
    varm_s = ", ".join(varm_show) + varm_tail

    uns_mod = diag.get("uns_mod_keys")
    uns_list = uns_mod if isinstance(uns_mod, list) else []
    uns_show = [str(x) for x in uns_list[:8]]
    uns_tail = " …" if len(uns_list) > len(uns_show) else ""
    uns_s = ", ".join(uns_show) + uns_tail

    means_prev = diag.get("var_prefix_means")
    n_means = len(means_prev) if isinstance(means_prev, list) else 0
    top_fn = diag.get("uns_top_factor_keys")
    top_s = ", ".join(str(x) for x in top_fn) if isinstance(top_fn, list) else ""

    return [
        "m3_deconvolution_cell2location: provenance.signature_extract_diagnostic — "
        f"varm_keys [{varm_s or '—'}]; uns['mod'] keys [{uns_s or '—'}]; "
        f"uns factor keys {top_s or '—'}; means_per_cluster var cols (preview, up to 25): {n_means}. "
        "See full snapshot in cell2location_run_provenance.json."
    ]


def _cell2location_gene_intersection_diagnostic_followup_lines(c2l: dict[str, Any]) -> list[str]:
    d = c2l.get("gene_intersection_diagnostic")
    if not isinstance(d, dict):
        return []
    if not any(k in d for k in ("n_shared_genes", "min_shared_genes_required")):
        return []
    n_sh = d.get("n_shared_genes")
    n_req = d.get("min_shared_genes_required")
    n_sp = d.get("n_spatial_var")
    n_sig = d.get("n_signature_rows")
    return [
        "m3_deconvolution_cell2location: provenance.gene_intersection_diagnostic — "
        f"n_shared_genes={n_sh}, min_shared_genes_required={n_req}, "
        f"n_spatial_var={n_sp}, n_signature_rows={n_sig}. "
        "Align spatial and reference var_names (e.g. symbol harmonization) or adjust training.min_shared_genes."
    ]


def cell2location_followup_messages(c2l: dict[str, Any] | None) -> list[str]:
    """Hints when Cell2location provenance shows a failed or incomplete training attempt."""
    if not c2l:
        return []
    st = str(c2l.get("status", "")).strip().lower()
    if st == "training_failed":
        err = str(c2l.get("training_error") or c2l.get("cell2location_import_error") or "").strip()
        base = (
            "m3_deconvolution_cell2location: training or import failed; use snakemake --use-conda with "
            "workflow/envs/m3_cell2location.yaml, verify training.reference_labels_key and h5ad layers, "
            "and read training_error / cell2location_import_error in cell2location_run_provenance.json."
        )
        if err and len(err) < 220:
            first = f"{base} Detail: {err}"
        else:
            first = base
        return (
            [first]
            + _cell2location_signature_diagnostic_followup_lines(c2l)
            + _cell2location_gene_intersection_diagnostic_followup_lines(c2l)
        )
    want = bool(c2l.get("training_enabled"))
    imp_ok = c2l.get("cell2location_import_ok")
    if want and st == "inputs_ok" and imp_ok is True:
        return [
            "m3_deconvolution_cell2location: training was enabled but status is still inputs_ok (training "
            "may have exited early); inspect cell2location_run_provenance.json and re-run with snakemake --use-conda.",
        ]
    return []


def rctd_followup_messages(rctd: dict[str, Any] | None) -> list[str]:
    """Actionable strings when RDS loaded but the hook did not reach ``status: ok``."""
    if not rctd or not rctd_rds_loads_ok(rctd) or rctd_create_succeeded(rctd):
        return []
    st = str(rctd.get("status", "")).strip().lower()
    if st == "spacexr_missing":
        return [
            "m3_deconvolution_rctd: spacexr is not installed; install it in the m3_rctd conda env "
            "(see workflow/envs/m3_rctd.yaml and note in rctd_run_provenance.json).",
        ]
    if st == "create_failed":
        return [
            "m3_deconvolution_rctd: spacexr create.RCTD failed; inspect rctd_error in "
            "rctd_run_provenance.json and validate RDS object types.",
        ]
    return [
        "m3_deconvolution_rctd: both RDS objects load but create.RCTD did not succeed; install spacexr "
        "in the m3_rctd conda env (see workflow/envs/m3_rctd.yaml) or inspect rctd_error / note in "
        "rctd_run_provenance.json.",
    ]


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("m3_deconvolution_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_deconvolution_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_deconvolution_paths_status.json") or {}
    scrna = _read_json(rr, "results/module3/scrna_spatial_integration_stub.json")
    s2 = _read_json(rr, "results/module3/m3_deconvolution_s2/deconvolution_s2_provenance.json")
    rctd = _read_json(rr, "results/module3/m3_deconvolution_rctd/rctd_run_provenance.json")
    c2l = _read_json(rr, "results/module3/m3_deconvolution_cell2location/cell2location_run_provenance.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append("Missing results/module3/m3_deconvolution_paths_status.json (run m3_deconvolution_paths_status)")

    ref_atlas = _group(paths_doc, "single_cell_reference_atlas") or {}
    spatial_in = _group(paths_doc, "spatial_transcriptomics_inputs") or {}
    deconv_out = _group(paths_doc, "deconvolution_method_outputs") or {}
    pseudobulk = _group(paths_doc, "pseudobulk_cell_state_de") or {}

    def n_ok(g: dict[str, Any]) -> int:
        return int(g.get("n_existing") or 0)

    ref_ok = n_ok(ref_atlas) > 0
    spat_ok = n_ok(spatial_in) > 0
    dec_ok = n_ok(deconv_out) > 0
    pseudo_ok = n_ok(pseudobulk) > 0
    n_groups_hit = sum(1 for x in (ref_ok, spat_ok, dec_ok, pseudo_ok) if x)

    readiness_tier = "D"
    if dec_ok and (ref_ok or spat_ok):
        readiness_tier = "B"
    elif n_groups_hit >= 2:
        readiness_tier = "B"
    elif n_groups_hit == 1:
        readiness_tier = "C"
    elif paths_doc.get("groups"):
        readiness_tier = "D"
    if scrna and readiness_tier == "D":
        readiness_tier = "C"
    s2_ok = bool(s2 and str(s2.get("status", "")).lower() == "ok")
    if s2_ok and readiness_tier == "C":
        readiness_tier = "B"
    rctd_staged = bool(rctd)
    # Any non-empty Cell2location provenance JSON (including training_failed) counts for checklist.
    c2l_staged = bool(c2l)
    c2l_trained = cell2location_provenance_trained(c2l)
    if c2l_trained and readiness_tier == "C":
        readiness_tier = "B"

    echo: dict[str, Any] = {}
    if scrna:
        echo = {
            "readiness_tier": scrna.get("readiness_tier"),
            "artifact_kind": scrna.get("artifact_kind"),
        }

    checklist: dict[str, Any] = {
        "single_cell_reference_atlas_staged": ref_ok,
        "spatial_transcriptomics_inputs_staged": spat_ok,
        "deconvolution_outputs_staged": dec_ok,
        "pseudobulk_cell_state_de_staged": pseudo_ok,
        "in_repo_cell2location_or_rctd": bool(rctd_staged or c2l_staged),
        "in_repo_cell2location_trained": c2l_trained,
        "cell2location_training_outputs_in_provenance": cell2location_training_output_paths_in_provenance(c2l),
        "cell2location_has_signature_extract_diagnostic": cell2location_has_signature_extract_diagnostic(c2l),
        "cell2location_has_gene_intersection_diagnostic": cell2location_has_gene_intersection_diagnostic(c2l),
        "cell2location_run_status": str((c2l or {}).get("status") or "").strip(),
        "rctd_provenance_present": rctd_provenance_present(rctd),
        "rctd_rds_loaded": rctd_rds_loads_ok(rctd),
        "rctd_create_ok": rctd_create_succeeded(rctd),
        "rctd_run_status": str((rctd or {}).get("status") or "").strip(),
        "in_repo_harmony_integration": False,
        "in_repo_s2_nnls_spatial_deconvolution": s2_ok,
        "note": "Use module3_public_inputs_status + sc_workflow_paths_status for raw data roots; this stub tracks deconvolution-ready staging.",
    }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_deconvolution_integration_stub",
        "note": "Checklist only; heavy deconvolution runs are optional Snakemake rules with real data under data_root.",
        "paths_status_echo": {
            "single_cell_reference_atlas": {"n_existing": n_ok(ref_atlas), "n_checks": int(ref_atlas.get("n_checks") or 0)},
            "spatial_transcriptomics_inputs": {"n_existing": n_ok(spatial_in), "n_checks": int(spatial_in.get("n_checks") or 0)},
            "deconvolution_method_outputs": {"n_existing": n_ok(deconv_out), "n_checks": int(deconv_out.get("n_checks") or 0)},
            "pseudobulk_cell_state_de": {"n_existing": n_ok(pseudobulk), "n_checks": int(pseudobulk.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "scrna_spatial_stub_echo": echo,
        "m3_deconvolution_s2_nnls_echo": (
            {
                "artifact_kind": s2.get("artifact_kind"),
                "method": s2.get("method"),
                "n_spots": s2.get("n_spots"),
            }
            if s2_ok
            else {}
        ),
        "m3_deconvolution_rctd_echo": rctd or {},
        "m3_deconvolution_cell2location_echo": c2l or {},
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Deconvolution output staging plus reference or spatial inputs, or two or more dimensions staged.",
            "C": "One staging dimension, or only scRNA/spatial integration stub without deconv paths.",
            "D": "No deconvolution staging paths and no stub echo.",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Align reference h5ad cell types with Visium spot coordinates under a shared sample_id map before external Cell2location/RCTD.",
            "Export pseudobulk DE from Seurat/Scanpy externally and stage TSVs for cross-check with bulk M2.1 DEA.",
        ]
        + (
            [
                "m3_deconvolution_s2_nnls is a scipy baseline; for production use rule m3_deconvolution_rctd_run or m3_deconvolution_cell2location_run with staged RDS/h5ad.",
            ]
            if s2_ok
            else []
        )
        + rctd_followup_messages(rctd)
        + cell2location_followup_messages(c2l),
    }

    out_rel = str(block.get("output_json", "results/module3/m3_deconvolution_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m3_deconvolution_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
