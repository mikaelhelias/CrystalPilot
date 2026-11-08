
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
#  The statistics conventions (shells, cut-off, frame rejection, Table 1, number
#  printing) come from mxconv, embedded by build.py as _mx; the names below are
#  the ones the rest of CrystalPilot calls.
js_float = _mx.fmt.number          # '12.3%' and '99.9*' give 12.3 and 99.9; None when there is none
js_fixed = _mx.fmt.fixed           # fixed decimals, an exact tie rounds away from zero
_js_number_text = _mx.fmt.plain    # 18.0 is "18", 0.1 stays "0.1"
_js_true = _mx.fmt.is_set          # not empty text, not 0, not missing


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
#  mxconv.dcc: suggestions for review (capped at `limit`, 20 % by default) and what
#  AutoPilot excludes unreviewed (mean ΔCC½ < 0, at most 10 %, worst part of a range
#  over the limit).
AUTOPILOT_DCC_LIMIT = _mx.dcc.AUTO_LIMIT
AUTOPILOT_DCC_MIN_PART = _mx.dcc.AUTO_MIN_PART       # fewest batches worth excluding from a range over the limit
_DCC_REASONS = _mx.dcc.REASON_LABELS
_worst_part = _mx.dcc.worst_part


def frame_suggestions(data, strategies=None, limit=0.20):
    """Bad frame ranges for EXCLUDE_DATA_RANGE, from parsed XDSCC12 results (mxconv.dcc.suggest)."""
    return _mx.dcc.suggest(data, strategies, limit)


def autopilot_frame_choice(data, oscillation):
    """What AutoPilot excludes from XDSCC12 results in its one pass (mxconv.dcc.automatic)."""
    return _mx.dcc.automatic(data, oscillation)


# ── what AutoPilot acts on, for the page ─────────────────────────────────────
_AUTOPILOT_COVERED_BY = {"insufficient_indexed_moderate": "indexing rate", "insufficient_indexed_severe": "indexing rate", "very_few_indexed": "indexing rate",
                         "low_indexed_fraction": "indexing rate", "half_integer_indices": "half-integer", "low_isa": "isa"}


def with_autopilot_findings(advice, findings):
    """The page's advice, and what AutoPilot acts on where the advice does not already say it."""
    merged = list(advice)
    for finding in findings:
        covered = _AUTOPILOT_COVERED_BY.get(finding["error"])
        if covered and any(covered in item["title"].lower() for item in advice):
            continue
        said, _, action = finding["message"].partition(" — ")
        rings = (finding.get("fix") or {}).get("_exclude_resolution_ranges") or []
        where = " Rings: " + ", ".join(str(r["label"]) for r in rings) + " Å." if rings else ""
        merged.append({"severity": {"fatal": "warning", "warning": "caution"}.get(finding["severity"], "info"), "title": said,
                       "body": ("AutoPilot responds by " + action if action.split(" ")[0].endswith("ing") else action[:1].upper() + action[1:]) + "." + where})
    return merged


def step_advice(step, metrics, lp_text):
    """What a log suggests, in the words the page shows."""
    if step == "IDXREF":
        return with_autopilot_findings(idxref_diagnostics(metrics, lp_text), LPParser.diagnose_idxref(lp_text))
    return with_autopilot_findings(page_diagnostics(step, metrics), LPParser.diagnose_correct(lp_text, metrics.get("statistics_table")))


# ── XSCALE autofill ──────────────────────────────────────────────────────────
def xscale_shells(high):
    """RESOLUTION_SHELLS for a high-resolution limit: ten shells of equal volume in 1/d²
    from 80 Å, then five 0.1 Å shells that visibly reach the cut-off."""
    return _mx.shells.text(_mx.shells.table(high))


def xds_shells(high):
    """RESOLUTION_SHELLS for CORRECT, which takes at most 9 values: six shells of equal
    volume in 1/d² from 80 Å, then three 0.1 Å shells that reach the cut-off."""
    return _mx.shells.text(_mx.shells.table_xds(high))


