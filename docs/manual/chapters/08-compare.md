# Comparing runs

**Goal:** see what a change did (space group, resolution limit, excluded frames, re-integration) without reading two logs side by side.

Every time CORRECT, IDXREF or XSCALE runs again, the previous log is kept next to the new one as `.prev1` (then `.prev2` … `.prev4`). Two features use them.

## Run History

1. Open the CORRECT (or IDXREF, or XSCALE) metrics and click **Run History**.
2. A table compares the last runs: cell, space group, ISa, R-meas, CC½, I/σ, completeness, resolution limits (for IDXREF: indexed fraction, lattice, quality of fit). Changed values are flagged, and a note explains resolution differences that make R-factors incomparable.

![Run History of CORRECT: the last runs side by side with the changes flagged.](images/08-01-history.png)

## Compare with another log

**Δ Compare with Previous** puts the current run next to the last one (`.prev1`). **Δ Compare with File…** compares it with a log you upload from anywhere: a previous processing, a beamline pipeline (autoPROC, xia2, EDNA all write CORRECT.LP), a colleague's run. Choose the file; the same table appears with the two runs.

![Compare with Previous, Compare with File…, Run History and the CSV export above the CORRECT metrics.](images/08-02-compare-buttons.png)

## Export

**⤓ Export CORRECT Data (.csv)** downloads the parsed statistics (shell table, Wilson data, moments, alien reflections); **⤓ Export INTEGRATE Data (.csv)** the per-frame data, for a spreadsheet or a plot of your own.

## Where the old logs are

In the folder of the run (chapter 4): `CORRECT.LP.prev1` is the run before the current one. Sub-folder mode (chapter 7) keeps complete runs apart instead of rotating logs; use it when you want to keep the reflection files of several strategies.
