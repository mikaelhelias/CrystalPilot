# -*- coding: utf-8 -*-
"""Regenerate the in-app Docs and Quick Guide tabs of CrystalPilot from structured content.

Replaces the <div id="main-tab-docs"> and <div id="main-tab-guide"> blocks in
files/src/frontend.html (ranges found by parsing, not by line numbers).
"""
import html as H
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

SRC = Path(r"F:\app\crystal_pilot\files\src\frontend.html")
VERSION = re.search(r'VERSION = "([^"]+)"', Path(r"F:\app\crystal_pilot\files\src\config.py").read_text(encoding="utf-8")).group(1)

# ── tiny HTML helpers (same look as the existing cards) ──────────────────────
BODY = "font-family:'DM Sans',var(--mono),sans-serif; font-size:0.84rem; color:var(--txt2); line-height:1.85;"
def P(t): return '<p style="margin:0 0 10px 0;">%s</p>' % t
def B(t): return '<b style="color:var(--txt);">%s</b>' % t
def C(t): return '<code style="color:var(--accent2);">%s</code>' % H.escape(t)
def A(url, t=None): return '<a href="%s" target="_blank" rel="noopener" style="color:var(--accent);">%s</a>' % (url, t or url)
def SUB(t): return '<div style="font-family:var(--head); font-size:0.78rem; font-weight:700; letter-spacing:0.15em; text-transform:uppercase; color:var(--accent2); margin:14px 0 6px 0;">%s</div>' % t
def UL(items): return '<div style="margin:0 0 10px 0;">' + ''.join('<p style="margin:0 0 4px 8px;">&bull; %s</p>' % i for i in items) + '</div>'
def NOTE(t, color="var(--accent)"): return '<div style="margin:10px 0; padding:10px 14px; background:rgba(99,179,237,0.07); border-left:3px solid %s; border-radius:0 6px 6px 0;">%s</div>' % (color, t)
def WARN(t): return NOTE(t, "#f6ad55")
def PRE(t): return '<pre style="margin:0 0 10px 0; padding:10px 12px; background:rgba(0,0,0,0.25); border:1px solid var(--border); border-radius:6px; font-family:var(--mono); font-size:0.78rem; color:var(--txt); overflow-x:auto; white-space:pre;">%s</pre>' % H.escape(t)
def TABLE(head, rows, widths=None):
    th = ''.join('<th style="text-align:left; padding:6px 8px; color:var(--accent2); font-weight:600; border-bottom:1px solid var(--border2);%s">%s</th>' % ((' width:%s;' % widths[i]) if widths else '', h) for i, h in enumerate(head))
    trs = ''.join('<tr style="border-bottom:1px solid var(--border);">' + ''.join('<td style="padding:5px 8px; vertical-align:top;">%s</td>' % c for c in r) + '</tr>' for r in rows)
    return '<div style="overflow-x:auto; margin:0 0 10px 0;"><table style="width:100%%; border-collapse:collapse; font-size:0.8rem;"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (th, trs)

SECTIONS = []   # (id, title, html)
def section(sid, title, *parts): SECTIONS.append((sid, title, ''.join(parts)))

XDSDOC = "https://xds.mr.mpg.de/html_doc/"
# ═════════════════════════════════════════════════════════════════════════════
section("doc-manual", "Illustrated manual",
    P("A step-by-step manual with screenshots of every task (installing, setting up a project, indexing, integrating, reading the results, "
      "space group, scaling, MTZ export, AIMLESS, AutoPilot, gemmi, Table 1, frame viewer, troubleshooting) is shipped as one HTML page and a PDF in the "
      + C("docs/manual") + " folder next to the application."),
    '<div id="doc-manual-links" style="margin:6px 0 10px 0;"><span style="color:var(--txt3);">Checking whether the manual is installed&hellip;</span></div>'
    '<script>(function(){ try { fetch("/manual/").then(function(r){ return r.json(); }).then(function(d){ var el = document.getElementById("doc-manual-links"); if (!el) return; '
    'if (d && d.available) { var hb = document.getElementById("manual-btn"); if (hb) hb.style.display = ""; el.innerHTML = \'<a class="btn-primary" href="/manual/CrystalPilot-Manual.html" target="_blank" rel="noopener" style="display:inline-block; padding:8px 16px; border-radius:8px; text-decoration:none; margin-right:8px;">&#128214; Open the illustrated manual</a>\' + (d.pdf ? \'<a class="btn-secondary" href="/manual/CrystalPilot-Manual.pdf" target="_blank" rel="noopener" style="display:inline-block; padding:8px 16px; border-radius:8px; text-decoration:none;">&#11015; PDF</a>\' : "") + \'<div style="font-size:0.75rem; color:var(--txt3); margin-top:6px;">Folder: \' + (d.folder || "") + "</div>"; } '
    'else { el.innerHTML = \'<span style="color:var(--txt3);">Not installed here. The manual is in the <code>docs/manual</code> folder of the CrystalPilot package; open <code>CrystalPilot-Manual.pdf</code> from there, or rebuild it with <code>python docs/manual/build_manual.py</code>.</span>\'; } }).catch(function(){}); } catch (e) {} })();</script>',
    P("This Docs tab is the reference: what every control and file does. The manual shows how to do things, in order, with pictures. "
      "The search box in the " + B("header") + " (" + C("Ctrl+K") + ") searches both from any tab: each result carries the sentence that matched with your "
      "words highlighted, and opens in its own window. The box at the top of this tab searches the same way, except that a Docs section is "
      "shown here, in place, with the words highlighted; only manual hits open a window. "
      "Inside the manual, the box in the side bar (Ctrl+K) searches its sections. The &#128214; Manual button in the header opens it directly."),
)

section("doc-overview", "Overview",
    P(B("CrystalPilot") + " is a browser-based interface for macromolecular diffraction data processing built around " + B("XDS") +
      " (W. Kabsch, MPI Heidelberg). It is one Python file that runs a small local web server; the interface opens in your normal browser. "
      "The core (projects, running XDS / XSCALE / XDSCONV, editing input files, live logs, statistics) needs only the Python standard library. "
      "The frame viewer and the gemmi analyses use a few scientific Python packages, and the CCP4 steps use a CCP4 installation."),
    P("What it drives, in the order of a typical processing session:"),
    TABLE(["Tab", "Programs", "What you get"], [
        ["Data Processing", "XDS (XYCORR &rarr; INIT &rarr; COLSPOT &rarr; IDXREF &rarr; DEFPIX &rarr; INTEGRATE &rarr; CORRECT)", "XDS.INP editor, generation from frame headers, run folders, live log, LP viewer with parsed metrics and charts, run history and comparison, Matthews calculator, resolution cut-off estimates, auto-indexing trials"],
        ["Frame Viewer", "&mdash;", "CBF / HDF5 (Eiger) / SMV / OSC / TIFF frames with contrast, zoom, magnifier, resolution and ice rings, SPOT.XDS overlay, image export"],
        ["XSCALE", "xscale_par", "Scaling and merging of one or more data sets, autofill from CORRECT, statistics and cut-offs"],
        ["XDSCONV", "xdsconv, f2mtz + cad (CCP4) or gemmi", "Conversion to CCP4 / MTZ, SHELX, XtalView with free-R flags"],
        ["POINTLESS", "pointless (CCP4)", "Laue and space group determination, one-click apply to XDS.INP and re-run CORRECT"],
        ["AIMLESS", "pointless, aimless, ctruncate (CCP4)", "Independent scaling, per-shell and per-batch statistics, amplitudes and twinning tests, comparison with XDS"],
        ["&Delta;CC&frac12;", "xdscc12 (K. Diederichs)", "Per-frame &Delta;CC&frac12;, suggested frame exclusions, apply and re-run CORRECT"],
        ["AutoPilot", "all of the above", "Fully automated pipeline with error diagnosis, retries, cut-off selection and MTZ output"],
        ["gemmi", "gemmi (Python)", "Merging statistics, completeness, lattice symmetry, anomalous scattering factors, deposition CIF, polarization check"],
        ["Statistics", "&mdash;", "Publication Table 1 from XSCALE.LP or CORRECT.LP with TSV, LaTeX and CSV export"],
    ], ["16%", "26%", "58%"]),
    P("Everything happens inside a " + B("project") + ": a folder that holds the input files you edit, the results, and a small metadata file. "
      "The interface remembers, per project, where the last XDS, XSCALE and XDSCONV runs wrote their output, so viewers, comparisons and downstream programs always find the right files (see section 6)."),
    SUB("The header and the keyboard"),
    P("Top right: " + B("&#11041; Check Connection") + " (is the server answering?), " + B("&#9881; Environment") + " (what was found on this computer, section 8), "
      + B("&#128214; Manual") + " (the illustrated manual, when installed), and the version badge, which opens the About panel. "
      + "Keys: " + C("Esc") + " closes any dialog (chart, file browser, lattice picker); " + C("Ctrl+Enter") + " (Cmd+Enter) starts " + B("Full Pipeline") + " unless the cursor is in a text editor; "
      + "in the folder browser " + C("Backspace") + " goes up, " + C("Alt+&larr;") + " / " + C("Alt+&rarr;") + " back and forward, " + C("Enter") + " in the path field opens the typed path; in the manual " + C("Ctrl+K") + " focuses the search box."),
    P("CrystalPilot runs natively on Linux and macOS. On Windows it runs inside the Windows Subsystem for Linux, installed and started by the provided wizard; the interface and the Windows drives are used exactly as on Linux (section 22)."),
)

section("doc-requirements", "Requirements",
    SUB("Required"),
    UL([B("Python 3.7 or newer") + " (the server itself uses only the standard library).",
        B("XDS") + " &mdash; the complete package: " + C("xds_par") + " / " + C("xds") + ", " + C("xscale_par") + " / " + C("xscale") + ", " + C("xdsconv") + " and the helper programs " + C("forkxds") + ", " + C("mcolspot") + ", " + C("mintegrate") + " that xds_par calls. Free for academic use from " + A("https://xds.mr.mpg.de", "xds.mr.mpg.de") + "; CrystalPilot cannot redistribute it.",
        "A current browser (Chrome, Edge, Firefox, Safari)."]),
    SUB("Needed for Eiger / HDF5 data"),
    UL([B("dectris-neggia") + " (" + C("dectris-neggia.so") + ") &mdash; the reader library XDS loads through " + C("LIB=") + " to read " + C(".h5") + " frames. Free from " + A("https://github.com/dectris/neggia/releases", "DECTRIS on GitHub") + ". CrystalPilot finds it next to the XDS binaries or where you point it in the Environment screen, and writes the " + C("LIB=") + " line for you."]),
    SUB("Optional"),
    UL([B("Python packages") + " " + C("numpy") + ", " + C("matplotlib") + ", " + C("h5py") + ", " + C("hdf5plugin") + ", " + C("fabio") + " for the frame viewer and header reading, and " + C("gemmi") + " for the gemmi tab and the MTZ fallback. The Linux installer and the Windows wizard install them; the Environment screen can install them later.",
        B("CCP4") + " for POINTLESS, AIMLESS, CTRUNCATE and the f2mtz / cad MTZ export. On Windows an installed CCP4 for Windows is used through a small bridge (section 22).",
        B("XDSCC12") + " for the &Delta;CC&frac12; tab; the tab can download the Linux or macOS binary for you."]),
)

