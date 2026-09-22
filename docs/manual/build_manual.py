#!/usr/bin/env python3
"""Build the CrystalPilot illustrated manual.

    python docs/manual/build_manual.py              chapters/*.md + images/*.png -> CrystalPilot-Manual.html (+ .pdf)
    python docs/manual/build_manual.py --capture    refresh the screenshots first (needs the processed test project;
                                                    runs tests/api/api_tests.sh with the real chain, then capture.js)
    python docs/manual/build_manual.py --no-pdf     skip the PDF step

Standard library only.  The Markdown subset understood: # / ## / ### headings,
paragraphs, **bold**, *italic*, `code`, [text](url), ![caption](images/x.png),
"- " bullets, "1. " numbered lists, "> " notes, "| a | b |" tables (first row =
header, second row = separator), ``` fenced code blocks, "---" rules.
"""
import base64
import json
import html as H
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CHAPTERS = HERE / "chapters"
IMAGES = HERE / "images"
OUT_HTML = HERE / "CrystalPilot-Manual.html"
OUT_PDF = HERE / "CrystalPilot-Manual.pdf"
OUT_INDEX = HERE / "CrystalPilot-Manual.index.json"
SPLASH = ROOT / "windows" / "splash.html"          # the loading screen: cover picture and cover text come from it
COVER_PNG = IMAGES / "00-loading-screen.png"
WRITTEN_WITH = "Anthropic Claude Fable 5.1"   # sections as plain text: the app's Docs search reads it


def version():
    m = re.search(r'VERSION = "([^"]+)"', (ROOT / "files" / "src" / "config.py").read_text(encoding="utf-8"))
    return m.group(1) if m else "?"


# ── Markdown subset → HTML ───────────────────────────────────────────────────
def inline(s):
    s = H.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", lambda m: "<code>%s</code>" % m.group(1), s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?![*\w])", r"<i>\1</i>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    return s


def image_tag(alt, src, missing):
    p = HERE / src
    if not p.exists():
        missing.append(src)
        return '<figure class="missing"><div class="ph">screenshot %s not captured yet</div><figcaption>%s</figcaption></figure>' % (H.escape(src), inline(alt))
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return '<figure><img src="data:image/png;base64,%s" alt="%s"><figcaption>%s</figcaption></figure>' % (data, H.escape(alt, quote=True), inline(alt))


