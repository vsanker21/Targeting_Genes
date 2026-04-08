"""Regression tests for ``tests/cell2location_test_doubles`` (shared fake cell2location stack)."""

from __future__ import annotations

from cell2location_test_doubles import fake_cell2location_modules


def test_fake_cell2location_modules_exposes_regression_and_spatial_classes() -> None:
    pkg, models = fake_cell2location_modules()
    assert pkg.models is models
    assert callable(models.RegressionModel)
    assert callable(models.Cell2location)
    assert hasattr(models.RegressionModel, "setup_anndata")
    assert hasattr(models.Cell2location, "setup_anndata")
