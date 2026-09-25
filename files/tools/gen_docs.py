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
    P("The illustrated manual is the documentation of CrystalPilot. The search box above and the one in the " + B("header") + " (" + C("Ctrl+K") + ") "
      "search it from any tab: each result carries the sentence that matched with your words highlighted and opens the manual at that section "
      "in its own window. Inside the manual, the box in the side bar (Ctrl+K) searches its sections. The &#128214; Manual button in the header opens it directly."),
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
    '<input id="docs-search" type="search" autocomplete="off" placeholder="Search the illustrated manual&hellip;  (e.g. run folder, Friedel, XSCALE cut-off)" '
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
    '  var foot = (man && !man.length) ? "<div style=\\"color:var(--txt3); font-size:0.75rem; padding:6px 10px;\\">Illustrated manual not installed here.</div>" : "";\n'
    '  if (!hits.length) { box.innerHTML = "<div style=\\"color:var(--txt3); padding:8px 12px;\\">No match for &ldquo;" + cpdsEsc(q) + "&rdquo;</div>" + foot; return; }\n'
    '  box.innerHTML = hits.map(function(h, i){ return cpdsRowHtml(h, i, terms); }).join("") + foot;\n'
    '  Array.prototype.forEach.call(box.querySelectorAll("a.ds-hit"), function(a){ a.onclick = function(e){ e.preventDefault(); var h = hits[+a.getAttribute("data-i")];\n'
    '    if (h.kind === "manual") { cpdsOpenHit(h, q); }\n'
    '    else { docJump(h.id); var body = document.querySelector("#" + h.id + " .card-body"); if (body) { cpdsClearMarks(); cpdsMarkDom(body, terms); } } }; });\n'
    '}\n'
    '</script>\n')

def render_docs():
    cards = ''.join('<div class="card" id="%s"><div class="card-header"><span class="card-title">%s</span></div><div class="card-body" style="%s">%s</div></div>\n' %
                    (sid, title, BODY, body) for sid, title, body in SECTIONS)
    return ('<div id="main-tab-docs" style="display:none;">\n' + SEARCH_UI + cards +
            '<div style="margin-top:10px; font-size:0.72rem; color:var(--txt3);">CrystalPilot ' + VERSION + '</div>\n</div>')

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
