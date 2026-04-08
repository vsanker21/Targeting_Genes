# CRAN + GitHub packages for MOVICS::getIntNMF (m2_movics_intnmf_tcga_gbm.R, m2_movics_intnmf_depmap_mae.R).
# Invoked by: python scripts/install_r_movics_dependencies.py

repos <- "https://cloud.r-project.org"
ip <- tryCatch(rownames(installed.packages()), error = function(e) character())

need_cran <- c("yaml", "jsonlite", "arrow", "BiocManager", "remotes")
miss <- setdiff(need_cran, ip)
if (length(miss) > 0L) {
  message("Installing CRAN packages: ", paste(miss, collapse = ", "))
  install.packages(miss, repos = repos, quiet = FALSE)
}

if (!requireNamespace("BiocManager", quietly = TRUE)) {
  stop("BiocManager failed to install")
}

if (!requireNamespace("remotes", quietly = TRUE)) {
  stop("remotes failed to install")
}

# SNFtool (MOVICS dependency) lists heatmap.plus, which was removed from active CRAN (archived 2021).
heatmap_plus_url <-
  "https://cran.r-project.org/src/contrib/Archive/heatmap.plus/heatmap.plus_1.3.tar.gz"
if (!requireNamespace("heatmap.plus", quietly = TRUE)) {
  message("Installing heatmap.plus from CRAN Archive (SNFtool / MOVICS dependency)...")
  op <- options(timeout = max(600, getOption("timeout")))
  install.packages(heatmap_plus_url, repos = NULL, type = "source", quiet = FALSE)
  options(op)
}
if (!requireNamespace("heatmap.plus", quietly = TRUE)) {
  stop(
    "heatmap.plus install failed. On Windows you may need Rtools for source packages: ",
    "https://cran.r-project.org/bin/windows/Rtools/ - match Rtools to your R version, then re-run this script."
  )
}

if (!requireNamespace("SNFtool", quietly = TRUE)) {
  message("Installing SNFtool from GitHub (MOVICS dependency)...")
  remotes::install_github("maxconway/SNFtool", ask = FALSE, upgrade = "never")
}
if (!requireNamespace("SNFtool", quietly = TRUE)) {
  stop("SNFtool installation failed after heatmap.plus; check messages above.")
}

if (!requireNamespace("MOVICS", quietly = TRUE)) {
  message("Installing MOVICS from GitHub (xlucpu/MOVICS) - may take several minutes.")
  remotes::install_github("xlucpu/MOVICS", ask = FALSE, upgrade = "never")
}

if (!requireNamespace("MOVICS", quietly = TRUE)) {
  stop("MOVICS installation failed; see https://github.com/xlucpu/MOVICS")
}

message("MOVICS dependency check OK: yaml, jsonlite, arrow, remotes, MOVICS")
