import {chromium} from '/opt/node22/lib/node_modules/playwright/index.mjs';
import fs from 'fs';
const OUT='/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/game/boot';
const W=+process.env.W||1920, H=+process.env.H||1080;
const log=(...a)=>{const s=`[${((Date.now()-t0)/1000).toFixed(1)}s] `+a.join(' ');console.log(s);fs.appendFileSync(OUT+'/boot.log',s+'\n');};
const t0=Date.now();
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',headless:true,
  args:['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--enable-webgl','--autoplay-policy=no-user-gesture-required']});
const ctx=await b.newContext({viewport:{width:W,height:H},deviceScaleFactor:1});
const p=await ctx.newPage();
p.on('console',m=>log('console.'+m.type(),m.text().slice(0,400)));
p.on('pageerror',e=>log('pageerror',String(e).slice(0,400)));
p.on('requestfailed',r=>log('requestfailed',r.url(),r.failure()?.errorText));
const cdp=await ctx.newCDPSession(p);
await cdp.send('Network.enable');
// throttle so the HTML loading screen is visible mid-progress (~25 MB/s)
await cdp.send('Network.emulateNetworkConditions',{offline:false,latency:20,downloadThroughput:25*1024*1024,uploadThroughput:1e7});
await p.goto('http://127.0.0.1:8765/index.html',{waitUntil:'domcontentloaded'});
log('domcontentloaded');
await p.waitForTimeout(400);
await p.screenshot({path:OUT+'/00_loading_start.png'});
let shotLoading=false;
for(let i=0;i<200;i++){
  const st=await p.evaluate(()=>{const s=document.getElementById('status');const f=document.getElementById('fill');return s?{op:getComputedStyle(s).opacity,w:f.style.width}:null});
  if(st && !shotLoading && parseFloat(st.w)>=35){await p.screenshot({path:OUT+'/01_loading_mid.png'});log('loading mid',st.w);shotLoading=true;}
  if(!st || st.op!=='1'){log('status gone/fading',JSON.stringify(st));break;}
  await p.waitForTimeout(250);
}
await cdp.send('Network.emulateNetworkConditions',{offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1});
// capture the handoff frames densely
for(let i=0;i<8;i++){await p.screenshot({path:OUT+`/02_handoff_${i}.png`});log('handoff shot',i);await p.waitForTimeout(300);}
const gl=await p.evaluate(()=>{const c=document.createElement('canvas');const g=c.getContext('webgl2');if(!g)return 'no webgl2';const d=g.getExtension('WEBGL_debug_renderer_info');return d?g.getParameter(d.UNMASKED_RENDERER_WEBGL):'webgl2 ok';});
log('webgl2 renderer:',gl);
let poll=0;
const deadline=Date.now()+ (+process.env.MAXSEC||900)*1000;
while(Date.now()<deadline){
  await p.waitForTimeout(4000);
  let cmd='';
  try{cmd=fs.readFileSync(OUT+'/cmd','utf8').trim();fs.unlinkSync(OUT+'/cmd');}catch(e){}
  if(cmd==='STOP')break;
  if(cmd.startsWith('SHOT ')){const [_,name,w,h]=cmd.split(' ');
    if(w){await p.setViewportSize({width:+w,height:+h});await p.waitForTimeout(6000);}
    await p.screenshot({path:OUT+'/'+name+'.png'});log('shot',name,w||'',h||'');continue;}
  if(cmd.startsWith('SEQ ')){const [_,name,n,ms]=cmd.split(' ');
    for(let k=0;k<+n;k++){await p.screenshot({path:OUT+`/${name}_${String(k).padStart(2,'0')}.png`});await p.waitForTimeout(+ms);}
    log('seq',name,n,ms);continue;}
  if(cmd.startsWith('EVAL ')){try{log('eval',JSON.stringify(await p.evaluate(cmd.slice(5))));}catch(e){log('evalerr',String(e));}continue;}
  if(cmd.startsWith('CLICK ')){const [_,x,y]=cmd.split(' ');await p.mouse.click(+x,+y);log('click',x,y);continue;}
  const fn=OUT+`/10_poll_${String(poll).padStart(3,'0')}.jpg`;
  if(poll%2===0||poll<20){await p.screenshot({path:fn,type:'jpeg',quality:70});} log('poll',poll); poll++;
}
await b.close();
log('done');
