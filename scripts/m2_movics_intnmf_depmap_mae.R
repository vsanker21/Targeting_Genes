#!/usr/bin/env Rscript
# MOVICS IntNMF on DepMap MAE: expression + CN + binary mutation (three views).
# Requires fetch_movics_staging_data (DepMap CSVs) and config/m2_movics_depmap_mae_run.yaml.
# Run from repo root; GLIOMA_TARGET_DATA_ROOT should match Snakemake DATA_ROOT.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1L) {
  stop("Usage: Rscript m2_movics_intnmf_depmap_mae.R <path/to/m2_movics_depmap_mae_run.yaml>")
}

suppressPackageStartupMessages({
  library(yaml)
  library(jsonlite)
})

if (!requireNamespace("MOVICS", quietly = TRUE)) {
  stop(
    "Package MOVICS not installed. Run: python scripts/install_r_movics_dependencies.py",
    call. = FALSE
  )
}

`%||%` <- function(x, y) if (is.null(x)) y else x

cfg_all <- yaml::read_yaml(args[1L])
cfg <- cfg_all$movics_intnmf_depmap_mae
if (is.null(cfg)) {
  stop("YAML must contain movics_intnmf_depmap_mae block")
}

repo_root <- getwd()

fetch_cfg <- yaml::read_yaml(file.path(repo_root, "config", "m2_movics_data_fetch.yaml"))
dep_blk <- fetch_cfg$depmap_gbm_mae
if (is.null(dep_blk)) {
  stop("config/m2_movics_data_fetch.yaml must contain depmap_gbm_mae block")
}
fnames <- dep_blk$filenames
if (is.null(fnames)) {
  fnames <- list()
}
out_dir <- dep_blk$out_dir
if (is.null(out_dir) || !nzchar(out_dir)) {
  out_dir <- "omics/multi_omics_mae"
}
rel_exp <- fnames$expression_gz %||% "depmap_gbm_expression_logtpm.tsv.gz"
rel_cn <- fnames$copy_number_gz %||% "depmap_gbm_cnv_log2.tsv.gz"
rel_mut <- fnames$mutation_binary_gz %||% "depmap_gbm_mutation_binary.tsv.gz"
mae_subpath <- function(od, fn) {
  od <- gsub("/", .Platform$file.sep, od, fixed = TRUE)
  file.path(od, fn)
}

resolve_data_root <- function() {
  e <- Sys.getenv("GLIOMA_TARGET_DATA_ROOT", unset = "")
  if (nzchar(e)) {
    return(e)
  }
  ds <- yaml::read_yaml(file.path(repo_root, "config", "data_sources.yaml"))
  as.character(ds$data_root)
}

data_root <- resolve_data_root()
if (!nzchar(data_root)) {
  stop("Empty data_root; set GLIOMA_TARGET_DATA_ROOT or data_sources.yaml data_root")
}

path_under_root <- function(rel) {
  rel <- gsub("/", .Platform$file.sep, rel, fixed = TRUE)
  p0 <- file.path(data_root, rel)
  if (dir.exists(p0) || file.exists(p0)) {
    return(normalizePath(p0, winslash = "/", mustWork = TRUE))
  }
  p1 <- file.path(repo_root, rel)
  if (file.exists(p1)) {
    return(normalizePath(p1, winslash = "/", mustWork = TRUE))
  }
  p0
}

path_rel_out <- function(p) {
  file.path(repo_root, gsub("/", .Platform$file.sep, p, fixed = TRUE))
}

read_mae_matrix_gz <- function(path) {
  if (!file.exists(path)) {
    stop("Missing matrix file: ", path)
  }
  con <- gzfile(path, "rt")
  on.exit(close(con), add = TRUE)
  df <- utils::read.delim(
    con,
    check.names = FALSE,
    stringsAsFactors = FALSE,
    comment.char = "",
    quote = ""
  )
  if (ncol(df) < 2L) {
    stop("Expected gene column + samples: ", path)
  }
  genes <- as.character(df[[1L]])
  mat <- as.matrix(df[, -1L, drop = FALSE])
  storage.mode(mat) <- "double"
  rownames(mat) <- genes
  mat
}

exp_p <- path_under_root(mae_subpath(out_dir, rel_exp))
cn_p <- path_under_root(mae_subpath(out_dir, rel_cn))
mut_p <- path_under_root(mae_subpath(out_dir, rel_mut))

out_tsv <- path_rel_out(cfg$output_clusters_tsv)
out_js <- path_rel_out(cfg$output_provenance_json)
dir.create(dirname(out_tsv), recursive = TRUE, showWarnings = FALSE)

