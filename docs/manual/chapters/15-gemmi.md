# Checks with gemmi

**Goal:** independent numbers to confirm or question what XDS reports, plus a few tools you need at the end of a project (anomalous scattering factors, a deposition file). The tab is shown at the **Expert** work mode and needs the Python package `gemmi` (installable from the tab).

## Run the analyses

1. Open the **gemmi** tab. The input file is filled from the project (**Autofill**: the latest `XDS_ASCII.HKL` or XSCALE output); change it to test another file.
2. Click **▶ Run All** (data quality and lattice symmetry), or **Data Quality** / **Lattice Symmetry** alone; the tools below run on their own buttons.

![The gemmi tab with the input file and the Run All button.](images/15-01-gemmi.png)

![Results: merging statistics per shell computed by gemmi, lattice symmetry, and the other tools.](images/15-02-gemmi-results.png)

| Analysis | What it tells you |
|---|---|
| **Data quality** | merging statistics per resolution shell (R-merge, R-meas, R-pim, CC½, I/σ, completeness, multiplicity) computed by gemmi from the unmerged reflections. **vs CORRECT.LP** or **vs XSCALE.LP** puts the XDS numbers next to them (**✕ Clear** removes them); they should agree closely, and disagreement usually means a different resolution limit or outlier treatment. |
| **Lattice symmetry** | whether the cell is compatible with a higher metric symmetry within an obliquity tolerance (default 3°). A hit does not prove higher symmetry, but it is a reason to run POINTLESS and to look at the merging statistics in the higher group. |
| **Anomalous scattering** | f′ and f″ of an element at your wavelength (or a scan around it): tells you how much anomalous signal to expect from Se, S, Zn, Br, … at the wavelength you used, and where the edge is. |
| **Deposition** | **Prepare Deposition** writes an mmCIF structure-factor file from the reflection data (and the merged MTZ when present) in the form the wwPDB expects; **Download CIF** saves it. |
| **Polarization** | applies a polarization correction to the unmerged intensities, the equivalent of the AIMLESS POLARIZATION keyword: choose the source type (synchrotron horizontal by default), the fraction *p* and the plane normal, then **Apply & Compare** writes a corrected MTZ and shows the R-factors before and after. XDS already corrects polarization, so use this only to test an unusual beamline setting; it does not change `XDS.INP`. |

## When to use it

- Before deposition: data-quality table for the paper (compare with Table 1), CIF file.
- When the merging statistics look too good or too bad: an independent computation removes one doubt.
- For phasing decisions: anomalous f″ at the wavelength you have.
