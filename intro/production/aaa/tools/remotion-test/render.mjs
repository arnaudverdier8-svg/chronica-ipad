// node render.mjs OUT.mp4 CONCURRENCY IMAGEFORMAT(jpeg|png) [COLORSPACE]
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import path from 'node:path';
const [out, conc, fmt, cs] = process.argv.slice(2);
const browserExecutable = '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';
const t0 = Date.now();
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts'), publicDir: path.resolve('public')});
const t1 = Date.now();
const composition = await selectComposition({serveUrl, id: 'Test', browserExecutable, logLevel: process.env.LOG || 'info'});
const t2 = Date.now();
let firstFrameAt = null, lastRendered = 0;
await renderMedia({
  serveUrl, composition, codec: 'h264', outputLocation: out, browserExecutable,
  concurrency: Number(conc), logLevel: process.env.LOG || 'info', imageFormat: fmt, jpegQuality: 92, crf: 16,
  colorSpace: cs || 'bt709', pixelFormat: 'yuv420p', audioCodec: 'aac', audioBitrate: '320k',
  onProgress: ({renderedFrames}) => { if (renderedFrames > 0 && firstFrameAt === null) firstFrameAt = Date.now(); lastRendered = renderedFrames; },
});
const t3 = Date.now();
console.log(`RTIME bundle=${(t1-t0)/1000}s select=${(t2-t1)/1000}s render+encode=${(t3-t2)/1000}s firstFrame=${((firstFrameAt??t3)-t2)/1000}s frames=${lastRendered} per_frame_steady=${((t3-(firstFrameAt??t2))/1000/Math.max(1,lastRendered-1)).toFixed(3)}s per_frame_total=${((t3-t2)/1000/60).toFixed(3)}s`);
