# Integrating and correcting: DEFPIX, INTEGRATE, CORRECT

**Goal:** integrated and corrected intensities (`XDS_ASCII.HKL`) with statistics you have read and understood.

## Choose where the run writes

Before the first full run decide the **run folder**; it is remembered per project.

![The run-folder field (1), the Subfolders mode switch (2) and the status line that shows the current output folder (3).](images/07-01-run-folder.png)

- Leave the field empty: XDS runs in the project folder (*Overwrite* mode); each new CORRECT or IDXREF keeps the previous log as `.prev1` … `.prev4`.
- Type or browse a folder (it can be next to the frames): CrystalPilot creates it and copies `XDS.INP` into it before every run. The field suggests the folder of the frames and the folders used recently.
- **Sub-folders** mode: every run gets a new numbered folder (or a name you type) inside the base folder, so different strategies (space groups, resolution limits, Friedel's law) can be compared side by side.

The status line shows the folder where results will be read from; on Windows also in Explorer notation. Everything downstream (LP viewer, comparison, POINTLESS, XSCALE autofill) follows this folder automatically.

## Run

1. Click **▶ Integrate & Correct** (DEFPIX → INTEGRATE → CORRECT). INTEGRATE is the slow step; xds_par uses the CPU cores set in the sidebar's XDS Config panel (4 by default, chapter 3).
2. Alternatives: **▶ Full Pipeline** runs everything from XYCORR (or up to the step chosen in *Stop at*); **⚡ CORRECT Only** re-runs CORRECT alone in seconds after a change of space group, cell, resolution or Friedel's law; **GXPARM Re-integrate** copies the geometry refined by CORRECT (`GXPARM.XDS`) over `XPARM.XDS` and runs DEFPIX → INTEGRATE → CORRECT again, which often improves the statistics; the **▶** next to any step runs from that step through CORRECT.

![Integrate & Correct, and CORRECT Only for quick re-runs.](images/07-02-integrate-button.png)

3. Every program run has a time limit (4 hours by default; `step_timeout` in the settings file). When it is exceeded the run is stopped and the log says so.

## Read the CORRECT result

Click the green **CORRECT** step (or, in the LP Viewer, choose CORRECT under *Key Metrics* and click **View Metrics**). The metrics panel is the heart of the analysis:

![CORRECT metrics: space group and cell, ISa, the shell table with colour-coded quality, charts, cut-off estimates.](images/07-03-correct-metrics.png)

@[After a run: each step one click away; CORRECT.LP read for you, the statistics per shell, the cut-off estimates and the charts.](videos/results.mp4)

1. **Space group and cell** as decided by CORRECT, with the χ² of the correction factors (Advanced). If you had left the space group open, this is XDS's proposal; POINTLESS (chapter 9) gives the definitive answer.
2. **ISa**, the asymptotic I/σ: above 20 is excellent, 10–20 good, below 5 indicates problems with the data or the integration.
3. The **resolution shell table**: per shell the number of observations and unique reflections, completeness, R-obs, R-meas, I/σ, CC½ and the anomalous statistics; cells are coloured by quality.

![The shell table.](images/07-04-correct-table.png)

4. The **charts** (R-factors and CC½, I/σ and completeness against resolution; Wilson plot; distribution moments at Expert level). Click any chart to enlarge it.

![Statistics against resolution.](images/07-05-correct-charts.png)

5. **Resolution cut-off estimates** by four criteria (I/σ ≈ 2, CC½ ≈ 50 %, R-obs ≈ 55 %, CC½ significance after Karplus & Diederichs 2012). The first three are interpolated between the two shells around the threshold, in 1/d², with each shell's value placed at the middle of the shell (the log prints the high limit of a shell, but the number is the mean over the whole shell); the last is the limit of the last shell whose CC½ XDS marks as significant (`*`). AutoPilot, the figures and these buttons use the same calculation. Each button applies its limit as `INCLUDE_RESOLUTION_RANGE` in `XDS.INP`; re-run **CORRECT Only** afterwards. CC½ significance is the modern default; the others are shown for comparison and for journals that ask for them.

![Cut-off estimates with apply buttons.](images/07-06-cutoffs.png)

6. **Matthews coefficient**: type the molecular weight; the cell and space group of this CORRECT run give V<sub>M</sub> and solvent content for 1…n molecules per asymmetric unit.

![The Matthews calculator under the CORRECT metrics.](images/07-07-matthews.png)

7. **Decisions offered by the panel.** *Systematic Absences Analysis* tests the screw axes expected for the space group against the observed absences and lists space-group suggestions, each with a **⚡ try** button that re-runs CORRECT in that group. The *Laue group* table (R<sub>meas</sub> of every compatible group relative to P1) has a **⚡ SG n** button per row for the same purpose. The *anomalous signal* summary (SigAno, CC(anom)) offers **Set FRIEDEL=FALSE & Re-run CORRECT** when Bijvoet pairs were merged but a signal seems present.
8. Further sections: **Wilson analysis** (B-factor, fit; Advanced), **Wilson distribution moments** per shell with ice-ring annotations (Expert), **Alien reflections** (outliers of the Wilson distribution), **Ice Ring Analysis** (**Auto-detect Ice Rings** scores the shells at the hexagonal ice spacings, **Chart overlay** marks them on the shell chart, **❄ Apply Selected Exclusions** or **Apply All Standard Ice Ranges** write EXCLUDE_RESOLUTION_RANGE lines to XDS.INP, **✕ Remove All Exclusions** takes them out), and **Diffraction Anisotropy** (**Analyse Anisotropy** computes, from XDS_ASCII.HKL with gemmi, the mean I/σ of the merged reflections, a true CC½ and a Wilson B along each reciprocal axis, when the gemmi package is installed). After any change to XDS.INP, run **⚡ CORRECT Only**.

CrystalPilot warns when something is wrong with the data. This is what an incomplete data set looks like: a 60-frame wedge processed for illustration gives 38 % completeness, and the metrics panel says so in orange before you read any number.

![The completeness warning on an incomplete data set (a 60-frame wedge): the banner and the low Complete% column.](images/07-09-low-completeness-warning.png)

## Read the INTEGRATE result

Click the green **INTEGRATE** step. The per-frame charts are the radiation-damage and crystal-behaviour diagnostics:

![INTEGRATE metrics: suggested profile parameters and the per-frame charts.](images/07-08-integrate-metrics.png)

- **Mosaicity (SIGMAR) and beam divergence (SIGMAB) per frame** (Advanced): a rising mosaicity trend means radiation damage.
- **Scale factor per frame** (Advanced): a steady decrease means damage or beam decay; jumps are beam dumps, shutter errors or crystal movement.
- **Reflections per frame**: strong (green), rejected (red), overloaded (orange); a drop in strong reflections goes with damage or slippage.

Use these to decide an `EXCLUDE_DATA_RANGE` (or let ΔCC½ decide, chapter 10), then re-run **CORRECT Only** or, for excluded frames, Integrate & Correct again.

## Figures for a report

Two ways to get a picture out of what you are looking at.

**⤓ Figures (.png)**, next to the other buttons on the CORRECT metrics (and on the XSCALE metrics for the merged data), writes a set of figures next to the log they come from: CC½, I/σ, completeness and R-meas, each as a PNG at 300 dpi and as a PDF for a journal, plus `CORRECT_Resolution_Statistics.png`, all four on one sheet — usually the one a report wants. The message names the folder and offers each file as a download. The merged set is named `XSCALE_…`, so the two never overwrite each other.

They are meant to be read by someone who was not sitting next to you:

- the resolution axis is **linear in 1/d²**, the space XDS bins the shells in, so the fall-off is not distorted by stretching the few low-resolution shells to the width of the high-resolution ones;
- the **cut-off suggested by that metric's criterion** is marked and everything beyond it shaded, so what would be discarded is visible. The number comes from the same code as the cut-off buttons, so a figure can never contradict the interface;
- **ice rings** with strong or moderate evidence are banded: a completeness dip or an R-meas spike at 3.90 or 2.25 Å is contamination, not resolution;
- a **CC½ shell XDS calls significant** at the 0.1 % level gets a filled marker, one it does not gets a hollow one;
- percentages use a fixed 0–100 axis, so two runs can be laid side by side and compared;
- the overall row, the space group, the cell, and a line naming the program, the log and the date travel with the figure.

**Any chart on screen**: click it to open it in a window. Drag the window by its title bar to move it and by the grip in its bottom-right corner to resize it (the chart is redrawn to fill it); it keeps its place and size for the next chart, and a double-click on the title bar puts it back in the middle. **⤓ PNG** in the corner of the window saves the chart. That saves the chart as it is — dark, every series together — drawn at a fixed size so it does not depend on your screen.

The figures need matplotlib, the same package the frame viewer uses; the Environment screen offers to install it if it is missing.

## If it goes wrong

| Symptom | What to do |
|---|---|
| INTEGRATE takes forever on Windows | frames are read over the `/mnt` bridge; copy the data set into the projects folder |
| `!!! ERROR !!! INSUFFICIENT NUMBER OF ACCEPTED SPOTS` in INTEGRATE | wrong lattice or cell; go back to IDXREF, pick a lower-symmetry lattice |
| CORRECT chooses a surprising space group | run POINTLESS (chapter 9) and compare; check the systematic absences it reports |
| Low completeness in the table | the rotation range was too short for this symmetry, or DEFPIX masked too much: look at ABS.cbf / BKGPIX.cbf in the frame viewer's XDS diagnostics row (Advanced) |
| Very different statistics from the beamline pipeline | compare the two logs with *Compare…* (chapter 8) |