section("doc-install", "Installation and start-up",
    SUB("Linux (installer)"),
    P("Put " + C("xds-gui-vNNN.py") + " and " + C("install-linux.sh") + " in one folder and run " + C("bash install-linux.sh") + ". The script creates a private Python environment, finds XDS, neggia and CCP4, installs a " + C("crystalpilot") + " command and a desktop entry, and starts CrystalPilot once. "
      "Afterwards: " + C("crystalpilot") + " (start and open the browser), " + C("crystalpilot fg") + " (in the terminal), " + C("crystalpilot stop") + ", " + C("crystalpilot status") + ", " + C("crystalpilot log") + ". Options: " + C("--prefix DIR") + ", " + C("--projects DIR") + ", " + C("--xds DIR") + ", " + C("--neggia FILE") + ", " + C("--ccp4-setup FILE") + ", " + C("--port N") + ", " + C("--no-launch") + ", " + C("--system-python") + "."),
    SUB("Windows (wizard)"),
    P("Double-click " + C("CrystalPilot-Setup.bat") + ". The wizard enables the Windows Subsystem for Linux if needed (it says so first, with the disk footprint), uses an existing Ubuntu or creates a dedicated runtime on the disk you choose, asks for the projects folder, picks up the XDS package and neggia from your Downloads, sets up CCP4 (Linux tarball, existing Linux CCP4, or CCP4 for Windows through a bridge), and creates desktop shortcuts. Afterwards start CrystalPilot from the " + B("CrystalPilot") + " shortcut; a loading screen opens and switches to the interface when the server is ready. Details in section 22."),
    SUB("Manual start (any platform with Python)"),
    PRE("python3 xds-gui-v%s.py                       # http://127.0.0.1:8000\n"
        "python3 xds-gui-vNNN.py --port 9000 --xds-path /opt/xds --projects-dir ~/data/projects\n"
        "python3 xds-gui-vNNN.py --help" % "NNN"),
    P("The server listens on " + B("127.0.0.1:8000") + " by default, i.e. only for browsers on the same computer. To use it from another machine start it with " + C("--host 0.0.0.0") + " (anyone who can reach the port can then open the interface, so do that on a trusted network only). "
      "The projects folder is " + C("./projects") + " next to where you started it unless " + C("--projects-dir") + " or " + C("XDS_GUI_PROJECTS") + " says otherwise."),
    SUB("First launch"),
    P("The first time the interface opens it shows the " + B("Environment") + " screen: what was found (XDS, xds_par, neggia, CCP4, Python packages), download links and path fields for anything missing, and the projects folder. It comes back when the situation changes, and is always available from the About panel (click the version in the header). See section 7."),
    SUB("Updating"),
    P("Replace the application file with the newer " + C("xds-gui-vNNN.py") + " and restart. On Linux run the installer again or copy the file to " + C("~/crystalpilot/app/crystalpilot.py") + ". On Windows the launcher copies the newest " + C("files\\xds-gui-v*.py") + " into the runtime every time it starts, and the wizard can be run again at any time; projects and settings are kept."),
)

section("doc-cli", "Command line, environment variables and settings",
    P("Precedence: command-line option &gt; " + B("settings file") + " &gt; environment variable &gt; built-in default."),
    TABLE(["Option", "Environment variable", "Default", "Meaning"], [
        [C("--port N"), C("XDS_GUI_PORT"), "8000", "TCP port"],
        [C("--host ADDR"), C("XDS_GUI_HOST"), "127.0.0.1", "Interface to listen on (" + C("0.0.0.0") + " = every interface)"],
        [C("--projects-dir DIR"), C("XDS_GUI_PROJECTS"), "./projects", "Folder that holds all projects"],
        [C("--xds-path DIR"), C("XDS_GUI_XDS_PATH"), "folder of the script", "Folder with xds_par, xscale_par, xdsconv"],
        [C("--restrict-browse"), C("XDS_GUI_RESTRICT_BROWSE"), "off", "Keep every folder and file the interface lists, reads, runs in or writes inside the projects folder (file browser, frame viewer, run folders, input files, AutoPilot)"],
        ["&mdash;", C("XDS_GUI_ALLOWED_HOSTS"), "&mdash;", "Extra host names a server on 127.0.0.1 answers to, comma-separated (it answers localhost, 127.x.x.x and [::1] only)"],
        ["&mdash;", C("XDS_GUI_SETTINGS"), C("~/.crystalpilot/settings.json"), "Where the interface stores what you set in it"],
        ["&mdash;", C("XDS_GUI_PARALLEL"), "1", "Use xds_par / xscale_par (0 = serial binaries)"],
        ["&mdash;", C("XDS_GUI_STEP_TIMEOUT"), "14400 s", "Time limit for one program run; the run and its children are stopped when exceeded"],
        ["&mdash;", C("XDS_GUI_CPU_CORES"), "4", "CPU cores the programs may use, all runs together"],
        ["&mdash;", C("XDS_GUI_RAM_GB"), "16 (at most &frac34; of the RAM)", "RAM in GB the programs may use, all runs together (0 = no limit)"],
        ["&mdash;", C("XDS_GUI_TOKEN"), "random per launch", "Fixes the API token (section 5) for scripted access"],
        ["&mdash;", C("NEGGIA"), "&mdash;", "Path of dectris-neggia.so if it is not next to XDS"],
        ["&mdash;", C("CBIN") + ", " + C("CCP4_BIN") + ", " + C("CCP4"), "&mdash;", "Where to look for CCP4 programs (otherwise PATH and the usual folders)"],
        ["&mdash;", C("HDF5_USE_FILE_LOCKING"), "FALSE", "Set by CrystalPilot unless you set it: HDF5 locks fail on network shares"],
        [C("--version"), "&mdash;", "", "Print the version"],
    ], ["17%", "22%", "17%", "44%"]),
    SUB("The settings file"),
    P(C("~/.crystalpilot/settings.json") + " holds what you set in the interface, per computer: " + C("xds_path") + ", " + C("neggia_lib") + ", " + C("ccp4_bin") + ", " + C("parallel") + " (true/false), " + C("cpu_cores") + ", " + C("ram_gb") + " and " + C("step_timeout") + " (seconds). It is written by the Environment screen, the XDS Config panel in the sidebar and the Parallel processing switch. Delete a key to fall back to the environment variable or the default."),
    SUB("Per-project memory"),
    P("Each project's " + C("metadata.json") + " keeps its description, data path, the completed steps, the folders of the last XDS / XSCALE / XDSCONV runs (" + C("last_run_folder") + ", " + C("last_xscale_folder") + ", " + C("last_xdsconv_folder") + ") and the last image path opened in the frame viewer (" + C("viewer_template") + ")."),
)

section("doc-security", "Security and access",
    P("CrystalPilot can read any folder you can read, run programs and write files, so it only answers the browser tab that opened it:"),
    UL(["When the page is served it hands the tab a " + B("per-launch token") + " as a cookie restricted to this site. Every " + C("/api/") + " request must carry it; other web sites open in the same browser cannot obtain it, so they cannot drive the API.",
        "Scripts pass the token, printed in the console banner at start-up, as the header " + C("X-CrystalPilot-Token") + " or as " + C("?token=") + ". Set " + C("XDS_GUI_TOKEN") + " to make it fixed.",
        "By default the server listens on this computer only, and then answers only requests addressed to " + C("localhost") + ", " + C("127.x.x.x") + " or " + C("[::1]") + ". A web site that points a name of its own at 127.0.0.1 (DNS rebinding) is refused, so it cannot load the page and take the token. Add other names with " + C("XDS_GUI_ALLOWED_HOSTS") + ".",
        C("--host 0.0.0.0") + " opens the server to the network; the token then still protects against other web sites, but anyone who can reach the port can open the interface. Use " + C("--restrict-browse") + " on shared machines: every path the interface lists, reads, runs in or writes must then lie inside the projects folder (links and " + C("..") + " are resolved first).",
        "Stopping the server (Ctrl+C, closing the console, the Stop script, SIGTERM) ends every program it started, with their helper processes, before it exits.",
        "Readable without the token: the " + C("/health") + " endpoint (used by the Windows loading screen), the illustrated manual under " + C("/manual/") + " and the static assets. Everything else, including every " + C("/api/") + " route, needs it."]),
)

section("doc-projects", "Projects and where files live",
    P("A project is a folder under the projects folder. Create one from the sidebar (name, optional description and data path), click it to make it active; drag entries to reorder the list (remembered by the browser), " + B("&#8635; Refresh") + " re-reads the projects folder. " + B("&#10005;") + " removes it from the list only (its files stay), " + B("&#128465;") + " deletes the folder. Project names may contain spaces but no path separators."),
    SUB("The rule"),
    P("Input files you edit (" + C("XDS.INP") + ", " + C("XSCALE.INP") + ", " + C("XDSCONV.INP") + ") live in the project folder. Program output lives in the " + B("folder where the program last ran") + ": the project folder itself, a run folder you chose (which can be anywhere, e.g. next to the frames), an auto-numbered sub-folder, or an " + C("XSCALE_NNN") + " folder. The interface records that folder per program in the project's metadata and every viewer, parser, comparison and downstream program reads from there. You never have to tell the LP viewer or POINTLESS where CORRECT ran."),
    PRE("projects/\n"
        "  my_dataset/\n"
        "    metadata.json        name, description, completed steps, last run folders, viewer path\n"
        "    XDS.INP              what you edit; copied into the run folder before every run\n"
        "    XSCALE.INP, XDSCONV.INP\n"
        "    CORRECT.LP ...       output, when XDS ran in the project folder itself\n"
        "    CORRECT.LP.prev1..4  previous CORRECT / IDXREF / XSCALE logs, rotated automatically\n"
        "    XSCALE_001/          sub-folder mode of XSCALE\n"
        "    pointless.log, aimless.log, ctruncate.log, *.mtz, XDSCC12.LP, AUTOPILOT_RESULTS.json\n"
        "                          written next to the XDS output they were made from"),
    P("The status line under the run-folder field shows the current output folder (and its Windows form under WSL). " + B("Open folder") + " next to the project name and next to the run folder open the corresponding folder in your file manager. " + C("GET /api/projects/&lt;name&gt;/locations") + " lists where every file resolves right now, for debugging."),
    SUB("Run folders"),
    UL([B("Overwrite") + " (default): XDS runs in the project folder, or in the folder typed in the run-folder field. Previous logs are kept as " + C(".prev1") + " to " + C(".prev4") + " for CORRECT and IDXREF.",
        B("Sub-folders") + ": each run gets a new numbered folder (or a name you type) inside the base folder, so different strategies can be compared side by side.",
        "The field suggests recently used folders and the folder of the frames; the choice is remembered per project."]),
    SUB("Packing a project into one file"),
    P(B("&#10515; Export (.zip)") + " next to the project name packs the project into one archive: the input files "
      "(XDS.INP, XSCALE.INP, XDSCONV.INP), every program log, the parsed reports, the figures, the refined geometry and the "
      "reflection files &mdash; from the project folder and from every run folder it has written to, one level deep, with a "
      + C("README.txt") + " naming the program, the project and the day. Left out on purpose: the frames, the "
      + C("*-CORRECTIONS.cbf") + " images XDS rewrites on every run, " + C("SPOT.XDS") + " and the rotated older logs "
      "(" + C(".prev1") + "&hellip;" + C(".prev4") + "). The message offers the file as a download, names it on disk, and links "
      "a second pass without the reflection files when only the numbers need to travel."),
)

section("doc-environment", "The Environment screen",
    P("Opened automatically on first launch and whenever something changes; open it any time with the " + B("&#9881; Environment") + " button in the header (also from the About panel behind the version badge). For every component it shows a status, an explanation and, where useful, an action:"),
    TABLE(["Row", "Meaning", "Action"], [
        ["Python packages", "numpy, matplotlib, h5py, hdf5plugin, fabio for the frame viewer and header reading", "&#11015; Install now (pip) &mdash; the pip / apt output streams below the row"],
        ["XDS", "xds_par or xds, xscale_par or xscale, xdsconv in the configured folder or on PATH", "Path field + Save &amp; re-check; download link"],
        ["Parallel processing", "whether xds_par and xscale_par exist and are enabled", "Switch in the sidebar"],
        ["XDS helper programs", "forkxds, mcolspot, mintegrate next to xds_par (row shown only when one is missing)", "copy the complete XDS package"],
        ["Eiger HDF5 reader", "dectris-neggia.so, needed for .h5 data", "Path field; download link"],
        ["CCP4", "pointless, aimless, ctruncate, f2mtz, cad", "&mdash; (set in the XDSCONV tab or the settings file)"],
        ["Projects folder", "where projects live, with the Windows path under WSL", "&#128194; Open in file manager"],
        ["Windows Subsystem for Linux", "shown under WSL: the distribution, where the Windows drives are mounted, the mapped drive letter", "&mdash;"],
    ], ["22%", "48%", "30%"]),
    P("Tick " + B("Don't show this again unless something changes") + " to keep it from opening at start; it returns when the fingerprint of the checks changes (for example after CCP4 was installed)."),
)

