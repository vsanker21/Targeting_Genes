#!/usr/bin/env python3
"""
Rank compounds by Pearson correlation with an Entrez disease signature.

Requires a real long-format perturbation TSV (compound_id, entrez_id, z_score) under
data_root — see config/m5_srges.yaml. No synthetic or placeholder reference data.

Config: config/m5_srges.yaml — m5_srges_run
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
from collections import defaultdict
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


def _read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def resolve_signature_tsv(rr: Path, m5_inputs: dict[str, Any], job_tag: str) -> Path:
    for job in (m5_inputs.get("lincs_disease_signature") or {}).get("jobs") or []:
        if str(job.get("tag", "")) == job_tag:
            rel = str(job.get("output_tsv", ""))
            if rel:
                return rr / rel.replace("/", os.sep)
    raise SystemExit(f"No lincs_disease_signature job with tag={job_tag!r} in config/module5_inputs.yaml")


def load_signature_entrez_weights(path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f, delimiter="\t")
        if not r.fieldnames or "entrez_id" not in r.fieldnames:
            raise SystemExit(f"Expected entrez_id column in {path}")
        wcol = "signed_neglog10_p" if "signed_neglog10_p" in r.fieldnames else r.fieldnames[1]
        for row in r:
            e = str(row["entrez_id"]).strip()
            if not e:
                continue
            try:
                out[e] = float(row[wcol])
            except (KeyError, ValueError):
                continue
    if len(out) < 10:
        raise SystemExit(f"Too few signature rows in {path}")
    return out


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 3 or n != len(ys):
        return float("nan")
    mx = sum(xs) / n
    my = sum(ys) / n
    vx = sum((a - mx) ** 2 for a in xs)
    vy = sum((b - my) ** 2 for b in ys)
    if vx < 1e-18 or vy < 1e-18:
        return 0.0
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    return cov / math.sqrt(vx * vy)


def resolve_perturbation_path(rr: Path, pt_template: str) -> Path:
    dr = data_root()
    ptxt = str(pt_template).replace("{data_root}", str(dr)).replace("/", os.sep)
    ppath = Path(ptxt)
    if not ppath.is_absolute():
        rel = str(pt_template).replace("{data_root}/", "").replace("{data_root}", "").strip("/\\")
        ppath = dr / rel.replace("/", os.sep)
    return ppath


def load_perturbation_long(path: Path) -> dict[str, dict[str, float]]:
    by_c: dict[str, dict[str, float]] = defaultdict(dict)
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f, delimiter="\t")
        need = {"compound_id", "entrez_id", "z_score"}
        if not r.fieldnames or not need.issubset({x.strip() for x in r.fieldnames}):
            raise SystemExit(f"perturbation_tsv needs columns {sorted(need)}; got {r.fieldnames}")
        col_c = next(c for c in r.fieldnames if c.strip() == "compound_id")
        col_e = next(c for c in r.fieldnames if c.strip() == "entrez_id")
        col_z = next(c for c in r.fieldnames if c.strip() == "z_score")
        for row in r:
            cid = str(row[col_c]).strip()
            e = str(row[col_e]).strip()
            if not cid or not e:
                continue
            try:
                by_c[cid][e] = float(row[col_z])
            except (KeyError, ValueError):
                continue
    if not by_c:
        raise SystemExit(f"No rows parsed from perturbation_tsv {path}")
    return dict(by_c)


def compound_scores_from_tsv(genes: list[str], sig: dict[str, float], by_c: dict[str, dict[str, float]]) -> list[tuple[str, float]]:
    wvec = [float(sig[g]) for g in genes]
    scores: list[tuple[str, float]] = []
    for cid, zmap in sorted(by_c.items()):
        zvec = [float(zmap.get(g, 0.0)) for g in genes]
        scores.append((cid, pearson(wvec, zvec)))
    scores.sort(key=lambda t: (-(t[1] if not math.isnan(t[1]) else -1e9), t[0]))
    return scores


def main() -> int:
    rr = repo_root()
    cfg_path = rr / "config" / "m5_srges.yaml"
    if not cfg_path.is_file():
        print(f"Missing {cfg_path}", file=sys.stderr)
        return 1
    doc = _read_yaml(cfg_path)
    block = doc.get("m5_srges_run") or {}
    if not block.get("enabled", True):
        print("m5_srges_run disabled")
        return 0

    pt = block.get("perturbation_tsv")
    if not pt:
        print("m5_srges_run requires perturbation_tsv in config/m5_srges.yaml", file=sys.stderr)
        return 1

    m5_inputs = _read_yaml(rr / "config" / "module5_inputs.yaml")
    job_tag = str(block.get("signature_job_tag", "welch"))
    sig_rel = block.get("signature_tsv")
    if sig_rel:
        sig_path = rr / str(sig_rel).replace("/", os.sep)
    else:
        sig_path = resolve_signature_tsv(rr, m5_inputs, job_tag)
    if not sig_path.is_file():
        print(f"Missing signature TSV {sig_path}", file=sys.stderr)
        return 1

    ppath = resolve_perturbation_path(rr, str(pt))
    if not ppath.is_file():
        print(
            f"Missing perturbation_tsv {ppath} — stage a real compound×entrez z-score table under data_root.",
            file=sys.stderr,
        )
        return 1

    sig = load_signature_entrez_weights(sig_path)
    genes_sorted = sorted(sig.keys())
    by_c = load_perturbation_long(ppath)
    ranked = compound_scores_from_tsv(genes_sorted, sig, by_c)

    rank_rel = str(block.get("rank_tsv", "results/module5/m5_srges_compound_ranks.tsv"))
    prov_rel = str(block.get("provenance_json", "results/module5/m5_srges_run_provenance.json"))
    flag_rel = str(block.get("done_flag", "results/module5/m5_srges_run.flag"))

    rank_path = rr / rank_rel.replace("/", os.sep)
    prov_path = rr / prov_rel.replace("/", os.sep)
    flag_path = rr / flag_rel.replace("/", os.sep)
    rank_path.parent.mkdir(parents=True, exist_ok=True)

    with rank_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["rank", "compound_id", "connectivity_score_pearson_r"])
        for i, (cid, sc) in enumerate(ranked, start=1):
            w.writerow([i, cid, f"{sc:.6g}" if not math.isnan(sc) else ""])

    try:
        sig_display = str(sig_path.resolve().relative_to(rr.resolve())).replace(os.sep, "/")
    except ValueError:
        sig_display = str(sig_path)

    prov = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "status": "ok",
        "reference_mode": "perturbation_tsv",
        "perturbation_tsv": str(ppath),
        "signature_tsv": sig_display,
        "signature_job_tag": job_tag,
        "n_genes_in_signature": len(sig),
        "n_genes_used_for_scoring": len(genes_sorted),
        "n_compounds_ranked": len(ranked),
        "rank_tsv": rank_rel.replace(os.sep, "/"),
        "note": (
            "Ranking from user perturbation_tsv vs disease signature; not full cmapPy sRGES on L1000 GCTX. "
            "Stage cmapPy/CLUE exports under data_root/lincs/srges_rank_score_exports for m5_srges_output_paths_status."
        ),
    }
    prov_path.write_text(json.dumps(prov, indent=2), encoding="utf-8")
    flag_path.write_text("ok\n", encoding="utf-8")
    print(f"Wrote {rank_path} ({len(ranked)} compounds)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
