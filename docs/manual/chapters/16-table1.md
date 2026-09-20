# Statistics: the publication Table 1

**Goal:** the data-collection and processing statistics table required by journals and the PDB, filled from your files and exported in the format you write in. The tab is shown from the **Normal** work mode.

## Build it

1. Open the **Statistics** tab. Click **⟳ Refresh** if you processed since the tab was last open.
2. The **source** is chosen for you: the newest **XSCALE.LP** (preferred: the merged data you will deposit), otherwise **CORRECT.LP**; the status line names it. To build the table from another run, open **Run History** on the CORRECT or XSCALE metrics and click that run under *Use for Table 1*. AutoPilot results can also be sent here with **Open in Statistics Tab**.

![Table 1 assembled from XSCALE.LP (the status line under the title names the source), with the export buttons marked.](images/16-01-table1.png)

The table lists, as *overall (highest shell)*:

| From | Rows |
|---|---|
| `XDS.INP` | detector, wavelength, oscillation, distance, data range and total rotation, frame template |
| `XSCALE.LP` or `CORRECT.LP` | space group, cell, resolution range, observations and unique reflections, completeness, multiplicity, R-merge, R-meas, I/σ, CC½, CC*, ISa, and for anomalous data CC(anom) and SigAno |
| the unmerged reflections (`XDS_ASCII.HKL`, or the XSCALE output file) | R-pim |
| `CORRECT.LP` | Wilson B and mosaicity (XSCALE.LP does not print them; the row says so) |

The resolution range runs from the lowest-resolution reflection in the data to the high limit of the last shell, and the highest shell is given as a range, for example 19.95–1.84 (2.05–1.84). The highest shell is the last bin of the statistics table; change RESOLUTION_SHELLS in XSCALE if you want it defined differently.

**R-pim.** XDS does not print R-pim, and R-meas/√multiplicity is only an approximation. CrystalPilot computes it with gemmi from the unmerged reflections of the same shells, a second or two after the table appears. As a check it computes R-meas the same way, and it prints R-pim only when that R-meas agrees with the one in the log; otherwise the row is left out and the status line says why (gemmi not installed, the reflection file is gone or belongs to another run, an XSCALE output written with MERGE=TRUE). In a shell with almost no signal the two R-meas values can differ; then only the overall value is given, which is one more reason to cut the resolution first.

## Export

- **📋 Copy TSV**: paste into Excel, Word or Google Sheets.
- **📋 Copy LaTeX**: a complete `table` environment with escaped symbols (Å, °, Greek letters, subscripts), ready for a manuscript.
- **⤓ Export .csv**: a two-column parameter / value file that any spreadsheet opens.

## Check before you publish

- The resolution limit and the shell boundaries agree with what you report in the text.
- Completeness and multiplicity match the merged data set you deposit (XSCALE output), not an earlier CORRECT run.
- For anomalous data the anomalous rows appear only when FRIEDEL'S_LAW was FALSE in XSCALE.
