#!/usr/bin/env python3
"""
Download public datasets referenced by GLIOMA-TARGET but not bundled with the GBM Detection mirror.

- GEO: series matrix + SOFT from NCBI FTP (matrix/ and soft/ subdirs).
- GTEx / TCGA reference expression: TOIL Xena hub (phenotype + optional full gene TPM matrix).

Requires network. Set GLIOMA_TARGET_DATA_ROOT to override the default data root.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable

USER_AGENT = "Mozilla/5.0 (compatible; GLIOMA-TARGET/1.0; +https://github.com/)"
# Long reads for multi-GB transfers over slow links
HTTP_TIMEOUT = int(os.environ.get("GLIOMA_TARGET_HTTP_TIMEOUT", "600"))

# Project outline: bulk microarray cohorts for tumor vs normal DEA context.
DEFAULT_GEO_BULK_SERIES = (
    "GSE4290",
    "GSE7696",
    "GSE50161",
    "GSE68848",
)

TOIL_PHENOTYPE = "https://toil.xenahubs.net/download/TcgaTargetGTEX_phenotype.txt.gz"
TOIL_GENE_TPM = "https://toil.xenahubs.net/download/TcgaTargetGtex_rsem_gene_tpm.gz"


def data_root() -> Path:
    env = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env:
        return Path(env)
    here = Path(__file__).resolve().parents[1]
    cfg = here / "config" / "data_sources.yaml"
    if cfg.is_file():
        try:
            import yaml

            dr = yaml.safe_load(cfg.read_text(encoding="utf-8")).get("data_root", "")
            if dr:
                return Path(dr.replace("/", os.sep))
        except ImportError:
            pass
    return Path(r"G:\GBM Detection\data")


def geo_parent_dir(gse: str) -> str:
    n = int(gse.replace("GSE", "", 1))
    return f"GSE{n // 1000}nnn"


def list_geo_subdir(url: str) -> list[str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        html = resp.read().decode("utf-8", "replace")
    out: list[str] = []
    for m in re.finditer(r'href="([^"]+)"', html):
        name = m.group(1)
        if name in ("../", "./") or name.startswith("http"):
            continue
        out.append(name.rstrip("/"))
    return out


def download_file(url: str, dest: Path, chunk: int = 1 << 20) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        total = resp.headers.get("Content-Length")
        total_n = int(total) if total and total.isdigit() else None
        got = 0
        with open(tmp, "wb") as f:
            while True:
                block = resp.read(chunk)
                if not block:
                    break
                f.write(block)
                got += len(block)
        if total_n is not None and got != total_n:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"Size mismatch for {url}: got {got}, expected {total_n}")
    tmp.replace(dest)


def download_file_resume(url: str, dest: Path, chunk: int = 1 << 20) -> None:
    """Download large file with optional HTTP Range resume into *.partial."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    expected = head_length(url)
    if dest.is_file() and expected is not None and dest.stat().st_size == expected:
        return

    partial = dest.with_suffix(dest.suffix + ".partial")
    existing = partial.stat().st_size if partial.is_file() else 0
    headers: dict[str, str] = {"User-Agent": USER_AGENT}
    if existing:
        headers["Range"] = f"bytes={existing}-"

    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=HTTP_TIMEOUT)
    except urllib.error.HTTPError as e:
        if e.code == 416 and partial.is_file() and expected is not None and partial.stat().st_size >= expected:
            partial.replace(dest)
            return
        raise
    try:
        status = resp.getcode()
        if status == 200 and existing:
            # Server ignored Range; restart from scratch.
            resp.close()
            partial.unlink(missing_ok=True)
            existing = 0
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            resp = urllib.request.urlopen(req, timeout=HTTP_TIMEOUT)
            status = resp.getcode()

        mode = "ab" if status == 206 and existing else "wb"
        if mode == "wb" and partial.exists():
            partial.unlink()
            existing = 0

        with open(partial, mode) as f:
            while True:
                block = resp.read(chunk)
                if not block:
                    break
                f.write(block)
    finally:
        resp.close()

    if expected is not None and partial.stat().st_size != expected:
        raise RuntimeError(
            f"Incomplete download {url}: size {partial.stat().st_size}, expected {expected}"
        )
    partial.replace(dest)


