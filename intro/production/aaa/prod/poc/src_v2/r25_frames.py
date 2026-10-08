"""2D frames f1664-1719 (R25-S): the board stitches itself in along the needle-path schedule (replay.py), on twos.
Each unique state is evaluated at t = f + 1.2 (first stitches already down on the f1664 bass frame; the last tie-down lands at f1718.94 so the last
state IS the final board), relit in texture space under the two candles (left lit on f1664, right on f1707, ignition + flicker from lightmodel),
fibres from the global set (only where their strand already exists), warped to 2560x1440 (or --scale) and graded.
python3 r25_frames.py [--scale 0.5] [--only 1690,1718]"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from replay import load, apply, copy_maps, et
from r25render import topdown_view, grade, to_screen, shade_window
import lightmodel as lm
import numpy as np, cv2
cv2.setNumThreads(3)
sys.path.insert(0, RND)

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
sch = np.load(f'{D}/schedule.npz'); st, en, rev, order = sch['st'], sch['en'], sch['rev'], sch['order']
fz = np.load(f'{D}/fibres.npz'); FIB = {k: fz[k] for k in fz.files}
view, s = topdown_view()
mg = 90
reg = (int(view[0]) - mg, int(view[1]) - mg, int(view[0] + view[2]) + mg, int(view[1] + view[3]) + mg)
x0, y0, x1, y1 = reg
fin = (FIB['root'][:, 0] >= x0) & (FIB['root'][:, 0] < x1) & (FIB['root'][:, 1] >= y0) & (FIB['root'][:, 1] < y1)
FIB = {k: v[fin] for k, v in FIB.items()}
FIB['P'] = FIB['P'] - np.array([x0 / PX, y0 / PX, 0], np.float32)
FIB['root'] = FIB['root'] - np.array([x0, y0], np.int32)
Wo, Ho = int(2560 * SCALE), int(1440 * SCALE)
m = copy_maps(canvas); del canvas
committed = np.zeros(len(rec), bool)
pos = 0
states = list(range(F_STITCH0, F_LASTHEX + 1, 2))      # 1664, 1666, ..., 1718
for f in states:
    t = f + 1.2
    while pos < len(order) and en[order[pos]] <= t:
        apply(m, rec[order[pos]], 1.0, bool(rev[order[pos]])); committed[order[pos]] = True; pos += 1
    if ONLY is not None and f not in ONLY and f != states[-1]:
        continue
    w = {k: (np.ascontiguousarray(v[y0:y1, x0:x1]) if isinstance(v, np.ndarray) and v.ndim >= 2 else v) for k, v in m.items()}
    part = np.nonzero((st < t) & (en > t) & ~committed & (st < 1e5))[0]
    for i in part:
        e = rec[i]
        if et(e) == 'SQ': continue
        frac = float((t - st[i]) / max(1e-6, en[i] - st[i]))
        e2 = list(e); e2[15] = (e[15][0] - x0, e[15][1] - y0)
        apply(w, tuple(e2), frac, bool(rev[i]))
    w['PX'] = PX
    gL = lm.gain('L', f + 0.5, with_swell=False); gR = lm.gain('R', f + 0.5, with_swell=False)
    # window maps are already cut: shade at window origin but with pool maps from the true board position
    from emb.shade import normals, ambient_occlusion, light_vec
    import shade2
    from emb.fibres import halo
    w['N'] = normals(w['h'], PX, blur=0.5); w['ao'] = ambient_occlusion(w['h'], PX)
    kL, kR, kF = lm.kmaps(w['h'].shape, x0, y0, 1, None)
    kF = lm.fill_map(kL, kR, gL, gR)
    col, vis = shade2.relight2(w, kL, kR, kF, gL, gR, N=w['N'], ao=w['ao'])
    col = halo(col, w, 0.3, 0.33)
    rx, ry = FIB['root'][:, 0], FIB['root'][:, 1]
    sw = w['sid'][ry, rx]
    sidd = cv2.dilate(w['sid'].astype(np.float32), np.ones((5, 5), np.uint8))[ry, rx].astype(np.int64)
    keep = np.where(sw > 0, sw, sidd) == FIB['sid']
    fsel = {k: v[keep] for k, v in FIB.items()}
    def project(P):
        Q = np.empty(P.shape[:2] + (2,), np.float32); Q[..., 0] = P[..., 0] * PX; Q[..., 1] = P[..., 1] * PX
        return Q, -P[..., 2]
    shade2.render_fibres2(col, fsel, vis[0], vis[1], kL, kR, kF, gL, gR, project)
    img = to_screen(col, (0, 0, x1 - x0, y1 - y0), (view[0] - x0, view[1] - y0, view[2], view[3]), s, (Wo, Ho))
    out = grade(img, grain=0.0)
    for ff in (f, f + 1):
        cv2.imwrite(f'{OUTD}/f{ff:04d}.png', cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
    if f == states[-1]:
        np.save(f'{OUTD}/last_linear.npy', img.astype(np.float16))
    log(f, 'committed', pos, 'partial', len(part), 'fibres', int(keep.sum()), 'gL %.2f gR %.2f' % (gL, gR))
log('done')
