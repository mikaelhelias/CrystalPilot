# Independent scaling with AIMLESS and CTRUNCATE

**Goal:** a second opinion on the scaling, CCP4-style statistics and output files, and amplitudes with twinning tests. Requires CCP4; the tab is shown from the **Advanced** work mode.

AIMLESS (Evans & Murshudov 2013) scales and merges the XDS integration independently of XSCALE. Comparing the two is a good check, and some downstream pipelines expect AIMLESS output.

## Run

1. Open the **AIMLESS** tab. The card shows the CCP4 status, the current CORRECT and XSCALE statistics for reference, and whether a POINTLESS-sorted MTZ already exists.
2. Options: resolution limits (empty = as integrated), **anomalous** on or off, number of bins, and which steps to run: POINTLESS (sorting and reindexing, needed the first time), AIMLESS, CTRUNCATE.
3. Click **▶ Run Pipeline**. POINTLESS → AIMLESS → CTRUNCATE run in turn with a live log; everything is written next to the XDS output (`aimless.log`, `ctruncate.log`, `aimless_scaled.mtz`, `aimless_unmerged.mtz`, `aimless_truncate.mtz`) and reloaded when you return.

![The AIMLESS tab with the reference statistics, the options and the Run Pipeline button.](images/13-01-aimless.png)

## Read the result

![AIMLESS results: key metrics compared with XDS, shell statistics, per-batch scale and B-factor charts, CTRUNCATE summary, output files.](images/13-02-aimless-results.png)

- **Compare key metrics**: R-merge/R-obs, I/σ, CC½, completeness, multiplicity for AIMLESS against CORRECT and XSCALE. Differences of a few tenths of a percent in R-meas are normal; large differences point to different resolution limits or outlier handling.
- **Resolution shell statistics**: R-merge, R-full, R-cum, R-meas, R-pim, I/σ, CC½, completeness, multiplicity, anomalous completeness and multiplicity per shell; the same table as the AIMLESS log.
- **Scale and B-factor per batch**: a smooth curve is healthy; a steep B-factor rise is radiation damage (see ΔCC½, chapter 10).
- **CTRUNCATE**: Wilson B, the cumulative intensity distribution and the twinning tests (L-test, H-test). A positive twin test changes your refinement strategy.
- **Output files** with their paths; **View log** shows the raw logs.

## If it goes wrong

| Symptom | What to do |
|---|---|
| "CCP4 not found" | same as for POINTLESS (chapter 9) |
| AIMLESS stops with a reindexing error | run POINTLESS first (tick it), or set the space group in XDS.INP and re-run CORRECT |
| CTRUNCATE refuses (negative or zero intensities) | normal for very weak outer shells: lower the resolution limit in the options |
| Statistics differ strongly from XSCALE | check that both used the same resolution limit and Friedel setting; anomalous on in AIMLESS pairs with FRIEDEL'S_LAW= FALSE |
