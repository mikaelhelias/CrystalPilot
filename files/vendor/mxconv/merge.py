"""Merging statistics from unmerged observations (numpy; gemmi for symmetry).

Definitions (sums over unique reflections h measured at least twice, and over
their n_h observations I_hi with mean <I_h>):
    R-merge = sum_h sum_i |I_hi - <I_h>|                      / sum_h sum_i I_hi
    R-meas  = sum_h sqrt(n_h / (n_h - 1)) sum_i |I_hi - <I_h>| / sum_h sum_i I_hi
    R-pim   = sum_h sqrt(1 / (n_h - 1))   sum_i |I_hi - <I_h>| / sum_h sum_i I_hi
<I_h> is the unweighted mean (as XDS and AIMLESS use in R factors).  R-pim is
computed this way, exactly; it is never R-meas / sqrt(multiplicity).

CC1/2 (default "random_w"): the observations of each reflection are split at
random into two halves (Karplus & Diederichs, 2012), each half averaged with
inverse-variance weights, and the half means correlated over the reflections
present in both halves.  This reproduces XDS and AIMLESS.  The split uses a fixed
seed, so a result is reproducible.  Other methods: "random" (unweighted half
means), "sigma_tau" (Assmann et al., 2016: (var(<I_h>) - m) / (var(<I_h>) + m),
m = mean of s_h^2 / n_h), "sigma_tau_w", "sigma_tau_sd".  n_cc, the number of
reflections correlated, gives the significance test (`significance`).

<I/sigma(I)> is the mean over unique reflections of the inverse-variance weighted
mean intensity over its sigma, sigma(<I_h>) = 1 / sqrt(sum_i 1/sigma_hi^2).

Completeness counts unique reflections against those possible in the shell
(systematic absences excluded; Friedel mates counted separately for anomalous
statistics, except centric ones).
"""
import numpy as np

from . import shells as _shells
from .significance import significant


def _group(keys):
    """Unique ids per observation, and the number of unique reflections."""
    uniq, inverse = np.unique(keys, return_inverse=True)
    return inverse, len(uniq)


def _possible(data, d_min, d_max, anomalous):
    """d of every possible unique reflection between d_min and d_max."""
    import gemmi
    cell = gemmi.UnitCell(*data.cell)
    hkl = np.asarray(gemmi.make_miller_array(cell, data.space_group, d_min * 0.999, d_max * 1.001, True))
    ops = data.space_group.operations()
    absent = np.asarray(ops.systematic_absences(hkl.astype(np.int32)), dtype=bool)
    hkl = hkl[~absent]
    from .unmerged import frac_matrix
    s = hkl.astype(np.float64) @ frac_matrix(cell)
    inv_d2 = np.einsum("ij,ij->i", s, s)
    inside = (inv_d2 <= 1.0 / d_min ** 2 * (1 + 1e-9)) & (inv_d2 >= 1.0 / d_max ** 2 * (1 - 1e-9))
    hkl, inv_d2 = hkl[inside], inv_d2[inside]
    weight = np.ones(len(hkl))
    if anomalous:
        centric = np.asarray(ops.centric_flag_array(hkl.astype(np.int32)), dtype=bool)
        weight = np.where(centric, 1.0, 2.0)
    return inv_d2, weight


def _cc_half_sigma_tau(mean, var_mean_err):
    """sigma-tau CC1/2 from per-reflection means and s^2/n; (cc, n)."""
    n = len(mean)
    if n < 3:
        return None, n
    var_y = np.var(mean, ddof=1)
    m = float(np.mean(var_mean_err))
    if var_y + m <= 0:
        return None, n
    return float((var_y - m) / (var_y + m)), n


