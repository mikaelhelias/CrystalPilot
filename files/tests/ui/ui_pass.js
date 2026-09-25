#!/usr/bin/env node
/* CrystalPilot regression battery - browser pass.
 *
 * Drives the real interface in headless Edge/Chrome through the DevTools
 * protocol: loads the page, opens the project, visits every main tab, triggers
 * the loaders behind each one (LP charts, XSCALE/XDSCONV logs, frame viewer on
 * the real master file, CCP4 result panels, Table 1, gemmi, history) and fails
 * on any JavaScript exception, on an expected chart that stayed blank, or on a
 * frame that did not render.  Screenshots go to tests/ui/out/.
 *
 *   CP_UI_URL=http://127.0.0.1:8082 CP_UI_PROJECT=real CP_UI_MASTER=/path/master.h5 node tests/ui/ui_pass.js
 *
 * Needs Node 22+ (global WebSocket) and msedge.exe / chrome / chromium.
 */
const { spawn, execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
// Temp folders go to <repo>/.tmp (the project's drive, ignored by git), not the system
// temp folder; leftovers of an interrupted run are removed at the next start.
const TMP = process.env.CP_TMP || path.join(__dirname, "../../..", ".tmp");
fs.mkdirSync(TMP, { recursive: true });
for (const old of fs.readdirSync(TMP)) {
  if (!/^cp\-ui\-/.test(old)) continue;
  try { if (Date.now() - fs.statSync(path.join(TMP, old)).mtimeMs > 3600e3) fs.rmSync(path.join(TMP, old), { recursive: true, force: true }); } catch (e) {}
}
const os = require("os");

const URL_ = process.env.CP_UI_URL || "http://127.0.0.1:8082";
const PROJECT = process.env.CP_UI_PROJECT || "real";
const MASTER = process.env.CP_UI_MASTER || "";
const OUT = path.join(__dirname, "out");
fs.mkdirSync(OUT, { recursive: true });

function findBrowser() {
  const cands = [process.env.CP_BROWSER,
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/microsoft-edge"];
  for (const c of cands) if (c && fs.existsSync(c)) return c;
  throw new Error("no Edge/Chrome found; set CP_BROWSER");
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const browser = findBrowser();
  const port = 9333 + Math.floor(Math.random() * 500);
  const profile = fs.mkdtempSync(path.join(TMP, "cp-ui-"));
  const proc = spawn(browser, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    "--remote-debugging-port=" + port, "--user-data-dir=" + profile, "--window-size=1500,1000", "about:blank"],
    { stdio: "ignore" });
  let ws, id = 0; const pending = new Map(); const events = [];
  try {
    let targets = null;
    for (let i = 0; i < 60 && !targets; i++) {
      try { targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); } catch (e) { await sleep(250); }
    }
    if (!targets) throw new Error("browser did not expose DevTools");
    const page = targets.find((t) => t.type === "page") || targets[0];
    ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    const dialogs = [];   // alert()/confirm() texts, auto-accepted so the pass never blocks
    const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.id && pending.has(d.id)) { const { res, rej } = pending.get(d.id); pending.delete(d.id); d.error ? rej(new Error(d.error.message)) : res(d.result); }
      else if (d.method === "Page.javascriptDialogOpening") { dialogs.push(d.params.message); send("Page.handleJavaScriptDialog", { accept: true }).catch(() => {}); }
      else if (d.method) events.push(d);
    };
    const evalJs = async (expr) => {
      const r = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
      if (r.exceptionDetails) throw new Error("page threw: " + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
      return r.result.value;
    };
    await send("Page.enable"); await send("Runtime.enable"); await send("Log.enable");

    const results = []; let failed = 0;
    const errorsSince = (mark) => events.slice(mark).filter((e) =>
      e.method === "Runtime.exceptionThrown" ||
      (e.method === "Runtime.consoleAPICalled" && e.params.type === "error") ||
      // network log entries (a 404 for a cache that does not exist yet is normal) are not script errors
      (e.method === "Log.entryAdded" && e.params.entry.level === "error" && e.params.entry.source !== "network" && !/favicon|ERR_ABORTED|net::ERR|Failed to load resource/.test(e.params.entry.text)))
      .map((e) => e.method === "Runtime.exceptionThrown" ? (e.params.exceptionDetails.exception?.description || e.params.exceptionDetails.text)
        : e.method === "Log.entryAdded" ? e.params.entry.text
        : e.params.args.map((a) => a.value || a.description || "").join(" "));
    const check = (name, ok, info) => { results.push({ name, ok, info }); console.log((ok ? "ok   " : "FAIL ") + name + (ok ? "" : " -- " + String(info).slice(0, 400))); if (!ok) failed++; };
    const shot = async (name) => { const r = await send("Page.captureScreenshot", { format: "png" }); fs.writeFileSync(path.join(OUT, name + ".png"), Buffer.from(r.data, "base64")); };
    const paintedCanvases = () => evalJs(`(() => {
      let n = 0, painted = 0;
      for (const cv of document.querySelectorAll('canvas')) {
        const r = cv.getBoundingClientRect(); if (r.width < 40 || r.height < 40 || cv.offsetParent === null) continue;
        n++;
        try { const ctx = cv.getContext('2d'); if (!ctx) continue;
          const d = ctx.getImageData(0, 0, cv.width, cv.height).data; let first = null, diff = false;
          for (let i = 0; i < d.length; i += 4 * 97) { const v = d[i] + d[i+1] * 256 + d[i+2] * 65536 + d[i+3] * 16777216; if (first === null) first = v; else if (v !== first) { diff = true; break; } }
          if (diff) painted++; } catch (e) {}
      }
      return { visible: n, painted }; })()`);
    const visibleErrors = () => evalJs(`Array.from(document.querySelectorAll('.status.error')).filter(e => e.offsetParent !== null).map(e => e.textContent.trim()).slice(0, 6)`);

    // ── load the page and the project ────────────────────────────────────
    let mark = events.length;
    await send("Page.navigate", { url: URL_ + "/" });
    let ready = false;
    for (let i = 0; i < 80 && !ready; i++) { await sleep(500); try { ready = await evalJs(`typeof loadProject === 'function' && typeof switchMainTab === 'function' && !!document.getElementById('project-list')`); } catch (e) {} }
    check("page loads and app functions are defined", ready, "app not ready after 40 s");
    await sleep(2500);   // splash / environment check
    check("no JavaScript errors while loading", errorsSince(mark).length === 0, errorsSince(mark).join(" | "));
    mark = events.length;
    // a fresh settings file means the first-launch Environment screen is up: dismiss it like a user would
    await evalJs(`(async () => { try { const s = document.getElementById('splash'); if (s) s.style.display = 'none'; } catch (e) {} ; try { if (typeof envClose === 'function') envClose(); } catch (e) {} ; await loadProject(${JSON.stringify(PROJECT)}); })()`);
    await sleep(2500);
    const cur = await evalJs(`typeof currentProject !== 'undefined' ? currentProject : null`);
    check("project opens", cur === PROJECT, "currentProject=" + cur + " " + errorsSince(mark).join(" | "));
    check("no JavaScript errors opening the project", errorsSince(mark).length === 0, errorsSince(mark).join(" | "));
    await shot("00_project");

    // ── Data processing: LP viewer charts, run history ───────────────────
    mark = events.length;
    await evalJs(`(async () => { switchMainTab('dp'); switchTab('lp'); await viewLPForStep('CORRECT'); })()`);
    await sleep(3500);
    let pc = await paintedCanvases();
    check("DP tab: CORRECT LP viewer draws charts", pc.painted >= 1, JSON.stringify(pc));
    check("DP tab: no JavaScript errors", errorsSince(mark).length === 0, errorsSince(mark).join(" | "));
    await shot("01_dp_correct_lp");
    mark = events.length;
    await evalJs(`(async () => { await viewLPForStep('IDXREF'); })()`); await sleep(2500);
    pc = await paintedCanvases();
    check("DP tab: IDXREF LP viewer draws charts", pc.painted >= 1, JSON.stringify(pc));
    await shot("02_dp_idxref_lp");
    // ── AutoPilot wizard: steps, folder drop, keyword order, choices from the server ──
    mark = events.length;
    const apw = await evalJs(`(async () => { if (typeof apwInit !== 'function') return { missing: true };
      switchMainTab('autopilot'); await new Promise(r => setTimeout(r, 2500));
      const noBatchTab = !document.getElementById('main-tab-btn-batch') && !document.getElementById('main-tab-batch');
      const visiblePages = () => Array.from(document.querySelectorAll('#main-tab-autopilot .apw-page')).filter(p => p.style.display !== 'none').map(p => p.getAttribute('data-page'));
      const firstPage = visiblePages();
      apwNext();                                   // no folder yet: stays on step 1
      const blocked = visiblePages()[0] === '0' && /folder/i.test(document.getElementById('apw-nav-msg').textContent);
      // a path dropped as text (from an address bar or a file manager that sends file:// URIs)
      const dt = new DataTransfer(); dt.setData('text/uri-list', 'file:///data/beamline/run%201');
      apwDrop({ preventDefault() {}, dataTransfer: dt });
      const dropped = _apwFolders.slice();
      const dt2 = new DataTransfer();              // a folder icon: no path the page can read
      apwDrop({ preventDefault() {}, dataTransfer: dt2 });
      const dropNote = /Drop folders/.test(document.getElementById('apw-folders-msg').textContent) && typeof apwLocateDropped === 'function';
      apwRemoveFolder(0);
      apwRenderFolders();
      const openBtn = /Add the open project/.test(document.getElementById('apw-open-project').textContent);
      await apwAddOpenProject();
      const addedProject = _apwProjects.length === 1 && _apwProjects[0].name === currentProject && !!_apwProjects[0].template;
      apwRemoveProject(0);
      apwResetKeywords(); apwMoveKeyword(2, -1);   // autoproc above processing
      document.getElementById('apw-keyword-input').value = 'XIA2'; apwAddKeyword();
      const keywords = _apwKeywords.slice();
      apwResetKeywords();
      const byStep = {};
      ['cutoffs', 'reprocessing', 'indexing'].forEach(s => { byStep[s] = Array.from(document.querySelectorAll('#apw-opt-' + s + ' [data-key]')).map(el => el.getAttribute('data-key')); });
      const dcc = document.querySelector('#apw-opt-reprocessing [data-key="dcc_half"]');
      const s0 = apwReadStrategy();
      document.querySelector('[data-key="sg_mode"]').value = 'fixed'; apwOptionsChanged();
      const cellShown = document.querySelector('#main-tab-autopilot [data-row="unit_cell"]').style.display !== 'none';
      const routeHidden = document.querySelector('#main-tab-autopilot [data-row="sg_route"]').style.display === 'none';
      document.querySelector('[data-key="sg_mode"]').value = 'auto'; apwOptionsChanged();
      apwGo(5); await new Promise(r => setTimeout(r, 800));   // the review waits for the data-set search
      const review = document.getElementById('apw-review').textContent;
      apwGo(0);
      switchMainTab('dp');
      return { noBatchTab, firstPage, blocked, dropped, dropNote, keywords, openBtn, addedProject, byStep, dccIsCheckbox: !!dcc && dcc.type === 'checkbox',
               defaults: { dcc: s0.dcc_half, route: s0.sg_route, crit: s0.criterion }, cellShown, routeHidden,
               reviewHasChoices: /Space group in an imported XDS\\.INP/.test(review) && /I\\/σ/.test(review) }; })()`);
    check("AutoPilot wizard: one tab (no Batch tab), six steps, Next needs a folder, dropped paths are added",
      !apw.missing && apw.noBatchTab && apw.firstPage.join() === '0' && apw.blocked && apw.dropped[0] === '/data/beamline/run 1' && apw.dropNote,
      JSON.stringify(apw));
    check("AutoPilot wizard: the open project can be added with its own XDS.INP",
      !apw.missing && apw.openBtn && apw.addedProject, JSON.stringify({ openBtn: apw.openBtn, addedProject: apw.addedProject }));
    check("AutoPilot wizard: keyword list is ordered and editable",
      !apw.missing && JSON.stringify(apw.keywords) === JSON.stringify(['fast_dp', 'autoproc', 'processing', 'xia2']), JSON.stringify(apw.keywords));
    check("AutoPilot wizard: choices land on their steps with AutoPilot's defaults, dependent fields follow, review lists them",
      !apw.missing && apw.byStep.cutoffs.indexOf('criterion') >= 0 && apw.byStep.reprocessing.indexOf('optimize') >= 0 && apw.byStep.indexing.indexOf('sg_route') >= 0
      && apw.dccIsCheckbox && apw.defaults.dcc === 'on' && apw.defaults.route === 'without_first' && apw.defaults.crit === 'isig2'
      && apw.cellShown && apw.routeHidden && apw.reviewHasChoices, JSON.stringify(apw));
    check("AutoPilot wizard: no JavaScript errors", errorsSince(mark).length === 0, errorsSince(mark).join(" | "));

    // ── report a problem: the dialog saves a report and says where it goes ──
    mark = events.length;
    const rep = await evalJs(`(async () => { if (typeof reportOpen !== 'function') return { missing: true };
      console.error('ui pass: a recorded page error');
      reportOpen(); await new Promise(r => setTimeout(r, 300));
      const tick = document.getElementById('report-project');
      const tickedByDefault = !!(tick && tick.checked);
      document.getElementById('report-text').value = 'ui pass: checking the problem report';
      await reportSave(); await new Promise(r => setTimeout(r, 3000));
      const res = document.getElementById('report-result');
      const link = res && res.querySelector('a[download]');
      let served = null;
      if (link) { const r = await fetch(link.getAttribute('href')); const blob = await r.blob(); served = { status: r.status, type: blob.type, size: blob.size }; }
      const hasAddress = !!(_reportLast && _reportLast.report_email);
      const mailButton = !!(res && Array.from(res.querySelectorAll('button')).some(b => /Open e-mail/.test(b.textContent)));
      const noAddressNote = !!(res && /no address for problem reports/.test(res.textContent));
      reportClose();
      return { tickedByDefault, served, recorded: (window._cpPageErrors || []).length, hasAddress, mailButton, noAddressNote }; })()`);
    check("Report: the dialog saves a report the browser can download, project files unticked by default",
      !rep.missing && rep.served && rep.served.status === 200 && rep.served.size > 500 && rep.tickedByDefault === false && rep.recorded >= 1,
      JSON.stringify(rep));
    // with an address the mail button appears; without one the page says so instead of offering a dead button
    check("Report: the send step matches whether an address is set",
      !rep.missing && (rep.hasAddress ? (rep.mailButton && !rep.noAddressNote) : (!rep.mailButton && rep.noAddressNote)),
      JSON.stringify(rep));

    // ── export: the button packs the project and the link serves the zip ──
    mark = events.length;
    const exp = await evalJs(`(async () => { if (typeof exportProject !== 'function') return { missing: true };
      await exportProject(false); await new Promise(r => setTimeout(r, 6000));
      const box = document.getElementById('export-msg');
      if (!box) return { noBox: true };
      const link = box.querySelector('a[download]');
      let served = null;
      if (link) { const r = await fetch(link.getAttribute('href')); const blob = await r.blob(); served = { status: r.status, type: blob.type, size: blob.size }; }
      return { text: box.textContent.replace(/\\s+/g, ' ').slice(0, 160), served }; })()`);
    check("Export: the project packs into a zip the browser can download",
      !exp.missing && !exp.noBox && exp.served && exp.served.status === 200 && exp.served.size > 2000,
      JSON.stringify(exp).slice(0, 300));
    check("Export: no JavaScript errors packing it", errorsSince(mark).length === 0, errorsSince(mark).join(" | "));

    // ── publication figures: the button writes them and the links serve them ──
    mark = events.length;
    const figs = await evalJs(`(async () => { if (typeof pubFigures !== 'function') return { missing: true };
      // the metrics section is rebuilt per step: the CORRECT one carries the button
      await viewLPForStep('CORRECT'); await new Promise(r => setTimeout(r, 2500));
      await pubFigures('correct'); await new Promise(r => setTimeout(r, 4000));
      const box = document.getElementById('pubfig-msg-correct');
      if (!box) return { noBox: true };
      const links = Array.from(box.querySelectorAll('a')).map(a => a.getAttribute('href'));
      let served = null;
      if (links.length) { const r = await fetch(links[0]); const blob = await r.blob(); served = { status: r.status, type: blob.type, size: blob.size }; }
      return { text: box.textContent.replace(/\\s+/g, ' ').slice(0, 200), links: links.length, served }; })()`);
    check("Figures: the button writes the PNGs and they can be downloaded",
      !figs.missing && !figs.noBox && figs.links === 10 && figs.served && figs.served.status === 200
      && figs.served.type === 'image/png' && figs.served.size > 5000, JSON.stringify(figs).slice(0, 300));
    check("Figures: no JavaScript errors writing them", errorsSince(mark).length === 0, errorsSince(mark).join(" | "));
    const gate = await evalJs(`(() => { if (typeof _figuresGate !== 'function') return { missing: true };
      _figuresGate();
      const btn = document.querySelector('button[onclick*="pubFigures"]');
      return { possible: _figuresPossible(), disabled: !!(btn && btn.disabled),
               modules: (_envData && _envData.modules) ? _envData.modules.matplotlib : null }; })()`);
    // this server has matplotlib (it just drew the figures), so the button must be live
    check("Figures: the button follows what the environment probe found",
      !gate.missing && gate.possible === true && gate.disabled === false, JSON.stringify(gate));

    mark = events.length;
    await evalJs(`(async () => { await showRunHistory('correct'); })()`); await sleep(2500);
    const histText = await evalJs(`(() => { const m = document.getElementById('chart-modal'); const b = document.getElementById('chart-modal-body'); const t = document.getElementById('chart-modal-title'); return (m && m.style.display !== 'none' && b) ? (t ? t.textContent : '') + ' | ' + b.textContent.slice(0, 200) : 'dialogs: ' + ${JSON.stringify(dialogs.join(" / "))}; })()`);
    check("DP tab: run history opens with content", /Run History/i.test(histText) && /\d/.test(histText), JSON.stringify(histText));
    const chartPng = await evalJs(`(async () => { if (typeof _openChartModal !== 'function' || typeof chartModalPng !== 'function') return { missing: true };
      const canvas = document.querySelector('#main-tab-dp canvas');
      if (!canvas || !canvas.onclick) return { noChart: true };
      canvas.onclick(); await new Promise(r => setTimeout(r, 600));
      const btn = document.getElementById('chart-modal-png');
      const shown = !!btn && btn.style.display !== 'none';
      // the saver must produce an opaque PNG of the size on screen
      const c = document.getElementById('chart-modal-canvas');
      const out = document.createElement('canvas'); out.width = c.width; out.height = c.height;
      const blob = await new Promise(res => { chartModalPng(); out.getContext('2d').drawImage(c, 0, 0); out.toBlob(res, 'image/png'); });
      document.getElementById('chart-modal').style.display = 'none';
      return { shown, w: c.width, h: c.height, bytes: blob ? blob.size : 0 }; })()`);
    check("Charts: the expanded chart offers a PNG and produces one",
      !chartPng.missing && !chartPng.noChart && chartPng.shown && chartPng.w > 300 && chartPng.bytes > 2000,
      JSON.stringify(chartPng));

    check("DP tab: history without JavaScript errors", errorsSince(mark).length === 0, errorsSince(mark).join(" | "));
    await shot("03_dp_history");
    await evalJs(`(() => { document.querySelectorAll('.modal, [id$="-modal"]').forEach(m => { m.style.display = 'none'; }); })()`);

    // ── Frame viewer on the real master file ─────────────────────────────
    mark = events.length;
    await evalJs(`switchMainTab('fv')`); await sleep(1500);
    if (MASTER) {
      await evalJs(`(async () => { const p = document.getElementById('fv-file-path'); p.value = ${JSON.stringify(MASTER)}; await fvLoadFrame(); })()`);
      let loaded = false;
      for (let i = 0; i < 60 && !loaded; i++) { await sleep(1000); loaded = await evalJs(`(() => { const im = document.getElementById('fv-image'); return !!(im && im.complete && im.naturalWidth > 100); })()`); }
      const st = await evalJs(`(document.getElementById('fv-status') || {}).textContent || ''`);
      check("Frame viewer: real frame rendered from the master file", loaded, "status=" + st + " " + errorsSince(mark).join(" | "));
      await evalJs(`(() => { try { fvToggleRings(); } catch (e) {} })()`); await sleep(1500);
      await shot("04_frame_viewer");
    } else {
      console.log("     (CP_UI_MASTER not set - frame render skipped)");
    }
    check("Frame viewer: no JavaScript errors", errorsSince(mark).length === 0, errorsSince(mark).join(" | "));

    // ── XSCALE ───────────────────────────────────────────────────────────
    mark = events.length;
    await evalJs(`(async () => { switchMainTab('xscale'); await xsLoadParams(); xsSwitchTab('lp'); await xsViewLP(); })()`); await sleep(3500);
    pc = await paintedCanvases();
    check("XSCALE tab: LP viewer draws charts", pc.painted >= 1, JSON.stringify(pc));
    check("XSCALE tab: no JavaScript errors", errorsSince(mark).length === 0, errorsSince(mark).join(" | "));
    await shot("05_xscale");

    // ── XDSCONV ──────────────────────────────────────────────────────────
    mark = events.length;
    await evalJs(`(async () => { switchMainTab('xdsconv'); await xcLoadParams(); xcSwitchTab('lp'); await xcViewLP(); })()`); await sleep(2500);
    const xcTxt = await evalJs(`(document.getElementById('xc-tab-lp') || {}).textContent || ''`);
    check("XDSCONV tab: LP shown", /XDSCONV/.test(xcTxt), xcTxt.slice(0, 200));
    check("XDSCONV tab: no JavaScript errors", errorsSince(mark).length === 0, errorsSince(mark).join(" | "));
    await shot("06_xdsconv");

    // ── POINTLESS / AIMLESS / ΔCC½ / AutoPilot / Table 1 / gemmi ─────────
    for (const [tab, name, extra, wantChart] of [
      ["pointless", "POINTLESS", "", false],
      ["aimless", "AIMLESS", "", true],
      ["deltacc", "ΔCC½", "", false],
      ["autopilot", "AutoPilot", "", false],
      ["table1", "Table 1", "await t1Load();", false],
      ["gemmi", "gemmi", "", false],
      ["guide", "Guide", "", false],
      ["docs", "Docs", "", false]]) {
      mark = events.length;
      await evalJs(`(async () => { switchMainTab(${JSON.stringify(tab)}); ${extra} })()`); await sleep(3000);
      const errs = errorsSince(mark);
      check(name + " tab: no JavaScript errors", errs.length === 0, errs.join(" | "));
      if (wantChart) { pc = await paintedCanvases(); check(name + " tab: result charts drawn", pc.painted >= 1, JSON.stringify(pc)); }
      const ve = await visibleErrors();
      if (ve.length) console.log("     note: visible error boxes on " + name + ": " + ve.join(" / ").slice(0, 300));
      await shot("07_" + tab);
    }
    // Docs tab: the illustrated manual itself, shown in the tab (filled when the tab opens), and its PDF
    mark = events.length;
    const man = await evalJs(`(async () => { const r = await fetch('/manual/'); const d = await r.json(); return { status: r.status, available: !!d.available, pdf: !!d.pdf }; })()`);
    await evalJs(`(async () => { switchMainTab('docs'); window.scrollTo(0, 0); })()`); await sleep(man.available ? 8000 : 1500);
    const docs = await evalJs(`(() => { const h = document.getElementById('docs-manual-host'); const r = h && h.shadowRoot;
      return { host: !!h, frames: document.querySelectorAll('#main-tab-docs iframe').length, chapters: r ? r.querySelectorAll('h1[id^="ch-"]').length : 0,
               toc: r ? r.querySelectorAll('#toc a').length : 0, images: r ? r.querySelectorAll('figure img').length : 0, pageHeight: document.body.scrollHeight,
               pdf: (document.getElementById('docs-manual-pdf') || {}).style ? document.getElementById('docs-manual-pdf').style.display : 'missing',
               note: (document.getElementById('docs-manual-note') || {}).textContent || '' }; })()`);
    check("Docs tab: " + (man.available ? "the illustrated manual on the page (all chapters, contents, pictures), no frame, PDF link" : "says the manual is not installed"),
      man.status === 200 && docs.host && docs.frames === 0 && (man.available
        ? (docs.chapters >= 18 && docs.toc >= 18 && docs.images >= 20 && docs.pageHeight > 20000 && (!man.pdf || docs.pdf === ""))
        : /Not installed/.test(docs.note)), JSON.stringify(docs));
    if (man.available) {
      // a contents link scrolls the page to its chapter
      const jump = await evalJs(`(async () => { const r = document.getElementById('docs-manual-host').shadowRoot; const a = r.querySelector('#toc a[href="#ch-11"]');
        window.scrollTo(0, 0); a.click(); await new Promise(res => setTimeout(res, 1500)); const t = r.getElementById('ch-11').getBoundingClientRect().top;
        const n = r.querySelector('nav').getBoundingClientRect();
        return { top: Math.round(t), scrollY: Math.round(window.scrollY), navTop: Math.round(n.top) }; })()`);
      check("Docs tab: a contents link scrolls the page to its chapter, the contents list stays in view", jump.scrollY > 1000 && jump.top > -60 && jump.top < 400 && jump.navTop >= 0 && jump.navTop < 150, JSON.stringify(jump));
    }

    // ── the Ask bar in the header: ranking, the context line, its own window ──
    // window.open needs a user gesture; Runtime.evaluate can carry one.
    const evalGesture = async (expr) => {
      const r = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true, userGesture: true });
      if (r.exceptionDetails) throw new Error("page threw: " + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
      return r.result.value;
    };
    const ask = await evalJs(`(async () => { const b = document.getElementById('askbar-in'); if (!b) return { missing: true };
      // the Environment screen opens on a timer after the splash and may come up after the
      // start-up dismissal; it is a modal over everything, so close it as a user would
      try { if (typeof envClose === 'function') envClose(); } catch (e) {}
      window.scrollTo(0, 0); b.value = 'xscale cut-off'; cpAskRender('xscale cut-off'); await new Promise(r => setTimeout(r, 500));
      const pop = document.getElementById('askbar-pop'), rows = Array.from(pop.querySelectorAll('a.ds-hit'));
      // the first rows must be on top of the page, not cut off by the header (0.6.6c showed one and a half)
      const clickable = rows.slice(0, 3).filter(r => { const q = r.getBoundingClientRect();
        const e = document.elementFromPoint(q.left + q.width / 2, q.top + Math.min(q.height / 2, 20)); return q.height > 0 && e && r.contains(e); }).length;
      const cover = rows[0] ? (function (q) { const e = document.elementFromPoint(q.left + q.width / 2, q.top + 10); return e ? (e.id || e.className || e.tagName) : null; })(rows[0].getBoundingClientRect()) : null;
      return { shown: pop.style.display !== 'none', rows: rows.length, marks: pop.querySelectorAll('mark').length, clickable, cover,
               top: (rows[0] || {}).textContent || '', snippets: rows.filter(r => r.querySelector('.ds-snip')).length }; })()`);
    check("Ask bar: the header search ranks the documentation and shows the matching sentence",
      !ask.missing && ask.shown && ask.rows >= 3 && ask.marks >= 2 && /XSCALE/i.test(ask.top) && ask.snippets === ask.rows && ask.clickable === 3,
      JSON.stringify(ask).slice(0, 300));
    // one window per gesture is all a browser grants, so ask twice
    const docWin = await evalGesture(`(() => {
      const w = cpdsOpenDocs('doc-quick-guide', ['xscale'], 'xscale');   // the Guide tab: the Docs tab holds only the manual
      if (!w) return { opened: false };
      const doc = { title: w.document.title, marks: w.document.querySelectorAll('mark').length,
                    card: !!w.document.querySelector('.card'), scripts: w.document.querySelectorAll('script').length,
                    back: /Open in the Docs tab/.test(w.document.body.textContent) };
      w.close();
      return { opened: true, doc };
    })()`);
    check("Ask bar: a Guide hit opens in its own window, marked and self-contained",
      docWin.opened && docWin.doc.card && docWin.doc.marks >= 1 && docWin.doc.scripts === 0 && docWin.doc.back && /Quick Guide/i.test(docWin.doc.title),
      JSON.stringify(docWin).slice(0, 300));
    const manWin = await evalGesture(`(() => {
      const m = cpdsPopup('/manual/CrystalPilot-Manual.html?q=xscale#ch-11', 'cpmanualcheck', 900, 700);
      const ok = !!m; if (m) m.close(); return ok;
    })()`);
    check("Ask bar: a manual hit opens the manual in its own window", manWin === true, String(manWin));
    await evalJs(`(() => { const b = document.getElementById('askbar-in'); b.value = ''; cpAskRender(''); })()`);
    await evalJs(`(async () => { switchMainTab('docs'); window.scrollTo(0, 0); })()`); await sleep(800);
    await shot("07_docs");
    check("Docs tab: no JavaScript errors", errorsSince(mark).length === 0, errorsSince(mark).join(" | "));
    await evalJs(`(async () => { switchMainTab('dp'); switchMainTab('autopilot'); })()`); await sleep(3500);
    const apTxt = await evalJs(`(() => { const r = document.getElementById('ap-results'), card = document.getElementById('apw-detail'); return r && r.style.display !== 'none' && card.style.display !== 'none' ? r.textContent.slice(0, 300) : ''; })()`);
    check("AutoPilot tab: cached results of the run are shown", /\d/.test(apTxt) && apTxt.length > 20, JSON.stringify(apTxt));
    await shot("07_autopilot_results");
    const t1 = await evalJs(`(document.getElementById('table1-output') || document.getElementById('t1-table') || document.querySelector('[id^="t1-"]') || {}).textContent || ''`);
    check("Table 1: statistics rendered", /Resolution|Completeness|R.?meas|CC/i.test(t1), t1.slice(0, 200));

    // ── Environment / About ──────────────────────────────────────────────
    mark = events.length;
    await evalJs(`(async () => { try { await envCheck(true); } catch (e) {} })()`); await sleep(2500);
    const envTxt = await evalJs(`(document.getElementById('env-rows') || document.getElementById('envcheck') || document.body).textContent`);
    check("Environment screen lists XDS", /XDS/.test(envTxt), "");
    check("Environment screen: no JavaScript errors", errorsSince(mark).length === 0, errorsSince(mark).join(" | "));
    await shot("08_environment");

    fs.writeFileSync(path.join(OUT, "results.json"), JSON.stringify(results, null, 2));
    console.log(`RESULT: ${results.length - failed} passed, ${failed} failed  (screenshots in ${OUT})`);
    process.exitCode = failed ? 1 : 0;
  } finally {
    try { ws && ws.close(); } catch (e) {}
    try { proc.kill(); } catch (e) {}
    await sleep(500);
    try { if (process.platform === "win32") execSync(`taskkill /PID ${proc.pid} /T /F`, { stdio: "ignore" }); } catch (e) {}
    try { fs.rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 300 }); } catch (e) {}   // Edge may still hold files for a moment
  }
}

main().catch((e) => { console.log("FAIL browser pass crashed -- " + e.message); process.exit(2); });
