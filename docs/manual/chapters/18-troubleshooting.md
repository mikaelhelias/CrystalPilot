# Troubleshooting and reference

## The one rule about files

Input files you edit (`XDS.INP`, `XSCALE.INP`, `XDSCONV.INP`) are in the project folder. Everything a program writes is in the folder where that program last ran, and CrystalPilot remembers that folder per program. When a viewer says a file is missing, look at the status line under the run-folder field: that is where it is looking. The Docs tab (*Projects and where files live*) has the full rule, and `http://127.0.0.1:8000/api/projects/<name>/locations` lists where every file resolves.

## Messages you may see

| Message | Cause | Fix |
|---|---|---|
| `XDS executable not found` | wrong or empty XDS folder | Environment screen or the XDS Config panel in the sidebar: enter the folder that contains `xds_par` |
| `XDS.INP not found` | never saved | **Save Parameters** or **Save File** |
| `!!! ERROR !!! ILLEGAL (OBSOLETE ?) KEYWORD OR PARAMETER VALUE` | a malformed line in XDS.INP | the log quotes the line; fix it in the Full Input File tab |
| `INSUFFICIENT PERCENTAGE OF INDEXED REFLECTIONS` | geometry, spot range or several lattices | chapter 6 |
| `CANNOT OPEN OR READ FILE` for an `.h5` frame | neggia library missing or `LIB=` wrong | Environment screen → Eiger HDF5 reader; regenerate XDS.INP |
| `XDS cannot read the images: N of the M data files ... are missing` | the `_data_00000N.h5` files are not in the same folder as the master file | copy the whole data set together, or point the template at the folder that holds it. The reader follows the links stored in the master file and looks next to the master and nowhere else |
| `NEGGIA ERROR: OPENING FILE RETURNED ERROR CODE: 2` followed by `could not open ... dectris-neggia.so` | same thing: a data file is missing. The library itself is fine — it printed the error | as above; CrystalPilot now says so before the run starts |
| `!!! ERROR !!! MISPLACED PARAMETER` (XSCALE) | keyword in the wrong section of a hand-edited XSCALE.INP | save the parameters again (both save buttons write a correct layout) |
| `XSCALE.INP has no INPUT_FILE= line and no XDS_ASCII.HKL was found` | no CORRECT output yet | run CORRECT, or add inputs with Auto-detect |
| `another program is already running in <folder>` | a run is active there, maybe in another tab | wait or **Stop** |
| `... exceeded the time limit of 240 min and was stopped` | very large data set or slow storage | raise `step_timeout` in `~/.crystalpilot/settings.json` |
| `stopped by the RAM limit - it needed more than N GB` | the run needed more memory than the *RAM (GB)* field allows | raise RAM in the XDS Config panel of the sidebar and run it again (0 = no limit) |
| The computer is slow while XDS runs | the programs use too many cores or too much memory | lower *CPU cores* or *RAM* in the XDS Config panel (chapter 3); they apply from the next run |
| *RAM limit not available here* under the RAM field | no cgroup v2, or CrystalPilot runs neither as root nor in a systemd user session | the CPU limit still works; chapter 3 |
| `CCP4 not found` | CCP4 not installed, not sourced, or installed somewhere CrystalPilot does not search (CCP4 9 is unpacked wherever you like) | Environment screen → CCP4 row: enter the CCP4 folder (or its bin folder) and Save & re-check. It is remembered per computer. Linux: sourcing `ccp4.setup-sh` before starting also works, but only for a start from that same terminal |
| `Not authorised` (403) when scripting | the request lacks the per-launch token | send the token printed in the console as `X-CrystalPilot-Token` or `?token=`; set `XDS_GUI_TOKEN` to fix it |
| `Port already in use` | another CrystalPilot (or program) on the port | the launcher opens the browser on the running one; otherwise change the port |
| Loading screen never switches (Windows) | the server did not start | read the console window; run the wizard again |

## Settings and where they are

| What | Where |
|---|---|
| XDS folder, neggia path, CCP4 folder, parallel on/off, CPU cores, RAM, step time limit | `~/.crystalpilot/settings.json` (per computer; written by the interface) |
| Work mode, cut-off preference | remembered by the browser |
| Per project: run folders, completed steps, last image path | `metadata.json` in the project folder |
| Windows launcher | `windows\crystalpilot.cfg` (runtime, port, install folder, projects, drive letter) |
| Windows runtime | `~/.crystalpilot/config.env` inside the runtime (`PORT`, `PROJECTS_DIR`, `CCP4_SETUP`, `CCP4_WIN`) |
| Logs of a run | `*.LP` in the run folder; `pointless.log`, `aimless.log`, `ctruncate.log`, `XDSCC12.LP`, `AUTOPILOT_RESULTS.json` next to the XDS output |
| Server log (Linux installer) | `~/crystalpilot/server.log` |

