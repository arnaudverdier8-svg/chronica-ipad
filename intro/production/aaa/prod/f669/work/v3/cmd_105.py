import __main__ as _m; R = _m.R
import numpy as np, copy
import loose
from scipy.spatial import cKDTree
import silhouette as SIL
A = shot._ASSETS
lo = loose.LooseEnds(A['kv'])
order = sorted(lo.stubborn, key=lambda j: lo.blocks[j]['anchor'][0])
def paths():
    return [lo.curve(lo.blocks[i], 669)[0] for i in order]
def mind(p, q):
    t = cKDTree(q[:, :2]); d, _ = t.query(p[:, :2]); return float(d.min())
P = paths()
print('min dists:', {(a, b): round(mind(P[a], P[b]), 2) for a in range(4) for b in range(a + 1, 4)})
base = copy.deepcopy(loose.STUB_DESIGN)
rng = np.random.default_rng(3)
best = None
for trial in range(300):
    for k in range(4):
        loose.STUB_DESIGN[k] = dict(base[k])
        if trial:
            loose.STUB_DESIGN[k]['heading'] = base[k]['heading'] + rng.uniform(-0.8, 0.8)
            loose.STUB_DESIGN[k]['curl'] = base[k]['curl'] * (1 if rng.random() < 0.5 else -1)
    P = paths()
    dm = min(mind(P[a], P[b]) for a in range(4) for b in range(a + 1, 4))
    ins = min(SIL.signed_dist_mm(p[:, :2]).min() for p in P)
    sc = min(dm, 6.0) + 0.3 * min(ins, 6.0)
    if ins > 5 and (best is None or sc > best[0]):
        best = (sc, dm, ins, [(round(loose.STUB_DESIGN[k]['heading'], 2), round(loose.STUB_DESIGN[k]['curl'], 2)) for k in range(4)])
print('best', best)
