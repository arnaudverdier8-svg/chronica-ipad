"""Seconds/frame at 2560x1440 for the three render modes (NUMBA_NUM_THREADS / cv2 threads = 2)."""
import sys, time, os, json; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
cv2.setNumThreads(2)
from emb.core import *
from emb.scene import load, composite_flat, PX
from emb.render import frontal, spot, undulation
from emb.oblique import Camera
from emb.obl_render import render_oblique, lift_map
from emb.fibres import render_fibres
from emb.shade import light_vec
res = {}
sc = load(); c, fib = composite_flat(sc)
H, W = c['h'].shape
km = spot((H, W), PX, 150, 92, 100, floor=0.3, aspect=1.55)
U = undulation((H, W), PX, 0.0, amp=1.2)
view = (23 * PX, 20 * PX, 284 * PX, 160 * PX)
# A) frontal, light moving -> full relight each frame
ts = []
for i in range(3):
    light = dict(az=150 - 20 * i, el=20, key_i=3.0, fill_i=0.17, rim_i=0.22, rim_az=25, rim_el=9)
    t = time.time(); img = frontal(c, view, (2560, 1440), light, fib=fib, kmap=km, undul=U); ts.append(time.time() - t)
res['frontal_relight_s'] = float(np.median(ts))
# B) frontal, light static, camera moving -> cached linear shaded plate, warp + fibres + grade only
light = dict(az=122, el=20, key_i=3.0, fill_i=0.17, rim_i=0.22, rim_az=25, rim_el=9)
from emb.shade import relight
from emb.fibres import halo
col, vis = relight(c, N=c['N'], ao=c['ao'], kmap=km, **light); col = halo(col, c)
ts = []
for i in range(3):
    t = time.time()
    x0, y0, w, h = view[0] + 5 * i, view[1], view[2] * 0.99, view[3] * 0.99
    sx = 2560 / w
    M = np.array([[sx, 0, -x0 * sx], [0, sx, -y0 * sx]], np.float32)
    img = cv2.warpAffine(cv2.GaussianBlur(col, (0, 0), 0.45), M, (2560, 1440), flags=cv2.INTER_LINEAR)
    def project(P):
        Q = np.empty(P.shape[:2] + (2,), np.float32); Q[..., 0] = (P[..., 0] * PX - x0) * sx; Q[..., 1] = (P[..., 1] * PX - y0) * sx
        return Q, -P[..., 2]
    render_fibres(img, fib, light_vec(122, 20), np.array([1, .92, .8], np.float32) * 3.0, np.array([.8, .86, 1], np.float32) * .17, vis, project)
    out = grade(img, 0.95, grain=0.012, seed=i)
    ts.append(time.time() - t)
res['frontal_camera_only_cached_s'] = float(np.median(ts))
# C) oblique ray-march with lifted, padded figure + DOF (ss=1 and ss=2)
cam = Camera((214, 99, 0), 215, 42, 72, 28, 2560, 1440)
l1 = lift_map(sc['k_alpha'], PX, 8.0, curl=0.8)
for ss in (1, 2):
    tm = {}
    t = time.time()
    render_oblique(sc, cam, dict(az=128, el=22, key_i=2.8, fill_i=0.18, rim_i=0.25, rim_az=25, rim_el=9), lift1=l1, dof_px=14,
                   timing=tm, pad=2.5, undul=U, ss=ss)
    res[f'oblique_lifted_ss{ss}_s'] = time.time() - t
    res[f'oblique_lifted_ss{ss}_breakdown'] = {k: round(v, 2) for k, v in tm.items()}
res['threads'] = 2
print(json.dumps(res, indent=1))
json.dump(res, open('out/bench_1440.json', 'w'), indent=1)
