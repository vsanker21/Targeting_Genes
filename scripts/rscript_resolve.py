"""
Resolve Rscript path for Snakemake / CLI (Windows often lacks Rscript on PATH).

Order matches Snakefile _rscript_exe: RSCRIPT, GLIOMA_TARGET_RSCRIPT, R_HOME,
Windows R-core registry (InstallPath), config/rscript_local.yaml, config/config.yaml,
PATH, Program Files glob. R does not need to be on PATH if the registry entry or
rscript_local.yaml (from configure_r_for_snakemake.py) is present.
"""

from __future__ import annotations

import glob
import os
import shutil
import sys
from pathlib import Path

import yaml


def _try_winreg_rscript() -> Path | None:
    """Windows: R-core InstallPath from HKLM (same as configure_r_for_snakemake)."""
    if sys.platform != "win32":
        return None
    import winreg

    for key_path in (r"SOFTWARE\R-core\R", r"SOFTWARE\WOW6432Node\R-core\R"):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
                install, _ = winreg.QueryValueEx(k, "InstallPath")
        except OSError:
            continue
        cand = Path(install) / "bin" / "Rscript.exe"
        if cand.is_file():
            return cand.resolve()
    return None


def resolve_rscript(repo_root: Path | None = None) -> str:
    rr = repo_root or Path(__file__).resolve().parents[1]

    for key in ("RSCRIPT", "GLIOMA_TARGET_RSCRIPT"):
        exe = os.environ.get(key, "").strip().strip('"')
        if exe and Path(exe).is_file():
            return str(Path(exe).resolve())

    r_home = os.environ.get("R_HOME", "").strip().strip('"')
    if r_home:
        rh = Path(r_home)
        for name in ("Rscript.exe", "Rscript"):
            cand = rh / "bin" / name
            if cand.is_file():
                return str(cand.resolve())

    reg = _try_winreg_rscript()
    if reg is not None:
        return str(reg)

    local_r = rr / "config" / "rscript_local.yaml"
    if local_r.is_file():
        try:
            loc = yaml.safe_load(local_r.read_text(encoding="utf-8")) or {}
            p = (loc.get("rscript") or "").strip().strip('"')
            if p:
                exp = Path(p).expanduser()
                if exp.is_file():
                    return str(exp.resolve())
        except (OSError, yaml.YAMLError):
            pass

    cfg_path = rr / "config" / "config.yaml"
    if cfg_path.is_file():
        try:
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            p = (cfg.get("rscript") or "").strip().strip('"')
            if p:
                exp = Path(p).expanduser()
                if exp.is_file():
                    return str(exp.resolve())
        except (OSError, yaml.YAMLError):
            pass

    for name in ("Rscript", "Rscript.exe"):
        w = shutil.which(name)
        if w:
            return w

    if sys.platform == "win32":
        for pattern in (
            r"C:\Program Files\R\R-*\bin\Rscript.exe",
            r"C:\Program Files (x86)\R\R-*\bin\Rscript.exe",
        ):
            found = sorted(glob.glob(pattern), reverse=True)
            if found:
                return found[0]

    raise FileNotFoundError(
        "Could not find Rscript. Run: python scripts/configure_r_for_snakemake.py "
        "(writes config/rscript_local.yaml), or set R_HOME / RSCRIPT, or set rscript: in config/config.yaml"
    )


def main() -> int:
    print(resolve_rscript())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
