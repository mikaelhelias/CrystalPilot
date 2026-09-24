# CrystalPilot interface map and test coverage

Every user-visible ability of the program, the server routes behind it, and
which part of the regression battery exercises it. "U" = `test_units.py`,
"A" = `api/api_tests.sh` sections 1-4, "S" = `api/sweep.sh` (section 5),
"B" = `ui/ui_pass.js` (browser pass). The route-coverage check in
`test_units.py` fails if a server route exists that none of these mention.

## Header and project sidebar

| Ability | Routes | Tests |
|---|---|---|
| Project list, create, open, delete (files or list only) | `GET/POST /api/projects`, `GET /api/projects/<n>`, `DELETE /api/projects/<n>` | A (create, encoded names, corrupt metadata), S (create/delete), B (open) |
| Percent-encoded and unusual project names, traversal refused | all project routes via `_pdir` | U, A |
| Open project / output folder in Explorer, Windows-view paths | `POST /api/open-folder`, `/api/config` (projects_drive) | S (dry run), U (`_windows_view` config) |
| XDS path "Set", parallel toggle, persisted settings | `POST /api/config` | S, U (config defaults), U (no undefined onclick) |
| Environment / first-launch screen, About, splash | `GET /api/environment`, `/health`, `/assets/*` | S, A (health readable by loading screen), B (envCheck) |
| Loading screen hand-over (Windows launcher) | `/health` with CORS | A section 2 |

## Data Processing tab