section("doc-xdsinp", "Editing XDS.INP",
    SUB("Three ways to fill it"),
    UL([B("Load from XDS.INP") + " reads the project's file into the form; " + B("Load from other XDS.INP&hellip;") + " imports the parameters of any XDS.INP (beamline pipelines, previous runs) into the form only &mdash; press " + B("Save Parameters") + " to write them.",
        B("Generate from images") + ": set " + C("NAME_TEMPLATE_OF_DATA_FRAMES") + " (type it, or browse to any frame &mdash; the name is turned into the " + C("????") + " template, and for Eiger data the master file is found from a data or template name) and click it. Detector geometry, wavelength, distance, oscillation, frame count and detector type are read from the frame header: CBF mini-headers, HDF5 / NeXus (including the Eiger count-rate cut-off as " + C("OVERLOAD=") + " and the sensor thickness), SMV, R-AXIS. For HDF5 data the " + C("LIB=") + " line pointing at neggia is written automatically. The generated file is saved at once.",
        B("Manual entry") + " in the Key Parameters form, or the raw text in the Full Input File tab."]),
    SUB("The Key Parameters form"),
    P("Groups: experiment (oscillation, wavelength, template, distance), detector (type, NX/NY, ORGX/ORGY, QX/QY), indexing (space group, cell, SIGNAL_PIXEL, ranges), corrections, reporting (resolution range, shells) and the neggia " + C("LIB=") + " line. Toggles mark a keyword " + B("Active") + " or " + B("Commented") + " (written with a leading " + C("!") + ", so the value is kept but XDS ignores it &mdash; set SPACE_GROUP_NUMBER to commented or 0 to let XDS decide)."),
    UL([B("From IDXREF") + " under the cell fields opens the lattice table of the latest IDXREF.LP; pick a Bravais lattice to fill cell and space group.",
        "POINTLESS and &Delta;CC&frac12; results offer " + B("Apply to XDS.INP") + " and " + B("Apply &amp; re-run CORRECT") + ".",
        "Resolution cut-off estimates in the CORRECT metrics apply " + C("INCLUDE_RESOLUTION_RANGE") + " with one click."]),
    NOTE("The editor changes only the keyword you edited. Lines that carry several keywords (" + C("NX= 4150 NY= 4371 QX= 0.075 QY= 0.075") + ", common in beamline files) keep the other keywords, trailing comments are preserved, an active line wins over a commented copy, and the geometry keywords " + C("ROTATION_AXIS") + ", " + C("INCIDENT_BEAM_DIRECTION") + ", " + C("DIRECTION_OF_DETECTOR_X/Y-AXIS") + ", " + C("FRACTION_OF_POLARIZATION") + ", " + C("POLARIZATION_PLANE_NORMAL") + " are never touched by the form &mdash; edit those in the Full Input File tab."),
    P("Parameter references: " + A(XDSDOC + "xds_parameters.html", "XDS.INP") + " &middot; " + A(XDSDOC + "xscale_parameters.html", "XSCALE.INP") + " &middot; " + A(XDSDOC + "xdsconv_parameters.html", "XDSCONV.INP") + "."),
)

section("doc-pipeline", "Running XDS",
    P("The pipeline track shows the eight steps (green done, orange running, red failed). Click a step to open its log; click the &#9654; next to a step to run from there through CORRECT."),
    TABLE(["Button", "Runs"], [
        ["&#9654; to IDXREF", "XYCORR &rarr; INIT &rarr; COLSPOT &rarr; IDXREF: corrections, background, spot search, indexing"],
        ["&#9654; Integrate &amp; Correct", "DEFPIX &rarr; INTEGRATE &rarr; CORRECT"],
        ["&#9654; Full Pipeline", "everything, or up to the step chosen in " + B("Stop at")],
        ["&#9889; CORRECT Only", "CORRECT alone &mdash; seconds; use after changing space group, cell, resolution or Friedel's law"],
        ["GXPARM Re-integrate", "copies the refined geometry GXPARM.XDS to XPARM.XDS and runs DEFPIX &rarr; INTEGRATE &rarr; CORRECT again; often improves statistics"],
        ["&#9209; Stop", "stops the running program together with its helper processes (xds_par forks forkxds, mcolspot, mintegrate)"],
    ], ["26%", "74%"]),
    UL(["Before each run the project's XDS.INP is copied into the run folder, so what you see in the editor is what runs.",
        B("Parallel processing") + " (sidebar) chooses xds_par / xscale_par or the serial binaries; remembered per computer.",
        B("CPU cores") + " and " + B("RAM (GB)") + " (sidebar, XDS Config) limit what XDS, XSCALE and the other programs may use, all runs together, so the computer stays usable: 4 cores and 16 GB (at most three quarters of the RAM) by default. The core count is in every XDS.INP and XSCALE.INP CrystalPilot writes: " + C("MAXIMUM_NUMBER_OF_PROCESSORS=") + " with " + C("MAXIMUM_NUMBER_OF_JOBS= 1") + " right after " + C("JOB=") + " in XDS.INP (otherwise xds_par runs several jobs of that many cores each), and " + C("MAXIMUM_NUMBER_OF_PROCESSORS=") + " before the first " + C("OUTPUT_FILE=") + " in XSCALE.INP. Changing it updates the files of every project and the open editors; a value from a beamline's XDS.INP is replaced. The programs are also held to that many cores. The RAM limit uses a Linux cgroup (as root, e.g. under WSL) or a systemd user scope; it counts the frames Linux keeps in memory too, which are dropped first. A run that needs more RAM than allowed is stopped and the log says so. Where neither is available the panel says why, and only the CPU limit applies.",
        "Every program run has a " + B("time limit") + " (4 hours by default, " + C("step_timeout") + " in the settings file). When it is exceeded the run is stopped, children included, and the log says so.",
        "Two programs are never started in the same folder at the same time; the second request is refused with a message.",
        "The " + B("Live Log") + " streams the program's output as it is produced; the step buttons update when a step finishes. A step is marked failed when its log contains " + C("!!! ERROR !!!") + " or when no log was written."]),
)

section("doc-autoindex", "Auto-indexing trials",
    P("The " + B("Auto-Index") + " card in the Data Processing tab runs a series of COLSPOT + IDXREF trials to find a combination that indexes: different SPOT_RANGE wedges and SIGNAL_PIXEL values, starting from the project's XDS.INP. Tiers: " + B("Quick") + " (a few trials), " + B("Medium") + ", " + B("Full") + " (wider grids, the whole data set, pairs of wedges, more index origins and tolerances); every tier ends with a bisection of SIGNAL_PIXEL between its two best trials. " + "the " + B("&#128274; SG/Cell") + " lock keeps the cell and space group of XDS.INP during the trials (off: every trial indexes freely). "
      "Each trial reports the spots found, the indexed fraction, a score (indexed fraction &times; min(1, indexed spots / 200)) and the spot and spindle deviations; for the selected trial " + B("Apply to XDS.INP") + " writes SIGNAL_PIXEL, SPOT_RANGE and any special parameters (INDEX_ERROR, MIN_PIXELS, INDEX_ORIGIN), " + B("Apply &amp; Re-run IDXREF") + " does that and runs COLSPOT + IDXREF at once; " + B("&#10515; CSV") + " exports the table and " + B("&#128203; Report") + " opens the text report. Trials run in their own folders and do not disturb the project's results. Results are cached per project."),
)

section("doc-lpviewer", "LP viewer, metrics, charts, history",
    P("The LP Viewer tab shows any step's log (from the current output folder, with the file path shown under the selector): choose the file and click " + B("View") + ", or click a green step in the pipeline track. " + B("Key Metrics") + " parses the log: choose the step and click " + B("View Metrics") + ". What it shows:"),
    UL([B("IDXREF") + " &mdash; indexed fraction, refined beam centre and distance, spot and spindle deviations, the full lattice table (44 Bravais types with quality of fit; the selected one marked), spot map.",
        B("INTEGRATE") + " &mdash; suggested profile parameters, mosaicity and divergence per frame, scale per frame, strong / rejected / overloaded reflections per frame; charts flag radiation damage, beam dumps and slippage.",
        B("CORRECT") + " &mdash; space group, cell, ISa, &chi;&sup2;, the resolution shell table with colour-coded quality, Wilson plot and B-factor, distribution moments with ice-ring annotations, alien reflections, anomalous signal, and the four resolution cut-off estimates with apply buttons (I/&sigma; &asymp; 2, CC&frac12; &asymp; 50 %, R-obs &asymp; 55 %, CC&frac12; significance after Karplus &amp; Diederichs 2012) plus " + B("Custom&hellip;") + " for a limit of your own; after applying, run " + B("CORRECT Only") + ".",
        B("CORRECT, decisions") + " &mdash; " + B("Systematic Absences Analysis") + " tests the screw axes expected for the space group against the observed absences and lists space-group suggestions with a " + B("&#9889; try") + " button that re-runs CORRECT in that group; the Laue-group table (R<sub>meas</sub> of every compatible group relative to P1) has a " + B("&#9889; SG n") + " button per row for the same purpose; the anomalous summary offers " + B("Set FRIEDEL=FALSE &amp; Re-run CORRECT") + " when Bijvoet pairs were merged.",
        B("CORRECT, ice and anisotropy") + " &mdash; " + B("Ice Ring Analysis") + ": " + B("Auto-detect Ice Rings") + " scores the shells at the hexagonal ice spacings, " + B("Chart overlay") + " marks them on the shell chart, " + B("&#10052; Apply Selected Exclusions") + " / " + B("Apply All Standard Ice Ranges") + " write EXCLUDE_RESOLUTION_RANGE lines to XDS.INP and " + B("&#10005; Remove All Exclusions") + " takes them out again. " + B("Diffraction Anisotropy") + ": " + B("Analyse Anisotropy") + " computes per-axis resolution statistics from XDS_ASCII.HKL with gemmi (needs the gemmi package).",
        B("COLSPOT") + " and " + B("INIT") + " &mdash; spot counts, gain and background summary."]),
    SUB("Run history and comparison"),
    P("CORRECT, IDXREF and XSCALE logs are rotated (" + C(".prev1") + " to " + C(".prev4") + ") every time the program runs again. " + B("Run History") + " compares the last runs side by side (cell, space group, ISa, R-factors, CC&frac12;, completeness, resolution; lattice quality for IDXREF) and flags what changed. " + B("&Delta; Compare with Previous") + " puts the current log next to " + C(".prev1") + "; " + B("&Delta; Compare with File&hellip;") + " compares it with a log uploaded from anywhere, for example a beamline auto-processing result."),
    SUB("Matthews calculator"),
    P("Under the CORRECT metrics: enter the molecular weight; the cell and space group of the latest CORRECT.LP give V<sub>M</sub> and solvent content for 1&hellip;n copies per asymmetric unit (Matthews 1968)."),
    SUB("Figures"),
    P(B("&#10515; Figures (.png)") + " on the CORRECT and the XSCALE metrics writes a set of figures next to the log they come from: "
      "CC&#189;, I/&#963;, completeness and R-meas, each as a PNG at 300 dpi and as a PDF (vector, for a journal), plus "
      + C("..._Resolution_Statistics") + ", the four on one sheet &mdash; usually the one a report wants. Names begin with "
      + C("CORRECT_") + " or " + C("XSCALE_") + ", so the two sets never overwrite each other. The links in the message download them "
      "and the folder is named there. Needs matplotlib (the Environment screen installs it with the frame-viewer packages)."),
    P("What is on them, beyond the curve: the resolution axis is " + B("linear in 1/d&sup2;") + " &mdash; the space XDS bins the shells in &mdash; "
      "so the fall-off is not distorted by stretching the few low-resolution shells; the " + B("cut-off this metric's criterion suggests") +
      " is marked and the range beyond it shaded, using the same code as the cut-off buttons, so a figure and the interface can never "
      "disagree; ice rings with strong or moderate evidence are banded, because a dip at 3.90 or 2.25 &#8491; is contamination rather than "
      "resolution; a CC&#189; shell XDS marks as significant at the 0.1&nbsp;% level gets a filled marker and one it does not a hollow one; "
      "percentages use a fixed 0&ndash;100 axis so two runs can be laid side by side; and the overall row, the space group, the cell and a "
      "provenance line (program, log, date) travel with the figure."),
    P("Any chart on screen opens in a window when clicked: drag its title bar to move it, the grip in its bottom-right corner to resize it (the chart is redrawn to fill it); a double-click on the title bar puts it back in the middle. "
      "It can also be saved as it is: " + B("&#10515; PNG") + " in the window. That image is drawn at a fixed "
      "size, so it does not depend on the screen it was saved from, and it keeps the dark interface colours and every series together."),
    SUB("Exports"),
    P(B("&#10515; Export CORRECT Data (.csv)") + " downloads the parsed CORRECT data (shell table, Wilson data, moments, aliens), " + B("&#10515; Export INTEGRATE Data (.csv)") + " the per-frame data. Every chart expands on click; " + B("hide") + " next to a chart title collapses it."),
)

