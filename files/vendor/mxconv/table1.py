"""Rows of Table 1 (data collection and processing).

Every statistic reads "overall (outer shell)".  R-pim is exact, computed from the
unmerged observations; it is never estimated as R-meas / sqrt(multiplicity), and
when it cannot be computed the row is left out.  CC* is derived from CC1/2.

`rows` takes program-independent values; `rows_from_xds` builds them from parsed
XDS (CORRECT) and XSCALE results.  Each row is {"section": name} or
{"label": text, "value": text}; labels may hold HTML markup (<sub>, &dagger;).
"""
import re

from .fmt import fixed, is_set, number, plain
from .stats import cc_star_text

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

# Decimals for statistics given as numbers (text values are shown as given).
DIGITS = {"completeness": 1, "r_meas": 1, "r_merge": 1, "i_sigma": 1, "cc_half": 1, "cc_anom": 1, "sig_anom": 3}

RPIM_PENDING = "pending"


def space_group_text(sg_number):
    """"P 2₁ 2₁ 2₁ (#19)" for a space-group number; "#n" when it has no symbol here."""
    value = number(sg_number)
    n = int(value) if value is not None else None
    return SG_SYMBOLS[n] + " (#" + str(n) + ")" if n in SG_SYMBOLS else "#" + ("NaN" if n is None else str(n))


def cell_text(cell):
    """"a, b, c  α, β, γ" with 2 and 1 decimals, from a dict a, b, c, alpha, beta, gamma."""
    return (", ".join(fixed(cell[k], 2) for k in ("a", "b", "c")) + "  "
            + ", ".join(fixed(cell[k], 1) for k in ("alpha", "beta", "gamma")))


def _clean(value, key=None, as_text=False):
    if value is None:
        return ""
    if not as_text and isinstance(value, float) and key in DIGITS:
        return fixed(value, DIGITS[key])
    return re.sub(r"[%*]", "", str(value)).strip()


def _pair(value, value_outer=None):
    if not value and value != 0:
        return ""
    text = str(value)
    if value_outer is not None and value_outer != "":
        text += " (" + str(value_outer) + ")"
    return text


def _multiplicity(row):
    if not row:
        return ""
    observed, unique = number(row.get("n_observed")), number(row.get("n_unique"))
    return fixed(observed / unique, 1) if unique and unique > 0 and observed is not None else ""


def _cc_star(row):
    if not row or not is_set(row.get("cc_half")):
        return ""
    value = number(str(row.get("cc_half")).replace("*", ""))
    if value is None:
        return ""
    return cc_star_text(value)


def rows(collection=None, overall=None, outer=None, resolution=("", ""), rpim=None,
         isa="", wilson_b="", mosaicity=None, derived_note="", as_text=False):
    """Table 1 rows.

    collection: {"detector", "wavelength", "detector_distance", "oscillation_range",
                 "n_images", "total_rotation", "space_group" (display text), "unit_cell" (text)}
    overall, outer: statistics of all data and of the outer shell, keys
        completeness, r_meas, r_merge, i_sigma, cc_half (percent), n_observed, n_unique,
        cc_anom, sig_anom; text (shown without % and *) or numbers (DIGITS decimals).
        Without `overall` no processing statistics are shown.
    resolution: (range text, outer-shell range text), e.g. ("48.2–1.84", "1.94–1.84").
    rpim: (overall, outer) exact R-pim in percent, RPIM_PENDING while it is computed,
          or None (row left out).
    derived_note: markup added to the Wilson B and mosaicity labels (their source).
    as_text: show every statistic as the program printed it, numbers included.
    """
    collection = collection or {}
    out = []

    def add(label, value):
        if value is not None and value != "":
            out.append({"label": label, "value": plain(value) if isinstance(value, float) else str(value)})

    def filled(value):
        return value if is_set(value) else ""

    def column(key):
        return (_pair(_clean(overall.get(key), key, as_text), _clean(outer.get(key), key, as_text) if outer else "")
                if overall else "")

    out.append({"section": "Data Collection"})
    add("Detector", filled(collection.get("detector")))
    add("Wavelength (Å)", filled(collection.get("wavelength")))
    add("Detector distance (mm)", filled(collection.get("detector_distance")))
    add("Oscillation range (°)", filled(collection.get("oscillation_range")))
    add("No. of images", filled(collection.get("n_images")))
    add("Total rotation range (°)", filled(collection.get("total_rotation")))
    add("Space group", collection.get("space_group") or "")
    add("Unit cell (a, b, c (Å); α, β, γ (°))", collection.get("unit_cell") or "")
    out.append({"section": "Data Processing"})
    res_text, res_outer = resolution or ("", "")
    add("Resolution range (Å)", _pair(res_text, res_outer) if res_text else "")
    add("Completeness (%)", column("completeness"))
    add("Redundancy", _pair(_multiplicity(overall), _multiplicity(outer)) if overall else "")
    add("R<sub>meas</sub> (%) &dagger;", column("r_meas"))
    if overall:
        if rpim == RPIM_PENDING:
            add("R<sub>pim</sub> (%) &Dagger;", "calculating…")
        elif rpim:
            add("R<sub>pim</sub> (%) &Dagger;", _pair(rpim[0], rpim[1] or ""))
    add("R<sub>merge</sub> (%) &sect;", column("r_merge"))
    add("⟨I/σ(I)⟩", column("i_sigma"))
    add("CC<sub>1/2</sub> (%) &Vert;", column("cc_half"))
    add("CC* (%) &Vert;", _pair(_cc_star(overall), _cc_star(outer)) if overall else "")
    add("Total reflections", _pair(overall.get("n_observed"), outer.get("n_observed") if outer else "") if overall else "")
    add("Unique reflections", _pair(overall.get("n_unique"), outer.get("n_unique") if outer else "") if overall else "")
    if overall and is_set(overall.get("cc_anom")):
        add("CC(anom) (%)", column("cc_anom"))
    if overall and is_set(overall.get("sig_anom")):
        add("SigAno", _pair(overall.get("sig_anom"), outer.get("sig_anom") if outer else ""))
    if isa:
        add("ISa", isa)
    add("Wilson B (Å²)" + derived_note, wilson_b)
    if mosaicity is not None and mosaicity != "":
        add("Mosaicity (°)" + derived_note, mosaicity)
    return out


