#!/usr/bin/env python3
"""
Record whether DrugCentral was loaded into PostgreSQL or skipped.

If GLIOMA_TARGET_DRUGCENTRAL_LOAD=1 and psql is available, runs load_drugcentral_postgres.py.
Otherwise writes a skip report (success exit 0).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def main() -> int:
    out = _REPO / "results/module4/drugcentral_postgres_load_status.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    db = os.environ.get("GLIOMA_TARGET_DRUGCENTRAL_DATABASE", "drugcentral").strip() or "drugcentral"

    if not _truthy("GLIOMA_TARGET_DRUGCENTRAL_LOAD"):
        payload = {
            "status": "skipped",
            "reason": "GLIOMA_TARGET_DRUGCENTRAL_LOAD not set to 1",
            "hint": "Set GLIOMA_TARGET_DRUGCENTRAL_LOAD=1 and PG* or --dsn, then re-run this script or the Snakemake rule.",
        }
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {out} (skipped)")
        return 0

    psql = shutil.which("psql")
    if not psql:
        payload = {
            "status": "failed",
            "reason": "psql not on PATH",
        }
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print("psql not found; wrote failure status", file=sys.stderr)
        return 0

    r = subprocess.run(
        [
            sys.executable,
            str(_REPO / "scripts" / "load_drugcentral_postgres.py"),
            "--database",
            db,
            "--create-db",
        ],
        cwd=str(_REPO),
    )
    payload = {
        "status": "loaded" if r.returncode == 0 else "failed",
        "database": db,
        "returncode": r.returncode,
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    # Always exit 0 so Snakemake records outcome in JSON (inspect status/returncode).
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
