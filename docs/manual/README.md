# CrystalPilot illustrated manual

Source of the user manual: one Markdown file per chapter in `chapters/`,
screenshots in `images/`, built into a single self-contained HTML file and a
PDF.

```bash
# from the repository root
python docs/manual/build_manual.py              # chapters + images -> CrystalPilot-Manual.html + .pdf
python docs/manual/build_manual.py --capture    # re-take every screenshot first (about 12 minutes)
python docs/manual/build_manual.py --capture 07-03-correct-metrics 11-03-xscale-lp   # only these shots
```

`--capture` starts the same processed test project the regression battery
uses (`files/tests/api/api_tests.sh` with the real chain on the 60-frame data
set, kept alive with `CP_KEEP_SERVER=1`), drives the interface in headless
Edge with `capture.js`, outlines the controls being described (numbered red
markers) and saves cropped PNGs. Every screenshot is therefore reproducible
and can be refreshed for each release.

The Windows installer pictures come from the wizard's own preview renderer:

```powershell
powershell -ExecutionPolicy Bypass -File windows\wizard.ps1 -Preview docs\manual\images\wizard
```

The application serves the built manual at `/manual/CrystalPilot-Manual.html`
and `.pdf` when this folder sits next to the application file (or in the source
tree layout); the Docs tab links to it.

Conventions for chapters: task first (what you want to achieve), numbered
steps naming the buttons exactly as labelled, one screenshot per step group
with a caption that says what to look at, then "What to look for" and "If it
goes wrong". Every chapter is written at **Expert** work mode so that every
option is visible; the work-mode chapter says which options disappear at
lower levels.

## Search

- Inside the manual: the box at the top of the side bar (or Ctrl+K) lists the sections that contain every word typed; a click scrolls there and highlights the words. `CrystalPilot-Manual.html?q=words#anchor` opens the manual with that search and highlight, which is how the app's Docs search links into it.
- Inside CrystalPilot: the search box at the top of the Docs tab searches the Docs sections and the manual. The manual part comes from `CrystalPilot-Manual.index.json` (one entry per heading, plain text, written by `build_manual.py` next to the HTML and served at `/manual/CrystalPilot-Manual.index.json`); without that file the Docs search still covers the Docs sections. The 📖 Manual button in the header appears when the manual is installed.

## Cover and colophon

The cover is the program's loading screen: `build_manual.py` renders `windows/splash.html?demo=<version>` with headless Edge/Chrome to `images/00-loading-screen.png` and takes the name, subtitle and credit line from that same file; the version comes from `files/src/config.py`. Change the text in `splash.html` or bump `VERSION` and the launcher and the manual agree after the next build. The colophon at the end states that the manual was written with Anthropic Claude Fable 5.1 (`WRITTEN_WITH` in `build_manual.py`).
