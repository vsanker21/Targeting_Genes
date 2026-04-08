#!/usr/bin/env Rscript
# ComBat-Seq (sva::ComBat_seq) on TCGA-GBM STAR counts — Primary Tumor subset, TSS proxy batch.
# Config: config/combat_seq_tcga_gbm.yaml (key combat_seq_tcga_gbm_primary)
#
# Usage: Rscript scripts/combat_seq_tcga_gbm_subset.R [path/to/combat_seq_tcga_gbm.yaml]

suppressPackageStartupMessages({
  if (!requireNamespace("yaml", quietly = TRUE)) stop("Install yaml (CRAN)")
  if (!requireNamespace("jsonlite", quietly = TRUE)) stop("Install jsonlite (CRAN)")
  if (!requireNamespace("arrow", quietly = TRUE)) stop("Install arrow (CRAN)")
  if (!requireNamespace("sva", quietly = TRUE)) {
    stop("Install Bioconductor sva: python scripts/install_r_combat_dependencies.py")
  }
})

repo_root <- function() {
  ca <- commandArgs(trailingOnly = FALSE)
  ff <- grep("^--file=", ca, value = TRUE)
  if (length(ff)) {
    normalizePath(file.path(dirname(sub("^--file=", "", ff[1])), ".."))
  } else {
    normalizePath(".")
  }
}

`%||%` <- function(x, y) if (is.null(x)) y else x

tss_from_barcode <- function(id) {
  id <- as.character(id)[[1L]]
  parts <- strsplit(id, "-", fixed = TRUE)[[1L]]
  if (length(parts) >= 2L) parts[[2L]] else NA_character_
}

args <- commandArgs(trailingOnly = TRUE)
rr <- repo_root()
cfg_path <- if (length(args) >= 1L) {
  normalizePath(args[[1L]], mustWork = TRUE)
} else {
  file.path(rr, "config", "combat_seq_tcga_gbm.yaml")
}
doc <- yaml::yaml.load_file(cfg_path)
block <- doc$combat_seq_tcga_gbm_primary
if (is.null(block)) stop("Missing combat_seq_tcga_gbm_primary in yaml")
if (!isTRUE(block$enabled)) {
  message("combat_seq_tcga_gbm_primary disabled")
  quit(save = "no", status = 0L)
}

counts_rel <- gsub("/", .Platform$file.sep, block$counts_matrix)
meta_rel <- gsub("/", .Platform$file.sep, block$sample_meta)
counts_path <- normalizePath(file.path(rr, counts_rel), mustWork = TRUE)
meta_path <- normalizePath(file.path(rr, meta_rel), mustWork = TRUE)

out_dir <- file.path(rr, gsub("/", .Platform$file.sep, block$output_dir))
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
out_matrix <- file.path(out_dir, block$output_matrix %||% "combat_seq_adjusted_counts.parquet")
out_prov <- file.path(out_dir, block$output_provenance %||% "combat_seq_provenance.json")

col_meta <- block$meta_column_matrix %||% "column_name"
st_col <- block$sample_type_col %||% "sample_type"
st_keep <- unlist(block$sample_types, use.names = FALSE)
min_per_batch <- as.integer(block$min_samples_per_batch %||% 3L)
min_batches <- as.integer(block$min_batches %||% 2L)
g_min_total <- as.integer(block$gene_filter_min_total %||% 10L)
g_min_samp <- as.integer(block$gene_filter_min_samples_expressing %||% 5L)

tab <- arrow::read_parquet(counts_path)
df <- as.data.frame(tab)
if (!"gene_id" %in% names(df)) stop("Counts parquet must have gene_id column")
gid <- df$gene_id
mat <- as.matrix(df[, setdiff(names(df), "gene_id"), drop = FALSE])
storage.mode(mat) <- "integer"
rownames(mat) <- as.character(gid)

meta <- read.delim(meta_path, sep = "\t", stringsAsFactors = FALSE, check.names = FALSE)
meta <- meta[meta[[st_col]] %in% st_keep, , drop = FALSE]
if (!nrow(meta)) stop("No samples after sample_type filter")

