#!/usr/bin/env python3
"""
Outline M2.3 immune or TME signature mirror checklist (no deconvolution or immune scoring).

Reads m2_3_immune_tme_mirror_paths_status.json and m2_movics_integration_stub.json.

Config: config/m2_3_immune_tme_mirror_outline_inputs.yaml (m2_3_immune_tme_mirror_integration_stub).
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
    p = repo_root() / "config" / "m2_3_immune_tme_mirror_outline_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8-sig"))


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


def _n_ok(g: dict[str, Any]) -> int:
    return int(g.get("n_existing") or 0)


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("m2_3_immune_tme_mirror_integration_stub") or {}
    if not block.get("enabled", True):
        print("m2_3_immune_tme_mirror_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m2_3_immune_tme_mirror_paths_status.json") or {}
    movics_stub = _read_json(rr, "results/module3/m2_movics_integration_stub.json")
    verhaak = rr / "results" / "module3" / "tcga_gbm_verhaak_subtype_summary.json"
    verhaak_ok = verhaak.is_file()

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m2_3_immune_tme_mirror_paths_status.json (run m2_3_immune_tme_mirror_paths_status)"
        )

    g_sig = _group(paths_doc, "immune_gene_signature_staging") or {}
    g_tme = _group(paths_doc, "tme_deconv_reference_staging") or {}

    sig_ok = _n_ok(g_sig) > 0
    tme_ok = _n_ok(g_tme) > 0

    readiness_tier = "D"
    if sig_ok and tme_ok:
        readiness_tier = "B"
    elif sig_ok or tme_ok:
        readiness_tier = "C"
    elif movics_stub or verhaak_ok:
        readiness_tier = "C"

    movics_echo: dict[str, Any] = {}
    if movics_stub:
        movics_echo = {
            "readiness_tier": movics_stub.get("readiness_tier"),
            "artifact_kind": movics_stub.get("artifact_kind"),
        }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_section": "M2.3",
        "artifact_kind": "m2_3_immune_tme_mirror_integration_stub",
        "note": "Checklist only; layer signatures onto bulk or pseudo-bulk DEA externally after staging GMT or TSV under data_root/immune_oncology/.",
        "paths_status_echo": {
            "immune_gene_signature_staging": {"n_existing": _n_ok(g_sig), "n_checks": int(g_sig.get("n_checks") or 0)},
            "tme_deconv_reference_staging": {"n_existing": _n_ok(g_tme), "n_checks": int(g_tme.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "in_repo_verhaak_subtype_summary_present": verhaak_ok,
        "m2_movics_integration_stub_echo": movics_echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Both immune signature staging and TME reference or external deconv output trees show at least one path.",
            "C": "One mirror dimension, in-repo Verhaak subtype summary, or MOVICS integration stub only.",
            "D": "No mirror paths and no Verhaak summary or MOVICS stub echo.",
        },
        "checklist": {
            "immune_gene_signatures_staged": sig_ok,
            "tme_reference_or_deconv_outputs_staged": tme_ok,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Mirror MSigDB immune C7 subsets or custom GMTs under gene_signature_sets.",
            "Run CIBERSORTx or MCP-counter externally and stage outputs under external_deconv_output_staging for comparison to Verhaak strata.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m2_3_immune_tme_mirror_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m2_3_immune_tme_mirror_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
