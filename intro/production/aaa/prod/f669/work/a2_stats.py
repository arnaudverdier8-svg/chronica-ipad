import os, sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/lib')
import numpy as np
from chron.config import MAPS
from chron.maps import MapSet
W = os.path.dirname(os.path.abspath(__file__))
G = MapSet(MAPS + '/p1_oath_ground')
R = G.stitches()
d = np.load(os.path.join(W, 'a1_entries.npz'))
mids, L, C, hue = d['mids'] / 10.0, d['L'], d['C'], d['hue']
names = json.load(open(G.path + '/groups.json'))['groups']
king = R['group'] == names.index('king')
gnd = R['group'] == 0
def box(x0, y0, x1, y1, sel):
    m = sel & (mids[:, 0] > x0) & (mids[:, 0] < x1) & (mids[:, 1] > y0) & (mids[:, 1] < y1)
    return np.nonzero(m)[0]
def show(nm, ids):
    print(nm, len(ids))
    if len(ids) == 0: return
    for q in (L, C, hue):
        print('   ', np.quantile(q[ids], [0.05, 0.25, 0.5, 0.75, 0.95]).round(3))
    print('    kinds', np.bincount(R['kind'][ids], minlength=12).tolist())
# head corners (backrest) in sheet mm: polygon top at y ~140.8; head x 270-318
show('king headL', box(268, 141, 278, 175, king))
show('king headR', box(312, 141, 326, 175, king))
show('king face', box(285, 150, 305, 165, king))
show('king botL', box(236, 225, 255, 258, king))
show('king botR', box(340, 215, 358, 258, king))
show('king robe', box(275, 200, 290, 240, king))
show('gnd near L shoulder', box(240, 170, 262, 200, gnd))
show('gnd near R shoulder', box(330, 175, 352, 195, gnd))
show('gnd L edge', box(232, 195, 242, 255, gnd))
