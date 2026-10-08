"""R25 bake of the embroidered hex board (MapSet in board px, PX px/mm), recording every stitch for replay.
Outputs (maps/):  canvas.npz   linen + iron-gall underdrawing (pre-stitch state) + 'base' padding map
                  record.pkl   ordered stitch events (R25 put() tuples, couching squeezes, card slips) with tags
                  hexmap.npz   per-pixel hex index + edge distance (for swell / wavefront)
python3 board_bake.py [--test]   (--test: only hexes within 2 of Grandbois, for look-dev)"""
import sys, os, json, math, time, pickle, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
sys.path.insert(0, RND)
import numpy as np, cv2
cv2.setNumThreads(2)
from emb.core import hex_lin, smooth_noise, hash1, WOOL, SILK, METAL, INK, LINEN, lin2oklab, oklab2lin, srgb2lin
from emb.linen import make_linen
from emb import stitch as S
from emb.strands import squeeze_along as _squeeze
from pieces_plan import plan
from piece_palette import col as pcol, OUTLINE
from elev import load_elev
from figures import load_card

TEST = '--test' in sys.argv
OUT = f'{POC}/maps' + ('_test' if TEST else '')
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
def log(*a): print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)

L = json.load(open(f'{POC}/data/layout.json'))
HEX = L['hexes']
HK = {(h['q'], h['r']): i for i, h in enumerate(HEX)}
PIECES = plan(L)
json.dump(PIECES, open(f'{POC}/data/pieces.json', 'w'), indent=0)
if TEST:
    keep = lambda q, r: (abs(q) + abs(q + r) + abs(r)) // 2 <= 2
else:
    keep = lambda q, r: True

# ------------------------------------------------------------------ record hooks
S.RECORD = []
def _sq_rec(h, mat, stamp, sid, pts, rad, amount, keepmat):
    S.RECORD.append(('SQ', np.array(pts, np.float32) + np.array(CUR_OXY[0], np.float32), rad, amount, keepmat, sid, S.TAG[0]))
    return _squeeze(h, mat, stamp, sid, pts, rad, amount, keepmat)
S.squeeze_along = _sq_rec
CUR_OXY = [(0, 0)]

def window(m, x0, y0, x1, y1):
    x0, y0 = max(0, int(x0)), max(0, int(y0)); x1, y1 = min(W, int(x1)), min(H, int(y1))
    w = {k: (v[y0:y1, x0:x1] if isinstance(v, np.ndarray) and v.ndim >= 2 else v) for k, v in m.items()}
    w['_oxy'] = (x0, y0); CUR_OXY[0] = (x0, y0)
    return w, x0, y0, x1, y1

def P(x, z):
    """world (game units) -> board px (float)"""
    return np.stack([(np.asarray(x) - BX0) * PPU, (np.asarray(z) - BZ0) * PPU], -1).astype(np.float32)

def lin(h): return hex_lin(h)

def shades_around(hexcol, n=5, spread=0.055, seed=0, hue=4.0):
    base = lin2oklab(lin(hexcol)[None])[0]
    r = np.random.default_rng(seed)
    labs = []
    for k in range(n):
        t = (k - (n - 1) / 2) / max(1, (n - 1) / 2)
        L_ = base[0] * (1 + spread * t + r.uniform(-0.01, 0.01))
        a, b = base[1], base[2]
        ang = math.radians(r.uniform(-hue, hue)); cs = 1 + r.uniform(-0.07, 0.07)
        labs.append([L_, (a * math.cos(ang) - b * math.sin(ang)) * cs, (a * math.sin(ang) + b * math.cos(ang)) * cs])
    return S.ShadeSet(np.array(labs, np.float32), seed)

# ------------------------------------------------------------------ canvas: linen + light ageing
log('canvas', W, H)
m = make_linen(H, W, PX, seed=41)
S.ensure(m)
rng = np.random.default_rng(5)
fox = np.zeros((H, W), np.float32)
for _ in range(int(W * H / PX / PX / 1e4 * 7 * 0.12)):
    cx_, cy_ = rng.uniform(0, W), rng.uniform(0, H)
    for _k in range(rng.integers(1, 4)):
        cv2.circle(fox, (int(cx_ + rng.normal(0, 2 * PX)), int(cy_ + rng.normal(0, 2 * PX))), max(1, int(rng.uniform(0.25, 1.2) * PX)), float(rng.uniform(0.4, 1)), -1, cv2.LINE_AA)
fox = cv2.GaussianBlur(fox, (0, 0), 0.35 * PX)
fc = lin('#9C7046'); a_ = np.clip(fox * 0.25, 0, 0.3)[..., None]
m['alb'][:] = m['alb'] * (1 - a_) + m['alb'] * (fc / fc.max()) * a_
del fox, a_
# very soft creases (cloth on a table)
log('linen done')

