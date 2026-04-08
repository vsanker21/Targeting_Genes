#!/usr/bin/env python3
"""
Programmatically install and *functionally* verify optional third-party stack.

  1) pip install -r requirements-optional.txt (cmapPy + deps)
  2) cmapPy: in-memory GCToo -> write_gct -> parse_gct round-trip (must match)
  3) GNINA: optional conda bootstrap into <repo>/.conda_envs/gnina if not on PATH
  4) Cell Ranger / Space Ranger: smoke-test --version or --help when found or env override

Exit 0 only when all *enforced* checks pass (see flags).

Usage:
  python scripts/ensure_optional_third_party_functional.py
  python scripts/ensure_optional_third_party_functional.py --require-10x-tools
  python scripts/ensure_optional_third_party_functional.py --no-bootstrap-gnina
  python scripts/ensure_optional_third_party_functional.py --skip-pip
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_tooling() -> dict[str, Any]:
    p = repo_root() / "config" / "third_party_tooling.yaml"
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    return doc.get("third_party_tooling") or {}


def pip_install_optional(rr: Path) -> None:
    req = rr / "requirements-optional.txt"
    if not req.is_file():
        raise FileNotFoundError(str(req))
    print("pip install -r requirements-optional.txt …", flush=True)
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", str(req)],
        cwd=str(rr),
    )


def functional_cmap_py_gct_roundtrip() -> None:
    """Import cmapPy IO stack and verify write_gct/parse round-trip."""
    import cmapPy.pandasGEXpress.GCToo as GCToo
    import cmapPy.pandasGEXpress.parse_gct as pg
    import cmapPy.pandasGEXpress.write_gct as wg

    data_df = pd.DataFrame(
        [[1.0, 2.0], [3.0, 4.0]],
        index=pd.Index(["g1", "g2"], name="rid"),
        columns=pd.Index(["s1", "s2"], name="cid"),
        dtype=np.float32,
    )
    gctoo = GCToo.GCToo(data_df=data_df)
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "ensure_cmapPy_smoke.gct"
        wg.write(gctoo, str(out), data_null="NaN", metadata_null="-666", filler_null="-666")
        parsed = pg.parse(str(out))
        pd.testing.assert_frame_equal(parsed.data_df, gctoo.data_df)
    print("ok  cmapPy functional: GCT write + parse round-trip", flush=True)


def gnina_exe_in_prefix(prefix: Path) -> Path | None:
    win = prefix / "Scripts" / "gnina.exe"
    if win.is_file():
        return win
    ux = prefix / "bin" / "gnina"
    if ux.is_file():
        return ux
    return None


def conda_bootstrap_gnina(rr: Path, tooling: dict[str, Any]) -> Path | None:
    """conda create -p <repo>/.conda_envs/gnina gnina python -c conda-forge"""
    rel = str(tooling.get("conda_gnina_prefix_relative", ".conda_envs/gnina"))
    prefix = (rr / rel.replace("/", os.sep)).resolve()
    existing = gnina_exe_in_prefix(prefix)
    if existing:
        print(f"ok  GNINA already present at {existing}", flush=True)
        return existing

    conda = shutil.which("conda")
    if not conda:
        print("SKIP conda bootstrap GNINA: conda not on PATH", file=sys.stderr)
        return None

    prefix.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        conda,
        "create",
        "-y",
        "-p",
        str(prefix),
        "-c",
        "conda-forge",
        "python=3.11",
        "gnina",
    ]
    print(" ".join(cmd), "…", flush=True)
    try:
        subprocess.check_call(cmd, timeout=3600)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"FAIL conda bootstrap GNINA: {e}", file=sys.stderr)
        return None

    exe = gnina_exe_in_prefix(prefix)
    if exe:
        print(f"ok  GNINA installed at {exe}", flush=True)
    return exe


def resolve_binary(
    b: dict[str, Any],
    env_overrides: dict[str, str],
    *,
    rr: Path,
) -> Path | None:
    bid = str(b.get("id", ""))
    envk = env_overrides.get(bid, "")
    if envk:
        raw = os.environ.get(envk, "").strip()
        if raw:
            p = Path(raw)
            if p.is_file():
                return p
    for name in b.get("exe_candidates") or []:
        w = shutil.which(str(name))
        if w:
            return Path(w)
    # Search under data_root tools (cellranger unpack)
    dr = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if not dr:
        try:
            ds = yaml.safe_load((rr / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
            dr = str(ds.get("data_root", "")).replace("/", os.sep)
        except OSError:
            dr = ""
    if dr and bid == "cellranger":
        base = Path(dr) / "tools" / "cellranger"
        if base.is_dir():
            for pat in ("**/cellranger.exe", "**/cellranger"):
                for hit in base.glob(pat):
                    if hit.is_file():
                        return hit
    return None


def smoke_binary(path: Path, *, tool_id: str) -> tuple[bool, str]:
    if tool_id == "gnina":
        cmd = [str(path), "--help"]
    else:
        cmd = [str(path), "--version"]
    try:
        kw: dict[str, Any] = {}
        if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            kw["creationflags"] = subprocess.CREATE_NO_WINDOW
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            **kw,
        )
        out = (r.stdout or r.stderr or "").strip()[:500]
        if r.returncode == 0 or (tool_id == "gnina" and r.returncode in (0, 1) and "gnina" in out.lower()):
            return True, out.splitlines()[0] if out else "ok"
        return False, out or f"exit {r.returncode}"
    except OSError as e:
        return False, str(e)


def main() -> int:
    ap = argparse.ArgumentParser(description="Install + functionally verify optional third-party tools.")
    ap.add_argument(
        "--require-10x-tools",
        action="store_true",
        help="Fail if cellranger and spaceranger are not runnable (PATH, env, or data_root/tools/cellranger).",
    )
    ap.add_argument(
        "--bootstrap-gnina",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="If gnina not found, try: conda create -p <repo>/.conda_envs/gnina … (default: on)",
    )
    ap.add_argument(
        "--gnina-required",
        action=argparse.BooleanOptionalAction,
        default=(platform.system() != "Windows"),
        help="Fail if GNINA is not runnable (default: required on non-Windows, optional on Windows).",
    )
    ap.add_argument(
        "--json-out",
        default="results/optional_third_party_functional_report.json",
        help="Write machine-readable report (default under results/)",
    )
    ap.add_argument(
        "--skip-pip",
        action="store_true",
        help="Skip pip install -r requirements-optional.txt (use when cmapPy is already installed).",
    )
    args = ap.parse_args()
    rr = repo_root()
    tooling = load_tooling()
    env_overrides = {str(k): str(v) for k, v in (tooling.get("binary_env_overrides") or {}).items()}

    report: dict[str, Any] = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "checks": [],
    }

    try:
        if not args.skip_pip:
            pip_install_optional(rr)
        functional_cmap_py_gct_roundtrip()
        report["checks"].append({"id": "cmapPy_pip", "ok": True, "skipped": bool(args.skip_pip)})
        report["checks"].append({"id": "cmapPy_gct_roundtrip", "ok": True})
    except Exception as e:
        report["checks"].append({"id": "cmapPy", "ok": False, "error": str(e)})
        _write_report(rr, args.json_out, report)
        print(f"FAIL cmapPy: {e}", file=sys.stderr)
        return 1

    gnina_spec = next((x for x in tooling.get("binaries") or [] if x.get("id") == "gnina"), None)
    if not gnina_spec:
        print("FAIL: third_party_tooling.yaml missing gnina binary spec", file=sys.stderr)
        return 1
    gnina_path = resolve_binary(gnina_spec, env_overrides, rr=rr)
    if gnina_path is None and args.bootstrap_gnina:
        gnina_path = conda_bootstrap_gnina(rr, tooling)

    gnina_ok = False
    gnina_msg = ""
    if gnina_path and gnina_path.is_file():
        gnina_ok, gnina_msg = smoke_binary(gnina_path, tool_id="gnina")
        print(f"{'ok ' if gnina_ok else 'FAIL '} GNINA smoke: {gnina_path} ({gnina_msg})")
    else:
        print("FAIL GNINA: not installed (set GLIOMA_TARGET_GNINA_EXE, add to PATH, or enable conda bootstrap)", file=sys.stderr)
    report["checks"].append({"id": "gnina", "ok": gnina_ok, "path": str(gnina_path) if gnina_path else None, "detail": gnina_msg})

    tenx_ok = True
    for bid in ("cellranger", "spaceranger"):
        b = next((x for x in tooling.get("binaries") or [] if x.get("id") == bid), None)
        if not b:
            report["checks"].append({"id": bid, "ok": False, "error": "missing yaml spec"})
            tenx_ok = False
            continue
        p = resolve_binary(b, env_overrides, rr=rr)
        if p is None:
            print(f"MISSING {bid}: not on PATH / env / data_root/tools/cellranger", flush=True)
            report["checks"].append({"id": bid, "ok": False, "path": None})
            tenx_ok = False
            continue
        ok, msg = smoke_binary(p, tool_id=bid)
        print(f"{'ok ' if ok else 'FAIL '} {bid}: {p} ({msg})", flush=True)
        report["checks"].append({"id": bid, "ok": ok, "path": str(p), "detail": msg})
        if not ok:
            tenx_ok = False

    _write_report(rr, args.json_out, report)

    if not gnina_ok and args.gnina_required:
        return 1
    if not gnina_ok and not args.gnina_required:
        print("WARN GNINA missing; continuing (GNINA optional on this platform / --no-gnina-required).", file=sys.stderr)
    if args.require_10x_tools and not tenx_ok:
        print("FAIL: --require-10x-tools and Cell Ranger tools not fully available", file=sys.stderr)
        return 1

    ok_bits = ["cmapPy functional"]
    if gnina_ok:
        ok_bits.append("GNINA runnable")
    print(f"\nensure_optional_third_party_functional: SUCCESS ({', '.join(ok_bits)}).", flush=True)
    if not tenx_ok and not args.require_10x_tools:
        print("(10x tools optional this run; use --require-10x-tools to enforce.)", flush=True)
    return 0


def _write_report(rr: Path, rel: str, report: dict[str, Any]) -> None:
    out = rr / rel.replace("/", os.sep)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
