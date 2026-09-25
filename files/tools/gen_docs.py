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
# The Docs tab IS the illustrated manual (docs/manual/CrystalPilot-Manual.html), shown
# in the tab at full height with its own contents and search; the PDF is one click
# away.  The page is large (screenshots and clips inside), so the frame is filled the
# first time the tab opens (_docsLoadManual, called from switchMainTab), not at start.
def render_docs():
    return (
        '<div id="main-tab-docs" style="display:none;">\n'
        '<div style="display:flex; align-items:center; gap:14px; margin:0 0 8px 0; font-size:0.78rem; color:var(--txt3);">'
        '<b style="font-family:var(--head); letter-spacing:0.15em; text-transform:uppercase; color:var(--accent);">Illustrated manual</b>'
        '<a id="docs-manual-pdf" href="/manual/CrystalPilot-Manual.pdf" target="_blank" rel="noopener" style="color:var(--accent); display:none;">&#11015; PDF</a>'
        '<span id="docs-manual-note"></span>'
        '<span style="margin-left:auto;">CrystalPilot ' + VERSION + '</span></div>\n'
        '<iframe id="docs-manual-frame" title="CrystalPilot illustrated manual" '
        'style="width:100%; height:calc(100vh - 140px); min-height:560px; border:1px solid var(--border); border-radius:10px; background:#fff; display:none;"></iframe>\n'
        '<script>\n'
        'function _docsLoadManual() {\n'
        '  var f = document.getElementById("docs-manual-frame"); if (!f || f.getAttribute("src")) return;\n'
        '  var note = document.getElementById("docs-manual-note");\n'
        '  note.textContent = "Loading the manual\u2026";\n'
        '  fetch("/manual/").then(function (r) { return r.json(); }).then(function (d) {\n'
        '    if (d && d.available) {\n'
        '      f.style.display = ""; f.setAttribute("src", "/manual/CrystalPilot-Manual.html"); note.textContent = "";\n'
        '      if (d.pdf) document.getElementById("docs-manual-pdf").style.display = "";\n'
        '      var hb = document.getElementById("manual-btn"); if (hb) hb.style.display = "";\n'
        '    } else {\n'
        '      note.innerHTML = "Not installed here. The manual is in the <code>docs/manual</code> folder of the CrystalPilot package; open <code>CrystalPilot-Manual.pdf</code> from there, or rebuild it with <code>python docs/manual/build_manual.py</code>.";\n'
        '    }\n'
        '  }).catch(function () { note.textContent = "The manual could not be loaded."; });\n'
        '}\n'
        '</script>\n'
        '</div>')

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
print("docs replaced lines %s, guide replaced lines %s; the Docs tab shows the illustrated manual; %d guide steps, version %s" % (rd, rg, len(GUIDE), VERSION))