section("doc-xscale", "XSCALE",
    P("Scales and merges one or more XDS_ASCII.HKL files. " + B("Auto-detect") + " lists reflection files in the project, its sub-folders and the current XDS output folder; " + B("Autofill from CORRECT.LP") + " transfers space group, cell and the resolution limit chosen by your cut-off preference."),
    TABLE(["Keyword", "Meaning"], [
        [C("INPUT_FILE"), "one line per data set; relative names are resolved from the run folder"],
        [C("OUTPUT_FILE"), "merged reflection file, default " + C("merged.ahkl") + " (XDS format; POINTLESS, AIMLESS and XDSCONV read it directly)"],
        [C("FRIEDEL'S_LAW") + " / " + C("MERGE"), "keep Bijvoet pairs for anomalous data / merge equivalents (FALSE keeps all observations for AIMLESS)"],
        [C("SPACE_GROUP_NUMBER") + ", " + C("UNIT_CELL_CONSTANTS"), "override the symmetry of the inputs"],
        [C("INCLUDE_RESOLUTION_RANGE"), "per data set; " + C("RESOLUTION_SHELLS") + " sets the statistics binning"],
        [C("STRICT_ABSORPTION_CORRECTION") + ", " + C("NBATCH") + ", " + C("REIDX") + ", " + C("REFERENCE_DATA_SET"), "toggleable advanced options"],
    ], ["34%", "66%"]),
    SUB("Saving"),
    UL([B("Update in existing XSCALE.INP") + " merges the form into the file and keeps everything else, comments included.",
        B("Save as new XSCALE.INP") + " writes a fresh file from the form.",
        "Both write every keyword into its XSCALE section (global keywords before " + C("OUTPUT_FILE") + ", output keywords after it, per-data-set keywords under each " + C("INPUT_FILE") + "); a file with misplaced keywords is repaired on save. An empty input list defaults to the project's XDS_ASCII.HKL from the last CORRECT run; if a run starts with no input at all, that file is inserted and the log says so."]),
    SUB("Running and results"),
    P("Run modes: " + B("Overwrite") + " in the project folder, or " + B("Sub-folders") + " " + C("XSCALE_001") + ", " + C("XSCALE_002") + "&hellip; (input paths are rewritten so they still resolve). XSCALE.LP is rotated like CORRECT.LP; the LP viewer shows the shell table, the ISa of each data set, and the same four cut-off estimates with apply buttons; Run History and Compare work for XSCALE as well."),
)

section("doc-xdsconv", "XDSCONV and MTZ",
    P("Converts XDS or XSCALE reflection files. " + B("Auto from XSCALE") + " picks the latest XSCALE output; the output name can be derived from the project. Formats: CCP4 (merged intensities and amplitudes), CCP4_F, CCP4_I, SHELX, XtalView; " + B("Free R flags") + " adds " + C("GENERATE_FRACTION_OF_TEST_REFLECTIONS") + " (5 % by default)."),
    UL(["With CCP4 available, " + C("f2mtz") + " and " + C("cad") + " run after XDSCONV and produce the final " + C(".mtz") + " (custom name possible). On Windows this uses CCP4 for Windows through the bridge installed by the wizard.",
        "Without CCP4, " + B("Convert with gemmi") + " writes an intensity MTZ (with free-R flags) from the XDS file directly; gemmi can be installed from the tab.",
        "Working folder: the project folder or the latest XSCALE sub-folder. XDSCONV.INP is copied there when the project's copy is newer."]),
)

section("doc-pointless", "POINTLESS",
    P("Determines the Laue group and the most likely space group from the systematic absences. Input: the latest XDS_ASCII.HKL (or an XSCALE output / MTZ you choose, " + B("Detect") + " finds candidates). Options: chirality, setting (symmetry-based or cell-based), a forced Laue group or space group, resolution limits. The log streams live and is saved as " + C("pointless.log") + " next to the XDS output; results are cached and reloaded when you return to the tab."),
    P("Results: the best solution with its confidence, the space group and Laue group score tables, the reindexing operator and, when present, the systematic-absence evidence. " + B("Apply to XDS.INP") + " writes SPACE_GROUP_NUMBER and the cell; " + B("Apply &amp; re-run CORRECT") + " does that and runs CORRECT at once. The anisotropy analysis of the same tab reads the cached results."),
)

section("doc-aimless", "AIMLESS and CTRUNCATE",
    P("An independent scaling and merging of the XDS integration, for comparison and for CCP4-style output. The tab runs " + B("POINTLESS") + " (sort and reindex), " + B("AIMLESS") + " (scaling; anomalous on or off; resolution limits; number of bins) and " + B("CTRUNCATE") + " (intensities to amplitudes, twinning tests). Inputs and CCP4 are detected automatically; the current CORRECT and XSCALE statistics are shown for reference."),
    P("Results: overall and per-shell statistics (R-merge, R-meas, R-pim, CC&frac12;, I/&sigma;, completeness, multiplicity, anomalous), per-batch scale and B-factor, charts, a comparison of key metrics with XDS CORRECT and XSCALE, the CTRUNCATE amplitude and twinning summary, and the list of output files (" + C("aimless_scaled.mtz") + ", " + C("aimless_unmerged.mtz") + ", " + C("aimless_truncate.mtz") + ", logs). Everything is saved next to the XDS output and reloaded when you return."),
)

section("doc-deltacc", "&Delta;CC&frac12; per frame (XDSCC12)",
    P("Runs Kay Diederichs' " + C("xdscc12") + " on XDS_ASCII.HKL to compute how much each frame (or batch of frames) contributes to CC&frac12;. Frames or batches with strongly negative &Delta;CC&frac12; harm the data set (radiation damage, ice, crystal movement)."),
    UL(["The tab checks for the binary; " + B("&#11015; Download automatically") + " fetches it (Linux, macOS) into your user folder and verifies that it runs; " + B("&#128196; View XDSCC12.LP") + " shows the raw log.",
        "Options: batch width (degrees per batch) and number of resolution bins, and four detection strategies that can be combined: " + B("Radiation damage tail") + " (progressive decline at the end), " + B("Negative blocks") + " (contiguous frames below zero), " + B("2-MAD outliers") + " (runs of &ge; 3 frames below median &minus; 2 MAD) and " + B("3-MAD severe") + " (adjacent pairs below median &minus; 3 MAD).",
        "The chart shows &Delta;CC&frac12; per frame; " + B("Suggested Exclusions") + " lists what the strategies found, with tick boxes (" + B("Select all") + " / " + B("none") + "). Click and drag on the chart to mark a range of your own: it appears under " + B("Selected Range") + " with " + B("Add to EXCLUDE_DATA_RANGE") + " and " + B("Clear selection") + ".",
        B("Add selected to EXCLUDE_DATA_RANGE") + " writes the ticked suggestions as " + C("EXCLUDE_DATA_RANGE") + " lines to XDS.INP; " + B("Apply selected &amp; Re-run CORRECT") + " does that and re-runs CORRECT so the effect is visible immediately. The XDSCC12 log is kept as " + C("XDSCC12.LP") + "."]),
)

