"""Derived statistics."""
import math

from .fmt import fixed


def cc_star(cc_half_fraction):
    """CC* = sqrt(2 CC1/2 / (1 + CC1/2)) (Karplus & Diederichs, 2012), CC1/2 as a fraction.
    0 for CC1/2 <= 0; CC1/2 above 1 is taken as 1."""
    if cc_half_fraction <= 0:
        return 0.0
    f = min(cc_half_fraction, 1)
    return math.sqrt(2.0 * f / (1.0 + f))


def cc_star_text(cc_half_percent):
    """CC* in percent with one decimal, from CC1/2 in percent ("" when CC1/2 is missing)."""
    if cc_half_percent is None:
        return ""
    fraction = cc_half_percent / 100.0
    if fraction <= 0:
        return "0.0"
    return fixed(cc_star(fraction) * 100, 1)


def multiplicity(n_observed, n_unique):
    """Observations per unique reflection, or None."""
    if n_observed is None or not n_unique or n_unique <= 0:
        return None
    return n_observed / n_unique