sid_list <- unique(as.character(meta$sample_submitter_id))
new_cols <- list()
cold_rows <- list()
for (sid in sid_list) {
  g <- meta[as.character(meta$sample_submitter_id) == sid, , drop = FALSE]
  cnames <- as.character(g[[col_meta]])
  cnames <- cnames[cnames %in% colnames(mat)]
  if (!length(cnames)) next
  if (length(cnames) == 1L) {
    new_cols[[sid]] <- mat[, cnames[1L]]
  } else {
    new_cols[[sid]] <- rowSums(mat[, cnames, drop = FALSE])
  }
  cold_rows[[length(cold_rows) + 1L]] <- data.frame(
    sample_id = sid,
    case_submitter_id = g$case_submitter_id[[1L]],
    stringsAsFactors = FALSE
  )
}
counts <- do.call(cbind, new_cols)
colnames(counts) <- names(new_cols)
coldata <- do.call(rbind, cold_rows)
rownames(coldata) <- coldata$sample_id

coldata$batch_tss <- vapply(coldata$case_submitter_id, tss_from_barcode, character(1L))
if (anyNA(coldata$batch_tss)) stop("Could not derive TSS batch for some samples")

common <- colnames(counts)[colnames(counts) %in% rownames(coldata)]
counts <- counts[, common, drop = FALSE]
coldata <- coldata[common, , drop = FALSE]

bt <- table(coldata$batch_tss)
keep_batches <- names(bt)[bt >= min_per_batch]
if (length(keep_batches) < min_batches) {
  stop(
    "Need >= ", min_batches, " batches with >= ", min_per_batch,
    " samples; got batches: ", paste(names(bt), "=", as.integer(bt), collapse = ", ")
  )
}
ok <- coldata$batch_tss %in% keep_batches
counts <- counts[, ok, drop = FALSE]
coldata <- coldata[ok, , drop = FALSE]
batch_fac <- factor(coldata$batch_tss)

gt <- rowSums(counts)
ns <- rowSums(counts >= 1L)
keepg <- gt >= g_min_total & ns >= g_min_samp
counts_f <- counts[keepg, , drop = FALSE]

cm <- as.matrix(counts_f)
storage.mode(cm) <- "integer"
adj <- sva::ComBat_seq(cm, batch = batch_fac, group = NULL)

colnames(adj) <- colnames(counts_f)
rownames(adj) <- rownames(counts_f)

out_df <- data.frame(gene_id = rownames(adj), adj, check.names = FALSE)
arrow::write_parquet(out_df, out_matrix)

n_batch <- length(levels(batch_fac))
tb_ct <- table(batch_fac)
prov <- list(
  generated_utc = format(as.POSIXct(Sys.time(), tz = "UTC"), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
  method = "sva::ComBat_seq",
  config_file = "config/combat_seq_tcga_gbm.yaml",
  subset_sample_types = as.list(st_keep),
  batch_mode = block$batch_mode %||% "tss",
  batch_definition = "Second hyphen-separated field of case_submitter_id (TCGA TSS code); proxy for site/institution, not lane or library batch.",
  min_samples_per_batch = min_per_batch,
  n_samples = ncol(adj),
  n_genes = nrow(adj),
  n_batches = n_batch,
  samples_per_batch = as.list(setNames(as.integer(tb_ct), names(tb_ct))),
  counts_source = gsub("\\\\", "/", block$counts_matrix),
  output_matrix = paste0(gsub("\\\\", "/", block$output_dir), "/", block$output_matrix %||% "combat_seq_adjusted_counts.parquet"),
  caveats = list(
    "TSS is a coarse batch proxy; residual technical variation may remain.",
    "Adjusted values are not guaranteed to be integers; do not treat as raw counts for DESeq2 without further methodology.",
    "ComBat-Seq with group=NULL removes batch among primary tumors only; biology confounded with TSS is partially absorbed — interpret exploratory plots with care."
  )
)
jsonlite::write_json(prov, out_prov, pretty = TRUE, auto_unbox = TRUE)
message("Wrote ", out_matrix, " (", nrow(adj), " genes x ", ncol(adj), " samples)")
message("Wrote ", out_prov)