section("doc-autopilot", "AutoPilot",
    P("AutoPilot processes one data set or many from start to finish without intervention and explains what it did. The tab is a wizard: "
      "six steps set everything up, and nothing runs until " + B("Start AutoPilot") + " on the last one. Every data set becomes a project of its own and is "
      "processed one after the other on the server: the page can be closed and reopened, and the tab picks the run up again."),
    SUB("1 · Folders"),
    P("Drop folders on the drop area, or type or paste their paths (Windows paths such as " + C("Z:\\DATA\\run1") + " are understood), or " + B("Browse") + ". "
      "A browser never tells a web page where a dragged folder is, so AutoPilot finds it by its name and the names and sizes of its files: in recently used folders, the projects folder, the home folder and the drives (at most 20 seconds). "
      "When the same folder is in two places it asks which; when it is not found, paste the path (Explorer: Shift + right-click &rarr; " + B("Copy as path") + "). "
      "Each folder is searched, down to the depth chosen, for Eiger " + C("*_master.h5") + " files and numbered frame series of at least five frames, by their names."),
    P(B("Add the open project") + " puts the project open in the sidebar into the run: it is processed in place with the XDS.INP you set up by hand in Data Processing, without a search or an import. Open another project and add it too."),
    SUB("2 · Data sets and their XDS.INP"),
    P("The data sets found are listed; untick what you do not want and edit the project names. Raster scans (grids of shots taken to find the crystal: a rasterImages folder or &ldquo;raster&rdquo; in the file name) are listed, marked and not ticked. For each one AutoPilot looks for the XDS.INP a beamline "
      "pipeline left behind &mdash; it carries the beamline's geometry (rotation axis direction, beam centre, detector orientation), which an image header often does not. "
      "Pipelines name their folders differently at every beamline, so the search is not tied to names: it looks in the folders from step 1, in each data set's folder, "
      "its parent and grandparent and below them, and in the folders you add under " + B("Also search in") + " (for example the beamline's processed-data folder)."),
    P("A file is a candidate when its " + C("NAME_TEMPLATE_OF_DATA_FRAMES") + " names the data set's images (the file name; beamline paths are not this computer's) "
      "and, where the image header can be read, its wavelength, detector distance and oscillation agree with it; a file that disagrees is listed as not used, with the reason. "
      "Candidates are ranked by how much of the image folder path in the template matches the data set's folder, then by the " + B("folders searched first") + " list, "
      "then the newest. That list holds words a folder name must " + B("contain") + " (" + C("fast_dp") + " matches " + C("fast_dp_2") + ", " + C("autoproc") + " matches "
      + C("autoPROC.run1") + "); the top word wins; add, remove and reorder words, the list is remembered."),
    TABLE(["Shown", "Meaning"], [
        [B("imported"), "one clear best file; it is used"],
        [B("pick one"), "equally good files that disagree on beam centre, distance, rotation axis, space group or cell; the first is used unless you choose"],
        [B("from header"), "no matching file; XDS.INP is written from the image header (with the neggia library for Eiger data)"],
        [B("your choice"), "you chose a file, or the header, in the list"],
    ]),
    P(B("view") + " shows the file exactly as it will be used. An imported XDS.INP keeps everything the beamline wrote except: the image template, which points at the images on this computer; "
      + C("LIB=") + " (the HDF5 library set in the wizard for Eiger data); file names that do not exist here (for example " + C("X-GEO_CORR") + "); " + C("DATA_RANGE") + ", " + C("SPOT_RANGE") + " and " + C("BACKGROUND_RANGE") + " when they go beyond the frames on disk; "
      "the beamline's computer settings (" + C("CLUSTER_NODES") + ", " + C("MAXIMUM_NUMBER_OF_JOBS") + ", " + C("MAXIMUM_NUMBER_OF_PROCESSORS") + ", " + C("SECONDS") + "); and " + C("INCLUDE_RESOLUTION_RANGE") + ", because the wizard's cut-offs decide. "
      "Every change is a comment starting with " + C("! CrystalPilot:") + " in the project's XDS.INP and a line in the log."),
    SUB("3 · Cut-offs, 4 · Reprocessing, 5 · Space group and indexing"),
    TABLE(["Choice", "What it decides"], [
        [B("Resolution cut-off"), "the criterion each data set is cut by: I/&sigma; &asymp; 2, CC&#189; &asymp; 50 %, CC&#189; significant, R-obs &asymp; 55 %"],
        [B("Friedel's law"), "a tick box for XSCALE and XDSCONV: ticked (default) TRUE merges anomalous pairs; untick for SAD/MAD to keep them apart"],
        [B("Resolution limits"), "optional INCLUDE_RESOLUTION_RANGE for every data set"],
        [B("Re-integrate with refined geometry"), "GXPARM &rarr; XPARM and a second DEFPIX-INTEGRATE-CORRECT: never, always, or " + B("only if better") + ": the first integration is put aside and restored when the re-integration does not improve the chosen measure (ISa, the resolution cut-off, or overall CC&#189;)"],
        [B("&Delta;CC&#189; frame rejection"), "XDSCC12; it runs inside the re-integration, so it does nothing when re-integration is &lsquo;never&rsquo; (the wizard says so)"],
        [B("Ice rings"), "exclude detected rings and re-run CORRECT, or leave them in"],
        [B("Space group and cell"), "determine per data set, or impose one SPACE_GROUP_NUMBER and UNIT_CELL_CONSTANTS on all &mdash; one crystal form in one setting, which merging needs (the cell is required: XDS takes a space group only together with its cell)"],
        [B("Space group in an imported XDS.INP"), "by default: process without it; if that fails, process with it; if that fails too, auto-index. Or always use it, or ignore it. Only data sets whose imported file has a space group are concerned."],
        [B("Screw axes"), "ticked by default: XDS chooses the space group without screw axes (C222 for C222&#8321;, P222 for P2&#8321;2&#8321;2&#8321;), so the axial reflections in CORRECT.LP are checked and, when they show screw axes, CORRECT runs again in the matching space group with the refined cell &mdash; seconds, no re-integration; the log says what was seen. Enantiomorphs (P4&#8321;/P4&#8323;, P3&#8321;/P3&#8322; &hellip;) cannot be told apart this way: one is kept and the log names the other. A space group given in the XDS.INP, or fixed for all data sets, is left alone. Untick to keep XDS's choice."],
        [B("If indexing fails"), "after AutoPilot's own IDXREF fixes: give up on that data set, or auto-index at the quick, medium or full tier"],
    ]),
    P("With the default space-group route a data set gets up to three runs, each from the imported file afresh; the first two do not auto-index, so a failed indexing moves on at once. "
      "The table shows which attempt a data set is on, and the log marks each one."),
    SUB("6 · Review and start"),
    P("One page lists every choice and how many data sets import their XDS.INP; a warning names data sets still marked " + B("pick one") + ". Give the run a name if you like and press " + B("Start AutoPilot") + "."),
    SUB("Runs, the data set view and merging"),
    P("One run is processed at a time, one data set at a time (XDS already uses every core). " + B("Skip current") + " stops the data set being processed and goes on; "
      + B("Stop") + " stops now: the data set being processed goes back in the queue with the rest, and " + B("Resume") + " processes it again, from a fresh XDS.INP when its XDS.INP was generated. A data set that finished stays finished even when Stop came in its last seconds. A data set that fails does not stop the run. The table shows each data set's status "
      "(with the phase and the attempt while it runs, and the reason when it failed), where its XDS.INP came from, space group, cell, cut-off, and the overall completeness, R-meas, I/&sigma;, CC&#189; and ISa "
      "read from its own CORRECT.LP, plus whether the re-integration was kept. The best value in a column is green; columns sort on a click."),
    P("Click a data set for its view: the phases (generate or check XDS.INP &rarr; XYCORR to IDXREF with automatic recovery &rarr; DEFPIX to CORRECT &rarr; ice-ring exclusion and resolution cut-off &rarr; optional re-integration, with the optional XDSCC12 exclusions inside it &rarr; XSCALE &rarr; XDSCONV to an MTZ; the cut-off is applied in XSCALE and XDSCONV, not written into XDS.INP; the first integration is always put aside, so a failed re-integration is undone), "
      "the live log, and when it has finished the summary with the before / after statistics, the shell table, the MTZ path, the retries and the diagnoses (stored as " + C("AUTOPILOT_RESULTS.json") + "). "
      + B("Open project") + " opens it in Data Processing. With a project open and no data set chosen, the view shows that project's last AutoPilot result."),
    P("With two or more finished data sets, tick them and " + B("Preview XSCALE.INP") + " or " + B("Merge with XSCALE") + ". Only data sets with the reference's space group "
      "and a cell within 3&nbsp;% on each axis (angles within 1.5&deg;) go in; the rest are listed with the reason. The reference is the data set with "
      "the highest ISa unless you choose one; it is the first INPUT_FILE and REFERENCE_DATA_SET, which anchors the scaling and the indexing. Each data set "
      "enters at its own cut-off with no low-resolution limit. The merge is written to " + C("<projects>/batches/<id>/merge_<date>/") + "; "
      "the reflection files are reached through short links in " + C("inputs/") + " because XDS cannot read file names with blanks. The preview shows "
      "that exact file; the merged statistics appear when XSCALE finishes."),
)

section("doc-gemmi", "gemmi analyses",
    P("Independent checks computed in Python with " + A("https://gemmi.readthedocs.io", "gemmi") + " on XDS_ASCII.HKL or an XSCALE output (autofilled from the project):"),
    UL([B("Data quality") + " &mdash; merging statistics per shell (R-merge, R-meas, R-pim, CC&frac12;, I/&sigma;, completeness, multiplicity) computed by gemmi, and " + B("vs CORRECT.LP") + " / " + B("vs XSCALE.LP") + " put the XDS numbers next to them (" + B("&#10005; Clear") + " removes the comparison).",
        B("Lattice symmetry") + " &mdash; possible higher metric symmetry of the cell within an obliquity tolerance, a hint for missed symmetry.",
        B("Anomalous scattering") + " &mdash; f' and f'' of an element at the wavelength (or a scan around it), for phasing decisions.",
        B("Deposition") + " &mdash; " + B("Prepare Deposition") + " writes an mmCIF structure-factor file from the reflection data (and the merged MTZ if present) for wwPDB deposition; " + B("Download CIF") + " saves it.",
        B("Polarization") + " &mdash; applies a polarization correction to the unmerged intensities (the equivalent of the AIMLESS POLARIZATION keyword) for a given source type, fraction and plane normal; " + B("Apply &amp; Compare") + " writes a corrected MTZ and shows the R-factors before and after. It does not change XDS.INP.",
        B("&#9654; Run All") + " runs data quality and lattice symmetry in one go. gemmi can be installed from the tab when missing."]),
)

section("doc-frameviewer", "Frame Viewer",
    P("Shows raw frames: CBF (PILATUS, EIGER miniCBF), HDF5 / Eiger (master file with all data chunks; type the master, a data file or the XDS template), ADSC / SMV, R-AXIS OSC, MarCCD, TIFF. Type a path, browse with &#128194;, or use " + B("From XDS.INP") + ". The last path is remembered per project and the " + B("Recent") + " menu lists the last five."),
    UL(["Navigation: &plusmn;1 / &plusmn;10 / &plusmn;100, slider, jump-to; multi-chunk Eiger sets are navigated as one series.",
        "Display: zoom 0.25&times; to 8&times; (slider), contrast as low / high percentiles, colour maps Grey (inverted), Grey, Heat and Blues; " + B("&#128269; Mag") + " opens a draggable, resizable magnifier inset at 0.5&times;, 2&times;, 4&times; or 8&times;.",
        B("Rings") + ": resolution rings from the geometry in the header or from XDS.INP: " + B("From Project") + " takes the project's file, " + B("Locate XDS.INP&hellip;") + " any file, " + B("Read XDS.INP Geometry") + " re-reads it; the px / dist / bcx / bcy fields can be edited by hand. " + B("Ice") + ": dashed rings at the hexagonal ice d-spacings.",
        B("Spots") + ": the SPOT.XDS overlay of the current output folder (green indexed, red not indexed), for frames inside SPOT_RANGE.",
        B("Save") + ": PNG (lossless) or JPEG of the current view with the overlays, at 1&times; (native detector resolution), 0.5&times;, 0.25&times; or 2&times;.",
        B("XDS diagnostics") + " (Advanced): loads the diagnostic images XDS writes into the output folder: " + C("SHOW_SPOT.cbf") + " from COLSPOT (the frame at SHOW_IMAGE_NUMBER with the strong pixels marked) and " + C("SHOW_HKL.cbf") + " from INTEGRATE (the predicted integration regions drawn on the frame).",
        "The header panel lists the geometry read from the file (wavelength, distance, pixel size, beam centre, image size, detector).",
        "Frames on network shares and, under WSL, on Windows drives are read directly; large Eiger sets are much faster from the projects folder (Linux side)."]),
)

section("doc-table1", "Statistics Table 1",
    P("Assembles a publication Table 1: collection parameters from XDS.INP (detector, wavelength, oscillation, distance, frames, total rotation), and statistics from " + B("XSCALE.LP") + " when present, otherwise " + B("CORRECT.LP") + ": space group, cell, resolution range, completeness, multiplicity, R-merge / R-meas, I/&sigma;, CC&frac12;, CC*, ISa, CC(anom) and SigAno for anomalous data, Wilson B and mosaicity (from CORRECT.LP), shown as overall (highest shell). The resolution range starts at the lowest-resolution reflection of the data, and the highest shell is given as a range. Another run is chosen in Run History (Use for Table 1)."),
    P(B("R-pim") + " is not printed by XDS and R-meas/&radic;multiplicity is only an approximation: it is computed with gemmi from the unmerged reflections of the same shells, and shown only when the R-meas computed the same way agrees with the log. Otherwise the row is left out and the status line gives the reason."),
    P("Export: " + B("Copy TSV") + " (Excel, Word, Sheets), " + B("Copy LaTeX") + " (a complete table environment with escaped symbols), " + B("&#10515; Export .csv") + " (a two-column parameter / value file for a spreadsheet); " + B("&#10227; Refresh") + " rebuilds the table after new processing."),
)

section("doc-modes", "Work modes and preferences",
    P(B("Work mode") + " in the sidebar sets how much is shown: " + B("Tutorial") + " (the core workflow with hints), " + B("Normal") + " (analysis tools, AutoPilot and the Statistics tab), " + B("Advanced") + " (diagnostics, corrections, more parameters, POINTLESS and AIMLESS), " + B("Expert") + " (everything, including &Delta;CC&frac12; and gemmi). If a tab described in this manual is not in the tab bar, raise the work mode."),
    TABLE(["Tab", "Shown from work mode"], [
        ["Data Processing, XSCALE, XDSCONV, Frame Viewer, Guide, Docs", "always"],
        ["AutoPilot, Statistics (Table 1)", "Normal"],
        ["POINTLESS, AIMLESS", "Advanced"],
        ["&Delta;CC&frac12;, gemmi", "Expert"],
    ], ["60%", "40%"]),
    P(B("Cutoff preference") + " chooses the criterion the XSCALE autofill and the CORRECT cut-off panel highlight by default (AutoPilot has its own cut-off choice, I/&sigma; &asymp; 2 by default). " + B("Parallel processing") + " and the XDS path are in the XDS Config panel. All of these are remembered."),
)

