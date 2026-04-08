#!/usr/bin/env python3
"""
Stream DrugCentral .sql.gz into psql (PostgreSQL). Requires `psql` on PATH and a created empty database.

Example:
  python scripts/load_drugcentral_postgres.py --database drugcentral --create-db

Env: PGHOST, PGPORT, PGUSER, PGPASSWORD (or use --dsn for libpq connection string).
"""

from __future__ import annotations

import argparse
import gzip
import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dump",
        type=Path,
        default=None,
        help="Path to drugcentral *.sql.gz (default: from GLIOMA_TARGET_DATA_ROOT + data_sources layout)",
    )
    ap.add_argument("--database", type=str, required=True, help="Target PostgreSQL database name")
    ap.add_argument(
        "--create-db",
        action="store_true",
        help="Run createdb before load (uses same PG* env as psql)",
    )
    ap.add_argument(
        "--dsn",
        type=str,
        default="",
        help="Optional libpq connection string; if set, passed as psql --dbname=",
    )
    args = ap.parse_args()

    dump = args.dump
    if dump is None:
        try:
            import yaml
        except ImportError:
            print("Install PyYAML or pass --dump", file=sys.stderr)
            return 1
        repo = Path(__file__).resolve().parents[1]
        dr = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
        if not dr:
            doc = yaml.safe_load((repo / "config/data_sources.yaml").read_text(encoding="utf-8"))
            dr = str(doc.get("data_root", ""))
        if not dr:
            print("Set GLIOMA_TARGET_DATA_ROOT or pass --dump", file=sys.stderr)
            return 1
        doc = yaml.safe_load((repo / "config/data_sources.yaml").read_text(encoding="utf-8"))
        rel = (doc.get("references") or {}).get("drugcentral_dump_gz")
        if not isinstance(rel, str):
            print("data_sources.references.drugcentral_dump_gz missing", file=sys.stderr)
            return 1
        dump = Path(rel.replace("{data_root}", dr).replace("/", os.sep))
    dump = dump.resolve()
    if not dump.is_file():
        print(f"Dump not found: {dump}", file=sys.stderr)
        return 1

    psql = shutil.which("psql")
    if not psql:
        print("psql not on PATH", file=sys.stderr)
        return 1
    createdb = shutil.which("createdb")

    db_target = args.dsn.strip() if args.dsn.strip() else args.database

    if args.create_db:
        if not createdb:
            print("createdb not on PATH", file=sys.stderr)
            return 1
        r = subprocess.run([createdb, args.database], capture_output=True, text=True)
        if r.returncode != 0 and "already exists" not in (r.stderr + r.stdout).lower():
            print(r.stderr or r.stdout, file=sys.stderr)
            return r.returncode

    print(f"Loading {dump} into database (streamed) …")
    proc = subprocess.Popen(
        [psql, "--dbname", db_target, "-v", "ON_ERROR_STOP=1"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdin is not None
    try:
        with gzip.open(dump, "rb") as gz:
            shutil.copyfileobj(gz, proc.stdin, length=1024 * 1024)
    except Exception as e:
        proc.stdin.close()
        proc.kill()
        print(e, file=sys.stderr)
        return 1
    proc.stdin.close()
    out, err = proc.communicate()
    if proc.returncode != 0:
        print(err.decode("utf-8", "replace"), file=sys.stderr)
        return proc.returncode
    print("Load finished OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
