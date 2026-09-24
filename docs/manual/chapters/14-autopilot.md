# AutoPilot: set it up once, process everything

**Goal:** one data set or a whole synchrotron trip processed without sitting next to it: each with a chosen resolution limit, merged reflections and an MTZ, compared in one table, the best of them merged, and a log that explains every decision. The tab is shown from the **Normal** work mode.

@[Setting up a run for a whole beamline visit: the folder, the data sets and their beamline XDS.INP, the six steps, Start.](videos/autopilot.mp4)

The **AutoPilot** tab is a wizard of six steps. Nothing runs until you press **Start AutoPilot** on the last one. Every data set becomes a project of its own, so everything the other tabs show is there for it afterwards, and everything AutoPilot did can be redone or refined by hand.

![The AutoPilot wizard: the six steps, the drop area for folders, and the runs below.](images/14-01-autopilot.png)

## 1. Folders

Drop the folders that hold the images on the drop area, or type or paste their paths and click **Add** (Windows paths such as `Z:\DATA\run1` are understood), or **Browse**. Add as many as you like.

A browser never tells a web page where a dragged folder is. AutoPilot therefore finds it by its name and the names and sizes of the files in it, looking in recently used folders, the projects folder, the home folder and the drives (for at most 20 seconds). If the same folder is in two places it asks which one; if it is not found, paste the path instead (in Explorer, Shift + right-click the folder → **Copy as path**).

**A project you set up by hand.** Open it in the sidebar and click **➕ Add the open project**. It is processed in place, with the `XDS.INP` you prepared in Data Processing — no search, no import, no space-group route. Open another project to add it too; a project can mix with dropped folders in one run.

**Search depth** sets how many folder levels below each folder are searched. Eiger `*_master.h5` files and numbered frame series (five frames or more) are found by their names, so a folder on a network share is listed in seconds.

## 2. Data sets and their XDS.INP

The data sets found are listed. Untick the ones you do not want, and change a project name if the file prefix is not a good one.

For each data set AutoPilot looks for the `XDS.INP` a beamline pipeline left behind. That file carries what the beamline knows about its own geometry — the direction of the rotation axis, the beam centre, the detector orientation — which an image header often does not say.

**Where it looks.** Pipelines name their folders differently at every beamline, so the search is not tied to folder names. It looks in the folders from step 1, in each data set's folder, its parent and its grandparent and everything below them, and in any folder you add under **Also search in** — typically the beamline's processed-data folder when it lives elsewhere.

**What counts.** A file is a candidate when its `NAME_TEMPLATE_OF_DATA_FRAMES` names this data set's images (by file name — the beamline's paths are not this computer's) and, when the image header can be read, its wavelength, detector distance and oscillation agree with the images. A file that disagrees is listed as *not used*, with the reason.

**Which one wins.** Candidates are ranked by:

1. how much of the image folder path in the file's template matches the data set's folder (a file for `…/sample/xtal1/` beats one for `…/sample/xtal2/` with the same file names);
2. the **Folders searched first** list: words that a folder name must *contain* — `fast_dp` also matches `fast_dp_2`, `autoproc` matches `autoPROC.run1`, `processing` matches `processing-old`. The word higher in the list wins. Add words, remove them and move them up or down; the list is remembered. **Defaults** puts back `fast_dp`, `processing`, `autoproc`;
3. the newest file.

Each data set is marked:

| Mark | Meaning |
|---|---|
| **imported** | one clear best file; it is used |
| **pick one** | equally good files that disagree on the beam centre, distance, rotation axis, space group or cell. The first is used unless you choose another in the list |
| **from header** | no matching file: `XDS.INP` is written from the image header, as *Generate from images* does (chapter 5) |
| **your choice** | you chose a file, or the header, yourself |

**view** shows the file exactly as it will be used. An imported `XDS.INP` keeps everything the beamline wrote, except:

- the image template, which now points at the images on this computer;
- `LIB=`, which becomes the HDF5 library set in this step for Eiger data (**Detect** finds it next to XDS, **Save** stores it);
- file names that do not exist on this computer (for example `X-GEO_CORR`), which are commented out;
- `DATA_RANGE`, `SPOT_RANGE` and `BACKGROUND_RANGE`, when they go beyond the frames on disk (a spot range with none of its frames on disk is commented out);
- the beamline's computer settings — `CLUSTER_NODES`, `MAXIMUM_NUMBER_OF_JOBS`, `MAXIMUM_NUMBER_OF_PROCESSORS`, `SECONDS` — commented out, and this computer's own added: `MAXIMUM_NUMBER_OF_PROCESSORS=` with the CPU cores of the XDS Config panel and `MAXIMUM_NUMBER_OF_JOBS= 1` (chapter 3);
- `INCLUDE_RESOLUTION_RANGE`, commented out, because your cut-offs decide.

