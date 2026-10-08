"""2D frames f1664-1719 (R25-S): the board stitches itself in as a wavefront from Grandbois, on twos.
Each unique state is evaluated at t = f+1 (so the last hex closes on f1719), relit in texture space on the
zero-tilt view window, fibres from the global set (only where their strand already exists), warped to
2560x1440 (or --scale for previews) and graded. Writes r25/f%04d.png (+ the last state's linear frame).
python3 r25_frames.py [--scale 0.5] [--only 1690,1718]"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from replay import load, apply, copy_maps
from r25render import LIGHT, kmap_for, topdown_view, grade, to_screen
import numpy as np, cv2
cv2.setNumThreads(3)
sys.path.insert(0, RND)
from emb.shade import relight, normals, ambient_occlusion, light_vec
from emb.fibres import halo, render_fibres

args = sys.argv[1:]
SCALE = float(args[args.index('--scale') + 1]) if '--scale' in args else 1.0
ONLY = [int(v) for v in args[args.index('--only') + 1].split(',')] if '--only' in args else None
OUTD = f'{POC}/r25' if SCALE == 1.0 else f'{POC}/preview/r25_{SCALE:g}'
os.makedirs(OUTD, exist_ok=True)
D = f'{POC}/maps'
T0 = time.time()
def log(*a): print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)

R, canvas, masks, hexmap = load(D)
rec = R['record']
sch = np.load(f'{D}/schedule.npz'); st, en, order = sch['st'], sch['en'], sch['order']
fz = np.load(f'{D}/fibres.npz'); FIB = {k: fz[k] for k in fz.files}
view, s = topdown_view()
mg = 90
reg = (int(view[0]) - mg, int(view[1]) - mg, int(view[0] + view[2]) + mg, int(view[1] + view[3]) + mg)
x0, y0, x1, y1 = reg
fin = (FIB['root'][:, 0] >= x0) & (FIB['root'][:, 0] < x1) & (FIB['root'][:, 1] >= y0) & (FIB['root'][:, 1] < y1)
FIB = {k: v[fin] for k, v in FIB.items()}
km = kmap_for((y1 - y0, x1 - x0), x0, y0)
KMED = float(np.median(kmap_for((H, W), 0, 0)))
Wo, Ho = int(2560 * SCALE), int(1440 * SCALE)
# bolder iron-gall underdrawing on the bare linen AHEAD of the wave: it lives only where the final state is stitched
# (so it is always covered by f1719 and the last 2D state stays identical to the Eevee radiance texture)
_ca = canvas['alb'][y0:y1, x0:x1]
_med = cv2.medianBlur(np.clip(_ca * 255, 0, 255).astype(np.uint8), 7).astype(np.float32) / 255 + 1e-3
_ratio = np.clip((_ca / _med).mean(-1), 0, 1)
_A = np.load(f'{D}/stateA.npz')
_covered = _A['mat'][y0:y1, x0:x1] != 0
del _A
INK_BOOST = np.where(_covered & (_ratio < 0.985), np.clip(_ratio, 0.2, 1) ** 1.8, 1.0).astype(np.float32)
m = copy_maps(canvas); del canvas
committed = np.zeros(len(rec), bool)
pos = 0
states = list(range(F_STITCH0, F_LASTHEX + 1, 2))      # 1664, 1666, ..., 1718
for f in states:
    t = f + 1.0
    # commit everything finished by t (in global commit order)
    while pos < len(order) and en[order[pos]] <= t:
        apply(m, rec[order[pos]], 1.0, hexmap, masks); committed[order[pos]] = True; pos += 1
    if ONLY is not None and f not in ONLY and f != states[-1]:
        continue
    w = {k: (np.ascontiguousarray(v[y0:y1, x0:x1]) if isinstance(v, np.ndarray) and v.ndim >= 2 else v) for k, v in m.items()}
    # partial (growing) strands on a window copy
    part = np.nonzero((st < t) & (en > t) & ~committed)[0]
    if len(part):
        # draw partials into a padded temporary full-size view only over the window: shift coordinates
        tmp = {k: (w[k] if k in w else m[k]) for k in m}
        tmp['base'] = np.ascontiguousarray(m['base'][y0:y1, x0:x1])
        for i in part:
            e = rec[i]
            frac = float((t - st[i]) / max(1e-6, en[i] - st[i]))
            if isinstance(e[0], str):
                if e[0] == 'SLIP':
                    e2 = (e[0], e[1], e[2] - y0, e[3] - x0) + tuple(e[4:])
                    if 0 <= e2[2] and 0 <= e2[3] and e2[2] + e[6].shape[0] <= y1 - y0 and e2[3] + e[6].shape[1] <= x1 - x0:
                        apply(tmp, e2, frac)
                continue
            e2 = list(e); e2[15] = (e[15][0] - x0, e[15][1] - y0)
            apply(tmp, tuple(e2), frac)
        w = tmp
    w['PX'] = PX
    bare = (w['mat'] == 0) & (INK_BOOST < 1)
    if bare.any():
        w['alb'] = w['alb'].copy(); w['alb'][bare] *= INK_BOOST[bare][:, None]
    w['N'] = normals(w['h'], PX, blur=0.5); w['ao'] = ambient_occlusion(w['h'], PX)
    lt = {k: v for k, v in LIGHT.items() if k != 'soft'}
    col, vis = relight(w, kmap=km, cam=None, soft=LIGHT['soft'], **lt)
    col = halo(col, w, 0.3, 0.33)
    # fibres whose strand already exists (same stitch id as in the final state)
    rx, ry = FIB['root'][:, 0] - x0, FIB['root'][:, 1] - y0
    sw = w['sid'][ry, rx]
    sidd = cv2.dilate(w['sid'].astype(np.float32), np.ones((5, 5), np.uint8))[ry, rx].astype(np.int64)
    keep = np.where(sw > 0, sw, sidd) == FIB['sid']
    fsel = {k: v[keep] for k, v in FIB.items()}
    fsel['P'] = fsel['P'] - np.array([x0 / PX, y0 / PX, 0], np.float32)
    fsel['root'] = fsel['root'] - np.array([x0, y0], np.int32)
    Lv = light_vec(LIGHT['az'], LIGHT['el'])
    key = np.array(LIGHT['key'], np.float32) * LIGHT['key_i'] * KMED
    fill = np.array(LIGHT['fill'], np.float32) * LIGHT['fill_i']
    def project(P):
        Q = np.empty(P.shape[:2] + (2,), np.float32); Q[..., 0] = P[..., 0] * PX; Q[..., 1] = P[..., 1] * PX
        return Q, -P[..., 2]
    render_fibres(col, fsel, Lv, key, fill, vis, project, width=0.9)
    img = to_screen(col, reg, view, s, (Wo, Ho))
    out = grade(img, grain=0.0)          # grain is added per frame in comp.py
    for ff in (f, f + 1):
        cv2.imwrite(f'{OUTD}/f{ff:04d}.png', cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
    if f == states[-1]:
        np.save(f'{OUTD}/last_linear.npy', img.astype(np.float16))
    log(f, 'committed', pos, 'partial', len(part), 'fibres', int(keep.sum()))
log('done')
