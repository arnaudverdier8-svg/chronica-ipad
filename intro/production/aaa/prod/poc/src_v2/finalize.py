"""Replay the whole RECORD in needle-path commit order -> final stitched state A (the 2D board at f1719), the lifted-footprint state B
(every piece's elevation unpicked: protected unfaded linen, ordered needle holes, snipped thread ends, faint underdrawing -- or, for the
small appliqued trees, the satin they sat on with the same holes) and the healed state C (the coupon's satin closed over the footprint).
Then a global fibre set and the R25 linear radiance textures of A, B, C (two candles at gain 1, base pools) for Eevee,
the low-pass mesh height, the footprint sweep map (heal order), the metal (gold border) mask + tangent map and the stitched figure cards.
python3 finalize.py [mapsdir]"""
import sys, os, json, time, pickle, math, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from replay import load, schedule, apply, copy_maps, et, etag, vnoise
from r25render import shade_window
from exr import write_exr
sys.path.insert(0, RND)
import numpy as np, cv2
cv2.setNumThreads(3)
from emb.fibres import halo, make_fibres
from emb.strands import raster_stitch
from emb.core import hex_lin, lin2oklab, oklab2lin, srgb2lin, lin2srgb
import lightmodel as lm, shade2
from emb.shade import normals, ambient_occlusion

D = sys.argv[1] if len(sys.argv) > 1 else f'{POC}/maps'
T0 = time.time()
def log(*a): print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)
L = json.load(open(f'{POC}/data/layout.json')); PIECES = json.load(open(f'{POC}/data/pieces.json'))
R, canvas, masks, hexmap = load(D)
rec = R['record']; hs = R['heal_start']
st, en, rev, info = schedule(R, L, PIECES)
order = np.lexsort((np.arange(len(rec)), en))
order = order[en[order] < 1e5]
np.savez_compressed(f'{D}/schedule.npz', st=st, en=en, rev=rev, order=order, t0_h=info['t0_h'], dur_h=info['dur_h'])
log('events', len(rec), 'scheduled', len(order), 'first/last end', float(en[order].min()), float(en[order].max()))
ICONK = ('icon', 'icon_out')
PIECE_BY_ID = {p['id']: i for i, p in enumerate(PIECES)}

# ---- A: everything stitched
m = copy_maps(canvas)
for i in order:
    apply(m, rec[i], 1.0, False)
log('A replayed')
np.savez_compressed(f'{D}/stateA.npz', **{k: m[k] for k in ('h', 'alb', 'T', 'mat', 'cov', 'sid')})

# ---- B pre: A without any piece elevation (icon, icon_out): bare linen where the big pieces sat, satin under the trees
Bm = copy_maps(canvas)
for i in order:
    if etag(rec[i])[0] in ICONK: continue
    apply(Bm, rec[i], 1.0, False)
log('B replayed')
# ---- C: the satin closes over the footprints (heal events, on the dome cushion)
Cm = copy_maps(Bm)
Cm['base'] = masks['base_heal'].astype(np.float32)
for i in range(hs, len(rec)):
    apply(Cm, rec[i], 1.0, False)
log('C replayed', len(rec) - hs, 'heal events')

