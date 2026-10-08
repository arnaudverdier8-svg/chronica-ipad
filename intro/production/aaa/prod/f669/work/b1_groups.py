import os, sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/lib')
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src')
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np, cv2
from chron.config import MAPS
from chron.maps import MapSet
from chron.record import replay, blank_like
from chron.color import lin2srgb
W = os.path.dirname(os.path.abspath(__file__))
G = MapSet(MAPS + '/p1_oath_ground'); R = G.stitches()
names = json.load(open(G.path + '/groups.json'))['groups']
print(names)
PX=10.0
def layer(sel, x0, y0, x1, y1, bg=0.5):
    H, Wd = y1-y0, x1-x0
    m = dict(h=np.full((H, Wd), -10.0, np.float32), alb=np.ones((H, Wd, 3), np.float32) * bg,
             T=np.zeros((H, Wd, 2), np.float32), mat=np.zeros((H, Wd), np.uint8), cov=np.zeros((H, Wd), np.float32),
             sid=np.zeros((H, Wd), np.int32), sfr=np.zeros((H, Wd), np.float32), base=np.zeros((H, Wd), np.float32),
             stamp=np.zeros((H, Wd), np.int32), PX=PX)
    order = R['order']; sel_o = order[np.isin(order, sel)]
    replay(m, R, sel_o, x0, y0)
    return (np.clip(lin2srgb(np.clip(m['alb'], 0, 1)), 0, 1) * 255).astype(np.uint8)
for nm in ['candle_0','candle_3','goblet_0','goblet_1','goblet_2','goblet_3']:
    gi = names.index(nm)
    sel = np.nonzero(R['group'] == gi)[0]
    P = R['P'][np.concatenate([np.arange(R['off'][k], R['off'][k+1]) for k in sel])]
    x0, y0 = int(P[:,0].min())-60, int(P[:,1].min())-60; x1, y1 = int(P[:,0].max())+60, int(P[:,1].max())+60
    g = G.read_px(x0, y0, x1, y1, 0, keys=['alb'])
    gi_img = (np.clip(lin2srgb(np.clip(g['alb'], 0, 1)), 0, 1) * 255).astype(np.uint8)
    lay = layer(sel, x0, y0, x1, y1)
    out = np.hstack([gi_img, lay])
    cv2.imwrite(f'{W}/b1_{nm}.png', cv2.resize(out[..., ::-1], None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
    print(nm, len(sel), (x0, y0, x1, y1))
