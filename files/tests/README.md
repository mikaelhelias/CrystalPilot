# CrystalPilot regression battery

Run before every build hand-over, from the `files` folder:

```bash
py -3 tests/run_all.py --same --api --real
```

`--same` rebuilds the newest `xds-gui-vNNN.py` in place (omit it to build the
next number), `--api` runs the Linux-side suite inside WSL, `--real` adds a
real `xscale_par` run on a copy of the project named `test` (the original is
never modified). The run ends with `READY: xds-gui-vNNN.py` or `NOT READY`.

The full check, to run before any hand-over that touched runner, handler,
generator, editor or the frontend's run controls:

```bash
py -3 tests/run_all.py --same --api --real-xds
```

`--real-xds` runs the whole chain with the real programs on a subset of the
frames the `test` project points to (default 60 frames, `CP_REAL_XDS_RANGE`
to change; `CP_REAL_PROJECT` for another project): XYCORR through CORRECT,
then XSCALE, XDSCONV with f2mtz/cad, POINTLESS, AIMLESS and CTRUNCATE (when
CCP4 is set up), the gemmi MTZ conversion and XDSCC12 (when installed). Every
program must report "completed" and its output must be picked up by the
parsers. Expect 10 to 20 minutes when the frames are on a network share.

| Stage | What it proves |
|-------|----------------|
| build, py_compile | the single file assembles and parses |
| pyflakes (if installed) | no undefined names |
| JS syntax | every inline script of the frontend parses |
| `test_units.py` (32 checks) | XSCALE.INP writer layout on real files, XDS.INP editor round trip of a real beamline file, LP parsers on real CORRECT/IDXREF/INTEGRATE/COLSPOT/INIT output, generator, reflection-file detection, name validation, process helper (stream, timeout, same-folder guard), project metadata safety, config defaults, no undefined onclick handlers or duplicate ids in the page |
| `test_review_fixes.py` (22 tests, included by default) | Real HTTP authorization and exact routes, encoded-name list removal retaining files, directory ownership, process cancellation and output freshness, AutoPilot folder/status/stop behavior, editing, dataset identity, saved CCP4 settings, build verification, Bash configuration round trips, and symmetry-equivalent FreeR assignments with preserved reference flags. Gemmi/NumPy and Linux-specific cases explicitly skip when unavailable. |
| `--review-ui` | Playwright checks literal project text, action callbacks for apostrophes, and XSCALE saves that preserve unchanged dataset-specific settings. Requires Node, Playwright and Edge; `CP_BROWSER` can select another Chromium executable, and `NODE_PATH` can point to an existing Playwright installation. |
| `test_workflows.py` (19 tests, included by default) | HTTP-to-process workflows: full XDS/XSCALE/XDSCONV/f2mtz/cad orchestration, AutoPilot, quick auto-indexing, external run folders, cancellation/retry, timeout, invalid requests, failed reruns, stale conversion outputs, and input/metadata/cache persistence failures. |
| `api/api_tests.sh` (34 checks) | live server: percent-encoded names, traversal 400, JSON errors, corrupt metadata, non-UTF-8 LP, Stop kills the whole process tree, step timeout, concurrent-run refusal, XSCALE "Save new" writes a valid file with the project's HKL, token/cookie/CORS rules, `/health` readable by the loading screen, and the real XSCALE run |

The complete battery, with the endpoint sweep and the browser pass:

```bash
py -3 tests/run_all.py --same --api --real-xds --ui
```

After the real chain it calls every remaining server route on the fresh
outputs (`api/sweep.sh`: history and comparison after reruns, exports, Table 1,
gemmi analyses, run folders, auto-indexing quick tier, a full AutoPilot run,
the header-derived XDS.INP generation, project delete, and more) and then
drives the real interface in headless Edge (`ui/ui_pass.js`):
every main tab is opened, the LP charts, XSCALE/XDSCONV logs, frame viewer on
the real master file, CCP4 panels, Table 1 and history are triggered, and any
JavaScript exception, blank chart or unrendered frame fails the run.
Screenshots land in `tests/ui/out/`. `INTERFACE_MAP.md` lists the program's
abilities and related test references. The route inventory checks textual
references only; it does not prove that each route or failure path executes.

## Fixtures

The workflow suite uses `fixtures/workflow_tool.py` as a deterministic external
program. It runs in a real subprocess and supplies existing LP fixtures, while
the actual server, runner, editor, parsers, job registry and metadata code execute.
Its HKL/MTZ outputs are test stand-ins, not scientifically validated data.
These tests complement the real-program checks; they do not replace validation
from diffraction images or numerical comparisons of processing results.

Run the workflow suite independently with:

```bash
python tests/test_workflows.py /absolute/path/to/xds-gui-v344.py
```

Tests create scratch projects and a server on an OS-assigned localhost port.
Stop requests target only test-owned jobs. On Windows the process tests need
permission to run `taskkill` on their own child processes.

`fixtures/` holds real files from a processed Eiger data set: the XDS.INP
CrystalPilot generated, the LP files of every step, and the XSCALE.INP the old
"Save new" button wrote (the one that produced MISPLACED PARAMETER). When a
bug is found in production, copy the file that triggered it here and add a
check that fails on the old behaviour before fixing.

## Adding a check

`test_units.py`: add a function under `define_checks` decorated with
`@check("name")`; raise `AssertionError` with a useful message on failure.
`api/api_tests.sh`: use `check "name" "shell test" "text shown on failure"`.

## The illustrated manual

`docs/manual/build_manual.py` builds `CrystalPilot-Manual.html/.pdf` and the search index from `docs/manual/chapters/*.md` and `images/`. `--capture` re-takes the screenshots: it starts this battery's real-chain server with `CP_REAL_IMPORT=test CP_SKIP_RERUNS=1 CP_SKIP_AUTOPILOT=1` (the finished results of project `test` are imported, only XDSCONV / POINTLESS / AIMLESS / gemmi run) and drives `capture.js`. The battery checks that `/manual/`, the HTML and the index are served, that the Docs-tab search finds Docs and manual hits, and that the header Manual button appears (sweep.sh, ui_pass.js). Details in `docs/manual/README.md`.