XSCALE_CUTOFF_MODES = {"isig": ("isig2", "I/σ ≈ 2.0"), "robs": ("r_obs_55", "R-obs ≈ 55%"),
                       "cc50": ("cc_half_50", "CC½ ≈ 50%"), "cc12": ("cc_half_sig", "CC½ significant")}
XSCALE_CUTOFF_DEFAULT = "cc50"
XSCALE_CUTOFF_ORDER = ("isig", "robs", "cc50", "cc12")      # the next one found when the chosen one is not reached


def xscale_autofill(metrics, mode=None):
    """XSCALE.INP values from a parsed CORRECT.LP: the space group, the cell, and a
    resolution from the chosen cut-off (or the next one found: I/σ, R-obs, CC½ 50%, CC½ significant)."""
    out = {"space_group": metrics.get("space_group"), "unit_cell": None, "resolution_low": None,
           "resolution_high": None, "shells": None, "cutoff": None, "fallback": False}
    cell = metrics.get("unit_cell")
    if cell:
        out["unit_cell"] = " ".join(js_fixed(cell[k], 2) for k in ("a", "b", "c", "alpha", "beta", "gamma"))
    mode = mode if mode in XSCALE_CUTOFF_MODES else XSCALE_CUTOFF_DEFAULT
    chosen, name, out["fallback"] = _mx.cutoff.choose(metrics.get("cutoffs") or {}, mode, order=XSCALE_CUTOFF_ORDER)
    if chosen is not None:
        high = float(js_fixed(chosen, 2))
        out.update({"resolution_low": "999", "resolution_high": js_fixed(high, 2), "shells": xscale_shells(high),
                    "cutoff": name, "cutoff_label": XSCALE_CUTOFF_MODES[name][1] + " → " + js_fixed(chosen, 2) + " Å" + (" (fallback)" if out["fallback"] else "")})
    return out


# ── Table 1 ──────────────────────────────────────────────────────────────────
SG_SYMBOLS = _mx.table1.SG_SYMBOLS
_sg_name = _mx.table1.space_group_text


def table1_rows(d):
    """The rows of Table 1 from /table1data's results: [{section}, {label, value}, ...].
    Each value reads overall (outer shell); R-pim only when exact (mxconv.table1)."""
    return _mx.table1.rows_from_xds(d)


# ── methods text ─────────────────────────────────────────────────────────────
_ENANTIOMORPHS = {76, 78, 91, 95, 92, 96, 144, 145, 151, 153, 152, 154, 169, 170, 171, 172, 178, 179, 180, 181, 212, 213}
METHOD_REFERENCES = {key: _mx.cite.REFERENCES[key] for key in ("xds", "xscale", "xdscc12", "pointless", "aimless")}


def _ranges_text(pairs):
    """1 5 and 7 7 read as 1-5 and 7."""
    parts = [a if a == b else a + "-" + b for a, b in pairs]
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def _active_ranges(text, key):
    found = []
    for line in str(text).splitlines():
        if line.lstrip().startswith("!"):
            continue
        pairs, _ = XDSINPEditor._split_pairs(line)
        found += [v.split()[:2] for k, v in pairs if k.upper() == key and len(v.split()) >= 2]
    return found


