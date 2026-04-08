#!/usr/bin/env python3
"""
Presence of supplementary open-reference files under data_root (config/data_sources.yaml).

Covers ARCHS4/recount HDF5 dir, Expression Atlas gene TSV dir, pathway GMTs, DGIdb, ChEMBL map,
ClinVar gene summary, gnomAD LOF-by-gene, optional DrugCentral dump — same layout as
download_supplementary_reference_resources.py.

Writes results/module3/supplementary_reference_resources_paths_status.json (+ .flag).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

# Keys under references: in data_sources.yaml (must match supplementary download layout).
_REF_KEYS: list[tuple[str, str]] = [
    ("archs4_recount_h5_dir", "archs4_recount_dir"),
    ("expression_atlas_genes_dir", "expression_atlas_genes_dir"),
    ("wikipathways_homo_sapiens_gmt", "wikipathways_homo_sapiens_gmt"),
    ("pathwaycommons_all_hgnc_gmt", "pathwaycommons_all_hgnc_gmt"),
    ("pathwaycommons_all_hgnc_gmt_plain", "pathwaycommons_all_hgnc_gmt_plain"),
    ("dgidb_tables_dir", "dgidb_dir"),
    ("chembl_uniprot_mapping", "chembl_uniprot_mapping_txt"),
    ("clinvar_gene_specific_summary", "clinvar_gene_specific_summary"),
    ("gnomad_lof_by_gene_bgz", "gnomad_lof_by_gene_bgz"),
    ("drugcentral_dump_gz", "drugcentral_dump_gz"),
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def count_files_shallow(path: Path, max_files: int = 50000) -> tuple[int, bool]:
    n = 0
    for root, _, files in os.walk(path):
        n += len(files)
        if n >= max_files:
            return n, True
    return n, False


def _one_path(dr: Path, rel_tmpl: str) -> dict[str, Any]:
    rel = rel_tmpl.replace("{data_root}", str(dr)).replace("/", os.sep)
    p = Path(rel)
    if p.is_file():
        return {
            "path": str(p),
            "kind": "file",
            "exists": True,
            "size_bytes": p.stat().st_size,
        }
    if p.is_dir():
        nf, trunc = count_files_shallow(p)
        return {
            "path": str(p),
            "kind": "directory",
            "exists": True,
            "n_files_under": nf,
            "file_count_truncated": trunc,
        }
    return {"path": str(p), "exists": False, "kind": "missing"}


def main() -> int:
    rr = repo_root()
    dr = data_root()
    ds_path = rr / "config" / "data_sources.yaml"
    if not ds_path.is_file():
        print(f"Missing {ds_path}", file=sys.stderr)
        return 1
    doc = yaml.safe_load(ds_path.read_text(encoding="utf-8"))
    ref = doc.get("references") or {}

    checks: list[dict[str, Any]] = []
    for display_name, yaml_key in _REF_KEYS:
        tmpl = ref.get(yaml_key)
        if not tmpl or not isinstance(tmpl, str):
            checks.append(
                {
                    "name": display_name,
                    "yaml_key": yaml_key,
                    "error": "missing_or_invalid_in_data_sources.references",
                }
            )
            continue
        row: dict[str, Any] = {"name": display_name, "yaml_key": yaml_key, **_one_path(dr, tmpl)}
        checks.append(row)

    n_ok = sum(1 for c in checks if c.get("exists") is True)
    out = {
        "data_root": str(dr.resolve()),
        "outline_module": 3,
        "artifact_kind": "supplementary_reference_resources_paths_status",
        "checks": checks,
        "n_existing": n_ok,
        "n_checks": len(checks),
        "note": "Presence only; fetch via scripts/download_supplementary_reference_resources.py.",
    }
    out_path = rr / "results" / "module3" / "supplementary_reference_resources_paths_status.json"
    flag_path = rr / "results" / "module3" / "supplementary_reference_resources_paths_status.flag"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {out_path} ({n_ok}/{len(checks)} present)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