section("doc-windows", "Windows (WSL) notes",
    P("XDS exists only for Linux, so on Windows CrystalPilot runs inside the Windows Subsystem for Linux (Windows 10 2004+ / Windows 11). The wizard sets everything up; you never need a Linux terminal."),
    UL([B("Projects") + " live inside the Linux runtime for speed. They are reachable from Explorer through the " + B("CrystalPilot Projects") + " desktop shortcut, a Quick Access entry, optionally a drive letter (" + C("P:\\Projects\\") + " by default) and the " + B("Open folder") + " buttons in the interface; the raw path is " + C("\\\\wsl.localhost\\&lt;runtime&gt;\\...") + ".",
        B("Windows drives") + " appear as " + C("/mnt/c") + ", " + C("/mnt/d") + "&hellip; and as buttons in the file browser. Every drive Windows has when CrystalPilot starts is mounted, local disks and connected network drives alike, so a disk plugged in later is there after a restart of the program. In the file browser you can also paste a Windows path straight from Explorer (" + C("D:\\data\\xtal1") + " or " + C("\\\\server\\share\\xtal1") + "): the drive or share is mounted on the spot. Reading large Eiger sets through " + C("/mnt") + " is slow; copy them into the projects folder for heavy work.",
        B("CCP4") + ": a Linux CCP4 unpacked by the wizard, an existing Linux CCP4 in the runtime, or an installed CCP4 for Windows called through the interop bridge (slower but complete for the steps CrystalPilot uses).",
        B("Launcher") + ": " + C("CrystalPilot.bat") + " starts the server in a console window (close it or Ctrl+C to stop) and opens a loading screen that switches to the interface when ready; it always uses the newest build in the " + C("files") + " folder. " + C("CrystalPilot-Stop.bat") + " stops a server left running. Settings of the runtime are in " + C("~/.crystalpilot/config.env") + " (port, projects folder, CCP4 mode) and of the launcher in " + C("windows\\crystalpilot.cfg") + ".",
        "Running the wizard again updates the application and keeps projects and settings; " + C("wizard.ps1 -Unattended -Config choices.json") + " installs without questions."]),
)

section("doc-xds-steps", "XDS steps reference",
    TABLE(["Step", "Purpose", "Key output"], [
        ["XYCORR", "Spatial correction tables for every pixel from the detector geometry.", "X-/Y-CORRECTIONS.cbf"],
        ["INIT", "Gain, background model and trusted region from a subset of frames.", "BKGINIT.cbf, BLANK.cbf, GAIN.cbf"],
        ["COLSPOT", "Strong spots over SPOT_RANGE, saved with centroids and intensities.", "SPOT.XDS"],
        ["IDXREF", "Indexing: orientation matrix, refinement of crystal and detector parameters, all 44 Bravais lattices scored. The space group is decided later, in CORRECT.", "XPARM.XDS, IDXREF.LP"],
        ["DEFPIX", "Untrusted regions (beamstop, shadows) and the resolution limit for integration.", "BKGPIX.cbf, ABS.cbf"],
        ["XPLAN", "Optional strategy step: completeness and multiplicity for possible rotation ranges.", "XPLAN.LP"],
        ["INTEGRATE", "3D profile-fitting integration of every frame with running refinement; per-frame scale, divergence, mosaicity. The slow step; xds_par uses every core.", "INTEGRATE.HKL, INTEGRATE.LP"],
        ["CORRECT", "Lorentz, polarization, absorption and decay corrections, Laue group and space group decision, final refinement, quality statistics, Wilson statistics, alien reflections.", "XDS_ASCII.HKL, CORRECT.LP, GXPARM.XDS"],
    ], ["14%", "62%", "24%"]),
    P("Complete documentation: " + A(XDSDOC + "XDS.html", "xds.mr.mpg.de/html_doc/XDS.html") + "."),
)

section("doc-formats", "Supported formats",
    P("XDS " + C("DETECTOR=") + " types written by the generator: EIGER (also EIGER2), PILATUS, ADSC, CCDCHESS (Rayonix, MarCCD), MAR345, RAXIS, SATURN, BRUKER."),
    TABLE(["Format", "Extensions", "Notes"], [
        ["CBF", ".cbf", "PILATUS / EIGER miniCBF; geometry from the mini-header"],
        ["HDF5 / Eiger", ".h5, .hdf5", "master file with external links to data chunks; LZ4 / bitshuffle via hdf5plugin; NeXus metadata; the XDS template " + C("_??????.h5") + " and data files resolve to the master"],
        ["ADSC / SMV", ".img, .smv", "beam centre in mm, converted to pixels"],
        ["R-AXIS", ".osc", "Rigaku binary header"],
        ["MarCCD / Rayonix", ".mccd, .mar", ""],
        ["TIFF", ".tif, .tiff", "through fabio"],
        ["Reflection files", ".HKL, .ahkl, .mtz", "XDS format (XDS_ASCII.HKL, XSCALE output such as merged.ahkl, recognised by extension or header) and MTZ for POINTLESS / AIMLESS inputs"],
    ], ["20%", "18%", "62%"]),
)

section("doc-troubleshooting", "Troubleshooting",
    TABLE(["Symptom", "What to do"], [
        ["XDS executable not found", "Set the folder in the Environment screen or the XDS Config panel (or " + C("--xds-path") + "). The folder must contain xds_par or xds; the Environment screen lists what is missing."],
        ["Eiger .h5 data cannot be read by XDS", "dectris-neggia.so is missing or " + C("LIB=") + " points elsewhere. Put it next to xds_par or set its path in the Environment screen and generate XDS.INP again."],
        ["IDXREF: INSUFFICIENT PERCENTAGE OF INDEXED REFLECTIONS", "Check ORGX / ORGY (try the detector centre), distance and wavelength, widen SPOT_RANGE, check the oscillation, look at the frames. The Auto-Index card tries these systematically."],
        ["XSCALE: MISPLACED PARAMETER", "A keyword was in the wrong section of XSCALE.INP. Save the parameters again (both save modes write a correct layout and repair an old file); check the Full Input File tab if you edited by hand."],
        ["XSCALE.INP has no INPUT_FILE line", "Add files with Auto-detect and save, or run CORRECT first; a run with no input uses the project's XDS_ASCII.HKL when it exists."],
        ["Another program is already running in this folder", "A run is still active in that folder (possibly from another tab). Stop it or wait; two programs must not write the same output."],
        ["A step stopped after the time limit", "Raise " + C("step_timeout") + " in the settings file for very large data sets or slow network storage."],
        ["The LP viewer / POINTLESS cannot find CORRECT.LP", "They read from the folder of the last run; the status line under the run-folder field shows it and " + C("/api/projects/&lt;name&gt;/locations") + " lists every file. Run CORRECT again if the folder was moved."],
        ["Not authorised (403) from a script", "Send the token from the console banner as " + C("X-CrystalPilot-Token") + " or " + C("?token=") + "; set " + C("XDS_GUI_TOKEN") + " to make it fixed."],
        ["Frame Viewer: missing Python dependencies", "Install from the Environment screen or the tab (pip / apt / dnf / brew / conda are tried), or " + C("pip install numpy matplotlib h5py hdf5plugin fabio") + "."],
        ["HDF5 frame will not load", "hdf5plugin must be installed; the master and all data files must be in the same folder. On network shares CrystalPilot disables HDF5 file locking for you."],
        ["CCP4 steps skipped", "CCP4 was not found: source ccp4.setup before starting, set " + C("CCP4") + " / " + C("CBIN") + ", or set the bin folder in the XDSCONV tab. On Windows, run the wizard again after installing CCP4."],
        ["Refused: this CrystalPilot answers only requests addressed to localhost", "The page was opened under another host name. Open it as " + C("http://localhost:PORT") + " or " + C("http://127.0.0.1:PORT") + ", or add the name to " + C("XDS_GUI_ALLOWED_HOSTS") + "."],
        ["This installation only works inside the projects folder (--restrict-browse)", "The server was started with " + C("--restrict-browse") + ": move the data into the projects folder, or start it without that option."],
        ["Port already in use", "Another CrystalPilot is probably running (the launcher then opens the browser on it); otherwise start with another port."],
        ["Resolution rings missing", "The viewer needs pixel size, distance, wavelength and beam centre: from the header or via From Project / Locate XDS.INP."],
        ["Windows: slow browsing or loading", "Folders under /mnt (Windows drives) are slow over the WSL bridge; keep heavy data in the projects folder. Disconnected network drives are skipped at start."],
    ], ["30%", "70%"]),
    SUB("The log file"),
    P("Everything the program prints to its console is also written to " + C("<projects folder>/logs/crystalpilot.log") +
      " (the path is in the start-up banner and on the Environment screen). It keeps the last three files of 2 MB "
      "(" + C("crystalpilot.log.1") + "&hellip;) and is the first thing to look at after a crash or a step that ended "
      "without an explanation &mdash; on Windows the console belongs to the launcher and is easy to lose. The API token is "
      "replaced in the file, so the log can be sent on. " + C("XDS_GUI_LOG=<path>") + " moves it, " + C("XDS_GUI_LOG=off") +
      " switches it off."),
    SUB("Reporting a problem to the author"),
    P(B("&#9888; Report a problem") + " in the header opens a short form: what happened and what you expected. "
      + B("Save report (.zip)") + " writes " + C("crystalpilot-report_<date>_<time>.zip") + " to " + C("<projects folder>/reports/")
      + " with that text, the program version, what the Environment screen found, the last lines of the log and any errors recorded "
      "in the page &mdash; and, only if you tick it, the open project's XDS.INP and logs (never the frames). User names are taken out of "
      "every path and the API token out of every line. " + B("CrystalPilot sends nothing itself") + ": the next button opens your own "
      "e-mail program with the author's address, a subject and a short message filled in; attach the saved zip and press send. "
      "The address is set in the program (" + C("REPORT_EMAIL") + ") and a lab can point it at its own support with "
      + C("XDS_GUI_REPORT_EMAIL") + "; without one, the report is still saved and the form says so."),
)