foot_lin = (masks['icon_dil'] > 0) & (Bm['mat'] == 0)
# ---- decorate B: ordered needle holes along the old outline, snipped thread ends, faint underdrawing
hid = hexmap['hid']
rng = np.random.default_rng(17)
hole = np.zeros(m['h'].shape, np.float32)
ink_faint = np.zeros(m['h'].shape, np.float32)
PI = R['piece_icons']
tufts = []
for p in PIECES:
    if p.get('skip') or p['id'] not in PI: continue
    ic = PI[p['id']]
    sub = np.zeros((ic['h'] + 4, ic['w'] + 4), np.uint8)
    # outline of the stitched elevation = where A differs from B inside the icon rect (the strands that were lifted)
    sl = (slice(ic['v'] - 2, ic['v'] + ic['h'] + 2), slice(ic['u'] - 2, ic['u'] + ic['w'] + 2))
    if sl[0].start < 0 or sl[1].start < 0: continue
    diff = (m['sid'][sl] != Bm['sid'][sl]).astype(np.uint8)
    diff = cv2.morphologyEx(diff, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    cs_, _ = cv2.findContours(diff, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for c in cs_:
        if len(c) < 10: continue
        pts = c[:, 0, :].astype(np.float32) + np.array([sl[1].start, sl[0].start], np.float32)
        seg = np.hypot(*np.diff(np.vstack([pts, pts[:1]]), axis=0).T); s = np.concatenate([[0], np.cumsum(seg)])
        pitch = (2.4 + 0.5 * rng.random()) * PX
        k = 0.0
        pos = rng.uniform(0, pitch)
        while pos < s[-1]:
            j = min(int(np.searchsorted(s, pos)), len(pts) - 1)
            hx, hy = pts[j]
            cv2.circle(hole, (int(round(hx)), int(round(hy))), max(1, int(rng.uniform(0.15, 0.24) * PX)), 1.0, -1, cv2.LINE_AA)
            if rng.random() < 0.34:
                tufts.append((hx, hy, p['id']))
            pos += pitch * (1 + rng.uniform(-0.12, 0.12))
        cv2.polylines(ink_faint, [np.round(pts).astype(np.int32).reshape(-1, 1, 2)], True, 1.0, 1, cv2.LINE_AA)
hole = cv2.GaussianBlur(hole, (0, 0), 0.5)
rim = np.clip(cv2.GaussianBlur(hole, (0, 0), 0.25 * PX) * 1.5 - hole, 0, 1)
B = copy_maps(Bm)
B['h'] = B['h'] - 0.20 * hole + 0.05 * rim
B['alb'] = B['alb'] * (1 - 0.50 * hole[..., None])
B['alb'][foot_lin] *= 0.88                     # protected linen under the lifted piece lies in the piece's own shade: toned down so it never glares
# faint underdrawing: the canvas carries it at full strength where the linen is bare; on satin add a thin iron-gall line
ink = hex_lin('#3E3025')
a_ink = (cv2.GaussianBlur(ink_faint, (0, 0), 0.25 * PX) * 0.30)[..., None]
B['alb'] = B['alb'] * (1 - a_ink) + ink * a_ink
# fade the full-strength underdrawing on the bare linen of the footprints to ~50 %
foot = (masks['icon_dil'] > 0)
ca = canvas['alb']
med = cv2.medianBlur(np.clip(ca[foot.nonzero()[0].min():foot.nonzero()[0].max() + 1, :, :] * 255, 0, 255).astype(np.uint8), 7).astype(np.float32) / 255 + 1e-3
y0f = foot.nonzero()[0].min()
ratio = np.clip((ca[y0f:y0f + med.shape[0]] / med).mean(-1), 0.2, 1.0)
inkw = np.where(ratio < 0.985, 1.0, 0.0).astype(np.float32)
fade = (foot[y0f:y0f + med.shape[0]] * inkw)[..., None] * 0.5
B['alb'][y0f:y0f + med.shape[0]] = np.where(fade > 0, B['alb'][y0f:y0f + med.shape[0]] * (1 + fade * (1 / np.clip(ratio, 0.2, 1)[..., None] - 1)), B['alb'][y0f:y0f + med.shape[0]])
del med, ratio, inkw, fade
# snipped thread ends lying on the cloth, in the colour of the strand that was cut (colour taken from A at the hole)
sidn = 900000
for (hx, hy, pid) in tufts:
    ix, iy = int(hx), int(hy)
    col = m['alb'][min(iy + 2, m['alb'].shape[0] - 1), ix]
    a = rng.uniform(0, 2 * math.pi); ln = rng.uniform(1.0, 2.6) * PX
    curv = rng.normal(0, 0.6)
    pts = []
    for t in np.linspace(0, 1, 5):
        a2 = a + curv * t
        pts.append((hx + math.cos(a2) * ln * t, hy + math.sin(a2) * ln * t))
    q = np.array(pts, np.float32)
    sidn += 1
    raster_stitch(B['h'], B['alb'], B['T'], B['mat'], B['cov'], B['sid'], B['base'], q, float(0.13 * PX), 0.22, 0.14, float(col[0]), float(col[1]), float(col[2]),
                  1, float(0.4 * PX), 0.5, float(0.2 * PX), sidn, int(sidn), 0.2, float(PX), 0.5, 0.4, 0.42)
log('B decorated: holes', int((hole > 0.5).sum() / 4), 'tufts', len(tufts))
np.savez_compressed(f'{D}/stateB.npz', **{k: B[k] for k in ('h', 'alb', 'T', 'mat', 'cov', 'sid')})
np.savez_compressed(f'{D}/stateC.npz', **{k: Cm[k] for k in ('h', 'alb', 'T', 'mat', 'cov', 'sid')})

# ---- global fibre set on A (a fibre belongs to the strand it grows from; absent where that strand is not stitched)
fib = make_fibres(m, density=0.9, seed=6, len_mm=(0.4, 2.0), max_fibres=1500000)
r_ = np.random.default_rng(6)
fib['A'] = (fib['A'] * r_.uniform(0.95, 1.05, (len(fib['A']), 1))).astype(np.float32)
Lr = fib['A'] @ np.array([0.2126, 0.7152, 0.0722], np.float32)
fib['alpha'] = (fib['alpha'] * np.clip((Lr - 0.03) / 0.12, 0, 1) * 0.85).astype(np.float32)
sidd = cv2.dilate(m['sid'].astype(np.float32), np.ones((5, 5), np.uint8)).astype(np.int64)
rt = fib['root']
sid0 = m['sid'][rt[:, 1], rt[:, 0]].astype(np.int64)
fib['sid'] = np.where(sid0 > 0, sid0, sidd[rt[:, 1], rt[:, 0]]).astype(np.int32)
okf = fib['sid'] > 0
fib = {k: v[okf] for k, v in fib.items()}
del sidd
np.savez_compressed(f'{D}/fibres.npz', **fib)
log('fibres', len(fib['P']))


def class_grade_apply(rad, mats):
    """per-terrain OKLab trim (data/class_grade.json: {terrain: [dL, chroma_scale, dh_deg]}) of the dyed fields, from the f1782 palette check"""
    path = f'{POC}/data/class_grade.json'
    if not os.path.exists(path): return rad
    cg = json.load(open(path))
    ter = np.array([h['t'] for h in L['hexes']])
    out = rad.copy()
    for t, (dL, cs, dh) in cg.items():
        ids = np.nonzero(ter == t)[0]
        if len(ids) == 0: continue
        sel = np.isin(hid, ids) & (mats != 3)
        sel = cv2.erode(sel.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        ys, xs = np.nonzero(sel)
        lab = lin2oklab(rad[ys, xs])
        C = np.hypot(lab[:, 1], lab[:, 2]) * cs; hh_ = np.arctan2(lab[:, 2], lab[:, 1]) + math.radians(dh)
        lab2 = np.stack([lab[:, 0] * (1 + dL), C * np.cos(hh_), C * np.sin(hh_)], 1)
        out[ys, xs] = oklab2lin(lab2)
    return out


def shade_full(mm, keep=None):
    reg = (0, 0, W, H)
    f = fib if keep is None else {k: v[keep] for k, v in fib.items()}
    col = shade_window(mm, reg, 1.0, 1.0, None, f)
    return class_grade_apply(col, mm['mat'])


radA = shade_full(m)
write_exr(f'{D}/radA.exr', radA)
log('radA', float(radA.mean()))
del radA
keepB = B['sid'][fib['root'][:, 1], fib['root'][:, 0]] == fib['sid']
radB = shade_full(B, keepB)
write_exr(f'{D}/radB.exr', radB)
log('radB', float(radB.mean()))
del radB
keepC = Cm['sid'][fib['root'][:, 1], fib['root'][:, 0]] == fib['sid']
radC = shade_full(Cm, keepC)
write_exr(f'{D}/radC.exr', radC)
log('radC', float(radC.mean()))
del radC
# ---- mesh height (mm): low-pass of the healed state (the pictures are not geometry; pockets would pop when the footprints heal)
hl = cv2.GaussianBlur(Cm['h'], (0, 0), 3.0 * PX)      # macro relief only: strand-scale relief is already lit in the R25 radiance
np.save(f'{D}/hlow.npy', hl.astype(np.float16))
# ---- metal (couched gold borders): mask + strand tangent for the travelling glint in Eevee
metal = (m['mat'] == 3).astype(np.float32)
Tm = m['T']
tg = np.dstack([metal, 0.5 + 0.5 * Tm[..., 0] * metal, 0.5 + 0.5 * Tm[..., 1] * metal])
write_exr(f'{D}/metal.exr', tg.astype(np.float32))
# ---- footprint sweep map (heal order): per piece, a needle sweep across the footprint perpendicular to the hex's satin rows, rows alternate
pid = masks['pidmap'].astype(np.int32)
sweep = np.zeros(pid.shape, np.float16)
hm_ = R.get('hexmeta', {})
for pi, p in enumerate(PIECES):
    ys, xs = np.nonzero(pid == pi + 1)
    if len(xs) < 20: continue
    hi = int(hid[int(ys.mean()), int(xs.mean())])
    th = math.radians(hm_.get(hi, dict(angle=90.0))['angle'])
    d = np.array([math.cos(th), math.sin(th)]); nn = np.array([-math.sin(th), math.cos(th)])
    P_ = np.stack([xs, ys], 1).astype(np.float64)
    s = P_ @ nn; a = P_ @ d
    sn = (s - s.min()) / max(s.max() - s.min(), 1.0)
    an = (a - a.min()) / max(a.max() - a.min(), 1.0)
    row = np.floor((s - s.min()) / (0.85 * PX)).astype(int)
    adir = np.where(row % 2 == 0, an, 1 - an)
    nz = 0.05 * vnoise(xs / PPU, ys / PPU, 5, 0.7)
    if (zlib.crc32(p['id'].encode()) & 1): sn = 1 - sn
    sweep[ys, xs] = np.clip(0.80 * sn + 0.20 * adir + nz, 0, 1).astype(np.float16)
np.save(f'{D}/sweep.npy', sweep)
log('sweep + metal done')
# ---- stitched figure cards for the 3D standing cards (albedo + height from the A state, alpha = stitched coverage)
E = f'{POC}/data/eevee'; os.makedirs(f'{E}/cards', exist_ok=True)
for p in PIECES:
    if p['kind'] != 'card' or p.get('skip') or p['id'] not in PI: continue
    ic = PI[p['id']]
    sl = (slice(ic['v'] - 2, ic['v'] + ic['h'] + 2), slice(ic['u'] - 2, ic['u'] + ic['w'] + 2))
    sid_a = m['sid'][sl]; sid_b = Bm['sid'][sl]
    cov = (sid_a != sid_b) & (m['mat'][sl] != 0)
    cov = cv2.morphologyEx(cov.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    al = cv2.GaussianBlur(cov.astype(np.float32), (0, 0), 0.6)
    alb = lin2srgb(np.clip(m['alb'][sl], 0, 1))
    hgt = m['h'][sl] * cov
    gx = cv2.Sobel(cv2.GaussianBlur(hgt, (0, 0), 0.6), cv2.CV_32F, 1, 0, ksize=3) / 8 * PX
    gy = cv2.Sobel(cv2.GaussianBlur(hgt, (0, 0), 0.6), cv2.CV_32F, 0, 1, ksize=3) / 8 * PX
    nz_ = 1.0 / np.sqrt(gx * gx + gy * gy + 1)
    nrm = np.dstack([0.5 - 0.5 * gx * nz_ * 1.4, 0.5 + 0.5 * gy * nz_ * 1.4, 0.5 + 0.5 * nz_])
    nm = f"{p['id']}"
    rgba = np.dstack([alb, al])
    cv2.imwrite(f'{E}/cards/{nm}_alb.png', cv2.cvtColor((rgba * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGBA2BGRA))
    cv2.imwrite(f'{E}/cards/{nm}_nrm.png', cv2.cvtColor((np.clip(nrm, 0, 1) * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR))
log('done')
