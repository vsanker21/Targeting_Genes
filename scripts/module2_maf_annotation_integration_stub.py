#!/usr/bin/env python3
"""
Outline M2.2: OncoKB / ClinVar integration gap report (no variant annotation run).

Summarizes TCGA MAF layer + DEA join provenance from config/tcga_mutation_layer.yaml and
results/module3/tcga_maf_*_provenance.json. Use for planning; licensing and coordinate
requirements block in-repo automation.

Config: config/tcga_mutation_layer.yaml — maf_annotation_integration_stub
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


def load_mutation_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "tcga_mutation_layer.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _read_json(rr: Path, rel: str) -> dict[str, Any] | None:
    p = rr / rel.replace("/", os.sep)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    rr = repo_root()
    cfg = load_mutation_cfg()
    block = cfg.get("maf_annotation_integration_stub") or {}
    if not block.get("enabled", True):
        print("maf_annotation_integration_stub disabled")
        return 0

    maf_glob = str(cfg.get("maf_glob") or "").strip()
    gene_summary_rel = str(cfg.get("gene_summary_tsv") or "results/module3/tcga_gbm_maf_gene_summary.tsv")
    gene_summary = rr / gene_summary_rel.replace("/", os.sep)

    layer = _read_json(rr, "results/module3/tcga_maf_layer_provenance.json") or {}
    joinp = _read_json(rr, "results/module3/tcga_maf_join_provenance.json") or {}

    blockers: list[str] = []
    if not layer:
        blockers.append("Missing results/module3/tcga_maf_layer_provenance.json (run m2_tcga_maf_gene_summary)")
    if not joinp:
        blockers.append("Missing results/module3/tcga_maf_join_provenance.json (run m2_tcga_maf_join_dea)")

    summary_rows = int(joinp.get("summary_rows") or 0)
    layer_status = str(layer.get("status") or ("ok" if layer else "unknown"))
    maf_gene_summary_populated = bool(maf_glob) and layer_status != "skipped" and summary_rows > 0

    welch_maf = rr / "results/module3/dea_gbm_vs_gtex_brain_tcga_maf.tsv"
    maf_cols_on_dea = welch_maf.is_file()
    if maf_cols_on_dea:
        try:
            header = welch_maf.read_text(encoding="utf-8", errors="replace").splitlines()[0]
            has_maf_cols = "tcga_maf_n_samples_mutated" in header
        except OSError:
            has_maf_cols = False
    else:
        has_maf_cols = False

    checklist: dict[str, Any] = {
        "maf_glob_configured": bool(maf_glob),
        "tcga_maf_gene_summary_nonempty": summary_rows > 0,
        "maf_layer_produced_variant_counts": maf_gene_summary_populated,
        "dea_tables_include_maf_count_columns": has_maf_cols,
        "oncokb_variant_annotation": False,
        "clinvar_variant_annotation": False,
        "note": "OncoKB/ClinVar need per-variant coordinates, reference/alternate alleles, and (for OncoKB) licensed API or file access — not implemented here.",
    }

    recommended: list[str] = []
    if not maf_glob:
        recommended.append("Set maf_glob in config/tcga_mutation_layer.yaml to ingest TCGA MAF files for gene-level summaries.")
    elif summary_rows == 0:
        recommended.append("Verify maf_glob matches files on disk and variant_classifications filter is not too strict.")
    recommended.append(
        "For ClinVar: map MAF rows to dbSNP/rsIDs or chr-pos-ref-alt and annotate with VEP + ClinVar VCF or API."
    )
    recommended.append(
        "For OncoKB: use official API/oncokb-annotator with MAF or VCF; comply with Johns Hopkins terms of use."
    )

    out = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "outline_section": "M2.2",
        "artifact_kind": "maf_annotation_integration_stub",
        "note": "Checklist only; no OncoKB or ClinVar queries are executed in this repository step.",
        "config_echo": {
            "maf_glob": maf_glob,
            "gene_summary_tsv": gene_summary_rel,
            "gene_summary_exists": gene_summary.is_file(),
        },
        "tcga_maf_layer_provenance_echo": layer,
        "tcga_maf_join_provenance_echo": joinp,
        "oncokb_clinvar_checklist": checklist,
        "blockers": blockers,
        "recommended_next_steps": recommended,
    }

    out_rel = str(block.get("output_json", "results/module3/maf_annotation_integration_stub.json"))
    out_path = rr / out_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")

    flag_rel = str(block.get("done_flag", "results/module3/maf_annotation_integration_stub.flag"))
    (rr / flag_rel.replace("/", os.sep)).write_text("ok\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
