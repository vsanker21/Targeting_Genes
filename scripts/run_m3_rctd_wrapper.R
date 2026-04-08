#!/usr/bin/env Rscript
# Invoked from run_m3_rctd_orchestrate.py inside conda env m3_rctd.
# Writes rctd_run_provenance.json always; rctd_run.flag only when status == ok; exit 1 if not ok.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3L) {
  stop("Usage: run_m3_rctd_wrapper.R <reference.rds> <spatialRNA.rds> <out_dir>")
}
ref_path <- args[[1L]]
spat_path <- args[[2L]]
outd <- args[[3L]]
dir.create(outd, recursive = TRUE, showWarnings = FALSE)
flag_path <- file.path(outd, "rctd_run.flag")
if (file.exists(flag_path)) {
  file.remove(flag_path)
}

if (!requireNamespace("jsonlite", quietly = TRUE)) {
  stop("jsonlite required (conda package r-jsonlite)")
}

prov <- list(
  reference_rds = ref_path,
  spatial_rna_rds = spat_path,
  ref_load_ok = FALSE,
  spatial_load_ok = FALSE,
  spacexr_available = requireNamespace("spacexr", quietly = TRUE)
)

ref <- tryCatch(
  {
    x <- readRDS(ref_path)
    prov$ref_load_ok <- TRUE
    x
  },
  error = function(e) {
    prov$ref_error <- conditionMessage(e)
    NULL
  }
)

spat <- tryCatch(
  {
    x <- readRDS(spat_path)
    prov$spatial_load_ok <- TRUE
    x
  },
  error = function(e) {
    prov$spatial_error <- conditionMessage(e)
    NULL
  }
)

prov$rctd_create_ok <- FALSE
env_truthy <- function(nm) {
  v <- Sys.getenv(nm, unset = "")
  tolower(trimws(v)) %in% c("1", "true", "yes", "y")
}
if (isTRUE(prov$spacexr_available) && !is.null(ref) && !is.null(spat)) {
  use_test_mode <- env_truthy("GLIOMA_TARGET_RCTD_TEST_MODE")
  res <- try(
    if (isTRUE(use_test_mode)) {
      spacexr::create.RCTD(spat, ref, max_cores = 1L, test_mode = TRUE)
    } else {
      spacexr::create.RCTD(spat, ref, max_cores = 1L)
    },
    silent = TRUE
  )
  if (inherits(res, "try-error") && !isTRUE(use_test_mode) && env_truthy("GLIOMA_TARGET_RCTD_FALLBACK_TEST_MODE")) {
    res <- try(spacexr::create.RCTD(spat, ref, max_cores = 1L, test_mode = TRUE), silent = TRUE)
    prov$rctd_retried_test_mode <- TRUE
  }
  prov$rctd_create_ok <- !inherits(res, "try-error")
  if (inherits(res, "try-error")) {
    prov$rctd_error <- as.character(res)
  }
} else if (!isTRUE(prov$spacexr_available)) {
  prov$note <- paste0(
    "spacexr not installed. In the m3_rctd env run e.g. ",
    "R -e \"remotes::install_github('dmcable/spacexr')\""
  )
}

# Align with Python orchestrator provenance (e.g. cell2location_run_provenance.json).
prov$artifact_kind <- "m3_deconvolution_rctd_run"
prov$status <- if (isTRUE(prov$rctd_create_ok)) {
  "ok"
} else if (!isTRUE(prov$ref_load_ok) || !isTRUE(prov$spatial_load_ok)) {
  "rds_load_failed"
} else if (!isTRUE(prov$spacexr_available)) {
  "spacexr_missing"
} else {
  "create_failed"
}

jsonlite::write_json(
  prov,
  file.path(outd, "rctd_run_provenance.json"),
  auto_unbox = TRUE,
  pretty = TRUE
)
# Match cell2location_run.flag: only mark Snakemake success when RCTD actually succeeded.
if (identical(prov$status, "ok")) {
  writeLines("ok", flag_path)
}
quit(status = if (identical(prov$status, "ok")) 0L else 1L)
