# Scaling and merging with XSCALE

**Goal:** a scaled, merged reflection file (`merged.ahkl`) from one or several data sets, with statistics and a chosen resolution limit.

@[Merging with XSCALE, the cut-off taken from CORRECT.LP, then an MTZ for refinement with XDSCONV (chapter 12).](videos/merge.mp4)

XSCALE puts data sets on a common scale, corrects absorption, detector and radiation-damage effects, and merges symmetry equivalents. Even for a single data set it is the normal way to produce the final merged file.

## Fill the parameters

1. Open the **XSCALE** tab, sub-tab **Key Parameters**.
2. **Input files**: click **🔍 Auto-detect**. It lists the `XDS_ASCII.HKL` files of the project, its sub-folders and the current XDS output folder; tick the ones to scale (several data sets of the same crystal form are merged together). You can also type a path, add rows with **+ Add Input File**, or remove one with its ✕. Leaving the list empty is fine: the project's `XDS_ASCII.HKL` from the last CORRECT run is used.
3. Click **🔄 Autofill from CORRECT.LP**: space group, cell and the resolution limit chosen by your *Cutoff preference* are transferred from the latest CORRECT run.
4. Check the other keywords:

![Key Parameters of XSCALE with Auto-detect and Autofill marked.](images/11-01-xscale-params.png)

| Keyword | Choose |
|---|---|
| FRIEDEL'S_LAW | TRUE for native data; FALSE for anomalous data (keeps Bijvoet pairs apart) |
| MERGE | FALSE keeps every observation (needed by AIMLESS and for unmerged deposition); TRUE merges to unique reflections |
| OUTPUT_FILE | `merged.ahkl` by default; XDS format, read directly by XDSCONV, POINTLESS and AIMLESS |
| INCLUDE_RESOLUTION_RANGE | from the autofill; adjust after reading the statistics |
| RESOLUTION_SHELLS | the bins of the statistics table |
| STRICT_ABSORPTION_CORRECTION, NBATCH, REIDX, REFERENCE_DATA_SET | Advanced/Expert options with toggles: absorption strictness, batch count for smooth scaling, re-indexing operator for one input, reference data set for consistent indexing |

## Save and run

![Update in existing XSCALE.INP, and Save as new XSCALE.INP.](images/11-02-xscale-save-run.png)

- **💾 Update in existing XSCALE.INP** merges the form into the file and keeps everything else (comments, other OUTPUT_FILE blocks).
- **📄 Save as new XSCALE.INP** writes a fresh file from the form.
- Both write every keyword into its XSCALE section (global keywords before `OUTPUT_FILE`, output keywords after it, per-data-set keywords under each `INPUT_FILE`), and repair a file that had keywords in the wrong place. If a run starts with no input file at all, the project's `XDS_ASCII.HKL` is inserted and the log says so.
- **Run mode**: *Overwrite* runs in the project folder (previous `XSCALE.LP` kept as `.prev1`); *Sub-folders* creates `XSCALE_001`, `XSCALE_002`, … and rewrites the input paths so they still resolve.
- Click **▶ Run XSCALE**. The log streams; the sub-tab **LP Viewer** opens the result.

![Run XSCALE at the top of the tab; View XSCALE.LP opens the result.](images/11-05-xscale-run.png)

## Read the result

![XSCALE.LP parsed: shell table, ISa per data set, charts.](images/11-03-xscale-lp.png)

- The shell table has the same columns as CORRECT (completeness, R-obs, R-meas, I/σ, CC½, anomalous); for several inputs the ISa of each data set is listed. The correlation factors between data sets, which tell you whether one of them does not belong, are in the log itself: search XSCALE.LP for `CORRELATIONS BETWEEN INPUT DATA SETS`.
- **Resolution cut-off estimates** with the four criteria; each button applies the limit to `XSCALE.INP` (then run again). **Run History** and **Compare…** work here too.

![Cut-off estimates for the merged data with apply buttons.](images/11-04-xscale-cutoffs.png)

## If it goes wrong

| Message | Fix |
|---|---|
| `!!! ERROR !!! MISPLACED PARAMETER` | a keyword sat in the wrong section of a hand-edited file: save the parameters again (either button) and run |
| `XSCALE.INP has no INPUT_FILE= line and no XDS_ASCII.HKL was found` | run CORRECT first, or add the files with Auto-detect and save |
| `CANNOT OPEN OR READ FILE` in the log | an input path is relative to the wrong folder; use Auto-detect, which writes absolute paths |
| Low correlation between two inputs | one data set is indexed differently (enantiomorph or axis permutation): give it a REIDX operator or scale it separately |
