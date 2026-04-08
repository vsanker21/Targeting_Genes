#!/usr/bin/env python3
"""
Outline M7: external validation / benchmark staging gap checklist (no metrics).

Reads m7_validation_paths_status.json and echoes gts_validation_integration_stub when present.

Config: config/m7_validation_outline_inputs.yaml — m7_validation_integration_stub
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
    p = repo_root() / "config" / "m7_validation_outline_inputs.yaml"
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


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("m7_validation_integration_stub") or {}
    if not block.get("enabled", True):
        print("m7_validation_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module7/m7_validation_paths_status.json") or {}
    gts_val = _read_json(rr, "results/module7/gts_validation_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append("Missing results/module7/m7_validation_paths_status.json (run m7_validation_paths_status)")

    ex = _group(paths_doc, "external_expression_holdout") or {}
    out_labs = _group(paths_doc, "external_outcome_labels") or {}
    bench = _group(paths_doc, "benchmark_reference_topn") or {}
    repro = _group(paths_doc, "reproducibility_manifests") or {}

    def n_ok(g: dict[str, Any]) -> int:
        return int(g.get("n_existing") or 0)

    ex_ok = n_ok(ex) > 0
    out_ok = n_ok(out_labs) > 0
    bench_ok = n_ok(bench) > 0
    repro_ok = n_ok(repro) > 0
    n_groups_hit = sum(1 for x in (ex_ok, out_ok, bench_ok, repro_ok) if x)

    readiness_tier = "D"
    if ex_ok and out_ok:
        readiness_tier = "B"
    elif n_groups_hit >= 2:
        readiness_tier = "B"
    elif n_groups_hit == 1:
        readiness_tier = "C"
    elif paths_doc.get("groups"):
        readiness_tier = "D"
    if gts_val and readiness_tier == "D":
        readiness_tier = "C"

    checklist: dict[str, Any] = {
        "external_expression_holdout_staged": ex_ok,
        "external_outcome_labels_staged": out_ok,
        "benchmark_reference_lists_staged": bench_ok,
        "reproducibility_manifests_staged": repro_ok,
        "held_out_dea_disjoint_from_training": False,
        "automated_benchmark_diff_or_auc": False,
        "prospective_trial_data_linked": False,
        "note": "Pair staging paths with gts_validation_integration_stub recommended_next_steps before claiming validated tiers.",
    }

    echo: dict[str, Any] = {}
    if gts_val:
        echo = {
            "readiness_tier": gts_val.get("readiness_tier"),
            "artifact_kind": gts_val.get("artifact_kind"),
        }

    doc_out = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 7,
        "artifact_kind": "m7_validation_integration_stub",
        "note": "Checklist only; no survival analysis, ROC, or benchmark regression execution.",
        "paths_status_echo": {
            "external_expression_holdout": {"n_existing": n_ok(ex), "n_checks": int(ex.get("n_checks") or 0)},
            "external_outcome_labels": {"n_existing": n_ok(out_labs), "n_checks": int(out_labs.get("n_checks") or 0)},
            "benchmark_reference_topn": {"n_existing": n_ok(bench), "n_checks": int(bench.get("n_checks") or 0)},
            "reproducibility_manifests": {"n_existing": n_ok(repro), "n_checks": int(repro.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "gts_validation_stub_echo": echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Expression holdout and outcome labels both staged, or two or more other validation dimensions staged.",
            "C": "One staging dimension, or only in-repo GTS validation stub without external paths.",
            "D": "No validation staging paths and no GTS validation stub echo.",
        },
        "checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": [
            "Ensure external matrices use disjoint samples from TCGA-GBM DEA used for GTS stub training context.",
            "Version-pin benchmark reference lists and add a small Snakemake or pytest diff when GLIOMA_TARGET_BENCHMARK_STRICT=1.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module7/m7_validation_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module7/m7_validation_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc_out, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
