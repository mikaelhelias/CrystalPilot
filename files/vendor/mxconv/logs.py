"""Statistics tables read from processing logs (standard library only).

Every reader returns the same shape:
    {"program": name, "shells": [row, ...], "overall": row}
with rows holding numbers (percent for completeness, R factors and CC1/2):
    d_low, d_high, n_obs, n_unique, n_possible, completeness, multiplicity,
    i_sigma, r_merge, r_meas, r_pim, cc_half, cc_half_significant, cc_anom
(None where the program does not print the value).

Readers: XDS CORRECT.LP / XSCALE.LP, AIMLESS log, and the cctbx table that DIALS
(dials.scale, dials.merge), xia2 and xia2.merging_statistics print.
`as_cutoff_shells` turns any of them into the shells `cutoff.determine` takes.
"""
import re


def _num(text):
    if text is None:
        return None
    text = str(text).strip().rstrip("%*").strip()
    try:
        return float(text)
    except ValueError:
        return None


# ── XDS ──────────────────────────────────────────────────────────────────────
_XDS_TITLE = "SUBSET OF INTENSITY DATA WITH SIGNAL/NOISE >= -3.0 AS FUNCTION OF RESOLUTION"


def read_xds(text):
    """The last resolution table of CORRECT.LP or XSCALE.LP (all data, S/N >= -3)."""
    lines = text.splitlines()
    starts = [k for k, line in enumerate(lines) if _XDS_TITLE in line]
    if not starts:
        return None
    shells, overall, d_low = [], None, None
    for line in lines[starts[-1] + 1:]:
        parts = line.split()
        if not parts:
            if shells:
                break
            continue
        if parts[0] in ("RESOLUTION", "LIMIT"):
            continue
        if len(parts) < 10:
            if shells:
                break
            continue
        row = {"n_obs": _num(parts[1]), "n_unique": _num(parts[2]), "n_possible": _num(parts[3]),
               "completeness": _num(parts[4]), "r_merge": _num(parts[5]), "i_sigma": _num(parts[8]),
               "r_meas": _num(parts[9]), "cc_half": _num(parts[10]) if len(parts) > 10 else None,
               "cc_half_significant": len(parts) > 10 and parts[10].endswith("*"),
               "cc_anom": _num(parts[11]) if len(parts) > 11 else None, "r_pim": None}
        if row["n_obs"] and row["n_unique"]:
            row["multiplicity"] = row["n_obs"] / row["n_unique"]
        if parts[0].lower() == "total":
            row.update({"d_low": None, "d_high": shells[-1]["d_high"] if shells else None})
            overall = row
            break
        row["d_high"] = _num(parts[0])
        row["d_low"] = d_low
        d_low = row["d_high"]
        shells.append(row)
    return {"program": "XDS", "shells": shells, "overall": overall}


# ── AIMLESS ──────────────────────────────────────────────────────────────────
def _loggraph_tables(text):
    """CCP4 loggraph tables: {title: (column names, rows of text values)}."""
    out = {}
    for m in re.finditer(r"\$TABLE\s*:\s*(.*?):\s*\n(.*?)\$\$(.*?)\$\$(.*?)\$\$(.*?)\$\$", text, re.S):
        title, columns, body = m.group(1).strip(), m.group(3).split(), m.group(5)
        rows = [line.split() for line in body.strip().splitlines() if line.strip()]
        out[title] = (columns, rows)
    return out


def _table(tables, prefix):
    title = next((t for t in reversed(list(tables)) if t.startswith(prefix)), None)
    if title is None:
        return {}
    columns, rows = tables[title]
    by_n = {}
    for row in rows:
        by_n[row[0]] = {c: _num(v) for c, v in zip(columns, row)}
    return by_n


