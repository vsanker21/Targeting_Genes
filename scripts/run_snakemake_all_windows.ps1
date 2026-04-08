# Full DAG on Windows: UTF-8 for Python subprocesses + optional supplementary wiring.
# This script forwards your current environment to snakemake (unlike run_windows_outline_gate.py,
# which strips GLIOMA_TARGET_INCLUDE_* for its snakemake all step — see scripts/snakemake_subprocess_env.py).
# Usage:
#   .\scripts\run_snakemake_all_windows.ps1
#   $env:GLIOMA_TARGET_INCLUDE_SUPPLEMENTARY_WIRING = "1"; .\scripts\run_snakemake_all_windows.ps1
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
Set-Location (Split-Path (Split-Path $PSScriptRoot))
if (-not $env:GLIOMA_TARGET_DATA_ROOT) {
    Write-Host "Set GLIOMA_TARGET_DATA_ROOT to your data tree (see config/data_sources.yaml)."
}
snakemake @args
