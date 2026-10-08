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
P = MapSet(MAPS + '/p1_oath'); G = MapSet(MAPS + '/p1_oath_ground'); R = G.stitches()
names = json.load(open(G.path + '/groups.json'))['groups']
mids, bb = entry_geometry(R); PX = 10.0
f = lambda x: (np.clip(lin2srgb(np.clip(x, 0, 1)), 0, 1) * 255).astype(np.uint8)[..., ::-1]
tiles = []
for nm in ['goblet_2', 'goblet_3']:
    gi = names.index(nm); sel = np.nonzero(R['group'] == gi)[0]
    x0 = int(bb[sel,0].min()) - 80; y0 = int(bb[sel,1].min()) - 80; x1 = int(bb[sel,2].max()) + 80; y1 = int(bb[sel,3].max()) + 80
    a = f(P.read_px(x0, y0, x1, y1, 0, keys=['alb'])['alb']).copy()
    Hh, Ww = y1 - y0, x1 - x0
    m = dict(h=np.full((Hh, Ww), -10.0, np.float32), alb=np.zeros((Hh, Ww, 3), np.float32), T=np.zeros((Hh, Ww, 2), np.float32),
             mat=np.zeros((Hh, Ww), np.uint8), cov=np.zeros((Hh, Ww), np.float32), sid=np.zeros((Hh, Ww), np.int32),
             sfr=np.zeros((Hh, Ww), np.float32), base=np.zeros((Hh, Ww), np.float32), stamp=np.zeros((Hh, Ww), np.int32), PX=PX)
    order = R['order']; replay(m, R, order[np.isin(order, sel)], x0, y0)
    cov = (m['h'] > -5).astype(np.uint8)
    cnts, _ = cv2.findContours(cv2.dilate(cov, np.ones((5,5),np.uint8)), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(a, cnts, -1, (0, 0, 255), 2)
    for xm in range(int(x0/10)//5*5, int(x1/10)+5, 5):
        X = int(xm*10 - x0)
        if 0 <= X < Ww: cv2.line(a, (X, 0), (X, Hh), (255, 255, 0), 1); cv2.putText(a, str(xm), (X+2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255,255,0), 1)
    for ym in range(int(y0/10)//5*5, int(y1/10)+5, 5):
        Y = int(ym*10 - y0)
        if 0 <= Y < Hh: cv2.line(a, (0, Y), (Ww, Y), (255, 255, 0), 1); cv2.putText(a, str(ym), (2, Y-2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255,255,0), 1)
    tiles.append(cv2.resize(a, None, fx=1.0, fy=1.0, interpolation=cv2.INTER_AREA))
h = max(t.shape[0] for t in tiles)
tt = [cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 4, cv2.BORDER_CONSTANT) for t in tiles]
cv2.imwrite(W + '/c3_gob23.png', np.hstack(tt))
