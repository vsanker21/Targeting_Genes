"""Helpers for interpreting Cell2location provenance in M3 deconvolution integration stub."""

from __future__ import annotations

from module3_deconvolution_integration_stub import (
    cell2location_followup_messages,
    cell2location_has_gene_intersection_diagnostic,
    cell2location_has_signature_extract_diagnostic,
    cell2location_provenance_trained,
    cell2location_provenance_useful,
    cell2location_training_output_paths_in_provenance,
)


def test_cell2location_provenance_useful_inputs_ok() -> None:
    assert cell2location_provenance_useful({"status": "inputs_ok"})


def test_cell2location_provenance_useful_trained_ok() -> None:
    assert cell2location_provenance_useful({"status": "trained_ok"})


def test_cell2location_provenance_useful_training_failed() -> None:
    assert not cell2location_provenance_useful({"status": "training_failed"})


def test_cell2location_provenance_useful_missing() -> None:
    assert not cell2location_provenance_useful(None)
    assert not cell2location_provenance_useful({})


def test_cell2location_provenance_trained_only_trained_ok() -> None:
    assert cell2location_provenance_trained({"status": "trained_ok"})
    assert not cell2location_provenance_trained({"status": "inputs_ok"})
    assert not cell2location_provenance_trained(None)


def test_training_output_paths_in_provenance_when_trained_with_paths() -> None:
    c2l = {
        "status": "trained_ok",
        "training": {
            "output_result_h5ad": "results/module3/m3_deconvolution_cell2location/spatial_cell2location.h5ad",
            "output_abundance_tsv": "results/module3/m3_deconvolution_cell2location/spot_cell_abundance_means.tsv",
        },
    }
    assert cell2location_training_output_paths_in_provenance(c2l)


def test_training_output_paths_false_without_training_block() -> None:
    assert not cell2location_training_output_paths_in_provenance({"status": "trained_ok"})


def test_training_output_paths_false_for_inputs_ok() -> None:
    assert not cell2location_training_output_paths_in_provenance(
        {
            "status": "inputs_ok",
            "training": {
                "output_result_h5ad": "x",
                "output_abundance_tsv": "y",
            },
        }
    )


def test_training_output_paths_false_when_paths_empty() -> None:
    assert not cell2location_training_output_paths_in_provenance(
        {
            "status": "trained_ok",
            "training": {"output_result_h5ad": "", "output_abundance_tsv": "y"},
        }
    )


def test_cell2location_followup_messages_training_failed() -> None:
    c2l = {"status": "training_failed", "training_error": "ValueError: bad"}
    msgs = cell2location_followup_messages(c2l)
    assert msgs
    assert "ValueError: bad" in msgs[0]
    assert len(msgs) == 1


def test_cell2location_followup_messages_training_failed_long_error_omits_detail() -> None:
    c2l = {"status": "training_failed", "training_error": "x" * 300}
    msgs = cell2location_followup_messages(c2l)
    assert msgs
    assert "Detail:" not in msgs[0]
    assert len(msgs) == 1


def test_cell2location_followup_messages_include_signature_extract_diagnostic() -> None:
    c2l = {
        "status": "training_failed",
        "training_error": "RuntimeError: extract failed",
        "signature_extract_diagnostic": {
            "varm_keys": ["means_per_cluster_mu_fg"],
            "uns_mod_keys": ["factor_names"],
            "uns_top_factor_keys": ["factor_names"],
            "var_prefix_means": ["means_per_cluster_mu_fg_A"],
        },
    }
    msgs = cell2location_followup_messages(c2l)
    assert len(msgs) >= 2
    assert "RuntimeError: extract failed" in msgs[0]
    assert any("signature_extract_diagnostic" in m for m in msgs[1:])
    assert any("means_per_cluster_mu_fg" in m for m in msgs[1:])


def test_cell2location_followup_messages_include_both_diagnostics_when_present() -> None:
    c2l = {
        "status": "training_failed",
        "training_error": "RuntimeError: failed",
        "signature_extract_diagnostic": {"varm_keys": ["k"]},
        "gene_intersection_diagnostic": {
            "n_spatial_var": 10,
            "n_signature_rows": 10,
            "n_shared_genes": 1,
            "min_shared_genes_required": 10,
        },
    }
    msgs = cell2location_followup_messages(c2l)
    assert len(msgs) >= 3
    assert any("signature_extract_diagnostic" in m for m in msgs[1:])
    assert any("gene_intersection_diagnostic" in m for m in msgs[1:])


def test_cell2location_followup_messages_include_gene_intersection_diagnostic() -> None:
    c2l = {
        "status": "training_failed",
        "training_error": "RuntimeError: too few genes",
        "gene_intersection_diagnostic": {
            "n_spatial_var": 18000,
            "n_signature_rows": 15000,
            "n_shared_genes": 2,
            "min_shared_genes_required": 10,
        },
    }
    msgs = cell2location_followup_messages(c2l)
    assert len(msgs) >= 2
    assert "too few genes" in msgs[0]
    assert any("gene_intersection_diagnostic" in m for m in msgs[1:])
    assert any("n_shared_genes=2" in m for m in msgs[1:])
    assert any("min_shared_genes_required=10" in m for m in msgs[1:])


def test_cell2location_followup_messages_inputs_ok_but_training_enabled() -> None:
    c2l = {"status": "inputs_ok", "training_enabled": True, "cell2location_import_ok": True}
    msgs = cell2location_followup_messages(c2l)
    assert len(msgs) == 1
    assert "inputs_ok" in msgs[0]


def test_cell2location_followup_messages_empty_when_ok() -> None:
    assert cell2location_followup_messages({"status": "trained_ok"}) == []
    assert cell2location_followup_messages({"status": "inputs_ok", "training_enabled": False}) == []


def test_cell2location_has_signature_extract_diagnostic() -> None:
    assert not cell2location_has_signature_extract_diagnostic(None)
    assert not cell2location_has_signature_extract_diagnostic({})
    assert not cell2location_has_signature_extract_diagnostic({"signature_extract_diagnostic": {}})
    assert cell2location_has_signature_extract_diagnostic(
        {"signature_extract_diagnostic": {"varm_keys": []}}
    )


def test_cell2location_has_gene_intersection_diagnostic() -> None:
    assert not cell2location_has_gene_intersection_diagnostic(None)
    assert not cell2location_has_gene_intersection_diagnostic({})
    assert not cell2location_has_gene_intersection_diagnostic({"gene_intersection_diagnostic": {}})
    assert cell2location_has_gene_intersection_diagnostic(
        {"gene_intersection_diagnostic": {"n_shared_genes": 0, "min_shared_genes_required": 10}}
    )
