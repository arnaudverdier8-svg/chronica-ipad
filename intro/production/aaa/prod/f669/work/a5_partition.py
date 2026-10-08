import os, sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/lib')
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src')
import numpy as np, cv2
from chron.config import MAPS
from chron.maps import MapSet
from chron.record import replay
from chron.color import lin2srgb
import silhouette as SIL
W = os.path.dirname(os.path.abspath(__file__))
G = MapSet(MAPS + '/p1_oath_ground')
R = G.stitches()
names = json.load(open(G.path + '/groups.json'))['groups']
off = R['off']
mids = np.array([R['P'][off[k]:off[k + 1]].mean(0) for k in range(len(R['typ']))], np.float32) / 10.0
x0, y0, x1, y1 = 2250, 1300, 3700, 2850
win = (mids[:, 0] * 10 > x0) & (mids[:, 0] * 10 < x1) & (mids[:, 1] * 10 > y0) & (mids[:, 1] * 10 < y1)
cand = np.nonzero(win)[0]
ins = np.zeros(len(mids), bool)
ins[cand] = SIL.inside(mids[cand])
king = R['group'] == names.index('king')
gnd = R['group'] == 0
keep = np.nonzero(king & ~ins)[0]
debris = np.nonzero(gnd & ins)[0]
print('king keep', len(keep), 'king unpick', int((king & ins).sum()), 'debris', len(debris))
def layer(sel, bg):
    H, Wd = y1 - y0, x1 - x0
    m = dict(h=np.full((H, Wd), -10.0, np.float32), alb=np.ones((H, Wd, 3), np.float32) * bg, T=np.zeros((H, Wd, 2), np.float32),
             mat=np.zeros((H, Wd), np.uint8), cov=np.zeros((H, Wd), np.float32), sid=np.zeros((H, Wd), np.int32),
             sfr=np.zeros((H, Wd), np.float32), base=np.zeros((H, Wd), np.float32), stamp=np.zeros((H, Wd), np.int32), PX=10.0)
    o = R['order']; replay(m, R, o[np.isin(o, sel)], x0, y0)
    return (np.clip(lin2srgb(np.clip(m['alb'], 0, 1)), 0, 1) * 255).astype(np.uint8)[..., ::-1].copy()
p = ((SIL.sil_mm() * 10 - [x0, y0])).astype(np.int32)
a = layer(keep, 0.9); cv2.polylines(a, [p], True, (0, 0, 255), 3)
b = layer(debris, 0.9); cv2.polylines(b, [p], True, (0, 0, 255), 3)
cv2.imwrite(os.path.join(W, 'a5_keep_debris.jpg'), cv2.resize(np.hstack([a, b]), None, fx=0.4, fy=0.4, interpolation=cv2.INTER_AREA))
