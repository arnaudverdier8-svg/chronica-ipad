import os, sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/lib')
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src')
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np, cv2
from chron.config import MAPS
from chron.maps import MapSet
from chron.record import replay
from chron.color import lin2srgb, lin2oklab
from kingvoid import entry_geometry
import silhouette as SIL
W = os.path.dirname(os.path.abspath(__file__))
G = MapSet(MAPS + '/p1_oath_ground'); R = G.stitches()
mids, bb = entry_geometry(R); PX = 10.0; mm = mids / PX
col = np.clip(R['fpar'][:, 3:6], 0, None); lab = lin2oklab(col[None])[0]
L = lab[:, 0]; C = np.hypot(lab[:, 1], lab[:, 2]); hue = np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360
reg = (R['group'] == 0) & (mm[:, 0] > 235) & (mm[:, 0] < 362) & (mm[:, 1] > 130) & (mm[:, 1] < 215)
idx = np.nonzero(reg)[0]
d = SIL.signed_dist_mm(mm[idx])
blue = (hue[idx] > 200) & (hue[idx] < 310) & (C[idx] < 0.09) & (L[idx] > 0.25)
print('region ground entries', len(idx), 'bluegrey', blue.sum())
sel = idx[blue]
print('signed dist quantiles', np.quantile(SIL.signed_dist_mm(mm[sel]), [0, .25, .5, .75, 1]).round(1))
for k in sel[:5]: print(mm[k].round(1), L[k].round(2), C[k].round(3), hue[k].round(0), R['kind'][k], R['region'][k])
X0, Y0, X1, Y1 = 2350, 1300, 3600, 2150
Hh, Ww = Y1-Y0, X1-X0
m = dict(h=np.full((Hh, Ww), -10.0, np.float32), alb=np.ones((Hh, Ww, 3), np.float32) * 0.5, T=np.zeros((Hh, Ww, 2), np.float32),
         mat=np.zeros((Hh, Ww), np.uint8), cov=np.zeros((Hh, Ww), np.float32), sid=np.zeros((Hh, Ww), np.int32),
         sfr=np.zeros((Hh, Ww), np.float32), base=np.zeros((Hh, Ww), np.float32), stamp=np.zeros((Hh, Ww), np.int32), PX=PX)
order = R['order']; replay(m, R, order[np.isin(order, sel)], X0, Y0)
im = (np.clip(lin2srgb(np.clip(m['alb'], 0, 1)), 0, 1) * 255).astype(np.uint8)[..., ::-1].copy()
cv2.polylines(im, [(SIL.sil_mm() * PX - np.array([X0, Y0])).astype(np.int32)], True, (0, 0, 255), 2)
cv2.imwrite(W + '/b11_panel.png', cv2.resize(im, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
