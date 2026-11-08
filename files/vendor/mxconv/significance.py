"""Is a correlation coefficient significant?  (Standard library only.)

CC1/2 of a shell is called significant when a Student t-test rejects "no
correlation" at the 0.1 % level (Karplus & Diederichs, 2012):
    t = CC sqrt((n - 2) / (1 - CC^2)),  n - 2 degrees of freedom,
where n is the number of reflections that took part in the correlation.
"""
import math

ALPHA = 0.001


def _betacf(a, b, x, max_iter=300, eps=3e-14):
    """Continued fraction for the incomplete beta function (modified Lentz)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def betainc(a, b, x):
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_front = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x)
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(ln_front) * _betacf(a, b, x) / a
    return 1.0 - math.exp(ln_front) * _betacf(b, a, 1.0 - x) / b


def p_value(cc, n):
    """One-sided p of a correlation cc from n pairs (probability of a value at least
    this large when there is no correlation).  None when n < 3."""
    if n is None or n < 3 or cc is None:
        return None
    if cc >= 1.0:
        return 0.0
    if cc <= -1.0:
        return 1.0
    df = n - 2
    t = cc * math.sqrt(df / (1.0 - cc * cc))
    tail = 0.5 * betainc(0.5 * df, 0.5, df / (df + t * t))
    return tail if t > 0 else 1.0 - tail


def significant(cc, n, alpha=ALPHA):
    """True when cc (a fraction, not percent) from n pairs is significant at `alpha`."""
    p = p_value(cc, n)
    return p is not None and p < alpha