# ------------------------------------------------------------------ hex geometry per pixel
gx = (BX0 + (np.arange(W, dtype=np.float32) + 0.5) / PPU)[None, :]
gz = (BZ0 + (np.arange(H, dtype=np.float32) + 0.5) / PPU)[:, None]
GX = np.broadcast_to(gx, (H, W)); GZ = np.broadcast_to(gz, (H, W))
qq, rr = axial_round(GX, GZ)
lut = -np.ones((80, 60), np.int32)
for (q, r), i in HK.items(): lut[q + 40, r + 30] = i
hid = lut[np.clip(qq + 40, 0, 79), np.clip(rr + 30, 0, 59)].astype(np.int32)
del qq, rr
hcx = np.array([h['x'] for h in HEX], np.float32); hcz = np.array([h['z'] for h in HEX], np.float32)
dedge = (edge_dist(GX, GZ, hcx[hid], hcz[hid]) * MMU).astype(np.float32)      # mm to nearest hex edge
ter = np.array([h['t'] for h in HEX])
is_water = np.isin(ter, ['sea', 'lake'])
water_px = is_water[hid]
np.savez_compressed(f'{OUT}/hexmap.npz', hid=hid.astype(np.int16), dedge=dedge.astype(np.float16))
log('hexmap')
wob = smooth_noise((H // 4 + 1, W // 4 + 1), 4 * PX / 4, 3, 2)
wob = cv2.resize(wob, (W, H), interpolation=cv2.INTER_LINEAR) * 0.45      # +-0.3 mm fill-edge wander

# ------------------------------------------------------------------ icon masks (pieces), rendered in board px
icon_mask = np.zeros((H, W), np.uint8)      # 1 where a piece's lying elevation is stitched (fields leave it bare)
ICON = {}                                     # id -> dict(x0,y0, lab (material idx image or None), names, alpha)
for p in PIECES:
    x0, z0, x1, z1 = p['icon']
    u0, v0 = (x0 - BX0) * PPU, (z0 - BZ0) * PPU
    wpx, hpx = int(round((x1 - x0) * PPU)), int(round((z1 - z0) * PPU))
    if wpx < 3 or hpx < 3 or u0 < 0 or v0 < 0 or u0 + wpx >= W or v0 + hpx >= H: p['skip'] = True; continue
    if p['kind'] in ('town', 'site', 'lumber', 'banner'):
        lab, names, J = load_elev(p['model'])
        # resample the 2x ID render to the icon rect (nearest keeps material ids exact)
        labr = cv2.resize(lab.astype(np.float32), (wpx, hpx), interpolation=cv2.INTER_NEAREST).astype(np.int32)
        alpha = (labr >= 0)
        ICON[p['id']] = dict(u=int(round(u0)), v=int(round(v0)), lab=labr, names=names, alpha=alpha)
    elif p['kind'] == 'tree':
        yy_, xx_ = np.mgrid[0:hpx, 0:wpx].astype(np.float32)
        tw = wpx / 2.0
        crown_h = hpx * 0.86
        half = (crown_h - yy_) / crown_h * 0 + yy_ / crown_h * tw   # half width grows downward
        crown = (np.abs(xx_ + 0.5 - tw) <= half + 0.3) & (yy_ <= crown_h)
        trunk = (np.abs(xx_ + 0.5 - tw) <= max(1.2, wpx * 0.09)) & (yy_ > crown_h - 1)
        lab = np.where(crown, 0, np.where(trunk, 1, -1)).astype(np.int32)
        ICON[p['id']] = dict(u=int(round(u0)), v=int(round(v0)), lab=lab, names=['pine', 'wood_dark'], alpha=lab >= 0)
    elif p['kind'] == 'card':
        c = load_card(p['unit'], p['realm'])
        al = cv2.resize(c['alpha'], (wpx, hpx), interpolation=cv2.INTER_AREA)
        ICON[p['id']] = dict(u=int(round(u0)), v=int(round(v0)), lab=None, alpha=al > 0.5, card=c, wpx=wpx, hpx=hpx)
    ic = ICON[p['id']]
    sl = (slice(ic['v'], ic['v'] + ic['alpha'].shape[0]), slice(ic['u'], ic['u'] + ic['alpha'].shape[1]))
    icon_mask[sl] |= ic['alpha'].astype(np.uint8)
icon_dil = cv2.dilate(icon_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(1.0 * PX) | 1, int(1.0 * PX) | 1)))
# per-piece footprint id map (piece index + 1), dilated ~1.2 mm, first come first served
pidmap = np.zeros((H, W), np.int16)
kd = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(2.4 * PX) | 1, int(2.4 * PX) | 1))
for pi, p in enumerate(PIECES):
    if p.get('skip'): continue
    ic = ICON[p['id']]; mg = int(2 * PX)
    hh_, ww_ = ic['alpha'].shape
    y0_, x0_ = max(0, ic['v'] - mg), max(0, ic['u'] - mg)
    y1_, x1_ = min(H, ic['v'] + hh_ + mg), min(W, ic['u'] + ww_ + mg)
    loc = np.zeros((y1_ - y0_, x1_ - x0_), np.uint8)
    loc[ic['v'] - y0_:ic['v'] - y0_ + hh_, ic['u'] - x0_:ic['u'] - x0_ + ww_] = ic['alpha']
    loc = cv2.dilate(loc, kd) > 0
    tgt = pidmap[y0_:y1_, x0_:x1_]
    tgt[loc & (tgt == 0)] = pi + 1
log('icons', len(ICON))

