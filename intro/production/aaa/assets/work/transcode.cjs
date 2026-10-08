const fs=require('fs'),path=require('path');
const BASIS=require('./npm/package/examples/jsm/libs/basis/basis_transcoder.js');
const wasm=fs.readFileSync(path.join(__dirname,'npm/package/examples/jsm/libs/basis/basis_transcoder.wasm'));
BASIS({wasmBinary:wasm}).then(M=>{
  M.initializeBasis();
  const dir=process.argv[2], out=process.argv[3];
  for(const fn of fs.readdirSync(dir)){
    if(!fn.endsWith('.ktx2'))continue;
    const data=new Uint8Array(fs.readFileSync(path.join(dir,fn)));
    const k=new M.KTX2File(data);
    if(!k.isValid()){console.log('invalid',fn);continue;}
    const w=k.getWidth(),h=k.getHeight(),hasA=k.getHasAlpha(),uastc=k.isUASTC();
    if(!k.startTranscoding()){console.log('start fail',fn);continue;}
    const fmt=13; // cTFRGBA32
    const sz=k.getImageTranscodedSizeInBytes(0,0,0,fmt);
    const dst=new Uint8Array(sz);
    const ok=k.transcodeImage(dst,0,0,0,fmt,0,-1,-1);
    k.close();k.delete();
    if(!ok){console.log('transcode fail',fn);continue;}
    fs.writeFileSync(path.join(out,fn.replace('.ktx2','.rgba')),dst);
    fs.writeFileSync(path.join(out,fn.replace('.ktx2','.json')),JSON.stringify({w,h,hasA,uastc}));
    console.log(fn,w,h,hasA,uastc,sz);
  }
});
