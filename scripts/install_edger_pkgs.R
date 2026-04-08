# CRAN + Bioconductor packages for scripts/edger_tcga_gbm_two_group.R
# Invoked by: python scripts/install_r_edger_dependencies.py

repos <- "https://cloud.r-project.org"
ip <- tryCatch(rownames(installed.packages()), error = function(e) character())

need_cran <- c("yaml", "jsonlite", "arrow", "BiocManager")
miss <- setdiff(need_cran, ip)
if (length(miss) > 0L) {
  message("Installing CRAN packages: ", paste(miss, collapse = ", "))
  install.packages(miss, repos = repos, quiet = FALSE)
}

if (!requireNamespace("BiocManager", quietly = TRUE)) {
  stop("BiocManager failed to install")
}

bio <- c("edgeR", "limma")
miss_bio <- bio[vapply(bio, function(p) !requireNamespace(p, quietly = TRUE), logical(1L))]
if (length(miss_bio) > 0L) {
  message("Installing Bioconductor packages: ", paste(miss_bio, collapse = ", "))
  BiocManager::install(miss_bio, ask = FALSE, update = FALSE)
}

message("edgeR dependency check OK: yaml, jsonlite, arrow, edgeR, limma")