def _cc_half_random(group, values, rng):
    """Random-half CC1/2 over reflections with observations in both halves; (cc, n)."""
    if len(group) < 4:
        return None, 0
    order = np.lexsort((rng.random_sample(len(group)), group))
    g, v = group[order], values[order]
    first = np.concatenate(([True], g[1:] != g[:-1]))
    start = np.flatnonzero(first)
    gid = np.cumsum(first) - 1
    half = (np.arange(len(g)) - start[gid]) % 2
    n_groups = int(gid[-1]) + 1
    n1 = np.bincount(gid[half == 0], minlength=n_groups)
    n2 = np.bincount(gid[half == 1], minlength=n_groups)
    s1 = np.bincount(gid[half == 0], weights=v[half == 0], minlength=n_groups)
    s2 = np.bincount(gid[half == 1], weights=v[half == 1], minlength=n_groups)
    both = (n1 > 0) & (n2 > 0)
    n = int(np.sum(both))
    if n < 3:
        return None, n
    m1, m2 = s1[both] / n1[both], s2[both] / n2[both]
    if np.std(m1) == 0 or np.std(m2) == 0:
        return None, n
    return float(np.corrcoef(m1, m2)[0, 1]), n


def _cc_half_random_weighted(group, values, weights, rng):
    """Random-half CC1/2 with inverse-variance weighted half means; (cc, n)."""
    if len(group) < 4:
        return None, 0
    order = np.lexsort((rng.random_sample(len(group)), group))
    g, v, w = group[order], values[order], weights[order]
    first = np.concatenate(([True], g[1:] != g[:-1]))
    start = np.flatnonzero(first)
    gid = np.cumsum(first) - 1
    half = (np.arange(len(g)) - start[gid]) % 2
    n_groups = int(gid[-1]) + 1
    sw1 = np.bincount(gid[half == 0], weights=w[half == 0], minlength=n_groups)
    sw2 = np.bincount(gid[half == 1], weights=w[half == 1], minlength=n_groups)
    s1 = np.bincount(gid[half == 0], weights=(w * v)[half == 0], minlength=n_groups)
    s2 = np.bincount(gid[half == 1], weights=(w * v)[half == 1], minlength=n_groups)
    both = (sw1 > 0) & (sw2 > 0)
    n = int(np.sum(both))
    if n < 3:
        return None, n
    m1, m2 = s1[both] / sw1[both], s2[both] / sw2[both]
    return float(np.corrcoef(m1, m2)[0, 1]), n


def _shell_stats(i, sigma, group, n_unique_all, cc_method, rng, r_mean="unweighted"):
    """Statistics of one set of observations; group = unique id per observation."""
    out = {"n_obs": int(len(i))}
    if len(i) == 0:
        out.update({"n_unique": 0, "multiplicity": None, "i_mean": None, "i_sigma": None, "r_merge": None,
                    "r_meas": None, "r_pim": None, "cc_half": None, "n_cc": 0})
        return out
    uniq, gid = np.unique(group, return_inverse=True)
    nu = len(uniq)
    n = np.bincount(gid, minlength=nu).astype(np.float64)
    s_i = np.bincount(gid, weights=i, minlength=nu)
    mean = s_i / n
    w = 1.0 / (sigma * sigma)
    s_w = np.bincount(gid, weights=w, minlength=nu)
    s_wi = np.bincount(gid, weights=w * i, minlength=nu)
    mean_w = s_wi / s_w
    sig_w = 1.0 / np.sqrt(s_w)
    dev = np.abs(i - (mean_w if r_mean == "weighted" else mean)[gid])
    s_dev = np.bincount(gid, weights=dev, minlength=nu)
    multi = n >= 2
    denom = float(np.sum(s_i[multi]))
    out["n_unique"] = int(nu)
    out["multiplicity"] = float(len(i)) / nu
    out["i_mean"] = float(np.mean(mean_w))
    out["i_sigma"] = float(np.mean(mean_w / sig_w))
    if denom > 0 and np.any(multi):
        nm = n[multi]
        out["r_merge"] = float(np.sum(s_dev[multi]) / denom)
        out["r_meas"] = float(np.sum(np.sqrt(nm / (nm - 1.0)) * s_dev[multi]) / denom)
        out["r_pim"] = float(np.sum(np.sqrt(1.0 / (nm - 1.0)) * s_dev[multi]) / denom)
    else:
        out["r_merge"] = out["r_meas"] = out["r_pim"] = None
    if cc_method == "random":
        cc, n_cc = _cc_half_random(gid, i, rng)
    elif cc_method == "random_w":
        cc, n_cc = _cc_half_random_weighted(gid, i, w, rng)
    elif cc_method == "sigma_tau_w":
        cc, n_cc = _cc_half_sigma_tau(mean_w[multi], (1.0 / s_w)[multi])
    elif cc_method == "sigma_tau_sd":
        s_sig2 = np.bincount(gid, weights=sigma * sigma, minlength=nu)
        cc, n_cc = _cc_half_sigma_tau(mean[multi], (s_sig2 / (n * n))[multi])
    else:
        sq = np.bincount(gid, weights=(i - mean[gid]) ** 2, minlength=nu)
        var_obs = np.where(multi, sq / np.maximum(n - 1.0, 1.0), 0.0)
        cc, n_cc = _cc_half_sigma_tau(mean[multi], (var_obs / n)[multi])
    out["cc_half"] = cc
    out["n_cc"] = int(n_cc)
    out["cc_half_significant"] = significant(cc, n_cc) if cc is not None else False
    return out