# ── XDS / XSCALE ─────────────────────────────────────────────────────────────
_XDS_KEYS = {"completeness": "completeness", "r_meas": "r_meas", "r_merge": "r_obs", "i_sigma": "i_sigma",
             "cc_half": "cc_half", "n_observed": "observed", "n_unique": "unique", "cc_anom": "anomal_corr",
             "sig_anom": "siganom"}
XDS_DERIVED_NOTE = ' <span style="font-size:0.75em; opacity:0.65;">(CORRECT.LP)</span>'


def _is_total(row):
    return str(row.get("resolution") or "").lower() == "total"


def _has_resolution(row):
    return is_set(row.get("resolution"))


def _xds_row(row):
    return None if row is None else {k: row.get(v) for k, v in _XDS_KEYS.items()}


def rows_from_xds(d):
    """Table 1 rows from parsed XDS results.

    d: {"xdsinp": collection values from XDS.INP, "xscale": parsed XSCALE.LP,
        "correct": parsed CORRECT.LP, "rpim": exact R-pim result (absent while it is
        computed)}.  XSCALE statistics are used when present, otherwise CORRECT's;
    Wilson B and mosaicity always come from CORRECT.
    """
    inp = d.get("xdsinp") or {}
    xscale = d.get("xscale") or {}
    correct = d.get("correct") or {}
    has_xscale = bool(xscale.get("statistics_table"))
    has_correct = bool(correct.get("statistics_table"))
    stats = xscale["statistics_table"] if has_xscale else (correct["statistics_table"] if has_correct else [])
    total, outer = None, None
    if stats:
        total = next((row for row in reversed(stats) if _has_resolution(row) and _is_total(row)), None) or stats[-1]
        for row in stats:
            if _has_resolution(row) and not _is_total(row):
                outer = row
    sg = xscale.get("space_group") if is_set(xscale.get("space_group")) else (
        correct.get("space_group") if is_set(correct.get("space_group")) else inp.get("space_group"))
    cell = xscale.get("unit_cell") if is_set(xscale.get("unit_cell")) else (
        correct.get("unit_cell") if is_set(correct.get("unit_cell")) else None)
    cell_value = cell_text(cell) if isinstance(cell, dict) else (inp.get("unit_cell") or "")
    primary = xscale if has_xscale else (correct if has_correct else {})
    shells = [row for row in stats if _has_resolution(row) and not _is_total(row)]
    rpim = d.get("rpim")
    res_text, res_outer = "", ""
    if outer:
        low = number(primary.get("resolution_range_low"))
        if low is None and rpim and is_set(rpim.get("d_low")):
            low = number(rpim.get("d_low"))
        if low is None and d.get("correct") is not None:
            low = number(correct.get("resolution_range_low"))
        low_text = "" if low is None else fixed(low, 2)
        res_text = (low_text + "–" if low_text else "") + str(outer["resolution"])
        before = shells[-2]["resolution"] if len(shells) > 1 else low_text
        res_outer = (str(before) + "–" if before else "") + str(outer["resolution"])
    if "rpim" not in d:
        rpim_value = RPIM_PENDING
    elif rpim and is_set(rpim.get("overall")):
        rpim_value = (rpim.get("overall"), rpim.get("outer") or "")
    else:
        rpim_value = None
    isa = ""
    if xscale.get("isa_table"):
        isa = ", ".join(str(r.get("isa")) for r in xscale["isa_table"])
    elif isinstance(correct.get("isa"), dict) and is_set(correct["isa"].get("isa")):
        isa = correct["isa"]["isa"]
    wilson = ""
    if isinstance(correct.get("wilson_line"), dict) and "b" in correct["wilson_line"]:
        wilson = fixed(correct["wilson_line"]["b"] or 0, 1)
    mosaicity = None
    if correct.get("mosaicity") is not None and correct.get("mosaicity") != "":
        mosaicity = fixed(correct["mosaicity"], 3)
    collection = {k: inp.get(k) for k in ("detector", "wavelength", "detector_distance", "oscillation_range",
                                         "n_images", "total_rotation")}
    collection["space_group"] = space_group_text(sg) if is_set(sg) else ""
    collection["unit_cell"] = cell_value
    return rows(collection, _xds_row(total), _xds_row(outer), (res_text, res_outer), rpim_value,
                isa, wilson, mosaicity, XDS_DERIVED_NOTE if has_xscale else "", as_text=True)
