(function () {
  "use strict";

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var clamp = function (x, a, b) { return x < a ? a : x > b ? b : x; };
  var lerp = function (a, b, t) { return a + (b - a) * t; };
  var smooth = function (t) { t = clamp(t, 0, 1); return t * t * (3 - 2 * t); };
  var calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  var RAD = Math.PI / 180;

  /* ------------------------------------------------------------------
     The example data set: values from its XDS.INP, IDXREF.LP and XSCALE.LP
     ------------------------------------------------------------------ */
  var DS = {
    a: 98.56, b: 119.66, c: 161.55, lambda: 0.979338, dist: 197.44,
    nx: 4150, ny: 4371, qx: 0.075, orgx: 2008.9, orgy: 2253.1, frames: 1800, osc: 0.2,
    spots: 45214, indexed: 44631
  };
  // Upper shell limit d, I/sigma, R-obs, CC1/2, completeness.
  var SHELLS = [
    [7.09, 66.15, 2.6, 100.0, 94.8], [5.02, 59.03, 3.5, 100.0, 100], [4.10, 58.52, 3.4, 100.0, 100],
    [3.56, 50.04, 4.4, 99.9, 100], [3.18, 41.02, 5.8, 99.9, 100], [2.90, 29.67, 8.6, 99.8, 100],
    [2.69, 20.44, 13.2, 99.6, 100], [2.52, 14.46, 18.5, 99.2, 100], [2.37, 10.91, 25.2, 98.8, 100],
    [2.25, 8.47, 32.2, 98.0, 100], [2.15, 6.02, 47.6, 95.7, 100], [2.05, 4.28, 67.7, 91.3, 100],
    [1.95, 2.90, 98.4, 83.2, 100], [1.85, 1.71, 161.8, 61.3, 100], [1.75, 0.92, 270.7, 34.1, 100]
  ];
  // A shell's mean belongs at the middle of the shell in 1/d^2, as in the program's cut-off estimates.
  var MID = SHELLS.map(function (s, i) {
    var lo = i ? SHELLS[i - 1][0] : 19.95;
    return 1 / Math.sqrt((1 / (lo * lo) + 1 / (s[0] * s[0])) / 2);
  });

  function meanIsig(d) {
    if (d >= MID[0]) return SHELLS[0][1];
    for (var i = 1; i < MID.length; i++) {
      if (d >= MID[i]) return lerp(SHELLS[i][1], SHELLS[i - 1][1], (d - MID[i]) / (MID[i - 1] - MID[i]));
    }
    return SHELLS[SHELLS.length - 1][1] * clamp(d / MID[MID.length - 1], 0.5, 1);
  }

  // A fixed pseudo-random number for |h| |k| |l|, so reflections related by mmm agree.
  function hash3(h, k, l) {
    var x = (Math.abs(h) * 73856093) ^ (Math.abs(k) * 19349663) ^ (Math.abs(l) * 83492791);
    x = Math.imul(x ^ (x >>> 15), 0x2c1b3c6d);
    x = Math.imul(x ^ (x >>> 12), 0x297a2d39);
    x ^= x >>> 15;
    return (x >>> 0) / 4294967296;
  }

  /* ------------------------------------------------------------------
     Reciprocal lattice and rotation geometry
     ------------------------------------------------------------------ */
  var L = null;

  function orientation() {
    var a = 0.62, b = 0.41, c = 1.05;
    var ca = Math.cos(a), sa = Math.sin(a), cb = Math.cos(b), sb = Math.sin(b), cc = Math.cos(c), sc = Math.sin(c);
    return [
      ca * cc - sa * cb * sc, -ca * sc - sa * cb * cc, sa * sb,
      sa * cc + ca * cb * sc, -sa * sc + ca * cb * cc, -ca * sb,
      sb * sc, sb * cc, cb
    ];
  }

  // Each reflection crosses the Ewald sphere at up to two rotation angles. These are solved
  // once, so a frame only has to look at the crossings close to its own angle.
  function buildLattice(dmin) {
    var a = DS.a, b = DS.b, c = DS.c, lam = DS.lambda;
    var hm = Math.floor(a / dmin), km = Math.floor(b / dmin), lm = Math.floor(c / dmin);
    var s2max = 1 / (dmin * dmin), s2min = 1 / (19.95 * 19.95);
    var cap = Math.ceil((2 * hm + 1) * (2 * km + 1) * (2 * lm + 1) * 0.28) + 1000;
    var H = new Int16Array(cap), K = new Int16Array(cap), LL = new Int16Array(cap), B = new Float32Array(cap);

    var lut = new Float32Array(4001);
    for (var i = 0; i <= 4000; i++) lut[i] = i ? meanIsig(1 / Math.sqrt(i / 4000 * s2max)) : SHELLS[0][1];

    var n = 0, ia2 = 1 / (a * a), ib2 = 1 / (b * b), ic2 = 1 / (c * c), ls = 4000 / s2max;
    for (var h = -hm; h <= hm; h++) {
      var h2 = h * h * ia2;
      for (var k = -km; k <= km; k++) {
        if ((h + k) & 1) continue;                       // C-centring: h + k even
        var hk2 = h2 + k * k * ib2;
        if (hk2 > s2max) continue;
        for (var l = -lm; l <= lm; l++) {
          if (h === 0 && k === 0 && (l & 1)) continue;   // 2(1) along c: 00l with l even
          var s2 = hk2 + l * l * ic2;
          if (s2 > s2max || s2 < s2min) continue;
          var isig = -Math.log(1 - hash3(h, k, l)) * lut[(s2 * ls) | 0];
          if (isig < 1.6 || n >= cap) continue;
          H[n] = h; K[n] = k; LL[n] = l;
          B[n] = clamp(Math.log(1 + isig) / Math.LN10 / 1.9, 0, 1);
          n++;
        }
      }
    }

    var U = orientation(), kapFac = lam / 2, sz0 = 1 / lam;
    var phiT = new Float32Array(2 * n), xT = new Float32Array(2 * n), yT = new Float32Array(2 * n), idT = new Int32Array(2 * n);
    var bins = new Int32Array(362), m = 0;
    for (i = 0; i < n; i++) {
      var ga = H[i] / a, gb = K[i] / b, gc = LL[i] / c;
      var gx = U[0] * ga + U[1] * gb + U[2] * gc;
      var gy = U[3] * ga + U[4] * gb + U[5] * gc;
      var gz = U[6] * ga + U[7] * gb + U[8] * gc;
      var g2 = ga * ga + gb * gb + gc * gc;
      var rho = Math.sqrt(gy * gy + gz * gz), kap = kapFac * g2;
      if (rho < 1e-9 || kap >= rho) continue;            // blind region around the spindle
      var alpha = Math.atan2(gy, gz), w = Math.acos(-kap / rho), sz = sz0 - kap;
      for (var s = -1; s <= 1; s += 2) {
        var phi = alpha + s * w;
        var tx = gx / sz, ty = rho * Math.sin(alpha - phi) / sz;
        if (Math.abs(tx) > 1.4 || Math.abs(ty) > 1.4) continue;
        var deg = phi / RAD % 360; if (deg < 0) deg += 360;
        phiT[m] = deg; xT[m] = tx; yT[m] = ty; idT[m] = i;
        bins[(deg | 0) + 1]++;
        m++;
      }
    }
    for (i = 1; i < 362; i++) bins[i] += bins[i - 1];
    var fill = bins.slice();
    var P = new Float32Array(m), X = new Float32Array(m), Y = new Float32Array(m), ID = new Int32Array(m);
    for (i = 0; i < m; i++) {
      var q = fill[phiT[i] | 0]++;
      P[q] = phiT[i]; X[q] = xT[i]; Y[q] = yT[i]; ID[q] = idT[i];
    }
    return { H: H, K: K, L: LL, B: B, n: n, P: P, X: X, Y: Y, ID: ID, m: m, bins: bins };
  }

  function dOf(h, k, l) {
    return 1 / Math.sqrt(h * h / (DS.a * DS.a) + k * k / (DS.b * DS.b) + l * l / (DS.c * DS.c));
  }

  /* ------------------------------------------------------------------
     Main view
     ------------------------------------------------------------------ */
  var lab = $("#lab"), sim = $("#sim"), ctx = sim.getContext("2d");
  var hud = $("#hud"), tip = $("#tip"), viewLabel = $("#viewLabel"), simNote = $("#simNote");
  var W = 0, H = 0, DPR = 1, Dmm = DS.dist, showRings = true, paused = false;
  var box = { x: 0, y: 0, w: 0, h: 0, mm: 1, ox: 0, oy: 0 };
  var bgLayer = document.createElement("canvas"), topLayer = document.createElement("canvas"), accLayer = document.createElement("canvas");
  var scene = "frames", sceneStart = 0, labOn = false, phi = 40;
  var mouse = { x: -1, y: -1, on: false };
  var sprites = [], cloudSprites = [];

  function sprite(rgb, size) {
    var c = document.createElement("canvas"); c.width = c.height = size;
    var g = c.getContext("2d"), r = size / 2, grad = g.createRadialGradient(r, r, 0, r, r, r);
    grad.addColorStop(0, "rgba(" + rgb + ",1)");
    grad.addColorStop(0.35, "rgba(" + rgb + ",.8)");
    grad.addColorStop(1, "rgba(" + rgb + ",0)");
    g.fillStyle = grad; g.fillRect(0, 0, size, size);
    return c;
  }

  function makeSprites() {
    sprites = [sprite("86,150,255", 16), sprite("120,220,255", 16), sprite("238,250,255", 16)];
    cloudSprites = [
      sprite("95,216,255", 16), sprite("112,190,255", 16), sprite("134,162,255", 16),
      sprite("160,140,255", 16), sprite("186,130,250", 16),
      sprite("215,232,255", 16),   // not yet indexed
      sprite("255,150,90", 16)     // does not fit the lattice
    ];
  }

  function layoutDetector() {
    var wmm = DS.nx * DS.qx, hmm = DS.ny * DS.qx;
    var scale = Math.min(W / wmm, H / hmm);
    box.mm = scale; box.w = wmm * scale; box.h = hmm * scale;
    box.x = (W - box.w) / 2; box.y = (H - box.h) / 2;
    box.ox = box.x + DS.orgx * DS.qx * scale;
    box.oy = box.y + DS.orgy * DS.qx * scale;
  }

  function ringRadius(d, D) {
    var th = Math.asin(clamp(DS.lambda / (2 * d), -1, 1));
    return D * Math.tan(2 * th) * box.mm;
  }

  // Background scatter that depends on the distance, then the module gaps and beamstop that sit in front of the spots.
  function paintLayers() {
    if (!W) return;
    bgLayer.width = topLayer.width = W; bgLayer.height = topLayer.height = H;
    var g = bgLayer.getContext("2d");
    g.fillStyle = "#040816"; g.fillRect(0, 0, W, H);
    g.save(); g.beginPath(); g.rect(box.x, box.y, box.w, box.h); g.clip();
    g.fillStyle = "#070e22"; g.fillRect(box.x, box.y, box.w, box.h);
    var r0 = ringRadius(14, Dmm), r1 = ringRadius(3.25, Dmm), r2 = ringRadius(2.15, Dmm);
    var rMax = Math.max(r2 * 1.7, 10);
    var rg = g.createRadialGradient(box.ox, box.oy, 0, box.ox, box.oy, rMax);
    var f = function (r) { return clamp(r / rMax, 0, 1); };
    rg.addColorStop(0, "rgba(90,130,255,.30)");
    rg.addColorStop(f(r0), "rgba(70,110,230,.16)");
    rg.addColorStop(clamp(f(r1) * 0.72, f(r0) + .001, 1), "rgba(50,90,200,.05)");
    rg.addColorStop(f(r1), "rgba(95,135,255,.20)");
    rg.addColorStop(clamp(f(r1) * 1.28, f(r1) + .001, .99), "rgba(50,90,200,.05)");
    rg.addColorStop(1, "rgba(40,70,160,0)");
    g.fillStyle = rg; g.fillRect(box.x, box.y, box.w, box.h);
    var dots = Math.round(box.w * box.h / 90);
    g.fillStyle = "rgba(140,170,255,.13)";
    for (var i = 0; i < dots; i++) {
      g.fillRect(box.x + hash3(i, 7, 1) * box.w, box.y + hash3(i, 3, 2) * box.h, DPR, DPR);
    }
    g.restore();

    var t = topLayer.getContext("2d");
    t.clearRect(0, 0, W, H);
    t.fillStyle = "#040816";
    var modW = box.w / 4, modH = box.h / 8, gw = Math.max(1, 10 * DS.qx * box.mm), gh = Math.max(1, 37 * DS.qx * box.mm);
    for (i = 1; i < 4; i++) t.fillRect(box.x + i * modW - gw / 2, box.y, gw, box.h);
    for (i = 1; i < 8; i++) t.fillRect(box.x, box.y + i * modH - gh / 2, box.w, gh);
    var bw = Math.max(3 * DPR, 3.2 * box.mm);
    t.beginPath();
    t.moveTo(box.x, box.oy - bw * 2.2); t.lineTo(box.ox - bw, box.oy - bw * 0.9);
    t.arc(box.ox, box.oy, bw * 1.15, Math.PI * 1.25, Math.PI * .75);
    t.lineTo(box.ox - bw, box.oy + bw * 0.9); t.lineTo(box.x, box.oy + bw * 2.2); t.closePath();
    t.fillStyle = "rgba(3,5,14,.96)"; t.fill();
    t.strokeStyle = "rgba(120,180,255,.3)"; t.lineWidth = Math.max(1, DPR * .8);
    t.strokeRect(box.x + .5, box.y + .5, box.w - 1, box.h - 1);
  }

  var RINGS = [8, 4, 3, 2.5, 2, 1.75];
  function drawRings() {
    ctx.save();
    ctx.beginPath(); ctx.rect(box.x, box.y, box.w, box.h); ctx.clip();
    ctx.lineWidth = Math.max(1, DPR * .8);
    ctx.font = "500 " + Math.round(10.5 * DPR) + "px Consolas, ui-monospace, monospace";
    ctx.textAlign = "center";
    for (var i = 0; i < RINGS.length; i++) {
      var r = ringRadius(RINGS[i], Dmm);
      if (r < 16 * DPR) continue;
      ctx.strokeStyle = "rgba(255,190,125,.34)";
      ctx.setLineDash([3 * DPR, 5 * DPR]);
      ctx.beginPath(); ctx.arc(box.ox, box.oy, r, 0, Math.PI * 2); ctx.stroke();
      ctx.setLineDash([]);
      var ly = box.oy - r;
      if (ly > box.y + 11 * DPR) {
        ctx.fillStyle = "rgba(255,205,155,.92)";
        ctx.fillText(RINGS[i] + " Å", box.ox, ly - 3 * DPR);
      }
    }
    ctx.restore();
  }

  var near = null;
  function drawFrame(angle, opts) {
    opts = opts || {};
    var sigma = opts.sigma || 0.32, reach = sigma * 3;
    var Dpx = Dmm * box.mm;
    ctx.globalCompositeOperation = "source-over"; ctx.globalAlpha = 1;
    ctx.drawImage(bgLayer, 0, 0);
    if (opts.acc) ctx.drawImage(accLayer, 0, 0);
    ctx.globalCompositeOperation = "lighter";
    var lo = Math.floor(angle - reach), hi = Math.floor(angle + reach);
    var x0 = box.x, x1 = box.x + box.w, y0 = box.y, y1 = box.y + box.h, ox = box.ox, oy = box.oy;
    var P = L.P, X = L.X, Y = L.Y, ID = L.ID, BR = L.B, bins = L.bins;
    var sk = clamp(W / 900, 0.62, 1) * DPR, s0 = 2.7 * sk, s1 = 3.5 * sk, s2 = 5 * sk, gain = opts.gain || 1;
    var mx = mouse.x, my = mouse.y, best = (13 * DPR) * (13 * DPR), hit = -1, hx = 0, hy = 0;
    var track = mouse.on && !opts.noHover;
    for (var b = lo; b <= hi; b++) {
      var bn = ((b % 360) + 360) % 360, end = bins[bn + 1];
      for (var e = bins[bn]; e < end; e++) {
        var dp = P[e] - angle;
        if (dp > 180) dp -= 360; else if (dp < -180) dp += 360;
        if (dp > reach || dp < -reach) continue;
        var px = ox + X[e] * Dpx, py = oy - Y[e] * Dpx;
        if (px < x0 || px > x1 || py < y0 || py > y1) continue;
        var u = dp / sigma, br = BR[ID[e]] * Math.exp(-0.5 * u * u) * gain;
        if (br < 0.035) continue;
        var lv = br > 0.5 ? 2 : br > 0.24 ? 1 : 0, sz = lv === 2 ? s2 : lv === 1 ? s1 : s0;
        ctx.globalAlpha = br > 0.62 ? 1 : br * 1.6;
        ctx.drawImage(sprites[lv], px - sz / 2, py - sz / 2, sz, sz);
        if (track) {
          var ddx = px - mx, ddy = py - my, dd = ddx * ddx + ddy * ddy;
          if (dd < best && br > 0.08) { best = dd; hit = e; hx = px; hy = py; }
        }
      }
    }
    ctx.globalCompositeOperation = "source-over"; ctx.globalAlpha = 1;
    ctx.drawImage(topLayer, 0, 0);
    if (showRings && !opts.noRings) drawRings();
    near = hit >= 0 ? { e: hit, x: hx, y: hy } : null;
    if (near) {
      ctx.strokeStyle = "#8fd0ff"; ctx.lineWidth = 1.5 * DPR;
      ctx.beginPath(); ctx.arc(hx, hy, 7 * DPR, 0, Math.PI * 2); ctx.stroke();
    }
    showTip();
  }

  function showTip() {
    if (!near) { tip.style.display = "none"; return; }
    var i = L.ID[near.e], h = L.H[i], k = L.K[i], l = L.L[i];
    tip.innerHTML = "<b>" + h + " " + k + " " + l + "</b>&nbsp; d = " + dOf(h, k, l).toFixed(2) + " Å";
    tip.style.display = "block";
    var tx = near.x / DPR + 14, ty = near.y / DPR - 34;
    var vw = W / DPR;
    if (tx + tip.offsetWidth > vw - 6) tx = near.x / DPR - tip.offsetWidth - 14;
    tip.style.left = tx + "px";
    tip.style.top = Math.max(4, ty) + "px";
  }

  /* ---------- 1: frames ---------- */
  function sceneFrames(now, dt) {
    if (!paused && !calm) phi = (phi + dt * (mouse.on ? 0.5 : 2.4)) % 360;
    drawFrame(phi);
    var frame = Math.floor(phi / DS.osc) % DS.frames + 1;
    hud.innerHTML = "Frame <b>" + frame + "</b> / " + DS.frames + " &nbsp;φ <b>" + phi.toFixed(1) + "°</b><br>EIGER 16M &nbsp;λ " + DS.lambda.toFixed(3) + " Å &nbsp;edge " + edgeRes().toFixed(2) + " Å";
  }

  function edgeRes() {
    var rmm = Math.min(DS.orgx, DS.nx - DS.orgx, DS.orgy, DS.ny - DS.orgy) * DS.qx;
    return DS.lambda / (2 * Math.sin(Math.atan(rmm / Dmm) / 2));
  }

  /* ---------- 2: COLSPOT ---------- */
  var sweep = { phi: 0, done: false, found: 0, cutoff: 0.4, total: 0 };
  var RANGES = [[0, 90], [270, 360]];
  var SWEEP_RATE = 26; // degrees per second

  function spotCutoff() {
    var hist = new Int32Array(101), m = L.m;
    for (var e = 0; e < m; e++) {
      var p = L.P[e];
      if ((p < 90 || p >= 270) && inDetector(e)) hist[(L.B[L.ID[e]] * 100) | 0]++;
    }
    var want = DS.spots, sum = 0;
    for (var b = 100; b >= 0; b--) { sum += hist[b]; if (sum >= want) break; }
    sweep.cutoff = b / 100; sweep.total = sum;
  }

  function inDetector(e) {
    var D = DS.dist;
    var x = DS.orgx * DS.qx + L.X[e] * D, y = DS.orgy * DS.qx - L.Y[e] * D;
    return x >= 0 && x <= DS.nx * DS.qx && y >= 0 && y <= DS.ny * DS.qx;
  }

  function startSweep() {
    Dmm = DS.dist; syncDistance();
    sweep.phi = 0; sweep.done = false; sweep.found = 0;
    accLayer.width = W; accLayer.height = H;
    if (calm) finishSweep();
  }

  function collect(from, to, g) {
    var Dpx = Dmm * box.mm, sz = 1.5 * DPR, found = 0;
    for (var b = Math.floor(from); b < Math.ceil(to); b++) {
      var bn = ((b % 360) + 360) % 360;
      for (var e = L.bins[bn]; e < L.bins[bn + 1]; e++) {
        var p = L.P[e];
        if (p < from || p >= to) continue;
        if (L.B[L.ID[e]] < sweep.cutoff) continue;
        var px = box.ox + L.X[e] * Dpx, py = box.oy - L.Y[e] * Dpx;
        if (px < box.x || px > box.x + box.w || py < box.y || py > box.y + box.h) continue;
        g.fillRect(px - sz / 2, py - sz / 2, sz, sz);
        found++;
      }
    }
    return found;
  }

  function finishSweep() {
    var g = accLayer.getContext("2d");
    g.fillStyle = "rgba(104,235,160,.5)";
    collect(0, 90, g); collect(270, 360, g);
    sweep.done = true; sweep.found = sweep.total;
    sweep.phi = 360;
  }

  function sceneColspot(now, dt) {
    if (!sweep.done) {
      var g = accLayer.getContext("2d");
      g.fillStyle = "rgba(104,235,160,.5)";
      var from = sweep.phi, to = from + dt * SWEEP_RATE;
      if (from < 90 && to >= 90) { sweep.found += collect(from, 90, g); to = 270 + (to - 90); from = 270; }
      if (to >= 360) { to = 360; sweep.done = true; }
      sweep.found += collect(from, to, g);
      sweep.phi = to;
      drawFrame(to % 360, { acc: true, sigma: 0.5, noRings: true, noHover: true });
      var angle = to % 360, frame = Math.min(DS.frames, Math.floor(to / DS.osc) + 1);
      hud.innerHTML = "COLSPOT &nbsp;frame <b>" + frame + "</b> / " + DS.frames + " &nbsp;φ <b>" + angle.toFixed(1) + "°</b>";
    } else {
      ctx.globalCompositeOperation = "source-over"; ctx.globalAlpha = 1;
      ctx.drawImage(bgLayer, 0, 0);
      ctx.drawImage(accLayer, 0, 0);
      ctx.drawImage(topLayer, 0, 0);
      hud.innerHTML = "COLSPOT &nbsp;<b>finished</b>";
    }
    var shown = sweep.done ? DS.spots : Math.round(sweep.found / Math.max(1, sweep.total) * DS.spots);
    $("#spotCount").textContent = Math.min(shown, DS.spots).toLocaleString("en-US");
  }

  /* ---------- 3: IDXREF ---------- */
  var cloud = null;
  var cam = { yaw: 0.8, pitch: 0.5 }, camTarget = { yaw: 0.8, pitch: 0.5 }, manualUntil = 0, drag = null;
  var VIEWS = {
    c: { yaw: 0, pitch: 0, label: "Down c*: a* across, b* up. h + k is always even, the C-centring." },
    a: { yaw: -Math.PI / 2, pitch: 0, label: "Down a*: rows of b* and c*." },
    b: { yaw: 0, pitch: Math.PI / 2, label: "Down b*: rows of a* and c*." }
  };
  var PATH = [
    { yaw: 0.8, pitch: 0.5, hold: 2.6 }, { view: "c", hold: 4.2 },
    { yaw: -0.7, pitch: 0.35, hold: 1.9 }, { view: "a", hold: 3.6 },
    { yaw: 0.5, pitch: 0.95, hold: 1.9 }, { view: "b", hold: 3.6 }
  ];
  var pathI = 0, pathLeft = 0;

  function buildCloud() {
    var maxPts = W / DPR < 560 ? 5000 : 11000, dCut = 6.5;
    var seen = 0, e, i;
    for (e = 0; e < L.m; e++) {
      var p = L.P[e];
      if (p >= 90 && p < 270) continue;
      i = L.ID[e];
      if (dOf(L.H[i], L.K[i], L.L[i]) >= dCut) seen++;
    }
    var stride = Math.max(1, Math.ceil(seen / maxPts)), n = Math.ceil(seen / stride) + 1;
    var c = { n: 0, X: new Float32Array(n), Y: new Float32Array(n), Z: new Float32Array(n), SX: new Float32Array(n), SY: new Float32Array(n), HUE: new Uint8Array(n), LATE: new Float32Array(n), S: new Float32Array(n), scale: dCut };
    var count = 0;
    for (e = 0; e < L.m; e++) {
      p = L.P[e];
      if (p >= 90 && p < 270) continue;
      i = L.ID[e];
      var hh = L.H[i], kk = L.K[i], ll = L.L[i];
      if (dOf(hh, kk, ll) < dCut) continue;
      if (count++ % stride) continue;
      var q = c.n++;
      var r1 = hash3(hh + 11, kk, ll), bad = r1 < 1 - DS.indexed / DS.spots;
      c.X[q] = hh / DS.a * dCut + (bad ? (hash3(hh, kk + 5, ll) - .5) * .05 : 0);
      c.Y[q] = kk / DS.b * dCut + (bad ? (hash3(hh, kk, ll + 9) - .5) * .05 : 0);
      c.Z[q] = ll / DS.c * dCut + (bad ? (hash3(hh + 3, kk, ll) - .5) * .05 : 0);
      c.SX[q] = L.X[e]; c.SY[q] = L.Y[e];
      c.HUE[q] = bad ? 6 : Math.min(4, Math.floor(Math.abs(ll / DS.c * dCut) * 5));
      c.LATE[q] = hash3(hh, kk + 17, ll);
      c.S[q] = lerp(2.6, 4.6, L.B[i]);
    }
    cloud = c;
  }

  function followPath(now, dt) {
    if (now < manualUntil) return;
    pathLeft -= dt;
    if (pathLeft <= 0) {
      var step = PATH[pathI % PATH.length]; pathI++;
      pathLeft = step.hold;
      if (step.view) setView(step.view, false);
      else { camTarget.yaw = step.yaw; camTarget.pitch = step.pitch; viewLabel.classList.remove("on"); pressView(null); }
    }
  }

  function setView(name, byHand) {
    var v = VIEWS[name];
    camTarget.yaw = v.yaw; camTarget.pitch = v.pitch;
    viewLabel.textContent = v.label; viewLabel.classList.add("on");
    pressView(name);
    if (byHand) manualUntil = performance.now() / 1000 + 9;
  }

  function pressView(name) {
    $$("[data-view]").forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-view") === name ? "true" : "false"); });
  }

  function project(x, y, z, cy, sy, cp, sp) {
    var x1 = x * cy + z * sy, z1 = -x * sy + z * cy;
    var y2 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
    return [x1, y2, z2];
  }

  function arrow(ax, ay, az, S, cx, cy0, cyw, syw, cp, sp, text, color) {
    var p = project(ax, ay, az, cyw, syw, cp, sp);
    var ex = cx + p[0] * S, ey = cy0 - p[1] * S, len = Math.sqrt(p[0] * p[0] + p[1] * p[1]);
    if (len < 0.08) return;
    ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = 2 * DPR;
    ctx.beginPath(); ctx.moveTo(cx, cy0); ctx.lineTo(ex, ey); ctx.stroke();
    var ang = Math.atan2(ey - cy0, ex - cx), hd = 8 * DPR;
    ctx.beginPath(); ctx.moveTo(ex, ey);
    ctx.lineTo(ex - hd * Math.cos(ang - .4), ey - hd * Math.sin(ang - .4));
    ctx.lineTo(ex - hd * Math.cos(ang + .4), ey - hd * Math.sin(ang + .4));
    ctx.closePath(); ctx.fill();
    ctx.font = "700 " + Math.round(14 * DPR) + "px Consolas, ui-monospace, monospace";
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(text, ex + Math.cos(ang) * 15 * DPR, ey + Math.sin(ang) * 15 * DPR);
    ctx.textBaseline = "alphabetic";
  }

  function sceneIdxref(now, dt, st) {
    if (!cloud) buildCloud();
    followPath(now, dt);
    var k = 1 - Math.exp(-dt * 2.6);
    cam.yaw += (camTarget.yaw - cam.yaw) * k;
    cam.pitch += (camTarget.pitch - cam.pitch) * k;
    if (!drag && now >= manualUntil && pathLeft > 0 && !viewLabel.classList.contains("on") && !calm) {
      camTarget.yaw += dt * 0.09;
    }

    var morphT = calm ? 1 : clamp(st / 1.7, 0, 1), m = smooth(morphT);
    ctx.globalCompositeOperation = "source-over"; ctx.globalAlpha = 1;
    ctx.fillStyle = "#040816"; ctx.fillRect(0, 0, W, H);
    if (m < 1) {
      ctx.globalAlpha = 1 - m;
      ctx.drawImage(bgLayer, 0, 0);
      ctx.drawImage(topLayer, 0, 0);
      ctx.globalAlpha = 1;
    }
    var cx = W / 2, cy0 = H / 2, S = Math.min(W, H) * 0.455;
    var cyw = Math.cos(cam.yaw), syw = Math.sin(cam.yaw), cp = Math.cos(cam.pitch), sp = Math.sin(cam.pitch);
    var Dpx = DS.dist * box.mm;
    var indexT = calm ? 1 : clamp((st - 1.7) / 1.5, 0, 1);
    ctx.globalCompositeOperation = "lighter";
    var c = cloud, n = c.n;
    for (var i = 0; i < n; i++) {
      var x = c.X[i], y = c.Y[i], z = c.Z[i];
      var x1 = x * cyw + z * syw, z1 = -x * syw + z * cyw;
      var y2 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
      var tx = cx + x1 * S, ty = cy0 - y2 * S;
      var mi = smooth(morphT * 1.35 - c.LATE[i] * 0.35);
      var fx = box.ox + c.SX[i] * Dpx, fy = box.oy - c.SY[i] * Dpx;
      var px = lerp(fx, tx, mi), py = lerp(fy, ty, mi);
      var isIndexed = indexT > c.LATE[i];
      var spr = cloudSprites[isIndexed ? c.HUE[i] : 5];
      var s = c.S[i] * DPR;
      ctx.globalAlpha = clamp(0.5 + z2 * 0.42, 0.22, 1);
      ctx.drawImage(spr, px - s / 2, py - s / 2, s, s);
    }
    ctx.globalCompositeOperation = "source-over"; ctx.globalAlpha = clamp((st - 2.6) / 0.8, 0, 1);
    if (calm) ctx.globalAlpha = 1;
    if (ctx.globalAlpha > 0) {
      arrow(.72, 0, 0, S, cx, cy0, cyw, syw, cp, sp, "a*", "#ffd28a");
      arrow(0, .72, 0, S, cx, cy0, cyw, syw, cp, sp, "b*", "#8ff0c0");
      arrow(0, 0, .72, S, cx, cy0, cyw, syw, cp, sp, "c*", "#d6b8ff");
    }
    ctx.globalAlpha = 1;
    var pct = (DS.indexed / DS.spots * 100) * indexT, cnt = Math.round(DS.indexed * indexT);
    $("#idxPct").textContent = pct.toFixed(1) + "%";
    $("#idxCount").textContent = cnt + " / " + DS.spots + " spots";
    hud.innerHTML = "Reciprocal space &nbsp;<b>" + n.toLocaleString("en-US") + "</b> spots shown";
  }

  /* ---------- 4: CORRECT ---------- */
  var plane = null;
  function buildPlane() {
    var dCut = 6.5, pts = [], kmax = Math.floor(DS.b / dCut), lmax = Math.floor(DS.c / dCut);
    for (var k = -kmax; k <= kmax; k += 2) {
      for (var l = -lmax; l <= lmax; l++) {
        if (k === 0 && l === 0) continue;
        if (dOf(0, k, l) < dCut) continue;
        var isig = -Math.log(1 - hash3(0, k, l) * 0.98) * meanIsig(dOf(0, k, l));
        pts.push({ k: k, l: l, axis: k === 0, abs: k === 0 && (l & 1) === 1, b: clamp(Math.log(1 + isig) / Math.LN10 / 1.9, .28, 1) });
      }
    }
    plane = pts;
  }

  function sceneCorrect(now, dt, st) {
    if (!plane) buildPlane();
    var t = calm ? 1 : smooth(st / 1.1), pulse = calm ? 1 : .55 + .45 * Math.sin(now * 2.4);
    ctx.globalCompositeOperation = "source-over"; ctx.globalAlpha = 1;
    ctx.fillStyle = "#040816"; ctx.fillRect(0, 0, W, H);
    var cx = W * 0.40, cy0 = H * 0.5, scale = H * 3.7 * lerp(.55, 1, t);
    var bk = 1 / DS.b * scale, cl = 1 / DS.c * scale;
    var dotS = clamp(cl * 0.66, 3 * DPR, 11 * DPR);

    // Column guide along the 00l axis
    ctx.strokeStyle = "rgba(143,208,255," + (.34 * t) + ")"; ctx.lineWidth = 1.5 * DPR;
    ctx.setLineDash([2 * DPR, 5 * DPR]);
    ctx.beginPath(); ctx.moveTo(cx, 0); ctx.lineTo(cx, H); ctx.stroke(); ctx.setLineDash([]);

    ctx.globalCompositeOperation = "lighter";
    for (var i = 0; i < plane.length; i++) {
      var p = plane[i];
      if (p.abs) continue;
      var px = cx + p.k * bk, py = cy0 - p.l * cl;
      if (px < -20 || px > W + 20 || py < -20 || py > H + 20) continue;
      var s = dotS * (p.axis ? 1.65 : lerp(.55, 1, p.b));
      ctx.globalAlpha = p.axis ? 1 : p.b * .52 * t;
      ctx.drawImage(cloudSprites[p.axis ? 0 : Math.min(4, Math.floor(Math.abs(p.l) / 6))], px - s / 2, py - s / 2, s, s);
    }
    ctx.globalCompositeOperation = "source-over"; ctx.globalAlpha = 1;

    // The systematically absent positions are drawn as open circles.
    ctx.lineWidth = 1.4 * DPR;
    ctx.font = "500 " + Math.round(10.5 * DPR) + "px Consolas, ui-monospace, monospace";
    ctx.textBaseline = "middle"; ctx.textAlign = "right";
    for (i = 0; i < plane.length; i++) {
      p = plane[i];
      if (!p.axis) continue;
      py = cy0 - p.l * cl;
      if (py < -10 || py > H + 10) continue;
      if (p.abs) {
        ctx.strokeStyle = "rgba(255,150,110," + (.35 + .55 * pulse * t) + ")";
        ctx.beginPath(); ctx.arc(cx, py, dotS * .46, 0, Math.PI * 2); ctx.stroke();
      }
      if (p.l > 0 && cl > 10 * DPR) {
        ctx.fillStyle = (p.l & 1) ? "rgba(255,170,130," + (.85 * t) + ")" : "rgba(190,226,255," + t + ")";
        ctx.fillText(String(p.l), cx - dotS * .7 - 3 * DPR, py);
      }
    }
    ctx.textBaseline = "alphabetic"; ctx.textAlign = "center";
    ctx.font = "700 " + Math.round(13 * DPR) + "px Consolas, ui-monospace, monospace";
    ctx.fillStyle = "#d6b8ff"; ctx.fillText("00l", cx + 21 * DPR, 22 * DPR);
    ctx.fillStyle = "#8ff0c0"; ctx.fillText("0k0", W - 26 * DPR, cy0 - 12 * DPR);
    hud.innerHTML = "<b>0kl</b> plane &nbsp;h = 0";
  }

  /* ---------- loop ---------- */
  var lastT = 0;
  function loop(ts) {
    requestAnimationFrame(loop);
    var now = ts / 1000, dt = Math.min(0.05, now - lastT); lastT = now;
    if (!labOn || !L || !W) return;
    var st = now - sceneStart;
    if (scene === "frames") sceneFrames(now, dt);
    else if (scene === "colspot") sceneColspot(now, dt);
    else if (scene === "idxref") sceneIdxref(now, dt, st);
    else if (scene === "correct") sceneCorrect(now, dt, st);
  }

  function setScene(name) {
    if (name === scene) return;
    var was = scene;
    scene = name;
    lab.setAttribute("data-stage", name);
    sceneStart = performance.now() / 1000;
    tip.style.display = "none"; near = null;
    viewLabel.classList.remove("on");
    updatePipe(name);
    if (!L) return;
    if (name === "colspot" && was !== "colspot") startSweep();
    if (name === "idxref") { pathI = 0; pathLeft = 0; manualUntil = 0; }
    if (name === "xscale") drawInset();
    if (name === "table1") revealTable();
    simNote.textContent = name === "correct" ? "Lattice from the real cell, the summary numbers from CORRECT.LP" : "Simulated from the real cell and detector geometry";
  }

  var PIPE_NOW = { frames: [0, 1], colspot: [2, 2], idxref: [3, 3], correct: [4, 7], xscale: [8, 8], table1: [9, 9] };
  var pipeItems = $$("#pipe li");
  function updatePipe(name) {
    var r = PIPE_NOW[name];
    pipeItems.forEach(function (li, i) {
      li.classList.toggle("done", i < r[0]);
      li.classList.toggle("now", i >= r[0] && i <= r[1]);
    });
  }

  function resize() {
    var rect = $("#view").getBoundingClientRect();
    if (rect.width < 10 || rect.height < 10) return;
    DPR = Math.min(window.devicePixelRatio || 1, 1.6);
    W = sim.width = Math.round(rect.width * DPR);
    H = sim.height = Math.round(rect.height * DPR);
    layoutDetector();
    paintLayers();
    accLayer.width = W; accLayer.height = H;
    if (scene === "colspot" && L) { finishSweep(); }
    if (cloud && (W / DPR < 560) !== (cloud.n < 6000)) cloud = null;
    fitChart();
  }

  function syncDistance() {
    var input = $("#dist");
    input.value = Math.round(Dmm);
    $("#distVal").textContent = Dmm === DS.dist ? "197.44" : Dmm.toFixed(2);
    paintLayers();
  }

  function initLab() {
    makeSprites();
    updatePipe("frames");
    resize();
    var build = function () {
      L = buildLattice(W / DPR < 560 ? 2.2 : 1.75);
      spotCutoff();
      if (scene === "colspot") startSweep();
      if (scene === "xscale") drawInset();
    };
    if (window.requestIdleCallback) requestIdleCallback(build, { timeout: 700 }); else setTimeout(build, 60);

    new IntersectionObserver(function (es) { labOn = es[0].isIntersecting; }, { rootMargin: "120px" }).observe(lab);
    if (window.ResizeObserver) new ResizeObserver(resize).observe($("#view"));
    else addEventListener("resize", resize);

    // The step nearest the reading line decides the scene.
    var steps = $$(".step");
    var pick = function () {
      var narrow = matchMedia("(max-width: 1000px)").matches;
      var line = innerHeight * (narrow ? 0.78 : 0.5), best = null, dist = 1e9;
      steps.forEach(function (st) {
        var r = st.getBoundingClientRect();
        var d = line < r.top ? r.top - line : line > r.bottom ? line - r.bottom : 0;
        if (d < dist) { dist = d; best = st; }
      });
      if (!best) return;
      steps.forEach(function (st) { st.classList.toggle("active", st === best); });
      setScene(best.getAttribute("data-stage"));
    };
    addEventListener("scroll", pick, { passive: true });
    addEventListener("resize", pick);
    pick();

    sim.addEventListener("pointermove", function (ev) {
      var r = sim.getBoundingClientRect();
      mouse.x = (ev.clientX - r.left) * DPR; mouse.y = (ev.clientY - r.top) * DPR;
      if (ev.pointerType === "mouse") mouse.on = true;
      if (drag) {
        camTarget.yaw = drag.yaw + (ev.clientX - drag.x) * 0.009;
        camTarget.pitch = clamp(drag.pitch + (ev.clientY - drag.y) * 0.009, -1.6, 1.6);
        cam.yaw = camTarget.yaw; cam.pitch = camTarget.pitch;
        manualUntil = performance.now() / 1000 + 9;
        viewLabel.classList.remove("on"); pressView(null);
      }
    });
    sim.addEventListener("pointerleave", function () { mouse.on = false; });
    sim.addEventListener("pointerdown", function (ev) {
      if (scene !== "idxref") return;
      drag = { x: ev.clientX, y: ev.clientY, yaw: cam.yaw, pitch: cam.pitch };
      if (sim.setPointerCapture) sim.setPointerCapture(ev.pointerId);
    });
    addEventListener("pointerup", function () { drag = null; });
    addEventListener("pointercancel", function () { drag = null; });

    $("#dist").addEventListener("input", function () { Dmm = +this.value; syncDistance(); });
    $("#ringsBtn").addEventListener("click", function () { showRings = !showRings; this.setAttribute("aria-pressed", showRings); });
    $("#pauseBtn").addEventListener("click", function () { paused = !paused; this.setAttribute("aria-pressed", paused); this.textContent = paused ? "Play" : "Pause"; });
    $("#rerunBtn").addEventListener("click", startSweep);
    $$("[data-view]").forEach(function (b) { b.addEventListener("click", function () { setView(b.getAttribute("data-view"), true); }); });

    fitChart();
    if (!critBuilt) buildChart();
    buildTable();
    requestAnimationFrame(loop);
  }

  /* ------------------------------------------------------------------
     XSCALE: the real shells and the cut-off criteria
     ------------------------------------------------------------------ */
  var CRIT = [
    { id: "iosig", label: "I/σ ≈ 2.0", d: 1.92, color: "var(--iosig)", thr: 2, axis: "L", why: "I/σ ≈ 2.0, interpolated. The traditional conservative criterion." },
    { id: "robs", label: "R-obs ≈ 55%", d: 2.16, color: "var(--robs)", thr: 55, axis: "R", why: "R-obs ≈ 55%, interpolated. The traditional conservative criterion." },
    { id: "cc", label: "CC½ ≈ 50%", d: 1.85, color: "var(--cc)", thr: 50, axis: "R", why: "CC½ ≈ 50%, interpolated. The commonly used intermediate criterion." },
    { id: "sig", label: "CC½ signif.", d: 1.75, color: "var(--sig)", thr: null, why: "CC½ significance: not reached. All shells are significant at the 0.1% level, and the outer shell has CC½ = 34.1%." }
  ];
  var chartW = 720, chartH = 330, cm = { l: 44, r: 46, t: 24, b: 34 }, cutD = 1.85, cutShown = 1.85, insetRaf = 0, critNow = 2, critBuilt = false;
  var xMin = 1 / (15 * 15), xMax = 1 / (1.75 * 1.75);
  function cx_(d) { return cm.l + (1 / (d * d) - xMin) / (xMax - xMin) * (chartW - cm.l - cm.r); }
  function yL(v) { return chartH - cm.b - Math.log(v / 0.5) / Math.log(100 / 0.5) * (chartH - cm.t - cm.b); }
  function yR(v) { return chartH - cm.b - v / 100 * (chartH - cm.t - cm.b); }

  function pathOf(col, y) {
    return SHELLS.map(function (s, i) { return (i ? "L" : "M") + cx_(MID[i]).toFixed(1) + " " + y(s[col]).toFixed(1); }).join(" ");
  }

  // The drawing takes the proportions of the space it has, so it fills the panel on any screen.
  function fitChart() {
    var r = $("#chart").getBoundingClientRect();
    if (r.width < 50 || r.height < 50) return;
    var want = Math.round(clamp(chartW * r.height / r.width, 250, 560));
    if (Math.abs(want - chartH) < 8 && critBuilt) return;
    chartH = want;
    $("#chart").setAttribute("viewBox", "0 0 " + chartW + " " + chartH);
    buildChart();
  }

  function serLabel(i, axis, col, dy, text, color) {
    var s = SHELLS[i], y = (axis === "L" ? yL(s[col]) : yR(s[col])) + dy;
    return '<text x="' + cx_(MID[i]) + '" y="' + y + '" text-anchor="middle" style="fill:' + color + ';font-weight:600">' + text + "</text>";
  }

  function buildChart() {
    var svg = $("#chart"), o = [], px = cm.l, pw = chartW - cm.l - cm.r, py = cm.t, ph = chartH - cm.t - cm.b, base = chartH - cm.b;
    o.push('<defs><clipPath id="plot"><rect x="' + px + '" y="' + py + '" width="' + pw + '" height="' + ph + '"/></clipPath></defs>');
    [1, 2, 5, 10, 20, 50, 100].forEach(function (v) {
      o.push('<line class="gl" x1="' + px + '" x2="' + (px + pw) + '" y1="' + yL(v) + '" y2="' + yL(v) + '"/><text class="axis" x="' + (px - 6) + '" y="' + (yL(v) + 4) + '" text-anchor="end">' + v + '</text>');
    });
    [0, 25, 50, 75, 100].forEach(function (v) {
      o.push('<text class="axis" x="' + (px + pw + 6) + '" y="' + (yR(v) + 4) + '">' + v + '%</text>');
    });
    [6, 3.5, 3, 2.5, 2.2, 2, 1.85, 1.75].forEach(function (d) {
      o.push('<line class="gl" x1="' + cx_(d) + '" x2="' + cx_(d) + '" y1="' + py + '" y2="' + base + '"/><text class="axis" x="' + cx_(d) + '" y="' + (base + 15) + '" text-anchor="middle">' + d + '</text>');
    });
    o.push('<text class="axis" x="' + (px + pw / 2) + '" y="' + (chartH - 3) + '" text-anchor="middle">Resolution (Å)</text>');
    o.push('<text class="axis" x="' + (px - 6) + '" y="' + (py - 10) + '" text-anchor="end" style="fill:var(--iosig)">I/σ</text>');
    o.push('<g clip-path="url(#plot)">');
    o.push('<path class="ser" data-s="compl" d="' + pathOf(4, yR) + '" stroke="var(--green)" stroke-dasharray="4 4"/>');
    o.push('<path class="ser" data-s="robs" d="' + pathOf(2, yR) + '" stroke="var(--robs)"/>');
    o.push('<path class="ser" data-s="cc" d="' + pathOf(3, yR) + '" stroke="var(--cc)"/>');
    o.push('<path class="ser" data-s="iosig" d="' + pathOf(1, yL) + '" stroke="var(--iosig)"/>');
    o.push('<g id="thrG" class="moves"><line id="thrLine" x1="' + px + '" x2="' + (px + pw) + '" y1="0" y2="0" stroke-width="1.4" stroke-dasharray="3 4"/></g>');
    o.push('<g id="beyond" class="moves"><rect x="0" y="' + py + '" width="' + (pw + 40) + '" height="' + ph + '" fill="rgba(3,6,15,.6)"/></g>');
    o.push('<g id="cutG" class="moves"><line x1="0" x2="0" y1="' + py + '" y2="' + base + '" stroke-width="2.4"/><text id="cutLabel" x="-6" y="' + (py + 13) + '" text-anchor="end" style="font-weight:700;font-size:13px"></text></g>');
    o.push('<line id="hoverLine" x1="0" x2="0" y1="' + py + '" y2="' + base + '" stroke="rgba(234,242,255,.4)" style="display:none"/>');
    o.push('</g>');
    o.push(serLabel(2, "L", 1, -9, "I/σ", "var(--iosig)"));
    o.push(serLabel(3, "R", 4, 16, "completeness", "var(--green)"));
    o.push(serLabel(9, "R", 2, 17, "R-obs", "var(--robs)"));
    o.push(serLabel(9, "R", 3, 16, "CC½", "var(--cc)"));
    svg.innerHTML = o.join("");

    if (!critBuilt) {
      critBuilt = true;
      var host = $("#critBtns");
      CRIT.forEach(function (c, i) {
        var b = document.createElement("button");
        b.type = "button"; b.className = "ghost crit"; b.style.setProperty("--c", c.color);
        b.textContent = c.label + " · " + c.d.toFixed(2) + " Å";
        b.addEventListener("click", function () { pickCrit(i); });
        host.appendChild(b);
      });
      svg.addEventListener("pointermove", function (ev) {
        var r = svg.getBoundingClientRect(), k = Math.min(r.width / chartW, r.height / chartH);
        var x = (ev.clientX - r.left - (r.width - chartW * k) / 2) / k, best = 0, bd = 1e9;
        MID.forEach(function (d, i) { var dd = Math.abs(cx_(d) - x); if (dd < bd) { bd = dd; best = i; } });
        var s = SHELLS[best], hl = $("#hoverLine");
        hl.style.display = ""; hl.setAttribute("x1", cx_(MID[best])); hl.setAttribute("x2", cx_(MID[best]));
        $("#xsShell").textContent = "Shell to " + s[0].toFixed(2) + " Å: I/σ " + s[1].toFixed(2) + ", R-obs " + s[2].toFixed(1) + "%, CC½ " + s[3].toFixed(1) + "%, completeness " + s[4].toFixed(1) + "%";
      });
      svg.addEventListener("pointerleave", function () { $("#hoverLine").style.display = "none"; });
    }
    pickCrit(critNow);
  }

  function pickCrit(i) {
    critNow = i;
    var c = CRIT[i];
    $$(".crit").forEach(function (b, j) { b.setAttribute("aria-pressed", i === j ? "true" : "false"); });
    $$("#chart .ser").forEach(function (p) {
      var s = p.getAttribute("data-s");
      p.classList.toggle("on", s === c.id || (c.id === "sig" && s === "cc"));
    });
    var x = cx_(c.d);
    $("#cutG").style.transform = "translateX(" + x + "px)";
    $("#cutG line").setAttribute("stroke", c.color);
    var label = $("#cutLabel");
    label.textContent = c.d.toFixed(2) + " Å"; label.style.fill = c.color;
    $("#beyond").style.transform = "translateX(" + x + "px)";
    var thr = $("#thrG");
    if (c.thr === null) { thr.style.opacity = 0; }
    else {
      thr.style.opacity = 1;
      thr.style.transform = "translateY(" + (c.axis === "L" ? yL(c.thr) : yR(c.thr)) + "px)";
      $("#thrLine").setAttribute("stroke", c.color);
    }
    var d = $("#xsD"); d.textContent = c.d.toFixed(2) + " Å"; d.style.color = c.color;
    $("#xsWhy").textContent = c.why;
    $("#xsLine").innerHTML = "XSCALE.INP: <b>INCLUDE_RESOLUTION_RANGE= 999 " + c.d.toFixed(2) + "</b>";
    cutD = c.d;
    animateInset();
  }

  function animateInset() {
    if (calm) { cutShown = cutD; drawInset(); return; }
    cancelAnimationFrame(insetRaf);
    var step = function () {
      cutShown += (cutD - cutShown) * 0.18;
      if (Math.abs(cutD - cutShown) < 0.002) cutShown = cutD;
      drawInset();
      if (cutShown !== cutD) insetRaf = requestAnimationFrame(step);
    };
    step();
  }

  // A small detector: spots inside the chosen limit stay bright, the rest fall away.
  function drawInset() {
    var c = $("#inset"), g = c.getContext("2d"), w = c.width, h = c.height;
    g.fillStyle = "#050a18"; g.fillRect(0, 0, w, h);
    if (!L) return;
    var wmm = DS.nx * DS.qx, hmm = DS.ny * DS.qx, s = Math.min(w / wmm, h / hmm);
    var bx = (w - wmm * s) / 2, by = (h - hmm * s) / 2, ox = bx + DS.orgx * DS.qx * s, oy = by + DS.orgy * DS.qx * s, D = DS.dist * s;
    var cutT = Math.tan(2 * Math.asin(DS.lambda / (2 * cutShown)));
    g.globalCompositeOperation = "lighter";
    for (var e = L.bins[50]; e < L.bins[51]; e++) {
      var tx = L.X[e], ty = L.Y[e], inside = tx * tx + ty * ty <= cutT * cutT;
      g.globalAlpha = inside ? clamp(L.B[L.ID[e]], .28, .95) : .05;
      g.fillStyle = inside ? "#9edcff" : "#6b7fa8";
      g.fillRect(ox + tx * D, oy - ty * D, 1.3, 1.3);
    }
    g.globalCompositeOperation = "source-over"; g.globalAlpha = 1;
    var col = getComputedStyle(document.documentElement).getPropertyValue("--accent");
    g.strokeStyle = col; g.lineWidth = 1.6;
    g.beginPath(); g.arc(ox, oy, D * cutT, 0, Math.PI * 2); g.stroke();
  }

  /* ------------------------------------------------------------------
     Table 1
     ------------------------------------------------------------------ */
  var TABLE = [
    ["#", "Data collection"],
    ["Detector", "EIGER", "Detector"],
    ["Wavelength (Å)", "0.979338", "Wavelength (\\AA{})"],
    ["Detector distance (mm)", "197.44", "Detector distance (mm)"],
    ["Oscillation range (°)", "0.2", "Oscillation range ($^{\\circ}$)"],
    ["No. of images", "1800", "No. of images"],
    ["Total rotation range (°)", "360", "Total rotation range ($^{\\circ}$)"],
    ["Space group", "C 2 2 2₁ (#20)", "Space group", "C 2 2 2$_1$ (\\#20)"],
    ["Unit cell a, b, c (Å); α, β, γ (°)", "98.56, 119.66, 161.55; 90.0, 90.0, 90.0", "Unit cell (a, b, c (\\AA{}); $\\alpha$, $\\beta$, $\\gamma$ ($^{\\circ}$))"],
    ["#", "Data processing"],
    ["Resolution range (Å)", "19.95–1.75 (1.85–1.75)", "Resolution range (\\AA{})", "19.95--1.75 (1.85--1.75)"],
    ["Completeness (%)", "99.9 (100.0)", "Completeness (\\%)"],
    ["Redundancy", "13.8 (13.6)", "Redundancy"],
    ["R-meas (%)", "9.5 (281.2)", "R$_{meas}$ (\\%)"],
    ["R-pim (%)", "2.6 (76.0)", "R$_{pim}$ (\\%)"],
    ["R-merge (%)", "9.2 (270.7)", "R$_{merge}$ (\\%)"],
    ["⟨I/σ(I)⟩", "15.20 (0.92)", "$\\langle I/\\sigma(I)\\rangle$"],
    ["CC½ (%)", "100.0 (34.1)", "CC$_{1/2}$ (\\%)"],
    ["CC* (%)", "100.0 (71.3)", "CC* (\\%)"],
    ["Total reflections", "1321885 (198398)", "Total reflections"],
    ["Unique reflections", "95995 (14627)", "Unique reflections"],
    ["ISa", "21.40", "ISa"],
    ["Wilson B (Å²)", "30.9", "Wilson B (\\AA{}$^2$)"]
  ];
  var tableTimer = 0;

  function buildTable() {
    $("#paperTable").innerHTML = TABLE.map(function (r) {
      return r[0] === "#" ? '<tr class="sec"><td colspan="2">' + r[1] + "</td></tr>" : "<tr><td>" + r[0] + "</td><td>" + r[1] + "</td></tr>";
    }).join("");
    if (calm) $$("#paperTable tr").forEach(function (t) { t.classList.add("in"); });
    $("#copyTsv").addEventListener("click", function () {
      copy(TABLE.map(function (r) { return r[0] === "#" ? r[1] : r[0] + "\t" + r[1]; }).join("\n"), "Copied as TSV.");
    });
    $("#copyTex").addEventListener("click", function () {
      var o = ["\\begin{table}[h]", "\\centering", "\\caption{Data collection and processing statistics.}", "\\begin{tabular}{ll}", "\\hline"];
      TABLE.forEach(function (r) {
        if (r[0] === "#") o.push("\\multicolumn{2}{l}{\\textbf{" + r[1] + "}} \\\\");
        else o.push(r[2] + " & " + (r[3] || r[1]) + " \\\\");
      });
      o.push("\\hline", "\\end{tabular}", "\\end{table}");
      copy(o.join("\n"), "Copied as LaTeX.");
    });
  }

  function revealTable() {
    if (calm) return;
    clearTimeout(tableTimer);
    var rows = $$("#paperTable tr"), i = 0;
    rows.forEach(function (t) { t.classList.remove("in"); });
    var next = function () {
      if (i >= rows.length) return;
      rows[i++].classList.add("in");
      tableTimer = setTimeout(next, 55);
    };
    tableTimer = setTimeout(next, 180);
  }

  function copy(text, msg) {
    var done = function () { $("#copyMsg").textContent = msg; };
    var fallback = function () {
      var t = document.createElement("textarea");
      t.value = text; t.style.position = "fixed"; t.style.opacity = 0;
      document.body.appendChild(t); t.select();
      try { document.execCommand("copy"); done(); } catch (e) { $("#copyMsg").textContent = "Your browser blocked the copy."; }
      t.remove();
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, fallback);
    else fallback();
  }

  /* ------------------------------------------------------------------
     Hero: X-ray wavefronts from the source, glints on the crystal
     ------------------------------------------------------------------ */
  function initHero() {
    var hero = $("#hero"), art = $("#heroArt"), c = $("#heroFx"), g = c.getContext("2d"), cw = 0, ch = 0, visible = true, r = 1;
    var SRC = [72 / 1400, 418 / 876], CORE = [905 / 1400, 420 / 876];
    var GLINTS = [[705, 45], [1022, 45], [1337, 372], [1097, 197], [643, 153], [538, 318], [1120, 770], [730, 722], [453, 530], [555, 455], [945, 738], [1232, 442], [850, 118]];
    var star = document.createElement("canvas"); star.width = star.height = 96;
    var sg = star.getContext("2d");
    var rad = sg.createRadialGradient(48, 48, 0, 48, 48, 22);
    rad.addColorStop(0, "rgba(230,245,255,1)"); rad.addColorStop(.3, "rgba(130,205,255,.55)"); rad.addColorStop(1, "rgba(120,190,255,0)");
    sg.fillStyle = rad; sg.fillRect(0, 0, 96, 96);
    sg.globalCompositeOperation = "lighter";
    [[96, 3], [3, 96]].forEach(function (d) {
      var lg = d[0] > d[1] ? sg.createLinearGradient(0, 48, 96, 48) : sg.createLinearGradient(48, 0, 48, 96);
      lg.addColorStop(0, "rgba(160,215,255,0)"); lg.addColorStop(.5, "rgba(225,242,255,.95)"); lg.addColorStop(1, "rgba(160,215,255,0)");
      sg.fillStyle = lg; sg.fillRect(48 - d[0] / 2, 48 - d[1] / 2, d[0], d[1]);
    });

    function size() {
      var rc = art.getBoundingClientRect();
      r = Math.min(window.devicePixelRatio || 1, 1.5);
      cw = c.width = Math.round(rc.width * r); ch = c.height = Math.round(rc.height * r);
    }
    size();
    if (window.ResizeObserver) new ResizeObserver(size).observe(art); else addEventListener("resize", size);
    new IntersectionObserver(function (es) { visible = es[0].isIntersecting; }).observe(hero);

    // On narrow screens the picture is cropped by object-fit: cover, so art coordinates go through the same mapping.
    function map(fx, fy) {
      var s = Math.max(cw / 1400, ch / 876), ow = 1400 * s, oh = 876 * s;
      return [(cw - ow) / 2 + fx * ow, (ch - oh) / 2 + fy * oh, s];
    }

    function frame(ts) {
      requestAnimationFrame(frame);
      if (!visible || !cw) return;
      var t = ts / 1000;
      g.clearRect(0, 0, cw, ch);
      g.globalCompositeOperation = "lighter";
      var src = map(SRC[0], SRC[1]), core = map(CORE[0], CORE[1]), s = src[2];
      var reach = core[0] - src[0] - 190 * s, FRONTS = 4, PERIOD = 6.4, pulse = 0;
      for (var i = 0; i < FRONTS; i++) {
        var p = ((t / PERIOD) + i / FRONTS) % 1;
        var rad = 70 * s + p * reach, alpha = Math.sin(Math.PI * p);
        alpha = alpha * alpha * .85;
        var spread = 40 * RAD, step = (3.6 * s * 2.4) / rad;
        for (var a = -spread; a <= spread; a += step) {
          var fall = 1 - Math.abs(a) / spread;
          g.globalAlpha = alpha * (.25 + .75 * fall);
          g.fillStyle = i % 2 ? "#c9b6ff" : "#a6dcff";
          var dr = 1.5 * s * 1.4;
          g.fillRect(src[0] + Math.cos(a) * rad - dr / 2, src[1] + Math.sin(a) * rad - dr / 2, dr, dr);
        }
        if (p > .9) pulse = Math.max(pulse, (p - .9) / .1);
      }
      if (pulse > 0) {
        var R = 360 * s, grad = g.createRadialGradient(core[0], core[1], 0, core[0], core[1], R);
        grad.addColorStop(0, "rgba(120,170,255,.22)"); grad.addColorStop(1, "rgba(110,120,255,0)");
        g.globalAlpha = Math.sin(pulse * Math.PI);
        g.fillStyle = grad; g.fillRect(core[0] - R, core[1] - R, 2 * R, 2 * R);
      }
      for (i = 0; i < GLINTS.length; i++) {
        var v = Math.sin(t * (.55 + i * .07) + i * 2.4);
        v = v > 0 ? v * v * v : 0;
        if (v < .02) continue;
        var pos = map(GLINTS[i][0] / 1400, GLINTS[i][1] / 876), sz = (46 + 54 * v) * s * 1.2;
        g.globalAlpha = v;
        g.drawImage(star, pos[0] - sz / 2, pos[1] - sz / 2, sz, sz);
      }
      g.globalAlpha = 1;
    }
    if (!calm) {
      requestAnimationFrame(frame);
      hero.addEventListener("pointermove", function (ev) {
        var rc = hero.getBoundingClientRect();
        var px = (ev.clientX - rc.left) / rc.width - .5, py = (ev.clientY - rc.top) / rc.height - .5;
        art.style.transform = "translate(" + (px * -16).toFixed(1) + "px," + (py * -12).toFixed(1) + "px)";
      });
    }
  }

  /* ------------------------------------------------------------------
     Videos
     ------------------------------------------------------------------ */
  function initVideos() {
    var player = $("#player"), caption = $("#caption"), tabs = $$(".tab"), current = 0, onScreen = false, started = false;
    function select(i, play) {
      current = (i + tabs.length) % tabs.length;
      tabs.forEach(function (t, j) {
        t.setAttribute("aria-selected", j === current ? "true" : "false");
        t.tabIndex = j === current ? 0 : -1;
      });
      var t = tabs[current];
      player.poster = t.getAttribute("data-poster");
      player.src = t.getAttribute("data-src");
      caption.textContent = t.getAttribute("data-caption");
      if (play) { var pr = player.play(); if (pr && pr.catch) pr.catch(function () {}); }
    }
    tabs.forEach(function (t, i) { t.addEventListener("click", function () { select(i, true); }); });
    $(".nav-btn.prev").addEventListener("click", function () { select(current - 1, true); });
    $(".nav-btn.next").addEventListener("click", function () { select(current + 1, true); });
    player.addEventListener("ended", function () { if (onScreen) select(current + 1, true); });
    new IntersectionObserver(function (es) {
      onScreen = es[0].isIntersecting;
      if (onScreen && !started && !calm) {
        started = true;
        var pr = player.play(); if (pr && pr.catch) pr.catch(function () {});
      }
      if (!onScreen && !player.paused) player.pause();
    }, { threshold: .4 }).observe(player);
  }

  /* ------------------------------------------------------------------
     Work modes
     ------------------------------------------------------------------ */
  function initModes() {
    var MODES = [
      ["Tutorial, for first contact", "The core workflow only, with explanatory hints under every card: project, XDS.INP, run, results, XSCALE, XDSCONV and the frame viewer."],
      ["Normal, for routine processing", "Adds the AutoPilot and Statistics tabs, FRIEDEL'S_LAW in the form, CORRECT Only and GXPARM Re-integrate. In the results: Matthews calculator, cut-off estimates, ISa, shell charts, ice-ring analysis, anomalous summary, run history and comparison."],
      ["Advanced, for diagnosing problems", "Adds the POINTLESS and AIMLESS tabs and the Corrections and Reporting parameters. In the results: IDXREF spot and spindle deviations, correction-factor χ² fit, Wilson analysis, INTEGRATE mosaicity and scale charts, anomalous shell tables. In the frame viewer: the XDS diagnostic images."],
      ["Expert, for everything", "Adds the ΔCC½ and gemmi tabs, XSCALE NBATCH, Convert with gemmi in XDSCONV, Wilson distribution moments, the Full auto-indexing tier and Force cell."]
    ];
    var at = $$("#appTabs .at"), btns = $$("#modeSeg button");
    function set(m) {
      btns.forEach(function (b, i) { b.setAttribute("aria-pressed", i === m ? "true" : "false"); });
      at.forEach(function (t) {
        var need = +t.getAttribute("data-t");
        t.classList.toggle("off", need > m);
        t.classList.toggle("new", need === m && m > 0);
      });
      $("#modeName").textContent = MODES[m][0];
      $("#modeAdds").textContent = MODES[m][1];
    }
    btns.forEach(function (b, i) { b.addEventListener("click", function () { set(i); }); });
    set(0);
  }

  /* ------------------------------------------------------------------
     The XDS.INP editor
     ------------------------------------------------------------------ */
  function initEditor() {
    var FIELDS = [
      { key: "SPACE_GROUP_NUMBER", value: "20", on: true },
      { key: "UNIT_CELL_CONSTANTS", value: "98.56 119.66 161.55 90 90 90", on: true },
      { key: "SIGNAL_PIXEL", value: "3", on: false },
      { key: "SPOT_RANGE", value: "1 450", on: true },
      { key: "FRIEDEL'S_LAW", value: "TRUE", on: true, flag: true },
      { key: "INCLUDE_RESOLUTION_RANGE", value: "50 1.75", on: false }
    ];
    var form = $("#inpForm"), file = $("#inpFile"), lastKey = null;
    var esc = function (s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;"); };
    var line = function (key, value, active) {
      var body = '<span class="key">' + esc(key) + "=</span> " + esc(value);
      var html = active ? body : '<span class="cm">!' + esc(key) + "= " + esc(value) + "</span>";
      return key === lastKey ? '<span class="flash">' + html + "</span>" : html;
    };
    function render() {
      var get = function (k) { return FIELDS.filter(function (f) { return f.key === k; })[0]; };
      var rows = [
        "JOB= XYCORR INIT COLSPOT IDXREF DEFPIX INTEGRATE CORRECT",
        line("MAXIMUM_NUMBER_OF_PROCESSORS", "4", true) + "  " + line("MAXIMUM_NUMBER_OF_JOBS", "1", true),
        line("NAME_TEMPLATE_OF_DATA_FRAMES", "/data/OdoL_7/OdoL_7_3703_??????.h5", true),
        line("LIB", "dectris-neggia.so", true),
        line("OSCILLATION_RANGE", "0.2", true) + "  " + line("X-RAY_WAVELENGTH", "0.979338", true),
        line("DETECTOR", "EIGER", true) + "  " + line("NX", "4150", true) + "  " + line("NY", "4371", true) + "  " + line("QX", "0.075", true) + "  " + line("QY", "0.075", true),
        line("ORGX", "2008.9", true) + "  " + line("ORGY", "2253.1", true) + "  " + line("DETECTOR_DISTANCE", "197.44", true),
        line("DATA_RANGE", "1 1800", true)
      ];
      FIELDS.forEach(function (f) { rows.push(line(f.key, f.value, f.on)); });
      file.innerHTML = rows.join("\n");
      $("#inpLines").textContent = rows.length + " lines shown";
    }
    FIELDS.forEach(function (f) {
      var row = document.createElement("div"); row.className = "row";
      var id = "f-" + f.key.replace(/\W/g, "");
      var label = document.createElement("label"); label.htmlFor = id; label.textContent = f.key;
      var sw = document.createElement("button");
      sw.type = "button"; sw.className = "sw";
      if (f.flag) {
        // FRIEDEL'S_LAW is a TRUE / FALSE button in the program's form, always written.
        label.htmlFor = ""; sw.id = id;
        var paintFlag = function () { sw.setAttribute("aria-pressed", f.value === "TRUE" ? "true" : "false"); sw.textContent = f.value; };
        paintFlag();
        sw.addEventListener("click", function () { f.value = f.value === "TRUE" ? "FALSE" : "TRUE"; paintFlag(); lastKey = f.key; render(); });
        row.appendChild(label); row.appendChild(document.createElement("span")); row.appendChild(sw);
      } else {
        var input = document.createElement("input");
        input.spellcheck = false; input.autocomplete = "off"; input.id = id; input.value = f.value;
        var paint = function (b, field) { b.setAttribute("aria-pressed", field.on ? "true" : "false"); b.textContent = field.on ? "Active" : "Commented"; };
        paint(sw, f);
        input.addEventListener("input", function () { f.value = input.value; lastKey = f.key; render(); });
        sw.addEventListener("click", function () { f.on = !f.on; paint(sw, f); lastKey = f.key; render(); });
        row.appendChild(label); row.appendChild(input); row.appendChild(sw);
      }
      form.appendChild(row);
    });
    render();
  }

  /* ------------------------------------------------------------------
     Release: the page names one so it works offline and without scripts;
     when served from the web, the newest release replaces it.
     ------------------------------------------------------------------ */
  function initRelease() {
    if (!/^https?:$/.test(location.protocol) || !window.fetch) return;
    fetch("https://api.github.com/repos/mikaelhelias/CrystalPilot/releases/latest")
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (release) {
        if (!release || !release.tag_name) return;
        var patterns = { win: /^CrystalPilot-Setup-.*\.exe$/, mac: /-mac\.tar\.gz$/, linux: /-linux\.tar\.gz$/, py: /^crystalpilot-.*\.py$/ };
        Object.keys(patterns).forEach(function (key) {
          var asset = (release.assets || []).filter(function (a) { return patterns[key].test(a.name); })[0];
          if (!asset) return;
          $$('[data-dl="' + key + '"]').forEach(function (a) { a.href = asset.browser_download_url; });
        });
        $$("[data-version]").forEach(function (el) { el.textContent = release.tag_name.replace(/^v/, ""); });
        var beta = /beta/i.test(release.name || "");
        $$("[data-beta]").forEach(function (el) { el.hidden = !beta; });
      })
      .catch(function () {});
  }

  /* ------------------------------------------------------------------
     Small things
     ------------------------------------------------------------------ */
  function initPage() {
    var bar = $("#bar");
    addEventListener("scroll", function () { bar.classList.toggle("stuck", scrollY > 8); }, { passive: true });

    // A visitor's own system comes first among the download buttons and is marked in the download section.
    var ua = navigator.userAgent || "", me = /Mac/.test(navigator.platform || ua) ? "mac" : /Win/.test(navigator.platform || ua) ? "win" : /Linux|X11/.test(ua) && !/Android/.test(ua) ? "linux" : "";
    if (me) {
      var box_ = $(".os[data-os='" + me + "']"); if (box_) box_.classList.add("mine");
      if (me !== "win") {
        $$("[data-downloads]").forEach(function (group) {
          var win = group.querySelector('[data-dl="win"]'), mine = group.querySelector('[data-dl="' + me + '"]');
          win.classList.remove("primary"); mine.classList.add("primary");
          win.querySelector("span").textContent = "Windows";
          mine.querySelector("span").textContent = me === "mac" ? "Download for Mac" : "Download for Linux";
          group.insertBefore(mine, group.firstChild);
        });
      }
    }

    $("#copy-cite").addEventListener("click", function () {
      var button = this, text = $("#citation").textContent;
      var done = function () { button.textContent = "Copied"; setTimeout(function () { button.textContent = "Copy citation"; }, 1600); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done);
    });

    var box = $("#lightbox"), big = $("#lightboxImg");
    $$(".shot").forEach(function (s) {
      s.addEventListener("click", function () {
        big.src = s.getAttribute("data-full");
        big.alt = s.querySelector("img").alt;
        box.showModal();
      });
    });
    box.addEventListener("click", function () { box.close(); });

    var reveals = $$(".reveal");
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (es) {
        es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
      }, { rootMargin: "0px 0px -8% 0px" });
      reveals.forEach(function (r) { io.observe(r); });
    } else reveals.forEach(function (r) { r.classList.add("in"); });
  }

  initPage();
  initRelease();
  initHero();
  initLab();
  initVideos();
  initModes();
  initEditor();
})();