def statistics(data, bounds=None, d_low=None, anomalous=False, cc_method="random_w", seed=0, d_min=None,
               r_mean="unweighted"):
    """Merging statistics per shell and overall.

    data: an `unmerged.Unmerged`.
    bounds: high-resolution limits of the shells, low to high resolution (A);
            default `shells.table(d_min)`, the 0.1 A outer-shell convention.
    d_low: low-resolution limit (default: the lowest-resolution observation).
    d_min: high-resolution limit (default: the highest-resolution observation, or bounds[-1]).
    anomalous: Friedel mates kept apart.
    Returns {"shells": [...], "overall": {...}}; each shell has d_low, d_high, n_obs,
    n_unique, n_possible, completeness (%), multiplicity, i_mean, i_sigma, r_merge,
    r_meas, r_pim (fractions), cc_half (fraction), n_cc, cc_half_significant.
    """
    rng = np.random.RandomState(seed)
    d_all = data.d()
    if d_min is None:
        d_min = float(bounds[-1]) if bounds else float(d_all.min())
    if bounds is None:
        bounds = _shells.table(d_min)
    if d_low is None:
        d_low = float(d_all.max())
    sel = (d_all >= d_min * (1 - 1e-6)) & (d_all <= d_low * (1 + 1e-6))
    keys = data.unique_keys(anomalous)[sel]
    i, sigma, d = data.i[sel], data.sigma[sel], d_all[sel]
    # a reflection exactly on a shell limit belongs to the lower-resolution shell, also
    # when rounding puts it a hair beyond (symmetry equivalents differ in the last bit)
    inv_edges = [1.0 / (b * b) * (1 + 1e-9) for b in bounds]
    shell_of = np.searchsorted(np.array(inv_edges), 1.0 / (d * d), side="left")
    shell_of = np.minimum(shell_of, len(bounds) - 1)
    # possible reflections up to the data's own limit, not past it
    poss_inv, poss_w = _possible(data, max(d_min, float(d.min())) if len(d) else d_min, d_low, anomalous)
    poss_shell = np.minimum(np.searchsorted(np.array(inv_edges), poss_inv, side="left"), len(bounds) - 1)
    result = []
    lows = [d_low] + list(bounds[:-1])
    for k, (lo, hi) in enumerate(zip(lows, bounds)):
        m = shell_of == k
        st = _shell_stats(i[m], sigma[m], keys[m], None, cc_method, rng, r_mean)
        possible = float(np.sum(poss_w[poss_shell == k]))
        st.update({"d_low": float(lo), "d_high": float(hi), "n_possible": int(possible),
                   "completeness": 100.0 * st["n_unique"] / possible if possible else None})
        result.append(st)
    overall = _shell_stats(i, sigma, keys, None, cc_method, rng, r_mean)
    possible = float(np.sum(poss_w))
    overall.update({"d_low": float(d_low), "d_high": float(bounds[-1]), "n_possible": int(possible),
                    "completeness": 100.0 * overall["n_unique"] / possible if possible else None})
    return {"shells": result, "overall": overall, "anomalous": anomalous, "cc_method": cc_method,
            "n_rejected": data.n_rejected, "source": data.source}


