#!/usr/bin/env python3
"""
Outline M2.1: TOIL/Xena hub staging checklist (primary bulk TPM DEA upstream).

Reads m2_1_toil_xena_hub_paths_status.json, m1_outline_integration_stub.json, and Welch DEA provenance when present.

Config: config/m2_1_toil_xena_hub_outline_inputs.yaml — m2_1_toil_xena_hub_integration_stub
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
    p = repo_root() / "config" / "m2_1_toil_xena_hub_outline_inputs.yaml"
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


def _both_canonical_gz(g_primary: dict[str, Any]) -> bool:
    phen = tpm = False
    for c in g_primary.get("checks") or []:
        if not c.get("exists"):
            continue
        pl = str(c.get("path", "")).replace("\\", "/").lower()
        if "phenotype" in pl and pl.endswith(".gz"):
            phen = True
        if "rsem_gene_tpm" in pl and pl.endswith(".gz"):
            tpm = True
    return phen and tpm


def main() -> int:
    rr = repo_root()
    doc = load_cfg()
    block = doc.get("m2_1_toil_xena_hub_integration_stub") or {}
    if not block.get("enabled", True):
        print("m2_1_toil_xena_hub_integration_stub disabled")
        return 0

    paths_doc = _read_json(rr, "results/module3/m2_1_toil_xena_hub_paths_status.json") or {}
    m1_stub = _read_json(rr, "results/module3/m1_outline_integration_stub.json")
    welch_prov = _read_json(rr, "results/module3/dea_gbm_vs_gtex_brain_provenance.json")

    blockers: list[str] = []
    if not paths_doc:
        blockers.append(
            "Missing results/module3/m2_1_toil_xena_hub_paths_status.json (run m2_1_toil_xena_hub_paths_status)"
        )

    g_primary = _group(paths_doc, "toil_xena_primary_gtex_hub") or {}
    g_supp = _group(paths_doc, "toil_hub_supplementary_staging") or {}

    both_gz_ok = _both_canonical_gz(g_primary)
    n_primary = _n_ok(g_primary)
    supp_ok = _n_ok(g_supp) > 0
    in_repo_welch = welch_prov is not None

    readiness_tier = "D"
    if both_gz_ok:
        readiness_tier = "B"
    elif n_primary > 0 or supp_ok:
        readiness_tier = "C"
    elif in_repo_welch:
        readiness_tier = "C"
    elif m1_stub:
        readiness_tier = "C"

    m1_echo: dict[str, Any] = {}
    if m1_stub:
        m1_echo = {
            "readiness_tier": m1_stub.get("readiness_tier"),
            "artifact_kind": m1_stub.get("artifact_kind"),
        }

    payload = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_section": "M2.1",
        "artifact_kind": "m2_1_toil_xena_hub_integration_stub",
        "note": "Checklist only; fetch hub files via download_all_required.py or Xena browser.",
        "paths_status_echo": {
            "toil_xena_primary_gtex_hub": {"n_existing": n_primary, "n_checks": int(g_primary.get("n_checks") or 0)},
            "toil_hub_supplementary_staging": {"n_existing": _n_ok(g_supp), "n_checks": int(g_supp.get("n_checks") or 0)},
            "data_root": paths_doc.get("data_root"),
        },
        "both_canonical_hub_gz_present": both_gz_ok,
        "in_repo_welch_dea_provenance": in_repo_welch,
        "m1_outline_stub_echo": m1_echo,
        "readiness_tier": readiness_tier,
        "tier_legend": {
            "B": "Both TcgaTargetGTEX_phenotype and TcgaTargetGtex_rsem_gene_tpm .gz files on disk.",
            "C": "Partial hub staging, in-repo Welch DEA provenance only, or M1 outline stub echo.",
            "D": "No hub paths and no Welch provenance or M1 echo.",
        },
        "checklist": {
            "toil_xena_directory_or_files_staged": n_primary > 0,
            "supplementary_manifest_or_extract_staging": supp_ok,
        },
        "blockers": blockers,
        "recommended_next_steps": [
            "Mirror files under data_root/gtex/xena_toil exactly as in config/data_sources.yaml gtex_xena_toil.",
            "After download, run extract_toil_gbm_brain_tpm.py + DEA rules; Welch provenance JSON confirms end-to-end use.",
        ],
    }

    out_rel = str(block.get("output_json", "results/module3/m2_1_toil_xena_hub_integration_stub.json"))
    flag_rel = str(block.get("done_flag", "results/module3/m2_1_toil_xena_hub_integration_stub.flag"))
    out_path = rr / out_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} tier={readiness_tier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
