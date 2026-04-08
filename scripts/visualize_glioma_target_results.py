#!/usr/bin/env python3
"""
High-resolution figures from GLIOMA-TARGET Module 7 outputs (v1.1 composite).

- **Composite** (`--output`): six data panels (no text summary panel).
- **Split** (`--split-panels`, on by default): each panel saved as its own UHD raster under
  `--panel-dir` with names `panel_01_…` … `panel_06_…`.

  python scripts/visualize_glioma_target_results.py \\
    --dpi 400 --fig-width 20 --fig-height 11 \\
    --output results/module7/glioma_target_results_uhd.png

  pip install matplotlib  (requirements-dev.txt)

Does not modify pipeline logic; read-only visualization.

Gene tick labels (panels 01 + 04) use large **bold** type and `FS_GENE_COLOR` for contrast; tune
`FS_GENE_BAR`, `FS_GENE_HEAT`, and `FS_*` at the top of this file if needed.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.gridspec import GridSpec
except ImportError:
    print("ERROR: install matplotlib:  pip install matplotlib", file=sys.stderr)
    raise SystemExit(2)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _cmap_neon() -> LinearSegmentedColormap:
    return LinearSegmentedColormap.from_list(
        "glioma_neon",
        ["#0a1628", "#0d4f4f", "#2ee6a6", "#e6329e", "#ffd447"],
        N=256,
    )


# Typography tuned for UHD exports (400+ DPI); gene symbols are maximized for legibility.
FS_GENE_BAR = 54  # 01_tier1_ranked_bars — HGNC symbols on Y-axis (bold)
FS_GENE_HEAT = 44  # 04_subscore_heatmap — gene symbols on X-axis (bold, rotated)
FS_GENE_COLOR = "#f8fafc"  # near-white on dark axes for gene tick labels
FS_TITLE = 15
FS_AXIS_LABEL = 14
FS_TICK = 12
FS_LEGEND = 12
FS_CBAR_LABEL = 12
FS_CBAR_TICK = 11
FS_SUPTITLE = 16
FS_FALLBACK_TEXT = 14


def apply_dark_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
            "font.size": FS_TICK,
            "axes.titlesize": FS_TITLE,
            "axes.labelsize": FS_AXIS_LABEL,
            "xtick.labelsize": FS_TICK,
            "ytick.labelsize": FS_TICK,
            "axes.facecolor": "#0b0f14",
            "figure.facecolor": "#06080c",
            "savefig.facecolor": "#06080c",
            "text.color": "#e8eef5",
            "axes.labelcolor": "#c5d4e8",
            "axes.edgecolor": "#3d4f66",
            "xtick.color": "#a8bdd4",
            "ytick.color": "#a8bdd4",
            "grid.color": "#2a3544",
            "grid.alpha": 0.45,
        }
    )


@dataclass
class VizContext:
    t1: pd.DataFrame
    full: pd.DataFrame | None
    top: pd.DataFrame
    heat_df: pd.DataFrame
    sub_cols: list[str]
    score_col: str
    cmap: LinearSegmentedColormap


def build_context(
    tier1: pd.DataFrame,
    full: pd.DataFrame | None,
    *,
    top_bars: int,
    top_heat: int,
) -> VizContext:
    score_col = "glioma_target_score"
    sub_cols = [
        c for c in ("gts_sub_E_norm", "gts_sub_M_norm", "gts_sub_D_norm", "gts_sub_N_norm") if c in tier1.columns
    ]
    t1 = tier1.sort_values(score_col, ascending=False).reset_index(drop=True)
    top = t1.head(max(top_bars, 5)).iloc[::-1]
    heat_n = min(top_heat, len(t1))
    heat_df = t1.head(heat_n)
    return VizContext(
        t1=t1,
        full=full,
        top=top,
        heat_df=heat_df,
        sub_cols=sub_cols,
        score_col=score_col,
        cmap=_cmap_neon(),
    )


def draw_panel_01_tier1_bars(fig: plt.Figure, ax: mpl.axes.Axes, ctx: VizContext) -> None:
    sc = pd.to_numeric(ctx.top[ctx.score_col], errors="coerce")
    colors = ctx.cmap((sc - sc.min()) / (sc.max() - sc.min() + 1e-12))
    y = np.arange(len(ctx.top))
    ax.barh(y, sc.values, color=colors, height=0.72, edgecolor="#1a2332", linewidth=0.35)
    ax.set_yticks(y)
    ax.set_yticklabels(
        ctx.top["hgnc_symbol"].astype(str),
        fontsize=FS_GENE_BAR,
        fontweight="bold",
        color=FS_GENE_COLOR,
    )
    ax.set_xlabel("GLIOMA-TARGET composite score (v1.1)", fontsize=FS_AXIS_LABEL)
    ax.tick_params(axis="x", labelsize=FS_TICK)
    ax.set_title(
        f"Tier-1 candidates — top {len(ctx.top)} by glioma_target_score (n={len(ctx.t1)} tier-1 genes)",
        color="#f0f4fa",
        fontweight="bold",
        fontsize=FS_TITLE,
        pad=12,
    )
    ax.grid(axis="x", linestyle="--", alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    sm = mpl.cm.ScalarMappable(
        cmap=ctx.cmap, norm=mpl.colors.Normalize(vmin=float(sc.min()), vmax=float(sc.max()))
    )
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.02, aspect=28)
    cbar.ax.tick_params(colors="#a8bdd4", labelsize=FS_CBAR_TICK)
    cbar.set_label("Score (within panel)", color="#c5d4e8", fontsize=FS_CBAR_LABEL)


def draw_panel_02_em_landscape(fig: plt.Figure, ax: mpl.axes.Axes, ctx: VizContext) -> None:
    if "gts_sub_E_norm" not in ctx.t1.columns or "gts_sub_M_norm" not in ctx.t1.columns:
        ax.set_axis_off()
        return
    ex = pd.to_numeric(ctx.t1["gts_sub_E_norm"], errors="coerce")
    mx = pd.to_numeric(ctx.t1["gts_sub_M_norm"], errors="coerce")
    comp = pd.to_numeric(ctx.t1[ctx.score_col], errors="coerce")
    sz = (comp - comp.min()) * 800 + 15
    cb = ax.scatter(
        ex,
        mx,
        c=comp,
        s=sz,
        cmap=ctx.cmap,
        alpha=0.85,
        edgecolors="#1a2332",
        linewidths=0.2,
    )
    ax.set_xlabel("Sub-score E (expression)", fontsize=FS_AXIS_LABEL)
    ax.set_ylabel("Sub-score M (DepMap + driver)", fontsize=FS_AXIS_LABEL)
    ax.set_title("E–M landscape (point size ∝ rank within tier-1)", fontsize=FS_TITLE)
    ax.tick_params(axis="both", labelsize=FS_TICK)
    cbar2 = fig.colorbar(cb, ax=ax, fraction=0.046, pad=0.03)
    cbar2.set_label("Composite", fontsize=FS_CBAR_LABEL)
    cbar2.ax.tick_params(labelsize=FS_CBAR_TICK)
    ax.grid(True, linestyle="--", alpha=0.3)


def draw_panel_03_cohort_hexbin(fig: plt.Figure, ax: mpl.axes.Axes, ctx: VizContext) -> None:
    full = ctx.full
    dep = "depmap_crispr_median_gbm"
    if (
        full is not None
        and ctx.score_col in full.columns
        and "delta_log2_expression" in full.columns
        and dep in full.columns
    ):
        fx = pd.to_numeric(full["delta_log2_expression"], errors="coerce")
        fy = pd.to_numeric(full[dep], errors="coerce")
        m = fx.notna() & fy.notna()
        hb = ax.hexbin(
            fx[m],
            fy[m],
            C=pd.to_numeric(full.loc[m, ctx.score_col], errors="coerce"),
            reduce_C_function=np.mean,
            gridsize=55,
            cmap="magma",
            mincnt=1,
            linewidths=0,
        )
        ax.scatter(
            pd.to_numeric(ctx.t1["delta_log2_expression"], errors="coerce"),
            pd.to_numeric(ctx.t1[dep], errors="coerce"),
            s=28,
            c="#2ee6a6",
            alpha=0.9,
            edgecolors="#ffffff",
            linewidths=0.25,
            label="Tier-1",
            zorder=5,
        )
        ax.set_xlabel("Δ log₂ expression (tumor vs normal)", fontsize=FS_AXIS_LABEL)
        ax.set_ylabel("DepMap CRISPR median (GBM)", fontsize=FS_AXIS_LABEL)
        ax.set_title("Cohort context: mean composite in (DE × dependency) bins", fontsize=FS_TITLE)
        ax.tick_params(axis="both", labelsize=FS_TICK)
        cbar3 = fig.colorbar(hb, ax=ax, fraction=0.046, pad=0.03)
        cbar3.set_label("Mean score", fontsize=FS_CBAR_LABEL)
        cbar3.ax.tick_params(labelsize=FS_CBAR_TICK)
        ax.legend(loc="lower right", fontsize=FS_LEGEND, framealpha=0.4)
    else:
        ax.text(
            0.5,
            0.5,
            "Provide full Welch stub\n(--full-tsv) for cohort hexbin",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=FS_FALLBACK_TEXT,
        )
    ax.grid(True, linestyle="--", alpha=0.25)


def draw_panel_04_subscore_heatmap(fig: plt.Figure, ax: mpl.axes.Axes, ctx: VizContext) -> None:
    if not ctx.sub_cols:
        ax.set_axis_off()
        return
    mat = ctx.heat_df[ctx.sub_cols].apply(pd.to_numeric, errors="coerce").to_numpy().T
    n = mat.shape[1]
    im = ax.imshow(mat, aspect="auto", cmap="inferno", vmin=0, vmax=1, interpolation="nearest")
    ax.set_yticks(range(len(ctx.sub_cols)))
    ax.set_yticklabels(["E", "M", "D", "N"][: len(ctx.sub_cols)], fontsize=FS_TICK + 1)
    ax.set_xticks(range(n))
    ax.set_xticklabels(
        ctx.heat_df["hgnc_symbol"].astype(str),
        rotation=75,
        ha="right",
        fontsize=FS_GENE_HEAT,
        fontweight="bold",
        color=FS_GENE_COLOR,
    )
    ax.set_title(f"Sub-score heatmap — top {n} genes", fontsize=FS_TITLE)
    ax.tick_params(axis="y", labelsize=FS_TICK + 1)
    cbar4 = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar4.set_label("Norm [0,1]", fontsize=FS_CBAR_LABEL)
    cbar4.ax.tick_params(labelsize=FS_CBAR_TICK)


def draw_panel_05_score_distribution(ax: mpl.axes.Axes, ctx: VizContext) -> None:
    vals = pd.to_numeric(ctx.t1[ctx.score_col], errors="coerce").dropna()
    ax.hist(vals, bins=36, color="#5b7cff", alpha=0.75, edgecolor="#0b0f14", linewidth=0.3)
    if ctx.full is not None and ctx.score_col in ctx.full.columns:
        fv = pd.to_numeric(ctx.full[ctx.score_col], errors="coerce").dropna()
        ax.hist(fv, bins=48, color="#2a3544", alpha=0.55, edgecolor="none", label="Full ranked (Welch)")
    ax.axvline(vals.median(), color="#ffd447", linestyle="--", linewidth=1, label="Tier-1 median")
    ax.set_xlabel("glioma_target_score", fontsize=FS_AXIS_LABEL)
    ax.set_title("Score distribution", fontsize=FS_TITLE)
    ax.tick_params(axis="both", labelsize=FS_TICK)
    ax.legend(fontsize=FS_LEGEND, framealpha=0.35)
    ax.grid(axis="y", linestyle="--", alpha=0.3)


def draw_panel_06_subscore_violin(ax: mpl.axes.Axes, ctx: VizContext) -> None:
    if not ctx.sub_cols:
        ax.set_axis_off()
        return
    parts = ax.violinplot(
        [pd.to_numeric(ctx.t1[c], errors="coerce").dropna().values for c in ctx.sub_cols],
        positions=range(1, len(ctx.sub_cols) + 1),
        showmeans=True,
        showmedians=False,
    )
    for b in parts["bodies"]:
        b.set_facecolor("#e6329e")
        b.set_edgecolor("#ffd447")
        b.set_alpha(0.65)
    ax.set_xticks(range(1, len(ctx.sub_cols) + 1))
    ax.set_xticklabels(["E", "M", "D", "N"][: len(ctx.sub_cols)], fontsize=FS_TICK + 1)
    ax.set_ylabel("Normalized sub-score", fontsize=FS_AXIS_LABEL)
    ax.set_title("Tier-1 sub-score density", fontsize=FS_TITLE)
    ax.tick_params(axis="y", labelsize=FS_TICK)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, axis="y", linestyle="--", alpha=0.3)


PANEL_DRAWERS = (
    ("01_tier1_ranked_bars", draw_panel_01_tier1_bars),
    ("02_E_M_landscape", draw_panel_02_em_landscape),
    ("03_cohort_hexbin_context", draw_panel_03_cohort_hexbin),
    ("04_subscore_heatmap", draw_panel_04_subscore_heatmap),
    ("05_score_distribution", lambda fig, ax, ctx: draw_panel_05_score_distribution(ax, ctx)),
    ("06_subscore_violin", lambda fig, ax, ctx: draw_panel_06_subscore_violin(ax, ctx)),
)

# Default figure sizes (inches) per panel for UHD export — tuned for clarity at 400+ DPI
PANEL_FIGSIZE: dict[str, tuple[float, float]] = {
    "01_tier1_ranked_bars": (26.0, 18.0),
    "02_E_M_landscape": (14.0, 12.0),
    "03_cohort_hexbin_context": (14.0, 12.0),
    "04_subscore_heatmap": (32.0, 13.0),
    "05_score_distribution": (14.0, 10.0),
    "06_subscore_violin": (12.0, 10.0),
}


def build_six_panel_figure(
    ctx: VizContext,
    fig_width: float,
    fig_height: float,
) -> plt.Figure:
    fig = plt.figure(figsize=(fig_width, fig_height), constrained_layout=False)
    gs = GridSpec(
        3,
        3,
        figure=fig,
        height_ratios=[1.15, 1.0, 0.95],
        width_ratios=[1.2, 1.0, 1.0],
        hspace=0.52,
        wspace=0.40,
        left=0.36,
        right=0.97,
        top=0.86,
        bottom=0.22,
    )
    ax1 = fig.add_subplot(gs[0, :])
    draw_panel_01_tier1_bars(fig, ax1, ctx)
    draw_panel_02_em_landscape(fig, fig.add_subplot(gs[1, 0]), ctx)
    draw_panel_03_cohort_hexbin(fig, fig.add_subplot(gs[1, 1]), ctx)
    draw_panel_04_subscore_heatmap(fig, fig.add_subplot(gs[1, 2]), ctx)
    draw_panel_05_score_distribution(fig.add_subplot(gs[2, 0]), ctx)
    ax_f = fig.add_subplot(gs[2, 1:3])
    draw_panel_06_subscore_violin(ax_f, ctx)
    fig.suptitle(
        "GLIOMA-TARGET — integrative therapeutic target landscape (Welch / TOIL DEA + DepMap + HGNC + STRING)",
        fontsize=FS_SUPTITLE,
        fontweight="bold",
        color="#f4f7fc",
        y=0.985,
    )
    return fig


def save_individual_panels(
    ctx: VizContext,
    panel_dir: Path,
    dpi: float,
    prefix: str,
) -> list[Path]:
    apply_dark_style()
    panel_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for slug, drawer in PANEL_DRAWERS:
        w, h = PANEL_FIGSIZE.get(slug, (14.0, 11.0))
        fig = plt.figure(figsize=(w, h), facecolor="#06080c")
        ax = fig.add_subplot(111)
        drawer(fig, ax, ctx)
        if slug == "01_tier1_ranked_bars":
            fig.subplots_adjust(left=0.40, right=0.94, top=0.86, bottom=0.05)
        elif slug == "04_subscore_heatmap":
            fig.subplots_adjust(left=0.10, right=0.94, top=0.82, bottom=0.50)
        else:
            fig.subplots_adjust(left=0.12, right=0.94, top=0.90, bottom=0.12)
        name = f"{prefix}{slug}.png" if prefix else f"{slug}.png"
        out = panel_dir / name
        fig.savefig(out, dpi=dpi, bbox_inches="tight", pad_inches=0.2, facecolor="#06080c")
        plt.close(fig)
        written.append(out)
        px_w = int(w * dpi)
        px_h = int(h * dpi)
        print(f"Wrote {out} (~{px_w}×{px_h} px @ {dpi} DPI)")
    return written


def load_tables(
    tier1_path: Path,
    full_path: Path | None,
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    t1 = pd.read_csv(tier1_path, sep="\t", low_memory=False)
    if full_path and full_path.is_file():
        full = pd.read_csv(full_path, sep="\t", low_memory=False)
    else:
        full = None
    return t1, full


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tier1-tsv", default="results/module7/glioma_target_tier1_welch.tsv")
    ap.add_argument("--full-tsv", default="results/module7/gts_candidate_table_welch_stub.tsv")
    ap.add_argument("--output", default="results/module7/glioma_target_results_uhd.png")
    ap.add_argument(
        "--output-pdf",
        default="",
        help="Optional composite PDF path (vector, same layout as --output PNG).",
    )
    ap.add_argument("--dpi", type=float, default=400.0)
    ap.add_argument("--fig-width", type=float, default=20.0)
    ap.add_argument("--fig-height", type=float, default=11.0, help="Composite figure height (6 panels, no text box).")
    ap.add_argument("--top-bars", type=int, default=42)
    ap.add_argument("--top-heat", type=int, default=48)
    ap.add_argument(
        "--split-panels",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write six separate UHD PNGs under --panel-dir (default: on).",
    )
    ap.add_argument("--panel-dir", default="results/module7/glioma_target_panels")
    ap.add_argument("--panel-prefix", default="", help="Optional prefix for panel filenames.")
    ap.add_argument(
        "--no-composite",
        action="store_true",
        help="Only write split panels, not the combined --output file.",
    )
    args = ap.parse_args()

    rr = repo_root()
    t1_path = rr / args.tier1_tsv.replace("/", os.sep)
    if not t1_path.is_file():
        print(f"ERROR: missing {t1_path}", file=sys.stderr)
        return 1
    full_path = rr / args.full_tsv.replace("/", os.sep)
    tier1, full = load_tables(t1_path, full_path if full_path.is_file() else None)
    if "glioma_target_score" not in tier1.columns:
        print("ERROR: tier-1 TSV missing glioma_target_score", file=sys.stderr)
        return 1

    apply_dark_style()
    ctx = build_context(tier1, full, top_bars=args.top_bars, top_heat=args.top_heat)

    if args.split_panels:
        pdir = rr / args.panel_dir.replace("/", os.sep)
        save_individual_panels(ctx, pdir, dpi=args.dpi, prefix=args.panel_prefix)

    if not args.no_composite:
        fig = build_six_panel_figure(ctx, args.fig_width, args.fig_height)
        out = rr / args.output.replace("/", os.sep)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=args.dpi, bbox_inches="tight", pad_inches=0.12)
        pdf_rel = str(args.output_pdf or "").strip()
        if pdf_rel:
            pdf_path = rr / pdf_rel.replace("/", os.sep)
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(pdf_path, format="pdf", bbox_inches="tight", pad_inches=0.12)
            print(f"Wrote composite PDF {pdf_path}")
        plt.close(fig)
        wpx = int(args.fig_width * args.dpi)
        hpx = int(args.fig_height * args.dpi)
        print(f"Wrote composite {out} ({wpx}×{hpx} px nominal)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
