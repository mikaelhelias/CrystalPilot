# Statistics: the publication Table 1

**Goal:** the data-collection and processing statistics table required by journals and the PDB, filled from your files and exported in the format you write in. The tab is shown from the **Normal** work mode.

## Build it

1. Open the **Statistics** tab. Click **⟳ Refresh** if you processed since the tab was last open.
2. Choose the **source** with the buttons above the table: **XSCALE.LP** (preferred: the merged data you will deposit) or **CORRECT.LP** (when you did not scale with XSCALE). AutoPilot results can also be sent here with **Open in Statistics Tab**.

![Table 1 assembled from XSCALE.LP, with the source buttons and the export buttons.](images/16-01-table1.png)

The table lists, as *overall (highest shell)*:

| From | Rows |
|---|---|
| `XDS.INP` | detector, wavelength, oscillation, distance, data range and total rotation, frame template |
| `XSCALE.LP` or `CORRECT.LP` | space group, cell, resolution range, observations and unique reflections, completeness, multiplicity, R-merge, R-meas, R-pim, I/σ, CC½, ISa, anomalous completeness and multiplicity where present |

The highest shell is the last bin of the statistics table; change RESOLUTION_SHELLS in XSCALE if you want the outer shell defined differently.

## Export

- **📋 Copy TSV**: paste into Excel, Word or Google Sheets.
- **📋 Copy LaTeX**: a complete `table` environment with escaped symbols (Å, °, Greek letters, subscripts), ready for a manuscript.
- **⤓ Export .csv**: a two-column parameter / value file that any spreadsheet opens.

## Check before you publish

- The resolution limit and the shell boundaries agree with what you report in the text.
- Completeness and multiplicity match the merged data set you deposit (XSCALE output), not an earlier CORRECT run.
- For anomalous data the anomalous rows appear only when FRIEDEL'S_LAW was FALSE in XSCALE.
