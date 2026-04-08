"""RCTD provenance helpers for M3 deconvolution integration stub (matches run_m3_rctd_wrapper.R fields)."""

from __future__ import annotations

from module3_deconvolution_integration_stub import (
    rctd_create_succeeded,
    rctd_followup_messages,
    rctd_provenance_present,
    rctd_rds_loads_ok,
)


def test_rctd_provenance_present() -> None:
    assert not rctd_provenance_present(None)
    assert not rctd_provenance_present({})
    assert rctd_provenance_present({"ref_load_ok": False})


def test_rctd_rds_loads_ok() -> None:
    assert not rctd_rds_loads_ok(None)
    assert not rctd_rds_loads_ok({"ref_load_ok": True})
    assert rctd_rds_loads_ok({"ref_load_ok": True, "spatial_load_ok": True})


def test_rctd_create_succeeded() -> None:
    assert not rctd_create_succeeded(None)
    assert not rctd_create_succeeded({"rctd_create_ok": False})
    assert rctd_create_succeeded({"rctd_create_ok": True})


def test_rctd_create_succeeded_prefers_status_ok() -> None:
    assert rctd_create_succeeded({"status": "ok", "rctd_create_ok": False})
    assert not rctd_create_succeeded({"status": "create_failed", "rctd_create_ok": True})


def test_rctd_create_succeeded_legacy_without_status_key() -> None:
    assert rctd_create_succeeded({"rctd_create_ok": True})
    assert not rctd_create_succeeded({"rctd_create_ok": False})


def test_rctd_followup_messages_empty_when_ok_or_no_rds() -> None:
    assert rctd_followup_messages(None) == []
    assert rctd_followup_messages({"status": "ok", "ref_load_ok": True, "spatial_load_ok": True}) == []
    assert rctd_followup_messages({"status": "create_failed", "ref_load_ok": False, "spatial_load_ok": True}) == []


def test_rctd_followup_messages_spacexr_missing() -> None:
    r = {"status": "spacexr_missing", "ref_load_ok": True, "spatial_load_ok": True}
    msgs = rctd_followup_messages(r)
    assert len(msgs) == 1
    assert "spacexr is not installed" in msgs[0]


def test_rctd_followup_messages_create_failed() -> None:
    r = {"status": "create_failed", "ref_load_ok": True, "spatial_load_ok": True}
    msgs = rctd_followup_messages(r)
    assert len(msgs) == 1
    assert "create.RCTD failed" in msgs[0]


def test_rctd_followup_messages_legacy_no_status() -> None:
    r = {"ref_load_ok": True, "spatial_load_ok": True, "rctd_create_ok": False}
    msgs = rctd_followup_messages(r)
    assert len(msgs) == 1
    assert "install spacexr" in msgs[0]


def test_rctd_followup_messages_empty_when_rds_load_failed() -> None:
    r = {
        "status": "rds_load_failed",
        "ref_load_ok": False,
        "spatial_load_ok": True,
    }
    assert rctd_followup_messages(r) == []


def test_rctd_followup_messages_unknown_status_fallback_when_rds_ok() -> None:
    r = {
        "status": "future_status",
        "ref_load_ok": True,
        "spatial_load_ok": True,
    }
    msgs = rctd_followup_messages(r)
    assert len(msgs) == 1
    assert "both RDS objects load" in msgs[0]
