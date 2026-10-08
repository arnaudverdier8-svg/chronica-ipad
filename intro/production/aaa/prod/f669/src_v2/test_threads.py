"""Standalone look-dev of the thread renderer: gold cords and purple wool on a flat linen colour, at the f669 scale."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np, cv2
import shot
from threads3d import ThreadSet
from chron.color import hex_lin, lin2oklab, oklab2lin
from chron import grade
f = 669
s = 5.8125
W, H = 300, 200
img = np.ones((H, W, 3), np.float32) * np.array([0.30, 0.22, 0.13], np.float32)
ctx = dict(x0=296.0, y0=205.0, s=s)
light = shot.light_of(f)
cpos = light['candle']['pos_mm']
lfn = shot.thread_light_fn(f)
fill = shot.NIGHT * shot.FILL_I * shot.I0
ts = ThreadSet()
# gold cords: three, with different shapes
for i, (a, b) in enumerate([((296, 176, 14.0), (306, 196, 0.2)), ((315, 180, 14.2), (325, 178, 0.2)), ((330, 190, 14.5), (318, 208, 0.2))]):
    t = np.linspace(0, 1, 44)[:, None]
    P = np.array(a) * (1 - t) + np.array(b) * t
    P[:, 2] -= 3.2 * np.sin(np.pi * t[:, 0])
    P[:, 2] = np.maximum(P[:, 2], 0.2)
    ts.add(P, float(os.environ.get('CR', 0.42)), shot.GOLD_CORD, kind=3, seed=i / 4.0, shadow=0.0, halo=0.0, dip_end=True)
# wool strands
Aa = np.array([0.050, 0.026, 0.050], np.float32)
for i, (a, b, h) in enumerate([((300, 212), (330, 222), 6.0), ((300, 226), (338, 232), 3.0), ((298, 236), (312, 246), 1.0)]):
    t = np.linspace(0, 1, 120)
    L = np.hypot(b[0] - a[0], b[1] - a[1])
    x = a[0] + (b[0] - a[0]) * t + 0.5 * np.sin(t * 9 + i)
    y = a[1] + (b[1] - a[1]) * t + 0.5 * np.cos(t * 7 + i)
    z = 0.45 + h * np.sin(np.pi * t) ** 2 * (t > 0.3)
    ts.add(np.c_[x, y, z], 0.42, Aa * (1 + 0.15 * i), kind=0, seed=0.3 + i * 0.21, slub=0.2, dip=True, fray=6, halo=0.22, fuzz_k=1.2)
ts.render(img, ctx, cpos, lfn, fill, shadow_strength=0.84, fuzz=True, fuzz_seed=3, flame_r_mm=6.0)
out = grade.grade(img, exposure=shot.EXPOSURE, act='II', seed=1)
cv2.imwrite(os.path.join(HERE, '..', 'work', 'test_threads.png'), cv2.resize(out[..., ::-1], None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC))
