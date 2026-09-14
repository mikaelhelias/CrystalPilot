#!/usr/bin/env node
/* Screenshot capture for the repository README (docs/readme/images), no markers.
 * Same plumbing as docs/manual/capture.js.
 *
 * Drives the real interface in headless Edge/Chrome (DevTools protocol) against
 * a server whose project has been processed (the battery's real-chain server:
 * tests/api/api_tests.sh with CP_REAL_XDS=1 CP_KEEP_SERVER=1, or any server
 * with a finished project).  For every step of STEPS it performs the action
 * and saves a cropped PNG to images/.
 *
 *   CP_UI_URL=http://127.0.0.1:8082 CP_UI_PROJECT=real CP_UI_MASTER=/path/x_master.h5 CP_UI_FOLDER=/path/to/datasets node docs/readme/capture_readme.js [ids...]
 *
 * Re-run any time; README.md links the pictures directly.
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

// ── the shot list (README pictures: no markers) ─────────────────────────────
const S = (id, o) => Object.assign({ id, wait: 1500, highlight: [], crop: "viewport" }, o);
const TABBAR = "document.getElementById('main-tab-btn-dp').parentElement";
const OPEN_PANELS = "setTier('expert'); if (!document.getElementById('prefs-body').classList.contains('open') && getComputedStyle(document.getElementById('prefs-body')).display === 'none') togglePrefsPanel(); if (document.getElementById('cutpref-body').style.display === 'none') toggleCutprefPanel();";
const APW_WAIT = "for (let i = 0; i < 150; i++) { await new Promise(r => setTimeout(r, 1000)); if (/looked at/.test(document.getElementById('apw-search-summary').textContent)) break; }";
const STEPS = [
  S("overview", { action: "setTier('expert'); switchMainTab('dp'); switchTab('params'); window.scrollTo(0, 0)", wait: 2500, crop: "viewport" }),
  S("work-mode-cutoff", { action: OPEN_PANELS + " switchMainTab('dp'); window.scrollTo(0, 0)", wait: 1200, crop: "document.getElementById('prefs-body').closest('.prefs-section') || document.getElementById('prefs-body').parentElement", extra: ["#cutpref-section-box"], cropPad: 12 }),
  S("tier-tutorial", { action: "setTier('tutorial'); switchMainTab('dp'); window.scrollTo(0, 0)", crop: TABBAR, cropPad: 12 }),
  S("tier-normal", { action: "setTier('normal'); switchMainTab('dp')", crop: TABBAR, cropPad: 12 }),
  S("tier-advanced", { action: "setTier('advanced'); switchMainTab('dp')", crop: TABBAR, cropPad: 12 }),
  S("tier-expert", { action: "setTier('expert'); switchMainTab('dp')", crop: TABBAR, cropPad: 12 }),
  S("idxref-metrics", { action: "setTier('expert'); switchMainTab('dp'); switchTab('lp'); await viewLPForStep('IDXREF')", wait: 3500, crop: "#tab-lp", maxHeight: 940 }),
  S("correct-metrics", { action: "switchTab('lp'); await viewLPForStep('CORRECT')", wait: 3500, crop: "#tab-lp", maxHeight: 940 }),
  S("correct-charts", { action: "const c = document.querySelector('#tab-lp canvas'); if (c) c.scrollIntoView({block:'center'})", wait: 800, crop: "document.querySelector('#tab-lp canvas') ? document.querySelector('#tab-lp canvas').closest('div') : document.getElementById('tab-lp')", cropPad: 60 }),
  S("xdsinp-editor", { action: "switchTab('params'); await loadParamsFromFile()", wait: 2000, crop: "#tab-params", maxHeight: 940 }),
  S("xscale-analysis", { action: "switchMainTab('xscale'); xsSwitchTab('lp'); await xsViewLP()", wait: 4000, crop: "#xs-tab-lp", maxHeight: 940 }),
  S("xscale-cutoffs", { action: "", wait: 500, crop: "(function(){ const d = Array.from(document.querySelectorAll('#xs-tab-lp div')).find(e => e.children.length === 0 && /^Resolution Cutoff Estimates/.test(e.textContent.trim())); return d ? d.parentElement : null; })()", extra: ["document.querySelector('#xs-tab-lp canvas').closest('div')"], cropPad: 14 }),
  S("autopilot-xdsinp-search", { action: "switchMainTab('autopilot'); apwGo(0); apwAddFolder(" + JSON.stringify(process.env.CP_UI_FOLDER || "") + "); apwNext(); " + APW_WAIT, wait: 1500, crop: "document.getElementById('apw-datasets').closest('.card')", cropPad: 8, maxHeight: 940 }),
  S("autopilot-xdsinp-view", { action: "const i = _apwFound.findIndex(d => d.xdsinp); await apwViewXdsinp(i < 0 ? 0 : i)", wait: 2500, crop: "document.querySelector('#chart-modal .modal-content-anim') || document.querySelector('#chart-modal > div')", cropPad: 4 }),
  S("frame-viewer", { action: "document.getElementById('chart-modal').style.display = 'none'; switchMainTab('fv'); document.getElementById('fv-file-path').value = MASTER; await fvLoadFrame(); await new Promise(r => setTimeout(r, 10000)); try { fvToggleRings(); } catch (e) {}; try { _iceToggleFrameViewer(); } catch (e) {}; try { fvSetZoom(0.24); } catch (e) {}", wait: 3000, crop: "document.getElementById('fv-rings-btn').closest('.card') || document.getElementById('fv-img-wrap').parentElement", cropPad: 10, maxHeight: 940 }),
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
        let fr = await evalJs(`return window.__cpFrame(${JSON.stringify(st.crop)}, ${JSON.stringify(st.highlight.concat(st.extra || []))}, ${pad}, ${st.maxHeight || 0})`);
        await sleep(200);
        fr = await evalJs(`return window.__cpFrame(${JSON.stringify(st.crop)}, ${JSON.stringify(st.highlight.concat(st.extra || []))}, ${pad}, ${st.maxHeight || 0})`);   // settle after the scroll
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
