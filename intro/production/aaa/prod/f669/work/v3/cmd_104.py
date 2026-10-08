import __main__ as _m; R = _m.R
import numpy as np, itertools, copy
import loose
import silhouette as SIL
A = shot._ASSETS
lo = loose.LooseEnds(A['kv'])
order = sorted(lo.stubborn, key=lambda j: lo.blocks[j]['anchor'][0])
def paths():
    out = []
    for k, i in enumerate(order):
        P, _ = lo.curve(lo.blocks[i], 669)
        out.append(P)
    return out
def seg_inter(p, q):
    # count crossings between polylines (2D)
    n = 0
    a0, a1 = p[:-1, :2], p[1:, :2]; b0, b1 = q[:-1, :2], q[1:, :2]
    d1 = a1 - a0; d2 = b1 - b0
    for i in range(0, len(a0), 2):
        r = d1[i]; 
        den = r[0] * d2[:, 1] - r[1] * d2[:, 0]
        w = b0 - a0[i]
        t = (w[:, 0] * d2[:, 1] - w[:, 1] * d2[:, 0]) / np.where(np.abs(den) < 1e-9, 1e-9, den)
        u = (w[:, 0] * r[1] - w[:, 1] * r[0]) / np.where(np.abs(den) < 1e-9, 1e-9, den)
        n += int(((t >= 0) & (t <= 1) & (u >= 0) & (u <= 1)).sum())
    return n
base = copy.deepcopy(loose.STUB_DESIGN)
def score(P):
    cr = sum(seg_inter(P[a], P[b]) for a in range(4) for b in range(a + 1, 4))
    ins = min(SIL.signed_dist_mm(p[:, :2]).min() for p in P)
    return cr, ins
P = paths()
print('current: crossings/min inside', score(P))
for k, i in enumerate(order):
    b = lo.blocks[i]; print(k, 'anchor', b['anchor'].round(1), 'end', P[k][-1, :2].round(1), 'len', len(P[k]))
best = None
rng = np.random.default_rng(1)
for trial in range(200):
    for k in range(4):
        loose.STUB_DESIGN[k] = dict(base[k])
        loose.STUB_DESIGN[k]['heading'] = base[k]['heading'] + (rng.uniform(-0.9, 0.9) if trial else 0)
        loose.STUB_DESIGN[k]['curl'] = base[k]['curl'] * (1 if trial == 0 or rng.random() < 0.5 else -1)
    P = paths()
    cr, ins = score(P)
    sc = cr * 10 - min(ins, 4.0)
    if best is None or sc < best[0]:
        best = (sc, cr, ins, [(loose.STUB_DESIGN[k]['heading'], loose.STUB_DESIGN[k]['curl']) for k in range(4)])
print('best', best)
