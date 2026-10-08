// Capture the live CHRONICA main menu's first frames natively (no upscaling) in the
// no-save state, with a deterministic virtual clock so the menu camera tour (3 s hold,
// then a 14 s pan) cannot start while SwiftShader renders slowly.
//
// Virtual clock: performance.now() is frozen inside each browser frame and advances by
// exactly 1000/60 ms per requestAnimationFrame tick, so Godot sees a steady 60 fps
// (FramePace keeps scaling_3d_scale = 1.0, as on a fast device) and game time is
// frame-based and reproducible. After the HTML loader starts fading (startGame resolved,
// i.e. callMain done: menu built and its first iteration run) we let K more Godot frames
// run, then hold every rAF callback: the canvas keeps the last presented image and we
// screenshot it (several times, to prove the frozen frame is stable).
//
// usage: W=2560 H=1440 OUT=dir FRAMES=6,30 node capture_menu.mjs
import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'fs';
const W = +process.env.W || 2560, H = +process.env.H || 1440;
const OUT = process.env.OUT;
const FRAMES = (process.env.FRAMES || '6,30').split(',').map(Number); // menu frames to grab, ascending
const ARGS = process.env.ARGS || '';
fs.mkdirSync(OUT, {recursive: true});
const t0 = Date.now();
const log = (...a) => { const s = `[${((Date.now() - t0) / 1000).toFixed(1)}s] ` + a.join(' '); console.log(s); fs.appendFileSync(OUT + '/capture.log', s + '\n'); };
const b = await chromium.launch({executablePath: '/opt/pw-browsers/chromium', headless: true,
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl',
         '--autoplay-policy=no-user-gesture-required', '--disable-background-timer-throttling',
         '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows']});
const ctx = await b.newContext({viewport: {width: W, height: H}, deviceScaleFactor: 1}); // fresh profile: no IDBFS save => 5-button card
const p = await ctx.newPage();
p.on('console', m => log('console.' + m.type(), m.text().slice(0, 300)));
p.on('pageerror', e => log('pageerror', String(e).slice(0, 300)));
await p.addInitScript(() => {
  const realNow = performance.now.bind(performance);
  const st = window.__vc = {virt: false, vt: 0, frame: 0, lastTs: -1, freezeAt: Infinity, held: [], menuFrame: -1};
  performance.now = function () { return st.virt ? st.vt : realNow(); };
  const realRAF = window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame = function (cb) {
    return realRAF(function (ts) {
      if (st.frame >= st.freezeAt) { st.held.push(cb); return; }
      if (ts !== st.lastTs) {           // a new browser frame: advance the virtual clock once
        st.lastTs = ts;
        if (!st.virt) { st.virt = true; st.vt = realNow(); } else { st.vt += 1000 / 60; }
        st.frame++;
      }
      cb(st.vt);
    });
  };
  window.__release = function (n) {      // run n more frames, then hold again
    st.freezeAt = st.frame + n;
    const h = st.held; st.held = [];
    for (const cb of h) window.requestAnimationFrame(cb);
  };
  document.addEventListener('DOMContentLoaded', () => {
    const s = document.getElementById('status');
    new MutationObserver(() => { if (s.style.opacity === '0' && st.menuFrame < 0) { st.menuFrame = st.frame; st.freezeAt = st.frame + (window.__firstHold || 1); } })
      .observe(s, {attributes: true, attributeFilter: ['style']});
  });
});
await p.addInitScript(`window.__firstHold = ${FRAMES[0]};`);
const url = 'http://127.0.0.1:8765/index.html' + (ARGS ? '?args=' + ARGS : '');
await p.goto(url, {waitUntil: 'domcontentloaded'});
log('domcontentloaded', url, W + 'x' + H);
// wait for the loader to start fading (callMain done) and for the hold
let vc;
for (let i = 0; i < 2400; i++) {
  vc = await p.evaluate(() => ({frame: __vc.frame, menu: __vc.menuFrame, held: __vc.held.length, freezeAt: __vc.freezeAt, vt: __vc.vt}));
  if (vc.menu >= 0 && vc.held > 0) break;
  if (i % 20 === 0) log('wait', JSON.stringify(vc));
  await p.waitForTimeout(500);
}
log('menu at frame', vc.menu, 'held at', vc.frame);
// the loader overlay fades over 0.5 s (CSS, real time) and is removed after 600 ms
for (let i = 0; i < 60; i++) { if (await p.evaluate(() => !document.getElementById('status'))) break; await p.waitForTimeout(250); }
await p.waitForTimeout(1500);
const env = await p.evaluate(() => ({iw: innerWidth, ih: innerHeight, dpr: devicePixelRatio,
  cw: document.getElementById('canvas').width, ch: document.getElementById('canvas').height,
  idb: typeof indexedDB, dev: window.chronicaDevice && window.chronicaDevice()}));
log('env', JSON.stringify(env));
let prev = vc.menu;
for (let k = 0; k < FRAMES.length; k++) {
  const target = FRAMES[k];
  if (k > 0) {
    await p.evaluate(n => __release(n), target - FRAMES[k - 1]);
    for (let i = 0; i < 2400; i++) {
      vc = await p.evaluate(() => ({frame: __vc.frame, held: __vc.held.length, freezeAt: __vc.freezeAt}));
      if (vc.frame >= vc.freezeAt && vc.held > 0) break;
      await p.waitForTimeout(500);
    }
    await p.waitForTimeout(1500);
  }
  const f = await p.evaluate(() => __vc.frame - __vc.menuFrame);
  for (let r = 0; r < 2; r++) {
    const fn = `${OUT}/menu_${W}x${H}_mf${String(f).padStart(3, '0')}_r${r}.png`;
    await p.screenshot({path: fn});
    log('shot', fn);
  }
}
await b.close();
log('done');
