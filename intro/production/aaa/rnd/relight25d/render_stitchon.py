"""Stitch-on demo: replay the recorded stitches of the knight in embroidery order (laid fills region by region with a
sweeping needle front, couching bars, then the couched outline cord), relit every 2 frames (on twos). Output mp4."""
import sys, time, os, math, subprocess; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
cv2.setNumThreads(1)
from emb.core import *
from emb.linen import make_linen, add_ageing
from emb import stitch as S
from emb.strands import raster_stitch
from emb.motif_knight import build_knight
from emb.render import frontal, prepare, spot
from emb.shade import normals, ambient_occlusion
from emb.fibres import make_fibres
PX = 10.0
N = int(sys.argv[1]) if len(sys.argv) > 1 else 120
OUT = int(sys.argv[2]) if len(sys.argv) > 2 else 900
outdir = 'work/stitchon_frames'; os.makedirs(outdir, exist_ok=True)
H = W = 1500
base = make_linen(H, W, PX, seed=31); add_ageing(base, seed=4, density=0.3)
S.RECORD = []
K = build_knight(base, PX, 135.0, 'blue', seed=2, margin_mm=0.2, verbose=False)
rec = S.RECORD; S.RECORD = None
final_base = K['maps']['base'].copy()
print('recorded stitches', len(rec))
# order: group by tag (builder order), within a fill region sweep along a diagonal (needle travels across the shape)
groups = []
for r_ in rec:
    if not groups or groups[-1][0] != r_[-1]: groups.append([r_[-1], []])
    groups[-1][1].append(r_)
seq = []
for tag, g in groups:
    if tag is not None and tag[0] == 'fill':
        c = np.array([st[0].mean(0) + np.array(st[15]) for st in g])
        # laid strands first (radius >= 0.3), then couching bars / tie-downs in their original order
        laid = [i for i, st in enumerate(g) if st[2] >= 0.3 and st[12] < 0.25]
        rest = [i for i in range(len(g)) if i not in set(laid)]
        o = sorted(laid, key=lambda i: c[i, 0] * 0.8 + c[i, 1] * 0.6)
        seq += [g[i] for i in o] + [g[i] for i in rest]
    else:
        seq += g
m = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in base.items()}
S.ensure(m); m['base'][:] = final_base
km = spot((H, W), PX, 70, 70, 90, floor=0.45)
light = dict(az=128, el=20, key_i=2.9, fill_i=0.18, rim_i=0.2, rim_az=25, rim_el=9)
n = len(seq); done = 0
uniq = N // 2
times = []
for u in range(uniq + 1):
    target = int(n * min(1.0, (u / uniq) ** 1.15)) if u < uniq else n
    for st in seq[done:target]:
        p, col, r_mm, h0, hamp, matid, ply_mm, ply_deg, taper, tw, seed, cov, hbias, sid, pexp, oxy, tag = st
        q = (p + np.array(oxy, np.float32)).astype(np.float32)
        raster_stitch(m['h'], m['alb'], m['T'], m['mat'], m['cov'], m['sid'], m['base'], q, float(r_mm * PX), float(h0), float(hamp),
                      float(col[0]), float(col[1]), float(col[2]), int(matid), float(ply_mm * PX), float(math.tan(math.radians(ply_deg))),
                      float(taper * PX), int(sid), int(seed), float(math.radians(tw)), float(PX), float(cov), float(hbias),
                      float(pexp if pexp is not None else (0.5 if matid == 3 else 0.42)))
    done = target
    t = time.time()
    m['N'] = normals(m['h'], PX); m['ao'] = ambient_occlusion(m['h'], PX)
    fib = make_fibres(m, density=1.0, seed=6) if done > 50 else None
    img = frontal(m, (100, 50, 1300, 1300), (OUT, OUT), light, fib=fib, kmap=km, exposure=0.95, seed=u)
    times.append(time.time() - t)
    for k in range(2):
        if 2 * u + k < N: save_rgb(f'{outdir}/f{2 * u + k:04d}.png', img)
    print(u, done, '%.2fs' % times[-1], flush=True)
print('mean relight s', np.mean(times))
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '30', '-i', f'{outdir}/f%04d.png', '-c:v', 'libx264', '-crf', '17',
                '-preset', 'medium', '-pix_fmt', 'yuv420p', 'out/stitch_on_demo.mp4'], check=True)
print('wrote out/stitch_on_demo.mp4')
