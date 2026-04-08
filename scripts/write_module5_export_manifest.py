#!/usr/bin/env python3
"""
Inventory Module 5 artifacts (path checks, LINCS Entrez signatures, flags).

Reads config/module5_inputs.yaml and lincs_disease_signature_provenance.json when present.

Config: module5_inputs.yaml — module5_export_manifest
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

import manifest_optional


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_m5_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module5_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def describe_path(rr: Path, rel: str | None, *, tag: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"tag": tag, "path": rel}
    if not rel:
        out["exists"] = False
        return out
    p = rr / str(rel).replace("/", os.sep)
    out["path_posix"] = str(Path(rel).as_posix())
    if not p.is_file():
        out["exists"] = False
        out["size_bytes"] = None
        return out
    st = p.stat()
    out["exists"] = True
    out["size_bytes"] = int(st.st_size)
    out["mtime_utc"] = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
    if p.suffix.lower() in (".tsv", ".txt", ".json"):
        try:
            with p.open("rb") as f:
                out["n_newlines"] = sum(1 for _ in f)
        except OSError:
            out["n_newlines"] = None
    if extra:
        out.update(extra)
    return out


def main() -> int:
    rr = repo_root()
    cfg = load_m5_cfg()
    block = cfg.get("module5_export_manifest") or {}
    if not block.get("enabled", True):
        print("module5_export_manifest disabled")
        return 0

    out_path = rr / str(block.get("output_json", "results/module5/module5_export_manifest.json")).replace("/", os.sep)
    artifacts: list[dict[str, Any]] = []

    dp = "results/module5/module5_data_paths_status.json"
    artifacts.append(describe_path(rr, dp, tag="module5.data_paths_status"))

    for rel, tag in (
        ("results/module5/cmap_tooling_scan.json", "module5.cmap_tooling_scan"),
        ("results/module5/cmap_tooling_scan.flag", "module5.cmap_tooling_scan.flag"),
        ("results/module5/lincs_connectivity_readiness.json", "module5.lincs_connectivity_readiness"),
        ("results/module5/lincs_connectivity_readiness.flag", "module5.lincs_connectivity_readiness.flag"),
        ("results/module5/lincs_signature_pack.json", "module5.lincs_signature_pack"),
        ("results/module5/lincs_signature_pack.flag", "module5.lincs_signature_pack.flag"),
        ("results/module5/srges_integration_stub.json", "module5.srges_integration_stub"),
        ("results/module5/srges_integration_stub.flag", "module5.srges_integration_stub.flag"),
        ("results/module5/m5_modality_paths_status.json", "module5.m5_modality_paths_status"),
        ("results/module5/m5_modality_paths_status.flag", "module5.m5_modality_paths_status.flag"),
        ("results/module5/m5_modality_integration_stub.json", "module5.m5_modality_integration_stub"),
        ("results/module5/m5_modality_integration_stub.flag", "module5.m5_modality_integration_stub.flag"),
        ("results/module5/m5_l1000_data_paths_status.json", "module5.m5_l1000_data_paths_status"),
        ("results/module5/m5_l1000_data_paths_status.flag", "module5.m5_l1000_data_paths_status.flag"),
        ("results/module5/m5_l1000_data_integration_stub.json", "module5.m5_l1000_data_integration_stub"),
        ("results/module5/m5_l1000_data_integration_stub.flag", "module5.m5_l1000_data_integration_stub.flag"),
        ("results/module5/m5_srges_output_paths_status.json", "module5.m5_srges_output_paths_status"),
        ("results/module5/m5_srges_output_paths_status.flag", "module5.m5_srges_output_paths_status.flag"),
        ("results/module5/m5_srges_output_integration_stub.json", "module5.m5_srges_output_integration_stub"),
        ("results/module5/m5_srges_output_integration_stub.flag", "module5.m5_srges_output_integration_stub.flag"),
        ("results/module5/m5_lincs_connectivity_mirror_paths_status.json", "module5.m5_lincs_connectivity_mirror_paths_status"),
        ("results/module5/m5_lincs_connectivity_mirror_paths_status.flag", "module5.m5_lincs_connectivity_mirror_paths_status.flag"),
        ("results/module5/m5_lincs_connectivity_mirror_integration_stub.json", "module5.m5_lincs_connectivity_mirror_integration_stub"),
        ("results/module5/m5_lincs_connectivity_mirror_integration_stub.flag", "module5.m5_lincs_connectivity_mirror_integration_stub.flag"),
        ("results/module5/lincs_disease_signature_provenance.json", "lincs_signature.provenance"),
        ("results/module5/lincs_disease_signature.flag", "lincs_signature.flag"),
        ("results/module5/lincs_stratified_signature.flag", "lincs_stratified_signature.flag"),
    ):
        artifacts.append(describe_path(rr, rel, tag=tag))

    prov_p = rr / "results/module5/lincs_disease_signature_provenance.json"
    if prov_p.is_file():
        prov = json.loads(prov_p.read_text(encoding="utf-8"))
        for job in prov.get("jobs") or []:
            rel = job.get("output")
            if rel:
                artifacts.append(
                    describe_path(
                        rr,
                        rel,
                        tag=f"lincs_signature:{job.get('tag', '')}",
                        extra={"input": job.get("input"), "n_entrez_unique": job.get("n_entrez_unique")},
                    )
                )
        for sj in prov.get("stratified_jobs") or []:
            if sj.get("status") != "ok":
                continue
            rel = sj.get("output")
            if rel:
                artifacts.append(
                    describe_path(
                        rr,
                        rel,
                        tag=f"lincs_signature.stratified:{sj.get('job_tag', '')}",
                        extra={"input": sj.get("input"), "n_entrez_unique": sj.get("n_entrez_unique")},
                    )
                )

    base = rr / "results/module5/lincs_disease_signature" / "stratified"
    if base.is_dir():
        for p in sorted(base.rglob("*.tsv")):
            try:
                rel = p.resolve().relative_to(rr.resolve()).as_posix()
            except ValueError:
                rel = str(p.as_posix())
            if any(a.get("path_posix") == rel for a in artifacts):
                continue
            artifacts.append(describe_path(rr, rel, tag="lincs_signature.stratified.unlisted"))

    manifest_optional.apply_optional_tags_to_artifacts(artifacts, block.get("optional_tags") or [])

    doc = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 5,
        "artifacts": artifacts,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} ({len(artifacts)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