def methods_text(facts):
    """A methods paragraph that states only what the facts show; what is unknown is left out."""
    inp = facts.get("inp_text") or ""
    values = xdsinp_values(inp)
    used, sentences = ["xds"], []
    first = "Diffraction images were processed with XDS"
    if facts.get("xds_version"):
        first += " (version " + facts["xds_version"] + ")"
    first += " (Kabsch, 2010a), run through CrystalPilot " + VERSION + "."
    sentences.append(first)
    bits = []
    data_range = (values.get("DATA_RANGE") or "").split()
    oscillation = (values.get("OSCILLATION_RANGE") or "").split()
    if oscillation:
        bits.append("with " + oscillation[0] + "° oscillation")
    wavelength = (values.get("X-RAY_WAVELENGTH") or "").split()
    if wavelength:
        bits.append("at a wavelength of " + wavelength[0] + " Å")
    detector = (values.get("DETECTOR") or "").split()
    distance = (values.get("DETECTOR_DISTANCE") or "").split()
    if detector:
        article = "an " if detector[0][0].upper() in "AEIOU" else "a "
        bits.append("on " + article + detector[0] + " detector" + (" at " + distance[0] + " mm" if distance else ""))
    if len(data_range) >= 2:
        sentences.append("Images " + data_range[0] + "-" + data_range[1] + " were used" + (", collected " + " ".join(bits) if bits else "") + ".")
    elif bits:
        sentences.append("The images were collected " + " ".join(bits) + ".")
    summary = facts.get("autopilot") or {}
    optimization = summary.get("optimization") or {}
    if optimization.get("kept") is True:
        sentences.append("Integration was repeated with the geometry refined by CORRECT.")
    elif optimization.get("kept") is False:
        sentences.append("A second integration with the geometry refined by CORRECT was tried and not kept.")
    excluded = _active_ranges(inp, "EXCLUDE_DATA_RANGE")
    if excluded:
        one_frame = len(excluded) == 1 and excluded[0][0] == excluded[0][1]
        sentence = ("Frame " if one_frame else "Frames ") + _ranges_text(excluded) + (" was excluded" if one_frame else " were excluded")
        dcc = summary.get("dcc_half") or {}
        if dcc.get("n_excluded"):
            sentence += " on the basis of ΔCC½ (XDSCC12; Assmann et al., 2020)"
            used.append("xdscc12")
        sentences.append(sentence + ".")
    rings = _active_ranges(inp, "EXCLUDE_RESOLUTION_RANGE")
    if rings:
        sentences.append(("The resolution ranges " if len(rings) > 1 else "The resolution range ") + _ranges_text(rings) + " Å " + ("were" if len(rings) > 1 else "was") + " excluded.")
    correct = facts.get("correct") or {}
    xscale = facts.get("xscale") or {}
    number = js_float(correct.get("space_group"))
    cell = correct.get("unit_cell")
    if number:
        sentence = "The data were indexed and integrated in space group " + _sg_name(number).replace(" (#", " (no. ")
        if isinstance(cell, dict):
            sentence += ", with a = " + js_fixed(cell["a"], 2) + ", b = " + js_fixed(cell["b"], 2) + ", c = " + js_fixed(cell["c"], 2) + " Å, α = " \
                        + js_fixed(cell["alpha"], 1) + ", β = " + js_fixed(cell["beta"], 1) + ", γ = " + js_fixed(cell["gamma"], 1) + "°"
        sentences.append(sentence + ".")
        if summary.get("sg_note"):
            sentences.append("The space group was assigned from the reflections along the principal axes.")
        if int(number) in _ENANTIOMORPHS:
            sentences.append("Systematic absences do not distinguish this space group from its enantiomorph.")
    if xscale.get("statistics_table"):
        sentences.append("The data were scaled with XSCALE (Kabsch, 2010b).")
        used.append("xscale")
    elif correct.get("statistics_table"):
        sentences.append("The data were scaled by the CORRECT step of XDS.")
    criterion = {"isig2": "⟨I/σ(I)⟩ of about 2", "cc_half_50": "CC½ of about 50%", "cc_half_sig": "the last shell of significant CC½",
                 "r_obs_55": "R-obs of about 55%"}.get(summary.get("criterion"))
    if criterion and summary.get("status") in ("success", "completed", "done"):
        sentences.append("The high-resolution limit was set at " + criterion + ".")
    table = {"xdsinp": {}, "correct": correct, "xscale": xscale, "rpim": None}
    rows = {r.get("label"): r.get("value") for r in table1_rows(table) if "label" in r}
    stats = [("resolution", "Resolution range (Å)", " Å"), ("completeness", "Completeness (%)", "%"), ("redundancy", "Redundancy", ""),
             ("R-meas", "R<sub>meas</sub> (%) &dagger;", "%"), ("⟨I/σ(I)⟩", "⟨I/σ(I)⟩", ""), ("CC½", "CC<sub>1/2</sub> (%) &Vert;", "%")]
    parts = [name + " " + rows[label] + unit for name, label, unit in stats if rows.get(label)]
    if parts:
        sentences.append("Overall statistics, with the outer shell in parentheses: " + ", ".join(parts) + ".")
    if facts.get("pointless_ran"):
        sentences.append("POINTLESS (Evans, 2006) was also run.")
        used.append("pointless")
    if facts.get("aimless_ran"):
        sentences.append("AIMLESS (Evans & Murshudov, 2013) was also run.")
        used.append("aimless")
    if facts.get("xdsconv_ran"):
        sentences.append("Reflections were converted with XDSCONV.")
    clients = sorted({c for c in facts.get("agent_clients") or [] if c})
    if facts.get("agent_acted"):
        who = " (" + ", ".join(clients) + ")" if clients else ""
        sentences.append("Processing was carried out by an AI agent" + who + " through CrystalPilot's agent interface; each of its actions is recorded in the project.")
    text, references = " ".join(sentences), [METHOD_REFERENCES[k] for k in used]
    if "xscale" in used:        # two papers of one year, told apart by a letter
        references = [r.replace("(2010).", "(2010a).") if k == "xds" else r.replace("(2010).", "(2010b).") if k == "xscale" else r
                      for k, r in zip(used, references)]
    else:
        text = text.replace("(Kabsch, 2010a)", "(Kabsch, 2010)")
    return {"text": text, "references": references, "programs": used}


