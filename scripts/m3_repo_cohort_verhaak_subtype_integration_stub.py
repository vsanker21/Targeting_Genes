#!/usr/bin/env python3
"""
Outline M3: cohort + Verhaak subtype checklist vs TOIL TPM hub and bundled references stubs.

Config: config/m3_repo_cohort_verhaak_subtype_outline_inputs.yaml — m3_repo_cohort_verhaak_subtype_integration_stub
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
    p = repo_root() / "config" / "m3_repo_cohort_verhaak_subtype_outline_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8-sig"))


def _read_json(rr: Path, rel: str) -> dict[str, Any] | None:
    p = rr / rel.replace("/", os.sep)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _group(paths_doc: dict[str, Any], gid: str) -> dict[str, Any]:
    for g in paths_doc.get("groups") or []:
        if str(g.get("id")) == gid:
            return g
    return {}


def _n_ok(g: dict[str, Any]) -> int:
    return int(g.get("n_existing") or 0)


def _tier_letter(doc: dict[str, Any] | None) -> str | None:
    if not doc:
        return None
    t = doc.get("readiness_tier")
    return str(t) if t is not None else None


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("m3_repo_cohort_verhaak_subtype_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_cohort_verhaak_subtype_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_repo_cohort_verhaak_subtype_paths_status.json") or {}
    toil_hub = _read_json(rr, "results/module3/m3_repo_toil_bulk_expression_integration_stub.json")
    bundled = _read_json(rr, "results/module3/m3_repo_bundled_references_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_repo_cohort_verhaak_subtype_paths_status.json "
            "(run m3_repo_cohort_verhaak_subtype_paths_status)"
        )

    g = _group(paths_doc, "cohort_verhaak_subtype_repo_outputs")
    n_ok = _n_ok(g)
    n_chk = int(g.get("n_checks") or 0)
    ch: list[dict[str, Any]] = list(g.get("checks") or [])

    toil_t = _tier_letter(toil_hub)
    bnd_t = _tier_letter(bundled)
    parent_signal = (toil_t and toil_t != "D") or (bnd_t and bnd_t != "D")

    readiness_tier = "D"
    if n_ok >= 5:
        readiness_tier = "B"
    elif n_ok >= 3:
        readiness_tier = "C"
    elif parent_signal:
        readiness_tier = "C"

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_repo_cohort_verhaak_subtype_integration_stub",
        "note": "MSigDB Verhaak GMT under references/; TPM from TOIL hub slice; inputs to stratified DEA and MOVICS-style partitions.",
        "paths_status_echo": {
            "cohort_verhaak_subtype_repo_outputs": {"n_existing": n_ok, "n_checks": n_chk},
            "repo_root": paths_doc.get("repo_root"),
        },
        "m3_repo_toil_bulk_expression_stub_echo": {
            "readiness_tier": toil_t,
            "artifact_kind": toil_hub.get("artifact_kind") if toil_hub else None,
        },
        "m3_repo_bundled_references_stub_echo": {
            "readiness_tier": bnd_t,
            "artifact_kind": bundled.get("artifact_kind") if bundled else None,
        },
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Cohort summary, Verhaak scores and summary, and mean TPM-by-subtype TSV plus provenance all present.",
            "C": "At least three tracked artifacts, or TOIL hub / bundled references stub shows partial readiness.",
            "D": "Fewer than three artifacts and no parent TPM or references stub signal.",
        },
        "checklist": {
            "cohort_design_summary_json": bool(len(ch) > 0 and ch[0].get("exists")),
            "verhaak_subtype_scores_tsv": bool(len(ch) > 1 and ch[1].get("exists")),
            "verhaak_subtype_summary_json": bool(len(ch) > 2 and ch[2].get("exists")),
            "mean_log_tpm_by_subtype_tsv": bool(len(ch) > 3 and ch[3].get("exists")),
            "mean_log_tpm_by_subtype_provenance_json": bool(len(ch) > 4 and ch[4].get("exists")),
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Run expression_cohort_summary after results/module3/toil_gbm_vs_brain_tpm.parquet and samples TSV exist.",
            "Run m2_verhaak_subtypes after TPM table and references/verhaak_msigdb_c2_cgp_2024.1.Hs.gmt exist.",
            "Run m2_mean_expression_by_subtype after subtype scores TSV exists.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m3_repo_cohort_verhaak_subtype_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m3_repo_cohort_verhaak_subtype_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
