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
W = os.path.dirname(os.path.abspath(__file__))
G = MapSet(MAPS + '/p1_oath_ground'); R = G.stitches()
mids, bb = entry_geometry(R); PX = 10.0; mm = mids / PX
BOX = [(272.5, 280.5, 111.0, 124.5), (280.5, 289.0, 110.0, 118.5), (301.5, 310.0, 110.0, 118.0), (310.5, 319.5, 113.0, 124.5)]
sel = np.nonzero(R['group'] == 0)[0]
tip = np.zeros(len(R['typ']), bool)
for x0, x1, y0, y1 in BOX:
    tip |= (mm[:, 0] > x0) & (mm[:, 0] < x1) & (mm[:, 1] > y0) & (mm[:, 1] < y1) & (R['group'] == 0)
ids = np.nonzero(tip)[0]; print(len(ids))
X0, Y0, X1, Y1 = 2600, 1000, 3300, 1300
Hh, Ww = Y1 - Y0, X1 - X0
def layer(sel_):
    m = dict(h=np.full((Hh, Ww), -10.0, np.float32), alb=np.ones((Hh, Ww, 3), np.float32) * 0.5, T=np.zeros((Hh, Ww, 2), np.float32),
             mat=np.zeros((Hh, Ww), np.uint8), cov=np.zeros((Hh, Ww), np.float32), sid=np.zeros((Hh, Ww), np.int32),
             sfr=np.zeros((Hh, Ww), np.float32), base=np.zeros((Hh, Ww), np.float32), stamp=np.zeros((Hh, Ww), np.int32), PX=PX)
    order = R['order']; replay(m, R, order[np.isin(order, sel_)], X0, Y0)
    return (np.clip(lin2srgb(np.clip(m['alb'], 0, 1)), 0, 1) * 255).astype(np.uint8)[..., ::-1]
near = np.nonzero((R['group'] == 0) & (mm[:,0] > X0/10) & (mm[:,0] < X1/10) & (mm[:,1] > Y0/10) & (mm[:,1] < Y1/10))[0]
a = layer(near); b = layer(ids)
cv2.imwrite(W + '/b10_tips.png', np.vstack([a, b]))
for k in ids: print(mm[k].round(1), R['kind'][k], R['region'][k])