# ── API reference: complete route list ───────────────────────────────────────
API_GROUPS = [
    ("General", [
        ["GET", "/health", "version (readable without token)"],
        ["GET", "/api/environment", "the Environment screen data"],
        ["GET", "/api/config", "configuration: xds_path, ccp4_bin, neggia_lib, projects_dir, parallel, settings_file, WSL info"],
        ["POST", "/api/config", "{xds_path, ccp4_bin, neggia_lib, parallel} &mdash; saved to the settings file"],
        ["GET", "/api/deps", "frame-viewer package status &middot; GET /api/deps/install (SSE) installs them"],
        ["GET", "/api/xdscheck", "XDS executables and helpers"],
        ["GET", "/api/ccp4check", "CCP4 programs and gemmi availability"],
        ["GET", "/api/ls?path=", "folder listing for the file browser"],
        ["POST", "/api/open-folder", "{path, dry} &mdash; open in the file manager (Explorer under WSL)"],
    ]),
    ("Projects", [
        ["GET / POST", "/api/projects", "list &middot; create {name, description, data_path}"],
        ["GET", "/api/projects/{name}", "metadata with output_dir"],
        ["DELETE", "/api/projects/{name}?files=true", "delete (files=true removes the folder)"],
        ["POST", "/api/projects/{name}/settings", "{viewer_template} remembered per project"],
        ["GET", "/api/projects/{name}/locations", "where every file resolves right now"],
    ]),
    ("XDS.INP and runs", [
        ["GET / POST", "/api/projects/{name}/xdsinp", "read / write the whole file {content}"],
        ["POST", "/api/projects/{name}/xdsinp/params", "{params: {KEY: value | null | '__commented__' | [[a,b],...]}}"],
        ["GET", "/api/projects/{name}/generate-xdsinp?template=", "generate from frame headers (template optional)"],
        ["GET", "/api/stream?project=&steps=|step=|stop_at=&run_folder=&copy_gxparm=", "SSE: run XDS steps (events step_start, log, step_done, error_msg, done)"],
        ["POST", "/api/run", "synchronous run {project_name, step | stop_at}"],
        ["POST", "/api/stop", "{project_name} stops that project's program (all when omitted), children included"],
        ["POST", "/api/run-folder", "{project_name, folder} prepare a run folder and copy XDS.INP"],
        ["POST", "/api/run-folder/list", "{base_folder} existing sub-folders and next number"],
        ["GET", "/api/autoindex/stream?project=&tier=quick|medium|full&force_cell=", "SSE auto-indexing &middot; GET .../autoindex-cached &middot; POST /api/autoindex/stop"],
    ]),
    ("Logs, metrics, history", [
        ["GET", "/api/projects/{name}/lp/{step}", "log text and its path"],
        ["GET", "/api/projects/{name}/metrics/{step}", "parsed IDXREF / INTEGRATE / CORRECT / COLSPOT / INIT"],
        ["GET", "/api/projects/{name}/spot-data", "SPOT.XDS summary &middot; .../integrate-params &middot; .../ice-rings"],
        ["GET", "/api/projects/{name}/history-{correct|idxref|xscale}", "previous runs (rotated logs)"],
        ["GET", "/api/projects/{name}/compare-{correct|idxref|xscale}", "current vs previous"],
        ["POST", "/api/projects/{name}/compare-{correct|idxref|xscale}-file", "{lp_content} current vs uploaded log"],
        ["GET", "/api/projects/{name}/matthews?mw=", "Matthews coefficient from CORRECT.LP"],
        ["GET", "/api/projects/{name}/export-data/{correct|integrate}", "CSV export"],
        ["GET", "/api/projects/{name}/table1data", "Table 1 &middot; POST .../export-table1 {rows}"],
    ]),
    ("XSCALE and XDSCONV", [
        ["GET / POST", "/api/projects/{name}/xscaleinp", "read / write XSCALE.INP"],
        ["POST", "/api/projects/{name}/xscaleinp/params", "{params, fresh} section-aware update; fresh=true writes a new file"],
        ["GET", "/api/xscale-detect-hkl?project= &middot; /api/projects/{name}/xscale-subfolders &middot; POST /api/xscale-run-folder", "inputs and run folders"],
        ["GET", "/api/xscale/stream?project=&run_folder= &middot; /api/projects/{name}/xscalelp", "run XSCALE (SSE) &middot; parsed XSCALE.LP"],
        ["GET / POST", "/api/projects/{name}/xdsconvinp &middot; .../xdsconvlp", "XDSCONV.INP and log"],
        ["GET", "/api/xdsconv/stream?project=&work_dir=&mtz_name=", "run XDSCONV (+ f2mtz / cad)"],
        ["GET", "/api/gemmi-mtz/stream?project=&input_file=&freer= &middot; /api/gemmi/install", "gemmi MTZ conversion (SSE) &middot; install gemmi"],
    ]),
    ("CCP4, XDSCC12, AutoPilot, gemmi", [
        ["GET", "/api/pointless/stream?project=&input_file=&chirality=&setting=&lauegroup=&spacegroup=&resolution_low=&resolution_high=", "run POINTLESS &middot; .../pointless-log(-raw) &middot; .../pointless-cached &middot; .../anisotropy-analyze"],
        ["GET", "/api/aimless/stream?project=&resolution_low=&resolution_high=&anomalous=&bins=&run_pointless=&run_ctruncate=&input_file=", "run AIMLESS &middot; .../aimless-log(-raw) &middot; .../ctruncate-log &middot; .../aimless-cached"],
        ["GET", "/api/xdscc12/check &middot; /api/xdscc12/download (SSE) &middot; /api/xdscc12/stream?project=&batch_width=&nbin=", "&middot; .../xdscc12-results &middot; .../xdscc12-lp"],
        ["GET", "/api/autopilot/stream?project=&criterion=&friedel=&template=&optimize=&dcc_half=&neggia_lib=", "run AutoPilot (SSE) &middot; /api/autopilot/status?project= &middot; .../autopilot-cached &middot; POST /api/autopilot/stop"],
        ["POST", "/api/gemmi/analyze", "{analysis: merging_stats | completeness | lattice_symmetry, project, input_file, res_low, res_high, n_shells, max_obliquity}"],
        ["POST", "/api/gemmi/anomalous &middot; /api/gemmi/deposition &middot; /api/gemmi/polarization", "{element, wavelength | energy, scan_range} &middot; {project, input_file, merged_mtz} &middot; {project, input_file, polarization, normal}"],
        ["GET", "/api/gemmi/lp-stats?project=&source=correct|xscale &middot; /api/gemmi/download-cif?path=", "LP statistics for comparison &middot; download a CIF"],
        ["GET", "/api/batch/strategy &middot; /api/batch/list &middot; /api/batch?id= &middot; /api/batch/log?id=&project=", "the AutoPilot wizard's choices &middot; the runs &middot; one run with its table &middot; one data set's log"],
        ["POST", "/api/batch/discover &middot; /create &middot; /start &middot; /stop &middot; /skip", "{folder, depth} &middot; {name, datasets (with xdsinp), strategy, search} &middot; {id}"],
        ["POST", "/api/batch/xdsinp-search &middot; /api/batch/xdsinp-preview", "{datasets, roots, keywords} &rarr; the matching XDS.INP files per data set, best first &middot; {path, dataset} &rarr; the file as it will be used, with the changes"],
        ["POST", "/api/batch/merge-plan &middot; /api/batch/merge", "{id, projects, reference, friedel} &rarr; the plan and the XSCALE.INP &middot; writes it and runs XSCALE"],
        ["POST", "/api/bug-report", "{description, project, include_project, page_errors} &rarr; writes the report zip and the text for an e-mail (nothing is sent)"],
        ["GET", "/api/bug-report?name=", "download a report this program wrote"],
        ["POST", "/api/export", "{project, reflections} &rarr; packs the project into &lt;project&gt;_&lt;date&gt;.zip and lists what went in"],
        ["GET", "/api/export?project=&name=", "download that archive (only a name this project's own exporter produced)"],
        ["POST", "/api/figures", "{project, source: CORRECT | XSCALE, metrics: [cc_half, completeness, i_sigma, r_meas]} &rarr; writes the PNGs next to that log and lists them"],
        ["GET", "/api/figure?project=&name=", "download one written figure (the name says which log it came from; any other name is refused)"],
    ]),
    ("Frame viewer", [
        ["GET", "/api/frame?path=&frame=&vmin=&vmax=&cmap=", "rendered frame as base64 PNG in JSON with header and geometry"],
        ["GET", "/api/h5/nframes?path= &middot; /api/frames/list?template= &middot; /api/fv-xdsinp?path= &middot; /api/fv-spots?dir=", "frame count &middot; files of a template &middot; geometry of an XDS.INP &middot; SPOT.XDS overlay"],
    ]),
]
api_html = [P("A JSON API drives the interface and can be scripted. Every " + C("/api/") + " request needs the per-launch token (header " + C("X-CrystalPilot-Token") + ", " + C("?token=") + ", or the cookie a served page holds); the token is printed in the console banner and can be fixed with " + C("XDS_GUI_TOKEN") + ". Long-running programs stream Server-Sent Events. Project names are percent-encoded in paths.")]
for gname, rows in API_GROUPS:
    api_html.append(SUB(gname))
    api_html.append(TABLE(["Method", "Endpoint", "Meaning"], [[m, C(e) if "&middot;" not in e else e.replace(" &middot; ", " &middot; "), d] for m, e, d in rows], ["11%", "47%", "42%"]))
section("doc-api", "API reference", *api_html)

section("doc-references", "References and links",
    SUB("Programs"),
    UL([A("https://xds.mr.mpg.de", "XDS") + " &mdash; Kabsch, W. (2010). Acta Cryst. D66, 125&ndash;132 and 133&ndash;144.",
        A("https://www.ccp4.ac.uk", "CCP4") + " &mdash; Agirre, J. et al. (2023). Acta Cryst. D79, 449&ndash;461.",
        "POINTLESS and AIMLESS &mdash; Evans, P. R. (2006). Acta Cryst. D62, 72&ndash;82; Evans, P. R. &amp; Murshudov, G. N. (2013). Acta Cryst. D69, 1204&ndash;1214.",
        "CTRUNCATE &mdash; French, S. &amp; Wilson, K. (1978). Acta Cryst. A34, 517&ndash;525 (the truncate procedure).",
        "XDSCC12 &mdash; Assmann, G., Brehm, W. &amp; Diederichs, K. (2016). J. Appl. Cryst. 49, 1021&ndash;1028.",
        A("https://gemmi.readthedocs.io", "gemmi") + " &mdash; Wojdyr, M. (2022). J. Open Source Softw. 7, 4200.",
        A("https://github.com/dectris/neggia", "dectris-neggia") + " &mdash; the HDF5 reader plug-in for XDS."]),
    SUB("Methods"),
    UL(["Diederichs, K. &amp; Karplus, P. A. (1997). Nature Struct. Biol. 4, 269&ndash;275 (R-meas).",
        "Karplus, P. A. &amp; Diederichs, K. (2012). Science 336, 1030&ndash;1033 (CC&frac12;).",
        "Matthews, B. W. (1968). J. Mol. Biol. 33, 491&ndash;497 (V<sub>M</sub>).",
        "Schneider, T. R. &amp; Garman, E. F. (1997) ice-ring d-spacings used for the annotations."]),
    SUB("Documentation"),
    UL([A(XDSDOC + "XDS.html", "XDS program description") + " &middot; " + A(XDSDOC + "xds_parameters.html", "XDS.INP") + " &middot; " + A(XDSDOC + "xscale_parameters.html", "XSCALE.INP") + " &middot; " + A(XDSDOC + "xdsconv_parameters.html", "XDSCONV.INP"),
        A("https://strucbio.biologie.uni-konstanz.de/xdswiki/", "XDSwiki") + " &mdash; tutorials and troubleshooting by the community."]),
    SUB("License"),
    P("CrystalPilot &copy; 2026 Mikael Elias is free software under the " + A("https://www.gnu.org/licenses/gpl-3.0.html", "GNU General Public License v3") +
      ", without any warranty. XDS, neggia, CCP4 and XDSCC12 are separate programs under their own licences."),
)

# ═════════════════════════════════════════════════════════════════════════════