def md_to_html(text, missing, chapter_no):
    out, i, lines = [], 0, text.split("\n")
    list_stack = []   # ("ul"|"ol")

    def close_lists():
        while list_stack:
            out.append("</%s>" % list_stack.pop())

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            close_lists(); i += 1; continue
        if s.startswith("```"):
            close_lists(); buf = []; i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            out.append("<pre>%s</pre>" % H.escape("\n".join(buf))); i += 1; continue
        m = re.match(r"^(#{1,3})\s+(.*)$", s)
        if m:
            close_lists(); lvl = len(m.group(1)); title = m.group(2).strip()
            if lvl == 1:
                out.append('<h1 id="ch-%02d">%s</h1>' % (chapter_no, inline(title)))
            else:
                anchor = "ch-%02d-%s" % (chapter_no, re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-"))
                out.append('<h%d id="%s">%s</h%d>' % (lvl, anchor, inline(title), lvl))
            i += 1; continue
        if s == "---":
            close_lists(); out.append("<hr>"); i += 1; continue
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", s)
        if m:
            close_lists(); out.append(image_tag(m.group(1), m.group(2), missing)); i += 1; continue
        if s.startswith("|"):
            close_lists(); rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            body = [r for r in rows[1:] if not all(re.match(r"^:?-{2,}:?$", c) for c in r)]
            out.append("<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (
                "".join("<th>%s</th>" % inline(c) for c in rows[0]),
                "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c) for c in r) for r in body)))
            continue
        if s.startswith("> "):
            close_lists(); buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip()); i += 1
            kind = "note"
            if buf and buf[0].lower().startswith(("warning:", "caution:")): kind = "warn"
            out.append('<div class="%s">%s</div>' % (kind, inline(" ".join(buf)))); continue
        m = re.match(r"^(\d+)\.\s+(.*)$", s)
        if m or s.startswith("- "):
            kind = "ol" if m else "ul"
            if not list_stack or list_stack[-1] != kind:
                close_lists(); list_stack.append(kind); out.append("<%s>" % kind)
            item = m.group(2) if m else s[2:]
            # continuation lines indented by two or more spaces belong to the item
            j = i + 1
            while j < len(lines) and lines[j].startswith("  ") and lines[j].strip() and not re.match(r"^\s*(\d+\.|-)\s", lines[j]):
                item += " " + lines[j].strip(); j += 1
            out.append("<li>%s</li>" % inline(item)); i = j; continue
        # paragraph
        close_lists(); buf = [s]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,3}\s|[-|>]|\d+\.\s|!\[|```)", lines[i].strip()) and lines[i].strip() != "---":
            buf.append(lines[i].strip()); i += 1
        out.append("<p>%s</p>" % inline(" ".join(buf)))
    close_lists()
    return "\n".join(out)


def browser():
    cands = [os.environ.get("CP_BROWSER"), r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
             r"C:\Program Files\Google\Chrome\Application\chrome.exe", "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/microsoft-edge"]
    return next((c for c in cands if c and Path(c).exists()), None) or shutil.which("msedge") or shutil.which("google-chrome") or shutil.which("chromium")


def headless(exe, output_flag, url, out, min_size, timeout, extra=(), grace=60):
    """Have the browser write `out` headless; (True, "") once it has, else (False, why).

    Two things made the old check wrong, in both directions:
    - Edge's msedge.exe returns before the file exists.  Measured on Windows
      with no other Edge running: the process returned 0.1 s after starting,
      the PDF appeared about 4 s later, and a profile of its own
      (--user-data-dir) changed neither.  So a correct PDF was reported as
      "PDF failed".  The file is now waited for, up to `grace` seconds after
      the process returns (15 times what was measured), and judged once its
      size has held still for a second.
    - The check only asked whether `out` existed and was big enough, and the
      previous build's file always was - the cover picture is even committed -
      so a render that never happened could be reported as done.  The browser
      now writes to a .part file, and `out` is replaced only when that is
      complete; a failure leaves the previous file exactly as it was.
    """
    part = out.with_name(out.stem + ".part" + out.suffix)
    try:
        part.unlink()
    except FileNotFoundError:
        pass
    try:
        r = subprocess.run([exe, "--headless=new", "--disable-gpu"] + list(extra) + [output_flag + str(part), url],
                           capture_output=True, text=True, timeout=timeout)
        said = (r.stderr or r.stdout or "").strip()
    except subprocess.TimeoutExpired:
        said = "the browser did not finish in %d s" % timeout
    size, seen, steady, deadline = -1, -1, 0, time.time() + grace
    while time.time() < deadline:
        time.sleep(0.5)
        size = part.stat().st_size if part.exists() else -1
        steady = steady + 1 if (size >= min_size and size == seen) else 0
        seen = size
        if steady >= 2:
            break
    if steady < 2:
        try:
            part.unlink()
        except FileNotFoundError:
            pass
        why = "no file was written within %d s" % grace if size < 0 else "the file is only %d bytes" % size
        return False, why + (": " + said[-200:] if said else "")
    os.replace(part, out)
    return True, ""


def splash_texts():
    """Name, subtitle and credit line exactly as the loading screen shows them (windows/splash.html)."""
    src = SPLASH.read_text(encoding="utf-8") if SPLASH.exists() else ""
    def part(cls, default):
        m = re.search(r'<div class="%s">(.*?)</div>' % cls, src, flags=re.S)
        return m.group(1).strip() if m else default
    return {"name": part("name", "CrystalPilot"), "sub": part("sub", "Crystallographic data processing &amp; analysis"),
            "credit": part("credit", "<b>Mikael Elias</b>")}


def render_cover(ver):
    """Screenshot of the loading screen in its finished state (splash.html?demo=<version>)."""
    exe = browser()
    if not exe or not SPLASH.exists():
        print("cover: browser or splash.html not found, keeping the existing picture" if COVER_PNG.exists() else "cover: no picture"); return COVER_PNG.exists()
    url = SPLASH.resolve().as_uri() + "?demo=" + ver
    ok, why = headless(exe, "--screenshot=", url, COVER_PNG, 20000, 120,
                       extra=("--hide-scrollbars", "--window-size=1400,820", "--virtual-time-budget=1500"))
    print("cover: rendered the loading screen (version %s) -> %s" % (ver, COVER_PNG.name) if ok
          else "cover: rendering failed, keeping the existing picture: " + why)
    return ok


def index_entries(chapter_html, chapter_title):
    """One entry per heading: anchor, chapter, title, plain text of the section (no images)."""
    heads = list(re.finditer(r'<h([123]) id="([^"]+)">(.*?)</h\1>', chapter_html, flags=re.S))
    out = []
    for k, m in enumerate(heads):
        end = heads[k + 1].start() if k + 1 < len(heads) else len(chapter_html)
        seg = re.sub(r"<img[^>]*>", " ", chapter_html[m.end():end])
        txt = re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", seg))).strip()
        out.append({"a": m.group(2), "c": chapter_title, "t": H.unescape(re.sub(r"<[^>]+>", "", m.group(3))), "x": txt})
    return out


# In-page search: every heading starts a section; a query lists the matching sections in the
# side bar and, on click, highlights the words in the text.  ?q=word#anchor (as the app's Docs
# search opens it) pre-fills the box and highlights that section.
SEARCH_JS = r"""
(function(){
  var main = document.querySelector('main'), box = document.getElementById('q'), hits = document.getElementById('hits'), toc = document.getElementById('toc');
  var secs = [], cur = null, chap = '';
  Array.prototype.forEach.call(main.children, function(el){
    if (/^H[123]$/.test(el.tagName)) { if (el.tagName === 'H1') chap = el.textContent.trim(); cur = { id: el.id, title: el.textContent.trim(), chap: chap, els: [el] }; secs.push(cur); }
    else if (cur) cur.els.push(el);
  });
  secs.forEach(function(s){ s.text = s.els.map(function(e){ return e.innerText || e.textContent; }).join(' ').replace(/\s+/g, ' '); s.low = s.text.toLowerCase(); s.tlow = s.title.toLowerCase(); });
  function esc(s){ return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
  function escH(s){ return s.replace(/[&<>]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]; }); }
  function terms(q){ return q.trim().toLowerCase().split(/\s+/).filter(function(t){ return t.length >= 2; }); }
  function clearMarks(){ Array.prototype.forEach.call(document.querySelectorAll('mark.cp'), function(m){ var p = m.parentNode; p.replaceChild(document.createTextNode(m.textContent), m); p.normalize(); }); }
  function markIn(els, ts){
    var re = new RegExp('(' + ts.map(esc).join('|') + ')', 'gi');
    els.forEach(function(root){
      var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null), nodes = [];
      while (w.nextNode()) nodes.push(w.currentNode);
      nodes.forEach(function(n){ var v = n.nodeValue; if (!re.test(v)) { re.lastIndex = 0; return; } re.lastIndex = 0;
        var frag = document.createDocumentFragment(), last = 0, m;
        while ((m = re.exec(v))) { frag.appendChild(document.createTextNode(v.slice(last, m.index))); var mk = document.createElement('mark'); mk.className = 'cp'; mk.textContent = m[0]; frag.appendChild(mk); last = m.index + m[0].length; }
        frag.appendChild(document.createTextNode(v.slice(last))); n.parentNode.replaceChild(frag, n); });
    });
  }
  function snippet(s, t){ var i = s.low.indexOf(t); if (i < 0) return escH(s.text.slice(0, 120)); var a = Math.max(0, i - 60), b = Math.min(s.text.length, i + t.length + 90);
    return (a ? '\u2026' : '') + escH(s.text.slice(a, i)) + '<mark>' + escH(s.text.slice(i, i + t.length)) + '</mark>' + escH(s.text.slice(i + t.length, b)) + (b < s.text.length ? '\u2026' : ''); }
  function goTo(s, ts){ clearMarks(); if (ts.length) markIn(s.els, ts); document.getElementById(s.id).scrollIntoView({ block: 'start' }); try { history.replaceState(null, '', location.search + '#' + s.id); } catch (e) {} }
  function search(q){
    var ts = terms(q);
    if (!ts.length) { hits.style.display = 'none'; toc.style.display = ''; hits.innerHTML = ''; window.__cpHits = 0; return; }
    var res = secs.filter(function(s){ return ts.every(function(t){ return s.low.indexOf(t) >= 0; }); })
      .map(function(s){ return { s: s, score: ts.reduce(function(n, t){ return n + (s.tlow.indexOf(t) >= 0 ? 10 : 0) + (s.low.split(t).length - 1); }, 0) }; })
      .sort(function(a, b){ return b.score - a.score; }).slice(0, 40);
    toc.style.display = 'none'; hits.style.display = '';
    hits.innerHTML = (res.length ? '<div class="n">' + res.length + ' section' + (res.length > 1 ? 's' : '') + '</div>' : '<div class="n">No match</div>')
      + res.map(function(r, i){ return '<a href="#' + r.s.id + '" data-i="' + i + '"><b>' + escH(r.s.title) + '</b><small>' + escH(r.s.chap) + '</small><span>' + snippet(r.s, ts[0]) + '</span></a>'; }).join('');
    Array.prototype.forEach.call(hits.querySelectorAll('a'), function(a){ a.onclick = function(e){ e.preventDefault(); goTo(res[+a.getAttribute('data-i')].s, ts); }; });
    window.__cpHits = res.length;
  }
  box.addEventListener('input', function(){ search(box.value); });
  box.addEventListener('keydown', function(e){ if (e.key === 'Escape') { box.value = ''; search(''); clearMarks(); } if (e.key === 'Enter') { var a = hits.querySelector('a'); if (a) a.click(); } });
  document.addEventListener('keydown', function(e){ if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) { e.preventDefault(); box.focus(); box.select(); } });
  window.__cpSearch = search;
  var q0 = new URLSearchParams(location.search).get('q');
  if (q0) { box.value = q0; search(q0); var id = location.hash.slice(1), s0 = null; secs.forEach(function(s){ if (s.id === id) s0 = s; }); if (s0) setTimeout(function(){ goTo(s0, terms(q0)); }, 60); }
})();
"""


CSS = """
:root { --bg:#0b1020; --panel:#121a2e; --txt:#e6edf7; --txt2:#b9c6dc; --acc:#6fb1ff; --acc2:#4cc9b0; --line:#25304a; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--txt2); font: 15px/1.65 "Segoe UI", system-ui, -apple-system, sans-serif; }
.wrap { display:flex; gap:32px; max-width:1240px; margin:0 auto; padding:28px 24px; }
nav { position:sticky; top:20px; align-self:flex-start; min-width:250px; max-width:270px; max-height:92vh; overflow:auto; background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px 16px; font-size:13px; }
nav a { display:block; color:var(--txt2); text-decoration:none; padding:3px 0; }
nav a.l2 { padding-left:14px; font-size:12px; color:#8fa3c7; }
nav a:hover { color:var(--acc); }
#q { width:100%; padding:7px 10px; border-radius:8px; border:1px solid var(--line); background:var(--bg); color:var(--txt); font-size:13px; margin-bottom:10px; outline:none; }
#q:focus { border-color:var(--acc); }
#hits .n { color:#8fa3c7; font-size:12px; margin-bottom:4px; }
#hits a { display:block; padding:7px 0; border-bottom:1px solid var(--line); }
#hits a b { display:block; color:var(--txt); font-weight:600; } #hits a small { color:#8fa3c7; font-size:11px; } #hits a span { display:block; font-size:12px; color:var(--txt2); line-height:1.45; margin-top:2px; }
mark { background:#f6c94d; color:#111; padding:0 2px; border-radius:2px; } mark.cp { background:#4cc9b0; }
main { flex:1; min-width:0; }
h1 { color:var(--txt); font-size:26px; margin:44px 0 10px; padding-top:18px; border-top:1px solid var(--line); letter-spacing:.01em; }
h1:first-of-type { border-top:0; margin-top:0; }
h2 { color:var(--acc); font-size:19px; margin:30px 0 8px; }
h3 { color:var(--acc2); font-size:15px; margin:22px 0 6px; text-transform:uppercase; letter-spacing:.08em; }
p { margin:0 0 12px; }
code { font-family: Consolas, "SF Mono", monospace; font-size:.92em; color:#9ed0ff; background:rgba(255,255,255,.05); padding:1px 5px; border-radius:4px; }
pre { background:#070b16; border:1px solid var(--line); border-radius:8px; padding:12px 14px; overflow:auto; font-family: Consolas, monospace; font-size:13px; color:var(--txt); }
ol, ul { margin:0 0 14px 22px; padding:0; } li { margin:0 0 6px; }
figure { margin:14px 0 20px; } figure img { max-width:100%; border:1px solid var(--line); border-radius:8px; box-shadow:0 8px 30px rgba(0,0,0,.45); }
figcaption { font-size:13px; color:#8fa3c7; margin-top:6px; }
figure.missing .ph { border:1px dashed #e0a458; color:#e0a458; padding:30px; text-align:center; border-radius:8px; }
.note { border-left:3px solid var(--acc); background:rgba(111,177,255,.08); padding:10px 14px; border-radius:0 8px 8px 0; margin:12px 0; }
.warn { border-left:3px solid #f6ad55; background:rgba(246,173,85,.08); padding:10px 14px; border-radius:0 8px 8px 0; margin:12px 0; }
table { border-collapse:collapse; width:100%; margin:10px 0 16px; font-size:14px; }
th { text-align:left; color:var(--acc2); border-bottom:1px solid var(--line); padding:6px 8px; }
td { border-bottom:1px solid var(--line); padding:6px 8px; vertical-align:top; }
.cover { text-align:center; padding:30px 20px 30px; }
.cover img.shot { display:block; width:100%; max-width:1100px; margin:0 auto 26px; border:1px solid var(--line); border-radius:12px; box-shadow:0 12px 40px rgba(0,0,0,.55); }
.cover .t { text-transform:uppercase; }
.colophon { margin-top:60px; font-size:13px; color:#8fa3c7; } .colophon hr { margin-bottom:14px; }
.cover .t { font-size:44px; font-weight:800; letter-spacing:.14em; color:var(--txt); }
.cover .s { color:var(--acc); letter-spacing:.3em; text-transform:uppercase; font-size:13px; margin-top:8px; }
.cover .v { color:#8fa3c7; margin-top:26px; font-size:14px; }
hr { border:0; border-top:1px solid var(--line); margin:22px 0; }
@media print {
  body { background:#fff; color:#222; font-size:11.5pt; } .wrap { display:block; padding:0; } nav, #q, #hits { display:none; } mark { background:none; color:inherit; }
  h1 { color:#111; page-break-before:always; border:0; } h1:first-of-type { page-break-before:avoid; } h2 { color:#0b4f9c; } h3 { color:#0a7a66; }
  code { color:#0b4f9c; background:#eef3fa; } pre { background:#f4f6fa; color:#222; border-color:#ccd; }
  figure { page-break-inside:avoid; } figure img { box-shadow:none; border-color:#ccd; }
  .note { background:#eef3fa; border-color:#0b4f9c; } .warn { background:#fdf3e6; border-color:#d98a2b; }
  th { color:#0a7a66; border-color:#ccd; } td { border-color:#dde; } figcaption { color:#555; }
  .cover { page-break-after:always; padding-top:0; } .cover .t { color:#111; } .cover img.shot { box-shadow:none; border-color:#ccd; max-width:100%; } .colophon { color:#555; } a { color:#0b4f9c; text-decoration:none; }
}
"""


def build_html():
    ver = version()
    chapters = sorted(CHAPTERS.glob("*.md"))
    if not chapters:
        sys.exit("no chapters in " + str(CHAPTERS))
    missing, body, toc, index = [], [], [], []
    for n, ch in enumerate(chapters, 1):
        text = ch.read_text(encoding="utf-8")
        title = next((l[2:].strip() for l in text.split("\n") if l.startswith("# ")), ch.stem)
        toc.append('<a href="#ch-%02d">%d. %s</a>' % (n, n, inline(title)))
        for l in text.split("\n"):
            if l.startswith("## "):
                t = l[3:].strip()
                toc.append('<a class="l2" href="#ch-%02d-%s">%s</a>' % (n, re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-"), inline(t)))
        chapter_html = md_to_html(text, missing, n)
        body.append(chapter_html)
        index.extend(index_entries(chapter_html, "%d. %s" % (n, title)))
    OUT_INDEX.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    render_cover(ver)
    sp = splash_texts()
    cover_img = ('<img class="shot" src="data:image/png;base64,%s" alt="The CrystalPilot loading screen">' % base64.b64encode(COVER_PNG.read_bytes()).decode("ascii")) if COVER_PNG.exists() else ""
    cover = ('<div class="cover">%s<div class="t">%s</div><div class="s">%s</div><div class="v">User manual &middot; Version %s &middot; %s</div></div>'
             % (cover_img, sp["name"], sp["sub"], ver, sp["credit"]))
    colophon = ('<div class="colophon"><hr><b>About this manual.</b> The screenshots were taken automatically on a real data set, and the cover is the program\'s loading screen. '
                'This manual was written with %s. '
                'CrystalPilot is free software under the GNU General Public License v3, without any warranty.</div>' % WRITTEN_WITH)
    page = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>CrystalPilot manual %s</title>"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><style>%s</style></head><body>"
            "%s"
            "<div class=\"wrap\"><nav><input id=\"q\" type=\"search\" placeholder=\"Search the manual\u2026 (Ctrl+K)\" autocomplete=\"off\">"
            "<div id=\"hits\" style=\"display:none\"></div><div id=\"toc\">%s</div></nav><main>%s%s</main></div><script>%s</script></body></html>") % (ver, CSS, cover, "".join(toc), "\n".join(body), colophon, SEARCH_JS)
    OUT_HTML.write_text(page, encoding="utf-8")
    print("wrote %s (%d chapters, %.1f MB) and %s (%d sections)" % (OUT_HTML.name, len(chapters), OUT_HTML.stat().st_size / 1e6, OUT_INDEX.name, len(index)))
    if missing:
        print("missing screenshots (%d): %s" % (len(missing), ", ".join(sorted(set(missing)))))
    return missing


def build_pdf():
    exe = browser()
    if not exe:
        print("no Edge/Chrome found: PDF skipped (set CP_BROWSER)"); return False
    url = OUT_HTML.resolve().as_uri()
    ok, why = headless(exe, "--print-to-pdf=", url, OUT_PDF, 10000, 300, extra=("--no-pdf-header-footer",))
    print("wrote %s (%.1f MB)" % (OUT_PDF.name, OUT_PDF.stat().st_size / 1e6) if ok
          else "PDF failed, the previous PDF is unchanged: " + why)
    return ok


def capture():
    """Start the battery's real-chain server (kept alive), run capture.js against it, stop it."""
    script = ROOT / "files" / "tests" / "api" / "api_tests.sh"
    build = sorted((ROOT / "files").glob("xds-gui-v*.py"), key=lambda p: int(re.search(r"v(\d+)", p.name).group(1)))[-1]
    win = os.name == "nt"
    wp = lambda p: subprocess.run(["wsl.exe", "-e", "wslpath", "-u", str(p)], capture_output=True, text=True).stdout.strip() if win else str(p)
    env_kv = ["APP=" + wp(build), "CP_REAL_XSCALE=1", "CP_REAL_XDS=1", "CP_KEEP_SERVER=1", "CP_SKIP_BASIC=1",
              "CP_REAL_IMPORT=" + os.environ.get("CP_MANUAL_PROJECT", "test"), "CP_SKIP_RERUNS=1", "CP_SKIP_AUTOPILOT=1"]
    cmd = (["wsl.exe", "-u", "root", "-e", "env"] + env_kv + ["bash", wp(script)]) if win else ["env"] + env_kv + ["bash", str(script)]
    print("starting the processed test project (about 6 minutes): " + " ".join(cmd))
    api = subprocess.Popen(cmd, cwd=str(ROOT / "files"), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1)
    ready = None
    for line in api.stdout:
        sys.stdout.write("   " + line)
        if line.startswith("SERVER_READY"):
            ready = dict(kv.split("=", 1) for kv in line.split()[1:]); break
    if not ready:
        api.wait(); sys.exit("the test server did not come up")
    master = ready.get("master", "")   # the real master file of the imported project (printed by api_tests.sh)
    env = dict(os.environ, CP_UI_URL="http://127.0.0.1:" + ready.get("port", "8082"), CP_UI_PROJECT="real", CP_UI_MASTER=master,
               CP_SKIP_STEPS=os.environ.get("CP_SKIP_STEPS", "14-02"))   # the AutoPilot result picture is the 60-frame wedge example
    rc = subprocess.run([shutil.which("node") or "node", str(HERE / "capture.js")] + sys.argv[2:], env=env).returncode
    stop = ["wsl.exe", "-u", "root", "-e", "touch", ready.get("dir", "/tmp/cp_api_d") + "/stop"] if win else ["touch", ready.get("dir", "/tmp/cp_api_d") + "/stop"]
    subprocess.run(stop); api.stdout.read(); api.wait()
    return rc == 0


if __name__ == "__main__":
    args = sys.argv[1:]
    ok = True
    if "--capture" in args:
        ok = capture()
    missing = build_html()
    if "--no-pdf" not in args:
        build_pdf()
    sys.exit(0 if ok and not missing else 1)