## Command line and environment

| Option | Environment variable | Default |
|---|---|---|
| `--port N` | `XDS_GUI_PORT` | 8000 |
| `--host ADDR` | `XDS_GUI_HOST` | 127.0.0.1 (this computer only; `0.0.0.0` for the network) |
| `--projects-dir DIR` | `XDS_GUI_PROJECTS` | `./projects` |
| `--xds-path DIR` | `XDS_GUI_XDS_PATH` | folder of the script |
| `--restrict-browse` | `XDS_GUI_RESTRICT_BROWSE` | off (on: every path the interface lists, reads, runs in or writes stays inside the projects folder) |
| | `XDS_GUI_ALLOWED_HOSTS` | extra host names a server on 127.0.0.1 answers to |
| | `XDS_GUI_SETTINGS`, `XDS_GUI_PARALLEL`, `XDS_GUI_CPU_CORES`, `XDS_GUI_RAM_GB`, `XDS_GUI_STEP_TIMEOUT`, `XDS_GUI_TOKEN`, `NEGGIA` | see the Docs tab |

## Keyboard

| Key | Does |
|---|---|
| `Esc` | closes the open dialog (chart, folder browser, lattice picker) |
| `Ctrl+Enter` (`Cmd+Enter`) | starts **▶ Full Pipeline**, unless the cursor is in a text editor |
| in the folder browser: `Backspace` / `Alt+←` / `Alt+→` / `Enter` | up one level / back / forward / open the typed path or the first matching folder |
| in the frame viewer jump field: `Enter` | go to that frame |
| `Ctrl+K` (`Cmd+K`) | focus the search box in the header, from any tab |
| in the manual: `Ctrl+K` | focus the manual's own search box |

## Security in one paragraph

The server answers only the browser tab that opened it: the page receives a per-launch token as a cookie, and every API call must carry it, so other web sites open in the same browser cannot drive CrystalPilot. By default it listens on this computer only and answers only requests addressed to `localhost`, `127.x.x.x` or `[::1]`, so a web site that points a name of its own at your computer is refused (add names with `XDS_GUI_ALLOWED_HOSTS`). If you start it with `--host 0.0.0.0` for colleagues, anyone who can reach the port can open it: do that on a trusted network and add `--restrict-browse`, which keeps every folder and file the interface lists, reads, runs in or writes inside the projects folder. The only things served without the token are the `/health` check, the manual under `/manual/` and the page's own assets.

## The log file

Everything CrystalPilot prints is also written to `<projects folder>/logs/crystalpilot.log` — the start-up banner and the Environment screen both name the path. It keeps the last three files of 2 MB. After a crash, or a step that stopped without saying why, that file is the first thing to read: on Windows the console window belongs to the launcher and is easy to lose. The API token is replaced in the file, so it can be sent on as it is. `XDS_GUI_LOG=<path>` puts it elsewhere, `XDS_GUI_LOG=off` switches it off.

## Reporting a problem to the author

**⚠ Report a problem** in the header opens a short form. Write what happened and what you expected, then **Save report (.zip)**. The report goes to `<projects folder>/reports/` and holds your text, the program version, what the Environment screen found, the end of the program's log and any errors the page recorded. Tick the box to add the open project's `XDS.INP` and logs — it is off by default because they are your data, and the frames are never included. User names are removed from every path and the API token from every line.

CrystalPilot sends nothing by itself. **Open e-mail** starts your own mail program with the address, a subject and a short message already filled in; attach the saved zip and press send. "What the e-mail will say" shows the message before you open it.

## Getting help

- The **search box in the header** (`Ctrl+K`) searches the Docs sections and this manual at once. Each result shows the sentence that matched with your words highlighted, and opens in its own window, so you can read it beside the work you were doing.

@[Asking the documentation from the header: the answer opens beside your work, the words highlighted.](videos/docs.mp4)
- The **Docs** tab is the reference for every control and file; the **Guide** tab is the short version of this manual. Its own search box works the same way, except that a Docs section is right there and is shown in place.
- The XDS documentation: [xds.mr.mpg.de/html_doc/XDS.html](https://xds.mr.mpg.de/html_doc/XDS.html); the XDSwiki for processing advice.
- When reporting a problem, include the log of the failing step (LP Viewer → the step), the `XDS.INP`, and the Environment screen's summary.
