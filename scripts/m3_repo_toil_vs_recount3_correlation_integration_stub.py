#!/usr/bin/env python3
"""
Outline M3: cross-assay correlation checklist vs TOIL Welch/OLS and recount3 bulk-DEA repo stubs.

Config: config/m3_repo_toil_vs_recount3_correlation_outline_inputs.yaml — m3_repo_toil_vs_recount3_correlation_integration_stub
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
    p = repo_root() / "config" / "m3_repo_toil_vs_recount3_correlation_outline_inputs.yaml"
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
    block = doc.get("m3_repo_toil_vs_recount3_correlation_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_toil_vs_recount3_correlation_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_repo_toil_vs_recount3_correlation_paths_status.json") or {}
    wel_stub = _read_json(rr, "results/module3/m3_repo_bulk_welch_ols_dea_integration_stub.json")
    r3_stub = _read_json(rr, "results/module3/m3_repo_recount3_bulk_dea_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_repo_toil_vs_recount3_correlation_paths_status.json "
            "(run m3_repo_toil_vs_recount3_correlation_paths_status)"
        )

    g = _group(paths_doc, "toil_vs_recount3_cross_assay_outputs")
    n_ok = _n_ok(g)
    n_chk = int(g.get("n_checks") or 0)
    ch: list[dict[str, Any]] = list(g.get("checks") or [])

    wel_t = _tier_letter(wel_stub)
    r3_t = _tier_letter(r3_stub)
    parent_signal = (wel_t and wel_t != "D") or (r3_t and r3_t != "D")

    readiness_tier = "D"
    if n_ok >= 2:
        readiness_tier = "B"
    elif n_ok >= 1:
        readiness_tier = "C"
    elif parent_signal:
        readiness_tier = "C"

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_repo_toil_vs_recount3_correlation_integration_stub",
        "note": "Downstream of m2_toil_welch_vs_recount3_bulk_effect_correlation; planning cross-check vs repo bulk DEA stubs.",
        "paths_status_echo": {
            "toil_vs_recount3_cross_assay_outputs": {"n_existing": n_ok, "n_checks": n_chk},
            "repo_root": paths_doc.get("repo_root"),
        },
        "m3_repo_bulk_welch_ols_dea_stub_echo": {"readiness_tier": wel_t, "artifact_kind": wel_stub.get("artifact_kind") if wel_stub else None},
        "m3_repo_recount3_bulk_dea_stub_echo": {"readiness_tier": r3_t, "artifact_kind": r3_stub.get("artifact_kind") if r3_stub else None},
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Cross-assay correlation JSON and recount3 PyDESeq2 vs edgeR concordance JSON both present.",
            "C": "One of the tracked JSONs exists, or parent Welch/OLS vs recount3 repo stubs show partial readiness.",
            "D": "No tracked JSONs and no signal from parent bulk-DEA integration stubs.",
        },
        "checklist": {
            "toil_vs_recount3_correlation_json": bool(len(ch) > 0 and ch[0].get("exists")),
            "recount3_pydeseq2_edger_concordance_json": bool(len(ch) > 1 and ch[1].get("exists")),
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Run m2_toil_welch_vs_recount3_bulk_effect_correlation after TOIL and recount3 DEA TSVs exist (scipy).",
            "Run m2_recount3_deseq2_edger_concordance if deseq2 and edgeR results TSVs exist.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m3_repo_toil_vs_recount3_correlation_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m3_repo_toil_vs_recount3_correlation_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
