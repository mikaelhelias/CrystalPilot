"""Reading and printing numbers.

`fixed` rounds an exact tie away from zero (2.5 -> 3, 0.125 -> 0.13), so a value
printed in a table keeps the digit a reader computing by hand expects.
`number` reads the number a text starts with ("12.3%" -> 12.3, "99.9*" -> 99.9).
"""
import re
from decimal import Decimal, ROUND_HALF_UP

_NUMBER_PREFIX = re.compile(r"\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)")


def number(value):
    """The number a value starts with; None when there is none (also for True/False and NaN)."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value == value else None
    match = _NUMBER_PREFIX.match(str(value))
    return float(match.group(1)) if match else None


def fixed(value, digits):
    """A number with a fixed count of decimals; an exact tie rounds away from zero."""
    value = float(value) or 0.0            # -0.0 prints as 0.0; -0.04 stays -0.0 at one decimal
    step = Decimal(1).scaleb(-digits) if digits else Decimal(1)
    return format(Decimal(value).quantize(step, rounding=ROUND_HALF_UP), "f")


def plain(value):
    """A number as text without a trailing .0: 18.0 is "18", 0.1 stays "0.1"."""
    if isinstance(value, float) and value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return str(value)


def is_set(value):
    """True for a value that holds something: not None/False, not empty text, not 0, not NaN."""
    if value is None or value is False or value == "" or value == 0:
        return False
    return value == value
