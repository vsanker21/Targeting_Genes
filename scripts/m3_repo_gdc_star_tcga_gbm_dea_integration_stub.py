#!/usr/bin/env python3
"""
Outline M3: GDC STAR TCGA-GBM DEA provenance checklist vs in-repo GDC matrix and STAR pairing stubs.

Config: config/m3_repo_gdc_star_tcga_gbm_dea_outline_inputs.yaml — m3_repo_gdc_star_tcga_gbm_dea_integration_stub
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
    p = repo_root() / "config" / "m3_repo_gdc_star_tcga_gbm_dea_outline_inputs.yaml"
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
    block = doc.get("m3_repo_gdc_star_tcga_gbm_dea_integration_stub") or {}
    if not block.get("enabled", True):
        print("m3_repo_gdc_star_tcga_gbm_dea_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m3_repo_gdc_star_tcga_gbm_dea_paths_status.json") or {}
    gdc_repo = _read_json(rr, "results/module3/m3_repo_gdc_expression_matrix_integration_stub.json")
    star_pair = _read_json(rr, "results/module3/m2_1_star_pairing_integration_stub.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m3_repo_gdc_star_tcga_gbm_dea_paths_status.json "
            "(run m3_repo_gdc_star_tcga_gbm_dea_paths_status)"
        )

    g = _group(paths_doc, "gdc_star_tcga_gbm_dea_provenance_outputs")
    n_ok = _n_ok(g)
    n_chk = int(g.get("n_checks") or 0)
    ch: list[dict[str, Any]] = list(g.get("checks") or [])

    gdc_t = _tier_letter(gdc_repo)
    sp_t = _tier_letter(star_pair)
    parent_signal = (gdc_t and gdc_t != "D") or (sp_t and sp_t != "D")

    readiness_tier = "D"
    if n_chk > 0 and n_ok >= n_chk:
        readiness_tier = "B"
    elif n_ok >= 2 or parent_signal:
        readiness_tier = "C"

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 3,
        "artifact_kind": "m3_repo_gdc_star_tcga_gbm_dea_integration_stub",
        "note": "Within-TCGA contrasts on STAR unstranded counts; distinct from TOIL TPM bulk DEA and recount3.",
        "paths_status_echo": {
            "gdc_star_tcga_gbm_dea_provenance_outputs": {"n_existing": n_ok, "n_checks": n_chk},
            "repo_root": paths_doc.get("repo_root"),
        },
        "m3_repo_gdc_expression_matrix_stub_echo": {
            "readiness_tier": gdc_t,
            "artifact_kind": gdc_repo.get("artifact_kind") if gdc_repo else None,
        },
        "m2_1_star_pairing_stub_echo": {
            "readiness_tier": sp_t,
            "artifact_kind": star_pair.get("artifact_kind") if star_pair else None,
        },
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "All tracked GDC STAR DEA artifacts present (provenance JSONs and DEA TSVs for both contrasts).",
            "C": "At least two tracked artifacts, or GDC repo matrix / STAR pairing stub shows partial readiness.",
            "D": "Fewer than two JSONs and no parent stub signal.",
        },
        "checklist": {
            "deseq2_primary_vs_recurrent_provenance_json": bool(len(ch) > 0 and ch[0].get("exists")),
            "deseq2_primary_vs_solid_normal_provenance_json": bool(len(ch) > 1 and ch[1].get("exists")),
            "edger_primary_vs_recurrent_provenance_json": bool(len(ch) > 2 and ch[2].get("exists")),
            "edger_primary_vs_solid_normal_provenance_json": bool(len(ch) > 3 and ch[3].get("exists")),
            "deseq2_primary_vs_recurrent_results_tsv": bool(len(ch) > 4 and ch[4].get("exists")),
            "deseq2_primary_vs_solid_normal_results_tsv": bool(len(ch) > 5 and ch[5].get("exists")),
            "edger_primary_vs_recurrent_qlf_tsv": bool(len(ch) > 6 and ch[6].get("exists")),
            "edger_primary_vs_solid_normal_qlf_tsv": bool(len(ch) > 7 and ch[7].get("exists")),
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Run m2_deseq2_tcga_primary_recurrent and m2_deseq2_tcga_primary_vs_solid_normal after STAR counts parquet exists (pydeseq2).",
            "Run m2_edger_tcga_primary_recurrent and m2_edger_tcga_primary_vs_solid_normal with R/edgeR.",
        ],
    }

    out_rel = str(
        block.get("output_json", "results/module3/m3_repo_gdc_star_tcga_gbm_dea_integration_stub.json")
    )
    flag_rel = str(
        block.get("done_flag", "results/module3/m3_repo_gdc_star_tcga_gbm_dea_integration_stub.flag")
    )
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
