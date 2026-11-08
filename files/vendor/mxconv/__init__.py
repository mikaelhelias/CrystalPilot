"""mxconv: conventions for macromolecular X-ray data statistics.

One definition of the statistics shells, the resolution cut-off, the delta-CC1/2
frame rejection and the rows of Table 1, independent of the program that
processed the data.  The modules imported here need only the Python standard
library; `unmerged`, `merge` and `anisotropy` (statistics from unmerged data)
need numpy and gemmi and are imported explicitly.
"""

__version__ = "0.2.0.dev0"

from . import fmt, shells, cutoff, stats, dcc, table1, cite, significance, logs  # noqa: F401
