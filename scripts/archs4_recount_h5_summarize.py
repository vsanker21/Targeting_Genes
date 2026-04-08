#!/usr/bin/env python3
"""Lightweight HDF5 inventory for ARCHS4/recount gtex_matrix.h5 + tcga_matrix.h5 (requires h5py)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

_REPO = Path(__file__).resolve().parents[1]


def _data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((_REPO / "config/data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def _summarize_h5(path: Path) -> dict[str, Any]:
    try:
        import h5py
    except ImportError:
        return {"path": str(path), "error": "h5py_not_installed", "hint": "pip install h5py"}
    if not path.is_file():
        return {"path": str(path), "error": "missing_file"}
    out: dict[str, Any] = {"path": str(path), "size_bytes": path.stat().st_size}
    try:
        with h5py.File(path, "r") as h5:
            def visitor(name: str, obj: Any) -> None:
                if hasattr(obj, "shape"):
                    out.setdefault("datasets", []).append(
                        {"name": name, "shape": list(obj.shape), "dtype": str(obj.dtype)}
                    )

            out["root_keys"] = list(h5.keys())
            h5.visititems(visitor)
    except OSError as e:
        out["error"] = str(e)
    return out


def main() -> int:
    dr = _data_root()
    doc = yaml.safe_load((_REPO / "config/data_sources.yaml").read_text(encoding="utf-8"))
    sub = doc.get("references") or {}
    ad = sub.get("archs4_recount_dir")
    if not isinstance(ad, str):
        print("Missing references.archs4_recount_dir", file=sys.stderr)
        return 1
    base = Path(ad.replace("{data_root}", str(dr)).replace("/", os.sep))
    gtex = base / "gtex_matrix.h5"
    tcga = base / "tcga_matrix.h5"
    payload = {
        "data_root": str(dr.resolve()),
        "gtex_matrix": _summarize_h5(gtex),
        "tcga_matrix": _summarize_h5(tcga),
    }
    out = _REPO / "results/module4/archs4_recount_h5_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
