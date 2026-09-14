# Exporting an MTZ with XDSCONV

**Goal:** a reflection file that refinement and phasing programs read: an MTZ for CCP4 / Phenix, or SHELX and XtalView formats.

## Fill the parameters

1. Open the **XDSCONV** tab, sub-tab **Key Parameters**.
2. **INPUT_FILE**: click **🔍 Auto from XSCALE** to pick the latest XSCALE output (`merged.ahkl`); a `XDS_ASCII.HKL` from CORRECT also works when you skipped XSCALE.
3. **OUTPUT_FILE** and format: `CCP4` (intensities and amplitudes, the usual choice for molecular replacement and refinement), `CCP4_F`, `CCP4_I`, `SHELX`, `XtalView`. **⚙ Auto-generate name** derives the name from the project.
4. **Free R flags**: keep *on* to write `GENERATE_FRACTION_OF_TEST_REFLECTIONS= 0.05` (5 % test set) unless you will inherit flags from an existing MTZ later.
5. **Friedel's law**: match what you used in XSCALE.
6. **Working folder**: the project folder, or the latest `XSCALE_NNN` sub-folder when XSCALE ran there.

![XDSCONV parameters with the input file, Auto from XSCALE, and the two run buttons.](images/12-01-xdsconv.png)

## Run

- **▶ Run XDSCONV** writes `XDSCONV.INP`, runs `xdsconv`, and, when CCP4 is available, runs `f2mtz` and `cad` with the `F2MTZ.INP` XDSCONV produced, giving the final `.mtz` (name shown in the log; on Windows the CCP4 for Windows programs are used through the bridge).
- **▶ Convert to MTZ (gemmi)** (Expert) writes an intensity MTZ with free-R flags directly from the XDS file with the gemmi library, without CCP4. gemmi can be installed from the tab if missing.

## Check

The sub-tab **LP Viewer** shows `XDSCONV.LP`: the number of reflections written, the resolution range, the free-R fraction, and the list of output files. The MTZ is in the working folder.

![XDSCONV.LP after a successful conversion with the MTZ produced by f2mtz and cad.](images/12-02-xdsconv-lp.png)

## If it goes wrong

| Symptom | What to do |
|---|---|
| "CCP4 not found", no `.mtz` | use **Convert to MTZ (gemmi)**, or install CCP4 (Linux: source `ccp4.setup-sh` before starting; Windows: run the wizard again) |
| `!!! ERROR !!! CANNOT OPEN INPUT_FILE` | the input path is relative to another folder: use Auto from XSCALE, or choose the right working folder |
| The MTZ has no free-R column | Free R flags were off; run again with them on, or use `freerflag` in CCP4 |
| Refinement complains about the space group | XDSCONV keeps the space group of the input; if POINTLESS proposed another setting, apply it and re-run CORRECT and XSCALE first |
