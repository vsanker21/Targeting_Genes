#!/usr/bin/env python3
"""Check that key paths under GLIOMA_TARGET_DATA_ROOT (or config) exist."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env_root = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    if env_root:
        data_root = Path(env_root)
    else:
        try:
            import yaml
        except ImportError:
            print("Need PyYAML or set GLIOMA_TARGET_DATA_ROOT", file=sys.stderr)
            return 1
        cfg = yaml.safe_load((root / "config" / "data_sources.yaml").read_text(encoding="utf-8"))
        data_root = Path(cfg["data_root"])

    checks = [
        ("TCGA-GBM", data_root / "tcga" / "TCGA-GBM"),
        ("GEO GSE57872", data_root / "geo" / "scrna_seq" / "GSE57872"),
        ("Dryad spatial_gbm", data_root / "dryad" / "spatial_gbm"),
        ("SRA GSE57872 counts", data_root / "sra" / "GSE57872" / "counts"),
        ("GEO bulk GSE4290", data_root / "geo" / "bulk_microarray" / "GSE4290" / "matrix"),
        ("GTEx Xena TPM", data_root / "gtex" / "xena_toil" / "TcgaTargetGtex_rsem_gene_tpm.gz"),
        ("GDC manifest", data_root / "gdc" / "tcga_gbm_open_star_counts" / "gdc_files_manifest.json"),
        ("GENCODE GTF", data_root / "references" / "gencode.v44.annotation.gtf.gz"),
        ("HGNC complete", data_root / "references" / "hgnc_complete_set.txt"),
    ]
    ok = True
    for label, p in checks:
        exists = p.exists()
        status = "OK" if exists else "MISSING"
        if not exists:
            ok = False
        print(f"{status}\t{label}\t{p}")

    dep_root = data_root / "depmap"
    dep_models = list(dep_root.glob("**/Model.csv")) if dep_root.is_dir() else []
    if not dep_models:
        print(f"MISSING\tDepMap Model.csv\t(under {dep_root})")
        ok = False
    else:
        print(f"OK\tDepMap Model.csv\t{dep_models[0]}")

    pipe_git = data_root / "pipelines" / "nf-core-rnaseq" / ".git"
    if pipe_git.is_dir():
        print(f"OK\tGit pipeline nf-core-rnaseq\t{pipe_git.parent}")
    else:
        print(f"WARN\tGit pipelines\t(not cloned; run download_all_required without --skip-git)")

    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