Every change is a comment starting with `! CrystalPilot:` in the project's `XDS.INP`, and a line in the log.

## 3. Cut-offs

| Choice | What it decides |
|---|---|
| Resolution cut-off | **I/σ ≈ 2** (default), **CC½ ≈ 50 %**, **CC½ significant** or **R-obs ≈ 55 %** — independent of the sidebar *Cutoff preference* |
| Friedel's law | tick box for XSCALE and XDSCONV: ticked (default) is TRUE and merges anomalous pairs; untick it for SAD/MAD data to keep the anomalous signal |
| Low- and high-resolution limit | optional `INCLUDE_RESOLUTION_RANGE` for every data set; the cut-off still applies inside it. A high limit alone keeps all low-resolution data (the low limit is then 999 Å) |

## 4. Reprocessing

| Choice | What it decides |
|---|---|
| Re-integrate with refined geometry (GXPARM → XPARM) | a second DEFPIX-INTEGRATE-CORRECT with the geometry CORRECT refined: **never**, **always** (default), or **only if better** — the first integration is put aside and restored when the re-integration does not improve the measure you choose (ISa, the resolution cut-off, or overall CC½) |
| ΔCC½ frame rejection (XDSCC12) | tick box, on by default. It runs inside the re-integration, so it does nothing when re-integration is *never*; the wizard tells you |
| Ice rings | excluded when CORRECT shows them (default), or left in |

## 5. Space group and indexing