def project_methods(project):
    """The methods paragraph of a project, from its own files, with what a reader should check."""
    folder = _pdir(project)
    facts, warnings = {}, []
    inp_path = _pfile(folder, "XDS.INP")
    if not inp_path.is_file():
        inp_path = folder / "XDS.INP"
    lp = _find_latest_lp(folder, "CORRECT")
    if lp:
        text = _read_text_lenient(lp)
        facts["correct"] = LPParser.parse_correct(text)
        found = re.search(r"VERSION\s+(.*?)\s+BUILT", text[:400])
        if found:
            facts["xds_version"] = found.group(1).strip()
    else:
        warnings.append("CORRECT has not run, so there are no statistics.")
    if inp_path.is_file():
        facts["inp_text"] = _read_text_lenient(inp_path)
        if lp and inp_path.stat().st_mtime > Path(lp).stat().st_mtime + 1:
            warnings.append("XDS.INP changed after the last CORRECT run, so what it says may not be what ran.")
    candidates = [_pfile(folder, "XSCALE.LP", "xscale")] + [c / "XSCALE.LP" for c in folder.iterdir() if c.is_dir() and c.name.startswith("XSCALE_")]
    candidates = [c for c in candidates if c.is_file()]
    if candidates:
        facts["xscale"] = LPParser.parse_xscale(_read_text_lenient(max(candidates, key=lambda c: c.stat().st_mtime)))
    cached = load_autopilot_cached_results(str(folder))
    if cached.get("has_results"):
        facts["autopilot"] = cached
    facts["pointless_ran"] = _pfile(folder, "pointless.log").is_file()
    facts["aimless_ran"] = _pfile(folder, "aimless.log").is_file()
    facts["xdsconv_ran"] = _pfile(folder, "XDSCONV.LP", "xdsconv").is_file()
    entries = agent_log_entries(project, 100000)
    facts["agent_acted"] = bool(entries)
    facts["agent_clients"] = [e.get("client") for e in entries if e.get("client") != "the page"]
    out = methods_text(facts)
    if not facts.get("autopilot") and not entries:
        warnings.append("XDS.INP shows what is set now, not any earlier steps done by hand.")
    out.update({"project": project, "warnings": warnings,
                "note": "Written from the project's files. Check it against your notes before using it."})
    return out
