"""Minimal fake ``cell2location`` / ``cell2location.models`` for tests (no GPU, no real fit)."""

from __future__ import annotations

import types


def fake_cell2location_modules() -> tuple[types.ModuleType, types.ModuleType]:
    """Return ``(fake_pkg, fake_models)`` suitable for ``sys.modules`` injection."""

    class RegressionModel:
        @staticmethod
        def setup_anndata(**kwargs: object) -> None:
            pass

        def __init__(self, adata: object) -> None:
            self._adata = adata

        def train(self, **kwargs: object) -> None:
            pass

        def export_posterior(self, adata: object, sample_kwargs: object | None = None) -> object:
            return adata

    class Cell2location:
        @staticmethod
        def setup_anndata(**kwargs: object) -> None:
            pass

        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def train(self, **kwargs: object) -> None:
            pass

        def export_posterior(self, adata: object, sample_kwargs: object | None = None) -> object:
            return adata

    fake_models = types.ModuleType("cell2location.models")
    fake_models.RegressionModel = RegressionModel
    fake_models.Cell2location = Cell2location
    fake_pkg = types.ModuleType("cell2location")
    fake_pkg.models = fake_models
    return fake_pkg, fake_models
