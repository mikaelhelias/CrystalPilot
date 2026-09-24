#!/usr/bin/env node
/* Screenshot capture for the CrystalPilot illustrated manual.
 *
 * Drives the real interface in headless Edge/Chrome (DevTools protocol) against
 * a server whose project has been processed (the battery's real-chain server:
 * tests/api/api_tests.sh with CP_REAL_XDS=1 CP_KEEP_SERVER=1, or any server
 * with a finished project).  For every step of STEPS it performs the action,
 * outlines the controls being described, and saves a cropped PNG to images/.
 *
 *   CP_UI_URL=http://127.0.0.1:8082 CP_UI_PROJECT=real CP_UI_MASTER=/path/x_master.h5 node docs/manual/capture.js [ids...]
 *
 * Re-run any time; the manual is rebuilt from the images by build_manual.py.
 */
const { spawn, execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const URL_ = process.env.CP_UI_URL || "http://127.0.0.1:8082";
const PROJECT = process.env.CP_UI_PROJECT || "real";
const MASTER = process.env.CP_UI_MASTER || "";
const OUT = path.join(__dirname, "images");
const ONLY = new Set(process.argv.slice(2));
fs.mkdirSync(OUT, { recursive: true });
const W = 1440, Hh = 960;

// ── the shot list ────────────────────────────────────────────────────────────
// action: JS run in the page (await allowed); highlight: selectors to outline
// (numbered in order); crop: selector or JS expression returning an element,
// "viewport" for the whole window; wait: ms after the action.
const S = (id, o) => Object.assign({ id, wait: 1500, highlight: [], crop: "viewport" }, o);
const SIDEBAR = "document.querySelector('#project-name').closest('.sidebar') || document.querySelector('.sidebar')";
const DPCARD = "document.querySelector('#run-dir-name').closest('.card') || document.getElementById('project-details')";
const TABBAR = "document.getElementById('main-tab-btn-dp').parentElement";
const STEPS = [
  // 02 work modes: the tab bar and the parameter form at each level
  S("02-01-tabs-tutorial", { action: "setTier('tutorial'); switchMainTab('dp')", highlight: ["#prefs-tier-badge"], crop: TABBAR, cropPad: 16 }),
  S("02-02-tabs-normal", { action: "setTier('normal'); switchMainTab('dp')", highlight: [], crop: TABBAR, cropPad: 16 }),
  S("02-03-tabs-advanced", { action: "setTier('advanced'); switchMainTab('dp')", highlight: [], crop: TABBAR, cropPad: 16 }),
  S("02-04-tabs-expert", { action: "setTier('expert'); switchMainTab('dp')", highlight: [], crop: TABBAR, cropPad: 16 }),
  S("02-05-params-tutorial", { action: "setTier('tutorial'); switchMainTab('dp'); switchTab('params'); await loadParamsFromFile()", wait: 2000, highlight: [], crop: "#tab-params", maxHeight: 900 }),
  S("02-06-params-expert", { action: "setTier('expert'); switchMainTab('dp'); switchTab('params'); await loadParamsFromFile()", wait: 2000, highlight: [], crop: "#tab-params", maxHeight: 900 }),
  S("02-07-mode-selector", { action: "setTier('expert')", highlight: ["#prefs-tier-badge", "#tier-info-bar"], crop: SIDEBAR }),
  // 03 first launch / environment
  S("03-01-environment", { action: "envCheck(true)", wait: 3000, highlight: ["#envcheck .btn-primary"], crop: "#envcheck" }),
  S("03-02-work-mode", { action: "envClose(); switchMainTab('dp')", highlight: ["#prefs-tier-badge", "#xds-path-input"], crop: SIDEBAR }),
  S("03-03-cpu-ram", { action: "envClose(); switchMainTab('dp'); document.getElementById('res-cpu').scrollIntoView({ block: 'center' })", wait: 800,
                       highlight: ["#res-cpu", "#res-ram"], crop: "document.getElementById('res-cpu').closest('.sidebar-section')", cropPad: 12 }),
  // 04 projects
  S("04-01-create-project", { action: "document.getElementById('project-name').value = 'lysozyme_1'; document.getElementById('project-desc').value = 'Pilatus 6M, 0.1 deg, 1800 frames';", highlight: ["#project-name", "button[onclick='createProject()']"], crop: SIDEBAR }),
  S("04-02-project-open", { action: "document.getElementById('project-name').value = ''; document.getElementById('project-desc').value = ''; await loadProject(PROJECT); switchMainTab('dp')", wait: 2500, highlight: ["#project-list", "#current-name"], crop: "viewport" }),
  S("04-03-open-folder", { action: "switchMainTab('dp')", highlight: ["button[onclick='openProjectFolder()']", "#rundir-status"], crop: "viewport" }),
  // 05 XDS.INP
  S("05-01-key-parameters", { action: "switchMainTab('dp'); switchTab('params'); await loadParamsFromFile()", wait: 2000, highlight: ["#p-name-template", "button[onclick=\"browseFolder('name-template')\"]"], crop: "#tab-params" }),
  S("05-02-generate", { action: "switchTab('params')", highlight: ["button[onclick*='generateFromImages'], button[onclick*='Generate'], button[onclick*='generate']"], crop: "#tab-params" }),
  S("05-03-toggles", { action: "switchTab('params')", highlight: ["#tog-sgnum", "#tog-uc", "button[onclick='fetchFromIdxref()']"], crop: "#p-sgnum", cropPad: 40 }),
  S("05-04-save", { action: "switchTab('params')", highlight: ["button[onclick='saveParams()']", "button[onclick='loadParamsFromFile()']", "button[onclick=\"browseFolder('load-xdsinp')\"]"], crop: "button[onclick='saveParams()']", cropPad: 40 }),
  S("05-05-full-file", { action: "switchTab('full'); await loadFullINP()", wait: 2000, highlight: [], crop: "#tab-full" }),
  // 06 index
  S("06-01-run-buttons", { action: "switchTab('params'); document.getElementById('pipeline').scrollIntoView({block:'start'}); window.scrollBy(0, -80)", highlight: ["#btn-run-idxref", "#pipeline"], crop: "#pipeline", cropPad: 20, maxHeight: 760 }),
  S("06-02-live-log", { action: "switchTab('params'); runStep('XYCORR'); for (let i = 0; i < 40; i++) { await new Promise(r => setTimeout(r, 250)); const lp = document.getElementById('log-panel'); if (lp && lp.style.display !== 'none' && (document.getElementById('log-content') || {}).textContent.length > 40) break; }", wait: 1500, highlight: ["#log-content", "#btn-stop"], crop: "#log-panel", cropPad: 30, maxHeight: 700 }),
  S("06-03-idxref-metrics", { action: "await new Promise(r => setTimeout(r, 6000)); switchTab('lp'); await viewLPForStep('IDXREF')", wait: 3000, highlight: ["#metrics-step"], crop: "#tab-lp" }),
  S("06-04-idxref-lattices", { action: "", wait: 500, highlight: [], crop: "Array.from(document.querySelectorAll('#tab-lp table')).find(t => /Complete/i.test(t.textContent) && /R-meas|Rmeas/i.test(t.textContent)) || document.querySelector('#tab-lp table')", cropPad: 30 }),
  S("06-05-cell-picker", { action: "switchTab('params'); await fetchFromIdxref()", wait: 2500, highlight: [], crop: "document.querySelector('#idxref-modal .modal-content-anim') || document.querySelector('#idxref-modal > div') || document.querySelector('.modal-content-anim')", cropPad: 8 }),
  S("06-06-autoindex", { action: "document.querySelectorAll('#idxref-modal, .modal').forEach(m => m.style.display='none'); switchTab('lp'); await viewLPForStep('IDXREF')", wait: 3000, highlight: ["#ai-btn-quick", "#ai-btn-full", "#ai-btn-forcecell"], crop: "#autoindex-card", cropPad: 16 }),
  // 07 integrate & correct
  S("07-01-run-folder", { action: "switchTab('params'); document.getElementById('run-dir-name').scrollIntoView({block:'center'})", highlight: ["#run-dir-name", "input[name='run-mode'][value='subfolder']", "#rundir-status"], crop: "#run-dir-name", cropPad: 40 }),
  S("07-02-integrate-button", { action: "switchTab('params')", highlight: ["#btn-run-integrate", "#btn-run-correct-only", "#btn-run-reintegrate"], crop: "#btn-run-idxref", cropPad: 40 }),
  S("07-03-correct-metrics", { action: "switchTab('lp'); await viewLPForStep('CORRECT')", wait: 3500, highlight: [], crop: "#tab-lp" }),
  S("07-04-correct-table", { action: "", wait: 300, highlight: [], crop: "Array.from(document.querySelectorAll('#tab-lp table')).find(t => /Complete/i.test(t.textContent) && /R-meas|Rmeas/i.test(t.textContent)) || document.querySelector('#tab-lp table')", cropPad: 30 }),
  S("07-05-correct-charts", { action: "const c = document.querySelector('#tab-lp canvas'); if (c) c.scrollIntoView({block:'center'})", wait: 800, highlight: [], crop: "document.querySelector('#tab-lp canvas') ? document.querySelector('#tab-lp canvas').closest('div') : document.getElementById('tab-lp')", cropPad: 60 }),
  S("07-06-cutoffs", { action: "", wait: 400, highlight: [], crop: "(function(){ const h = Array.from(document.querySelectorAll('#tab-lp div, #lp-metrics div, div')).find(d => d.children.length === 0 && /^Resolution Cutoff Estimates/.test(d.textContent.trim())); return h ? h.parentElement : null; })()", cropPad: 16 }),
  S("07-07-matthews", { action: "const m = document.getElementById('matthews-panel'); if (m) { const i = m.querySelector('input'); if (i) { i.value = '30000'; i.dispatchEvent(new Event('input')); } const b = m.querySelector('button'); if (b) b.click(); }", wait: 2500, highlight: ["#matthews-panel input", "#matthews-panel button"], crop: "#matthews-panel", cropPad: 20, maxHeight: 600 }),
  S("07-08-integrate-metrics", { action: "await viewLPForStep('INTEGRATE')", wait: 3500, highlight: [], crop: "#tab-lp" }),
  // 08 compare
  S("08-01-history", { action: "await showRunHistory('correct')", wait: 2500, highlight: [], crop: "document.querySelector('#chart-modal .modal-content-anim') || document.querySelector('#chart-modal > div') || document.getElementById('chart-modal')", cropPad: 8 }),
  S("08-02-compare-buttons", { action: "document.getElementById('chart-modal').style.display = 'none'; await viewLPForStep('CORRECT')", wait: 2500, highlight: ["button[onclick*='showRunHistory']", "button[onclick*='showCompareCorrect']", "a[href*='export-data'], button[onclick*='export']"], crop: "button[onclick*='showRunHistory']", cropPad: 40 }),
  // 09 pointless
  S("09-01-pointless", { action: "switchMainTab('pointless'); await ptlLoadCachedResults()", wait: 3000, highlight: ["#ptl-run-btn"], crop: "viewport" }),
  S("09-02-pointless-results", { action: "document.getElementById('ptl-results').scrollIntoView({block:'start'})", wait: 600, highlight: ["button[onclick='ptlApplyAndRerunCorrect()']", "button[onclick='ptlApplyToXDS()']"], crop: "#ptl-results", cropPad: 20 }),
  // 10 deltacc
  S("10-01-deltacc", { action: "switchMainTab('deltacc'); await dccLoadCachedResults()", wait: 2500, highlight: ["#dcc-run-btn"], crop: "viewport" }),
  // 11 xscale
  S("11-01-xscale-params", { action: "switchMainTab('xscale'); xsSwitchTab('params'); await xsLoadParams()", wait: 2500, highlight: ["button[onclick='xsAutoDetect()']", "button[onclick='xsAutofillFromCorrect()']"], crop: "#xs-tab-params" }),
  S("11-02-xscale-save-run", { action: "", wait: 300, highlight: ["button[onclick='xsUpdateParams()']", "button[onclick='xsSaveParamsNew()']"], crop: "button[onclick='xsUpdateParams()']", cropPad: 40 }),
  S("11-05-xscale-run", { action: "", wait: 300, highlight: ["#btn-run-xscale", "button[onclick='xsGoToLP()']"], crop: "#btn-run-xscale", cropPad: 40 }),
  S("11-03-xscale-lp", { action: "xsSwitchTab('lp'); await xsViewLP()", wait: 3500, highlight: [], crop: "#xs-tab-lp" }),
  S("11-04-xscale-cutoffs", { action: "", wait: 400, highlight: [], crop: "(function(){ const h = Array.from(document.querySelectorAll('#xs-tab-lp div')).find(d => d.children.length === 0 && /^Resolution Cutoff Estimates/.test(d.textContent.trim())); return h ? h.parentElement : null; })()", cropPad: 16 }),
  // 12 xdsconv
  S("12-01-xdsconv", { action: "switchMainTab('xdsconv'); xcSwitchTab('params'); await xcLoadParams()", wait: 2500, highlight: ["#xc-input-file", "button[onclick='xcAutoInputFile()']", "#btn-run-xdsconv", "#btn-run-gemmi"], crop: "#xc-tab-params" }),
  S("12-02-xdsconv-lp", { action: "xcSwitchTab('lp'); await xcViewLP()", wait: 2500, highlight: [], crop: "#xc-tab-lp" }),
  // 13 aimless
  S("13-01-aimless", { action: "switchMainTab('aimless'); await amlLoadCachedResults()", wait: 3500, highlight: ["#aml-run-btn"], crop: "viewport" }),
  S("13-02-aimless-results", { action: "document.getElementById('aml-results').scrollIntoView({block:'start'})", wait: 800, highlight: [], crop: "#aml-results", cropPad: 20, maxHeight: 1400 }),
  // 14 autopilot
  S("14-01-autopilot", { action: "switchMainTab('autopilot'); apwGo(0); window.scrollTo(0, 0)", wait: 3000, highlight: ["#apw-steps", "#apw-drop"], crop: "viewport" }),
  S("14-02-autopilot-results", { action: "document.getElementById('ap-results').scrollIntoView({block:'start'})", wait: 800, highlight: [], crop: "#ap-results", cropPad: 20, maxHeight: 1400 }),
  // 15 gemmi
  S("15-01-gemmi", { action: "switchMainTab('gemmi'); gmInit()", wait: 2500, highlight: ["#btn-gm-all"], crop: "viewport" }),
  S("15-02-gemmi-results", { action: "await gmRunAll()", wait: 6000, highlight: [], crop: "#gm-results", cropPad: 20, maxHeight: 1400 }),
  // 16 table 1
  S("16-01-table1", { action: "switchMainTab('table1'); await t1Load()", wait: 9000, highlight: ["button[onclick='t1CopyTSV()']", "button[onclick='t1CopyLatex()']", "button[onclick='t1ExportXlsx()']"], crop: "#main-tab-table1 .card", cropPad: 16, maxHeight: 1500 }),
  // 17 frame viewer
  S("17-01-frame-load", { action: "switchMainTab('fv'); document.getElementById('fv-file-path').value = MASTER; await fvLoadFrame()", wait: 12000, highlight: ["#fv-file-path", "button[onclick='fvLoadFromINP()']", "#fv-recent-btn"], crop: "viewport" }),
  S("17-02-frame-rings", { action: "try { fvToggleRings(); } catch (e) {}; try { _iceToggleFrameViewer(); } catch (e) {}; try { fvSetZoom(0.24); } catch (e) {}", wait: 2500, highlight: ["#fv-rings-btn", "#fv-ice-btn", "#fv-spots-btn", "#fv-save-btn"], crop: "document.getElementById('fv-rings-btn').closest('.card') || document.getElementById('fv-img-wrap').parentElement", cropPad: 10, maxHeight: 940 }),
  S("17-03-frame-header", { action: "document.getElementById('fv-header-info').scrollIntoView({block:'start'})", wait: 600, highlight: [], crop: "#fv-header-info", cropPad: 20, maxHeight: 900 }),
  // 18 docs
  S("18-01-docs", { action: "switchMainTab('docs'); window.scrollTo(0,0)", wait: 1200, highlight: ["#docs-toc"], crop: "viewport" }),
];

// ── browser plumbing (same as tests/ui/ui_pass.js) ───────────────────────────
function findBrowser() {
  const cands = [process.env.CP_BROWSER, "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe", "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Google/Chrome/Application/chrome.exe", "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/microsoft-edge"];
  for (const c of cands) if (c && fs.existsSync(c)) return c;
  throw new Error("no Edge/Chrome found; set CP_BROWSER");
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function main() {
  const browser = findBrowser();
  const port = 9400 + Math.floor(Math.random() * 400);
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "cp-cap-"));
  const proc = spawn(browser, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--hide-scrollbars", "--force-device-scale-factor=1",
    "--remote-debugging-port=" + port, "--user-data-dir=" + profile, `--window-size=${W},${Hh}`, "about:blank"], { stdio: "ignore" });
  let ws, id = 0; const pending = new Map();
  const send = (m, p = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method: m, params: p })); });
  let done = 0, failed = 0;
  try {
    let targets = null;
    for (let i = 0; i < 60 && !targets; i++) { try { targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); } catch (e) { await sleep(250); } }
    if (!targets) throw new Error("browser did not expose DevTools");
    const page = targets.find((t) => t.type === "page") || targets[0];
    ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.id && pending.has(d.id)) { const { res, rej } = pending.get(d.id); pending.delete(d.id); d.error ? rej(new Error(d.error.message)) : res(d.result); }
      else if (d.method === "Page.javascriptDialogOpening") send("Page.handleJavaScriptDialog", { accept: true }).catch(() => {});
    };
    await send("Page.enable"); await send("Runtime.enable");
    // (no Emulation.setDeviceMetricsOverride: it disables window scrolling in headless Edge)
    const evalJs = async (expr) => {
      const r = await send("Runtime.evaluate", { expression: `(async () => { const PROJECT = ${JSON.stringify(PROJECT)}; const MASTER = ${JSON.stringify(MASTER)}; ${expr} })()`, awaitPromise: true, returnByValue: true });
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    };
    // highlight helpers injected once
    const HELPERS = `
      window.__cpHL = function(sels) {
        window.__cpUnHL();
        const made = [];
        sels.forEach((sel, i) => {
          const el = window.__cpEl(sel);
          if (!el || el.offsetParent === null && el.tagName !== 'BODY') return;
          el.classList.add('cp-hl');
          const r = el.getBoundingClientRect();
          const b = document.createElement('div'); b.className = 'cp-hl-badge'; b.textContent = String(i + 1);
          b.style.cssText = 'position:fixed; z-index:99999; left:' + Math.max(0, r.left - 14) + 'px; top:' + Math.max(0, r.top - 14) + 'px; width:26px; height:26px; border-radius:50%; background:#ff5a36; color:#fff; font:700 15px/26px system-ui; text-align:center; box-shadow:0 2px 8px rgba(0,0,0,.6);';
          document.body.appendChild(b); made.push(b);
        });
        if (!document.getElementById('cp-hl-style')) { const s = document.createElement('style'); s.id = 'cp-hl-style'; s.textContent = '.cp-hl { outline: 3px solid #ff5a36 !important; outline-offset: 3px !important; border-radius: 6px; }'; document.head.appendChild(s); }
      };
      window.__cpUnHL = function() { document.querySelectorAll('.cp-hl').forEach(e => e.classList.remove('cp-hl')); document.querySelectorAll('.cp-hl-badge').forEach(e => e.remove()); };
      window.__cpEl = function(spec) { let el = null; try { el = (spec.startsWith('document.') || spec.startsWith('window.') || spec.startsWith('(') || spec.startsWith('Array.')) ? eval(spec) : document.querySelector(spec); } catch (e) {} return el; };
      // Frame a shot: the union of the crop target (if any) and of every highlighted element is
      // scrolled into view; for a crop the clip (page coordinates) covers that union plus padding.
      window.__cpFrame = function(spec, hl, pad, maxH) {
        const els = [];
        const target = spec === 'viewport' ? null : window.__cpEl(spec);
        if (spec !== 'viewport' && !target) return { clip: null, missing: true };
        if (target) els.push(target);
        (hl || []).forEach(s => { const e = window.__cpEl(s); if (e && e.offsetParent !== null) els.push(e); });
        if (!els.length) return { clip: null };
        const fixed = els.some(e => { let p = e; while (p && p !== document.body) { if (getComputedStyle(p).position === 'fixed') return true; p = p.parentElement; } return false; });
        const union = () => { let l = 1e9, t = 1e9, r = -1e9, b = -1e9; els.forEach(e => { const q = e.getBoundingClientRect(); if (q.width < 2 || q.height < 2) return; l = Math.min(l, q.left); t = Math.min(t, q.top); r = Math.max(r, q.right); b = Math.max(b, q.bottom); }); return r < l ? null : { left: l, top: t, right: r, bottom: b, width: r - l, height: b - t }; };
        let u = union(); if (!u) return { clip: null, missing: true };
        if (!fixed) {
          const H = window.innerHeight, need = u.height + 2 * pad;
          if (spec === 'viewport') {
            if (u.top - pad < 0 || u.bottom + pad > H) window.scrollBy({ top: need >= H ? u.top - pad : u.top - (H - u.height) / 2, left: 0, behavior: 'instant' });
          } else {
            window.scrollBy({ top: u.top - pad, left: 0, behavior: 'instant' });
          }
          u = union();
        }
        if (spec === 'viewport') return { clip: null };
        const vx = Math.max(0, u.left - pad), vy = Math.max(0, u.top - pad);
        const w = Math.min(window.innerWidth - vx, u.right + pad - vx), h = Math.min(maxH || 100000, Math.min(window.innerHeight - vy, u.bottom + pad - vy));
        return { clip: { x: vx + window.scrollX, y: vy + window.scrollY, width: Math.max(200, w), height: Math.max(120, h) } };
      };`;
    await send("Page.navigate", { url: URL_ + "/" });
    let ready = false;
    for (let i = 0; i < 80 && !ready; i++) { await sleep(500); try { ready = await evalJs(`return typeof loadProject === 'function' && !!document.getElementById('project-list')`); } catch (e) {} }
    if (!ready) throw new Error("app not ready");
    await sleep(2500);
    await evalJs(HELPERS);
    await evalJs(`try { const s = document.getElementById('splash'); if (s) s.style.display = 'none'; } catch (e) {}; try { envClose(); } catch (e) {}; await loadProject(PROJECT); try { setTier('expert'); } catch (e) {}`);
    // overlays lock body scrolling while they are up; make sure the page can scroll for the crops
    await evalJs(`document.documentElement.style.scrollBehavior = 'auto'; document.body.style.scrollBehavior = 'auto'; document.documentElement.style.overflow = 'auto'; document.body.style.overflow = 'auto'; document.body.style.height = 'auto'; document.body.classList.remove('modal-open', 'no-scroll');`);
    if (process.env.CP_DEBUG) console.log("     body overflow: " + await evalJs(`return getComputedStyle(document.body).overflowY + '/' + getComputedStyle(document.documentElement).overflowY + ' h=' + document.documentElement.scrollHeight + ' inner=' + window.innerHeight + ' autoindex=' + !!document.getElementById('autoindex-card')`));
    await sleep(2500);

    if (process.env.CP_EVAL) {   // debugging aid: evaluate an expression in the page and print the result
      console.log("CP_EVAL -> " + JSON.stringify(await evalJs(process.env.CP_EVAL)));
      return;
    }
    for (const st of STEPS) {
      if (process.env.CP_ONLY_STEPS && !process.env.CP_ONLY_STEPS.split(",").includes(st.id.slice(0, 5))) continue;
      if ((process.env.CP_SKIP_STEPS || "").split(",").includes(st.id.slice(0, 5))) { console.log("  -- " + st.id + " skipped (existing picture kept)"); continue; }
      if (ONLY.size && !ONLY.has(st.id)) continue;
      try {
        if (st.action) await evalJs(st.action);
        await sleep(st.wait);
        const pad = st.cropPad || (st.crop === "viewport" ? 40 : 16);
        let fr = await evalJs(`return window.__cpFrame(${JSON.stringify(st.crop)}, ${JSON.stringify(st.highlight)}, ${pad}, ${st.maxHeight || 0})`);
        await sleep(200);
        fr = await evalJs(`return window.__cpFrame(${JSON.stringify(st.crop)}, ${JSON.stringify(st.highlight)}, ${pad}, ${st.maxHeight || 0})`);   // settle after the scroll
        if (fr.missing) console.log("     (crop target not found for " + st.id + ", using the viewport)");
        const clip = fr.clip;
        if (st.highlight.length) await evalJs(`window.__cpHL(${JSON.stringify(st.highlight)})`);   // badges are drawn for the final scroll position
        await sleep(250);
        const params = { format: "png" };
        if (clip) params.clip = Object.assign({ scale: 1 }, clip);
        if (process.env.CP_DEBUG) console.log("     clip " + st.id + " " + JSON.stringify(clip) + " scroll=" + JSON.stringify(await evalJs(`return [window.scrollX, window.scrollY, document.documentElement.scrollHeight]`)));
        const shot = await send("Page.captureScreenshot", params);
        fs.writeFileSync(path.join(OUT, st.id + ".png"), Buffer.from(shot.data, "base64"));
        await evalJs(`window.__cpUnHL()`);
        done++; console.log("ok   " + st.id);
      } catch (e) {
        failed++; console.log("FAIL " + st.id + " -- " + e.message.slice(0, 300));
        try { await evalJs(`window.__cpUnHL()`); } catch (e2) {}
      }
    }
    console.log(`RESULT: ${done} captured, ${failed} failed -> ${OUT}`);
    process.exitCode = failed ? 1 : 0;
  } finally {
    try { ws && ws.close(); } catch (e) {}
    try { proc.kill(); } catch (e) {}
    await sleep(500);
    try { if (process.platform === "win32") execSync(`taskkill /PID ${proc.pid} /T /F`, { stdio: "ignore" }); } catch (e) {}
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) {}
  }
}
main().catch((e) => { console.log("FAIL capture crashed -- " + e.message); process.exit(2); });
