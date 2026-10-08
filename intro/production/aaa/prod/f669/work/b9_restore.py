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
W = os.path.dirname(os.path.abspath(__file__))
G = MapSet(MAPS + '/p1_oath_ground'); R = G.stitches()
names = json.load(open(G.path + '/groups.json'))['groups']
mids, bb = entry_geometry(R); PX = 10.0; mm = mids / PX
col = np.clip(R['fpar'][:, 3:6], 0, None); lab = lin2oklab(col[None])[0]
L = lab[:, 0]; C = np.hypot(lab[:, 1], lab[:, 2]); hue = np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360
def layer(sel, x0, y0, x1, y1, bg=0.5):
    Hh, Ww = y1 - y0, x1 - x0
    m = dict(h=np.full((Hh, Ww), -10.0, np.float32), alb=np.ones((Hh, Ww, 3), np.float32) * bg, T=np.zeros((Hh, Ww, 2), np.float32),
             mat=np.zeros((Hh, Ww), np.uint8), cov=np.zeros((Hh, Ww), np.float32), sid=np.zeros((Hh, Ww), np.int32),
             sfr=np.zeros((Hh, Ww), np.float32), base=np.zeros((Hh, Ww), np.float32), stamp=np.zeros((Hh, Ww), np.int32), PX=PX)
    order = R['order']; replay(m, R, order[np.isin(order, sel)], x0, y0)
    return (np.clip(lin2srgb(np.clip(m['alb'], 0, 1)), 0, 1) * 255).astype(np.uint8)
tiles = []
for nm, xc, wb, ylo in (('candle_1', 497.5, 0.0, 256.8), ('candle_2', 522.5, 0.0, 255.2)):
    gi = names.index(nm); sel = np.nonzero(R['group'] == gi)[0]
    x0 = int(bb[sel,0].min()) - 40; y0 = int(bb[sel,1].min()) - 40; x1 = int(bb[sel,2].max()) + 40; y1 = int(bb[sel,3].max()) + 40
    isr = (L[sel] < 0.62) & (mm[sel, 1] < ylo)
    # dark outline of the flame / body on the axis stays subject
    rest = sel[isr]; subj = sel[~isr]
    a = layer(rest, x0, y0, x1, y1)[..., ::-1]; b = layer(subj, x0, y0, x1, y1)[..., ::-1]
    tiles.append(np.hstack([a, b]))
    print(nm, len(rest), len(subj))
h = max(t.shape[0] for t in tiles)
tt = [cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 6, cv2.BORDER_CONSTANT) for t in tiles]
cv2.imwrite(W + '/b9_restore.png', cv2.resize(np.hstack(tt), None, fx=0.55, fy=0.55, interpolation=cv2.INTER_AREA))
