#!/usr/bin/env python3
"""
Orchestrate programmatic downloads for GLIOMA-TARGET using every practical method:

  • HTTPS / NCBI GEO FTP / TOIL Xena (urllib, same stack as download_external_datasets.py)
  • DepMap Portal API → signed Google Cloud Storage URLs (fresh CSV each run)
  • GDC REST API → open TCGA-GBM STAR gene count TSVs (parallel GETs)
  • Reference annotations (GENCODE, HGNC) from EBI FTP / GCS / GitHub raw
  • Shallow git clone of public pipelines (nf-core, cmapPy) when `git` is on PATH
  • LINCS / CLUE REST API JSON snapshots when CLUE_API_KEY or CLUE_API_TOKEN_FILE is set (token outside repo)
  • Optional: STRING-DB (very large), WSL+curl fallback on failure
  • Optional: open-source extensions (MSigDB GMTs, MCP-counter genes, …) — config/open_source_data_extensions.yaml;
    run with --with-open-extensions or scripts/download_open_source_extensions.py
  • Optional: high-value public layers (GDSC, PRISM, Open Targets, GDC methylation beta, CELLxGENE Census h5ad, CGGA hook) —
    config/high_value_public_datasets.yaml; run with --with-high-value-datasets or scripts/download_high_value_public_datasets.py
  • Optional: supplementary references (Expression Atlas gene TSVs, ARCHS4/recount HDF5, WikiPathways + PathwayCommons GMT,
    ChEMBL UniProt map + DGIdb, ClinVar gene summary, gnomAD LOF-by-gene; optional DrugCentral) —
    config/supplementary_reference_resources.yaml; run with --with-supplementary-reference-resources or
    scripts/download_supplementary_reference_resources.py

CGGA: add HTTPS URLs to config/m2_movics_data_fetch.yaml and run scripts/fetch_movics_staging_data.py
(or download_all_required.py --with-movics-staging). Controlled CPTAC / Synapse protected objects
still require credentials and are not bulk-fetched here.
LINCS CLUE only: scripts/fetch_clue_api_subset.py (needs CLUE_API_KEY or CLUE_API_TOKEN_FILE).
Set GLIOMA_TARGET_DATA_ROOT to override the data directory (default from config/data_sources.yaml).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml

# Reuse GEO / TOIL helpers
sys.path.insert(0, str(Path(__file__).resolve().parent))
import download_external_datasets as ext  # noqa: E402

DEPMAP_FILES_CSV = "https://depmap.org/portal/api/download/files"
GDC_FILES_ENDPOINT = "https://api.gdc.cancer.gov/files"
GDC_DATA_ENDPOINT = "https://api.gdc.cancer.gov/data"

STRING_PROTEIN_LINKS = (
    "https://stringdb-static.org/download/protein.links.v12.0/9606.protein.links.v12.0.txt.gz"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_yaml(name: str) -> dict[str, Any]:
    p = _repo_root() / "config" / name
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def wsl_curl_download(url: str, dest: Path) -> bool:
    """Fallback: WSL curl when native download fails (e.g. flaky TLS)."""
    try:
        dest = dest.resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.drive:
            return False
        drive = dest.drive.rstrip(":").lower()
        rest = str(dest).split(":", 1)[1].replace("\\", "/")
        wsl_path = f"/mnt/{drive}{rest}"
        subprocess.run(
            ["wsl", "-e", "curl", "-fL", "--retry", "3", "-o", wsl_path, url],
            check=True,
            timeout=ext.HTTP_TIMEOUT * 3,
            capture_output=True,
        )
        return dest.is_file() and dest.stat().st_size > 0
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return False


def download_with_fallback(url: str, dest: Path, resume: bool = False) -> None:
    try:
        if resume:
            ext.download_file_resume(url, dest)
        else:
            ext.download_file(url, dest)
    except Exception as e:
        print(f"  primary download failed ({e}); trying WSL curl …")
        if not wsl_curl_download(url, dest):
            raise


def depmap_release_key(release: str) -> tuple[int, int]:
    m = re.search(r"(\d{2})Q(\d)", release or "")
    if not m:
        return (-1, -1)
    return int(m.group(1)), int(m.group(2))


def fetch_depmap_rows() -> list[dict[str, str]]:
    req = urllib.request.Request(DEPMAP_FILES_CSV, headers={"User-Agent": ext.USER_AGENT})
    with urllib.request.urlopen(req, timeout=ext.HTTP_TIMEOUT) as r:
        text = r.read().decode("utf-8", "replace")
    return list(csv.DictReader(io.StringIO(text)))


def resolve_depmap_release(rows: list[dict[str, str]], prefer: str | None, want_names: list[str]) -> str:
    """Pick a portal release that contains every file in *want_names*.

    The DepMap files index mixes many release families (PRISM, Harmonized proteomics, …) whose
    names also contain YYQq patterns. Taking max(releases) by quarter alone can select a release
    that does not ship Model.csv / Omics* matrices — e.g. *Harmonized Public Proteomics 26Q1* ties
    *DepMap Public 26Q1* on (26, 1) but only has a handful of files.
    """
    rels = {r["release"] for r in rows if r.get("release")}
    if not rels:
        raise RuntimeError("DepMap files CSV contained no releases.")
    want = set(want_names)
    if not want:
        raise RuntimeError("depmap.files is empty in config/required_downloads.yaml.")

    def files_for(rel: str) -> set[str]:
        return {str(r.get("filename") or "") for r in rows if r.get("release") == rel}

    if prefer:
        if prefer not in rels:
            raise RuntimeError(
                f"depmap.prefer_release {prefer!r} not in portal index "
                f"(see https://depmap.org/portal/api/download/files)."
            )
        missing = want - files_for(prefer)
        if missing:
            raise RuntimeError(f"depmap.prefer_release {prefer!r} missing files: {sorted(missing)}")
        return prefer

    candidates = [rel for rel in rels if want <= files_for(rel)]
    if not candidates:
        raise RuntimeError(
            "No portal release contains all depmap.files from config/required_downloads.yaml. "
            f"Wanted: {sorted(want)}. "
            "Update filenames in YAML to match the portal index or set depmap.prefer_release."
        )

    def sort_key(rel: str) -> tuple[int, int, int, str]:
        y, q = depmap_release_key(rel)
        pub = 1 if rel.startswith("DepMap Public") else 0
        return (y, q, pub, rel)

    return max(candidates, key=sort_key)


def download_depmap_bundle(root: Path, cfg: dict[str, Any]) -> None:
    dm = cfg.get("depmap") or {}
    want_names: list[str] = list(dm.get("files") or [])
    prefer = dm.get("prefer_release") or None

    print("DepMap: fetching file index …")
    rows = fetch_depmap_rows()
    release = resolve_depmap_release(rows, prefer, want_names)
    print(f"DepMap: using release {release}")
    sub = [r for r in rows if r["release"] == release and r["filename"] in want_names]
    found = {r["filename"] for r in sub}
    missing = set(want_names) - found
    if missing:
        raise RuntimeError(f"DepMap release missing files: {sorted(missing)}")

    out_dir = root / "depmap" / re.sub(r"[^\w]+", "_", release).strip("_").lower()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []

    for row in sorted(sub, key=lambda x: x["filename"]):
        url = row["url"]
        dest = out_dir / row["filename"]
        print(f"  DepMap GET {row['filename']}")
        t0 = time.time()
        download_with_fallback(url, dest, resume=True)
        st = dest.stat().st_size
        manifest.append(
            {
                "filename": row["filename"],
                "path": str(dest),
                "bytes": st,
                "md5_expected": row.get("md5_hash"),
                "seconds": round(time.time() - t0, 2),
            }
        )

    (out_dir / "download_manifest.json").write_text(
        json.dumps({"release": release, "files": manifest}, indent=2),
        encoding="utf-8",
    )


def gdc_tcga_gbm_open_star_manifest() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    filters: dict[str, Any] = {
        "op": "and",
        "content": [
            {"op": "=", "content": {"field": "cases.project.project_id", "value": "TCGA-GBM"}},
            {"op": "=", "content": {"field": "access", "value": "open"}},
            {"op": "=", "content": {"field": "data_category", "value": "Transcriptome Profiling"}},
            {"op": "=", "content": {"field": "experimental_strategy", "value": "RNA-Seq"}},
            {"op": "=", "content": {"field": "data_format", "value": "TSV"}},
            {
                "op": "=",
                "content": {"field": "data_type", "value": "Gene Expression Quantification"},
            },
        ],
    }
    fields = ["file_id", "file_name", "file_size", "md5sum", "data_type"]
    hits: list[dict[str, Any]] = []
    page_size = 500
    offset = 0
    pagination: dict[str, Any] = {}
    while True:
        body = {
            "filters": filters,
            "fields": ",".join(fields),
            "format": "JSON",
            "size": page_size,
            "from": offset,
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            GDC_FILES_ENDPOINT,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": ext.USER_AGENT},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=ext.HTTP_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        chunk = payload["data"]["hits"]
        pagination = payload["data"]["pagination"]
        hits.extend(chunk)
        offset += len(chunk)
        if offset >= int(pagination.get("total", 0)) or not chunk:
            break
    return hits, pagination


def download_gdc_star_counts(root: Path, cfg: dict[str, Any], workers: int) -> None:
    gdc = cfg.get("gdc") or {}
    if not gdc.get("download_star_counts", True):
        print("GDC: skipping STAR counts (config download_star_counts: false)")
        return

    sub = gdc.get("star_counts_subdir", "gdc/tcga_gbm_open_star_counts")
    out_dir = root / sub.replace("/", os.sep)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("GDC: querying open TCGA-GBM RNA-Seq gene quantification TSVs …")
    hits, pagination = gdc_tcga_gbm_open_star_manifest()
    total = int(pagination.get("total", len(hits)))
    print(f"GDC: {len(hits)} / {total} files in manifest")

    meta_path = out_dir / "gdc_files_manifest.json"
    meta_path.write_text(json.dumps({"pagination": pagination, "hits": hits}, indent=2), encoding="utf-8")

    def one(hit: dict[str, Any]) -> tuple[str, str]:
        fid = hit["file_id"]
        fname = hit["file_name"]
        dest = out_dir / fname
        expected = int(hit["file_size"])
        if dest.is_file() and dest.stat().st_size == expected:
            return fname, "skip"
        url = f"{GDC_DATA_ENDPOINT}/{fid}"
        download_with_fallback(url, dest, resume=False)
        if dest.stat().st_size != expected:
            raise RuntimeError(f"size mismatch {fname}")
        return fname, "ok"

    print(f"GDC: downloading with {workers} workers …")
    errors: list[str] = []
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = [ex.submit(one, h) for h in hits]
        for fut in as_completed(futs):
            try:
                name, status = fut.result()
                done += 1
                if status != "skip" or done <= 3 or done % 50 == 0 or done == len(hits):
                    print(f"  [{status}] {name} ({done}/{len(hits)})")
            except Exception as e:
                errors.append(str(e))
                print(f"  [FAIL] {e}")
    if errors:
        raise RuntimeError(f"GDC downloads failed ({len(errors)}): {errors[:5]}")


def download_references(root: Path, cfg: dict[str, Any]) -> None:
    ref = cfg.get("references") or {}
    out = root / "references"
    out.mkdir(parents=True, exist_ok=True)
    mapping = {
        "gencode_gtf_gz": out / "gencode.v44.annotation.gtf.gz",
        "hgnc_complete_tsv": out / "hgnc_complete_set.txt",
        "encode_blacklist_hg38_gz": out / "hg38-blacklist.v2.bed.gz",
    }
    for key, dest_name in mapping.items():
        url = ref.get(key)
        if not url:
            continue
        dest = dest_name
        print(f"  REF GET {key}")
        download_with_fallback(url, dest, resume=True)
    (out / "README.txt").write_text(
        "GENCODE v44 GTF and HGNC complete set for gene ID harmonization.\n"
        "hg38-blacklist.v2.bed.gz from Boyle-Lab/Blacklist (GitHub raw) for alignment QC.\n",
        encoding="utf-8",
    )


def download_string_if_requested(root: Path, cfg: dict[str, Any]) -> None:
    opt = cfg.get("optional") or {}
    if not opt.get("string_protein_links"):
        return
    dest = root / "string" / "9606.protein.links.v12.0.txt.gz"
    print("STRING: protein links (large) …")
    download_with_fallback(STRING_PROTEIN_LINKS, dest, resume=True)


def load_clue_api_key() -> str | None:
    """Read CLUE user_key from env or external file (first line). Never read from inside this repo."""
    for env in ("CLUE_API_KEY", "user_key"):
        k = os.environ.get(env, "").strip()
        if k:
            return k
    path = os.environ.get("CLUE_API_TOKEN_FILE", "").strip()
    if not path:
        return None
    p = Path(path).expanduser()
    if not p.is_file():
        print(f"CLUE: CLUE_API_TOKEN_FILE not found: {p}", file=sys.stderr)
        return None
    try:
        line = p.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    except OSError as e:
        print(f"CLUE: could not read token file: {e}", file=sys.stderr)
        return None
    return line or None


def _win_path_to_wsl(p: Path) -> str:
    p = p.resolve()
    if not p.drive:
        raise RuntimeError(f"Cannot map path to WSL: {p}")
    drive = p.drive.rstrip(":").lower()
    rest = str(p).split(":", 1)[1].replace("\\", "/")
    return f"/mnt/{drive}{rest}"


def _git_clone_cmd(url: str, dest: Path, branch: str | None, use_wsl: bool) -> list[str]:
    if use_wsl:
        wsl_dest = _win_path_to_wsl(dest)
        cmd = ["wsl", "-e", "git", "clone", "--depth", "1", "--single-branch"]
        if branch:
            cmd += ["--branch", str(branch)]
        cmd += [url, wsl_dest]
    else:
        git_exe = shutil.which("git")
        assert git_exe
        cmd = [git_exe, "clone", "--depth", "1", "--single-branch"]
        if branch:
            cmd += ["--branch", str(branch)]
        cmd += [url, str(dest)]
    return cmd


def _resolve_git_strategy() -> tuple[bool, bool]:
    """Returns (use_wsl, ok). If ok is False, skip clones."""
    if shutil.which("git"):
        return False, True
    try:
        subprocess.run(
            ["wsl", "-e", "git", "--version"],
            capture_output=True,
            text=True,
            timeout=45,
            check=True,
        )
        return True, True
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False, False


def clone_git_pipelines(root: Path, cfg: dict[str, Any]) -> None:
    gp = cfg.get("git_pipelines") or {}
    if not gp.get("enabled", True):
        print("GIT: disabled in config.")
        return
    use_wsl, ok = _resolve_git_strategy()
    if not ok:
        print("GIT: no `git` on PATH and WSL git unavailable — skip shallow clones.")
        return
    if use_wsl:
        print("GIT: using WSL git (native git not on PATH).")
    for spec in gp.get("repos") or []:
        url = spec.get("url")
        rel = spec.get("path")
        if not url or not rel:
            continue
        dest = root / rel.replace("/", os.sep)
        if (dest / ".git").is_dir():
            print(f"  GIT skip (exists) {dest}")
            continue
        if dest.exists():
            raise RuntimeError(f"GIT: path exists but is not a git repo: {dest}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        br = spec.get("branch")
        cmd = _git_clone_cmd(url, dest, br, use_wsl)
        print(f"  GIT clone → {dest}")
        cp = subprocess.run(cmd, timeout=7200, capture_output=True, text=True)
        if cp.returncode != 0:
            msg = (cp.stderr or cp.stdout or "").strip() or f"exit {cp.returncode}"
            raise RuntimeError(f"git clone failed for {url}: {msg}")


def fetch_clue_json(base_url: str, path: str, filter_json: str | None, api_key: str) -> Any:
    base_url = base_url.rstrip("/")
    if filter_json:
        url = f"{base_url}{path}?filter={quote(filter_json, safe='')}"
    else:
        url = f"{base_url}{path}"
    req = urllib.request.Request(
        url,
        headers={"user_key": api_key, "User-Agent": ext.USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=ext.HTTP_TIMEOUT) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"CLUE HTTP {e.code} for {url}: {body}") from e
    return json.loads(raw.decode("utf-8"))


def download_clue_lincs_subset(root: Path, cfg: dict[str, Any], api_key: str) -> None:
    clue = cfg.get("clue_api") or {}
    if not clue.get("enabled_if_token", True):
        return
    base = clue.get("base_url") or "https://api.clue.io"
    sub = clue.get("out_subdir") or "lincs/clue_api_subset"
    out = root / sub.replace("/", os.sep)
    out.mkdir(parents=True, exist_ok=True)
    for snap in clue.get("snapshots") or []:
        name = snap.get("name")
        path = snap.get("path")
        if not name or not path:
            continue
        filt = snap.get("filter_json")
        print(f"  CLUE GET {path} → {name}")
        data = fetch_clue_json(base, path, filt, api_key)
        (out / name).write_text(json.dumps(data, indent=2), encoding="utf-8")
    (out / "README.txt").write_text(
        "JSON snapshots from https://api.clue.io (LINCS / CLUE).\n"
        "Requires user_key; do not commit keys. Regenerate with scripts/download_all_required.py.\n",
        encoding="utf-8",
    )


def probe_aws_cli() -> None:
    """Optional: verify AWS CLI can reach a public bucket (no credentials required for list)."""
    try:
        r = subprocess.run(
            ["aws", "s3", "ls", "s3://gdc-open-access/", "--no-sign-request"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if r.returncode == 0:
            print("AWS CLI: public GDC bucket list OK (first lines):\n", "\n".join(r.stdout.splitlines()[:5]))
        else:
            print("AWS CLI: gdc-open-access probe failed (install AWS CLI v2 to use S3 mirrors).")
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        print("AWS CLI: not available (optional).")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--skip-depmap", action="store_true")
    p.add_argument("--skip-gdc", action="store_true")
    p.add_argument("--skip-geo", action="store_true")
    p.add_argument("--skip-gtex", action="store_true")
    p.add_argument("--skip-references", action="store_true")
    p.add_argument("--no-gtex-tpm", action="store_true")
    p.add_argument("--with-string", action="store_true", help="Download STRING protein links (~large).")
    p.add_argument("--probe-aws", action="store_true", help="Run a no-auth AWS S3 ls against a public GDC prefix.")
    p.add_argument("--skip-git", action="store_true", help="Skip shallow git clones (nf-core, cmapPy).")
    p.add_argument(
        "--skip-clue",
        action="store_true",
        help="Skip CLUE API even if CLUE_API_KEY / CLUE_API_TOKEN_FILE is set.",
    )
    p.add_argument("--gdc-workers", type=int, default=6, help="Parallel GDC /data downloads.")
    p.add_argument(
        "--with-recount3-de-counts",
        action="store_true",
        help="Download recount3 TCGA-GBM + GTEx brain G029 gene sums (~320 MB) for harmonized count DE.",
    )
    p.add_argument(
        "--with-movics-staging",
        action="store_true",
        help="After other phases, run scripts/fetch_movics_staging_data.py (DepMap multi-omics MAE + CGGA URLs + CBTTC readme).",
    )
    p.add_argument(
        "--with-open-extensions",
        action="store_true",
        help="After references phase, run scripts/download_open_source_extensions.py (MSigDB GMTs, MCP-counter, optional GEO).",
    )
    p.add_argument(
        "--with-high-value-datasets",
        action="store_true",
        help="Run scripts/download_high_value_public_datasets.py (GDSC, PRISM, Open Targets, GDC methylation, CELLxGENE S3, CGGA hook).",
    )
    p.add_argument(
        "--skip-high-value-gdc-methylation",
        action="store_true",
        help="Forwarded to download_high_value_public_datasets.py (--skip-gdc-methylation).",
    )
    p.add_argument(
        "--with-supplementary-reference-resources",
        action="store_true",
        help="Run scripts/download_supplementary_reference_resources.py (Atlas genes, ARCHS4 matrices, pathways, drug–target priors, ClinVar/gnomAD).",
    )
    p.add_argument(
        "--skip-supplementary-archs4",
        action="store_true",
        help="Forwarded to download_supplementary_reference_resources.py (--skip-archs4-h5).",
    )
    p.add_argument(
        "--force-supplementary-archs4",
        action="store_true",
        help="Forwarded to download_supplementary_reference_resources.py (--force-archs4-h5); mutually exclusive with --skip-supplementary-archs4.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.skip_supplementary_archs4 and args.force_supplementary_archs4:
        print("ERROR: --skip-supplementary-archs4 and --force-supplementary-archs4 are mutually exclusive.", file=sys.stderr)
        return 1
    root = ext.data_root()
    print(f"data_root: {root.resolve()}")
    if not root.is_dir():
        print("ERROR: data_root does not exist.", file=sys.stderr)
        return 1

    cfg = _load_yaml("required_downloads.yaml")
    if args.with_string:
        cfg.setdefault("optional", {})["string_protein_links"] = True

    if args.probe_aws:
        probe_aws_cli()

    report: dict[str, Any] = {"data_root": str(root.resolve()), "started": time.time(), "phases": []}

    try:
        if not args.skip_geo:
            print("Phase: GEO bulk microarray …")
            for gse in cfg.get("geo_bulk_series") or []:
                print(f"  GEO {gse}")
                ext.download_geo_series(gse, root)
            report["phases"].append("geo_bulk")

        if not args.skip_gtex:
            print("Phase: TOIL Xena (GTEx + TCGA TPM) …")
            ext.download_gtex_xena(root, include_full_tpm=not args.no_gtex_tpm)
            report["phases"].append("gtex_toil")

        if not args.skip_references:
            print("Phase: reference annotations …")
            download_references(root, cfg)
            report["phases"].append("references")

        if args.with_open_extensions:
            print("Phase: open-source extensions (gene sets, deconvolution priors; see config/open_source_data_extensions.yaml) …")
            subprocess.check_call(
                [sys.executable, str(_repo_root() / "scripts" / "download_open_source_extensions.py")],
                cwd=str(_repo_root()),
                env={**os.environ},
            )
            report["phases"].append("open_source_extensions")

        if args.with_supplementary_reference_resources:
            print("Phase: supplementary reference resources (see config/supplementary_reference_resources.yaml) …")
            sup_cmd = [
                sys.executable,
                str(_repo_root() / "scripts" / "download_supplementary_reference_resources.py"),
            ]
            if args.skip_supplementary_archs4:
                sup_cmd.append("--skip-archs4-h5")
            if args.force_supplementary_archs4:
                sup_cmd.append("--force-archs4-h5")
            subprocess.check_call(sup_cmd, cwd=str(_repo_root()), env={**os.environ})
            report["phases"].append("supplementary_reference_resources")

        if args.with_high_value_datasets:
            print("Phase: high-value public datasets (see config/high_value_public_datasets.yaml) …")
            hv_cmd = [
                sys.executable,
                str(_repo_root() / "scripts" / "download_high_value_public_datasets.py"),
            ]
            if args.skip_high_value_gdc_methylation:
                hv_cmd.append("--skip-gdc-methylation")
            subprocess.check_call(hv_cmd, cwd=str(_repo_root()), env={**os.environ})
            report["phases"].append("high_value_public_datasets")

        if not args.skip_depmap:
            print("Phase: DepMap (API + cloud storage) …")
            download_depmap_bundle(root, cfg)
            report["phases"].append("depmap")

        if not args.skip_gdc:
            print("Phase: GDC open TCGA-GBM expression …")
            download_gdc_star_counts(root, cfg, workers=args.gdc_workers)
            report["phases"].append("gdc_star_counts")

        if args.with_recount3_de_counts or (cfg.get("recount3") or {}).get("download_harmonized_g029"):
            print("Phase: recount3 harmonized G029 gene sums (TCGA GBM + GTEx brain) …")
            subprocess.check_call(
                [sys.executable, str(_repo_root() / "scripts" / "download_recount3_harmonized_g029.py")],
                cwd=str(_repo_root()),
            )
            report["phases"].append("recount3_harmonized_g029")

        download_string_if_requested(root, cfg)
        if cfg.get("optional", {}).get("string_protein_links"):
            report["phases"].append("string")

        if not args.skip_git:
            print("Phase: shallow git clones (pipelines) …")
            clone_git_pipelines(root, cfg)
            report["phases"].append("git_pipelines")

        if not args.skip_clue:
            clue_key = load_clue_api_key()
            if clue_key:
                print("Phase: LINCS / CLUE API (token from env or CLUE_API_TOKEN_FILE) …")
                download_clue_lincs_subset(root, cfg, clue_key)
                report["phases"].append("clue_api")
            else:
                print(
                    "Phase: LINCS / CLUE API — skipped "
                    "(set CLUE_API_KEY or CLUE_API_TOKEN_FILE to a path outside the repo)."
                )

        if args.with_movics_staging:
            print("Phase: MOVICS / multi-omics staging (DepMap MAE, optional CGGA HTTP, CBTTC readme) …")
            subprocess.check_call(
                [sys.executable, str(_repo_root() / "scripts" / "fetch_movics_staging_data.py")],
                cwd=str(_repo_root()),
                env={**os.environ},
            )
            report["phases"].append("movics_staging")

    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        RuntimeError,
        OSError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
    ) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    report["finished"] = time.time()
    report["elapsed_sec"] = round(report["finished"] - report["started"], 2)
    out_report = _repo_root() / "results" / "download_all_report.json"
    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"OK — all requested phases done in {report['elapsed_sec']}s")
    print(f"Report: {out_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
