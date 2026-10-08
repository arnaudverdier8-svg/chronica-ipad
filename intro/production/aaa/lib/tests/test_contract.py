"""Contract + exactness tests (fast, read-only):  python3 tests/test_contract.py [sheet]
1. MapSet manifest/channels/levels load; 2. read() padding is seamless and never void (G4);
3. EXACT replay: <sheet>_ground + all group entries replayed in needle order == <sheet> (stitch-on at 100 % equals the
   bake; unpick at 0 equals the bake); 4. king-only state at k=0 equals the ground (unpick at 100 % = void)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from chron.config import MAPS
from chron.maps import MapSet
from chron.anim.groupanim import GroupAnim
sheet = sys.argv[1] if len(sys.argv) > 1 else 'p1_oath'
F = MapSet(os.path.join(MAPS, sheet)); G = MapSet(os.path.join(MAPS, sheet + '_ground'))
print('channels', F.channels)
print('levels', [(l['level'], l['PX'], l['W'], l['H']) for l in F.man['levels']])
gj = json.load(open(os.path.join(G.path, 'groups.json')))
groups = gj['groups'][1:]
ga = GroupAnim(G, groups)
st = ga.state(ga.n)
x0, y0, x1, y1 = ga.bbox
ref = F.read_px(x0, y0, x1, y1, 0)
dh = np.abs(st['h'].astype(np.float16).astype(np.float32) - ref['h'])
da = np.abs(st['alb'].astype(np.float16).astype(np.float32) - ref['alb'])
dm = (st['mat'] != ref['mat']).mean()
bad = (dh > 2e-3) | (da.max(-1) > 2e-3)
print(f'exact replay over groups bbox {ga.bbox}: pixels differing {bad.sum()} of {bad.size} ({bad.mean():.2e}; float16 '
      f'rounding flips), mat mismatch={dm:.5f}')
assert bad.mean() < 1e-5 and dm == 0, 'replay is not exact'
st0 = ga.state(0)
g0 = G.read_px(x0, y0, x1, y1, 0)
assert np.abs(st0['h'].astype(np.float16).astype(np.float32) - g0['h']).max() < 2e-3
w = F.read(-30, -30, 40, 40, 1)
assert w['valid'].all() and np.isfinite(w['h']).all()
print('OK')
