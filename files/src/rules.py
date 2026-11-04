
# ═════════════════════════════════════════════════════════════════════════════
#  PAGE RULES - what the interface concludes from parsed results
#
#  The step diagnostics, the frame-rejection suggestions, the XSCALE autofill and
#  the rows of Table 1, on the server so that the page and an agent get one answer.
#  LPParser.diagnose_* is a separate set: it decides what AutoPilot retries.
#
#  js_float and js_fixed read and print numbers as the page always has, so a value
#  in a table or a message keeps its last digit (2.5 prints as 3 at no decimals).
# ═════════════════════════════════════════════════════════════════════════════
_JS_FLOAT_PREFIX = re.compile(r"\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)")


def js_float(value):
    """The number a value starts with, as '12.3%' or '99.9*' give 12.3 and 99.9.  None when there is none."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value == value else None
    match = _JS_FLOAT_PREFIX.match(str(value))
    return float(match.group(1)) if match else None


def js_fixed(value, digits):
    """A number with a fixed count of decimals; an exact tie rounds away from zero."""
    from decimal import Decimal, ROUND_HALF_UP
    number = float(value) or 0.0            # -0.0 prints as 0.0; -0.04 stays -0.0 at one decimal
    step = Decimal(1).scaleb(-digits) if digits else Decimal(1)
    return format(Decimal(number).quantize(step, rounding=ROUND_HALF_UP), "f")


def _js_number_text(value):
    """A number as text with no trailing .0: 18.0 is 18, 0.1 stays 0.1."""
    if isinstance(value, float) and value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return str(value)


def _js_true(value):
    """True for what an if statement in the page took as set: not empty text, not 0, not missing."""
    if value is None or value is False or value == "" or value == 0:
        return False
    return value == value


def _is_total(row):
    return str(row.get("resolution") or "").lower() == "total"


def _has_resolution(row):
    return _js_true(row.get("resolution"))


def _last_total(table):
    for row in reversed(table):
        if _has_resolution(row) and _is_total(row):
            return row
    return None


# ── step diagnostics ─────────────────────────────────────────────────────────
def idxref_lp_extras(text):
    """The subtree table of IDXREF.LP, and the axes whose cluster indices are half-integer.

    An axis counts when at least 30% of the cluster rows (and at least 3 rows) show an
    index between 0.35 and 0.65 from the nearest integer on it.
    """
    result = {"all_subtrees": [], "half_integer_axes": []}
    if not text:
        return result
    lines = str(text).split("\n")
    in_subtree = False
    for raw in lines:
        line = raw.rstrip()
        if re.search(r"SUBTREE\s+POPULATION", line):
            in_subtree = True
            continue
        if in_subtree:
            row = re.match(r"^\s*(\d+)\s+(\d+)\s*$", line)
            if row:
                result["all_subtrees"].append({"subtree": int(row.group(1)), "population": int(row.group(2))})
            elif line.strip() and result["all_subtrees"]:
                in_subtree = False
    in_cluster = False
    half = [0, 0, 0]
    rows = 0
    pattern = re.compile(r"^\s*\d+\s+.*\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$")
    for line in lines:
        if "CLUSTER COORDINATES AND INDICES" in line:
            in_cluster = True
            continue
        if in_cluster:
            if re.match(r"^\s*#\s+COORDINATES", line):
                continue
            row = pattern.match(line)
            if row:
                rows += 1
                for axis in range(3):
                    index = float(row.group(axis + 1))
                    fraction = abs(index - math.floor(index + 0.5))
                    if 0.35 < fraction < 0.65:
                        half[axis] += 1
            elif re.match(r"^\s*$", line) or "PARAMETERS OF" in line or re.match(r"^\s*\*", line):
                if rows > 0:
                    in_cluster = False
    if rows >= 3:
        for axis in range(3):
            if half[axis] / rows >= 0.3:
                result["half_integer_axes"].append(axis + 1)
    return result


def _diagnostics_idxref(m, diags):
    def add(severity, title, body):
        diags.append({"severity": severity, "title": title, "body": body})

    if "indexed_count" in m and "total_spots" in m and (m["total_spots"] or 0) > 0:
        pct = (m["indexed_count"] or 0) / m["total_spots"] * 100
        if pct < 30:
            add("warning", "Very low indexing rate (" + js_fixed(pct, 1) + "%)",
                "Fewer than 30% of spots were indexed. Common causes: wrong beam center (ORGX/ORGY), ice rings contributing non-Bragg spots, multiple crystals, or incorrect DETECTOR_DISTANCE. "
                "Try: verify beam center visually, add EXCLUDE_RESOLUTION_RANGE= for ice rings, increase MINIMUM_NUMBER_OF_PIXELS_IN_A_SPOT=, or use the Auto-Indexing tool below.")
        elif pct < 50:
            add("caution", "Low indexing rate (" + js_fixed(pct, 1) + "%)",
                "Less than 50% of spots were indexed. This may be acceptable if there are ice rings or a second lattice, but check that beam center and detector geometry are correct. "
                "Consider excluding ice ring resolution ranges or increasing MINIMUM_NUMBER_OF_PIXELS_IN_A_SPOT=.")
    if all(k in m for k in ("orgx", "orgy", "orgx_initial", "orgy_initial")):
        shift = math.sqrt((m["orgx"] - m["orgx_initial"]) ** 2 + (m["orgy"] - m["orgy_initial"]) ** 2)
        moved = ("(ORGX " + js_fixed(m["orgx_initial"], 1) + " → " + js_fixed(m["orgx"], 1) + ", ORGY "
                 + js_fixed(m["orgy_initial"], 1) + " → " + js_fixed(m["orgy"], 1) + "). ")
        if shift > 30:
            add("warning", "Very large beam center shift (" + js_fixed(shift, 1) + " px)",
                "IDXREF refined the beam center by " + js_fixed(shift, 1) + " pixels from the header value " + moved
                + "Shifts this large risk mis-indexing. Verify the beam center visually using the Frame Viewer with a low-angle image, "
                  "then update ORGX/ORGY in the parameter editor and re-run COLSPOT + IDXREF.")
        elif shift > 15:
            add("caution", "Large beam center shift (" + js_fixed(shift, 1) + " px)",
                "The header beam center was refined by " + js_fixed(shift, 1) + " pixels " + moved
                + "This is unusually large and the header value may be inaccurate. If subsequent steps show high R-factors, verify the beam center independently.")
    spot = m.get("sigma_spot")
    if spot is not None and spot > 3.0:
        add("warning" if spot > 6.0 else "caution", "High σ(spot) = " + js_fixed(spot, 2) + " px",
            "The standard deviation between observed and predicted spot positions is above 3 pixels. "
            "This can happen with split reflections, high mosaicity, or poorly described detector geometry. "
            "Try increasing MAXIMUM_ERROR_OF_SPOT_POSITION= (e.g. to 6.0). "
            "If the crystal diffracts well but spots are split, check for multiple lattices or twinning.")
    spindle = m.get("sigma_spindle")
    if spindle is not None and spindle > 0.5:
        add("warning" if spindle > 2.0 else "caution", "High σ(spindle) = " + js_fixed(spindle, 3) + "°",
            "The standard deviation of spindle (rotation) positions is above 0.5°. "
            "This suggests problems with the rotation axis calibration, goniometer, or oscillation range. "
            "Try increasing MAXIMUM_ERROR_OF_SPINDLE_POSITION= (e.g. to 4.0), or check that the oscillation range in the header is correct.")
    subtrees = m.get("_all_subtrees")
    if subtrees and len(subtrees) >= 2:
        first, second = subtrees[0]["population"], subtrees[1]["population"]
        if first > 0 and second > 0 and second / first > 0.3:
            ratio = second / first
            listed = ", ".join("#" + str(s["subtree"]) + ": " + str(s["population"]) for s in subtrees[:5])
            add("warning" if ratio > 0.7 else "caution", "Multiple subtrees with comparable populations",
                "The subtree table shows two or more lattice clusters with similar populations (" + listed + "). "
                "This typically indicates a twinned crystal, multiple crystals in the beam, or a split crystal. "
                "Try: narrower SPOT_RANGE (fewer frames), SEPMIN=4 CLUSTER_RADIUS=2 (for Pilatus/Eiger), "
                "or inspect reciprocal space with spot2pdb in coot to visualize the separate lattices.")
    axes = m.get("_half_integer_axes")
    if axes:
        labels = ", ".join("axis " + str(a) for a in axes)
        add("caution", "Half-integer cluster indices detected (" + labels + ")",
            "The difference vector table shows systematic half-integer indices along " + labels + ". "
            "This usually means the corresponding unit cell axis is doubled relative to what IDXREF found. "
            "Check the reduced cell parameters below the cluster table — if an axis is suspiciously short, "
            "try doubling it via UNIT_CELL_CONSTANTS= with SPACE_GROUP_NUMBER=1. "
            "Alternatively, use well-separated SPOT_RANGEs instead of one continuous range (XDSwiki).")


def _diagnostics_correct(m, diags):
    def add(severity, title, body):
        diags.append({"severity": severity, "title": title, "body": body})

    table = m.get("statistics_table") or []
    isa_entry = m.get("isa") if _js_true(m.get("isa")) else None
    isa = js_float(isa_entry.get("isa")) if isinstance(isa_entry, dict) else None
    if isa is not None:
        if isa < 5:
            add("warning", "ISa = " + js_fixed(isa, 1) + " — severe systematic errors",
                "ISa below 5 almost always indicates something is severely wrong (XDSwiki). "
                "Common causes: wrong geometry in XDS.INP, wrong space group (too high symmetry), high radiation damage, "
                "badly split crystal, or mechanical/detector problems. "
                "Check: is the space group correct? Is the crystal single? Discuss with beamline staff if hardware is suspected.")
        elif isa < 10:
            add("caution", "ISa = " + js_fixed(isa, 1) + " — elevated systematic errors",
                "ISa below 10 indicates significant systematic errors beyond counting statistics. "
                "Possible causes: beam instability, crystal splitting, ice contamination, detector calibration issues, "
                "or absorption from a large loop/mount. "
                "Good experimental setups typically achieve ISa ≥ 20 (Diederichs, 2010).")
    mosaicity = m.get("mosaicity")
    if mosaicity is not None:
        if mosaicity > 2.0:
            add("warning", "Very high mosaicity = " + js_fixed(mosaicity, 3) + "°",
                "Mosaicity above 2° is extreme and will cause severe spot overlap. "
                "Consider: re-screening for a better crystal, improving cryoprotection, annealing, or collecting with finer slicing (smaller oscillation range). "
                "If this is the only crystal available, ensure the oscillation range is ≤ mosaicity/3.")
        elif mosaicity > 1.0:
            add("caution", "High mosaicity = " + js_fixed(mosaicity, 3) + "°",
                "Mosaicity above 1° causes reflection overlap and degrades data quality. "
                "Common causes: cryo-cooling stress, physical crystal damage, or inherent disorder. "
                "Consider fine-slicing (oscillation ≤ 0.5°), flash-annealing, or trying a different cryoprotectant. "
                "Verify the oscillation range is smaller than the mosaicity.")
    if len(table) > 2:
        for row in table[:3]:
            if _has_resolution(row) and not _is_total(row):
                r_meas = js_float(row.get("r_meas"))
                value = r_meas if r_meas is not None else js_float(row.get("r_obs"))
                if value is not None and value > 15:
                    add("warning" if value > 30 else "caution", "High R-factor at low resolution (" + js_fixed(value, 1) + "% in first shell)",
                        "Elevated R-factors in the lowest-resolution shell (where signal should be strongest) "
                        "typically indicate a fundamental problem rather than ice rings. "
                        "Check: is the indexing correct? Is the beam center accurate? Is the space group correct? "
                        "A wrong indexing solution often manifests as high R at low resolution with acceptable R at high resolution.")
                break
    total = _last_total(table)
    if total and _js_true(total.get("completeness")):
        completeness = js_float(total.get("completeness"))
        if completeness is not None and completeness < 80:
            add("warning" if completeness < 50 else "caution", "Low overall completeness (" + js_fixed(completeness, 1) + "%)",
                "Completeness below 80% may compromise downstream structure solution and refinement. "
                "Common causes: insufficient rotation range for the crystal symmetry, "
                "detector geometry issues blocking reflections, or overly aggressive resolution cutoff. "
                "For molecular replacement, aim for > 90% completeness; for anomalous phasing, > 95%.")
    if total and isa_entry is not None and isa is not None and isa >= 8:
        overall_r = js_float(total.get("r_meas"))
        if overall_r is not None and overall_r > 20:
            add("caution", "High R-meas (" + js_fixed(overall_r, 1) + "%) despite acceptable ISa (" + js_fixed(isa, 1) + ")",
                "When ISa is reasonable but R-meas is elevated, the most common cause is wrong space group — "
                "XDS may have assigned too-high symmetry, forcing non-equivalent reflections to merge. "
                "Try: re-run CORRECT with SPACE_GROUP_NUMBER=0 to let XDS re-evaluate, "
                "or run POINTLESS for an independent space group determination. "
                "Also check whether the unit cell is correct — a misindexed cell axis produces the same symptom.")
    shells = [row for row in table if _has_resolution(row) and not _is_total(row)]
    if len(table) >= 5 and len(shells) >= 4:
        middle = js_float(shells[int(math.floor(len(shells) * 0.6))].get("completeness"))
        outer = js_float(shells[-1].get("completeness"))
        inner = js_float(shells[0].get("completeness"))
        if None not in (middle, outer, inner) and inner > 90 and middle < 75 and outer < 40:
            add("caution", "Possible anisotropic diffraction (completeness: " + js_fixed(inner, 0) + "% → " + js_fixed(middle, 0) + "% → " + js_fixed(outer, 0) + "%)",
                "Completeness drops steeply across resolution shells, which can indicate anisotropic diffraction — "
                "the crystal diffracts to different resolutions along different axes. "
                "Consider: anisotropic resolution cutoffs (STARANISO server at staraniso.globalphasing.org), "
                "or use the Anisotropy Analysis panel in CrystalPilot for a more detailed assessment. "
                "When reporting, specify resolution limits along each principal axis rather than a single isotropic cutoff.")
    chi2 = m.get("chi2_values")
    if chi2:
        largest = max(chi2)
        if largest > 5.0:
            add("warning", "High correction factor χ² = " + js_fixed(largest, 1),
                "The chi-squared goodness-of-fit for the correction factors (decay, absorption, modulation) is very high. "
                "This means the empirical corrections are struggling to model systematic errors in the data. "
                "Common causes: crystal decay (radiation damage), strong absorption from the mount or crystal, "
                "or anisotropic absorption from a non-spherical crystal. "
                "Try: adjust CORRECTIONS= (e.g. remove MODULATION), or check if the crystal mount is contributing scatter.")
        elif largest > 2.5:
            add("caution", "Elevated correction factor χ² = " + js_fixed(largest, 1),
                "The chi-squared for correction factors is somewhat elevated (ideal ≈ 1.0). "
                "This may indicate moderate absorption effects, crystal decay, or slight model inadequacy. "
                "Usually not critical, but if data quality is worse than expected, investigate absorption or decay.")
    moments = m.get("wilson_moments")
    if moments:
        values = []
        for row in moments:
            if isinstance(row, (list, tuple)) and len(row) >= 3 and row[1] != "overall":
                second = js_float(row[2])
                if second is not None:
                    values.append(second)
        if len(values) >= 3:
            total_moment = 0
            for value in values:
                total_moment = total_moment + value
            average = total_moment / len(values)
            if average < 0.75:
                add("warning", "Wilson second moment ⟨I²⟩/2⟨I⟩² = " + js_fixed(average, 3) + " — possible twinning",
                    "The average second moment of the Wilson distribution is well below the theoretical value of 1.0 for untwinned acentric data "
                    "(a perfect twin gives 0.5). "
                    "This strongly suggests merohedral or pseudo-merohedral twinning. "
                    "Run CTRUNCATE (via the AIMLESS pipeline) for the L-test and H-test to confirm. "
                    "If twinned, structure solution requires twin-aware refinement in REFMAC5 or phenix.refine.")
            elif average < 0.85:
                add("caution", "Wilson second moment ⟨I²⟩/2⟨I⟩² = " + js_fixed(average, 3) + " — check for twinning",
                    "The second moment is slightly below the expected value of 1.0. "
                    "This could indicate partial twinning, pseudo-symmetry, or translational NCS. "
                    "Run CTRUNCATE for formal twinning tests (L-test). "
                    "Note: anisotropy, ice rings, or NCS can also depress the moments without actual twinning.")
    if len(table) >= 3 and len(shells) >= 2:
        cc_outer = js_float(shells[-1].get("cc_half"))
        sigma_outer = js_float(shells[-1].get("i_sigma"))
        if cc_outer is not None and cc_outer < 10 and sigma_outer is not None and sigma_outer < 0.5:
            add("info", "Outer shell: CC½=" + js_fixed(cc_outer, 1) + "%, I/σ=" + js_fixed(sigma_outer, 1) + " — no useful signal",
                "The outermost resolution shell has negligible signal. "
                "This is normal if the resolution cutoff was set conservatively, "
                "but if you see many such shells, consider reducing the resolution limit in XDS.INP "
                "(INCLUDE_RESOLUTION_RANGE=) to speed up processing and reduce noise in the merged data.")
    if m.get("friedels_law") == "FALSE" and total:
        corr = js_float(total.get("anomal_corr"))
        sig = js_float(total.get("siganom"))
        if corr is not None and sig is not None:
            if corr > 30 and sig > 1.2:
                add("info", "Anomalous signal detected (CCanom=" + js_fixed(corr, 0) + "%, SigAnom=" + js_fixed(sig, 2) + ")",
                    "Significant anomalous differences are present in the data overall. "
                    "This is promising for SAD/MAD phasing. "
                    "Check per-shell values to determine the useful resolution range for anomalous signal — "
                    "it typically extends to lower resolution than the diffraction limit.")
            elif corr < 10 and sig < 0.8:
                add("caution", "Weak or absent anomalous signal (CCanom=" + js_fixed(corr, 0) + "%, SigAnom=" + js_fixed(sig, 2) + ")",
                    "The anomalous correlation and SigAnom are very low. "
                    "If this data was collected for SAD/MAD phasing, the anomalous signal may be insufficient. "
                    "Consider: was the wavelength tuned to the absorption edge? Is there enough redundancy? "
                    "If this is native data, set FRIEDEL'S_LAW=TRUE in CORRECT to merge Friedel pairs and improve statistics.")


def page_diagnostics(step, metrics):
    """What the results of IDXREF or CORRECT suggest: a list of {severity, title, body}.
    Sources: XDSwiki "Problems" page, Diederichs CCP4 school material, CCP4BB."""
    diags = []
    if step == "IDXREF":
        _diagnostics_idxref(metrics, diags)
    elif step == "CORRECT":
        _diagnostics_correct(metrics, diags)
    return diags


def idxref_diagnostics(metrics, lp_text):
    """The diagnostics of an IDXREF run, with what only the raw log holds."""
    extras = idxref_lp_extras(lp_text)
    enriched = dict(metrics)
    if extras["all_subtrees"]:
        enriched["_all_subtrees"] = extras["all_subtrees"]
    if extras["half_integer_axes"]:
        enriched["_half_integer_axes"] = extras["half_integer_axes"]
    return page_diagnostics("IDXREF", enriched)


# ── frames to exclude (ΔCC½) ─────────────────────────────────────────────────
def frame_suggestions(data, strategies=None):
    """Bad frame ranges for EXCLUDE_DATA_RANGE, from parsed XDSCC12 results.

    Adapts to how much of the data is damaged.  With under 30% of the frames negative,
    median - MAD outliers work.  From 30% on the median itself is near zero or negative,
    so ΔCC½ < 0 is the threshold (Assmann et al., 2016: such a frame lowers CC½) and the
    worst contiguous negative blocks and the damaged tail are found instead.
    Diederichs recommends excluding no more than about 10% per iteration; suggestions
    are capped at 20% of the frames and the page warns above 10%.
    """
    strategies = strategies or {}
    use = lambda key: strategies.get(key, True) is not False
    summary = data.get("summary") or {}
    frames = data.get("frames") or []
    count = len(frames)
    diagnostics = {"hasRadDamage": False, "radDamageOnsetIdx": None, "radDamageOnsetBatch": None}
    if not count:
        return {"ranges": [], "diagnostics": diagnostics}
    deltas = [f["delta_only"] for f in frames]
    negative_pct = len([v for v in deltas if v < 0]) / count * 100
    median, mad = summary.get("median_delta_only"), summary.get("mad_delta_only")
    if median is None or mad is None:
        ordered = sorted(deltas)
        median = ordered[len(ordered) // 2]
        deviations = sorted(abs(v - median) for v in ordered)
        mad = deviations[len(deviations) // 2]
        if mad < 0.01:
            mad = 0.01
    ranges, used = [], set()

    def sum_of(values):
        total = 0
        for value in values:
            total = total + value
        return total

    # A: radiation damage tail.  Walking back from the end, the tail starts after the
    # first sliding window that averages >= 0; it counts at >= 10 frames and >= 5% of the
    # data, when its second half is worse than its first or both are clearly negative.
    if use("radtail"):
        window = max(3, min(7, int(math.floor(count * 0.02))))
        onset = count
        for start in range(count - window, -1, -1):
            if sum_of(deltas[start:start + window]) / window >= 0:
                onset = start + 1
                break
            if start == 0:
                onset = 0
        length = count - onset
        if length >= 10 and length >= int(math.floor(count * 0.05)):
            half = length // 2
            first_half = deltas[onset:onset + half]
            second_half = deltas[onset + half:]
            avg_first = sum_of(first_half) / len(first_half)
            avg_second = sum_of(second_half) / len(second_half)
            if avg_second < avg_first or (avg_first < -0.5 and avg_second < -0.5):
                diagnostics.update({"hasRadDamage": True, "radDamageOnsetIdx": onset, "radDamageOnsetBatch": frames[onset]["batch"]})
                ranges.append({"start": frames[onset]["batch"], "end": frames[count - 1]["batch"], "count": length,
                               "avg_delta": sum_of(deltas[onset:]) / length, "reason": "radiation_damage"})
                used.update(range(onset, count))

    def finish(run):
        run["avg_delta"] = run["_sum"] / run["count"]
        ranges.append(run)

    def runs_below(threshold, minimum, reason, mark):
        """Contiguous runs of frames under a threshold; mark: they count as used for later strategies."""
        run = None
        for i in range(count):
            if i in used:
                if run and run["count"] >= minimum:
                    finish(run)
                run = None
                continue
            if deltas[i] < threshold:
                if not run:
                    run = {"start": frames[i]["batch"], "end": frames[i]["batch"], "_sum": 0, "count": 0, "_first": i, "reason": reason}
                run["end"] = frames[i]["batch"]
                run["_sum"] = run["_sum"] + deltas[i]
                run["count"] += 1
            else:
                if run and run["count"] >= minimum:
                    finish(run)
                    if mark:
                        used.update(range(run["_first"], run["_first"] + run["count"]))
                run = None
        if run and run["count"] >= minimum:
            finish(run)

    # B: contiguous negative blocks, when the median can no longer be trusted
    if use("negblock") and negative_pct >= 30:
        runs_below(0, 3, "negative_block", True)
    # C: statistical outliers (median - 2 MAD); stricter when B already ran
    if use("outlier2"):
        runs_below(median - 2 * mad, 5 if negative_pct >= 30 else 3, "isolated_bad", True)
    # D: severe outlier pairs (median - 3 MAD)
    if use("outlier3"):
        runs_below(median - 3 * mad, 2, "isolated_bad", False)

    merged = []
    for item in sorted(ranges, key=lambda r: r["start"]):
        if merged and item["start"] <= merged[-1]["end"] + 2:
            previous = merged[-1]
            together = previous["count"] + item["count"]
            previous["avg_delta"] = (previous["avg_delta"] * previous["count"] + item["avg_delta"] * item["count"]) / together
            previous["count"] = together
            previous["end"] = max(previous["end"], item["end"])
            if item["reason"] == "radiation_damage":
                previous["reason"] = "radiation_damage"
        else:
            merged.append({k: item[k] for k in ("start", "end", "count", "avg_delta", "reason")})
    limit = int(math.floor(count * 0.20))
    kept, excluded = [], 0
    for item in sorted(merged, key=lambda r: r["avg_delta"]):
        if excluded + item["count"] <= limit:
            kept.append(item)
            excluded += item["count"]
    return {"ranges": sorted(kept, key=lambda r: r["start"]), "diagnostics": diagnostics}


# ── XSCALE autofill ──────────────────────────────────────────────────────────
def xscale_shells(high):
    """RESOLUTION_SHELLS for a high-resolution limit: ten shells of equal volume in 1/d²
    from 80 Å, then five 0.1 Å shells that visibly reach the cut-off."""
    d_low, n_fine, n_coarse = 80.0, 5, 10
    fine_start = high + n_fine * 0.10
    if fine_start >= d_low:
        return js_fixed(high, 2)
    inv_low = 1.0 / (d_low * d_low)
    inv_fine = 1.0 / (fine_start * fine_start)
    bounds = [math.sqrt(1.0 / (inv_low + i * (inv_fine - inv_low) / n_coarse)) for i in range(1, n_coarse)]
    for i in range(n_fine + 1):
        d = fine_start - i * 0.10
        if d < high - 0.001:
            break
        bounds.append(d)
    return " ".join(js_fixed(v, 2) for v in bounds)


def xds_shells(high):
    """RESOLUTION_SHELLS for CORRECT, which takes at most 9 values: six shells of equal
    volume in 1/d² from 80 Å, then three 0.1 Å shells that reach the cut-off."""
    d_low, n_fine, n_coarse = 80.0, 3, 6
    fine_start = high + n_fine * 0.10
    inv_low = 1.0 / (d_low * d_low)
    inv_fine = 1.0 / (fine_start * fine_start)
    bounds = [math.sqrt(1.0 / (inv_low + i * (inv_fine - inv_low) / n_coarse)) for i in range(1, n_coarse)]
    bounds += [fine_start - i * 0.10 for i in range(n_fine)] + [high]
    return " ".join(js_fixed(v, 2) for v in bounds[-9:])


XSCALE_CUTOFF_MODES = {"isig": ("isig2", "I/σ ≈ 2.0"), "robs": ("r_obs_55", "R-obs ≈ 55%"),
                       "cc50": ("cc_half_50", "CC½ ≈ 50%"), "cc12": ("cc_half_sig", "CC½ significant")}
XSCALE_CUTOFF_DEFAULT = "cc50"


def xscale_autofill(metrics, mode=None):
    """XSCALE.INP values from a parsed CORRECT.LP: the space group, the cell, and a
    resolution from the chosen cut-off (or the next one found: I/σ, R-obs, CC½ 50%, CC½ significant)."""
    out = {"space_group": metrics.get("space_group"), "unit_cell": None, "resolution_low": None,
           "resolution_high": None, "shells": None, "cutoff": None, "fallback": False}
    cell = metrics.get("unit_cell")
    if cell:
        out["unit_cell"] = " ".join(js_fixed(cell[k], 2) for k in ("a", "b", "c", "alpha", "beta", "gamma"))
    cutoffs = metrics.get("cutoffs") or {}
    found = cutoffs.get("all_cutoffs") or {}
    reached = cutoffs.get("reached") or {}
    values = {"isig": found.get("isig2") if reached.get("isig2") else None,
              "robs": found.get("r_obs_55") if reached.get("r_obs_55") else None,
              "cc50": found.get("cc_half_50") if reached.get("cc_half_50") else None,
              "cc12": found.get("cc_half_sig")}
    mode = mode if mode in XSCALE_CUTOFF_MODES else XSCALE_CUTOFF_DEFAULT
    chosen, name = values.get(mode), mode
    if chosen is None:
        out["fallback"] = True
        name = next((k for k in ("isig", "robs", "cc50", "cc12") if values[k] is not None), None)
        chosen = values[name] if name else None
    if chosen is not None:
        high = float(js_fixed(chosen, 2))
        out.update({"resolution_low": "999", "resolution_high": js_fixed(high, 2), "shells": xscale_shells(high),
                    "cutoff": name, "cutoff_label": XSCALE_CUTOFF_MODES[name][1] + " → " + js_fixed(chosen, 2) + " Å" + (" (fallback)" if out["fallback"] else "")})
    return out


# ── Table 1 ──────────────────────────────────────────────────────────────────
SG_SYMBOLS = {1: "P 1", 2: "P -1", 3: "P 2", 4: "P 2₁", 5: "C 2", 10: "P 2/m", 16: "P 2 2 2",
              17: "P 2 2 2₁", 18: "P 2₁ 2₁ 2", 19: "P 2₁ 2₁ 2₁", 20: "C 2 2 2₁", 21: "C 2 2 2", 22: "F 2 2 2",
              23: "I 2 2 2", 24: "I 2₁ 2₁ 2₁", 75: "P 4", 76: "P 4₁", 77: "P 4₂", 78: "P 4₃", 79: "I 4", 80: "I 4₁",
              89: "P 4 2 2", 90: "P 4 2₁ 2", 91: "P 4₁ 2 2", 92: "P 4₁ 2₁ 2", 93: "P 4₂ 2 2", 94: "P 4₂ 2₁ 2",
              95: "P 4₃ 2 2", 96: "P 4₃ 2₁ 2", 97: "I 4 2 2", 98: "I 4₁ 2 2",
              143: "P 3", 144: "P 3₁", 145: "P 3₂", 146: "R 3", 149: "P 3 1 2", 150: "P 3 2 1",
              151: "P 3₁ 1 2", 152: "P 3₁ 2 1", 153: "P 3₂ 1 2", 154: "P 3₂ 2 1", 155: "R 3 2",
              168: "P 6", 169: "P 6₁", 170: "P 6₅", 171: "P 6₂", 172: "P 6₄", 173: "P 6₃",
              177: "P 6 2 2", 178: "P 6₁ 2 2", 179: "P 6₅ 2 2", 180: "P 6₂ 2 2", 181: "P 6₄ 2 2", 182: "P 6₃ 2 2",
              195: "P 2 3", 196: "F 2 3", 197: "I 2 3", 198: "P 2₁ 3", 199: "I 2₁ 3",
              207: "P 4 3 2", 208: "P 4₂ 3 2", 209: "F 4 3 2", 210: "F 4₁ 3 2", 211: "I 4 3 2", 212: "P 4₃ 3 2",
              213: "P 4₁ 3 2", 214: "I 4₁ 3 2"}


def _sg_name(number):
    value = js_float(number)
    n = int(value) if value is not None else None
    return SG_SYMBOLS[n] + " (#" + str(n) + ")" if n in SG_SYMBOLS else "#" + ("NaN" if n is None else str(n))


def table1_rows(d):
    """The rows of Table 1 from /table1data's results: [{section}, {label, value}, ...].
    Each value reads overall (outer shell).  A label may hold markup such as <sub>."""
    inp = d.get("xdsinp") or {}
    xscale = d.get("xscale") or {}
    correct = d.get("correct") or {}
    has_xscale = bool(xscale.get("statistics_table"))
    has_correct = bool(correct.get("statistics_table"))
    stats = xscale["statistics_table"] if has_xscale else (correct["statistics_table"] if has_correct else [])
    total, outer = None, None
    if stats:
        total = _last_total(stats) or stats[-1]
        for row in stats:
            if _has_resolution(row) and not _is_total(row):
                outer = row
    sg = xscale.get("space_group") if _js_true(xscale.get("space_group")) else (
        correct.get("space_group") if _js_true(correct.get("space_group")) else inp.get("space_group"))
    cell = xscale.get("unit_cell") if _js_true(xscale.get("unit_cell")) else (
        correct.get("unit_cell") if _js_true(correct.get("unit_cell")) else None)
    if isinstance(cell, dict):
        cell_text = (", ".join(js_fixed(cell[k], 2) for k in ("a", "b", "c")) + "  "
                     + ", ".join(js_fixed(cell[k], 1) for k in ("alpha", "beta", "gamma")))
    else:
        cell_text = inp.get("unit_cell") or ""
    primary = xscale if has_xscale else (correct if has_correct else {})
    shells = [row for row in stats if _has_resolution(row) and not _is_total(row)]
    rpim = d.get("rpim")
    res_text, res_outer = "", ""
    if outer:
        low = js_float(primary.get("resolution_range_low"))
        if low is None and rpim and _js_true(rpim.get("d_low")):
            low = js_float(rpim.get("d_low"))
        if low is None and d.get("correct") is not None:
            low = js_float(correct.get("resolution_range_low"))
        low_text = "" if low is None else js_fixed(low, 2)
        res_text = (low_text + "–" if low_text else "") + str(outer["resolution"])
        before = shells[-2]["resolution"] if len(shells) > 1 else low_text
        res_outer = (str(before) + "–" if before else "") + str(outer["resolution"])

    def clean(value):
        return "" if value is None else re.sub(r"[%*]", "", str(value)).strip()

    def redundancy(row):
        if not row:
            return ""
        observed, unique = js_float(row.get("observed")), js_float(row.get("unique"))
        return js_fixed(observed / unique, 1) if unique and unique > 0 and observed is not None else ""

    def pair(value, value_outer=None):
        if not value and value != 0:
            return ""
        text = str(value)
        if value_outer is not None and value_outer != "":
            text += " (" + str(value_outer) + ")"
        return text

    def cc_star(row):
        if not row or not _js_true(row.get("cc_half")):
            return ""
        value = js_float(str(row.get("cc_half")).replace("*", ""))
        if value is None:
            return ""
        fraction = value / 100.0
        if fraction <= 0:
            return "0.0"
        fraction = min(fraction, 1)
        return js_fixed(math.sqrt(2.0 * fraction / (1.0 + fraction)) * 100, 1)

    def column(key):
        return pair(clean(total.get(key)), clean(outer.get(key)) if outer else "") if total else ""

    isa = ""
    if xscale.get("isa_table"):
        isa = ", ".join(str(r.get("isa")) for r in xscale["isa_table"])
    elif isinstance(correct.get("isa"), dict) and _js_true(correct["isa"].get("isa")):
        isa = correct["isa"]["isa"]
    rows = []

    def add(label, value):
        if value is not None and value != "":
            rows.append({"label": label, "value": _js_number_text(value) if isinstance(value, float) else str(value)})

    def filled(value):
        return value if _js_true(value) else ""

    rows.append({"section": "Data Collection"})
    add("Detector", filled(inp.get("detector")))
    add("Wavelength (Å)", filled(inp.get("wavelength")))
    add("Detector distance (mm)", filled(inp.get("detector_distance")))
    add("Oscillation range (°)", filled(inp.get("oscillation_range")))
    add("No. of images", filled(inp.get("n_images")))
    add("Total rotation range (°)", filled(inp.get("total_rotation")))
    add("Space group", _sg_name(sg) if _js_true(sg) else "")
    add("Unit cell (a, b, c (Å); α, β, γ (°))", cell_text)
    rows.append({"section": "Data Processing"})
    add("Resolution range (Å)", pair(res_text, res_outer) if res_text else "")
    add("Completeness (%)", column("completeness"))
    add("Redundancy", pair(redundancy(total), redundancy(outer)) if total else "")
    add("R<sub>meas</sub> (%) &dagger;", column("r_meas"))
    # R-pim is exact, from the unmerged reflections, and only when it could be checked
    # against the R-meas of the log.  Never R-meas/sqrt(N).
    if total:
        if "rpim" not in d:
            add("R<sub>pim</sub> (%) &Dagger;", "calculating…")
        elif rpim and _js_true(rpim.get("overall")):
            add("R<sub>pim</sub> (%) &Dagger;", pair(rpim.get("overall"), rpim.get("outer") or ""))
    add("R<sub>merge</sub> (%) &sect;", column("r_obs"))
    add("⟨I/σ(I)⟩", column("i_sigma"))
    add("CC<sub>1/2</sub> (%) &Vert;", column("cc_half"))
    add("CC* (%) &Vert;", pair(cc_star(total), cc_star(outer)) if total else "")
    add("Total reflections", pair(total.get("observed"), outer.get("observed") if outer else "") if total else "")
    add("Unique reflections", pair(total.get("unique"), outer.get("unique") if outer else "") if total else "")
    if total and _js_true(total.get("anomal_corr")):
        add("CC(anom) (%)", column("anomal_corr"))
    if total and _js_true(total.get("siganom")):
        add("SigAno", pair(total.get("siganom"), outer.get("siganom") if outer else ""))
    if isa:
        add("ISa", isa)
    wilson = ""
    if isinstance(correct.get("wilson_line"), dict) and "b" in correct["wilson_line"]:
        wilson = js_fixed(correct["wilson_line"]["b"] or 0, 1)
    from_correct = ' <span style="font-size:0.75em; opacity:0.65;">(CORRECT.LP)</span>' if has_xscale else ""
    add("Wilson B (Å²)" + from_correct, wilson)
    if correct.get("mosaicity") is not None and correct.get("mosaicity") != "":
        add("Mosaicity (°)" + from_correct, js_fixed(correct["mosaicity"], 3))
    return rows