def download_geo_series(gse: str, out_root: Path) -> list[Path]:
    parent = geo_parent_dir(gse)
    base = f"https://ftp.ncbi.nlm.nih.gov/geo/series/{parent}/{gse}/"
    target = out_root / "geo" / "bulk_microarray" / gse
    target.mkdir(parents=True, exist_ok=True)
    manifest = target / "download_manifest.json"
    saved: list[Path] = []
    for sub in ("matrix", "soft"):
        url = base + sub + "/"
        try:
            names = list_geo_subdir(url)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
        for name in names:
            if not name.endswith(".gz"):
                continue
            file_url = base + sub + "/" + name
            dest = target / sub / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.is_file() and dest.stat().st_size > 0:
                saved.append(dest)
                continue
            print(f"  GET {file_url}")
            download_file(file_url, dest)
            saved.append(dest)
    manifest.write_text(
        json.dumps({"gse": gse, "base": base, "files": [str(p) for p in saved]}, indent=2),
        encoding="utf-8",
    )
    return saved


def head_length(url: str) -> int | None:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=min(HTTP_TIMEOUT, 120)) as r:
            cl = r.headers.get("Content-Length")
            return int(cl) if cl and cl.isdigit() else None
    except Exception:
        return None


def download_gtex_xena(out_root: Path, include_full_tpm: bool) -> list[Path]:
    gtex_dir = out_root / "gtex" / "xena_toil"
    gtex_dir.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []

    pheno = gtex_dir / "TcgaTargetGTEX_phenotype.txt.gz"
    if not pheno.is_file() or pheno.stat().st_size == 0:
        print(f"  GET {TOIL_PHENOTYPE}")
        download_file(TOIL_PHENOTYPE, pheno)
    out.append(pheno)

    tpm_path = gtex_dir / "TcgaTargetGtex_rsem_gene_tpm.gz"
    if include_full_tpm:
        expected = head_length(TOIL_GENE_TPM)
        if tpm_path.is_file() and expected and tpm_path.stat().st_size == expected:
            print(f"  SKIP (complete) {tpm_path.name}")
        else:
            print(f"  GET (large, ~1.3 GB) {TOIL_GENE_TPM}")
            t0 = time.time()
            download_file_resume(TOIL_GENE_TPM, tpm_path)
            print(f"  done in {time.time() - t0:.1f}s")
        out.append(tpm_path)

    (gtex_dir / "README.txt").write_text(
        "TcgaTargetGTEX_phenotype.txt.gz — sample metadata (tissue, study).\n"
        "TcgaTargetGtex_rsem_gene_tpm.gz — TOIL RSEM gene TPM for TCGA+GTEx targets.\n"
        "Source: https://xenabrowser.net/ (TOIL RNA-seq hub).\n",
        encoding="utf-8",
    )
    return out


def parse_args(argv: Iterable[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--geo-series",
        nargs="*",
        default=list(DEFAULT_GEO_BULK_SERIES),
        help="GEO series accessions (default: outline bulk microarray set).",
    )
    p.add_argument("--skip-geo", action="store_true")
    p.add_argument("--skip-gtex", action="store_true")
    p.add_argument(
        "--no-gtex-tpm",
        action="store_true",
        help="Only download GTEx/TCGA phenotype; skip the ~1.3 GB gene TPM matrix.",
    )
    return p.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    root = data_root()
    print(f"data_root: {root.resolve()}")
    if not root.is_dir():
        print("ERROR: data_root does not exist.", file=sys.stderr)
        return 1

    try:
        if not args.skip_geo:
            for gse in args.geo_series:
                print(f"GEO {gse}")
                download_geo_series(gse, root)
        if not args.skip_gtex:
            print("GTEx / TOIL Xena")
            download_gtex_xena(root, include_full_tpm=not args.no_gtex_tpm)
    except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    print("OK — downloads finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
