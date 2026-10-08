import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'fs';
const G='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/game';
const OUT=G+'/boot2';
const W=960,H=540;
const t0=Date.now();
const log=(...a)=>{const s=`[${((Date.now()-t0)/1000).toFixed(1)}s] `+a.join(' ');console.log(s);fs.appendFileSync(OUT+'/boot.log',s+'\n');};
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',headless:true,
  args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--autoplay-policy=no-user-gesture-required']});
const ctx=await b.newContext({viewport:{width:W,height:H},deviceScaleFactor:1});
const p=await ctx.newPage();
p.on('console',m=>log('console.'+m.type(),m.text().slice(0,300)));
p.on('pageerror',e=>log('pageerror',String(e).slice(0,300)));
await p.route('**/__test.webm',r=>r.fulfill({status:200,contentType:'video/webm',body:fs.readFileSync(G+'/www/test.webm')}));
await p.addInitScript(()=>{
  window.__ev=[]; const T=()=>Math.round(performance.now());
  const ol=console.log; console.log=function(...a){ if(String(a[0]).startsWith('Godot Engine')) window.__ev.push(['godot_banner',T()]); return ol.apply(this,a);} ;
  new PerformanceObserver(l=>{for(const e of l.getEntries()){ if(/index\.(pck|wasm)$/.test(e.name)) window.__ev.push(['res_end '+e.name.split('/').pop(),Math.round(e.responseEnd)]);}}).observe({type:'resource',buffered:true});
  document.addEventListener('DOMContentLoaded',()=>{
    window.__ev.push(['dcl',T()]);
    const st=document.getElementById('status');
    new MutationObserver(ms=>{for(const m of ms){ if(m.type==='attributes') window.__ev.push(['status_style '+st.style.opacity,T()]); if(m.removedNodes) for(const n of m.removedNodes) if(n===st) window.__ev.push(['status_removed',T()]);}}).observe(st,{attributes:true,attributeFilter:['style']});
    new MutationObserver(ms=>{for(const m of ms) for(const n of m.removedNodes) if(n.id==='status') window.__ev.push(['status_removed',T()]);}).observe(document.body,{childList:true});
    const v=document.createElement('video'); v.src='/__test.webm'; v.muted=true; v.autoplay=true; v.loop=true; v.playsInline=true;
    v.style.cssText='position:fixed;right:0;bottom:0;width:320px;height:180px;z-index:50;';
    document.body.appendChild(v); window.__vf=[];
    const cb=(now,md)=>{window.__vf.push([Math.round(now),md.presentedFrames,+md.mediaTime.toFixed(3)]); v.requestVideoFrameCallback(cb);};
    v.requestVideoFrameCallback(cb);
    // rAF heartbeat to measure main-thread blocks
    window.__raf=[]; const rf=()=>{window.__raf.push(T()); requestAnimationFrame(rf);}; requestAnimationFrame(rf);
  });
});
await p.goto('http://127.0.0.1:8765/index.html',{waitUntil:'domcontentloaded'});
log('dcl');
// wait until status removed (page responsive again)
for(let i=0;i<600;i++){
  const gone=await p.evaluate(()=>!document.getElementById('status'));
  if(gone){log('status gone');break;}
  await p.waitForTimeout(500);
}
await p.screenshot({path:OUT+'/first_frame_960.png'});
log('shot1');
const data=await p.evaluate(()=>{
  const raf=window.__raf; let gaps=[]; for(let i=1;i<raf.length;i++){const g=raf[i]-raf[i-1]; if(g>200) gaps.push([raf[i-1],g]);}
  const vf=window.__vf; let vgaps=[]; for(let i=1;i<vf.length;i++){const g=vf[i][0]-vf[i-1][0]; if(g>200) vgaps.push({at:vf[i-1][0],gap_ms:g,presented_before:vf[i-1][1],presented_after:vf[i][1],media_before:vf[i-1][2],media_after:vf[i][2]});}
  return {ev:window.__ev,rafGaps:gaps,videoGaps:vgaps,vfCount:vf.length,lastVf:vf[vf.length-1]};
});
fs.writeFileSync(OUT+'/timing.json',JSON.stringify(data,null,1));
log('timing',JSON.stringify(data).slice(0,1500));
await p.waitForTimeout(3000);
await p.screenshot({path:OUT+'/first_frame_960_b.png'});
await b.close(); log('done');
