#!/usr/bin/env python3
"""
Inventory Module 7 GTS stub artifacts (global + stratified tables, flags, provenance).

Config: config/module7_inputs.yaml — module7_export_manifest
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

import manifest_optional


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_m7_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module7_inputs.yaml"
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
    cfg = load_m7_cfg()
    block = cfg.get("module7_export_manifest") or {}
    if not block.get("enabled", True):
        print("module7_export_manifest disabled")
        return 0

    out_path = rr / str(block.get("output_json", "results/module7/module7_export_manifest.json")).replace("/", os.sep)
    artifacts: list[dict[str, Any]] = []

    for rel, tag in (
        ("results/module7/gts_validation_integration_stub.json", "gts_validation.integration_stub"),
        ("results/module7/gts_validation_integration_stub.flag", "gts_validation.integration_stub.flag"),
        ("results/module7/m7_validation_paths_status.json", "m7_validation_paths_status"),
        ("results/module7/m7_validation_paths_status.flag", "m7_validation_paths_status.flag"),
        ("results/module7/m7_validation_integration_stub.json", "m7_validation_integration_stub"),
        ("results/module7/m7_validation_integration_stub.flag", "m7_validation_integration_stub.flag"),
        ("results/module7/m7_gts_external_score_mirror_paths_status.json", "m7_gts_external_score_mirror_paths_status"),
        ("results/module7/m7_gts_external_score_mirror_paths_status.flag", "m7_gts_external_score_mirror_paths_status.flag"),
        ("results/module7/m7_gts_external_score_mirror_integration_stub.json", "m7_gts_external_score_mirror_integration_stub"),
        ("results/module7/m7_gts_external_score_mirror_integration_stub.flag", "m7_gts_external_score_mirror_integration_stub.flag"),
        ("results/module7/gts_candidate_stub_provenance.json", "gts_stub.provenance"),
        ("results/module7/gts_candidate_stub.flag", "gts_stub.flag"),
        ("results/module7/gts_stratified_candidate_stub.flag", "gts_stub.stratified.flag"),
    ):
        artifacts.append(describe_path(rr, rel, tag=tag))

    prov_p = rr / "results/module7/gts_candidate_stub_provenance.json"
    if prov_p.is_file():
        prov = json.loads(prov_p.read_text(encoding="utf-8"))
        for job in prov.get("jobs") or []:
            rel = job.get("output")
            if rel:
                ex: dict[str, Any] = {
                    "input": job.get("input"),
                    "n_rows": job.get("n_rows"),
                    "tier_counts": job.get("tier_counts"),
                }
                if job.get("tier1_output") is not None:
                    ex["tier1_output"] = job.get("tier1_output")
                if job.get("n_tier1_rows") is not None:
                    ex["n_tier1_rows"] = job.get("n_tier1_rows")
                artifacts.append(
                    describe_path(
                        rr,
                        rel,
                        tag=f"gts_stub:{job.get('tag', '')}",
                        extra=ex,
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
                        tag=f"gts_stub.stratified:{sj.get('job_tag', '')}",
                        extra={"input": sj.get("input"), "n_rows": sj.get("n_rows"), "tier_counts": sj.get("tier_counts")},
                    )
                )

    base = rr / "results/module7/gts_candidate_stratified"
    if base.is_dir():
        for p in sorted(base.rglob("*.tsv")):
            try:
                rel = p.resolve().relative_to(rr.resolve()).as_posix()
            except ValueError:
                rel = str(p.as_posix())
            if any(a.get("path_posix") == rel for a in artifacts):
                continue
            artifacts.append(describe_path(rr, rel, tag="gts_stub.stratified.unlisted"))

    for rel, tag in (
        ("results/module7/glioma_target_results_uhd.png", "viz.composite_png"),
        ("results/module7/glioma_target_results_uhd.pdf", "viz.composite_pdf"),
        ("results/module7/glioma_target_visualization.flag", "viz.flag"),
        ("results/module7/glioma_target_results_report.docx", "m7.docx_report"),
        ("results/module7/glioma_target_deliverables.flag", "m7.deliverables.flag"),
    ):
        artifacts.append(describe_path(rr, rel, tag=tag))

    panel_root = rr / "results/module7/glioma_target_panels"
    if panel_root.is_dir():
        for p in sorted(panel_root.glob("*.png")):
            try:
                rel = p.resolve().relative_to(rr.resolve()).as_posix()
            except ValueError:
                rel = str(p.as_posix())
            artifacts.append(describe_path(rr, rel, tag="viz.panel"))

    manifest_optional.apply_optional_tags_to_artifacts(artifacts, block.get("optional_tags") or [])

    doc = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 7,
        "artifacts": artifacts,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} ({len(artifacts)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
