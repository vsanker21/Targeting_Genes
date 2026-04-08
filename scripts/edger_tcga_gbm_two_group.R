#!/usr/bin/env Rscript
# edgeR glmQLF: same TCGA-GBM STAR counts and sample aggregation as PyDESeq2
# (scripts/tcga_gbm_deseq2_two_group.py). Reads config/deseq2_tcga_gbm.yaml blocks.
#
# Usage: Rscript scripts/edger_tcga_gbm_two_group.R <yaml_block_key>
# Example: Rscript scripts/edger_tcga_gbm_two_group.R deseq2_tcga_primary_vs_recurrent
#
# Requires: Bioconductor edgeR, limma; CRAN yaml, jsonlite, arrow

suppressPackageStartupMessages({
  if (!requireNamespace("yaml", quietly = TRUE)) stop("Install CRAN package: yaml")
  if (!requireNamespace("jsonlite", quietly = TRUE)) stop("Install CRAN package: jsonlite")
  if (!requireNamespace("arrow", quietly = TRUE)) stop("Install CRAN package: arrow")
  if (!requireNamespace("edgeR", quietly = TRUE)) {
    stop("Install Bioconductor edgeR (e.g. BiocManager::install(\"edgeR\"))")
  }
  if (!requireNamespace("limma", quietly = TRUE)) {
    stop("Install Bioconductor limma (e.g. BiocManager::install(\"limma\"))")
  }
})

`%||%` <- function(x, y) if (is.null(x)) y else x

repo_root <- function() {
  ca <- commandArgs(trailingOnly = FALSE)
  ff <- grep("^--file=", ca, value = TRUE)
  if (length(ff)) {
    normalizePath(file.path(dirname(sub("^--file=", "", ff[1])), ".."))
  } else {
    normalizePath(".")
  }
}

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1L) {
  stop("Usage: Rscript edger_tcga_gbm_two_group.R <yaml_block_key>")
}
block_key <- args[[1L]]
rr <- repo_root()
cfg_path <- file.path(rr, "config", "deseq2_tcga_gbm.yaml")
doc <- yaml::yaml.load_file(cfg_path)
block <- doc[[block_key]]
if (is.null(block)) stop("Unknown yaml block: ", block_key)

edg <- block$edger
if (is.null(edg) || !isTRUE(edg$enabled)) {
  message(block_key, ": edger disabled in yaml")
  quit(save = "no", status = 0L)
}

resolve_pair <- function(b) {
  p_lab <- as.character(b$primary_label)
  if (!is.null(b$normal_label)) {
    o_lab <- as.character(b$normal_label)
    cmap <- stats::setNames(
      c(as.character(b$condition_primary), as.character(b$condition_normal)),
      c(p_lab, o_lab)
    )
    tag <- "primary_vs_solid_tissue_normal"
  } else if (!is.null(b$recurrent_label)) {
    r_lab <- as.character(b$recurrent_label)
    cmap <- stats::setNames(
      c(as.character(b$condition_primary), as.character(b$condition_recurrent)),
      c(p_lab, r_lab)
    )
    tag <- "primary_vs_recurrent"
  } else {
    stop("Block must define normal_label or recurrent_label (with conditions).")
  }
  list(lab_a = p_lab, lab_b = names(cmap)[2L], cmap = cmap, tag = tag)
}

rp <- resolve_pair(block)
lab_a <- rp$lab_a
lab_b <- names(rp$cmap)[2L]
cond_map <- rp$cmap
tag <- rp$tag

counts_path <- normalizePath(file.path(rr, gsub("/", .Platform$file.sep, block$counts_matrix)), mustWork = FALSE)
meta_path <- normalizePath(file.path(rr, gsub("/", .Platform$file.sep, block$sample_meta)), mustWork = FALSE)
if (!file.exists(counts_path)) stop("Missing counts matrix: ", counts_path)
if (!file.exists(meta_path)) stop("Missing sample meta: ", meta_path)

out_dir <- file.path(rr, gsub("/", .Platform$file.sep, edg$output_dir))
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
out_tsv <- file.path(out_dir, edg$output_results %||% "edger_qlf_results.tsv")
out_prov <- file.path(out_dir, edg$output_provenance %||% "edger_provenance.json")

col_meta <- block$meta_column_matrix %||% "column_name"
st_col <- block$sample_type_col %||% "sample_type"
min_rep <- as.integer(block$pydeseq2$min_replicates %||% 2L)
g_min_total <- as.integer(block$gene_filter_min_total %||% 10L)
g_min_samp <- as.integer(block$gene_filter_min_samples_expressing %||% 5L)

num <- as.character(edg$contrast_numerator)
den <- as.character(edg$contrast_denominator)
if (length(num) != 1L || length(den) != 1L) {
  stop("edger.contrast_numerator and contrast_denominator must be set (logFC = num - denom, matching PyDESeq2).")
}

tab <- arrow::read_parquet(counts_path)
df <- as.data.frame(tab)
if (!"gene_id" %in% names(df)) {
  stop("Counts parquet must include a gene_id column (GDC matrix convention).")
}
gid <- df$gene_id
mat <- as.matrix(df[, setdiff(names(df), "gene_id"), drop = FALSE])
storage.mode(mat) <- "integer"
rownames(mat) <- as.character(gid)