def by_counts(data, counts, anomalous=None, cc_method="random_w", seed=0, min_i_sigma=None):
    """Statistics in the shells of a program's log, given as observation counts.

    Observations are sorted from low to high resolution and cut at the counts of
    the log's own table, so no shell limit is guessed from a value printed to 0.01 A
    (the method of CrystalPilot's exact R-pim).  Returns one dict per shell, and
    the overall one, as `statistics` does (without completeness).
    """
    if anomalous is None:                      # as the program merged: FRIEDEL'S_LAW=FALSE keeps mates apart
        anomalous = not data.friedel
    if min_i_sigma is not None:                # XDS tables count only observations with I/sigma >= -3
        data = data.subset(data.i / data.sigma >= min_i_sigma)
    d = data.d()
    order = np.argsort(-d, kind="stable")
    keys = data.unique_keys(anomalous)
    rng = np.random.RandomState(seed)
    out, start = [], 0
    total = int(sum(counts))
    for c in counts:
        idx = order[start:start + c]
        out.append(_shell_stats(data.i[idx], data.sigma[idx], keys[idx], None, cc_method, rng))
        start += c
    idx = order[:total]
    overall = _shell_stats(data.i[idx], data.sigma[idx], keys[idx], None, cc_method, rng)
    return {"shells": out, "overall": overall}


def checked_rpim(data, log_shells, log_overall_r_meas, anomalous=None, tolerance=(0.2, 0.01)):
    """Exact R-pim (percent, overall and outer shell) for a Table 1 whose other numbers
    come from a program's log, withheld unless R-meas computed from the same
    observations agrees with the log (absolute tolerance in percent, or relative).

    log_shells: [{"n_obs": int, "r_meas": percent}, ...] low to high resolution.
    Returns {"overall": text|None, "outer": text|None, "reason": text}.
    """
    from .fmt import fixed
    counts = [int(s["n_obs"]) for s in log_shells]
    n_file, n_log = len(data), sum(counts)
    out = {"overall": None, "outer": None, "reason": ""}
    if n_file < n_log or (n_file - n_log) > 0.01 * max(n_log, 1):
        out["reason"] = "the file holds %d observations, the log counts %d: not the same run" % (n_file, n_log)
        return out
    got = by_counts(data, counts, anomalous, min_i_sigma=-3.0 if data.source == "XDS_ASCII" else None)
    reasons = []
    for key, mine, logged, what in (("overall", got["overall"], log_overall_r_meas, "overall"),
                                    ("outer", got["shells"][-1], log_shells[-1].get("r_meas"), "outer shell")):
        if logged is None or mine["r_meas"] is None:
            reasons.append(what + ": no R-meas to check against")
            continue
        r_meas = 100.0 * mine["r_meas"]
        if abs(r_meas - logged) > max(tolerance[0], tolerance[1] * abs(logged)):
            reasons.append("%s: R-meas %.1f %% here, %.1f %% in the log" % (what, r_meas, logged))
            continue
        out[key] = fixed(100.0 * mine["r_pim"], 1)
    out["reason"] = "; ".join(reasons)
    return out