# ------------------------------------------------------------------ farm plots (crop rows) per farm hex
PLOTS = []
for h in HEX:
    if h['t'] != 'farm' or not keep(h['q'], h['r']): continue
    rnd = np.random.default_rng(1000 + 37 * h['q'] + h['r'])
    ang = rnd.choice([-28, -18, 18, 28]) + rnd.uniform(-4, 4)
    for k, (ox, oz) in enumerate([(-0.31, -0.29), (0.31, -0.29), (-0.31, 0.27), (0.31, 0.27)]):
        w_, h_ = 0.54 + rnd.uniform(-0.04, 0.03), 0.36 + rnd.uniform(-0.03, 0.03)
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        cx_, cz_ = h['x'] + ox + rnd.uniform(-0.03, 0.03), h['z'] + oz + rnd.uniform(-0.03, 0.03)
        pts = [(cx_ + ca * dx - sa * dz, cz_ + sa * dx + ca * dz) for dx, dz in [(-w_ / 2, -h_ / 2), (w_ / 2, -h_ / 2), (w_ / 2, h_ / 2), (-w_ / 2, h_ / 2)]]
        PLOTS.append(dict(hex=(h['q'], h['r']), pts=pts, ang=ang, k=k, green=k % 2))
plot_mask = np.zeros((H, W), np.uint8)
plot_lab = np.zeros((H, W), np.int32)
for i, pl in enumerate(PLOTS):
    poly = np.round(P(*np.array(pl['pts']).T)).astype(np.int32)
    tmp = np.zeros((H, W), np.uint8)
    cv2.fillPoly(tmp, [poly], 1)
    tmp &= (1 - icon_dil)
    plot_lab[tmp > 0] = i + 1
    plot_mask |= tmp

# ------------------------------------------------------------------ underdrawing (iron-gall) on the bare linen
ud = np.zeros((H, W), np.float32)
r_ud = np.random.default_rng(9)
def ink_line(pts_px, val=0.8, wmm=0.32, closed=False):
    q = S.resample(np.asarray(pts_px, np.float32), 0.6 * PX)
    if closed and len(q) > 2: q = np.vstack([q, q[:1]])
    q = q + (np.stack([S.smooth_noise1(len(q), 8, r_ud), S.smooth_noise1(len(q), 8, r_ud)], 1) * 0.12 * PX).astype(np.float32)
    cv2.polylines(ud, [np.round(q * 4).astype(np.int32)], False, float(val * r_ud.uniform(0.7, 1.0)), max(1, int(wmm * PX)), cv2.LINE_AA, shift=2)
for h in HEX:
    if h['t'] in ('sea', 'lake'): continue
    cs = hex_corners(h['q'], h['r'], 0.985)
    ink_line(P(*np.array(cs + cs[:1]).T), 0.75)
