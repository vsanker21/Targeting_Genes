#!/usr/bin/env python3
"""
Verify optional third-party stack: pip packages (cmapPy), PATH binaries (Cell Ranger, Space Ranger, GNINA),
and optional data_root marker paths from config/third_party_tooling.yaml.

Exit 0 always unless --strict (then exit 1 if any pip import or required binary missing).

Core pipeline does not require these. Install: install_optional_third_party.py; functional I/O gate:
ensure_optional_third_party_functional.py; CI parity: run_optional_stack_ci.py.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    cfg = yaml.safe_load((repo_root() / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
    return Path(cfg["data_root"].replace("/", os.sep))


def load_tooling_cfg() -> dict[str, Any]:
    p = repo_root() / "config" / "third_party_tooling.yaml"
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    return doc.get("third_party_tooling") or {}


def check_pip_optional(rr: Path, block: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    req_name = block.get("pip_requirements_optional", "requirements-optional.txt")
    req_path = rr / str(req_name)
    import_map: dict[str, str] = dict(block.get("pip_import_names") or {})
    rows: list[dict[str, Any]] = []
    failures: list[str] = []

    if not req_path.is_file():
        rows.append({"kind": "pip_optional_file", "path": str(req_name), "exists": False})
        failures.append("requirements-optional.txt missing")
        return rows, failures

    packages: list[str] = []
    for line in req_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = line.split(";", 1)[0].strip()
        for sep in ("==", ">=", "<=", "~=", "!=", "<", ">"):
            if sep in name:
                name = name.split(sep, 1)[0].strip()
                break
        packages.append(name)

    for pkg in packages:
        mod = import_map.get(pkg, import_map.get(pkg.lower(), pkg.lower().replace("-", "_")))
        spec = importlib.util.find_spec(mod)
        ok = spec is not None
        rows.append(
            {
                "kind": "pip_import",
                "package": pkg,
                "import_module": mod,
                "importable": ok,
                "origin": getattr(spec, "origin", None) if spec else None,
            }
        )
        if not ok:
            failures.append(f"pip:{pkg}")

    return rows, failures


def check_binaries(block: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for b in block.get("binaries") or []:
        bid = str(b.get("id", ""))
        names = list(b.get("exe_candidates") or [])
        found: str | None = None
        for n in names:
            w = shutil.which(n)
            if w:
                found = w
                break
        rows.append(
            {
                "kind": "binary",
                "id": bid,
                "display_name": b.get("display_name", bid),
                "resolved_path": found,
                "on_path": found is not None,
                "install_note": b.get("install_note"),
            }
        )
        if not found:
            failures.append(f"binary:{bid}")
    return rows, failures


def check_optional_paths(block: dict[str, Any], dr: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in block.get("optional_path_checks") or []:
        tmpl = str(item.get("path_template", "")).replace("{data_root}", str(dr)).replace("/", os.sep)
        p = Path(tmpl)
        rows.append(
            {
                "kind": "data_root_marker",
                "name": item.get("name", ""),
                "path": str(p),
                "exists": p.is_file() or p.is_dir(),
                "note": item.get("note"),
            }
        )
    return rows


def conda_gnina_listed() -> dict[str, Any]:
    conda = shutil.which("conda")
    if not conda:
        return {"kind": "conda_gnina", "checked": False, "reason": "conda not on PATH"}
    try:
        prefix = os.environ.get("CONDA_PREFIX", "").strip()
        cmd = [conda, "list", "-p", prefix, "--json"] if prefix else [conda, "list", "--json"]
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "")[:800]
            try:
                ej = json.loads(r.stdout or "{}")
                if isinstance(ej, dict) and ej.get("error"):
                    err = str(ej.get("error", ""))[:800]
            except json.JSONDecodeError:
                pass
            return {
                "kind": "conda_gnina",
                "checked": True,
                "installed": False,
                "conda_list_failed": True,
                "detail": err,
            }
        data = json.loads(r.stdout or "[]")
        # conda list --json returns list of dicts with "name" key
        names = {str(x.get("name", "")).lower() for x in data if isinstance(x, dict)}
        return {"kind": "conda_gnina", "checked": True, "installed": "gnina" in names}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        return {"kind": "conda_gnina", "checked": True, "error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify optional third-party tooling.")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any package from requirements-optional.txt fails to import (after pip install)",
    )
    ap.add_argument(
        "--strict-binaries",
        action="store_true",
        help="Also exit 1 if Cell Ranger, Space Ranger, or GNINA are not found on PATH",
    )
    ap.add_argument(
        "--json-out",
        default="results/third_party_tooling_status.json",
        help="Write detailed status JSON under repo (default: results/third_party_tooling_status.json)",
    )
    args = ap.parse_args()
    rr = repo_root()
    dr = data_root()
    block = load_tooling_cfg()

    pip_rows, pip_fail = check_pip_optional(rr, block)
    bin_rows, bin_fail = check_binaries(block)
    path_rows = check_optional_paths(block, dr)
    conda_row = conda_gnina_listed()

    summary = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "data_root": str(dr.resolve()),
        "pip_optional": pip_rows,
        "binaries": bin_rows,
        "data_root_markers": path_rows,
        "conda": conda_row,
        "failures_if_strict": pip_fail + bin_fail,
        "note": "Binaries (Cell Ranger, GNINA) are not pip-installable; use vendor/conda instructions in third_party_tooling.yaml.",
    }

    out_rel = args.json_out.strip() or "results/third_party_tooling_status.json"
    out_path = rr / out_rel.replace("/", os.sep)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")

    for row in pip_rows:
        if row.get("kind") == "pip_import":
            st = "ok " if row.get("importable") else "MISSING "
            print(f"{st} pip import {row.get('package')} -> {row.get('import_module')}")
    for row in bin_rows:
        st = "ok " if row.get("on_path") else "MISSING "
        print(f"{st} PATH {row.get('id')}: {row.get('resolved_path') or '(not found)'}")
    if conda_row.get("checked"):
        print(f"conda gnina package present: {conda_row.get('installed')}")

    pip_strict = list(pip_fail)
    bin_strict = list(bin_fail) if args.strict_binaries else []

    if args.strict and pip_strict:
        print(f"\n--strict: pip import(s) failed: {pip_strict}", file=sys.stderr)
        return 1
    if args.strict_binaries and bin_strict:
        print(f"\n--strict-binaries: not on PATH: {bin_strict}", file=sys.stderr)
        return 1

    all_warn = pip_fail + bin_fail
    if all_warn:
        print(f"\n(non-fatal) {len(all_warn)} optional item(s) not satisfied: {all_warn}")
        print("Python extras: python scripts/install_optional_third_party.py")
        print("Functional I/O:  python scripts/ensure_optional_third_party_functional.py")
        print("CI parity:       python scripts/run_optional_stack_ci.py")
        print("GNINA (conda):   python scripts/install_optional_third_party.py --conda-gnina")
        print("Cell Ranger:     see config/third_party_tooling.yaml (10x Genomics download)")
    else:
        print("\nAll checked optional pip imports and PATH binaries are satisfied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
