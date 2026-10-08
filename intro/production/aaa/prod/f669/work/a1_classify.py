"""Analysis: colour classes of king-group entries and ground entries around the king polygon."""
import os, sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/lib')
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np, cv2
from chron.config import MAPS
from chron.maps import MapSet
from chron.record import replay, blank_like
from chron.color import lin2oklab, lin2srgb
W = os.path.dirname(os.path.abspath(__file__))
G = MapSet(MAPS + '/p1_oath_ground')
R = G.stitches()
names = json.load(open(G.path + '/groups.json'))['groups']
gk = names.index('king')
x0, y0, x1, y1 = 2250, 1300, 3700, 2850      # level-0 px window around the king
g = G.read_px(x0, y0, x1, y1, 0, keys=['h', 'alb', 'T', 'mat', 'cov', 'sid', 'gpoly', 'grp'])
print({k: (v.shape if hasattr(v, 'shape') else v) for k, v in g.items()})
# entry mid points
off = R['off']; P = R['P']
mids = np.array([P[off[k]:off[k + 1]].mean(0) for k in range(len(R['typ']))], np.float32)
col = R['fpar'][:, 3:6]
lab = lin2oklab(np.clip(col, 0, None)[None])[0]
Lc = lab[:, 0]; C = np.hypot(lab[:, 1], lab[:, 2]); hue = np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360
inwin = (mids[:, 0] > x0) & (mids[:, 0] < x1) & (mids[:, 1] > y0) & (mids[:, 1] < y1)
king = np.nonzero(R['group'] == gk)[0]
gnd = np.nonzero((R['group'] == 0) & inwin)[0]
print('king', len(king), 'ground in win', len(gnd))
np.savez(os.path.join(W, 'a1_entries.npz'), mids=mids, L=Lc, C=C, hue=hue)
# hue/L histogram of king entries
for nm, sel in (('king', king), ('gnd', gnd)):
    hh = np.histogram(hue[sel][C[sel] > 0.03], bins=24, range=(0, 360))[0]
    print(nm, 'hue hist (C>.03):', hh.tolist())
    print(nm, 'L quantiles', np.quantile(Lc[sel], [0.05, 0.25, 0.5, 0.75, 0.95]).round(3), 'C q', np.quantile(C[sel], [0.05, 0.5, 0.95]).round(3))
# render king-only layer on white, ground-only on grey for visual
def layer(sel, bg):
    m = dict(h=np.full((y1 - y0, x1 - x0), -10.0, np.float32), alb=np.ones((y1 - y0, x1 - x0, 3), np.float32) * bg,
             T=np.zeros((y1 - y0, x1 - x0, 2), np.float32), mat=np.zeros((y1 - y0, x1 - x0), np.uint8),
             cov=np.zeros((y1 - y0, x1 - x0), np.float32), sid=np.zeros((y1 - y0, x1 - x0), np.int32),
             sfr=np.zeros((y1 - y0, x1 - x0), np.float32), base=np.zeros((y1 - y0, x1 - x0), np.float32),
             stamp=np.zeros((y1 - y0, x1 - x0), np.int32), PX=10.0)
    order = R['order']
    sel_o = order[np.isin(order, sel)]
    replay(m, R, sel_o, x0, y0)
    return m
mk = layer(king, 0.9)
img = (np.clip(lin2srgb(np.clip(mk['alb'], 0, 1)), 0, 1) * 255).astype(np.uint8)
cv2.imwrite(os.path.join(W, 'a1_king_layer.jpg'), cv2.resize(img[..., ::-1], None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
gimg = (np.clip(lin2srgb(np.clip(g['alb'], 0, 1)), 0, 1) * 255).astype(np.uint8)
gp = g['gpoly'].astype(np.float32)
cnt, _ = cv2.findContours((np.abs(gp - 2) < 0.5).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
gi = gimg[..., ::-1].copy()
cv2.drawContours(gi, cnt, -1, (0, 0, 255), 3)
cv2.imwrite(os.path.join(W, 'a1_ground.jpg'), cv2.resize(gi, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
np.save(os.path.join(W, 'a1_kingpoly.npy'), (np.abs(gp - 2) < 0.5))
np.save(os.path.join(W, 'a1_sid.npy'), g['sid'])
