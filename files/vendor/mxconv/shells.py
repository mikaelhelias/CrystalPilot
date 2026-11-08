"""Resolution shells for statistics tables.

Low-resolution shells of equal volume in reciprocal space (equal steps in 1/d^2),
then shells 0.1 A wide that reach the high-resolution limit.  The outer shell of
a Table 1 is then 0.1 A wide, wide enough to hold meaningful statistics and
narrow enough to describe the edge of the data.

Boundaries are the high-resolution limits of the shells, from low to high
resolution, the way XSCALE and CORRECT take RESOLUTION_SHELLS.
"""
import math

from .fmt import fixed

D_LOW = 80.0          # low-resolution end of the first shell (A)
FINE_WIDTH = 0.10     # width of the outer shells (A)


def _equal_volume(d_low, d_high, n):
    """The n-1 inner boundaries that cut d_low..d_high into n shells of equal volume."""
    inv_low = 1.0 / (d_low * d_low)
    inv_high = 1.0 / (d_high * d_high)
    return [math.sqrt(1.0 / (inv_low + i * (inv_high - inv_low) / n)) for i in range(1, n)]


def table(high, d_low=D_LOW, n_coarse=10, n_fine=5, width=FINE_WIDTH):
    """Boundaries for a merging-statistics table (15 shells by default).

    Ten shells of equal volume from d_low, then five shells `width` wide that
    reach `high`.  When the data reach no further than about 0.5 A past d_low,
    a single shell at `high` is returned.
    """
    fine_start = high + n_fine * width
    if fine_start >= d_low:
        return [high]
    bounds = _equal_volume(d_low, fine_start, n_coarse)
    for i in range(n_fine + 1):
        d = fine_start - i * width
        if d < high - 0.001:
            break
        bounds.append(d)
    return bounds


def table_xds(high, d_low=D_LOW, n_coarse=6, n_fine=3, width=FINE_WIDTH):
    """Boundaries for XDS CORRECT, which takes at most nine values: six shells of equal
    volume from d_low, then three shells `width` wide that reach `high`."""
    fine_start = high + n_fine * width
    bounds = _equal_volume(d_low, fine_start, n_coarse)
    bounds += [fine_start - i * width for i in range(n_fine)] + [high]
    return bounds[-9:]


def text(bounds, digits=2):
    """Boundaries as a RESOLUTION_SHELLS value: "7.37 5.22 ... 1.84"."""
    return " ".join(fixed(v, digits) for v in bounds)


def mid_points(highs, low_edge=0.0):
    """The middle of each shell in 1/d^2.

    A table prints the high-resolution limit of each shell, but a statistic is
    the mean over the whole shell, so it belongs to the middle of the shell.
    The first shell starts at `low_edge` (1/d^2; 0 means infinite d).
    """
    out = []
    for d in highs:
        high_edge = 1.0 / (d * d)
        out.append(0.5 * (low_edge + high_edge))
        low_edge = high_edge
    return out
