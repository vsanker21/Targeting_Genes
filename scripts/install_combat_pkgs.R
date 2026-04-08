# CRAN + Bioconductor packages for scripts/combat_seq_tcga_gbm_subset.R (sva::ComBat_seq)

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

if (!requireNamespace("sva", quietly = TRUE)) {
  message("Installing Bioconductor package: sva")
  BiocManager::install("sva", ask = FALSE, update = FALSE)
}

message("ComBat-Seq dependency check OK: yaml, jsonlite, arrow, sva")
