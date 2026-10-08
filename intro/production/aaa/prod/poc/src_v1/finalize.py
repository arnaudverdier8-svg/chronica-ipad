"""Replay the whole RECORD in wavefront commit order -> final stitched state A (the 2D board at f1719), build the
ghost state B (icons lifted: bare protected linen, underdrawing, needle holes), a global fibre set, and the
R25 linear radiance textures of A and B for Eevee (emission ground). Also the low-pass height for the mesh.
python3 finalize.py [mapsdir]"""
import sys, os, json, time, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from replay import load, schedule, apply, kind_of, copy_maps
from r25render import LIGHT, kmap_for
from exr import write_exr
sys.path.insert(0, RND)
import numpy as np, cv2
cv2.setNumThreads(3)
from emb.shade import relight, normals, ambient_occlusion, light_vec
from emb.fibres import halo, make_fibres, render_fibres
from emb.core import hex_lin

D = sys.argv[1] if len(sys.argv) > 1 else f'{POC}/maps'
T0 = time.time()
def log(*a): print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)
L = json.load(open(f'{POC}/data/layout.json')); PIECES = json.load(open(f'{POC}/data/pieces.json'))
R, canvas, masks, hexmap = load(D)
rec = R['record']
st, en = schedule(R, L, PIECES)
order = np.lexsort((np.arange(len(rec)), en))
np.savez_compressed(f'{D}/schedule.npz', st=st, en=en, order=order)
log('events', len(rec), 'first/last end', en.min(), en.max())
ICONK = ('icon', 'icon_out')

# ---- A: everything
m = copy_maps(canvas)
for i in order:
    apply(m, rec[i], 1.0, hexmap, masks)
log('A replayed')
np.savez_compressed(f'{D}/stateA.npz', **{k: m[k] for k in ('h', 'alb', 'T', 'mat', 'cov', 'sid')})

# ---- global fibre set (on A), board mm coordinates
fib = make_fibres(m, density=0.9, seed=6, len_mm=(0.4, 2.0), max_fibres=1500000)
rng = np.random.default_rng(6)
fib['A'] = (fib['A'] * rng.uniform(0.95, 1.05, (len(fib['A']), 1))).astype(np.float32)
Lr = fib['A'] @ np.array([0.2126, 0.7152, 0.0722], np.float32)
fib['alpha'] = (fib['alpha'] * np.clip((Lr - 0.03) / 0.12, 0, 1) * 0.85).astype(np.float32)
# a fibre belongs to the strand it grows from: roots on the edge just outside a strand take the neighbouring strand id
sidd = cv2.dilate(m['sid'].astype(np.float32), np.ones((5, 5), np.uint8)).astype(np.int64)
r_ = fib['root']
sid0 = m['sid'][r_[:, 1], r_[:, 0]].astype(np.int64)
fib['sid'] = np.where(sid0 > 0, sid0, sidd[r_[:, 1], r_[:, 0]]).astype(np.int32)
okf = fib['sid'] > 0
fib = {k: v[okf] for k, v in fib.items()}
del sidd
np.savez_compressed(f'{D}/fibres.npz', **fib)
log('fibres', len(fib['P']))


def shade_full(mm, fib, keep=None):
    mm = dict(mm); mm['PX'] = PX
    mm['N'] = normals(mm['h'], PX, blur=0.5); mm['ao'] = ambient_occlusion(mm['h'], PX)
    km = kmap_for(mm['h'].shape, 0, 0)
    lt = {k: v for k, v in LIGHT.items() if k != 'soft'}
    col, vis = relight(mm, kmap=km, cam=None, soft=LIGHT['soft'], **lt)
    col = halo(col, mm, 0.3, 0.33)
    f = fib if keep is None else {k: v[keep] for k, v in fib.items()}
    Lv = light_vec(LIGHT['az'], LIGHT['el'])
    key = np.array(LIGHT['key'], np.float32) * LIGHT['key_i'] * float(np.median(kmap_for((H, W), 0, 0)))
    fill = np.array(LIGHT['fill'], np.float32) * LIGHT['fill_i']
    def project(P):
        Q = np.empty(P.shape[:2] + (2,), np.float32); Q[..., 0] = P[..., 0] * PX; Q[..., 1] = P[..., 1] * PX
        return Q, -P[..., 2]
    render_fibres(col, f, Lv, key, fill, vis, project, width=0.9)
    return col


