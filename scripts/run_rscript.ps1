# Run Rscript without adding R\bin to PATH. Same resolution as Snakemake (rscript_resolve.py).
# Usage (from repo root):  powershell -File scripts/run_rscript.ps1 --version
#                          powershell -File scripts/run_rscript.ps1 scripts/m2_movics_intnmf_tcga_gbm.R config/m2_movics_run.yaml

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
Push-Location $RepoRoot
try {
    $exe = (python "$PSScriptRoot/rscript_resolve.py").Trim()
    if (-not (Test-Path -LiteralPath $exe)) {
        Write-Error "Resolved Rscript missing: $exe - run: python scripts/configure_r_for_snakemake.py"
    }
    & $exe @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
