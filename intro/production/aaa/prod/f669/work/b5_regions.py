import os, sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/lib')
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np
from chron.config import MAPS
from chron.maps import MapSet
G = MapSet(MAPS + '/p1_oath_ground'); R = G.stitches()
names = json.load(open(G.path + '/groups.json'))['groups']
reg = R['region']; grp = R['group']
for gi, nm in enumerate(names):
    if gi == 0: continue
    sel = np.nonzero(grp == gi)[0]
    rs, cnt = np.unique(reg[sel], return_counts=True)
    out = []
    for r, c in zip(rs, cnt):
        ng = int(((grp == 0) & (reg == r)).sum())
        out.append((int(r), int(c), ng))
    shared = [o for o in out if o[2] > 0 and o[0] != 65535]
    print(nm, 'regions', len(rs), 'entries', len(sel), 'regions shared with ground:', [(o[0], o[1], o[2]) for o in shared][:20])
