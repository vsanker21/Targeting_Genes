"""Registry YAML stays parseable and structurally complete for manuscript discipline."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]


def test_manuscript_scientific_registry_yaml_loads() -> None:
    p = _ROOT / "config" / "manuscript_scientific_registry.yaml"
    assert p.is_file()
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    reg = doc.get("manuscript_scientific_registry") or {}
    assert reg.get("document_status") in ("draft", "preregistered", "manuscript_submitted")
    assert "flagship_claim" in reg and isinstance(reg["flagship_claim"], dict)
    assert "public_replication_and_holdout_cohorts" in reg
    cohorts = reg["public_replication_and_holdout_cohorts"]
    assert isinstance(cohorts, list) and len(cohorts) >= 3
    for c in cohorts:
        assert c.get("cohort_id")
        assert c.get("role")
    contract = reg.get("preregistered_analysis_contract") or {}
    assert isinstance(contract, dict)
    truth = reg.get("cns_readiness_truth_in_advertising") or {}
    assert "public_cohorts_strengthen" in truth


def test_preregistered_registry_has_hypothesis_and_competitors() -> None:
    p = _ROOT / "config" / "manuscript_scientific_registry.yaml"
    reg = yaml.safe_load(p.read_text(encoding="utf-8")).get("manuscript_scientific_registry") or {}
    if reg.get("document_status") != "preregistered":
        return
    fc = reg.get("flagship_claim") or {}
    assert str(fc.get("one_sentence", "")).strip(), "preregistered registry needs flagship_claim.one_sentence"
    assert fc.get("axis") in ("biology", "computational_method", "integrated_resource")
    comps = reg.get("closest_competitor_papers") or []
    assert len(comps) >= 3
    doi_re = re.compile(r"^10\.\d{4,}/")
    for c in comps:
        assert c.get("they_already_showed")
        assert c.get("we_add")
        assert c.get("pmid")
        doi = str(c.get("doi", "")).strip()
        assert doi_re.match(doi), f"competitor {c.get('short_name')} needs valid doi: {doi!r}"
    prim = str((reg.get("preregistered_analysis_contract") or {}).get("primary_endpoint", "")).strip()
    assert prim, "preregistered registry needs preregistered_analysis_contract.primary_endpoint"


def test_holdout_preregistered_outputs_yaml_loads() -> None:
    p = _ROOT / "config" / "holdout_preregistered_outputs.yaml"
    assert p.is_file()
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    ho = doc.get("holdout_preregistered_outputs") or {}
    assert isinstance(ho.get("cohorts"), list) and len(ho["cohorts"]) >= 1


def test_prisma_literature_search_yaml_loads() -> None:
    p = _ROOT / "config" / "prisma_literature_search.yaml"
    assert p.is_file()
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    pr = doc.get("prisma_literature_search") or {}
    assert pr.get("protocol_version")
    assert "eligibility_criteria" in pr
    assert "screening_log" in pr
    assert pr.get("flowchart_svg_export")
    assert pr.get("flowchart_pdf_export")


def test_preregistered_geo_holdouts_in_download_list() -> None:
    """Manuscript GEO holdout accessions must be listed for programmatic fetch."""
    reg_p = _ROOT / "config" / "manuscript_scientific_registry.yaml"
    req_p = _ROOT / "config" / "required_downloads.yaml"
    reg = yaml.safe_load(reg_p.read_text(encoding="utf-8")).get("manuscript_scientific_registry") or {}
    if reg.get("document_status") != "preregistered":
        return
    geo_list = list((yaml.safe_load(req_p.read_text(encoding="utf-8")) or {}).get("geo_bulk_series") or [])
    gse_re = re.compile(r"^GSE\d+$")
    for c in reg.get("public_replication_and_holdout_cohorts") or []:
        cid = str(c.get("cohort_id", ""))
        if cid not in ("geo_series_bulk_gbm_holdout_A", "geo_series_bulk_gbm_holdout_B"):
            continue
        gse = str(c.get("series_id_freeze", "")).strip()
        assert gse_re.match(gse), f"series_id_freeze must look like GSE…, got {gse!r}"
        assert gse in geo_list, f"{gse} must appear in config/required_downloads.yaml geo_bulk_series"
