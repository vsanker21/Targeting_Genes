#!/usr/bin/env python3
"""
Aggregate Module 3–7 export manifests and select provenance JSONs into one index with fresh file stats.

Harvests paths from provenance keys: output, output_rnk, input, input_tsv, gts_input (per config list).
Absolute paths under the repo root are rewritten to repo-relative POSIX keys (stable dedup vs manifests).

Config: config/pipeline_inventory.yaml — pipeline_results_index (optional_path_posix: mark paths optional after merge).

Summary lists sources_summary (manifest/provenance JSONs loaded vs missing), missing_required_path_posix
and missing_optional_path_posix (sorted path_posix).
Strict checks: CLI --strict, or env GLIOMA_TARGET_PIPELINE_INDEX_STRICT set to 1/true/yes/on (Snakemake/subprocess).
Unset, empty, 0, false, no, off, or any other value disables env strict. Same exit 1 and summary.strict_* when enabled.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

# Bump when summary shape or semantics change (for downstream parsers).
INDEX_SCHEMA = 1


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "pipeline_inventory.yaml"
    if not p.is_file():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _normalize_posix(raw: str) -> str:
    return str(Path(str(raw).strip().replace("\\", "/")).as_posix())


def _repo_relative_path_posix(rr: Path, raw: str | None) -> str:
    """Repo-relative forward-slash path for index keys; absolutes under rr are relativized."""
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    try:
        p = Path(s).expanduser()
        if p.is_absolute():
            rel = p.resolve().relative_to(rr.resolve())
            return rel.as_posix()
    except (ValueError, OSError):
        pass
    return _normalize_posix(s)


def stat_path(rr: Path, rel: str) -> dict[str, Any]:
    rel = str(rel).replace("/", os.sep)
    p = rr / rel
    out: dict[str, Any] = {"path_posix": str(Path(rel).as_posix()), "exists": p.is_file()}
    if not out["exists"]:
        out["size_bytes"] = None
        out["mtime_utc"] = None
        return out
    st = p.stat()
    out["size_bytes"] = int(st.st_size)
    out["mtime_utc"] = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
    return out


def merge_unique(
    acc: "OrderedDict[str, dict[str, Any]]",
    path_posix: str,
    *,
    module: int,
    source: str,
    tag: str,
    rr: Path,
    optional: bool = False,
) -> None:
    key = _repo_relative_path_posix(rr, path_posix)
    if not key:
        return
    st = stat_path(rr, key)
    if key not in acc:
        acc[key] = {
            "module": module,
            "sources": [source],
            "tags": [tag],
            **st,
        }
        if optional:
            acc[key]["optional"] = True
        return
    acc[key]["sources"].append(source)
    acc[key]["tags"].append(tag)
    acc[key]["exists"] = st["exists"]
    acc[key]["size_bytes"] = st["size_bytes"]
    acc[key]["mtime_utc"] = st["mtime_utc"]
    if optional:
        acc[key]["optional"] = True


def _job_input_paths(job: dict[str, Any]) -> str | None:
    return job.get("input") or job.get("gts_input") or job.get("input_tsv")


def _job_output_paths(job: dict[str, Any]) -> str | None:
    return job.get("output") or job.get("output_rnk")


def _sources_summary(source_status: list[dict[str, Any]]) -> dict[str, int]:
    out = {
        "n_manifest": 0,
        "n_manifest_loaded": 0,
        "n_manifest_missing": 0,
        "n_provenance": 0,
        "n_provenance_loaded": 0,
        "n_provenance_missing": 0,
    }
    for s in source_status:
        kind = s.get("kind")
        loaded = bool(s.get("loaded"))
        if kind == "manifest":
            out["n_manifest"] += 1
            if loaded:
                out["n_manifest_loaded"] += 1
            else:
                out["n_manifest_missing"] += 1
        elif kind == "provenance":
            out["n_provenance"] += 1
            if loaded:
                out["n_provenance_loaded"] += 1
            else:
                out["n_provenance_missing"] += 1
    return out


def harvest_provenance_outputs(rr: Path, prov_path: Path, module: int, acc: OrderedDict[str, dict[str, Any]]) -> bool:
    if not prov_path.is_file():
        return False
    data = json.loads(prov_path.read_text(encoding="utf-8"))
    src = str(prov_path.relative_to(rr)).replace("\\", "/")
    for job in data.get("jobs") or []:
        if job.get("status") and str(job.get("status")).lower() != "ok":
            continue
        tag = job.get("tag") or job.get("job_name") or "job"
        out = _job_output_paths(job)
        if out:
            merge_unique(acc, str(out), module=module, source=src, tag=f"{tag}:output", rr=rr)
        inn = _job_input_paths(job)
        if inn:
            merge_unique(acc, str(inn), module=module, source=src, tag=f"{tag}:input", rr=rr)
    for sj in data.get("stratified_jobs") or []:
        if sj.get("status") and str(sj.get("status")).lower() != "ok":
            continue
        jt = sj.get("job_tag", "")
        out = _job_output_paths(sj)
        if out:
            merge_unique(acc, str(out), module=module, source=src, tag=f"{jt}:stratified:output", rr=rr)
        inn = _job_input_paths(sj)
        if inn:
            merge_unique(acc, str(inn), module=module, source=src, tag=f"{jt}:stratified:input", rr=rr)
    return True


def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Merge M3–M7 export manifests + provenance paths into pipeline_results_index.json.",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Exit with code 1 if any required path is missing or optional_path_posix lists unknown paths. "
            "Same if env GLIOMA_TARGET_PIPELINE_INDEX_STRICT is 1/true/yes/on (0/false/no/off unset strict)."
        ),
    )
    return ap.parse_args(argv)


def _strict_from_cli(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "strict", False))


def _strict_from_env() -> bool:
    v = os.environ.get("GLIOMA_TARGET_PIPELINE_INDEX_STRICT", "").strip().lower()
    if not v or v in ("0", "false", "no", "off"):
        return False
    return v in ("1", "true", "yes", "on")


def _strict_enabled(args: argparse.Namespace) -> bool:
    return _strict_from_cli(args) or _strict_from_env()


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = []
    args = parse_args(argv)
    strict = _strict_enabled(args)
    strict_triggers: list[str] = []
    if _strict_from_cli(args):
        strict_triggers.append("cli")
    if _strict_from_env():
        strict_triggers.append("env")

    rr = repo_root()
    cfg = load_cfg().get("pipeline_results_index") or {}
    if not cfg.get("enabled", True):
        print("pipeline_results_index disabled")
        return 0

    out_rel = str(cfg.get("output_json", "results/pipeline_results_index.json"))
    out_path = rr / out_rel.replace("/", os.sep)

    acc: OrderedDict[str, dict[str, Any]] = OrderedDict()
    source_status: list[dict[str, Any]] = []

    for rel in cfg.get("manifest_paths") or []:
        mp = rr / str(rel).replace("/", os.sep)
        src = str(rel).replace("\\", "/")
        if not mp.is_file():
            source_status.append({"path": src, "kind": "manifest", "loaded": False})
            continue
        source_status.append({"path": src, "kind": "manifest", "loaded": True})
        doc = json.loads(mp.read_text(encoding="utf-8"))
        mod = int(doc.get("outline_module", 0) or 0)
        for art in doc.get("artifacts") or []:
            pp = art.get("path_posix") or art.get("path")
            tag = str(art.get("tag", ""))
            merge_unique(
                acc,
                str(pp),
                module=mod,
                source=src,
                tag=tag,
                rr=rr,
                optional=bool(art.get("optional")),
            )

    for item in cfg.get("provenance_paths") or []:
        if isinstance(item, str):
            rel, mod = item, 0
        else:
            rel = item.get("path", "")
            mod = int(item.get("module", 0) or 0)
        prov_p = rr / str(rel).replace("/", os.sep)
        src = str(rel).replace("\\", "/")
        ok = harvest_provenance_outputs(rr, prov_p, mod, acc)
        source_status.append({"path": src, "kind": "provenance", "module": mod, "loaded": ok})

    inv_src = "config/pipeline_inventory.yaml"
    primary_deliverables_summary: list[dict[str, Any]] = []
    for item in cfg.get("primary_deliverables") or []:
        if not isinstance(item, dict):
            continue
        pp = str(item.get("path_posix") or "").strip()
        if not pp:
            continue
        mod = int(item.get("module", 7) or 7)
        pid = str(item.get("id") or "primary").strip() or "primary"
        merge_unique(acc, pp, module=mod, source=inv_src, tag=f"primary_deliverable:{pid}", rr=rr)
        primary_deliverables_summary.append(
            {
                "id": pid,
                "path_posix": _repo_relative_path_posix(rr, pp),
                "module": mod,
                "tier_filter": item.get("tier_filter"),
                "note": item.get("note"),
            }
        )

    optional_raw = cfg.get("optional_path_posix") or []
    optional_keys = [_normalize_posix(x) for x in optional_raw if str(x).strip()]
    optional_path_posix_unmatched: list[str] = []
    for key in optional_keys:
        if key in acc:
            acc[key]["optional"] = True
        else:
            optional_path_posix_unmatched.append(key)
    for key in optional_path_posix_unmatched:
        print(
            f"pipeline_results_index: optional_path_posix not in merged index: {key}",
            file=sys.stderr,
        )

    entries = list(acc.values())
    n_exist = sum(1 for e in entries if e.get("exists"))
    n_miss = len(entries) - n_exist
    n_missing_required = sum(
        1 for e in entries if not e.get("exists") and not e.get("optional")
    )
    n_missing_optional = sum(1 for e in entries if not e.get("exists") and e.get("optional"))
    n_optional = sum(1 for e in entries if e.get("optional"))
    by_mod: dict[str, dict[str, int]] = {}
    for e in entries:
        m = str(e.get("module", 0))
        by_mod.setdefault(
            m,
            {
                "n": 0,
                "n_existing": 0,
                "n_optional": 0,
                "n_missing_required": 0,
                "n_missing_optional": 0,
            },
        )
        by_mod[m]["n"] += 1
        if e.get("exists"):
            by_mod[m]["n_existing"] += 1
        if e.get("optional"):
            by_mod[m]["n_optional"] += 1
        if not e.get("exists"):
            if e.get("optional"):
                by_mod[m]["n_missing_optional"] += 1
            else:
                by_mod[m]["n_missing_required"] += 1

    missing_required_path_posix = sorted(
        str(e["path_posix"]) for e in entries if not e.get("exists") and not e.get("optional")
    )
    missing_optional_path_posix = sorted(
        str(e["path_posix"]) for e in entries if not e.get("exists") and e.get("optional")
    )

    src_sum = _sources_summary(source_status)

    strict_rc = 0
    if strict:
        if n_missing_required > 0:
            strict_rc = 1
            print(
                f"write_pipeline_results_index: strict failing: n_missing_required={n_missing_required}",
                file=sys.stderr,
            )
            for p in missing_required_path_posix:
                print(f"  missing required: {p}", file=sys.stderr)
        if optional_path_posix_unmatched:
            strict_rc = 1
            print(
                "write_pipeline_results_index: --strict failing: optional_path_posix_unmatched="
                f"{optional_path_posix_unmatched!r}",
                file=sys.stderr,
            )

    summary: dict[str, Any] = {
        "index_schema": INDEX_SCHEMA,
        "primary_deliverables": primary_deliverables_summary,
        "n_paths_unique": len(entries),
        "n_existing": n_exist,
        "n_missing": n_miss,
        "n_missing_required": n_missing_required,
        "n_missing_optional": n_missing_optional,
        "n_optional": n_optional,
        "missing_required_path_posix": missing_required_path_posix,
        "missing_optional_path_posix": missing_optional_path_posix,
        "optional_path_posix_unmatched": optional_path_posix_unmatched,
        "sources_summary": src_sum,
        "by_outline_module": by_mod,
    }
    if strict:
        summary["strict_mode"] = True
        summary["strict_ok"] = strict_rc == 0
        summary["strict_triggers"] = strict_triggers

    doc = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "sources": source_status,
        "entries": entries,
        "summary": summary,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(
        f"Wrote {out_path} unique_paths={len(entries)} existing={n_exist} "
        f"missing={n_miss} (required_missing={n_missing_required} optional_missing={n_missing_optional} "
        f"n_optional={n_optional} optional_path_posix_unmatched={len(optional_path_posix_unmatched)}) "
        f"sources manifest {src_sum['n_manifest_loaded']}/{src_sum['n_manifest']} "
        f"provenance {src_sum['n_provenance_loaded']}/{src_sum['n_provenance']}"
    )
    return strict_rc if strict else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
