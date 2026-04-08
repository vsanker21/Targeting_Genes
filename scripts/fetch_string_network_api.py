#!/usr/bin/env python3
"""
Fetch STRING protein–protein network edges for HGNC symbol lists (DEA STRING exports).

Uses STRING public HTTP API (POST recommended). Please be polite: one request per job,
caller_identity set. See https://string-db.org/help/api/

Config: config/module2_integration.yaml → string_api_network_fetch

Outputs one JSON per job (edges as parsed TSV rows) plus aggregate provenance JSON.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_symbols(path: Path, *, max_genes: int) -> list[str]:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if s and not s.startswith("#"):
            lines.append(s)
    return lines[:max_genes]


def fetch_network_tsv(
    symbols: list[str],
    *,
    api_base: str,
    species: int,
    required_score: int,
    network_type: str,
    timeout_s: int,
) -> tuple[list[dict[str, str]], str]:
    if not symbols:
        return [], ""
    url = f"{api_base.rstrip('/')}/tsv/network"
    params = {
        "identifiers": "\r".join(symbols),
        "species": species,
        "required_score": required_score,
        "network_type": network_type,
        "caller_identity": "glioma-target-pipeline",
    }
    time.sleep(1.0)
    r = requests.post(url, data=params, timeout=timeout_s)
    r.raise_for_status()
    text = r.text.strip()
    if not text:
        return [], text
    rows_out: list[dict[str, str]] = []
    lines = text.splitlines()
    if not lines:
        return [], text
    header = lines[0].split("\t")
    for line in lines[1:]:
        parts = line.split("\t")
        rows_out.append({header[i]: parts[i] if i < len(parts) else "" for i in range(len(header))})
    return rows_out, text


def main() -> int:
    ap = argparse.ArgumentParser(description="STRING API network fetch for DEA symbol lists.")
    ap.add_argument(
        "--config",
        default="config/module2_integration.yaml",
        help="Path under repo root (default: config/module2_integration.yaml)",
    )
    args = ap.parse_args()
    rr = repo_root()
    cfg_path = (rr / args.config.replace("/", os.sep)).resolve()
    if not cfg_path.is_file():
        print(f"Missing {cfg_path}", file=sys.stderr)
        return 1

    doc = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    block = doc.get("string_api_network_fetch") or {}
    if not block.get("enabled", True):
        print("string_api_network_fetch disabled; writing skip provenance only.")
        prov = {
            "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
            "skipped": True,
            "jobs": [],
        }
        out_p = rr / "results/module4/string_api/string_api_fetch_provenance.json"
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(prov, indent=2), encoding="utf-8")
        print(f"Wrote {out_p}")
        return 0

    api_base = str(block.get("string_api_base", "https://string-db.org/api"))
    species = int(block.get("species_tax_id", 9606))
    max_genes = int(block.get("network_max_genes", 400))
    required_score = int(block.get("required_score", 400))
    network_type = str(block.get("network_type", "functional"))
    timeout_s = int(block.get("request_timeout_s", 120))
    jobs = block.get("jobs") or []
    if not jobs:
        print("No string_api_network_fetch.jobs configured", file=sys.stderr)
        return 1

    job_results: list[dict[str, Any]] = []
    for j in jobs:
        jid = str(j.get("job_id", "job"))
        inp = rr / str(j.get("input_symbols_txt", "")).replace("/", os.sep)
        outp = rr / str(j.get("output_json", "")).replace("/", os.sep)
        if not inp.is_file():
            print(f"MISSING input {inp} for job {jid}", file=sys.stderr)
            return 1
        symbols = read_symbols(inp, max_genes=max_genes)
        raw_head = ""
        if not symbols:
            edges: list[dict[str, str]] = []
        else:
            try:
                edges, raw_head = fetch_network_tsv(
                    symbols,
                    api_base=api_base,
                    species=species,
                    required_score=required_score,
                    network_type=network_type,
                    timeout_s=timeout_s,
                )
            except (requests.RequestException, OSError) as e:
                print(f"STRING API error for {jid}: {e}", file=sys.stderr)
                return 1

        payload = {
            "job_id": jid,
            "input_symbols_txt": str(inp.relative_to(rr)).replace("\\", "/"),
            "n_symbols_submitted": len(symbols),
            "n_edges": len(edges),
            "species_tax_id": species,
            "api_base": api_base,
            "required_score": required_score,
            "network_type": network_type,
            "edges": edges,
            "raw_tsv_preview": (raw_head[:2000] if len(raw_head) > 2000 else raw_head),
        }
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        job_results.append(
            {
                "job_id": jid,
                "output_json": str(outp.relative_to(rr)).replace("\\", "/"),
                "n_symbols_submitted": len(symbols),
                "n_edges": len(edges),
                "ok": True,
            }
        )
        print(f"ok  {jid}: {len(symbols)} symbols → {len(edges)} edges → {outp}")

    prov = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "string_api_base": api_base,
        "species_tax_id": species,
        "jobs": job_results,
    }
    prov_p = rr / "results/module4/string_api/string_api_fetch_provenance.json"
    prov_p.parent.mkdir(parents=True, exist_ok=True)
    prov_p.write_text(json.dumps(prov, indent=2), encoding="utf-8")
    print(f"Wrote {prov_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
