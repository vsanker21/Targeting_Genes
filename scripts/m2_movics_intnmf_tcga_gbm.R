#!/usr/bin/env Rscript
# MOVICS IntNMF on TCGA-GBM: TPM (log2) + raw counts (log2) as two Gaussian omics layers.
# Config: config/m2_movics_run.yaml — run from repo root (Snakemake cwd).

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1L) {
  stop("Usage: Rscript m2_movics_intnmf_tcga_gbm.R <path/to/m2_movics_run.yaml>")
}

suppressPackageStartupMessages({
  library(yaml)
  library(jsonlite)
  library(arrow)
})

if (!requireNamespace("MOVICS", quietly = TRUE)) {
  stop(
    "Package MOVICS not installed. Run: python scripts/install_r_movics_dependencies.py",
    call. = FALSE
  )
}

cfg_all <- yaml::read_yaml(args[1L])
cfg <- cfg_all$movics_intnmf
if (is.null(cfg)) {
  stop("YAML must contain movics_intnmf block")
}

repo_root <- getwd()
path_rel <- function(p) file.path(repo_root, gsub("/", .Platform$file.sep, p, fixed = TRUE))

tpmp <- path_rel(cfg$tpm_matrix)
cntp <- path_rel(cfg$counts_matrix)
metp <- path_rel(cfg$sample_meta)

out_tsv <- path_rel(cfg$output_clusters_tsv)
out_js <- path_rel(cfg$output_provenance_json)
dir.create(dirname(out_tsv), recursive = TRUE, showWarnings = FALSE)

write_prov <- function(obj) {
  write_json(obj, out_js, auto_unbox = TRUE, pretty = TRUE)
}

if (!file.exists(tpmp) || !file.exists(cntp) || !file.exists(metp)) {
  write_prov(list(status = "error", reason = "missing_input_matrix_or_meta"))
  stop("Missing TPM, counts, or sample meta at configured paths")
}

meta <- read.csv(metp, sep = "\t", stringsAsFactors = FALSE, check.names = FALSE)
st_col <- cfg$sample_type_col
id_col <- cfg$meta_column_matrix
types_keep <- unlist(cfg$filter_sample_types, use.names = FALSE)
sel <- meta[[st_col]] %in% types_keep
ids <- as.character(meta[[id_col]][sel])
ids <- ids[nzchar(ids)]
if (length(ids) < 5L) {
  write_prov(list(status = "error", reason = "too_few_samples_after_meta_filter", n = length(ids)))
  stop("Too few samples after meta filter")
}

read_expr <- function(path, want_cols) {
  df <- as.data.frame(arrow::read_parquet(path))
  if (!"gene_id" %in% names(df)) {
    stop("Parquet must contain gene_id column")
  }
  rownames(df) <- df$gene_id
  df$gene_id <- NULL
  miss <- setdiff(want_cols, colnames(df))
  if (length(miss) > 0L) {
    stop("Missing columns in matrix: ", length(miss), " e.g. ", miss[[1L]])
  }
  as.matrix(df[, want_cols, drop = FALSE])
}

mat_t <- read_expr(tpmp, ids)
mat_c <- read_expr(cntp, ids)
if (!identical(dim(mat_t), dim(mat_c))) {
  write_prov(list(status = "error", reason = "tpm_counts_dim_mismatch"))
  stop("TPM and counts dimensions differ")
}

ng <- as.integer(cfg$max_genes)
if (is.na(ng) || ng < 50L) {
  ng <- 500L
}

lt <- log2(pmax(mat_t, 0) + 1)
v <- apply(lt, 1L, stats::var)
ord <- order(-v)
ix <- ord[seq_len(min(ng, nrow(lt)))]
mat_t <- lt[ix, , drop = FALSE]
mat_c <- log2(pmax(mat_c[ix, , drop = FALSE], 0) + 1)

k <- as.integer(cfg$n_clust)
if (is.na(k) || k < 2L) {
  k <- 3L
}
k <- min(k, ncol(mat_t) - 1L, 20L)

mo_data <- list(tpm = mat_t, counts = mat_c)
types <- c("gaussian", "gaussian")

t0 <- proc.time()[[3L]]
res <- try(
  MOVICS::getIntNMF(data = mo_data, N.clust = k, type = types),
  silent = TRUE
)
elapsed <- proc.time()[[3L]] - t0

if (inherits(res, "try-error")) {
  write_prov(list(status = "error", reason = "movics_getIntNMF_failed", message = as.character(res)))
  stop(attr(res, "condition")$message)
}

cr <- res$clust.res
write.table(
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
  n_samples = ncol(mat_t),
  n_genes = nrow(mat_t),
  sample_types = types_keep,
  seconds_movics = round(elapsed, 3),
  movics_version = tryCatch(as.character(utils::packageVersion("MOVICS")), error = function(e) "unknown"),
  tpm_matrix = cfg$tpm_matrix,
  counts_matrix = cfg$counts_matrix
))

message("Wrote ", out_tsv, " and ", out_js)
