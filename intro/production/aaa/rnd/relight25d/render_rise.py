"""Knight-rise demo: the stitched knight swells (stumpwork padding), peels up from the cloth top-first and floats
~9 mm above its own underdrawing / needle-hole ghost, casting a soft detached shadow. Camera arcs from near-frontal
(12 deg) to oblique (38 deg). Output: PNG sequence + mp4."""
import sys, time, os, math, subprocess; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
cv2.setNumThreads(2)
from emb.core import *
from emb.scene import load, PX
from emb.oblique import Camera
from emb.obl_render import render_oblique, lift_map
from emb.render import undulation
W, H = int(sys.argv[1]) if len(sys.argv) > 1 else 1280, int(sys.argv[2]) if len(sys.argv) > 2 else 720
N = int(sys.argv[3]) if len(sys.argv) > 3 else 150
only = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 else None
outdir = 'work/rise_frames'; os.makedirs(outdir, exist_ok=True)
sc = load()
Hc, Wc = sc['canvas']['h'].shape
sm = lambda x: float(np.clip(x, 0, 1)) ** 2 * (3 - 2 * float(np.clip(x, 0, 1)))
times = []
for f in (only or range(N)):
    t = f / 30.0
    pad = 2.6 * sm((t - 0.6) / 1.3)
    p = sm((t - 1.6) / 1.7)
    Lb = 9.0 * sm((t - 1.7) / 1.9) + (0.35 * math.sin(2 * math.pi * 0.5 * (t - 3.6)) * sm((t - 3.6) / 0.6) if t > 3.6 else 0)
    l1 = lift_map(sc['k_alpha'], PX, Lb, curl=0.10 * Lb, peel=(p, 270) if p < 1 else None) if Lb > 0 else np.zeros_like(sc['k_alpha'], np.float32)
    e = sm(t / 4.6)
    cam = Camera((236 + 4 * e, 101 + 3 * e, 2.0 * e), 290 - 45 * e, 10 + 25 * e, 62, 28, W, H)
    U = undulation((Hc, Wc), PX, t, amp=1.0)
    light = dict(az=142 - 22 * sm(t / 5), el=21, key_i=2.8, fill_i=0.18, rim_i=0.25, rim_az=25, rim_el=9)
    tm = {}
    t0 = time.time()
    img, zf, lay = render_oblique(sc, cam, light, lift1=l1, dof_px=W / 2560 * 12, timing=tm, pad=pad, undul=U, seed=f,
                                  kmap_params=dict(cx=230, cy=95, r=120, floor=0.35, aspect=1.4))
    times.append(time.time() - t0)
    save_rgb(f'{outdir}/f{f:04d}.png', img)
    print(f, 'pad %.2f lift %.2f peel %.2f' % (pad, Lb, p), '%.2fs' % times[-1], {k: round(v, 2) for k, v in tm.items()}, flush=True)
print('mean s/frame', np.mean(times[1:]) if len(times) > 1 else times)
if only is None:
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '30', '-i', f'{outdir}/f%04d.png', '-c:v', 'libx264', '-crf', '16',
                    '-preset', 'medium', '-pix_fmt', 'yuv420p', 'out/knight_rise.mp4'], check=True)
    print('wrote out/knight_rise.mp4')
