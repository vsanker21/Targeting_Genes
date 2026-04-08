#!/usr/bin/env python3
"""
Install or upgrade R (Windows), then refresh config/rscript_local.yaml for Snakemake edgeR rules.

Windows strategies (see --method):
  auto   — try winget, then download latest CRAN R-*-win.exe and silent-install
  winget — winget install/upgrade RProject.R only
  cran   — CRAN installer only

After a successful install, calls configure_r_for_snakemake.persist_discovered_rscript() so
Snakefile _rscript_exe() resolves the correct Rscript path (registry / Program Files).

Requires: Administrator elevation is often required for silent installers into Program Files.

Usage:
  python scripts/install_r_for_snakemake.py
  python scripts/install_r_for_snakemake.py --upgrade
  python scripts/install_r_for_snakemake.py --method cran --dry-run
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import configure_r_for_snakemake as _cfg  # noqa: E402

USER_AGENT = "TargetingGenes-install-r/1.0 (python urllib)"
CRAN_WIN_BASE = "https://cran.r-project.org/bin/windows/base/"
WINGET_ID = "RProject.R"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run(cmd: list[str], *, dry_run: bool) -> int:
    print("Running:", " ".join(cmd))
    if dry_run:
        return 0
    r = subprocess.run(cmd, check=False)
    return r.returncode


def _winget_cmd(subcommand: str, *, dry_run: bool) -> int:
    """subcommand is 'install' or 'upgrade'."""
    winget = shutil.which("winget")
    if not winget:
        return 127
    cmd = [
        winget,
        subcommand,
        "-e",
        "--id",
        WINGET_ID,
        "--accept-package-agreements",
        "--accept-source-agreements",
        "--silent",
    ]
    return _run(cmd, dry_run=dry_run)


def install_via_winget(*, upgrade: bool, dry_run: bool) -> bool:
    if not shutil.which("winget"):
        print("winget not on PATH; skipping winget.", file=sys.stderr)
        return False

    if upgrade:
        code = _winget_cmd("upgrade", dry_run=dry_run)
        if code == 0:
            return True
        print("winget upgrade exited", code, "(continuing with install if needed)", file=sys.stderr)

    code = _winget_cmd("install", dry_run=dry_run)
    if code == 0:
        return True

    if not upgrade:
        code2 = _winget_cmd("upgrade", dry_run=dry_run)
        if code2 == 0:
            return True

    print("winget install/upgrade failed; try an elevated terminal (Run as administrator).", file=sys.stderr)
    return False


def latest_cran_win_exe_url() -> tuple[str, str]:
    req = urllib.request.Request(CRAN_WIN_BASE, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    pairs = re.findall(
        r'href\s*=\s*"(R-(\d+)\.(\d+)\.(\d+)-win\.exe)"',
        html,
        flags=re.I,
    )
    if not pairs:
        raise RuntimeError(f"No R-x.y.z-win.exe link found on {CRAN_WIN_BASE}")

    def key(t: tuple[str, str, str, str]) -> tuple[int, int, int]:
        _, a, b, c = t
        return (int(a), int(b), int(c))

    best = max(pairs, key=key)
    rel = best[0]
    ver = f"{best[1]}.{best[2]}.{best[3]}"
    return CRAN_WIN_BASE + rel, ver


def install_via_cran(*, dry_run: bool) -> bool:
    url, ver = latest_cran_win_exe_url()
    print(f"CRAN installer: {url} (version {ver})")
    if dry_run:
        return True

    tmp = Path(tempfile.gettempdir()) / f"R-{ver}-win-install-targeting-genes.exe"
    print(f"Downloading to {tmp} …")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=600) as resp:
        tmp.write_bytes(resp.read())

    # Inno Setup style (CRAN Windows builds)
    code = subprocess.run(
        [str(tmp), "/VERYSILENT", "/NORESTART", "/SUPPRESSMSGBOXES"],
        check=False,
    ).returncode
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass

    if code != 0:
        print(
            f"Installer exited {code}. Run the .exe as Administrator or use winget.",
            file=sys.stderr,
        )
        return False
    return True


def install_macos_brew(*, dry_run: bool) -> bool:
    brew = shutil.which("brew")
    if not brew:
        return False
    code = _run([brew, "install", "--cask", "r"], dry_run=dry_run)
    return code == 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--method",
        choices=("auto", "winget", "cran"),
        default="auto",
        help="How to install on Windows (default: auto).",
    )
    ap.add_argument(
        "--upgrade",
        action="store_true",
        help="Prefer winget upgrade before install (Windows).",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print actions only; do not install or write files.")
    ap.add_argument(
        "--write-config-yaml",
        action="store_true",
        help="Also set rscript: in config/config.yaml after discovery.",
    )
    ap.add_argument(
        "--sync-only",
        action="store_true",
        help="Do not install; only run R discovery and write rscript_local.yaml.",
    )
    args = ap.parse_args()

    rr = repo_root()

    if args.sync_only:
        _, code = _cfg.persist_discovered_rscript(
            dry_run=args.dry_run,
            write_config_yaml=args.write_config_yaml,
            rr=rr,
        )
        return code

    if sys.platform == "win32":
        ok = False
        if args.method in ("auto", "winget"):
            ok = install_via_winget(upgrade=args.upgrade, dry_run=args.dry_run)
        if not ok and args.method in ("auto", "cran"):
            ok = install_via_cran(dry_run=args.dry_run)
        if not ok and not args.dry_run:
            existing = _cfg.discover_rscript()
            if existing is not None:
                print(
                    f"Install step did not report success, but Rscript exists at {existing}; syncing path.",
                    file=sys.stderr,
                )
            else:
                print(
                    "Install step did not report success. Fix errors above, or install R manually from "
                    "https://cran.r-project.org/bin/windows/base/ then run:\n"
                    "  python scripts/configure_r_for_snakemake.py",
                    file=sys.stderr,
                )
                return 1
    elif sys.platform == "darwin":
        ok = install_macos_brew(dry_run=args.dry_run)
        if not ok and not args.dry_run and _cfg.discover_rscript() is None:
            print(
                "Homebrew cask 'r' failed or brew missing. Install R, then:\n"
                "  python scripts/configure_r_for_snakemake.py",
                file=sys.stderr,
            )
            return 1
    else:
        if _cfg.discover_rscript() is None:
            print(
                "On Linux install R with your distro (e.g. sudo apt install r-base), then run:\n"
                "  python scripts/configure_r_for_snakemake.py",
                file=sys.stderr,
            )
            return 1
        print("Linux: R already on PATH; syncing config/rscript_local.yaml.", file=sys.stderr)

    found, code = _cfg.persist_discovered_rscript(
        dry_run=args.dry_run,
        write_config_yaml=args.write_config_yaml,
        rr=rr,
        banner_note="Path refreshed after scripts/install_r_for_snakemake.py",
    )
    if code != 0 and not args.dry_run:
        print(
            "Install reported success but Rscript was not found yet. "
            "Open a new terminal (refreshes PATH) and run: python scripts/configure_r_for_snakemake.py",
            file=sys.stderr,
        )
        return 1
    if found and not args.dry_run:
        print(f"Rscript pinned for Snakemake: {found}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