for p in PIECES:
    if p.get('skip'): continue
    ic = ICON[p['id']]
    cs_, _ = cv2.findContours(ic['alpha'].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for c in cs_:
        if len(c) < 6: continue
        ink_line(c[:, 0, :].astype(np.float32) + np.array([ic['u'], ic['v']], np.float32), 0.85, 0.28, closed=True)
for pl in PLOTS:
    ink_line(P(*np.array(pl['pts'] + pl['pts'][:1]).T), 0.7, 0.28)
riv = np.array(L['river'], np.float32)
ink_line(P(riv[:, 0], riv[:, 1]), 0.8, 0.35)
ud = cv2.GaussianBlur(ud, (0, 0), sigmaX=0.1 * PX, sigmaY=0.08 * PX)
ink = lin('#4A3A2E')
a_ = np.clip(ud * 0.62, 0, 0.66)[..., None]
m['alb'][:] = m['alb'] * (1 - a_) + ink * a_
del a_, ud
log('underdrawing')

# ------------------------------------------------------------------ padding ('base' height under stitches)
pad_h = {'forest': 1.35, 'plains': 1.15, 'farm': 1.0, 'hills': 1.45, 'mountain': 1.3, 'quarry': 1.1, 'sea': 0.0, 'lake': 0.0}
ph = np.array([pad_h[t] for t in ter], np.float32)[hid]
dome = np.sqrt(np.clip(1 - (1 - np.clip((dedge - 0.6) / 6.0, 0, 1)) ** 2, 0, 1))
base = (ph * dome).astype(np.float32)
base[water_px] = 0.22
# crop plots and icons sit on a slightly higher cushion
base = np.where(plot_mask > 0, base + 0.25, base)
base = np.where(icon_mask > 0, np.maximum(base, 0) + 0.3, base)
m['base'][:] = base
del ph, dome
np.savez_compressed(f'{OUT}/canvas.npz', **{k: m[k] for k in ('h', 'alb', 'T', 'mat', 'cov', 'sid')})
log('canvas saved')

# ------------------------------------------------------------------ helpers to stitch a masked region in a window
def fill_mask(mask_win, x0, y0, field_angle, shades, style='split', pitch=0.85, L=7.0, seed=0, matid=SILK, h0=0.06, hamp=0.42,
              r_fac=0.6, couch=None, maxlen=70, bend=4.0, hbias=0.0, colfn=None, tw=18):
    mw = {k: (v[y0:y0 + mask_win.shape[0], x0:x0 + mask_win.shape[1]] if isinstance(v, np.ndarray) and v.ndim >= 2 else v) for k, v in m.items()}
    mw['_oxy'] = (x0, y0); CUR_OXY[0] = (x0, y0)
    lab = np.where(mask_win, 1, 0).astype(np.int32)
    Hh, Ww = lab.shape
    n = smooth_noise((Hh, Ww), 25 * PX, seed + 3) if bend > 0 else 0
    c2, s2 = S.const_field((Hh, Ww), field_angle)
    if bend > 0:
        a2 = math.radians(field_angle) * 2 + np.radians(bend) * 2 * n
        c2, s2 = np.cos(a2).astype(np.float32), np.sin(a2).astype(np.float32)
    src = np.zeros((1, 1, 3), np.float32)
    # dye lots: a smooth luminance field over the region picks neighbouring shades in patches (bible 4.6)
    base_col = shades.lin[len(shades.lin) // 2]
    Ls = shades.lab[:, 0]; spread = float(Ls.max() - Ls.min()) / max(1e-3, float(Ls.mean()))
    nz = smooth_noise((Hh, Ww), 14 * PX, seed + 77, 2)
    srcimg = (base_col[None, None] * (1 + 0.9 * spread * np.clip(nz * 1.6, -1, 1))[..., None]).astype(np.float32)
    return S.fill_region(mw, lab, 1, (c2, s2), srcimg, shades, PX, style=style, pitch=pitch, L=L, seed=seed, matid=matid,
                         couch=couch, maxlen=maxlen, h0=h0, hamp=hamp, r_fac=r_fac, tw_deg=tw, cov=1.0, hbias=hbias, colfn=colfn)

def put_poly(pts_px, colr, r_mm, h0, hamp, matid=WOOL, **kw):
    CUR_OXY[0] = (0, 0)
    mm = dict(m); mm['_oxy'] = (0, 0)
    return S.put(mm, np.asarray(pts_px, np.float32), colr, r_mm, h0, hamp, matid, **kw)

def stem(pts_px, colr, width=1.2, seed=0, h0=0.55, hamp=0.45, L=3.5, matid=WOOL):
    mm = dict(m); mm['_oxy'] = (0, 0); CUR_OXY[0] = (0, 0)
    S.stem_path(mm, np.asarray(pts_px, np.float32), colr, PX, L=L, width=width, h0=h0, hamp=hamp, seed=seed, matid=matid)

def running(pts_px, colr, on=2.6, off=1.5, r_mm=0.34, seed=0, h0=0.5, hamp=0.32, phase=0.0):
    q = S.resample(np.asarray(pts_px, np.float32), 0.2 * PX)
    seg = np.hypot(*np.diff(q, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)]) / PX
    rr_ = np.random.default_rng(seed)
    pos = phase
    while pos < s[-1] - 0.5:
        a, b = pos, min(pos + on * (1 + rr_.uniform(-0.15, 0.15)), s[-1])
        ss = np.linspace(a, b, max(2, int((b - a) / 0.4) + 2))
        pp = np.stack([np.interp(ss, s, q[:, 0]), np.interp(ss, s, q[:, 1])], 1) + rr_.normal(0, 0.05 * PX, 2)
        put_poly(pp, colr * (1 + rr_.uniform(-0.05, 0.05)), r_mm, h0, hamp, WOOL, ply_mm=0.6, taper_mm=0.35, tw_deg=15, seed=seed, hbias=0.25)
        pos = b + off * (1 + rr_.uniform(-0.2, 0.2))

def edge_seg(q, r, i, inset=0.0):
    cs = hex_corners(q, r, 1.0 - inset)
    return cs[i], cs[(i + 1) % 6]

# neighbours of corner-edge i of a pointy hex: edge between corner i and i+1 faces direction angle 60*i
NB = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]   # edge i midpoint direction 60*i deg (x right, z down)

def tag(kind, key, order=0.0):
    S.TAG[0] = (kind, key, float(order))

# ------------------------------------------------------------------ 1. satin coupons (land hexes)
FIELD = {'forest': ('#3F7E42', 0.08), 'plains': ('#CFAF64', 0.06), 'farm': ('#D6BE74', 0.05), 'hills': ('#BF6B37', 0.07),
         'mountain': ('#CFC6B4', 0.04), 'quarry': ('#C19C64', 0.05)}
nf = 0
for i, h in enumerate(HEX):
    t = h['t']
    if t in ('sea', 'lake') or not keep(h['q'], h['r']): continue
    cx, cz = h['x'], h['z']
    u0, v0 = (cx - 1.0 - BX0) * PPU, (cz - 1.05 - BZ0) * PPU
    x0, y0 = int(max(0, u0)), int(max(0, v0)); x1, y1 = int(min(W, u0 + 2.0 * PPU)), int(min(H, v0 + 2.1 * PPU))
    sl = (slice(y0, y1), slice(x0, x1))
    mk = (hid[sl] == i) & (dedge[sl] > 0.75 + wob[sl]) & (icon_dil[sl] == 0) & (plot_mask[sl] == 0)
    if mk.sum() < 50: continue
    colh, spr = FIELD[t]
    sh = shades_around(colh, 5, spr, seed=100 + i, hue=3.5)
    ang = [30.0, 90.0, 150.0][(h['q'] - h['r']) % 3] + float(hash1(i, 5)) * 8 - 4
    tag('field', (h['q'], h['r']), 0.0)
    S.RECORD.append(('PAD', i, (hex_lin(colh) * 0.62).astype(np.float32), S.TAG[0]))
    fill_mask(mk, x0, y0, ang, sh, style='split', pitch=0.85, L=7.5, seed=200 + i, matid=SILK, h0=0.05, hamp=0.40, r_fac=0.6, bend=3.0)
    nf += 1
log('fields', nf, 'stitches', len(S.RECORD))

