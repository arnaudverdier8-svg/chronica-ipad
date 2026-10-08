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
names = json.load(open(G.path + '/groups.json'))['groups']
mids, bb = entry_geometry(R); PX = 10.0
res = {}
f = lambda x: (np.clip(lin2srgb(np.clip(x, 0, 1)), 0, 1) * 255).astype(np.uint8)
tiles = []
for nm in ['goblet_0','goblet_1','goblet_2','goblet_3','candle_0','candle_1','candle_2','candle_3']:
    gi = names.index(nm); sel = np.nonzero(R['group'] == gi)[0]
    x0 = int(bb[sel,0].min()) - 60; y0 = int(bb[sel,1].min()) - 60; x1 = int(bb[sel,2].max()) + 60; y1 = int(bb[sel,3].max()) + 60
    ly = G.read_px(x0, y0, x1, y1, 0, keys=['ud', 'gpoly', 'alb'])
    ud = ly['ud'].astype(np.float32); gp = ly['gpoly']
    inpoly = (gp == gi).astype(np.uint8)
    m = (ud > 0.25).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
    # fill holes
    ff = m.copy(); msk = np.zeros((m.shape[0]+2, m.shape[1]+2), np.uint8); cv2.floodFill(ff, msk, (0,0), 2)
    filled = ((ff != 2) | (m > 0)).astype(np.uint8)
    # restrict to polygon (ud outside polygon is other groups' ud)
    subj = cv2.dilate(filled * inpoly, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)))
    ins = np.array([subj[int(np.clip(mids[k,1]-y0,0,subj.shape[0]-1)), int(np.clip(mids[k,0]-x0,0,subj.shape[1]-1))] > 0 for k in sel])
    res[nm] = dict(sel=sel, ins=ins)
    print(nm, 'subject', int(ins.sum()), 'restore', int((~ins).sum()))
    # visual
    base = f(ly['alb'])[..., ::-1].copy()
    ov = base.copy()
    ov[subj > 0] = (0.6 * ov[subj > 0] + 0.4 * np.array([0, 255, 0])).astype(np.uint8)
    for k, i in zip(sel, ins):
        c = (0, 160, 0) if i else (0, 0, 255)
        cv2.circle(ov, (int(mids[k,0]-x0), int(mids[k,1]-y0)), 4, c, -1)
    tiles.append(cv2.resize(ov, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
h = max(t.shape[0] for t in tiles)
pad = lambda t: cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 4, cv2.BORDER_CONSTANT)
cv2.imwrite(W + '/b6_subject_a.png', np.hstack([pad(t) for t in tiles[:4]]))
cv2.imwrite(W + '/b6_subject_b.png', np.hstack([pad(t) for t in tiles[4:]]))
