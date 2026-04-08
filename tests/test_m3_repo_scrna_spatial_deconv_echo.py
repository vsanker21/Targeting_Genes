"""m3_repo_scrna_spatial_integration_stub deconvolution echo block."""

from __future__ import annotations

from m3_repo_scrna_spatial_integration_stub import _m3_deconv_integration_stub_echo_block


def test_deconv_echo_empty_when_no_doc() -> None:
    b = _m3_deconv_integration_stub_echo_block(None)
    assert b["readiness_tier"] is None
    assert b["in_repo_cell2location_or_rctd"] is None
    assert b["cell2location_run_status"] is None
    assert b["cell2location_has_signature_extract_diagnostic"] is None


def test_deconv_echo_dec_without_checklist_preserves_doc_tier_and_nulls_rctd_fields() -> None:
    dec = {"readiness_tier": "C", "artifact_kind": "m3_deconvolution_integration_stub"}
    b = _m3_deconv_integration_stub_echo_block(dec)
    assert b["readiness_tier"] == "C"
    assert b["artifact_kind"] == "m3_deconvolution_integration_stub"
    assert b["in_repo_cell2location_or_rctd"] is None
    assert b["cell2location_run_status"] is None
    assert b["rctd_run_status"] is None


def test_deconv_echo_pulls_checklist_fields() -> None:
    dec = {
        "readiness_tier": "B",
        "artifact_kind": "m3_deconvolution_integration_stub",
        "checklist": {
            "in_repo_cell2location_or_rctd": True,
            "cell2location_run_status": "training_failed",
            "cell2location_has_signature_extract_diagnostic": True,
            "cell2location_has_gene_intersection_diagnostic": False,
            "rctd_run_status": "ok",
        },
    }
    b = _m3_deconv_integration_stub_echo_block(dec)
    assert b["readiness_tier"] == "B"
    assert b["in_repo_cell2location_or_rctd"] is True
    assert b["cell2location_run_status"] == "training_failed"
    assert b["cell2location_has_signature_extract_diagnostic"] is True
    assert b["cell2location_has_gene_intersection_diagnostic"] is False
    assert b["rctd_run_status"] == "ok"