# ------------------------------------------------------------------ 2. crop plots (laid rows, couched) on farm hexes
for i, pl in enumerate(PLOTS):
    mkf = plot_lab == i + 1
    ys, xs = np.nonzero(mkf)
    if len(xs) < 30: continue
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    mk = mkf[y0:y1, x0:x1] & (dedge[y0:y1, x0:x1] > 0.6)
    gcol = ['#5A9140', '#73A04A'][pl['green']]
    sh = shades_around(gcol, 4, 0.10, seed=500 + i, hue=5)
    tag('plot', pl['hex'], 1.0 + 0.1 * pl['k'])
    fill_mask(mk, x0, y0, pl['ang'], sh, style='laid', pitch=0.8, seed=600 + i, matid=WOOL, h0=0.1, hamp=0.42, r_fac=0.62, bend=0,
              couch=dict(spacing=3.0, tie=3.5, r_mm=0.36, colmul=0.62, h0=0.45, hamp=0.3, matid=WOOL), hbias=0.1, maxlen=30)
    poly = P(*np.array(pl['pts'] + pl['pts'][:1]).T)
    tag('plot_out', pl['hex'], 1.5 + 0.1 * pl['k'])
    stem(poly, lin('#6E5032'), width=0.75, seed=700 + i, h0=0.45, hamp=0.35, L=2.6)
log('plots', len(PLOTS), 'stitches', len(S.RECORD))

