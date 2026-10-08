import os, sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/lib')
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src')
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np, cv2
from chron.config import MAPS
from chron.maps import MapSet
from chron.record import replay
from chron.color import lin2srgb
from kingvoid import entry_geometry
G = MapSet(MAPS + '/p1_oath_ground'); R = G.stitches()
mids, bb = entry_geometry(R); PX = 10.0; mm = mids / PX
B = (69.0, 245.0, 90.0, 267.5)
reg = R['region']
gnd = R['group'] == 0
inb = gnd & (mm[:, 0] > B[0]) & (mm[:, 0] < B[2]) & (mm[:, 1] > B[1]) & (mm[:, 1] < B[3])
B2 = (67.5, 243.5, 91.5, 269.0)
cup = np.zeros(len(mids), bool)
for r in np.unique(reg[inb]):
    if r == 65535: continue
    e = np.nonzero(gnd & (reg == r))[0]
    fi = ((bb[e, 0] / PX > B2[0]) & (bb[e, 2] / PX < B2[2]) & (bb[e, 1] / PX > B2[1]) & (bb[e, 3] / PX < B2[3])).mean()
    mid_in = inb[e].mean()
    if fi > 0.85: cup[e] = True
    print('region', r, 'n', len(e), 'inside frac %.2f' % fi, 'mid-in %.2f' % mid_in)
# outlines
out = np.nonzero(inb & (reg == 65535))[0]
print('outline entries in box', len(out))
x0m, y0m, x1m, y1m = 60, 238, 100, 275
x0, y0, x1, y1 = [int(v * 10) for v in (x0m, y0m, x1m, y1m)]
Hh, Ww = y1 - y0, x1 - x0
def layer(sel, bg=0.5):
    m = dict(h=np.full((Hh, Ww), -10.0, np.float32), alb=np.ones((Hh, Ww, 3), np.float32) * bg, T=np.zeros((Hh, Ww, 2), np.float32),
             mat=np.zeros((Hh, Ww), np.uint8), cov=np.zeros((Hh, Ww), np.float32), sid=np.zeros((Hh, Ww), np.int32),
             sfr=np.zeros((Hh, Ww), np.float32), base=np.zeros((Hh, Ww), np.float32), stamp=np.zeros((Hh, Ww), np.int32), PX=PX)
    o = R['order']; replay(m, R, o[np.isin(o, sel)], x0, y0)
    return (np.clip(lin2srgb(np.clip(m['alb'], 0, 1)), 0, 1) * 255).astype(np.uint8)[..., ::-1]
allg = np.nonzero(gnd & (mm[:, 0] > x0m) & (mm[:, 0] < x1m) & (mm[:, 1] > y0m) & (mm[:, 1] < y1m))[0]
a = layer(allg); b = layer(np.nonzero(cup)[0]); c = layer(out)
im = np.hstack([a, b, c])
cv2.imwrite('c6_cup0.png', cv2.resize(im, None, fx=0.9, fy=0.9))
np.save('c6_cup.npy', np.nonzero(cup)[0])
