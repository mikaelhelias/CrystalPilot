# Space group with POINTLESS

**Goal:** an independent, evidence-based Laue group and space group, applied to `XDS.INP` with one click. Requires CCP4; the tab is shown from the **Advanced** work mode.

CORRECT proposes a space group from the merging statistics of the candidate symmetries. POINTLESS (Phil Evans, CCP4) scores the symmetry elements and reads the systematic absences, which decides between screw-axis alternatives such as P2₁2₁2₁ and P22₁2₁.

## Run it

1. Open the **POINTLESS** tab. The card shows whether CCP4 was found and the current CORRECT result (cell, space group) for reference.
2. **Input file**: leave it blank and the latest `XDS_ASCII.HKL` of the run folder is used; the **🔍** button fills the field with what it finds (XSCALE outputs and MTZ files are accepted too if you want to test merged data).
3. **Options**: *chirality* (chiral for proteins), *setting* (symmetry-based is the CCP4 convention; cell-based keeps the input axes), optional forced Laue group or space group, resolution limits.
4. Click **▶ Run POINTLESS**. The log streams; the result is saved as `pointless.log` next to the XDS output and reloaded whenever you return to the tab.

![The POINTLESS tab with the current CORRECT information and the Run button.](images/09-01-pointless.png)

## Read the result

![POINTLESS results: best solution and confidence, space group and Laue group score tables, apply buttons.](images/09-02-pointless-results.png)

- **Best solution** with its total probability; the reindexing operator if the axes change.
- **Space group scores**: each candidate with the probability from systematic absences. A single candidate above ~0.8 is clear; two close candidates (typical for one uncertain screw axis) mean you should process both and decide by refinement, or collect more data.
- **Laue group scores**: the symmetry elements found and their Z-scores and CC values.

## Apply it

- **Apply SG #n to XDS.INP** writes SPACE_GROUP_NUMBER and the cell (in the POINTLESS setting) to the project's `XDS.INP` and sets the toggles to active.
- **Apply SG #n & Re-run CORRECT** does the same and runs CORRECT immediately, so the new statistics appear in the Data Processing tab within seconds.
- **📄 View POINTLESS Log** shows the raw `pointless.log`.

## If it goes wrong

| Symptom | What to do |
|---|---|
| "CCP4 not found" | install CCP4 and source `ccp4.setup-sh` before starting CrystalPilot (Linux), or run the Windows wizard again after installing CCP4 for Windows; set the bin folder in the XDSCONV tab if it is in an unusual place |
| Input file not found | run CORRECT first; the tab reads the output folder of the last run |
| POINTLESS proposes a different cell setting | accept it; XDS is re-run with the reindexed cell when you apply |
| Two space groups with similar probability | process both (sub-folder mode, chapter 7) and refine; the systematic-absence table shows which reflections decide |