write_prov <- function(obj) {
  write_json(obj, out_js, auto_unbox = TRUE, pretty = TRUE)
}

mat_e <- try(read_mae_matrix_gz(exp_p), silent = TRUE)
mat_c <- try(read_mae_matrix_gz(cn_p), silent = TRUE)
mat_m <- try(read_mae_matrix_gz(mut_p), silent = TRUE)
if (inherits(mat_e, "try-error") || inherits(mat_c, "try-error") || inherits(mat_m, "try-error")) {
  write_prov(list(
    status = "error",
    reason = "failed_to_read_mae_matrices",
    expression_gz = mae_subpath(out_dir, rel_exp),
    copy_number_gz = mae_subpath(out_dir, rel_cn),
    mutation_binary_gz = mae_subpath(out_dir, rel_mut),
    data_root = data_root
  ))
  stop("Failed to read one or more MAE .tsv.gz files under data_root (run fetch_movics_staging_data first)")
}

samples <- intersect(colnames(mat_e), colnames(mat_c))
samples <- intersect(samples, colnames(mat_m))
genes <- intersect(rownames(mat_e), rownames(mat_c))
genes <- intersect(genes, rownames(mat_m))
samples <- sort(samples)

if (length(samples) < 5L) {
  write_prov(list(status = "error", reason = "too_few_samples", n = length(samples)))
  stop("Too few shared samples across the three matrices")
}
if (length(genes) < 50L) {
  write_prov(list(status = "error", reason = "too_few_genes", n = length(genes)))
  stop("Too few shared genes across the three matrices")
}

mat_e <- mat_e[genes, samples, drop = FALSE]
mat_c <- mat_c[genes, samples, drop = FALSE]
mat_m <- mat_m[genes, samples, drop = FALSE]

ng <- as.integer(cfg$max_genes)
if (is.na(ng) || ng < 50L) {
  ng <- 1500L
}

v <- apply(mat_e, 1L, stats::var, na.rm = TRUE)
v[is.na(v)] <- 0
ord <- order(-v)
ix <- ord[seq_len(min(ng, length(ord)))]
mat_e <- mat_e[ix, , drop = FALSE]
mat_c <- mat_c[ix, , drop = FALSE]
mat_m <- mat_m[ix, , drop = FALSE]

row_mins <- apply(mat_c, 1L, min, na.rm = TRUE)
mat_c_nn <- sweep(mat_c, 1L, row_mins, `-`)
mat_c_nn[is.na(mat_c_nn)] <- 0

mat_m <- round(mat_m)
mat_m[mat_m > 1] <- 1
mat_m[mat_m < 0] <- 0

k <- as.integer(cfg$n_clust)
if (is.na(k) || k < 2L) {
  k <- 3L
}
k <- min(k, ncol(mat_e) - 1L, 20L)

mo_data <- list(expression = mat_e, copy_number = mat_c_nn, mutation = mat_m)
types <- c("gaussian", "gaussian", "binomial")

t0 <- proc.time()[[3L]]
res <- try(
  MOVICS::getIntNMF(data = mo_data, N.clust = k, type = types),
  silent = TRUE
)
elapsed <- proc.time()[[3L]] - t0

if (inherits(res, "try-error")) {
  write_prov(list(
    status = "error",
    reason = "movics_getIntNMF_failed",
    message = as.character(res),
    n_samples = ncol(mat_e),
    n_genes = nrow(mat_e)
  ))
  stop(attr(res, "condition")$message)
}

cr <- res$clust.res
utils::write.table(
  cr,
  file = out_tsv,
  sep = "\t",
  row.names = FALSE,
  quote = FALSE
)

write_prov(list(
  status = "ok",
  method = res$mo.method,
  n_clust = k,
  n_samples = ncol(mat_e),
  n_genes = nrow(mat_e),
  seconds_movics = round(elapsed, 3),
  movics_version = tryCatch(as.character(utils::packageVersion("MOVICS")), error = function(e) "unknown"),
  data_root = data_root,
  views = list(
    expression = mae_subpath(out_dir, rel_exp),
    copy_number = mae_subpath(out_dir, rel_cn),
    mutation_binary = mae_subpath(out_dir, rel_mut)
  ),
  intnmf_types = types,
  copy_number_transform = "rowwise_subtract_min_for_nonnegativity",
  note = paste0(
    "DepMap cell-line models (ModelID columns); not TCGA tumors. ",
    "Do not compare cluster labels to m2_movics_intnmf_tcga_gbm (TCGA GDC STAR)."
  )
))

message("Wrote ", out_tsv, " and ", out_js)