# The box at the top of the Docs tab. The RANKING and the result rows come from
# the shared engine (cpds* in frontend.html, next to the header Ask bar): two
# boxes that rank differently would be two manuals to the reader. What differs
# is only where a hit lands — inside this tab the section is right there, so a
# Docs hit scrolls to it and highlights the words, while a manual hit opens the
# illustrated manual in its own window.
SEARCH_UI = (
    '<div style="margin:0 0 14px 0;">'
    '<input id="docs-search" type="search" autocomplete="off" placeholder="Search the documentation and the illustrated manual&hellip;  (e.g. run folder, Friedel, XSCALE cut-off)" '
    'oninput="docsSearch(this.value)" onkeydown="if(event.key===\'Escape\'){this.value=\'\';docsSearch(\'\');}" '
    'style="width:100%; padding:10px 14px; border-radius:10px; border:1px solid var(--border2); background:var(--panel2); color:var(--txt); font-family:var(--body); font-size:0.9rem; outline:none;">'
    '<div id="docs-search-results" style="display:none; margin-top:6px; max-height:60vh; overflow-y:auto; background:var(--panel2); border:1px solid var(--border); border-radius:10px;"></div>'
    '<style>#main-tab-docs mark { background:#f6c94d; color:#111; padding:0 2px; border-radius:2px; } #main-tab-docs mark.ds { background:#4cc9b0; }</style>'
    '</div>\n'
    '<script>\n'
    'var _dsTimer = null;\n'
    'function docsSearch(q) { clearTimeout(_dsTimer); _dsTimer = setTimeout(function(){ _docsSearchNow(q); }, 150); }\n'
    'function _docsSearchNow(q) {\n'
    '  var box = document.getElementById("docs-search-results"); if (!box) return;\n'
    '  var terms = cpdsTerms(q); cpdsClearMarks();\n'
    '  if (!terms.length) { box.style.display = "none"; box.innerHTML = ""; return; }\n'
    '  // the manual index arrives once, asynchronously; redraw when it does\n'
    '  cpdsLoadManual(function(){ var b = document.getElementById("docs-search"); if (b && b.value.trim()) _docsSearchNow(b.value); });\n'
    '  var hits = cpdsSearch(q, 40), man = cpdsManualState();\n'
    '  box.style.display = "";\n'
    '  var foot = (man && !man.length) ? "<div style=\\"color:var(--txt3); font-size:0.75rem; padding:6px 10px;\\">Illustrated manual not installed here: Docs sections only.</div>" : "";\n'
    '  if (!hits.length) { box.innerHTML = "<div style=\\"color:var(--txt3); padding:8px 12px;\\">No match for &ldquo;" + cpdsEsc(q) + "&rdquo;</div>" + foot; return; }\n'
    '  box.innerHTML = hits.map(function(h, i){ return cpdsRowHtml(h, i, terms); }).join("") + foot;\n'
    '  Array.prototype.forEach.call(box.querySelectorAll("a.ds-hit"), function(a){ a.onclick = function(e){ e.preventDefault(); var h = hits[+a.getAttribute("data-i")];\n'
    '    if (h.kind === "manual") { cpdsOpenHit(h, q); }\n'
    '    else { docJump(h.id); var body = document.querySelector("#" + h.id + " .card-body"); if (body) { cpdsClearMarks(); cpdsMarkDom(body, terms); } } }; });\n'
    '}\n'
    '</script>\n')

def render_docs():
    toc = ''.join('<a href="#" onclick="docJump(\'%s\');return false" style="display:block;color:%s;text-decoration:none;">%d. %s</a>' %
                  (sid, 'var(--accent2)' if i == 0 else 'var(--txt2)', i + 1, re.sub(r"<[^>]+>", "", title)) for i, (sid, title, _) in enumerate(SECTIONS))
    cards = ''.join('<div class="card" id="%s"><div class="card-header"><span class="card-title">%d. %s</span></div><div class="card-body" style="%s">%s</div></div>\n' %
                    (sid, i + 1, title, BODY, body) for i, (sid, title, body) in enumerate(SECTIONS))
    return ('<div id="main-tab-docs" style="display:none;">\n' + SEARCH_UI +
            '<div style="display:flex; gap:20px; align-items:flex-start;">\n'
            '<div id="docs-toc" style="position:sticky; top:20px; min-width:220px; max-width:240px; max-height:85vh; overflow-y:auto; background:var(--panel2); border:1px solid var(--border); border-radius:10px; padding:14px 16px;">\n'
            '<div style="font-family:var(--head); font-size:0.79rem; font-weight:700; letter-spacing:0.18em; text-transform:uppercase; color:var(--accent); margin-bottom:8px;">Contents</div>\n'
            '<div id="docs-toc-links" style="font-family:var(--mono); font-size:0.78rem; line-height:2.1;">' + toc + '</div>\n'
            '<div style="margin-top:10px; font-size:0.72rem; color:var(--txt3);">CrystalPilot ' + VERSION + '</div>\n'
            '</div>\n<div style="flex:1; min-width:0;">\n' + cards + '</div>\n</div>\n</div>')

# ── Quick Guide ──────────────────────────────────────────────────────────────
GUIDE = [
    ("1 · Install and start", P("Linux: " + C("bash install-linux.sh") + " next to the application file, then " + C("crystalpilot") + ". Windows: " + C("CrystalPilot-Setup.bat") + " once, then the desktop shortcut. The interface opens at " + C("http://127.0.0.1:8000") + ". On the first start the " + B("Environment") + " screen tells you what was found (XDS, neggia for Eiger data, CCP4, Python packages) and how to fix anything missing; it is always reachable from the About panel.")),
    ("2 · Create or select a project", P("In the sidebar type a name and click " + B("＋ Create Project") + ", or click an existing one. A project is a folder that holds your input files and results; " + B("Open folder") + " shows it in your file manager (under Windows also as " + C("P:\\Projects\\...") + ").")),
    ("3 · Set up XDS.INP", P(B("Generate from images") + " reads geometry, wavelength, oscillation and frame count from the frame headers (Eiger master files included, with the neggia " + C("LIB=") + " line); " + B("Load from XDS.INP") + " or " + B("Load from other XDS.INP…") + " imports an existing file; or type values in the Key Parameters form. Toggles mark a keyword active or commented. " + B("From IDXREF") + " fills cell and space group from the lattice table once IDXREF has run. Edit exotic keywords in the Full Input File tab.")),
    ("4 · Run", P(B("▶ to IDXREF") + " first, then " + B("▶ Integrate & Correct") + "; " + B("⚡ CORRECT Only") + " after changing symmetry or resolution; " + B("GXPARM Re-integrate") + " for a second pass with refined geometry. Choose overwrite or numbered sub-folders in the run-folder field. " + B("⏹ Stop") + " ends the run and its helper processes. If indexing fails, the " + B("Auto-Index") + " card tries spot ranges and thresholds for you.")),
    ("5 · Inspect", P("Click a green step for its log; " + B("Key Metrics") + " gives tables and charts (lattice table, per-frame scale and mosaicity, shell statistics, Wilson plot, moments, aliens, anomalous signal, cut-off estimates with apply buttons). " + B("Run History") + " compares the last runs, " + B("Compare…") + " an uploaded log. The Matthews calculator sits under the CORRECT metrics. Export parsed data as CSV.")),
    ("6 · Frame Viewer", P("Load a frame or the XDS template (or " + B("From XDS.INP") + "), step through the series, adjust contrast and zoom, open the magnifier with " + B("Mag") + ", show resolution rings, ice rings and the SPOT.XDS overlay, save the view as PNG. The path is remembered per project; " + B("Recent") + " lists the last five.")),
    ("7 · XSCALE", P("Add the XDS_ASCII.HKL files (" + B("Auto-detect") + "), " + B("Autofill from CORRECT.LP") + " for symmetry and resolution, set Friedel's law and merge mode, save (" + B("Update") + " keeps the file, " + B("Save new") + " starts clean; both write a valid XSCALE layout) and run. The LP viewer shows the statistics and cut-off estimates for the merged data.")),
    ("8 · Space group and independent scaling", P(B("POINTLESS") + " determines the Laue and space group and can apply it to XDS.INP and re-run CORRECT. " + B("AIMLESS") + " scales and merges independently, with CTRUNCATE amplitudes and twinning tests, and compares its statistics with XDS. Both need CCP4.")),
    ("9 · Frame quality", P(B("ΔCC½") + " runs XDSCC12 to find frames that harm the data; accept the suggested exclusions and re-run CORRECT with one click.")),
    ("10 · Convert", P(B("XDSCONV") + " writes CCP4 / MTZ (with f2mtz and cad when CCP4 is present, or with gemmi otherwise), SHELX or XtalView files with free-R flags.")),
    ("11 · AutoPilot", P("A wizard: drop the folders, check which beamline XDS.INP each data set imports, choose the cut-offs, the reprocessing (GXPARM re-integration, ΔCC½) and what to do with the space group and failed indexing, review, start. Every data set is processed unattended with error recovery, XSCALE and MTZ output; compare them in one table and merge the best.")),
    ("12 · Checks with gemmi", P("Merging statistics and completeness computed independently, lattice symmetry hints, anomalous scattering factors, a deposition CIF and a polarization check.")),
    ("13 · Table 1", P("The " + B("Statistics") + " tab builds a publication Table 1 from XSCALE.LP or CORRECT.LP; copy as TSV or LaTeX, or export a .csv.")),
    ("14 · Tips", UL(["Work mode (Tutorial / Normal / Advanced / Expert) controls how much is shown; the cut-off preference sets the criterion autofill uses.",
                      "Everything reads and writes in the folder of the last run; the status line under the run-folder field shows it.",
                      "The server answers only the browser tab that opened it; scripts need the token printed at start (" + C("X-CrystalPilot-Token") + "). " + C("--host 0.0.0.0") + " opens it to the network, " + C("--restrict-browse") + " confines the file browser.",
                      "Under Windows keep large Eiger data in the projects folder; the Windows drives are under " + C("/mnt/c") + ", " + C("/mnt/z") + "&hellip;",
                      "Parameter references: " + A(XDSDOC + "xds_parameters.html", "XDS.INP") + " · " + A(XDSDOC + "xscale_parameters.html", "XSCALE.INP") + " · " + A(XDSDOC + "xdsconv_parameters.html", "XDSCONV.INP") + "."])),
]
def render_guide():
    body = ''.join('<div style="font-family:var(--head); font-size:0.78rem; font-weight:700; letter-spacing:0.15em; text-transform:uppercase; color:var(--accent2); margin:14px 0 6px 0;">%s</div>%s' % (t, b) for t, b in GUIDE)
    return ('<div id="main-tab-guide" style="display:none;">\n<div class="card">\n<div class="card-header"><span class="card-title">Quick Guide</span>'
            '<span style="font-size:0.75rem; color:var(--txt3);">CrystalPilot v' + VERSION + '</span></div>\n'
            '<div class="card-body" style="font-family:var(--mono); font-size:0.82rem; color:var(--txt2); line-height:1.7;">\n'
            + NOTE(B("XDS Documentation: ") + A(XDSDOC + "XDS.html", "xds.mr.mpg.de/html_doc/XDS.html") + " &mdash; the official reference for all XDS parameters and methods (W. Kabsch, MPI Heidelberg). The " + B("Docs") + " tab next to this one is the complete CrystalPilot manual.")
            + body + '\n</div>\n</div>\n</div>')

# ── splice ───────────────────────────────────────────────────────────────────
class Rng(HTMLParser):
    def __init__(self, target): super().__init__(); self.t = target; self.on = False; self.depth = 0; self.start = None; self.end = None
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if not self.on and a.get("id") == self.t: self.on = True; self.depth = 0; self.start = self.getpos()
        if self.on and tag == "div": self.depth += 1
    def handle_endtag(self, tag):
        if self.on and tag == "div":
            self.depth -= 1
            if self.depth == 0: self.on = False; self.end = self.getpos()

def splice(text, target, new_html):
    r = Rng(target); r.feed(text)
    lines = text.split("\n")
    (l1, c1), (l2, c2) = r.start, r.end
    before = "\n".join(lines[:l1 - 1]) + ("\n" if l1 > 1 else "") + lines[l1 - 1][:c1]
    after_line = lines[l2 - 1][c2 + len("</div>"):]
    after = after_line + ("\n" + "\n".join(lines[l2:]) if l2 < len(lines) else "")
    indent = " " * 16
    new_block = "\n".join(indent + l if l.strip() else l for l in new_html.split("\n"))
    return before + new_block.lstrip() + after, (l1, l2)

text = SRC.read_text(encoding="utf-8")
text, rd = splice(text, "main-tab-docs", render_docs())
text, rg = splice(text, "main-tab-guide", render_guide())
SRC.write_text(text, encoding="utf-8", newline="\n")
print("docs replaced lines %s, guide replaced lines %s; %d doc sections, %d guide steps, version %s" % (rd, rg, len(SECTIONS), len(GUIDE), VERSION))
