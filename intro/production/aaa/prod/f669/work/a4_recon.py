"""Verify: the ground patch can be rebuilt exactly from analytic linen + stored ghost layers + replay of ground entries."""
import os, sys, time
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/lib')
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np, cv2
from chron.config import MAPS
from chron.maps import MapSet
from chron.record import replay, blank_like
from chron.linen import make_linen
from chron.color import hex_lin
W = os.path.dirname(os.path.abspath(__file__))
G = MapSet(MAPS + '/p1_oath_ground')
R = G.stitches()
PX = 10.0
x0, y0, x1, y1 = 2250, 1300, 3700, 2850
M = 40   # blur margin
t = time.time()
ly = G.read_px(x0 - M, y0 - M, x1 + M, y1 + M, 0, keys=['ghost', 'ud', 'holes', 'pad'])
print('layers', time.time() - t)
# global linen albedo mean (bake normalisation of the ink colour): estimate on a large sample
t = time.time()
samp = [make_linen(400, 400, PX, xm, ym, seed=11)['alb'].mean() for xm in (50, 250, 450) for ym in (40, 160, 280)]
amean = float(np.mean(samp)); print('alb mean est', amean, np.std(samp), time.time() - t)
H, Wd = y1 - y0 + 2 * M, x1 - x0 + 2 * M
lin = make_linen(H, Wd, PX, (x0 - M) / PX, (y0 - M) / PX, seed=11)
gm = ly['ghost'].astype(np.float32)
s = cv2.GaussianBlur(gm, (0, 0), 0.4 * PX)
lin['h'] = np.where(lin['h'] > 0, lin['h'] * (1 - 0.30 * s), lin['h']).astype(np.float32)
ink = hex_lin('#6E3326')
a = np.clip(ly['ud'].astype(np.float32) * 0.72, 0, 0.6)[..., None]
lin['alb'] = lin['alb'] * (1 - a) + (lin['alb'] * ink / (amean + 1e-3) * 0.9) * a
hole = ly['holes'].astype(np.float32)
rim = np.clip(cv2.GaussianBlur(hole, (0, 0), 0.22 * PX) * 1.7 - hole, 0, 1)
lin['h'] = lin['h'] - 0.28 * hole + 0.07 * rim
lin['alb'] = lin['alb'] * (1 - 0.5 * hole[..., None]) * (1 + 0.06 * rim[..., None])
for k in ('h', 'alb', 'T', 'cov'):
    lin[k] = lin[k].astype(np.float16)
# crop margin
for k in ('h', 'alb', 'T', 'mat', 'cov'):
    lin[k] = lin[k][M:-M, M:-M]
mm = blank_like(lin)
mm['base'] = ly['pad'][M:-M, M:-M].astype(np.float32)
off = R['off']
bx0 = np.minimum.reduceat(R['P'][:, 0], off[:-1]); bx1 = np.maximum.reduceat(R['P'][:, 0], off[:-1])
by0 = np.minimum.reduceat(R['P'][:, 1], off[:-1]); by1 = np.maximum.reduceat(R['P'][:, 1], off[:-1])
pad = 30
hit = (bx1 > x0 - pad) & (bx0 < x1 + pad) & (by1 > y0 - pad) & (by0 < y1 + pad)
order = R['order']
sel = order[(R['group'][order] == 0) & hit[order]]
print('ground entries to replay', len(sel))
t = time.time()
replay(mm, R, sel, x0, y0)
print('replay', time.time() - t)
st = G.read_px(x0, y0, x1, y1, 0, keys=['h', 'alb', 'T', 'mat', 'cov', 'sid'])
for k in ('h', 'alb', 'mat'):
    dd = np.abs(mm[k].astype(np.float32) - st[k].astype(np.float32))
    print(k, 'max', dd.max(), 'p99.9', np.quantile(dd, 0.999), 'frac>1e-2', (dd > 1e-2).mean())
print('sid equal frac', (mm['sid'] == st['sid']).mean())
dd = np.abs(mm['alb'].astype(np.float32) - st['alb'].astype(np.float32)).max(-1)
cv2.imwrite(os.path.join(W, 'a4_diff.png'), np.clip(dd * 2000, 0, 255).astype(np.uint8)[::2, ::2])
