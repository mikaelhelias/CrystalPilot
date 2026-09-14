# Indexing: XYCORR, INIT, COLSPOT, IDXREF

**Goal:** find the crystal lattice and a first orientation. This is the first half of the pipeline and the place where most problems show up, so it is run and checked on its own.

## Run to IDXREF

1. With `XDS.INP` saved (chapter 5), look at the pipeline track at the top of the Data Processing tab: eight steps, grey when pending.
2. Click **▶ to IDXREF**. XYCORR, INIT, COLSPOT and IDXREF run one after the other; the track turns orange for the running step and green when done.

![The run buttons above the pipeline track; "to IDXREF" is the first thing to click.](images/06-01-run-buttons.png)

3. Watch the **Live Log**: it is the program's own output, line by line. **⏹ Stop** ends the run together with the helper processes xds_par starts.

![The live log during a run, with the Stop button.](images/06-02-live-log.png)

Before each run the project's `XDS.INP` is copied into the run folder (chapter 7), so what you see in the editor is what runs. A step is marked failed (red) when its log contains `!!! ERROR !!!` or when no log was written.

## Read the IDXREF result

1. Click the green **IDXREF** step in the track (or open the **LP Viewer** sub-tab and choose IDXREF): the log opens, and **Key Metrics** shows the parsed result.

![IDXREF metrics: indexed fraction, refined beam centre and distance, deviations, and the lattice table.](images/06-03-idxref-metrics.png)

What to look for:

| Value | Good | Suspect |
|---|---|---|
| Indexed spots | above 70–80 % of the spots | below 50 %: wrong beam centre, distance or oscillation, or more than one lattice |
| Standard deviation of spot position | ≤ 1.5 px | > 3 px: check geometry |
| Standard deviation of spindle position | ≤ 1.5 × oscillation | large: oscillation range or rotation axis wrong |
| Refined beam centre and distance | close to the header values | jumps of several pixels or mm: header values wrong |

2. The **lattice table** lists the 44 Bravais lattice characters with their quality of fit and cell. The line XDS selected is marked. The correct choice is the highest symmetry whose quality of fit is still small (typically below 10–20); a low-symmetry lattice with the same cell is always a safe fallback.

![The Bravais lattice table with quality of fit and cells; the selected lattice is highlighted.](images/06-04-idxref-lattices.png)

3. To use a lattice for integration: in **Key Parameters** click **⟲ Cell & space group from IDXREF**, pick a row, and the cell and a space group of that lattice are filled in (set the toggles to *Active* and save). CORRECT decides the final space group later; you may also keep the space group commented and let XDS run in P1.

![The lattice picker opened from the parameter form.](images/06-05-cell-picker.png)

## When indexing fails: Auto-Index

The **Auto-Indexing** card sits under the IDXREF metrics (open the LP Viewer, choose IDXREF). It tries combinations for you: several SPOT_RANGE wedges, SIGNAL_PIXEL values and indexing tolerances, starting from your `XDS.INP`, each trial in its own folder so nothing of the project is disturbed.

![The Auto-Indexing card under the IDXREF metrics with the Quick, Medium and Full tiers and the SG/Cell lock.](images/06-06-autoindex.png)

1. Click **Quick** (a few trials, one or two minutes), **Medium** (several wedges), or **Full** (Expert: a systematic search including a bisection of the signal threshold). The **🔒 SG/Cell** lock keeps the cell and space group of `XDS.INP` during the trials instead of letting each trial index freely (🔓 = free indexing).
2. Each trial reports spots found, indexed fraction, chosen lattice and cell. Select a trial: **Apply to XDS.INP** writes its SIGNAL_PIXEL, SPOT_RANGE and any special parameters (INDEX_ERROR, MIN_PIXELS, INDEX_ORIGIN); **Apply & Re-run IDXREF** does that and runs COLSPOT + IDXREF at once. **⤓ CSV** exports the table, **📋 Report** opens the text report.
3. If you only applied, run **▶ to IDXREF** again.

## If it goes wrong

| Message or symptom | Meaning and fix |
|---|---|
| `INSUFFICIENT PERCENTAGE OF INDEXED REFLECTIONS` | beam centre, distance, wavelength or oscillation wrong; too thin a spot range; ice or a second lattice. Try the detector centre as ORGX/ORGY, widen SPOT_RANGE, look at the frames (chapter 17), run Auto-Index |
| Very few spots in COLSPOT | SIGNAL_PIXEL too high or wrong TRUSTED_REGION / untrusted areas; check STRONG_PIXEL and the frames |
| `CANNOT READ IMAGE` / `!!! ERROR !!! CANNOT OPEN` | template path wrong, or for `.h5` data the `LIB=` line or the neggia library missing |
| XYCORR or INIT fail immediately with `ILLEGAL KEYWORD` | a keyword value is malformed; open the Full Input File and look at the line quoted in the log |
| The run stops with "another program is already running in this folder" | a run is still active there (perhaps another browser tab): Stop it or wait |