radA = shade_full(m, fib)
write_exr(f'{D}/radA.exr', radA)
log('radA', float(radA.mean()))
del radA

# ---- B: icons lifted -> protected linen + underdrawing (from the canvas) + needle holes along the footprints
B = copy_maps(m)
reg = (masks['icon_dil'] > 0)
for k in ('h', 'alb', 'T', 'mat', 'cov', 'sid'):
    B[k][reg] = canvas[k][reg]
# the slip sat on the coupon's padding felt: lifting it leaves the felt (the coupon's colour, darker, matte),
# with the iron-gall underdrawing of the icon and the needle holes of its couching
FIELDC = {'forest': '#3F7E42', 'plains': '#CFAF64', 'farm': '#D6BE74', 'hills': '#BF6B37', 'mountain': '#CFC6B4', 'quarry': '#C19C64',
          'sea': '#1F4E90', 'lake': '#24548A'}
hid = hexmap['hid']
fcol = np.array([hex_lin(FIELDC[h['t']]) for h in L['hexes']], np.float32) * 0.58
lin_ref = np.median(canvas['alb'][::7, ::7].reshape(-1, 3), 0)
ys_, xs_ = np.nonzero(reg)
felt = fcol[hid[ys_, xs_]] * np.clip(canvas['alb'][ys_, xs_] / lin_ref, 0.35, 1.25)
B['alb'][ys_, xs_] = felt
B['h'][ys_, xs_] = canvas['base'][ys_, xs_] * 0.82 + 0.05 if 'base' in canvas else B['h'][ys_, xs_]
B['mat'][ys_, xs_] = 1; B['cov'][ys_, xs_] = 0.0
# needle holes: along the stitched regions' edges inside each icon (where strands entered the cloth)
rng = np.random.default_rng(17)
sidA = m['sid']
edges = np.zeros(sidA.shape, bool)
edges[:, 1:] |= sidA[:, 1:] != sidA[:, :-1]; edges[1:, :] |= sidA[1:, :] != sidA[:-1, :]
edges &= (masks['icon'] > 0) | (cv2.dilate(masks['icon'], np.ones((3, 3), np.uint8)) > 0)
ys, xs = np.nonzero(edges)
pick = rng.permutation(len(xs))[: int(len(xs) / (1.1 * PX))]
hole = np.zeros(sidA.shape, np.float32)
for i in pick:
    cv2.circle(hole, (int(xs[i] + rng.normal(0, 0.5)), int(ys[i] + rng.normal(0, 0.5))), int(max(1, rng.uniform(0.14, 0.26) * PX)), 1.0, -1, cv2.LINE_AA)
hole = cv2.GaussianBlur(hole, (0, 0), 0.5)
rim = np.clip(cv2.GaussianBlur(hole, (0, 0), 0.25 * PX) * 1.6 - hole, 0, 1)
B['h'][:] = B['h'] - 0.22 * hole + 0.06 * rim
B['alb'][:] = B['alb'] * (1 - 0.62 * hole[..., None])
# a few cut thread ends left in the holes (short wool stubs in the icon's colours)
np.savez_compressed(f'{D}/stateB.npz', **{k: B[k] for k in ('h', 'alb', 'T', 'mat', 'cov', 'sid')})
keepB = B['sid'][fib['root'][:, 1], fib['root'][:, 0]] == fib['sid']
radB = shade_full(B, fib, keepB)
write_exr(f'{D}/radB.exr', radB)
log('radB', float(radB.mean()))
del radB
# ---- mesh height (mm): low-pass of B (the flat pictures are not geometry), plus the padding domes
hl = cv2.GaussianBlur(B['h'], (0, 0), 1.2 * PX)
np.save(f'{D}/hlow.npy', hl.astype(np.float16))
log('done')
