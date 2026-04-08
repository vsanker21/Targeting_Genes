# Install Bioconductor + CRAN packages for supplementary pathway enrichment (fgsea, clusterProfiler).
# Run once: Rscript scripts/install_r_supplementary_enrichment.R
# Or: python scripts/install_r_supplementary_dependencies.py
# Snakemake: rule install_r_supplementary_enrichment (touches results/r_supplementary_enrichment_packages.flag).

repos <- c(CRAN = "https://cloud.r-project.org")
options(repos = repos)
# Large AnnotationHub/org packages: avoid spurious timeouts on slow networks
ot <- getOption("timeout")
if (is.null(ot) || ot < 600L) {
  options(timeout = max(600L, as.integer(Sys.getenv("GLIOMA_TARGET_R_DOWNLOAD_TIMEOUT", "600"))))
}

verbose <- tolower(Sys.getenv("CI", "")) %in% c("1", "true", "yes") ||
  tolower(Sys.getenv("GLIOMA_TARGET_R_VERBOSE", "")) %in% c("1", "true", "yes")

bm <- Sys.getenv("GLIOMA_TARGET_R_BIOC_MIRROR", "")
if (nzchar(bm)) {
  options(BioC_mirror = bm)
  message("Using BioC_mirror: ", bm)
}

if (!requireNamespace("BiocManager", quietly = TRUE)) {
  install.packages("BiocManager", repos = repos["CRAN"], quiet = !verbose)
}

pkgs <- c(
  "fgsea",
  "clusterProfiler",
  "enrichplot",
  "AnnotationDbi",
  "org.Hs.eg.db",
  "data.table"
)

BiocManager::install(pkgs, ask = FALSE, update = FALSE, quiet = !verbose)

# Verify namespaces load
for (p in c("fgsea", "clusterProfiler", "enrichplot", "AnnotationDbi", "org.Hs.eg.db", "data.table")) {
  if (!requireNamespace(p, quietly = TRUE)) {
    stop("Failed to load namespace: ", p)
  }
}

message("OK: supplementary enrichment R packages installed.")
