"""Statistics and resolution limits along directions in reciprocal space.

Observations whose scattering vector lies within a cone (half-angle 30 degrees by
default) around a direction are binned by resolution, and CC1/2 and <I/sigma(I)>
are computed per bin; the cut-off criteria of `cutoff` then give a resolution
limit along that direction.  The default directions are the reciprocal axes a*,
b*, c* (for non-orthogonal cells these are not perpendicular).

Each observation is taken at the index it was measured with, so symmetry
equivalents of one reflection count in the directions they lie in.
"""
import math

import numpy as np

from . import cutoff as _cutoff
from .merge import _shell_stats


def reciprocal_axes(cell):
    """Unit vectors along a*, b*, c* (Cartesian, the frame of `Unmerged.reciprocal_vectors`)."""
    from .unmerged import frac_matrix
    frac = frac_matrix(cell)
    axes = {}
    for name, row in zip(("a*", "b*", "c*"), np.eye(3)):
        v = row @ frac
        axes[name] = v / np.linalg.norm(v)
    return axes


def wilson_b(shells, d_max=None, min_i_sigma=None):
    """Wilson B (A^2) from shells: least-squares slope of ln<I> against s^2/4 = 1/(4 d^2),
    ln<I> = A - 2 B s^2/4, over all shells with a positive mean intensity, as XDS's Wilson
    line "using all data" (reproduces XDS's B within about 1 A^2 on real data).  Optional
    restrictions: shells beyond d_max only, shells with <I/sigma> >= min_i_sigma only (all
    qualifying shells when fewer than three remain).  None when fewer than three shells qualify."""
    points = []
    for sh in shells:
        if not sh.get("n_obs") or sh.get("i_mean") is None or sh["i_mean"] <= 0:
            continue
        if min_i_sigma is not None and sh.get("i_sigma") is not None and sh["i_sigma"] < min_i_sigma:
            continue
        mid = 0.5 * (1.0 / sh["d_low"] ** 2 + 1.0 / sh["d_high"] ** 2)
        points.append((mid / 4.0, math.log(sh["i_mean"]), 1.0 / math.sqrt(mid)))
    beyond = [p for p in points if d_max is None or p[2] < d_max]
    use = beyond if len(beyond) >= 3 else points
    if len(use) < 3:
        return None
    x = np.array([p[0] for p in use])
    y = np.array([p[1] for p in use])
    slope = np.polyfit(x, y, 1)[0]
    return float(-slope / 2.0)


WILSON_BINS = 20          # shells equal in 1/d^2 for the Wilson fit, finer than the statistics shells


def _wilson_shells(i, sigma, keys, d, d_low, d_min, n_bins=WILSON_BINS):
    """Shells equal in 1/d^2 with the merged mean intensity and <I/sigma>, for `wilson_b`."""
    lo, hi = 1.0 / d_low ** 2, 1.0 / d_min ** 2
    edges = [lo + (hi - lo) * k / n_bins for k in range(n_bins + 1)]
    which = np.minimum(np.searchsorted(np.array(edges[1:]), 1.0 / (d * d), side="left"), n_bins - 1)
    out = []
    for k in range(n_bins):
        m = which == k
        st = _shell_stats(i[m], sigma[m], keys[m], None, "sigma_tau", None)
        st.update({"d_low": 1.0 / math.sqrt(edges[k]) if edges[k] > 0 else d_low, "d_high": 1.0 / math.sqrt(edges[k + 1])})
        out.append(st)
    return out


def along(data, directions=None, half_angle=30.0, n_bins=10, d_min=None, d_low=None, seed=0):
    """Per-direction shells, cut-offs and Wilson B, and the same for all observations.

    directions: {name: vector} in the Cartesian reciprocal frame (default a*, b*, c*).
    Returns {"half_angle": deg, "n_obs": int, "directions": {name: entry}, "isotropic": entry},
    entry = {"n_obs": int, "shells": [...], "cutoffs": result of cutoff.determine,
    "wilson_b": A^2 or None}.  Statistics shells are equal steps in d*^3 between d_low
    and d_min (defaults: the data's range); the Wilson fit uses 20 finer shells equal in
    1/d^2 over the same range.
    """
    s = data.reciprocal_vectors()
    norm = np.sqrt(np.einsum("ij,ij->i", s, s))
    d = 1.0 / np.where(norm > 0, norm, np.inf)
    d_min = float(d[norm > 0].min()) if d_min is None else d_min
    d_low = float(d[norm > 0].max()) if d_low is None else d_low
    keys = data.unique_keys(False)
    cos_limit = math.cos(math.radians(half_angle))
    directions = directions or reciprocal_axes(data.cell)
    # bin edges equal in d*^3 (equal reciprocal volume)
    lo3, hi3 = (1.0 / d_low) ** 3, (1.0 / d_min) ** 3
    edges = [((lo3 + (hi3 - lo3) * k / n_bins) ** (1.0 / 3.0)) for k in range(1, n_bins + 1)]
    bounds = [1.0 / e for e in edges]
    in_range = (norm > 0) & (d >= d_min * (1 - 1e-6)) & (d <= d_low * (1 + 1e-6))
    out = {"half_angle": half_angle, "n_obs": int(np.sum(in_range)), "directions": {}}
    rng = np.random.RandomState(seed)
    masks = []
    for name, vec in directions.items():
        u = np.asarray(vec, dtype=np.float64)
        u = u / np.linalg.norm(u)
        cos = np.abs(s @ u) / np.where(norm > 0, norm, 1.0)
        masks.append((name, (cos >= cos_limit) & in_range))
    masks.append((None, in_range))
    for name, inside in masks:
        dd = d[inside]
        bins = np.minimum(np.searchsorted(np.array(edges), 1.0 / dd, side="left"), n_bins - 1)
        shells, lows = [], [d_low] + bounds[:-1]
        for k in range(n_bins):
            m = bins == k
            idx = np.flatnonzero(inside)[m]
            st = _shell_stats(data.i[idx], data.sigma[idx], keys[idx], None, "random_w", rng)
            st.update({"d_low": lows[k], "d_high": bounds[k]})
            shells.append(st)
        cut_rows = [{"idx": k, "d": sh["d_high"], "i_sigma": sh["i_sigma"],
                     "cc_half": None if sh["cc_half"] is None else 100.0 * sh["cc_half"],
                     "r_obs": None if sh["r_merge"] is None else 100.0 * sh["r_merge"],
                     "cc_half_significant": bool(sh.get("cc_half_significant"))}
                    for k, sh in enumerate(shells) if sh["n_obs"]]
        sel = np.flatnonzero(inside)
        fine = _wilson_shells(data.i[sel], data.sigma[sel], keys[sel], d[sel], d_low, d_min)
        entry = {"n_obs": int(np.sum(inside)), "shells": shells,
                 "cutoffs": _cutoff.determine(cut_rows, "cc_half_30"), "wilson_b": wilson_b(fine)}
        if name is None:
            out["isotropic"] = entry
        else:
            out["directions"][name] = entry
    return out
