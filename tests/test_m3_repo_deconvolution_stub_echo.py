"""m3_repo_deconvolution_integration_stub echo of main deconvolution stub JSON."""

from __future__ import annotations

from m3_repo_deconvolution_integration_stub import _echo_block_from_deconv_integration_stub


def test_echo_block_includes_checklist_and_tier() -> None:
    dec = {
        "readiness_tier": "B",
        "artifact_kind": "m3_deconvolution_integration_stub",
        "checklist": {
            "cell2location_run_status": "training_failed",
            "in_repo_cell2location_or_rctd": True,
        },
        "recommended_next_steps": ["a", "b"],
    }
    echo = _echo_block_from_deconv_integration_stub(dec)
    assert echo["readiness_tier"] == "B"
    assert echo["artifact_kind"] == "m3_deconvolution_integration_stub"
    assert echo["checklist"]["cell2location_run_status"] == "training_failed"
    assert echo["checklist"]["in_repo_cell2location_or_rctd"] is True
    assert echo["n_recommended_next_steps"] == 2


def test_echo_block_tolerates_minimal_doc() -> None:
    echo = _echo_block_from_deconv_integration_stub({})
    assert echo["readiness_tier"] is None
    assert echo["checklist"] is None
    assert echo["n_recommended_next_steps"] == 0
