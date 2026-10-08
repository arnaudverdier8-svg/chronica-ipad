"""Motion test: 3 s @30fps, frontal rostrum camera trucking right + slight push-in while the key light sweeps
left->right (az 155 -> 65) and rises (el 16 -> 26). Cloth sways (undulation over time). Output mp4."""
import sys, time, os, math, subprocess; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
cv2.setNumThreads(2)
from emb.core import *
from emb.scene import load, composite_flat, PX
from emb.render import frontal, spot, undulation
W, H = int(sys.argv[1]) if len(sys.argv) > 1 else 1280, int(sys.argv[2]) if len(sys.argv) > 2 else 720
N = int(sys.argv[3]) if len(sys.argv) > 3 else 90
outdir = 'work/motion_frames'; os.makedirs(outdir, exist_ok=True)
sc = load(); c, fib = composite_flat(sc)
Hc, Wc = c['h'].shape
km = spot((Hc, Wc), PX, 150, 92, 100, floor=0.3, aspect=1.55)
ease = lambda x: x * x * (3 - 2 * x)
times = []
for f in range(N):
    u = f / (N - 1); e = ease(u)
    az = 155 - 90 * e; el = 16 + 10 * e
    w_mm = 200 - 18 * e                       # slow push-in
    x0 = 38 + 34 * e; y0 = 100 - w_mm * 9 / 32   # truck right (~4.6 px/frame at 1280 => slow)
    U = undulation((Hc, Wc), PX, f / 30.0, amp=1.2)
    light = dict(az=az, el=el, key_i=3.0, fill_i=0.17, rim_i=0.2, rim_az=25, rim_el=9)
    t = time.time()
    img = frontal(c, (x0 * PX, y0 * PX, w_mm * PX, w_mm * 9 / 16 * PX), (W, H), light, fib=fib, kmap=km, exposure=0.95,
                  undul=U, seed=f)
    times.append(time.time() - t)
    save_rgb(f'{outdir}/f{f:04d}.png', img)
    print(f, '%.2fs' % times[-1], flush=True)
print('mean s/frame', np.mean(times[1:]))
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '30', '-i', f'{outdir}/f%04d.png', '-c:v', 'libx264', '-crf', '16',
                '-preset', 'medium', '-pix_fmt', 'yuv420p', 'out/motion_test.mp4'], check=True)
print('wrote out/motion_test.mp4')
