"""Resolution cut-off from a table of merging statistics.

One definition for every criterion: a statistic is attached to the middle of
its shell in 1/d^2 (not to the shell's printed high-resolution limit, which
makes every cut-off about half a shell too optimistic), and the cut-off is the
point where it crosses its threshold, interpolated linearly in 1/d^2 between the
two shells around it.

Criteria
    cc_half_30   CC1/2 falls to 30 %; the default, the threshold AIMLESS and DIALS/xia2 use
                 (Evans & Murshudov, 2013)
    isig2        <I/sigma(I)> falls to 2.0
    cc_half_50   CC1/2 falls to 50 %
    r_obs_55     R-merge (R-obs) rises to 55 %
    cc_half_sig  the last shell whose CC1/2 is significant at the 0.1 % level
                 (Karplus & Diederichs, 2012), as marked by the program: the upper
                 bound to test by paired refinement.  Without significance marks it
                 falls back on isig2.

Shell rows (`Shell` dicts) hold numbers, not text:
    {"d": high-resolution limit (A), "i_sigma": float|None, "cc_half": percent|None,
     "cc_half_significant": bool, "r_obs": percent|None}
`from_xds_table` turns the rows of an XDS CORRECT/XSCALE table into them.
"""
from .shells import mid_points

CRITERIA = {          # key: (field, threshold, crossing upwards)
    "isig2": ("i_sigma", 2.0, False),
    "cc_half_50": ("cc_half", 50.0, False),
    "r_obs_55": ("r_obs", 55.0, True),
    "cc_half_30": ("cc_half", 30.0, False),
}

# Short names used by interfaces, with their labels, and the default.
MODES = {"isig": ("isig2", "I/σ ≈ 2.0"), "robs": ("r_obs_55", "R-obs ≈ 55%"),
         "cc50": ("cc_half_50", "CC½ ≈ 50%"), "cc30": ("cc_half_30", "CC½ ≈ 30%"),
         "cc12": ("cc_half_sig", "CC½ significant")}
DEFAULT_MODE = "cc30"
# When the chosen criterion is not reached, the first one reached in this order is used.
FALLBACK_ORDER = ("cc30", "isig", "robs", "cc50", "cc12")


def _float(text, strip=""):
    try:
        text = str(text)
        for ch in strip:
            text = text.replace(ch, "")
        return float(text)
    except (ValueError, TypeError):
        return None


def from_xds_table(statistics_table):
    """Shell dicts from the rows of an XDS statistics table (text values as printed;
    the "total" row and rows without a resolution are skipped).  Each keeps `idx`,
    its position in the original table."""
    out = []
    for i, row in enumerate(statistics_table or []):
        res = row.get("resolution", "")
        if not res or str(res).lower() == "total":
            continue
        d = _float(res)
        if d is None:
            continue
        cc_text = row.get("cc_half", "")
        out.append({"idx": i, "d": d,
                    "i_sigma": _float(row.get("i_sigma", "")),
                    "cc_half": _float(cc_text, "*%"),
                    "r_obs": _float(row.get("r_obs", ""), "%"),
                    "cc_half_significant": "*" in str(cc_text)})
    return out


def _crossing(shells, field, threshold, upwards):
    """(d, reached) for one criterion.  reached is False when every shell passes."""
    for k in range(1, len(shells)):
        v0, v1 = shells[k - 1][field], shells[k][field]
        if v0 is None or v1 is None:
            continue
        crossed = (v0 <= threshold < v1) if upwards else (v0 >= threshold > v1)
        if crossed:
            frac = (threshold - v0) / (v1 - v0)
            inv = shells[k - 1]["_inv_d2"] + frac * (shells[k]["_inv_d2"] - shells[k - 1]["_inv_d2"])
            if inv > 0:
                return (1.0 / inv) ** 0.5, True
    # No clean crossing.  If the last shell fails (values not monotonic), cut at
    # the last shell that still passes; if every shell fails, at the first.
    last = shells[-1][field]
    if len(shells) >= 2 and last is not None:
        fails = last > threshold if upwards else last < threshold
        if fails:
            for s in reversed(shells):
                v = s[field]
                if v is None:
                    continue
                if (v <= threshold) if upwards else (v >= threshold):
                    return s["d"], True
            return shells[0]["d"], True
    # Every shell passes: all the data can be kept.
    return (shells[-1]["d"] if last is not None else None), False


def determine(shells, criterion="isig2"):
    """Cut-offs for all criteria from Shell dicts (low to high resolution).

    Returns {"resolution": d of `criterion`, "criterion", "shell_index": idx of the
    shell nearest to it, "all_cutoffs": {criterion: d}, "reached": {criterion: bool}}.
    `reached` is False when the data never cross the threshold (the cut-off is
    then the edge of the data).  When no shell carries a significance mark,
    cc_half_sig falls back on isig2.
    """
    result = {"resolution": None, "criterion": criterion, "shell_index": None, "all_cutoffs": {}}
    shells = [dict(s) for s in shells or []]
    if not shells:
        return result
    for s, mid in zip(shells, mid_points([s["d"] for s in shells])):
        s["_inv_d2"] = mid
    reached = {}
    for key in ("isig2", "cc_half_50", "r_obs_55", "cc_half_30"):
        field, threshold, upwards = CRITERIA[key]
        value, reached[key] = _crossing(shells, field, threshold, upwards)
        result["all_cutoffs"][key] = round(value, 2) if value is not None else None
    starred = [s for s in shells if s.get("cc_half_significant")]
    if starred:
        result["all_cutoffs"]["cc_half_sig"] = starred[-1]["d"]
        reached["cc_half_sig"] = starred[-1] is not shells[-1]
    else:
        result["all_cutoffs"]["cc_half_sig"] = result["all_cutoffs"]["isig2"]
        reached["cc_half_sig"] = reached["isig2"]
    result["reached"] = reached
    chosen = result["all_cutoffs"].get(criterion)
    result["resolution"] = chosen
    if chosen is not None:
        nearest = min(shells, key=lambda s: abs(s["d"] - chosen))
        result["shell_index"] = nearest.get("idx", shells.index(nearest))
    return result


def determine_xds(statistics_table, criterion="isig2"):
    """`determine` on the rows of an XDS CORRECT/XSCALE statistics table."""
    return determine(from_xds_table(statistics_table), criterion)


def choose(cutoffs, mode=None, order=FALLBACK_ORDER):
    """The cut-off an interface applies, from the result of `determine`.

    `mode` is one of MODES (default DEFAULT_MODE).  A criterion counts only when
    the data reached it (CC1/2 significance always counts).  When the chosen one
    was not reached, the first reached in `order` is used.
    Returns (d or None, mode used or None, fallback: bool).
    """
    cutoffs = cutoffs or {}
    found = cutoffs.get("all_cutoffs") or {}
    reached = cutoffs.get("reached") or {}
    values = {"isig": found.get("isig2") if reached.get("isig2") else None,
              "robs": found.get("r_obs_55") if reached.get("r_obs_55") else None,
              "cc50": found.get("cc_half_50") if reached.get("cc_half_50") else None,
              "cc30": found.get("cc_half_30") if reached.get("cc_half_30") else None,
              "cc12": found.get("cc_half_sig")}
    mode = mode if mode in MODES else DEFAULT_MODE
    chosen = values.get(mode)
    if chosen is not None:
        return chosen, mode, False
    name = next((k for k in order if values.get(k) is not None), None)
    return (values[name] if name else None), name, True
