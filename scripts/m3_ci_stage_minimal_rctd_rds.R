#!/usr/bin/env Rscript
# Build tiny spacexr Reference + SpatialRNA objects and saveRDS for m3_deconvolution_rctd_run smoke tests.
# Requires spacexr (remotes::install_github('dmcable/spacexr') or BiocManager::install('spacexr')).
#
# Usage:
#   Rscript scripts/m3_ci_stage_minimal_rctd_rds.R <data_root>
# Paths under data_root match config/m3_deconvolution_rctd_inputs.yaml.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1L) {
  stop("Usage: m3_ci_stage_minimal_rctd_rds.R <GLIOMA_TARGET_DATA_ROOT>")
}
dr <- args[[1L]]
if (!dir.exists(dr)) {
  dir.create(dr, recursive = TRUE, showWarnings = FALSE)
}
dr <- normalizePath(dr, mustWork = TRUE)
if (!requireNamespace("Matrix", quietly = TRUE)) {
  stop("Matrix required (install in m3_rctd conda env)")
}
if (!requireNamespace("spacexr", quietly = TRUE)) {
  stop("spacexr required: remotes::install_github('dmcable/spacexr')")
}

ref_rel <- "m3_spatial_deconv/rctd/reference.rds"
spat_rel <- "m3_spatial_deconv/rctd/spatialRNA.rds"
ref_path <- file.path(dr, ref_rel)
spat_path <- file.path(dr, spat_rel)
dir.create(dirname(ref_path), recursive = TRUE, showWarnings = FALSE)
dir.create(dirname(spat_path), recursive = TRUE, showWarnings = FALSE)

set.seed(42L)
genes <- sprintf("GENE%03d", 1:30L)
n_cell <- 10L
n_spot <- 6L
ref_dense <- matrix(
  as.integer(pmax(1L, rpois(length(genes) * n_cell, lambda = 15L))),
  nrow = length(genes),
  ncol = n_cell
)
rownames(ref_dense) <- genes
colnames(ref_dense) <- sprintf("cell%02d", seq_len(n_cell))
ref_counts <- as(as(ref_dense, "matrix"), "dgCMatrix")
ct <- factor(
  rep(c("typeA", "typeB"), length.out = n_cell),
  levels = c("typeA", "typeB")
)
names(ct) <- colnames(ref_counts)
ref <- spacexr::Reference(ref_counts, ct, min_UMI = 1L)

spat_dense <- matrix(
  as.integer(pmax(1L, rpois(length(genes) * n_spot, lambda = 12L))),
  nrow = length(genes),
  ncol = n_spot
)
rownames(spat_dense) <- genes
colnames(spat_dense) <- sprintf("spot%02d", seq_len(n_spot))
spat_counts <- as(as(spat_dense, "matrix"), "dgCMatrix")
coords <- data.frame(
  x = runif(n_spot),
  y = runif(n_spot),
  row.names = colnames(spat_counts)
)
puck <- spacexr::SpatialRNA(coords, spat_counts)

saveRDS(ref, ref_path)
saveRDS(puck, spat_path)
message("Wrote ", ref_path, " and ", spat_path)