meta <- read.delim(meta_path, sep = "\t", stringsAsFactors = FALSE, check.names = FALSE)
if (!col_meta %in% names(meta) || !st_col %in% names(meta)) {
  stop("Meta must include meta_column_matrix and sample_type_col")
}
meta <- meta[meta[[st_col]] %in% c(lab_a, lab_b), , drop = FALSE]
if (!nrow(meta)) stop("No samples after sample_type filter")

meta$condition <- cond_map[as.character(meta[[st_col]])]
if (anyNA(meta$condition)) stop("Unmapped sample_type in meta")

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
  uc <- unique(g$condition)
  if (length(uc) != 1L) stop("Ambiguous conditions for sample_submitter_id ", sid)
  cold_rows[[length(cold_rows) + 1L]] <- data.frame(
    sample_id = sid,
    condition = uc[[1L]],
    stringsAsFactors = FALSE
  )
}
counts <- do.call(cbind, new_cols)
colnames(counts) <- names(new_cols)
coldata <- do.call(rbind, cold_rows)
rownames(coldata) <- coldata$sample_id

common <- colnames(counts)[colnames(counts) %in% rownames(coldata)]
counts <- counts[, common, drop = FALSE]
coldata <- coldata[common, , drop = FALSE]

tb <- table(coldata$condition)
n_by_cond <- stats::setNames(as.integer(tb), names(tb))
for (cn in unique(as.character(cond_map))) {
  n <- sum(as.character(coldata$condition) == cn)
  if (n < min_rep) {
    stop(
      "Need >= ", min_rep, " samples per group; got ",
      paste(names(n_by_cond), n_by_cond, sep = "=", collapse = ", ")
    )
  }
}

gt <- rowSums(counts)
ns <- rowSums(counts >= 1L)
keep <- gt >= g_min_total & ns >= g_min_samp
counts_f <- counts[keep, , drop = FALSE]

samples <- data.frame(
  sample_id = rownames(coldata),
  condition = coldata$condition,
  stringsAsFactors = FALSE
)
samples <- samples[match(colnames(counts_f), samples$sample_id), , drop = FALSE]
rownames(samples) <- samples$sample_id

# Reference-free design; colnames stripped for makeContrasts (order matches PyDESeq2 num vs den)
samples$condition <- factor(as.character(samples$condition), levels = c(den, num))
design <- stats::model.matrix(~ 0 + condition, data = samples)
colnames(design) <- sub("^condition", "", colnames(design))

contr <- limma::makeContrasts(contrasts = paste0(num, " - ", den), levels = design)

y <- edgeR::DGEList(counts = counts_f, samples = samples)
y <- edgeR::calcNormFactors(y)
y <- edgeR::estimateDisp(y, design)
fit <- edgeR::glmQLFit(y, design)
qlf <- edgeR::glmQLFTest(fit, contrast = contr)
tt <- edgeR::topTags(qlf, n = Inf, sort.by = "none")
res <- as.data.frame(tt$table)
res$gene_id <- rownames(res)
res <- res[, c("gene_id", setdiff(names(res), "gene_id"))]

utils::write.table(
  res,
  file = out_tsv,
  sep = "\t",
  row.names = FALSE,
  quote = FALSE
)

prov <- list(
  generated_utc = format(as.POSIXct(Sys.time(), tz = "UTC"), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
  yaml_block = block_key,
  analysis_tag = tag,
  method = "edgeR_glmQLF",
  contrast_logFC = paste0(num, " - ", den),
  interpretation = paste0("logFC from glmQLF (", num, " vs ", den, "); positive => higher in ", num),
  samples_per_condition = as.list(n_by_cond),
  n_genes_tested = nrow(res),
  counts_source = gsub("\\\\", "/", sub(paste0("^", rr, "/?"), "", counts_path)),
  normalization = "TMM (calcNormFactors)",
  gene_filter_min_total = g_min_total,
  gene_filter_min_samples_expressing = g_min_samp,
  note = "Parallel to PyDESeq2 on the same aggregated integer counts; QL F-test and TMM differ from DESeq2 Wald / size factors — expect correlated but not identical rankings."
)

if (identical(tag, "primary_vs_recurrent")) {
  prov$n_samples_primary <- as.integer(n_by_cond[[as.character(block$condition_primary)]])
  prov$n_samples_recurrent <- as.integer(n_by_cond[[as.character(block$condition_recurrent)]])
}
if (identical(tag, "primary_vs_solid_tissue_normal")) {
  prov$n_samples_primary_tumor <- as.integer(n_by_cond[[as.character(block$condition_primary)]])
  prov$n_samples_solid_tissue_normal <- as.integer(n_by_cond[[as.character(block$condition_normal)]])
  prov$caveats <- list(
    "Only five TCGA-GBM Solid Tissue Normal aliquots in this STAR matrix — extremely low power and unstable variance.",
    "Solid Tissue Normal is adjacent/surgical brain, not population-matched reference tissue; paired cases may share patient background with some primaries.",
    "This contrast completes a same-pipeline STAR tumor-vs-TCGA-normal stub only; it is not a substitute for tumor vs GTEx (or other broad normal) on harmonized counts."
  )
  prov$estimand_note <- "Bulk log fold change (Primary Tumor vs Solid Tissue Normal) on GDC STAR unstranded integer counts; interpret as exploratory."
}

jsonlite::write_json(prov, out_prov, pretty = TRUE, auto_unbox = TRUE)
message("Wrote ", out_tsv, " (", nrow(res), " genes)")
message("Wrote ", out_prov)
