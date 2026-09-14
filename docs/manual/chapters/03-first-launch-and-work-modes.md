# First launch, the Environment screen and the work modes

**Goal:** know that everything the program needs is in place, and choose how much of the interface you want to see.

## The Environment screen

The first time the interface opens, and again whenever something about the installation changes, the **Environment check** appears over the page. Each row is one component with a status badge:

![The Environment check on first launch: Python packages, XDS, parallel binaries, the Eiger reader, CCP4, the projects folder. Every row that can be fixed has a path field and a button.](images/03-01-environment.png)

| Row | OK means | If not OK |
|---|---|---|
| Python packages for the frame viewer | numpy, matplotlib, h5py, hdf5plugin, fabio are importable | click **⬇ Install now (pip)**; the pip/apt output streams below |
| XDS | `xds_par` (or `xds`), `xscale_par` and `xdsconv` found in the folder shown | type the folder that contains them, **Save & re-check**; the link goes to the XDS download page |
| Parallel processing | `xds_par` and `xscale_par` present and enabled | only serial binaries found: processing works on one core |
| XDS helper programs (row shown only when one is missing) | `forkxds`, `mcolspot`, `mintegrate` next to `xds_par` | copy the complete XDS package; xds_par needs them for COLSPOT and INTEGRATE |
| Eiger HDF5 reader | `dectris-neggia.so` found | needed only for `.h5` data: download from DECTRIS, place it next to `xds_par` or type its path |
| CCP4 (optional) | pointless, aimless, ctruncate, f2mtz, cad found | POINTLESS, AIMLESS and the MTZ export are unavailable until CCP4 is installed and sourced (Windows: run the wizard again) |
| Projects folder | where projects live; on Windows also the Explorer path | **📂 Open in file manager** opens it |
| Windows Subsystem for Linux (Windows only) | information: the distribution, where the Windows drives are mounted, the mapped drive letter | — |

1. Fix what is red or orange (paths are saved per computer, in `~/.crystalpilot/settings.json`).
2. Click **Continue**. Tick **Don't show this again unless something changes** if you do not want the screen at every start; it comes back when the fingerprint of the checks changes, for example after CCP4 was installed.
3. Later: click **⚙ Environment** in the header to open the screen again (it is also in the About panel behind the version badge). The header also has **⬡ Check Connection** (is the server answering?) and, when the manual is installed, **📖 Manual**.

## Work modes: how much you see

The sidebar has a **Work mode** selector with four levels. A higher level never removes anything; it adds tabs, parameters and analysis sections. The manual describes the interface at **Expert**, so if a button or field mentioned here is not on your screen, raise the level.

![The work-mode selector in the sidebar; the badge shows the current level and the info bar under the tab bar explains it.](images/02-07-mode-selector.png)

| Level | Meant for | Adds |
|---|---|---|
| **Tutorial** | first contact | the core workflow only, with explanatory hints under every card: project, XDS.INP, run, results, XSCALE, XDSCONV, frame viewer |
| **Normal** | routine processing | the **AutoPilot** and **Statistics** tabs; FRIEDEL'S_LAW and RESOLUTION_SHELLS in the parameter form; **CORRECT Only** and **GXPARM Re-integrate**; in the results: Matthews calculator, cut-off estimates, ISa, shell charts, ice-ring analysis, anomalous summary, run history and comparison buttons |
| **Advanced** | diagnosing problems | the **POINTLESS** and **AIMLESS** tabs; the *Corrections* and *Reporting* parameter groups, MINIMUM_FRACTION_OF_INDEXED_SPOTS; in XSCALE: STRICT_ABSORPTION_CORRECTION and REIDX; IDXREF spot and spindle deviations; correction-factor χ² fit, Wilson analysis, INTEGRATE mosaicity and scale charts, the anomalous shell tables; the frame viewer's XDS diagnostic images |
| **Expert** | everything | the **ΔCC½** and **gemmi** tabs; XSCALE NBATCH; **Convert with gemmi** in XDSCONV; Wilson distribution moments; the **Full** auto-indexing tier and **Force cell** |

The tab bar at each level:

![Tutorial: Data Processing, XSCALE, XDSCONV, Frame Viewer, Guide, Docs.](images/02-01-tabs-tutorial.png)

![Normal adds AutoPilot and Statistics.](images/02-02-tabs-normal.png)

![Advanced adds POINTLESS and AIMLESS.](images/02-03-tabs-advanced.png)

![Expert adds ΔCC½ and gemmi.](images/02-04-tabs-expert.png)

The same parameter form at Tutorial and at Expert:

![Key Parameters at Tutorial level: experiment, detector and indexing essentials.](images/02-05-params-tutorial.png)

![Key Parameters at Expert level: the Corrections and Reporting groups and every toggle are visible.](images/02-06-params-expert.png)

## Everything Expert level unlocks, tab by tab

- **Data Processing, Key Parameters:** MINIMUM_FRACTION_OF_INDEXED_SPOTS (Advanced); the *Corrections* group: CORRECTIONS (DECAY MODULATION ABSORPTION), STRICT_ABSORPTION_CORRECTION, MINIMUM_I/SIGMA, REFLECTIONS/CORRECTION_FACTOR, REFINE(INTEGRATE), the neggia LIB line (Advanced); the *Reporting* group: INCLUDE_RESOLUTION_RANGE, RESOLUTION_SHELLS (Advanced/Normal); FRIEDEL'S_LAW (Normal).
- **Data Processing, run buttons:** **CORRECT Only** and **GXPARM Re-integrate** (Normal).
- **Auto-Index card:** the **Full** tier (bisection of SIGNAL_PIXEL) is Expert; Quick, Medium and the **🔒 SG/Cell** lock are available at every level.
- **IDXREF metrics:** compare and history buttons (Normal); spot position and spindle deviation cards (Advanced).
- **CORRECT metrics:** compare and history (Normal); ISa, shell charts, resolution cut-off estimates, Matthews calculator, ice-ring analysis, anomalous summary (Normal); correction-factor χ² fit, Wilson B-factor analysis, anomalous per-shell details (Advanced); Wilson distribution moments (Expert). The systematic-absence analysis, the Laue-group table and the anisotropy card are shown at every level.
- **INTEGRATE metrics:** reflections per frame (Normal); mosaicity/divergence and scale-factor charts (Advanced).
- **XSCALE:** FRIEDEL'S_LAW (Normal); STRICT_ABSORPTION_CORRECTION and REIDX (Advanced); NBATCH (Expert); in the results the anomalous shell details (Advanced).
- **XDSCONV:** the gemmi status line and **Convert to MTZ (gemmi)** (Expert).
- **Frame Viewer:** the *XDS diagnostics* row that loads the diagnostic images XDS writes (BKGINIT, BLANK, ABS, …) (Advanced).
- **Tabs:** AutoPilot and Statistics (Normal), POINTLESS and AIMLESS (Advanced), ΔCC½ and gemmi (Expert).

## Cutoff preference

Next to the work mode, **Cutoff preference** chooses which resolution criterion the XSCALE autofill and AutoPilot use by default: I/σ ≈ 2, CC½ ≈ 50 %, R-obs ≈ 55 %, or CC½ significance. It is remembered, like the work mode.
