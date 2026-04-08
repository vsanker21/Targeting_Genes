#!/usr/bin/env Rscript
# edgeR glmQLF: same recount3 integer counts as PyDESeq2 (dea_deseq2_recount3_tcga_gbm_vs_gtex_brain.py).
# Reads prepared recount3_de_counts_matrix.parquet + recount3_de_sample_meta.tsv under output_dir.
#
# Usage: Rscript scripts/edger_recount3_tcga_gbm_vs_gtex_brain.R
# Prerequisite: run the Python script first (or Snakemake m2_deseq2_recount3_tcga_gbm_vs_gtex_brain).
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

rr <- repo_root()
cfg_path <- file.path(rr, "config", "deseq2_recount3_tcga_gtex.yaml")
doc <- yaml::yaml.load_file(cfg_path)
block <- doc$deseq2_recount3_tcga_gbm_vs_gtex_brain
if (is.null(block)) stop("Missing deseq2_recount3_tcga_gbm_vs_gtex_brain block in yaml")

edg <- block$edger
if (is.null(edg) || !isTRUE(edg$enabled)) {
  message("deseq2_recount3_tcga_gbm_vs_gtex_brain: edger disabled in yaml")
  quit(save = "no", status = 0L)
}

out_dir <- file.path(rr, gsub("/", .Platform$file.sep, block$output_dir))
matrix_name <- edg$prepared_counts_matrix %||% block$prepared_counts_matrix %||% "recount3_de_counts_matrix.parquet"
meta_name <- edg$prepared_sample_meta %||% block$prepared_sample_meta %||% "recount3_de_sample_meta.tsv"
counts_path <- normalizePath(file.path(out_dir, gsub("/", .Platform$file.sep, matrix_name)), mustWork = FALSE)
meta_path <- normalizePath(file.path(out_dir, gsub("/", .Platform$file.sep, meta_name)), mustWork = FALSE)

if (!file.exists(counts_path)) {
  stop(
    "Missing prepared counts matrix: ", counts_path,
    "\nRun: python scripts/dea_deseq2_recount3_tcga_gbm_vs_gtex_brain.py"
  )
}
if (!file.exists(meta_path)) stop("Missing sample meta: ", meta_path)

num <- as.character(edg$contrast_numerator)
den <- as.character(edg$contrast_denominator)
if (length(num) != 1L || length(den) != 1L) {
  stop("edger.contrast_numerator and contrast_denominator must be set (logFC = num - denom).")
}

p2 <- block$pydeseq2
min_rep <- as.integer(p2$min_replicates %||% 2L)
g_min_total <- as.integer(block$gene_filter_min_total %||% 10L)
g_min_samp <- as.integer(block$gene_filter_min_samples_expressing %||% 5L)

out_sub <- gsub("/", .Platform$file.sep, edg$output_subdir %||% "")
if (nzchar(out_sub)) {
  out_dir_edg <- file.path(out_dir, out_sub)
} else {
  out_dir_edg <- out_dir
}
dir.create(out_dir_edg, recursive = TRUE, showWarnings = FALSE)
out_tsv <- file.path(out_dir_edg, edg$output_results %||% "edger_qlf_results.tsv")
out_prov <- file.path(out_dir_edg, edg$output_provenance %||% "edger_provenance.json")

tab <- arrow::read_parquet(counts_path)
df <- as.data.frame(tab)
if (!"gene_id" %in% names(df)) {
  stop("Counts parquet must include gene_id column.")
}
gid <- df$gene_id
mat <- as.matrix(df[, setdiff(names(df), "gene_id"), drop = FALSE])
storage.mode(mat) <- "integer"
rownames(mat) <- as.character(gid)

meta <- read.delim(meta_path, sep = "\t", stringsAsFactors = FALSE, check.names = FALSE)
if (!"sample_id" %in% names(meta) || !"condition" %in% names(meta)) {
  stop("Meta must include sample_id and condition columns.")
}

common <- intersect(colnames(mat), as.character(meta$sample_id))
if (!length(common)) stop("No overlap between matrix columns and meta sample_id")
mat <- mat[, common, drop = FALSE]
meta <- meta[match(common, as.character(meta$sample_id)), , drop = FALSE]
rownames(meta) <- meta$sample_id

tb <- table(meta$condition)
n_by_cond <- stats::setNames(as.integer(tb), names(tb))
conds <- unique(as.character(meta$condition))
for (cn in conds) {
  n <- sum(as.character(meta$condition) == cn)
  if (n < min_rep) {
    stop(
      "Need >= ", min_rep, " samples per group; got ",
      paste(names(n_by_cond), n_by_cond, sep = "=", collapse = ", ")
    )
  }
}

gt <- rowSums(mat)
ns <- rowSums(mat >= 1L)
keep <- gt >= g_min_total & ns >= g_min_samp
counts_f <- mat[keep, , drop = FALSE]

samples <- data.frame(
  sample_id = colnames(counts_f),
  condition = meta[ colnames(counts_f), "condition"],
  stringsAsFactors = FALSE
)
rownames(samples) <- samples$sample_id

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
  yaml_block = "deseq2_recount3_tcga_gbm_vs_gtex_brain",
  method = "edgeR_glmQLF",
  contrast_logFC = paste0(num, " - ", den),
  interpretation = paste0(
    "logFC from glmQLF (", num, " vs ", den, "); positive => higher in ", num,
    " — recount3 G029 counts; parallel to PyDESeq2 on the same prepared matrix."
  ),
  samples_per_condition = as.list(n_by_cond),
  n_genes_tested = nrow(res),
  counts_matrix = gsub("\\\\", "/", sub(paste0("^", rr, "/?"), "", counts_path)),
  sample_meta = gsub("\\\\", "/", sub(paste0("^", rr, "/?"), "", meta_path)),
  normalization = "TMM (calcNormFactors)",
  gene_filter_min_total = g_min_total,
  gene_filter_min_samples_expressing = g_min_samp,
  note = "Same integer matrix as PyDESeq2; QL F-test and TMM differ from DESeq2 — expect correlated rankings."
)

jsonlite::write_json(prov, out_prov, pretty = TRUE, auto_unbox = TRUE)
message("Wrote ", out_tsv, " (", nrow(res), " genes)")
message("Wrote ", out_prov)