| Ability | Routes | Tests |
|---|---|---|
| Key-parameter editor (ranges, cell, SG, toggles, protected keys, multi-keyword lines) | `POST .../xdsinp/params`, `GET/POST .../xdsinp` | U (real XDS.INP round trip, lists, comments), A section 4 (subset ranges), S (first save in a new project: loaded file's geometry kept / standard axes, real XYCORR) |
| Generate XDS.INP from frame header | `GET .../generate-xdsinp` | U (generator from Eiger header), S |
| Run folder: overwrite / sub-folder, auto-number, copy XDS.INP | `POST /api/run-folder`, `/api/run-folder/list` | S |
| Run one step / from step / pipeline, live log, Stop | `GET /api/stream`, `POST /api/stop`, `/api/run` | A (fake xds: stop kills tree, timeout, concurrency, JSON errors), A section 4 (real XYCORR..CORRECT), S (reruns) |
| LP viewer + parsed metrics for every step, charts | `GET .../lp/<step>`, `.../metrics/<step>` | U (real LP parsers), S (all 7 steps), B (CORRECT and IDXREF charts drawn) |
| Run history and comparison (previous runs, uploaded file) | `GET .../history-{correct,idxref,xscale}`, `.../compare-{correct,idxref,xscale}`, `POST .../compare-*-file` | S (after reruns produce .prev1), B (history modal) |
| Matthews calculator | `GET .../matthews` | A section 4, U (formula) |
| CSV export of statistics | `GET .../export-data/{correct,integrate}` | S |
| IDXREF cell / space-group picker, apply SG from POINTLESS | `POST .../xdsinp/params` | U (editor), B (no undefined handlers) |
| Auto-indexing (quick / medium / full tiers) | `GET /api/autoindex/stream`, `.../autoindex-cached`, `POST /api/autoindex/stop` | S (quick tier on real frames) |
| File and folder browser, drives under WSL | `GET /api/ls` | A (restrict), S |

## Frame Viewer tab

| Ability | Routes | Tests |
|---|---|---|
| Render CBF / HDF5 frames, contrast, colour map, frame stepping | `GET /api/frame`, `/api/h5/nframes`, `/api/frames/list` | S (real master file PNG, frame count, file list), B (frame rendered, rings toggled) |
| Header extraction, geometry from XDS.INP, spot overlay | `GET /api/fv-xdsinp`, `/api/fv-spots` | S, U (`_h5_find_master`, header units) |
| Remembered image path per project, recent list | `POST .../settings` | S |
| Missing Python packages banner / installer | `GET /api/deps`, `/api/deps/install` | S (deps); install excluded on purpose (side effects) |

## XSCALE tab

| Ability | Routes | Tests |
|---|---|---|
| Key parameters, "Update", "Save new", full-text editor | `POST .../xscaleinp/params`, `GET/POST .../xscaleinp` | U (writer layout on real files, broken fixture repaired), A section 1 (Save new resolves the run-folder HKL), S |
| Auto-detect HKL files, sub-folders, run modes | `GET /api/xscale-detect-hkl`, `.../xscale-subfolders`, `POST /api/xscale-run-folder` | A, S |
| Run XSCALE, LP viewer, metrics, resolution cut-off | `GET /api/xscale/stream`, `.../xscalelp` | A section 3 and 4 (real), S (rerun), B (LP charts) |

## XDSCONV tab

| Ability | Routes | Tests |
|---|---|---|
| Parameters, full text, run, f2mtz + cad, gemmi fallback | `GET/POST .../xdsconvinp`, `GET /api/xdsconv/stream`, `.../xdsconvlp`, `GET /api/gemmi-mtz/stream`, `/api/gemmi/install` | A section 4 (real, MTZ created), S, B; gemmi install excluded |

## POINTLESS / AIMLESS tabs

| Ability | Routes | Tests |
|---|---|---|
| CCP4 detection, run POINTLESS, parse and cache, logs, anisotropy | `GET /api/ccp4check`, `/api/pointless/stream`, `.../pointless-log(-raw)`, `.../pointless-cached`, `.../anisotropy-analyze` | A section 4 (real), S, U (harvested log parses), B |
| Run AIMLESS (+POINTLESS, +CTRUNCATE), charts, tables, logs | `GET /api/aimless/stream`, `.../aimless-log(-raw)`, `.../ctruncate-log`, `.../aimless-cached` | A section 4 (real), S, U (harvested logs), B (charts drawn) |

## ΔCC½ (XDSCC12) tab

| Ability | Routes | Tests |
|---|---|---|
| Binary check, download, run, results, apply exclusions | `GET /api/xdscc12/check`, `/api/xdscc12/stream`, `.../xdscc12-results`, `.../xdscc12-lp`, `/api/xdscc12/download` | S (check, results, lp), A section 4 (run when installed), B; download excluded |

## AutoPilot tab

| Ability | Routes | Tests |
|---|---|---|
| Automated pipeline with retries, status, cached results, stop | `GET /api/autopilot/stream`, `/api/autopilot/status`, `.../autopilot-cached`, `POST /api/autopilot/stop` | S (full real run on the 60-frame project: ap_done with success, results file, cached results; `CP_SKIP_AUTOPILOT=1` to skip), U (autopilot helpers use the process helper), B (results panel shows the run) |
| Auto import of frame information (header read from the real master file) | `GET .../generate-xdsinp`, `/api/fv-xdsinp`, `/api/h5/nframes` | S (generated XDS.INP carries the header's wavelength, detector size, distance, oscillation), U (generator, `_h5_find_master`, unit heuristics) |

## Table 1 and gemmi tabs

| Ability | Routes | Tests |
|---|---|---|
| Table 1 assembly, export (xlsx/TSV/LaTeX) | `GET .../table1data`, `POST .../export-table1` | S, B (statistics rendered) |
| gemmi merging statistics, completeness, lattice symmetry, anomalous, deposition, polarization, LP stats | `POST /api/gemmi/{analyze,anomalous,deposition,polarization}`, `GET /api/gemmi/lp-stats` | S, B |

| Publication figures from a shell table (CORRECT or XSCALE): four metrics as PNG + PDF and a four-panel overview, written next to that log, name carries the source, axis linear in 1/d², the program's own cut-off and detected ice rings drawn in | `POST /api/figures`, `GET /api/figure?project=&name=` | U (writer on the real fixture, the cut-off/axis rules, name guard), S, B (button writes and serves them) |
| Any chart saved as a PNG from the expanded view, at a fixed size | `chartModalPng` | B |
| Export a project as one zip (inputs, logs, reflection files, figures, reports; never frames, correction images, SPOT.XDS or rotated logs), download guarded to this project's own archive | `POST /api/export`, `GET /api/export?project=&name=` | U (contents, name guard), S, B |
| Everything printed also goes to a rotating log in the projects folder; the API token is redacted on the way | `_LogTee`, `_start_logging`, `XDS_GUI_LOG` | U (redaction, rotation), S (written, no token) |
| A feature is disabled when its module is missing, instead of failing on the click | `/api/environment` `modules`, `_figuresGate` | U, B |
| Report a problem to the author: description, version, environment, log tail, page errors, optional project files; user names and the token removed; nothing sent by the program (a zip plus the user's own mail program) | header button, `POST /api/bug-report`, `GET /api/bug-report?name=`, `REPORT_EMAIL` / `XDS_GUI_REPORT_EMAIL` | U (redaction, contents, mail-link length, name guard), S, B |

| Batch processing: discover data sets in a folder, one project each, a strategy (indexing fallback, GXPARM re-integration never/always/only if better, fixed space group and cell, ice rings, ΔCC½, limits) driving AutoPilot, a resumable queue, a comparison table, a merge with an XSCALE.INP built from the consistent data sets | Batch tab, `/api/batch/*` | U (strategy, discovery, merge layout, the better-judgement), W (every data set processed, failure carries on, stop/resume, if_better restores), S (real data: discover, create, start, skip, stop, XDS.INP from headers, log, merge plan), B |

## Guide / Docs tabs

Static content: B (no JavaScript errors when shown).

| Ability | Where | Tests |
|---|---|---|
| Documentation search: ranked over the Docs sections and the manual index, every term marked, the matching sentence shown | header Ask bar (`Ctrl+K`), Docs-tab box | B (ranking, context, window), U (one engine) |
| A hit opens in its own window: the manual at its anchor with `?q=`, a Docs section as a standalone page | `cpdsOpenHit` / `cpdsOpenDocs` | B |

## Cross-cutting

| Concern | Tests |
|---|---|
| Programs run in their own process group; Stop and timeouts kill children | U (`_run_streaming`), A |
| Per-launch token, cookie, no CORS, localhost bind | A section 2 |
| File locations (`_pfile/_pout/_project_out_dir`), `locations` report | A section 4, S |
| Lenient decoding of program output, JSON errors instead of tracebacks | A section 1 |
| Build integrity, JS syntax, undefined handlers, duplicate ids | run_all, U |
| A failed or stopped attempt never passes an old log off as its output, and never hides it either: the LP moved aside comes back when nothing new was written (LP viewer, metrics, history keep the last good CORRECT.LP) | R (`test_failed_process_cannot_reuse_old_output_but_leaves_it_readable`), W (`test_failed_rerun_keeps_the_last_good_log_readable`), B (DP tab) |
| A stream route refused before work starts tells an EventSource why (terminal error event); a script gets the 404 | W (`test_invalid_requests_fail_before_starting_work`), A section 2 |

## Not covered (by design or not yet)

- `/api/deps/install`, `/api/gemmi/install`, `/api/xdscc12/download`: they install software; excluded from automated runs.
- A full AutoPilot run: available behind `CP_REAL_AUTOPILOT=1` (slow).
- Windows wizard end to end (WSL runtime import, real install): manual procedure (see the 2026-09-05 session notes); run_all checks that wizard.ps1, launch.ps1 and CrystalPilot-Uninstall.ps1 parse and that the wizard renders its five pages (-Preview). The installer .exe (windows/make_installer.py, IExpress) is checked by unpacking it and running its bootstrap with -Preview.
- Visual correctness of charts (values, labels): the browser pass checks that charts are drawn and that no script fails, not what they show.

Known limitations as of 0.6.7b (2026-09-23):

- RAM limit: needs cgroup v2 and either root (WSL: tested, own cgroup `crystalpilot-jobs`) or a systemd user session (`systemd-run --user --scope`: not yet tried on a real non-root Linux desktop; the WSL Ubuntu has no normal user to test it with).
- AutoPilot screw axes (`_ap_sg_from_absences`): enantiomorphs (P4₁/P4₃, P3₁/P3₂, P6₁/P6₅) cannot be told apart by absences - the first is kept and the log names the other; with too few axial reflections XDS's space group is kept. Verified on OdoL_7 only (C222 -> C222₁).
- Raster scans (`_is_raster_scan`): recognised by name only (a folder with "raster" in the last three path parts, or "raster" in the file name - NSLS-II FMX naming); other beamlines' raster scans are listed as ordinary, ticked data sets.
- ΔCC½ (XDSCC12): skipped by the API suite because XDSCC12 is not installed in the test WSL.
- The 0.6.7 / 0.6.7b Windows installers were built and checked (`-Preview`, parse), not run on a clean Windows machine.
- The manual's videos play only in the HTML manual; the PDF shows a still frame. Media cannot be checked in the Browser pane while it is hidden: test playback headless.
