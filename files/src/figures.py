
# ═════════════════════════════════════════════════════════════════════════════
#  PUBLICATION FIGURES
#
#  One figure per metric from a resolution-shell table (CORRECT.LP or
#  XSCALE.LP), plus a four-panel overview, written next to the log they came
#  from, as PNG (300 dpi) and PDF (vector, for a journal).
#
#  What these do that a plain "metric versus shell" plot cannot:
#
#   * the x axis is LINEAR IN 1/d², the space XDS bins the shells in, so the
#     curve shows where the data really fall off instead of stretching the few
#     low-resolution shells to the same width as the high-resolution ones;
#   * the DECISION each metric drives is drawn in - the threshold as a rule
#     and the cut-off the program itself suggests for that criterion, with
#     the range beyond it shaded, so what would be discarded is visible.
#     The number comes from the same code the cut-off buttons use, so the
#     figure and the interface can never disagree;
#   * ICE RINGS the log gives strong or moderate evidence for are marked as
#     bands: a completeness dip or an R-meas spike at 3.90 or 2.25 Å is
#     contamination, not resolution;
#   * a CC½ shell XDS marks as significant at the 0.1 % level gets a filled
#     marker, one it does not gets a hollow one;
#   * percentages use a fixed 0-100 axis, so two runs can be laid side by side;
#   * the overall row, the space group and the cell travel with the figure, and
#     a provenance line names the program, the log and the day - a figure in a
#     paper should say where it came from.
#
#  The interface's own charts stay what they are: dark, interactive, every
#  series on one canvas.  These are for printing.
#
#  matplotlib only, and never pyplot (it picks a GUI backend and is not safe to
#  call from a request thread): Figure + FigureCanvasAgg, as the frame viewer.
# ═════════════════════════════════════════════════════════════════════════════

# Ink on paper: CrystalPilot's own accents, darkened for print on white.
_FIG_INK = "#1a202c"        # titles and values
_FIG_MUTED = "#4a5568"      # axis labels, footer
_FIG_RULE = "#cbd5e0"       # axes and grid
_FIG_BEYOND = "#edf2f7"     # the range past the cut-off
_FIG_ICE = "#faf089"        # detected ice rings
_FIG_MARK = "#718096"       # thresholds, cut-off marker

FIGURE_METRICS = {
    "cc_half": {
        "file": "CC_HALF_vs_Resolution",
        "label": "CC½ (%)",
        "title": "Half-data-set correlation",
        "color": "#2b6cb0",
        "threshold": (50.0, "CC½ 50%"),
        "criterion": "cc_half_50",
        "percent": True,
        "stars": True,
    },
    "i_sigma": {
        "file": "I_SIGMA_vs_Resolution",
        "label": "I/σ",
        "title": "Signal-to-noise ratio",
        "color": "#434190",
        "threshold": (2.0, "I/σ = 2"),
        "criterion": "isig2",
        "percent": False,
        "stars": False,
    },
    "completeness": {
        # No cut-off criterion rides on completeness, so the overall value is
        # drawn as the reference instead of an invented threshold.
        "file": "COMPLETENESS_vs_Resolution",
        "label": "Completeness (%)",
        "title": "Completeness",
        "color": "#2c7a7b",
        "threshold": None,
        "criterion": None,
        "percent": True,
        "stars": False,
    },
    "r_meas": {
        # The 55 % criterion is defined on R-obs, so only its cut-off is marked
        # here - drawing a 55 % rule against an R-meas curve would be wrong.
        "file": "R_MEAS_vs_Resolution",
        "label": "R-meas (%)",
        "title": "Merging residual",
        "color": "#9c4221",
        "threshold": None,
        "criterion": "r_obs_55",
        "percent": False,
        "stars": False,
    },
}
FIGURE_ORDER = ["cc_half", "i_sigma", "completeness", "r_meas"]
FIGURE_PANEL = "Resolution_Statistics"
FIGURE_FORMATS = ("png", "pdf")
FIGURE_SOURCES = ("CORRECT", "XSCALE")
_CRITERION_LABEL = {"isig2": "I/σ 2", "cc_half_50": "CC½ 50%",
                    "r_obs_55": "R-obs 55%", "cc_half_sig": "CC½ significant"}