# ------------------------------------------------------------------ 3. sea + lakes: laid denim, couched, wave marks
sea_mask = water_px & (dedge > -1)
land_near = cv2.dilate((~water_px).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
sea_fill = water_px & ~land_near
if TEST:
    ok = np.zeros((H, W), bool)
    for h in HEX:
        if keep(h['q'], h['r']) and h['t'] in ('sea', 'lake'): ok |= hid == HK[(h['q'], h['r'])]
    sea_fill &= ok
sea_sh = shades_around('#1F4E90', 6, 0.08, seed=31, hue=4)
lake_sh = shades_around('#24548A', 4, 0.06, seed=32, hue=4)
# tile the sea in strips of ~ 2 hex rows so the record has spatial locality (and per-hex tags)
for i, h in enumerate(HEX):
    if h['t'] not in ('sea', 'lake') or not keep(h['q'], h['r']): continue
    cx, cz = h['x'], h['z']
    u0, v0 = (cx - 1.0 - BX0) * PPU, (cz - 1.05 - BZ0) * PPU
    x0, y0 = int(max(0, u0)), int(max(0, v0)); x1, y1 = int(min(W, u0 + 2.0 * PPU)), int(min(H, v0 + 2.1 * PPU))
    sl = (slice(y0, y1), slice(x0, x1))
    mk = (hid[sl] == i) & sea_fill[sl] & (dedge[sl] > 0.3 + 0.5 * wob[sl])
    if mk.sum() < 50: continue
    tag('sea', (h['q'], h['r']), 0.0)
    S.RECORD.append(('PAD', i, (hex_lin('#1F4E90' if h['t'] == 'sea' else '#24548A') * 0.8).astype(np.float32), S.TAG[0]))
    fill_mask(mk, x0, y0, 0.0 + float(hash1(i, 9)) * 6 - 3, lake_sh if h['t'] == 'lake' else sea_sh, style='split', pitch=0.9, L=13.0,
              seed=900 + i, matid=WOOL, h0=0.05, hamp=0.36, r_fac=0.6, bend=5.0,
              couch=dict(spacing=8.5, tie=5.0, r_mm=0.33, colmul=0.93, h0=0.32, hamp=0.22, matid=WOOL), maxlen=40)
log('sea', 'stitches', len(S.RECORD))
# wave marks: cream stem-stitch '~' marks, 2-3 per sea hex
wave_c = lin('#DCD2BC')
for i, h in enumerate(HEX):
    if h['t'] != 'sea' or not keep(h['q'], h['r']): continue
    rnd = np.random.default_rng(3000 + i)
    for k in range(rnd.integers(2, 4)):
        for _try in range(10):
            ox, oz = rnd.uniform(-0.55, 0.55), rnd.uniform(-0.5, 0.5)
            if edge_dist(np.array(h['x'] + ox), np.array(h['z'] + oz), h['x'], h['z']) > 0.25: break
        wx = h['x'] + ox; wz = h['z'] + oz
        span = rnd.uniform(0.2, 0.28)
        tt = np.linspace(-0.5, 0.5, 24)
        xs_ = wx + tt * span; zs_ = wz + 0.022 * np.sin(tt * 2 * math.pi * 1.0 + 0.5)
        tag('wave', (h['q'], h['r']), 2.0 + 0.1 * k)
        stem(P(xs_, zs_), wave_c * (1 + rnd.uniform(-0.05, 0.05)), width=0.75, seed=3100 + 7 * i + k, h0=0.5, hamp=0.32, L=2.4)
# faint sea-grid dashes (pale blue running stitch) along sea/sea edges
grid_c = lin('#6E93B4')
done_e = set()
for i, h in enumerate(HEX):
    if h['t'] != 'sea' or not keep(h['q'], h['r']): continue
    for e in range(6):
        nq, nr = h['q'] + NB[e][0], h['r'] + NB[e][1]
        if (nq, nr) not in HK or HEX[HK[(nq, nr)]]['t'] != 'sea': continue
        key = tuple(sorted([(h['q'], h['r']), (nq, nr)]))
        if key in done_e: continue
        done_e.add(key)
        a, b = edge_seg(h['q'], h['r'], e)
        tag('grid', (h['q'], h['r']), 3.0)
        running(P(*np.array([a, b]).T), grid_c, on=2.0, off=2.2, r_mm=0.26, seed=4000 + len(done_e), h0=0.42, hamp=0.22)
log('waves+grid', 'stitches', len(S.RECORD))

# ------------------------------------------------------------------ 4. seams (cream running stitch) + coast outline + realm borders
seam_c = lin('#E2D3B6')
coast_c = lin('#3A2A1C')
gold = np.array([0.815, 0.515, 0.141], np.float32)
REALM_TIE = {'gold': lin('#4A2A14'), 'red': lin('#A3302B')}
done_e = set()
for i, h in enumerate(HEX):
    if not keep(h['q'], h['r']): continue
    for e in range(6):
        nq, nr = h['q'] + NB[e][0], h['r'] + NB[e][1]
        nb = HEX[HK[(nq, nr)]] if (nq, nr) in HK else None
        key = tuple(sorted([(h['q'], h['r']), (nq, nr)]))
        land_a = h['t'] not in ('sea', 'lake'); land_b = nb is not None and nb['t'] not in ('sea', 'lake')
        a, b = edge_seg(h['q'], h['r'], e)
        if land_a and land_b and key not in done_e:
            done_e.add(key)
            tag('seam', (h['q'], h['r']), 4.0)
            running(P(*np.array([a, b]).T), seam_c, on=2.6, off=1.6, r_mm=0.34, seed=5000 + len(done_e), h0=0.35, hamp=0.3)
        if land_a and not land_b:
            a2, b2 = edge_seg(h['q'], h['r'], e, 0.012)
            tag('coast', (h['q'], h['r']), 4.2)
            stem(P(*np.array([a2, b2]).T), coast_c, width=1.0, seed=5500 + i * 7 + e, h0=0.4, hamp=0.42, L=3.0)
        # realm border: couched gold pair on the inside of the realm
        ra = h.get('realm'); rb = nb.get('realm') if nb is not None else None
        if ra is not None and ra != rb:
            a3, b3 = edge_seg(h['q'], h['r'], e, 0.055)
            ex = np.array(b3) - np.array(a3); ex /= np.linalg.norm(ex)
            a3 = np.array(a3) - ex * 0.03; b3 = np.array(b3) + ex * 0.03
            pts = P(*np.array([a3, b3]).T)
            pts = S.resample(pts, 0.3 * PX)
            nrm = np.array([-(pts[-1, 1] - pts[0, 1]), pts[-1, 0] - pts[0, 0]], np.float32); nrm /= np.linalg.norm(nrm)
            rr_ = np.random.default_rng(6000 + i * 7 + e)
            tag('border', (h['q'], h['r']), 5.0)
            for k_, o in enumerate((-0.42, 0.42)):
                qpts = pts + nrm * o * PX + (np.stack([S.smooth_noise1(len(pts), 9, rr_), S.smooth_noise1(len(pts), 9, rr_)], 1) * 0.05 * PX)
                put_poly(qpts.astype(np.float32), gold * (1 + rr_.uniform(-0.06, 0.04)), 0.37, 0.6, 0.4, METAL, ply_mm=0.4, ply_deg=62,
                         taper_mm=0.3, tw_deg=55, seed=6100 + k_, cov=0.0, hbias=0.35)
            seg = np.hypot(*np.diff(pts, axis=0).T); s_ = np.concatenate([[0], np.cumsum(seg)]) / PX
            pos = rr_.uniform(0.5, 2.0)
            tc = REALM_TIE[ra]
            while pos < s_[-1] - 0.4:
                c = np.array([np.interp(pos, s_, pts[:, 0]), np.interp(pos, s_, pts[:, 1])], np.float32)
                qq_ = np.stack([c - nrm * 0.95 * PX, c + nrm * 0.95 * PX]).astype(np.float32)
                put_poly(qq_, tc * (1 + rr_.uniform(-0.1, 0.1)), 0.2, 1.0, 0.14, SILK, ply_mm=0.3, taper_mm=0.15, tw_deg=0, seed=6200, cov=0.0, hbias=0.5)
                pos += 2.6 * (1 + rr_.uniform(-0.15, 0.15))
log('seams/coast/borders', 'stitches', len(S.RECORD))

# ------------------------------------------------------------------ 5. river (couched cord), hill mounds, mountain peaks
if not TEST:
    rv = P(riv[:, 0], riv[:, 1])
    rv = S.smooth_poly(S.resample(rv, 0.8 * PX), 6)
    tag('river', (-3, -3), 4.5)
    for k_, o in enumerate((-0.9, 0.0, 0.9)):
        d_ = np.gradient(rv, axis=0); d_ /= (np.linalg.norm(d_, axis=1, keepdims=True) + 1e-6)
        nn = np.stack([-d_[:, 1], d_[:, 0]], 1)
        S.cord_path(dict(m, _oxy=(0, 0)), (rv + nn * o * PX).astype(np.float32), lin(['#4C93B8', '#5BA6C8', '#4C93B8'][k_]), PX,
                    width=1.1, h0=0.5, hamp=0.45, seed=7000 + k_, tie=3.0, tie_col=lin('#2E5C78'))
mound_c, mound_o = lin('#D9A441'), lin('#6B4A22')
peak_l, peak_d, peak_o = lin('#EEE7DA'), lin('#A49A8A'), lin('#3B3028')
for i, h in enumerate(HEX):
    if h['t'] not in ('hills', 'mountain') or not keep(h['q'], h['r']): continue
    rnd = np.random.default_rng(8000 + i)
    spots = [(-0.38, -0.25), (0.3, -0.32), (-0.05, 0.25), (0.42, 0.3), (-0.45, 0.32)]
    rnd.shuffle(spots)
    nk = 0
    for (ox, oz) in spots:
        x_, z_ = h['x'] + ox + rnd.uniform(-0.06, 0.06), h['z'] + oz + rnd.uniform(-0.06, 0.06)
        if h['t'] == 'hills':
            w_, h_ = rnd.uniform(0.3, 0.38), rnd.uniform(0.16, 0.2)
            tt = np.linspace(0, math.pi, 28)
            xs_ = x_ + np.cos(tt) * w_ / 2; zs_ = z_ - np.sin(tt) * h_
            poly = np.stack([xs_, zs_], 1)
        else:
            w_, h_ = rnd.uniform(0.3, 0.4), rnd.uniform(0.3, 0.38)
            poly = np.array([(x_ - w_ / 2, z_), (x_ - w_ * 0.08, z_ - h_), (x_ + w_ / 2, z_)])
        ppx = P(poly[:, 0], poly[:, 1])
        mk_full = np.zeros((H, W), np.uint8)
        x0, y0 = int(ppx[:, 0].min()) - 3, int(ppx[:, 1].min()) - 3; x1, y1 = int(ppx[:, 0].max()) + 4, int(ppx[:, 1].max()) + 4
        if x0 < 0 or y0 < 0 or x1 >= W or y1 >= H: continue
        if icon_dil[y0:y1, x0:x1].any() or plot_mask[y0:y1, x0:x1].any(): continue
        if np.any(edge_dist(poly[:, 0], poly[:, 1], h['x'], h['z']) < 0.08): continue
        mk = np.zeros((y1 - y0, x1 - x0), np.uint8)
        cv2.fillPoly(mk, [np.round(ppx - np.array([x0, y0])).astype(np.int32)], 1)
        mk = mk.astype(bool)
        m['base'][y0:y1, x0:x1] += (mk * 0.35).astype(np.float32)
        tag('relief', (h['q'], h['r']), 2.0 + 0.2 * nk)
        if h['t'] == 'hills':
            fill_mask(mk, x0, y0, 160.0, shades_around('#D9A441', 4, 0.07, seed=8100 + i), style='laid', pitch=0.7, seed=8200 + i * 5 + nk,
                      matid=SILK, h0=0.25, hamp=0.42, r_fac=0.62, bend=0, hbias=0.2)
            stem(ppx, mound_o, width=0.7, seed=8300 + i * 5 + nk, h0=0.6, hamp=0.35, L=2.4)
        else:
            mid_u = P(np.array([poly[1, 0]]), np.array([poly[1, 1]]))[0, 0] - x0
            left = mk.copy(); left[:, int(mid_u):] = False
            right = mk & ~left
            fill_mask(left, x0, y0, 62.0, shades_around('#EEE7DA', 3, 0.04, seed=8400 + i), style='laid', pitch=0.7, seed=8500 + i * 5 + nk,
                      matid=SILK, h0=0.3, hamp=0.4, bend=0, hbias=0.2)
            fill_mask(right, x0, y0, 118.0, shades_around('#A49A8A', 3, 0.05, seed=8600 + i), style='laid', pitch=0.7, seed=8700 + i * 5 + nk,
                      matid=WOOL, h0=0.3, hamp=0.4, bend=0, hbias=0.2)
            stem(ppx, peak_o, width=0.75, seed=8800 + i * 5 + nk, h0=0.6, hamp=0.35, L=2.4)
        nk += 1
        if nk >= (3 if h['t'] == 'hills' else 3): break
log('relief icons', 'stitches', len(S.RECORD))

# ------------------------------------------------------------------ 6. piece icons (elevations of the game models, trees, figure cards)
DIRS = {'stone': 0, 'plaster': 0, 'cloth': 0, 'wood': 90, 'wood_dark': 90, 'plank': 0, 'window': 90, 'metal': 0, 'gold': 90,
        'white': 90, 'blazon': 90, 'pine': None, 'dirt': 0, 'cloth_dark': 0}
icon_order = {}
for p in PIECES:
    if p.get('skip') or not keep(*p['hex']): continue
    ic = ICON[p['id']]
    u, v = ic['u'], ic['v']
    hh_, ww_ = ic['alpha'].shape
    if p['kind'] == 'card':
        # appliqued figure slip: the game's own embroidered card art, padded; pasted as one event
        c = ic['card']
        alb = cv2.resize(c['alb'], (ww_, hh_), interpolation=cv2.INTER_AREA)
        al = cv2.resize(c['alpha'], (ww_, hh_), interpolation=cv2.INTER_AREA)
        nm = cv2.resize(c['nrm'], (ww_, hh_), interpolation=cv2.INTER_AREA) * 2 - 1
        dt = cv2.distanceTransform((al > 0.5).astype(np.uint8), cv2.DIST_L2, 3) / PX
        hgt = 0.55 * np.sqrt(np.clip(1 - (1 - np.clip(dt / 1.0, 0, 1)) ** 2, 0, 1))
        # small relief from the card normal map (integrated gradients)
        nz = np.clip(nm[..., 2], 0.3, 1)
        gxp = cv2.GaussianBlur(-nm[..., 0] / nz, (0, 0), 1.0); gyp = cv2.GaussianBlur(nm[..., 1] / nz, (0, 0), 1.0)
        rel = np.cumsum(gxp, 1) / PX * 0.12 + np.cumsum(gyp, 0) / PX * 0.12
        rel -= cv2.GaussianBlur(rel, (0, 0), 4)
        hgt = (hgt + np.clip(rel, -0.15, 0.15) * (al > 0.5)).astype(np.float32)
        tag('icon', p['id'], 0.0)
        S.RECORD.append(('SLIP', p['id'], v, u, srgb2lin(np.clip(alb, 0, 1)).astype(np.float32), hgt, al.astype(np.float32), S._SID[0] + 1, S.TAG[0]))
        S._SID[0] += 1
        continue
    names = ic['names']; lab = ic['lab']
    realm = p.get('realm') or 'gold'
    k_ = 0
    for mi, nm_ in enumerate(names):
        mk_all = lab == mi
        if mk_all.sum() < 4: continue
        nc, cc = cv2.connectedComponents(mk_all.astype(np.uint8), connectivity=4)
        for c_ in range(1, nc):
            mk = cc == c_
            if mk.sum() < 3: continue
            colh = '#2E4A2C' if nm_ == 'pine' else pcol(nm_, realm)
            if nm_ == 'pine':
                ang = 90.0
            elif nm_.startswith('roof') or nm_ in ('slate', 'thatch'):
                ys_, xs_ = np.nonzero(mk)
                ang = 90.0 if (ys_.max() - ys_.min()) > 0.8 * (xs_.max() - xs_.min()) else 72.0 + 36 * (k_ % 2)
            else:
                ang = DIRS.get(nm_, 0.0)
            sh = shades_around(colh, 3, 0.06, seed=9000 + k_ + zlib.crc32(p['id'].encode()) % 1000, hue=3)
            tag('icon', p['id'], 0.1 * k_)
            if mk.sum() < 0.6 * PX * PX * 2:   # tiny bits (windows, finials): one or two satin dots
                ys_, xs_ = np.nonzero(mk)
                cxp, cyp = xs_.mean() + u, ys_.mean() + v
                ln = max(1.0, (ys_.max() - ys_.min() + 1))
                put_poly(np.array([[cxp, cyp - ln / 2 + 0.5], [cxp, cyp + ln / 2 - 0.5]], np.float32), sh.lin[1], max(0.22, min(0.4, (xs_.max() - xs_.min() + 1) / PX / 2)),
                         0.35, 0.35, WOOL, ply_mm=0.4, taper_mm=0.1, tw_deg=10, seed=9100, hbias=0.35)
            else:
                pitch = 0.62 if p['kind'] in ('tree', 'lumber') else 0.68
                fill_mask(mk, u, v, ang, sh, style='laid', pitch=pitch, seed=9200 + k_, matid=WOOL, h0=0.15, hamp=0.4, r_fac=0.62, bend=0,
                          hbias=0.3, maxlen=25)
            k_ += 1
    # outline: brown stem around the silhouette (and roof / wall boundaries for towns)
    cs_, _ = cv2.findContours(ic['alpha'].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    tag('icon_out', p['id'], 0.8)
    for c in cs_:
        if len(c) < 8: continue
        pts = S.smooth_poly(S.resample(c[:, 0, :].astype(np.float32), 0.5 * PX), 2) + np.array([u, v], np.float32)
        pts = np.vstack([pts, pts[:1]])
        stem(pts, lin(OUTLINE), width=0.55 if p['kind'] in ('tree', 'lumber') else 0.7, seed=9300 + k_, h0=0.65, hamp=0.35, L=2.0)
    if p['kind'] in ('town', 'site'):
        roofm = np.zeros_like(lab, np.uint8)
        for mi, nm_ in enumerate(names):
            if nm_.startswith('roof') or nm_ in ('slate', 'thatch'): roofm |= (lab == mi).astype(np.uint8)
        cs_, _ = cv2.findContours(roofm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for c in cs_:
            if len(c) < 12: continue
            pts = S.smooth_poly(S.resample(c[:, 0, :].astype(np.float32), 0.5 * PX), 1) + np.array([u, v], np.float32)
            stem(np.vstack([pts, pts[:1]]), lin(OUTLINE), width=0.45, seed=9400 + k_, h0=0.62, hamp=0.3, L=1.8)
log('icons stitched', 'stitches', len(S.RECORD))

# ------------------------------------------------------------------ save
rec = S.RECORD; S.RECORD = None
pickle.dump(dict(record=rec, plots=PLOTS, W=W, H=H, PX=PX), open(f'{OUT}/record.pkl', 'wb'), protocol=4)
np.savez_compressed(f'{OUT}/masks.npz', icon=icon_mask, icon_dil=icon_dil, plot=plot_mask, base=m['base'], pidmap=pidmap)
# the bake-order final maps (look-dev reference; the film uses the replay in wavefront order)
np.savez_compressed(f'{OUT}/bake_final.npz', **{k: m[k] for k in ('h', 'alb', 'T', 'mat', 'cov', 'sid')})
log('saved', len(rec))
