#!/usr/bin/env python3
"""
Summarize Module 4-related export artifacts (paths, sizes, STRING job metadata).

Reads config/module2_integration.yaml, dea_string_export_provenance.json, and
stratified_string_export_provenance.json; records file stats for WGCNA subset, traits,
subtype means, global and stratified STRING lists, and GSEA prerank .rnk files.

Config: config/module2_integration.yaml — module4_export_manifest
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

import manifest_optional


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_integration_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "module2_integration.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def describe_path(rr: Path, rel: str | None, *, tag: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"tag": tag, "path": rel}
    if not rel:
        out["exists"] = False
        return out
    p = rr / str(rel)
    out["path_posix"] = str(Path(rel).as_posix())
    if not p.is_file():
        out["exists"] = False
        out["size_bytes"] = None
        return out
    st = p.stat()
    out["exists"] = True
    out["size_bytes"] = int(st.st_size)
    out["mtime_utc"] = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
    if p.suffix.lower() in (".txt", ".tsv", ".csv", ".json", ".rnk"):
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
    cfg = load_integration_cfg()
    block = cfg.get("module4_export_manifest") or {}
    if not block.get("enabled", True):
        print("module4_export_manifest disabled")
        return 0

    out_path = rr / str(block.get("output_json", "results/module4/module4_export_manifest.json"))
    artifacts: list[dict[str, Any]] = []

    str_prov_p = rr / "results/module3/dea_string_export_provenance.json"
    if str_prov_p.is_file():
        prov = json.loads(str_prov_p.read_text(encoding="utf-8"))
        for job in prov.get("jobs") or []:
            jn = job.get("job_name", "")
            rel = job.get("output_txt")
            if rel:
                artifacts.append(
                    describe_path(
                        rr,
                        rel,
                        tag=f"dea_string_export:{jn}",
                        extra={"job_status": job.get("status"), "n_symbols_exported": job.get("n_symbols_exported")},
                    )
                )

    strat_p = rr / "results/module4/stratified_string_export_provenance.json"
    if strat_p.is_file():
        prov = json.loads(strat_p.read_text(encoding="utf-8"))
        for job in prov.get("jobs") or []:
            rel = job.get("output_txt")
            if rel:
                jt = job.get("job_tag", "")
                artifacts.append(
                    describe_path(
                        rr,
                        rel,
                        tag=f"stratified_string_export:{jt}",
                        extra={
                            "job_status": job.get("status"),
                            "n_symbols_exported": job.get("n_symbols_exported"),
                            "input_tsv": job.get("input_tsv"),
                        },
                    )
                )

    wgc = cfg.get("wgcna_hub_subset") or {}
    for fld, tag in [
        ("output_parquet", "wgcna_hub_subset.parquet"),
        ("output_long_tsv", "wgcna_hub_subset.long_tsv"),
        ("provenance_json", "wgcna_hub_subset.provenance"),
    ]:
        artifacts.append(describe_path(rr, wgc.get(fld), tag=tag))

    wst = cfg.get("wgcna_sample_traits") or {}
    for fld, tag in [("output_tsv", "wgcna_sample_traits.tsv"), ("provenance_json", "wgcna_sample_traits.provenance")]:
        artifacts.append(describe_path(rr, wst.get(fld), tag=tag))

    wr3 = cfg.get("wgcna_hub_subset_recount3_only") or {}
    for fld, tag in [
        ("output_parquet", "wgcna_hub_subset_recount3_only.parquet"),
        ("output_long_tsv", "wgcna_hub_subset_recount3_only.long_tsv"),
        ("provenance_json", "wgcna_hub_subset_recount3_only.provenance"),
    ]:
        artifacts.append(describe_path(rr, wr3.get(fld), tag=tag))

    wstr3 = cfg.get("wgcna_sample_traits_recount3_only") or {}
    for fld, tag in [
        ("output_tsv", "wgcna_sample_traits_recount3_only.tsv"),
        ("provenance_json", "wgcna_sample_traits_recount3_only.provenance"),
    ]:
        artifacts.append(describe_path(rr, wstr3.get(fld), tag=tag))

    sme = cfg.get("subtype_mean_expression") or {}
    artifacts.append(describe_path(rr, sme.get("output_tsv"), tag="subtype_mean_expression.tsv"))

    gsea = cfg.get("gsea_prerank_export") or {}
    gsea_prov = gsea.get("aggregate_provenance_json")
    if gsea_prov:
        artifacts.append(describe_path(rr, gsea_prov, tag="gsea_prerank.provenance"))
    for gj in gsea.get("jobs") or []:
        rel = gj.get("output_rnk")
        if rel:
            artifacts.append(
                describe_path(
                    rr,
                    rel,
                    tag=f"gsea_prerank:{gj.get('job_name', '')}",
                )
            )

    strat_gsea = rr / "results/module4/gsea/stratified"
    if strat_gsea.is_dir():
        for p in sorted(strat_gsea.rglob("*.rnk")):
            if p.is_file():
                rel = str(p.relative_to(rr)).replace("\\", "/")
                artifacts.append(describe_path(rr, rel, tag="gsea_prerank.stratified"))

    str_api = cfg.get("string_api_network_fetch") or {}
    artifacts.append(
        describe_path(rr, "results/module4/string_api/string_api_fetch_provenance.json", tag="string_api_fetch.provenance")
    )
    for j in str_api.get("jobs") or []:
        rel = j.get("output_json")
        if rel:
            artifacts.append(
                describe_path(rr, rel, tag=f"string_api_network:{j.get('job_id', '')}"),
            )

    artifacts.append(
        describe_path(rr, "results/module4/wgcna_hub_gene_overlap_summary.json", tag="wgcna_hub_gene_overlap_summary"),
    )

    archs4_blk = cfg.get("archs4_expression_join") or {}
    for fld, tag in [
        ("output_welch", "archs4_dea_join:welch"),
        ("output_ols", "archs4_dea_join:ols"),
    ]:
        rel = archs4_blk.get(fld)
        if rel:
            artifacts.append(describe_path(rr, rel, tag=tag))
    for rel, tag in (
        ("results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/deseq2_archs4.tsv", "archs4_dea_join:deseq2"),
        ("results/module3/deseq2_recount3_tcga_gbm_vs_gtex_brain/edger_archs4.tsv", "archs4_dea_join:edger"),
        ("results/module3/dea_archs4_join_provenance.json", "archs4_dea_join:provenance"),
        ("results/module4/archs4_recount_h5_summary.json", "archs4_recount_h5_summary"),
        ("results/module4/archs4_outline_driver_expression_context.json", "archs4_outline_driver_context"),
        ("results/module4/m4_supplementary_open_enrichment_plan.json", "supplementary:m4_open_enrichment_plan"),
        ("results/module4/m4_clusterprofiler_supplementary_plan.json", "supplementary:m4_clusterprofiler_plan"),
        ("results/module4/gsea/fgsea_supplementary_pathways_results.tsv", "supplementary:fgsea_results"),
        ("results/module4/gsea/clusterprofiler_supplementary_enricher.tsv", "supplementary:clusterprofiler_results"),
    ):
        artifacts.append(describe_path(rr, rel, tag=tag))

    for rel, tag in (
        ("results/module4/m4_network_paths_status.json", "m4_network_paths_status"),
        ("results/module4/m4_network_paths_status.flag", "m4_network_paths_status.flag"),
        ("results/module4/m4_network_integration_stub.json", "m4_network_integration_stub"),
        ("results/module4/m4_network_integration_stub.flag", "m4_network_integration_stub.flag"),
        ("results/module4/m4_string_cache_paths_status.json", "m4_string_cache_paths_status"),
        ("results/module4/m4_string_cache_paths_status.flag", "m4_string_cache_paths_status.flag"),
        ("results/module4/m4_string_cache_integration_stub.json", "m4_string_cache_integration_stub"),
        ("results/module4/m4_string_cache_integration_stub.flag", "m4_string_cache_integration_stub.flag"),
        ("results/module4/m4_gsea_mirror_paths_status.json", "m4_gsea_mirror_paths_status"),
        ("results/module4/m4_gsea_mirror_paths_status.flag", "m4_gsea_mirror_paths_status.flag"),
        ("results/module4/m4_gsea_mirror_integration_stub.json", "m4_gsea_mirror_integration_stub"),
        ("results/module4/m4_gsea_mirror_integration_stub.flag", "m4_gsea_mirror_integration_stub.flag"),
        ("results/module4/m4_pathway_database_mirror_paths_status.json", "m4_pathway_database_mirror_paths_status"),
        ("results/module4/m4_pathway_database_mirror_paths_status.flag", "m4_pathway_database_mirror_paths_status.flag"),
        ("results/module4/m4_pathway_database_mirror_integration_stub.json", "m4_pathway_database_mirror_integration_stub"),
        ("results/module4/m4_pathway_database_mirror_integration_stub.flag", "m4_pathway_database_mirror_integration_stub.flag"),
    ):
        artifacts.append(describe_path(rr, rel, tag=tag))

    manifest_optional.apply_optional_tags_to_artifacts(artifacts, block.get("optional_tags") or [])

    payload = {
        "outline_module": 4,
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "artifacts": artifacts,
        "note": "Presence and size only; use sidecar provenance JSONs for scientific parameters.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} ({len(artifacts)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
