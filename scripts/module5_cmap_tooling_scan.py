#!/usr/bin/env python3
"""
Module 5 (outline): record cmapPy importability and LINCS path-check summary for connectivity work.

Reads results/module5/module5_data_paths_status.json (must exist). Optionally augments with
lincs_disease_signature_provenance.json when already on disk (e.g. after a full snakemake run).
If results/optional_third_party_functional_report.json exists (from ensure_optional_third_party_functional),
merges a slim summary under optional_third_party_functional (GCT round-trip status, binary checks).

Does not import heavy cmapPy submodules beyond package resolution; does not run queries.

Config: config/module5_inputs.yaml — cmap_tooling_scan
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_m5_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module5_inputs.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def summarize_optional_functional_report(path: Path) -> dict[str, Any] | None:
    """Parse ensure_optional_third_party_functional JSON; return slim dict or None on failure."""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    rows: list[dict[str, Any]] = []
    for c in doc.get("checks") or []:
        row: dict[str, Any] = {"id": c.get("id"), "ok": bool(c.get("ok"))}
        if "skipped" in c:
            row["skipped"] = c.get("skipped")
        if c.get("path"):
            row["path"] = c.get("path")
        rows.append(row)
    gct = next((x for x in rows if x.get("id") == "cmapPy_gct_roundtrip"), None)
    rr = repo_root()
    try:
        rel_s = str(path.resolve().relative_to(rr.resolve())).replace("\\", "/")
    except ValueError:
        rel_s = str(path).replace("\\", "/")
    return {
        "report_path": rel_s,
        "generated_utc": doc.get("generated_utc"),
        "checks": rows,
        "cmapPy_gct_roundtrip_ok": bool(gct and gct.get("ok")),
    }


def main() -> int:
    rr = repo_root()
    cfg = load_m5_cfg()
    block = cfg.get("cmap_tooling_scan") or {}
    if not block.get("enabled", True):
        print("cmap_tooling_scan disabled")
        return 0

    dp = rr / "results/module5/module5_data_paths_status.json"
    if not dp.is_file():
        print(f"Missing {dp} (run module5_data_paths_status first)", file=sys.stderr)
        return 1

    path_data = json.loads(dp.read_text(encoding="utf-8"))
    checks = path_data.get("checks") or []
    path_checks = {str(c.get("name", "")): bool(c.get("exists")) for c in checks}

    cmap_spec = importlib.util.find_spec("cmapPy")
    cmap_importable = cmap_spec is not None

    lincs_prov_p = rr / "results/module5/lincs_disease_signature_provenance.json"
    lincs_summary: dict[str, Any] = {"provenance_present": lincs_prov_p.is_file()}
    if lincs_prov_p.is_file():
        prov = json.loads(lincs_prov_p.read_text(encoding="utf-8"))
        jobs = prov.get("jobs") or []
        sj = prov.get("stratified_jobs") or []
        lincs_summary["n_global_signature_jobs"] = len(jobs)
        lincs_summary["n_stratified_signature_jobs_total"] = len(sj)
        lincs_summary["n_stratified_signature_jobs_ok"] = sum(1 for x in sj if x.get("status") == "ok")

    out = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_module": 5,
        "cmapPy_importable": cmap_importable,
        "cmapPy_spec_origin": getattr(cmap_spec, "origin", None) if cmap_spec else None,
        "python_executable": sys.executable,
        "module5_path_checks": path_checks,
        "data_root_from_status": path_data.get("data_root"),
        "lincs_disease_signature": lincs_summary,
        "note": "cmapPy_importable uses importlib.util.find_spec only. Path checks are from module5_data_paths_status; they do not validate GCTX contents.",
    }

    fn_rel = str(
        block.get("optional_functional_report_json")
        or "results/optional_third_party_functional_report.json"
    )
    fn_path = rr / fn_rel.replace("/", os.sep)
    if fn_path.is_file():
        summ = summarize_optional_functional_report(fn_path)
        out["optional_third_party_functional"] = summ
    else:
        out["optional_third_party_functional"] = None

    out_rel = str(block.get("output_json", "results/module5/cmap_tooling_scan.json"))
    out_path = rr / out_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")

    flag_rel = str(block.get("done_flag", "results/module5/cmap_tooling_scan.flag"))
    flag_path = rr / flag_rel.replace("/", os.sep)
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    flag_path.write_text("ok\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