| Choice | What it decides |
|---|---|
| Space group and cell | determined for each data set (default), or one space group and cell imposed on all. For one crystal form, imposing it keeps every data set in the same setting, which merging needs. The cell is required: XDS takes a space group only together with its cell |
| Space group in an imported XDS.INP | for data sets whose imported file has a space group and its unit cell (a space group without a cell is left out). By default: **process without it; if that fails, with it; if that fails too, auto-index**. Or always use it, or ignore it |
| Screw axes | tick box, on by default; shown when the space group is determined for each data set. XDS chooses the space group without screw axes (C222 for C222₁, P222 for P2₁2₁2₁). Ticked, the axial reflections in CORRECT.LP are checked, and when they show screw axes CORRECT runs again in the matching space group with the refined cell — seconds, no re-integration; the re-integration and the merge then use it. The log says what was seen, for example *0,0,l only every 2nd present → C222₁ (#20), not C222 (#21) as XDS chose*. Enantiomorphs (P4₁/P4₃, P3₁/P3₂ …) cannot be told apart this way: one is kept and the log names the other. A space group given in the XDS.INP is left alone. Unticked, XDS's choice is kept |
| If indexing fails | after AutoPilot's own IDXREF fixes: give up on that data set, or auto-index at the quick, medium (default) or full tier |

With the default route a data set gets up to three runs, each starting again from the imported file: first without its space group, then with it, then with auto-indexing and the space group left open. The first two do not auto-index, so a failed indexing moves on to the next attempt at once. With **give up** as the indexing choice, the route ends after the second run.

## 6. Review and start

One page lists every choice, how many data sets import their `XDS.INP`, and warns about data sets still marked *pick one*. Give the run a name if you like, and click **▶ Start AutoPilot**.

One run is processed at a time, one data set at a time, because XDS already uses every processor core. You can close the page: the run carries on, and the tab picks it up when you come back.

## Runs

The **Runs** card lists every run. For the chosen one:

- **Skip current** stops the data set being processed and goes on with the next.
- **Stop** stops now. The data set being processed goes back in the queue with the rest, and **Resume** processes it again — from a fresh `XDS.INP` when its `XDS.INP` was generated (the interrupted run's changes are kept as `XDS.INP.interrupted_run`). A data set that had just finished stays finished.
- A data set that fails does not stop the others; its row says why.

The table shows each data set's status (with the phase and the attempt while it runs), where its `XDS.INP` came from, space group, cell, resolution cut-off, and the overall completeness, R-meas, I/σ, CC½ and ISa from its own CORRECT.LP, plus whether the re-integration was kept (hover for the numbers it was judged on). The best value of each column is green. Click a heading to sort.

## One data set: progress and summary

Click a row to follow that data set below the table. The phase bar and the live log show the progress:

1. Import, generate or check `XDS.INP`.
2. XYCORR → INIT → COLSPOT → IDXREF with automatic recovery: when a step fails AutoPilot diagnoses the log and retries, up to three times per step. For IDXREF the fixes are wider spot-position and spindle tolerances, a refinement without the detector position, SEPMIN / CLUSTER_RADIUS for close lattices, and a lower MINIMUM_FRACTION_OF_INDEXED_SPOTS; when indexing still fails, the Auto-Index search of chapter 6 (SPOT_RANGE wedges, SIGNAL_PIXEL, index origin) takes over at the tier you chose. For INTEGRATE it is a larger DELPHI (10, 20, 45, 90) or a refinement without the cell. AutoPilot does not search for the beam centre: a wrong ORGX/ORGY has to be corrected by hand, or comes right with the beamline's XDS.INP.
3. DEFPIX → INTEGRATE → CORRECT.
4. Ice rings with strong or moderate evidence are excluded and CORRECT re-run (when chosen); a data set whose ISa is below 3 stops here. The resolution cut-off is worked out by the chosen criterion. It is not written into `XDS.INP`: CORRECT keeps all the data, and the limit is applied in XSCALE and XDSCONV.
5. The re-integration with the refined geometry, as chosen in step 4 of the wizard. The first integration is always put aside first, so a re-integration that fails, or that loses under *only if better*, is undone. The optional ΔCC½ exclusions happen here: XDSCC12, EXCLUDE_DATA_RANGE, and DEFPIX-INTEGRATE-CORRECT once more.
6. XSCALE at the cut-off.
7. XDSCONV and f2mtz/cad (or gemmi) to an MTZ.

![AutoPilot results on a 60-frame wedge (hence the completeness warning): status and diagnoses, the shell table, the MTZ path.](images/14-02-autopilot-results.png)

When it has finished, the summary shows:

- **Status**, number of retries and the list of diagnosed problems (for example `ice_rings_detected`, `solution_inaccurate`).
- **Optimization**: ISa, R-meas, CC½, I/σ and resolution before and after the re-integration pass.
- The **statistics by resolution shell** from XSCALE, the chosen cut-offs by every criterion, and the **MTZ** path.
- **Open in Statistics Tab** builds Table 1 from this run; **Open project** opens the data set in Data Processing. Results are saved as `AUTOPILOT_RESULTS.json` in the project. With a project open and no data set clicked, the tab shows that project's last AutoPilot result.

## Merge

With two or more finished data sets, tick the ones you want together, optionally choose the reference and Friedel's law, and click **Preview XSCALE.INP** to read the file before anything runs, or **Merge with XSCALE**.

- Only data sets with the reference's space group and a cell within 3 % on each axis (angles within 1.5°) go in; the others are listed with the reason.
- The reference is the data set with the highest ISa unless you choose one. It is the first input and the REFERENCE_DATA_SET, so it anchors the scaling and the indexing.
- Each data set enters at its own cut-off, with no low-resolution limit.
- The merge is written to `<projects folder>/batches/<run>/merge_<date>/`. The reflection files are reached through short names in `inputs/`, because XDS cannot read file names that contain blanks. The preview shows exactly that file.

When XSCALE finishes, the merged completeness, R-meas, I/σ and CC½ appear under the merge.

## After AutoPilot

Everything is ordinary project output: open the CORRECT and XSCALE metrics, run POINTLESS, compare with a manual run through *Run History*, or adjust `XDS.INP` and re-run steps by hand.

## If it goes wrong

| Symptom | What to do |
|---|---|
| A data set is *from header* although the beamline processed it | add the beamline's processed-data folder under **Also search in** and click **Search for XDS.INP again**; open the list to see files that were *not used* and why |
| *not used: wavelength … in the XDS.INP, … in the images* | the file belongs to another sweep with the same file names; the right one may be further down the list |
| The image folder's path has blanks (`/mnt/c/Users/First Last/...`) | nothing to do: XDS cannot read such a path, so the project gets a link without blanks (`frames`) and the template goes through it. Blanks in the frame file names themselves cannot be worked around: rename the frames |
| Stops after IDXREF retries | indexing needs a human look: open the IDXREF metrics and the frames, then use Auto-Index or fix the geometry (chapter 6) |
| "XDS.INP could not be generated" | the header lacks wavelength or oscillation: open the project in Data Processing, fill them in, and run the steps there |
| No MTZ at the end | CCP4 and gemmi both unavailable: install one (chapter 12) and run XDSCONV by hand |