def figure_file_name(source, metric, fmt="png"):
    """The file one metric is written to.

    The source is part of the name: XSCALE.LP usually sits in the same folder as
    CORRECT.LP, and both give a curve of the same metrics, so bare names meant
    the second set quietly replaced the first.
    """
    stem = FIGURE_PANEL if metric == "panel" else FIGURE_METRICS[metric]["file"]
    return "%s_%s.%s" % (str(source).upper(), stem, fmt)


def figure_file_names(source):
    """Every name this source can write - what a download request is checked against."""
    return {figure_file_name(source, metric, fmt)
            for metric in list(FIGURE_ORDER) + ["panel"]
            for fmt in FIGURE_FORMATS}


def figure_source_of(name):
    """Which log a figure name belongs to, or None when it is not one of ours."""
    for source in FIGURE_SOURCES:
        if name in figure_file_names(source):
            return source
    return None


# ── reading the table ────────────────────────────────────────────────────────
def _fig_number(value):
    """A cell of an XDS table as a number: '-1.8', '97.4*', '55.3%' -> float."""
    text = str(value or "").strip().replace("%", "").replace("*", "")
    if not text or text in ("-", "--"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _fig_shells(metrics):
    """The shell rows of a parsed LP, without the 'total' line."""
    table = metrics.get("statistics_table") or []
    return [r for r in table if str(r.get("resolution", "")).strip().lower() != "total"]


def _fig_total(metrics):
    """The 'total' row, or None."""
    for row in metrics.get("statistics_table") or []:
        if str(row.get("resolution", "")).strip().lower() == "total":
            return row
    return None


def _fig_points(shells, metric):
    """[(1/d², value, significant)] for one metric, low to high resolution."""
    points = []
    for row in shells:
        d = _fig_number(row.get("resolution"))
        value = _fig_number(row.get(metric))
        if d is None or value is None or d <= 0:
            continue
        points.append((1.0 / (d * d), value, "*" in str(row.get(metric, ""))))
    return points


def _fig_annotation(metrics):
    """Space group and cell on one line (empty when the log does not say)."""
    parts = []
    name = str(metrics.get("current_sg_name") or "").strip()
    number = str(metrics.get("space_group") or "").strip()
    if name and number:
        parts.append("%s (no. %s)" % (name, number))
    elif name or number:
        parts.append(name or ("space group " + number))
    cell = metrics.get("unit_cell") or {}
    try:
        a, b, c = float(cell["a"]), float(cell["b"]), float(cell["c"])
        al, be, ga = float(cell["alpha"]), float(cell["beta"]), float(cell["gamma"])
    except (KeyError, TypeError, ValueError):
        return "   ".join(parts)
    text = "%.1f  %.1f  %.1f Å" % (a, b, c)
    if max(abs(al - 90), abs(be - 90), abs(ga - 90)) > 0.05:
        text += "   %.1f  %.1f  %.1f°" % (al, be, ga)
    parts.append(text)
    return "   ".join(parts)


def _fig_overall(metrics, shells):
    """The line under the axes: the overall row plus what else XDS reports."""
    bits = []
    if shells:
        # the first shell's number is its HIGH limit; the data's low limit is reported separately
        lo = _fig_number(metrics.get("resolution_range_low")) or _fig_number(shells[0].get("resolution"))
        hi = _fig_number(shells[-1].get("resolution"))
        if lo and hi:
            bits.append("%.2f–%.2f Å" % (lo, hi))
    total = _fig_total(metrics)
    if total:
        for key, fmt in (("completeness", "completeness %.1f%%"), ("r_meas", "R-meas %.1f%%"),
                         ("i_sigma", "I/σ %.1f"), ("cc_half", "CC½ %.1f%%")):
            value = _fig_number(total.get(key))
            if value is not None:
                bits.append(fmt % value)
    isa = metrics.get("isa")
    isa = _fig_number(isa.get("isa")) if isinstance(isa, dict) else None
    if isa is not None:
        bits.append("ISa %.1f" % isa)
    friedel = str(metrics.get("friedels_law") or "").strip().upper()
    if friedel in ("TRUE", "FALSE"):
        bits.append("Friedel's law " + friedel.lower())
    return ("Overall  " + "  ·  ".join(bits)) if bits else ""


def _fig_overall_values(metrics):
    """The overall row as numbers, for the reference line on a metric."""
    total = _fig_total(metrics) or {}
    return {key: _fig_number(total.get(key)) for key in FIGURE_ORDER}


def _fig_ice_bands(metrics):
    """[(1/d²_lo, 1/d²_hi, label)] for the ice rings the log shows evidence of."""
    bands = []
    try:
        rings = LPParser.detect_ice_rings(metrics.get("statistics_table") or [])
    except Exception:
        return bands
    for ring in rings or []:
        # weak evidence at every candidate spacing reads as noise on a figure:
        # the same rule AutoPilot uses before it excludes a ring
        if not LPParser.ice_ring_is_actionable(ring):
            continue
        try:
            lo, hi = float(ring.get("lo")), float(ring.get("hi"))
        except (TypeError, ValueError):
            continue
        if lo <= 0 or hi <= 0:
            continue
        bands.append((1.0 / (max(lo, hi) ** 2), 1.0 / (min(lo, hi) ** 2), str(ring.get("label") or "")))
    return bands


# ── drawing ──────────────────────────────────────────────────────────────────
def _fig_axes(ax, points, percent, label):
    """Axes linear in 1/d² but labelled in Å; horizontal grid, two spines."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    span = max(xs) - min(xs)
    pad = (span * 0.04) if span else 0.01
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    if percent:
        ax.set_ylim(0, 100)                 # fixed, so two runs compare directly
    else:
        ax.set_ylim(min(0.0, min(ys) * 1.1), (max(ys) * 1.14) if max(ys) > 0 else 1.0)
    lo_x, hi_x = min(xs), max(xs)
    ticks = [lo_x + (hi_x - lo_x) * i / 5.0 for i in range(6)]
    ax.set_xticks([t for t in ticks if t > 0])
    ax.set_xticklabels(["%.2f" % (1.0 / (t ** 0.5)) for t in ticks if t > 0])
    ax.set_xlabel("Resolution (Å)   —   linear in 1/d²", fontsize=9, color=_FIG_MUTED, labelpad=7)
    ax.set_ylabel(label, fontsize=10, color=_FIG_INK, labelpad=6)
    ax.grid(True, axis="y", color=_FIG_RULE, linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(_FIG_RULE)
        ax.spines[side].set_linewidth(0.9)
    ax.tick_params(colors=_FIG_MUTED, labelsize=9, length=3, width=0.8)


def _fig_draw_metric(ax, metric, points, context, legend=True):
    """One metric on one axis: bands, the decision it drives, then the curve."""
    spec = FIGURE_METRICS[metric]
    _fig_axes(ax, points, spec["percent"], spec["label"])
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_lo, x_hi = ax.get_xlim()
    y_lo, y_hi = ax.get_ylim()

    # what the suggested cut-off would discard, behind everything else
    cut_d = context["cutoffs"].get(spec["criterion"]) if spec["criterion"] else None
    try:
        cut_x = 1.0 / (float(cut_d) ** 2) if cut_d else None
    except (TypeError, ValueError, ZeroDivisionError):
        cut_x = None
    if cut_x and x_lo < cut_x < x_hi:
        ax.axvspan(cut_x, x_hi, color=_FIG_BEYOND, zorder=0)
        ax.axvline(cut_x, color=_FIG_MARK, linewidth=1.0, dashes=(5, 3), zorder=2)
        # one label, one number: the cut-off this criterion gives
        ax.annotate("%s\ncut-off %.2f Å" % (_CRITERION_LABEL.get(spec["criterion"], "suggested"), float(cut_d)),
                    xy=(cut_x, y_hi), xytext=(5, -5), textcoords="offset points",
                    ha="left", va="top", fontsize=8, color=_FIG_MARK, linespacing=1.5, zorder=5)

    # a dip or a spike here is ice, not resolution
    first_ice = True
    for x1, x2, _label in context["ice"]:
        if x2 < x_lo or x1 > x_hi:
            continue
        ax.axvspan(max(x1, x_lo), min(x2, x_hi), color=_FIG_ICE, alpha=0.6, zorder=1,
                   label="detected ice ring" if (first_ice and legend) else None)
        first_ice = False

    if spec["threshold"]:
        level, tlabel = spec["threshold"]
        if y_lo <= level <= y_hi:
            ax.axhline(level, color=_FIG_MARK, linewidth=0.9, dashes=(2, 3), zorder=2)
            # named at the right edge only when no cut-off line already names it
            if not cut_x:
                ax.annotate(tlabel, xy=(x_hi, level), xytext=(-2, 4), textcoords="offset points",
                            ha="right", va="bottom", fontsize=8, color=_FIG_MARK, zorder=5)
    else:
        # no threshold: show the overall value of this metric as the reference
        overall = context["overall_values"].get(metric)
        if overall is not None and y_lo <= overall <= y_hi:
            ax.axhline(overall, color=_FIG_MARK, linewidth=0.9, dashes=(2, 3), zorder=2)
            ax.annotate("overall %.1f%s" % (overall, "%" if spec["percent"] else ""),
                        xy=(x_hi, overall), xytext=(-2, 4), textcoords="offset points",
                        ha="right", va="bottom", fontsize=8, color=_FIG_MARK, zorder=5)

    colour = spec["color"]
    ax.plot(xs, ys, color=colour, linewidth=1.9, solid_capstyle="round", zorder=3)
    if spec["stars"] and any(p[2] for p in points):
        for subset, face, edge_w, label in (
                ([p for p in points if p[2]], colour, 0.9, "significant at 0.1%"),
                ([p for p in points if not p[2]], "white", 1.3, "not significant")):
            if subset:
                ax.plot([p[0] for p in subset], [p[1] for p in subset], linestyle="none", marker="o",
                        markersize=5.4, markerfacecolor=face, markeredgecolor=colour if face == "white" else "white",
                        markeredgewidth=edge_w, zorder=4, label=label if legend else None)
    else:
        ax.plot(xs, ys, linestyle="none", marker="o", markersize=5, markerfacecolor=colour,
                markeredgecolor="white", markeredgewidth=0.9, zorder=4)
    ax.set_title(spec["title"], fontsize=11, color=_FIG_INK, loc="left", pad=8, fontweight="semibold")
    handles, _labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(loc="lower left", fontsize=8, frameon=False, handlelength=1.6, borderaxespad=0.4)


def _fig_footer(fig, context, subtitle, left=0.012):
    """What this is (top), the overall numbers (bottom), where it came from (top right).

    The provenance line sits at the top right because the overall line is
    long and the two shared a baseline in the first version: they overlapped.
    """
    if subtitle:
        fig.text(left, 0.972, subtitle, fontsize=9, color=_FIG_MUTED, ha="left", va="top")
    if context["provenance"]:
        fig.text(0.988, 0.972, context["provenance"], fontsize=7.5, color="#a0aec0", ha="right", va="top")
    if context["overall"]:
        fig.text(left, 0.022, context["overall"], fontsize=8.5, color=_FIG_MUTED, ha="left", va="bottom")


def _fig_save(fig, out_dir, source, metric):
    """PNG to look at, PDF for a journal. Returns the paths written."""
    import matplotlib
    written = []
    # Type 42 keeps the PDF's text searchable and editable, which is what
    # journals ask for; matplotlib's default Type 3 is refused by some.
    with matplotlib.rc_context({"pdf.fonttype": 42, "ps.fonttype": 42}):
        for fmt in FIGURE_FORMATS:
            target = out_dir / figure_file_name(source, metric, fmt)
            fig.savefig(str(target), format=fmt, facecolor="white", dpi=300)
            written.append(target)
    return written


def write_metric_figure(out_dir, source, metric, shells, context):
    """One metric as PNG and PDF. Returns the paths (empty when there is no curve)."""
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    points = _fig_points(shells, metric)
    if len(points) < 2:
        return []
    fig = Figure(figsize=(7.2, 4.7), dpi=300)
    FigureCanvasAgg(fig)
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0.095, 0.165, 0.885, 0.70])
    _fig_draw_metric(ax, metric, points, context)
    _fig_footer(fig, context, context["subtitle"], left=0.095)
    return _fig_save(fig, out_dir, source, metric)


def write_panel_figure(out_dir, source, shells, context, metrics=None):
    """Every metric on one sheet - usually the figure a report wants."""
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    use = [m for m in (metrics or FIGURE_ORDER) if len(_fig_points(shells, m)) >= 2]
    if len(use) < 2:
        return []
    fig = Figure(figsize=(11.0, 7.4), dpi=300)
    FigureCanvasAgg(fig)
    fig.patch.set_facecolor("white")
    rows, cols = (2, 2) if len(use) > 2 else (1, len(use))
    for i, metric in enumerate(use):
        # the key belongs on the sheet once, not in every panel
        _fig_draw_metric(fig.add_subplot(rows, cols, i + 1), metric, _fig_points(shells, metric),
                         context, legend=(i == 0))
    fig.subplots_adjust(left=0.065, right=0.985, top=0.90, bottom=0.105, wspace=0.20, hspace=0.45)
    _fig_footer(fig, context, "Resolution statistics   ·   " + context["subtitle"])
    return _fig_save(fig, out_dir, source, "panel")


def publication_figures(lp_path, out_dir, source="CORRECT", metrics=None):
    """Write the figures for an LP file.

    Returns {"files": [...], "skipped": [...], "annotation": str, "shells": n}.
    Raises RuntimeError when matplotlib is missing or the LP has no shell table.
    """
    from datetime import datetime as _dt
    from pathlib import Path as _Path
    lp_path = _Path(lp_path)
    out_dir = _Path(out_dir)
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        raise RuntimeError("matplotlib is not installed in this environment. "
                           "The Environment screen offers to install it (numpy, matplotlib, h5py, hdf5plugin, fabio).")

    content = _read_text_lenient(lp_path)
    parsed = LPParser.parse_xscale(content) if str(source).upper() == "XSCALE" else LPParser.parse_correct(content)
    shells = _fig_shells(parsed)
    if len(shells) < 2:
        raise RuntimeError("No resolution-shell table in " + lp_path.name +
                           " - run CORRECT (or XSCALE) to completion first.")

    wanted = [m for m in (metrics or FIGURE_ORDER) if m in FIGURE_METRICS]
    if not wanted:
        raise RuntimeError("No known metric requested. Known: " + ", ".join(FIGURE_ORDER))

    try:
        cutoffs = (LPParser.determine_resolution_cutoff(parsed.get("statistics_table") or []) or {}).get("all_cutoffs") or {}
    except Exception:
        cutoffs = {}
    annotation = _fig_annotation(parsed)
    context = {
        "ice": _fig_ice_bands(parsed),
        "cutoffs": cutoffs,
        "overall": _fig_overall(parsed, shells),
        "overall_values": _fig_overall_values(parsed),
        "subtitle": ("%s   ·   %s" % (str(source).upper(), annotation)) if annotation else str(source).upper(),
        "provenance": "CrystalPilot %s   ·   %s   ·   %s" % (VERSION, lp_path.name, _dt.now().strftime("%Y-%m-%d")),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    written, skipped = [], []

    def record(paths, metric, points):
        for path in paths:
            written.append({"metric": metric, "name": path.name, "path": str(path),
                            "format": path.suffix.lstrip("."), "points": points,
                            "size": path.stat().st_size,
                            "title": "All metrics" if metric == "panel" else FIGURE_METRICS[metric]["title"]})

    for metric in wanted:
        try:
            paths = write_metric_figure(out_dir, source, metric, shells, context)
        except Exception as exc:
            skipped.append({"metric": metric, "reason": str(exc)})
            continue
        if not paths:
            skipped.append({"metric": metric, "reason": "no values in the shell table"})
            continue
        record(paths, metric, len(_fig_points(shells, metric)))

    if len(wanted) > 1:
        try:
            paths = write_panel_figure(out_dir, source, shells, context, wanted)
            if paths:
                record(paths, "panel", len(shells))
        except Exception as exc:
            skipped.append({"metric": "panel", "reason": str(exc)})

    if not written:
        raise RuntimeError("None of the requested metrics had values in " + lp_path.name)
    return {"files": written, "skipped": skipped, "annotation": annotation, "shells": len(shells)}
