// Capture UI-free demo-mode plates of the game's menu world (seed 4242) with Playwright Chromium + SwiftShader.
// usage: node capture_plates.mjs   (needs the static server on 127.0.0.1:8765 serving /home/user/chronica-ipad)
import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'fs';
const OUT=process.argv[2];
const W=+(process.env.W||1920), H=+(process.env.H||1080);
const cfgs=JSON.parse(process.argv[3]);
const t0=Date.now();
const log=(...a)=>{const s=`[${((Date.now()-t0)/1000).toFixed(1)}s] `+a.join(' ');console.log(s);fs.appendFileSync(OUT+'/capture.log',s+'\n');};
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',headless:true,
  args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--enable-webgl']});
for(const [name,args] of cfgs){
  const ctx=await b.newContext({viewport:{width:W,height:H},deviceScaleFactor:1});
  const p=await ctx.newPage();
  p.on('console',m=>{const t=m.text(); if(!/WebGL|GPU stall/.test(t)) log(name,'console',t.slice(0,200));});
  await p.goto('http://127.0.0.1:8765/index.html?args='+args,{waitUntil:'domcontentloaded'});
  for(let i=0;i<600;i++){const st=await p.evaluate(()=>{const s=document.getElementById('status');return s?getComputedStyle(s).opacity+'|'+getComputedStyle(s).display:'gone'}); if(st==='gone'||!st.startsWith('1')||st.endsWith('none')) {log(name,'status',st);break;} await p.waitForTimeout(500);}
  await p.waitForTimeout(+(process.env.SETTLE||45000));
  await p.screenshot({path:`${OUT}/${name}.png`,timeout:180000}); log(name,"shot");
  await ctx.close();
}
await b.close(); log('done');
