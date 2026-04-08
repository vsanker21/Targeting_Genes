#!/usr/bin/env python3
"""
Inventory Module 6 artifacts: structure-tool path checks + structure_druggability_bridge outputs.

Config: config/module6_inputs.yaml — module6_export_manifest
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


def load_m6_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module6_inputs.yaml"
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
    cfg = load_m6_cfg()
    block = cfg.get("module6_export_manifest") or {}
    if not block.get("enabled", True):
        print("module6_export_manifest disabled")
        return 0

    out_path = rr / str(block.get("output_json", "results/module6/module6_export_manifest.json")).replace("/", os.sep)
    tooling = cfg.get("structure_tooling_path_checks") or {}
    artifacts: list[dict[str, Any]] = []

    t_json = str(tooling.get("output_json", "results/module6/module6_structure_tooling_paths_status.json"))
    t_flag = str(tooling.get("done_flag", "results/module6/module6_structure_tooling_paths_status.flag"))
    artifacts.append(describe_path(rr, t_json, tag="module6.structure_tooling_paths_status"))
    artifacts.append(describe_path(rr, t_flag, tag="module6.structure_tooling_paths_status.flag"))

    for rel, tag in (
        ("results/module6/structure_admet_integration_stub.json", "module6.structure_admet_integration_stub"),
        ("results/module6/structure_admet_integration_stub.flag", "module6.structure_admet_integration_stub.flag"),
        ("results/module6/m6_toxicity_paths_status.json", "module6.m6_toxicity_paths_status"),
        ("results/module6/m6_toxicity_paths_status.flag", "module6.m6_toxicity_paths_status.flag"),
        ("results/module6/m6_toxicity_integration_stub.json", "module6.m6_toxicity_integration_stub"),
        ("results/module6/m6_toxicity_integration_stub.flag", "module6.m6_toxicity_integration_stub.flag"),
        ("results/module6/m6_docking_output_paths_status.json", "module6.m6_docking_output_paths_status"),
        ("results/module6/m6_docking_output_paths_status.flag", "module6.m6_docking_output_paths_status.flag"),
        ("results/module6/m6_docking_output_integration_stub.json", "module6.m6_docking_output_integration_stub"),
        ("results/module6/m6_docking_output_integration_stub.flag", "module6.m6_docking_output_integration_stub.flag"),
        ("results/module6/m6_compound_library_mirror_paths_status.json", "module6.m6_compound_library_mirror_paths_status"),
        ("results/module6/m6_compound_library_mirror_paths_status.flag", "module6.m6_compound_library_mirror_paths_status.flag"),
        ("results/module6/m6_compound_library_mirror_integration_stub.json", "module6.m6_compound_library_mirror_integration_stub"),
        ("results/module6/m6_compound_library_mirror_integration_stub.flag", "module6.m6_compound_library_mirror_integration_stub.flag"),
        ("results/module6/structure_druggability_bridge_provenance.json", "structure_bridge.provenance"),
        ("results/module6/structure_druggability_bridge.flag", "structure_bridge.flag"),
        ("results/module6/structure_druggability_bridge_stratified.flag", "structure_bridge.stratified.flag"),
    ):
        artifacts.append(describe_path(rr, rel, tag=tag))

    prov_p = rr / "results/module6/structure_druggability_bridge_provenance.json"
    if prov_p.is_file():
        prov = json.loads(prov_p.read_text(encoding="utf-8"))
        for job in prov.get("jobs") or []:
            rel = job.get("output")
            if rel:
                artifacts.append(
                    describe_path(
                        rr,
                        rel,
                        tag=f"structure_bridge:{job.get('tag', '')}",
                        extra={"gts_input": job.get("gts_input"), "n_rows": job.get("n_rows")},
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
                        tag=f"structure_bridge.stratified:{sj.get('job_tag', '')}",
                        extra={"gts_input": sj.get("gts_input"), "n_rows": sj.get("n_rows")},
                    )
                )

    base = rr / "results/module6/structure_druggability_bridge_stratified"
    if base.is_dir():
        for p in sorted(base.rglob("*.tsv")):
            try:
                rel = p.resolve().relative_to(rr.resolve()).as_posix()
            except ValueError:
                rel = str(p.as_posix())
            if any(a.get("path_posix") == rel for a in artifacts):
                continue
            artifacts.append(describe_path(rr, rel, tag="structure_bridge.stratified.unlisted"))

    manifest_optional.apply_optional_tags_to_artifacts(artifacts, block.get("optional_tags") or [])

    doc = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 6,
        "artifacts": artifacts,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} ({len(artifacts)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
