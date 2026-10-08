import os, sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/lib')
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src')
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np, cv2
from chron.config import MAPS
from chron.maps import MapSet
from chron.record import replay
from chron.color import lin2srgb, lin2oklab
import silhouette as SIL
from kingvoid import entry_geometry
W = os.path.dirname(os.path.abspath(__file__))
G = MapSet(MAPS + '/p1_oath_ground'); R = G.stitches()
names = json.load(open(G.path + '/groups.json'))['groups']
gk = names.index('king')
mids, bb = entry_geometry(R); PX = 10.0
mm = mids / PX
ins = np.zeros(len(mids), bool)
near = (mids[:, 0] > 2200) & (mids[:, 0] < 3800) & (mids[:, 1] > 1250) & (mids[:, 1] < 2900)
idx = np.nonzero(near)[0]; ins[idx] = SIL.inside(mm[idx])
king = R['group'] == gk
keep = np.nonzero(king & ~ins)[0]
print('keep', len(keep))
col = np.clip(R['fpar'][:, 3:6], 0, None)
lab = lin2oklab(col[None])[0]
L = lab[:, 0]; C = np.hypot(lab[:, 1], lab[:, 2]); hue = np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360
# summarize keep entries by hue bins and L
for nm, sel in (('keep', keep),):
    print('L q', np.quantile(L[sel], [.1, .5, .9]).round(2))
    for h0 in range(0, 360, 30):
        s = sel[(hue[sel] >= h0) & (hue[sel] < h0 + 30) & (C[sel] > 0.025)]
        if len(s): print(h0, len(s), 'L', L[s].mean().round(2), 'C', C[s].mean().round(3))
    print('low-C', (C[sel] <= 0.025).sum())
# render keep layer with entry colour on gray, mark classes
x0, y0, x1, y1 = 2250, 1000, 3700, 2850
H, Wd = y1 - y0, x1 - x0
def layer(sel):
    m = dict(h=np.full((H, Wd), -10.0, np.float32), alb=np.ones((H, Wd, 3), np.float32) * 0.5, T=np.zeros((H, Wd, 2), np.float32),
             mat=np.zeros((H, Wd), np.uint8), cov=np.zeros((H, Wd), np.float32), sid=np.zeros((H, Wd), np.int32),
             sfr=np.zeros((H, Wd), np.float32), base=np.zeros((H, Wd), np.float32), stamp=np.zeros((H, Wd), np.int32), PX=PX)
    order = R['order']; replay(m, R, order[np.isin(order, sel)], x0, y0)
    return (np.clip(lin2srgb(np.clip(m['alb'], 0, 1)), 0, 1) * 255).astype(np.uint8)
img = layer(keep)
sil = (SIL.sil_mm() * PX - np.array([x0, y0])).astype(np.int32)
im2 = img[..., ::-1].copy(); cv2.polylines(im2, [sil], True, (0, 0, 255), 3)
cv2.imwrite(W + '/b3_keep.png', cv2.resize(im2, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
np.savez(W + '/b3_cls.npz', keep=keep, L=L, C=C, hue=hue)