def read_aimless(text):
    """Shells from AIMLESS's tables against resolution (R factors and I/sd, CC1/2 with the
    number of pairs, completeness) and the overall column of its summary.

    AIMLESS bins are equal steps in 1/d^2 starting at 0; each row prints the bin
    middle, so the high-resolution limit is 1/sqrt(middle + half a step)."""
    tables = _loggraph_tables(text)
    title = next((t for t in reversed(list(tables)) if t.startswith("Analysis against resolution, ")
                  and not t.startswith("Analysis against resolution, with")), None)
    res = _table({title: tables[title]}, title) if title else {}
    if not res:
        return None
    cc = _table(tables, "Correlations CC(1/2) within dataset")
    comp = _table(tables, "Completeness & multiplicity v. resolution")
    keys = sorted(res, key=lambda n: int(n))
    mids = [res[n]["1/d^2"] for n in keys]
    overall = _aimless_summary(text) or {}
    # middles are (k - 1/2) * step, printed to 4 decimals: least-squares step
    weights = [k + 0.5 for k in range(len(mids))]
    step = sum(w * m for w, m in zip(weights, mids)) / sum(w * w for w in weights)

    def pct(v):
        return None if v is None else 100.0 * v

    shells, d_low = [], None
    for k, n in enumerate(keys):
        r, c, p = res[n], cc.get(n, {}), comp.get(n, {})
        d_high = 1.0 / ((k + 1) * step) ** 0.5
        row = {"d_low": d_low, "d_high": d_high, "n_obs": p.get("Nmeas", r.get("Nmeas")), "n_unique": p.get("Nref"),
               "n_possible": None, "completeness": p.get("%poss"), "multiplicity": p.get("Mlplct"),
               "i_sigma": r.get("Mn(I/sd)"), "r_merge": pct(r.get("Rmrg")), "r_meas": pct(r.get("Rmeas")),
               "r_pim": pct(r.get("Rpim")), "cc_half": pct(c.get("CC1/2")), "n_cc": c.get("NCC1/2"),
               "cc_half_significant": None, "cc_anom": pct(c.get("CCanom"))}
        d_low = d_high
        shells.append(row)
    return {"program": "AIMLESS", "shells": shells, "overall": overall or None}


_AIMLESS_SUMMARY = {
    "Low resolution limit": "d_low", "High resolution limit": "d_high", "Rmerge  (all I+ and I-)": "r_merge",
    "Rmeas (all I+ & I-)": "r_meas", "Rpim (all I+ & I-)": "r_pim", "Total number of observations": "n_obs",
    "Total number unique": "n_unique", "Mean((I)/sd(I))": "i_sigma", "Mn(I) half-set correlation CC(1/2)": "cc_half",
    "Completeness": "completeness", "Multiplicity": "multiplicity", "Anomalous completeness": None,
}


def _aimless_summary(text):
    """Overall values: the first of the three columns (Overall, InnerShell, OuterShell)."""
    start = text.rfind("Summary data for")
    if start < 0:
        return None
    out = {}
    for line in text[start:start + 6000].splitlines():
        for label, key in _AIMLESS_SUMMARY.items():
            if key and line.strip().startswith(label):
                values = line[line.find(label) + len(label):].split()
                v = _num(values[0]) if values else None
                if v is not None and key in ("r_merge", "r_meas", "r_pim", "cc_half"):
                    v *= 100.0
                out[key] = v
    return out or None


# ── DIALS / xia2 / cctbx ─────────────────────────────────────────────────────
_CCTBX_COLUMNS = {"d_max": "d_low", "d_min": "d_high", "#obs": "n_obs", "#uniq": "n_unique",
                  "mult.": "multiplicity", "%comp": "completeness", "<I/sI>": "i_sigma", "r_mrg": "r_merge",
                  "r_meas": "r_meas", "r_pim": "r_pim", "cc1/2": "cc_half", "cc_ano": "cc_anom"}


def read_merging_statistics(text):
    """The cctbx (iotbx) table "d_max  d_min  #obs  #uniq ... cc1/2 cc_ano" printed by
    dials.scale, dials.merge, xia2 and xia2.merging_statistics; the last one in the
    text.  Its last row (spanning all bins) is the overall one.  A '*' after cc1/2
    marks significance at the 0.1 % level where the program tests it."""
    lines = text.splitlines()
    starts = [k for k, line in enumerate(lines) if line.split()[:2] == ["d_max", "d_min"] and "cc1/2" in line]
    if not starts:
        return None
    names = lines[starts[-1]].split()
    rows = []
    for line in lines[starts[-1] + 1:]:
        parts = line.split()
        if len(parts) != len(names) or _num(parts[0]) is None:
            break
        row = {"cc_half_significant": None}
        for name, value in zip(names, parts):
            key = _CCTBX_COLUMNS.get(name)
            if key:
                row[key] = _num(value)
            if name == "cc1/2" and value.endswith("*"):
                row["cc_half_significant"] = True
        for key in ("r_merge", "r_meas", "r_pim", "cc_half", "cc_anom"):
            if row.get(key) is not None:
                row[key] *= 100.0
        rows.append(row)
    overall = None
    if len(rows) > 1 and rows[-1]["d_low"] >= rows[0]["d_low"] - 0.02 and rows[-1]["d_high"] <= rows[-2]["d_high"]:
        overall = rows.pop()
    return {"program": "cctbx", "shells": rows, "overall": overall}


def as_cutoff_shells(table):
    """Shells for `cutoff.determine` from any reader's result."""
    out = []
    for k, row in enumerate(table["shells"]):
        out.append({"idx": k, "d": row["d_high"], "i_sigma": row.get("i_sigma"), "cc_half": row.get("cc_half"),
                    "r_obs": row.get("r_merge"), "cc_half_significant": bool(row.get("cc_half_significant"))})
    return out
