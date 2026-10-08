"""R25 bake of the embroidered hex board, v2 (muted menu palette, varied icons, real padding rows, needle-path tags).
Outputs (maps/):  canvas.npz   linen + iron-gall underdrawing (pre-stitch state)
                  record.pkl   ordered stitch events (R25 put() tuples + couching squeezes) tagged (kind, key, order, gid), hex meta, piece icons
                  hexmap.npz   per-pixel hex index + edge distance
                  masks.npz    icon / icon_dil (linen knock-outs of the big pieces), tree mask, plots, base (cushion), base_heal, pidmap
python3 board_bake.py [--test]   (--test: only hexes within 3 of Grandbois, for look-dev)"""
import sys, os, json, math, time, pickle, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
sys.path.insert(0, RND)
import numpy as np, cv2
cv2.setNumThreads(2)
from emb.core import hex_lin, smooth_noise, hash1, WOOL, SILK, METAL, INK, LINEN, lin2oklab, oklab2lin, srgb2lin
from linen2 import make_linen
from emb import stitch as S
from emb.strands import squeeze_along as _squeeze
import pal2
from bakelib import Baker, tag, shades_around, new_gid, CUR_OXY
import icons2
from icons2 import K_FORE
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
from pieces_plan import visible_hexes
VIS = visible_hexes(L, 1.6)
if TEST:
    keep = lambda q, r: (abs(q) + abs(q + r) + abs(r)) // 2 <= 3
else:
    keep = lambda q, r: True
hv = lambda q, r: keep(q, r) and (q, r) in VIS          # heavy icons only where the camera can see

# ------------------------------------------------------------------ record hooks
S.RECORD = []
def _sq_rec(h, mat, stamp, sid, pts, rad, amount, keepmat):
    S.RECORD.append(('SQ', np.array(pts, np.float32) + np.array(CUR_OXY[0], np.float32), rad, amount, keepmat, sid, S.TAG[0]))
    return _squeeze(h, mat, stamp, sid, pts, rad, amount, keepmat)
S.squeeze_along = _sq_rec
_put0 = S.put
def _put_oxy(m, p, *a, **k):
    CUR_OXY[0] = m.get('_oxy', (0, 0))
    return _put0(m, p, *a, **k)
S.put = _put_oxy

def P(x, z):
    """world (game units) -> board px (float32)"""
    return np.stack([(np.asarray(x) - BX0) * PPU, (np.asarray(z) - BZ0) * PPU], -1).astype(np.float32)

def lin(h): return hex_lin(h)

# ------------------------------------------------------------------ canvas: linen + light ageing
log('canvas', W, H)
m = make_linen(H, W, PX, seed=41, base_hex=pal2.LINEN_BASE)
S.ensure(m)
m['h'][:] *= 0.80                      # the weave is a texture, not a relief (v3: 0.80, thread irregularity breaks the dot grid so the raking light can pick the threads out)
rng = np.random.default_rng(5)
fox = np.zeros((H, W), np.float32)
for _ in range(int(W * H / PX / PX / 1e4 * 7 * 0.10)):
    cx_, cy_ = rng.uniform(0, W), rng.uniform(0, H)
    for _k in range(rng.integers(1, 4)):
        cv2.circle(fox, (int(cx_ + rng.normal(0, 2 * PX)), int(cy_ + rng.normal(0, 2 * PX))), max(1, int(rng.uniform(0.25, 1.2) * PX)), float(rng.uniform(0.4, 1)), -1, cv2.LINE_AA)
fox = cv2.GaussianBlur(fox, (0, 0), 0.35 * PX)
fc = lin('#9C7046'); a_ = np.clip(fox * 0.22, 0, 0.28)[..., None]
m['alb'][:] = m['alb'] * (1 - a_) + m['alb'] * (fc / fc.max()) * a_
del fox, a_
# soft creases (cloth lying on a table): a few long, very low ridges + a slow undulation of the weave
yy_, xx_ = np.mgrid[0:H:4, 0:W:4].astype(np.float32)
cre = np.zeros(yy_.shape, np.float32)
for k in range(5):
    a0 = rng.uniform(-0.5, 0.5); c0 = rng.uniform(0, 1)
    d = ((yy_ / H - c0) * math.cos(a0) - (xx_ / W - 0.5) * math.sin(a0)) * H / PX
    cre += rng.uniform(0.10, 0.22) * np.exp(-(d / rng.uniform(5, 11)) ** 2) * np.clip(1 - np.abs(xx_ / W - rng.uniform(0.2, 0.8)) / rng.uniform(0.35, 0.7), 0, 1)
cre = cv2.resize(cre, (W, H), interpolation=cv2.INTER_CUBIC)
m['h'][:] += cre; del cre, yy_, xx_
LINEN_ALB = None
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

B = Baker(m, W, H)

# ------------------------------------------------------------------ icons of the pieces, in board px
BIG = ('town', 'site', 'lumber', 'banner', 'card')
icon_mask = np.zeros((H, W), np.uint8)      # linen knock-out of the big pieces (their elevation is stitched on bare linen)
tree_mask = np.zeros((H, W), np.uint8)      # tree icons are appliqued onto the satin
ICON = {}
def card_embroidery(unit, realm, wpx, hpx, seed):
    c = load_card(unit, realm)
    alb = cv2.resize(cv2.cvtColor((c['alb'] * 255).astype(np.uint8), cv2.COLOR_RGB2BGR), (wpx, hpx), interpolation=cv2.INTER_AREA)
    alb = cv2.cvtColor(alb, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    al = cv2.resize(c['alpha'], (wpx, hpx), interpolation=cv2.INTER_AREA)
    sil = (al > 0.6).astype(np.uint8)
    sil = cv2.erode(sil, np.ones((3, 3), np.uint8))            # strips the anti-aliased die-cut ring of the sprite
    return alb, sil
for p in PIECES:
    x0, z0, x1, z1 = p['icon']
    u0, v0 = (x0 - BX0) * PPU, (z0 - BZ0) * PPU
    wpx, hpx = int(round((x1 - x0) * PPU)), int(round((z1 - z0) * PPU))
    if wpx < 3 or hpx < 3 or u0 < 0 or v0 < 0 or u0 + wpx >= W or v0 + hpx >= H or not keep(*p['hex']): p['skip'] = True; continue
    if p['kind'] in ('town', 'site', 'lumber', 'banner'):
        lab, names, J = load_elev(p['model'])
        labr = cv2.resize(lab.astype(np.float32), (wpx, hpx), interpolation=cv2.INTER_NEAREST).astype(np.int32)
        ICON[p['id']] = dict(u=int(round(u0)), v=int(round(v0)), lab=labr, names=names, alpha=(labr >= 0), cols=None)
    elif p['kind'] == 'tree':
        lab, names, tiers = icons2.tree_lab(p['sp'], p['rad'], p['height'], p['seed'])
        hh_, ww_ = lab.shape
        # the icon rect is defined by the piece plan; resample the label image to it
        labr = cv2.resize(lab.astype(np.float32), (wpx, hpx), interpolation=cv2.INTER_NEAREST).astype(np.int32)
        cd, cl = pal2.TREE[p['sp']]
        ICON[p['id']] = dict(u=int(round(u0)), v=int(round(v0)), lab=labr, names=names, alpha=labr >= 0, cols=[cd, cl, pal2.TRUNK])
    elif p['kind'] == 'card':
        alb, sil = card_embroidery(p['unit'], p['realm'], wpx, hpx, 0)
        ICON[p['id']] = dict(u=int(round(u0)), v=int(round(v0)), lab=None, alpha=sil > 0, card=alb, wpx=wpx, hpx=hpx)
    ic = ICON[p['id']]
    sl = (slice(ic['v'], ic['v'] + ic['alpha'].shape[0]), slice(ic['u'], ic['u'] + ic['alpha'].shape[1]))
    if p['kind'] == 'tree': tree_mask[sl] |= ic['alpha'].astype(np.uint8)
    else: icon_mask[sl] |= ic['alpha'].astype(np.uint8)
kdil = int(0.55 * PX) | 1
# v3: a clean footprint outline (pressed padding), not the crumbly nearest-neighbour edge of the elevation labels: close the gaps between the parts of an
# elevation, then smooth the boundary (gaussian + threshold, sigma 0.3 mm)
_ic = cv2.morphologyEx(icon_mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(1.3 * PX) | 1, int(1.3 * PX) | 1)))
_ic = (cv2.GaussianBlur(_ic.astype(np.float32), (0, 0), 0.30 * PX) > 0.5).astype(np.uint8)
icon_mask = np.maximum(icon_mask, _ic)
icon_dil = cv2.dilate(icon_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kdil, kdil)))
icon_dil = (cv2.GaussianBlur(icon_dil.astype(np.float32), (0, 0), 0.25 * PX) > 0.5).astype(np.uint8)
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

# ------------------------------------------------------------------ farm plots, hill mounds, peaks, tufts (geometry, in the idiom of the game board)
PLOTS = []; POLES = []; STOOKS = []; MOUNDS = []; PEAKS = []; TUFTS = []
for h in HEX:
    q, r = h['q'], h['r']
    if not hv(q, r): continue
    hc = (h['x'], h['z']); key = (q, r)
    if h['t'] == 'farm':
        plots, pole, stook = icons2.farm_plots(hc, key)
        for k, pl in enumerate(plots): PLOTS.append(dict(pl, hex=key, k=k))
        if pole: POLES.append(dict(hex=key, p=pole))
        if stook: STOOKS.append(dict(hex=key, s=stook))
    elif h['t'] == 'hills':
        for k, mo in enumerate(icons2.hill_mounds(hc, key)): MOUNDS.append(dict(mo, hex=key, k=k))
    elif h['t'] == 'mountain':
        for k, pk in enumerate(icons2.mountain_peaks(hc, key)): PEAKS.append(dict(pk, hex=key, k=k))
    elif h['t'] == 'plains':
        tu, sh = icons2.plain_tufts(hc, key)
        TUFTS.append(dict(hex=key, tufts=tu, shrub=sh))
plot_mask = np.zeros((H, W), np.uint8)
plot_lab = np.zeros((H, W), np.int32)
for i, pl in enumerate(PLOTS):
    poly = np.round(P(*np.array(pl['pts']).T)).astype(np.int32)
    tmp = np.zeros((H, W), np.uint8)
    cv2.fillPoly(tmp, [poly], 1)
    tmp &= (1 - icon_dil)
    plot_lab[(tmp > 0) & (plot_lab == 0)] = i + 1
    plot_mask |= tmp
SEA_HEX = [(h['x'], h['z']) for h in HEX if h['t'] == 'sea' and hv(h['q'], h['r'])]
LAND_HEX = [(h['x'], h['z']) for h in HEX if h['t'] not in ('sea', 'lake')]
WAVES = icons2.wave_marks(SEA_HEX, LAND_HEX)
log('plots', len(PLOTS), 'mounds', len(MOUNDS), 'peaks', len(PEAKS), 'waves', len(WAVES))

# ------------------------------------------------------------------ underdrawing (iron-gall) on the bare linen
ud = np.zeros((H, W), np.float32)
r_ud = np.random.default_rng(9)
def ink_line(pts_px, val=0.8, wmm=0.40, closed=False):
    q = S.resample(np.asarray(pts_px, np.float32), 0.6 * PX)
    if closed and len(q) > 2: q = np.vstack([q, q[:1]])
    q = q + (np.stack([S.smooth_noise1(len(q), 8, r_ud), S.smooth_noise1(len(q), 8, r_ud)], 1) * 0.12 * PX).astype(np.float32)
    cv2.polylines(ud, [np.round(q * 4).astype(np.int32)], False, float(val * r_ud.uniform(0.75, 1.0)), max(1, int(wmm * PX)), cv2.LINE_AA, shift=2)
for h in HEX:
    if h['t'] in ('sea', 'lake') or not keep(h['q'], h['r']): continue
    cs = hex_corners(h['q'], h['r'], 0.985)
    ink_line(P(*np.array(cs + cs[:1]).T), 0.85)
    if h['t'] in ('forest', 'hills', 'quarry', 'mountain'):
        ink_line(P(*np.array(icons2.dash_ring(h['q'], h['r'], 0.80)).T), 0.55, 0.30)
for p in PIECES:
    if p.get('skip'): continue
    ic = ICON[p['id']]
    cs_, _ = cv2.findContours(ic['alpha'].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for c in cs_:
        if len(c) < 6: continue
        ink_line(c[:, 0, :].astype(np.float32) + np.array([ic['u'], ic['v']], np.float32), 0.9, 0.30, closed=True)
for pl in PLOTS:
    ink_line(P(*np.array(pl['pts'] + pl['pts'][:1]).T), 0.7, 0.30)
for mo in MOUNDS:
    ink_line(P(*mo['poly'].T), 0.6, 0.30, closed=True)
for pk in PEAKS:
    ink_line(P(*np.array(pk['pts'] + pk['pts'][:1]).T), 0.6, 0.30)
riv = np.array(L['river'], np.float32)
ink_line(P(riv[:, 0], riv[:, 1]), 0.85, 0.42)
ud = cv2.GaussianBlur(ud, (0, 0), sigmaX=0.1 * PX, sigmaY=0.08 * PX)
ink = lin(pal2.INK)
a_ = np.clip(ud * 0.80, 0, 0.82)[..., None]
m['alb'][:] = m['alb'] * (1 - a_) + ink * a_
del a_, ud
log('underdrawing')

# ------------------------------------------------------------------ padding cushion ('base' height under stitches)
pad_h = {'forest': 1.35, 'plains': 1.15, 'farm': 1.0, 'hills': 1.45, 'mountain': 1.3, 'quarry': 1.1, 'sea': 0.0, 'lake': 0.0}
ph = np.array([pad_h[t] for t in ter], np.float32)[hid]
dome = np.sqrt(np.clip(1 - (1 - np.clip((dedge - 0.6) / 6.0, 0, 1)) ** 2, 0, 1))
base_heal = (ph * dome).astype(np.float32)
base_heal[water_px] = 0.22
base = base_heal.copy()
base = np.where(plot_mask > 0, base + 0.22, base)
# bare linen under the big pieces: nothing raised, no emboss.  v3: the padding around a footprint is PRESSED, it eases down into the footprint over ~1.8 mm
# (a soft shoulder) instead of the 1.2 mm cliff that read as torn paper
_dist = cv2.distanceTransform((icon_dil == 0).astype(np.uint8), cv2.DIST_L2, 5)
_w = smoothstep(0.0, 1.8 * PX, _dist).astype(np.float32)
base = np.where(icon_dil > 0, 0.0, base * _w)
del _dist, _w
m['base'][:] = base
del ph, dome
np.savez_compressed(f'{OUT}/canvas.npz', **{k: m[k] for k in ('h', 'alb', 'T', 'mat', 'cov', 'sid')})
# a pristine copy of the linen for the 'heal' fills (the satin that later closes over a footprint)
mh = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in m.items()}
mh['base'][:] = base_heal
log('canvas saved')

# ------------------------------------------------------------------ 1. padding rows + satin coupons (land hexes)
HEXMETA = {}
def pad_colour(hexcol):
    """undyed / dull felt: same hue as the coupon but much paler and low chroma, so the padding band reads as a lighter felt layer ahead of the thread"""
    lab = lin2oklab(lin(hexcol)[None])[0]
    lab[1:] *= pal2.PAD_CHROMA; lab[0] = 0.88 * lab[0] + 0.12 * pal2.PAD_L + 0.04
    return oklab2lin(lab[None])[0]
nf = 0
for i, h in enumerate(HEX):
    t = h['t']
    if t in ('sea', 'lake') or not keep(h['q'], h['r']): continue
    cx, cz = h['x'], h['z']
    u0, v0 = (cx - 1.0 - BX0) * PPU, (cz - 1.05 - BZ0) * PPU
    x0, y0 = int(max(0, u0)), int(max(0, v0)); x1, y1 = int(min(W, u0 + 2.0 * PPU)), int(min(H, v0 + 2.1 * PPU))
    sl = (slice(y0, y1), slice(x0, x1))
    own = (hid[sl] == i) & (dedge[sl] > 0.75 + wob[sl])
    mk = own & (icon_dil[sl] == 0)
    if mk.sum() < 50: continue
    colh, spr = pal2.DYE[t]
    sh = shades_around(colh, 5, spr, seed=100 + i, hue=3.5)
    ang = [30.0, 90.0, 150.0][(h['q'] - h['r']) % 3] + float(hash1(i, 5)) * 8 - 4
    HEXMETA[i] = dict(angle=ang, t=t)
    # padding: laid felt rows across the satin direction, low chroma (undyed felt), pressed down under the satin as it arrives
    mpad = cv2.erode(mk.astype(np.uint8), np.ones((int(0.45 * PX) | 1,) * 2, np.uint8)) > 0
    if mpad.sum() > 200:
        tag('pad', (h['q'], h['r']), 0.0)
        shp = shades_around(None, 3, 0.07, seed=700 + i, hue=3.0, lin_col=pad_colour(colh))
        B.fill_mask(mpad, x0, y0, ang + 90.0, shp, style='laid', pitch=1.25, seed=700 + i, matid=WOOL, h0=0.0, hamp=0.14, r_fac=0.52,
                    bend=0, maxlen=80, hbias=-0.06, gapfill=False, dye_noise=9.0)
    tag('field', (h['q'], h['r']), 0.0)
    B.fill_mask(mk, x0, y0, ang, sh, style='split', pitch=0.85, L=7.5, seed=200 + i, matid=SILK, h0=0.05, hamp=0.40, r_fac=0.6, bend=3.0)
    nf += 1
log('fields', nf, 'events', len(S.RECORD))

# ------------------------------------------------------------------ 2. crop plots on farm hexes: laid rows in two tones, outlined; pole + stook
for i, pl in enumerate(PLOTS):
    mkf = plot_lab == i + 1
    ys, xs = np.nonzero(mkf)
    if len(xs) < 30: continue
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    mk = mkf[y0:y1, x0:x1] & (dedge[y0:y1, x0:x1] > 0.6)
    kind = pl['kind']
    g0 = {'green': pal2.PLOT_GREENS, 'wheat': pal2.PLOT_WHEAT, 'plough': pal2.PLOT_PLOUGH}[kind]
    c_a, c_b = g0[pl['ci'] % len(g0)], g0[(pl['ci'] + 1) % len(g0)]
    sh = shades_around(c_a, 3, 0.05, seed=500 + i, hue=4)
    ca_, cb_ = lin(c_a), lin(c_b)
    fa = math.radians(pl['furrow']); pu_ = np.array([-math.sin(fa), math.cos(fa)], np.float32)
    def stripes(col, p, pu_=pu_, ca_=ca_, cb_=cb_):
        c = p.mean(0) @ pu_ / PX
        t = (math.floor(c / 1.7) % 2)
        return (ca_ if t == 0 else cb_ * 0.95) * float((col / (ca_ + 1e-6)).mean())
    tag('plot', pl['hex'], 1.0 + 0.1 * pl['k'])
    B.fill_mask(mk, x0, y0, pl['furrow'], sh, style='laid', pitch=0.8, seed=600 + i, matid=WOOL, h0=0.1, hamp=0.42, r_fac=0.62, bend=0,
                hbias=0.1, maxlen=30, colfn=lambda col, p, f=stripes: f(col, p))
    poly = P(*np.array(pl['pts'] + pl['pts'][:1]).T)
    tag('plot_out', pl['hex'], 1.5 + 0.1 * pl['k'])
    B.stem(poly, lin('#34401F' if kind == 'green' else '#4B3A1E'), width=0.75, seed=700 + i, h0=0.45, hamp=0.35, L=2.6)
for pole in POLES:
    p0, p1 = pole['p']
    tag('fence', pole['hex'], 1.9)
    B.put_poly(P(*np.array([p0, p1]).T), lin(pal2.FENCE) * 1.0, 0.85, 0.55, 0.5, WOOL, ply_mm=2.0, ply_deg=20, taper_mm=0.5, tw_deg=10, seed=17, hbias=0.4)
for st in STOOKS:
    sx, sz, rw, hh = st['s']
    tri = np.array([(sx - rw, sz), (sx, sz - hh), (sx + rw, sz)])
    ppx = P(tri[:, 0], tri[:, 1])
    x0, y0 = int(ppx[:, 0].min()) - 3, int(ppx[:, 1].min()) - 3; x1, y1 = int(ppx[:, 0].max()) + 4, int(ppx[:, 1].max()) + 4
    if x0 < 0 or y0 < 0 or x1 >= W or y1 >= H: continue
    mk = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillPoly(mk, [np.round(ppx - np.array([x0, y0])).astype(np.int32)], 1)
    tag('fence', st['hex'], 1.95)
    B.fill_mask(mk > 0, x0, y0, 80.0, shades_around(pal2.STOOK, 3, 0.06, seed=910), style='laid', pitch=0.6, seed=911, matid=WOOL, h0=0.2, hamp=0.4, bend=0, hbias=0.2, maxlen=12)
    B.stem(np.vstack([ppx, ppx[:1]]), lin(pal2.STOOK_O), width=0.6, seed=912, h0=0.6, hamp=0.35, L=2.0)
log('plots', len(PLOTS), 'events', len(S.RECORD))

# ------------------------------------------------------------------ 3. sea + lakes: laid denim, couched
land_near = cv2.dilate((~water_px).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
sea_fill = water_px & ~land_near
if TEST:
    ok = np.zeros((H, W), bool)
    for h in HEX:
        if keep(h['q'], h['r']) and h['t'] in ('sea', 'lake'): ok |= hid == HK[(h['q'], h['r'])]
    sea_fill &= ok
sea_sh = shades_around(pal2.SEA, 6, 0.08, seed=31, hue=4)
lake_sh = shades_around(pal2.LAKE, 4, 0.06, seed=32, hue=4)
for i, h in enumerate(HEX):
    if h['t'] not in ('sea', 'lake') or not keep(h['q'], h['r']): continue
    cx, cz = h['x'], h['z']
    u0, v0 = (cx - 1.0 - BX0) * PPU, (cz - 1.05 - BZ0) * PPU
    x0, y0 = int(max(0, u0)), int(max(0, v0)); x1, y1 = int(min(W, u0 + 2.0 * PPU)), int(min(H, v0 + 2.1 * PPU))
    sl = (slice(y0, y1), slice(x0, x1))
    mk = (hid[sl] == i) & sea_fill[sl] & (dedge[sl] > 0.3 + 0.5 * wob[sl])
    if mk.sum() < 50: continue
    tag('sea', (h['q'], h['r']), 0.0)
    B.fill_mask(mk, x0, y0, 0.0 + float(hash1(i, 9)) * 6 - 3, lake_sh if h['t'] == 'lake' else sea_sh, style='split', pitch=0.9, L=13.0,
                seed=900 + i, matid=WOOL, h0=0.05, hamp=0.36, r_fac=0.6, bend=5.0,
                couch=dict(spacing=8.5, tie=5.0, r_mm=0.33, colmul=0.93, h0=0.32, hamp=0.22, matid=WOOL), maxlen=40, dye_noise=22.0)
log('sea', 'events', len(S.RECORD))
# wave marks: hand-placed, irregular (blue-noise darts, three mark types, coast-biased density)
wave_c = lin(pal2.WAVE)
for k, (wx, wz, kind, span, tilt) in enumerate(WAVES):
    for j, path in enumerate(icons2.wave_paths(wx, wz, kind, span, tilt, k)):
        pp = np.array(path, np.float64)
        tag('wave', (round(wx, 2), round(wz, 2)), 2.0 + 0.1 * j)
        B.stem(P(pp[:, 0], pp[:, 1]), wave_c * (0.9 + 0.2 * hash1(k * 7 + j, 3)), width=0.70, seed=3100 + 7 * k + j, h0=0.5, hamp=0.32, L=2.4)
# faint sea-grid dashes (pale blue running stitch) along sea/sea edges
grid_c = lin(pal2.GRID)
NB = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]
def edge_seg(q, r, i, inset=0.0):
    cs = hex_corners(q, r, 1.0 - inset)
    return cs[i], cs[(i + 1) % 6]
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
        B.running(P(*np.array([a, b]).T), grid_c, on=2.0, off=2.2, r_mm=0.26, seed=4000 + len(done_e), h0=0.42, hamp=0.22)
log('waves+grid', 'events', len(S.RECORD))

# ------------------------------------------------------------------ 4. seams, dashed inner rings, coast outline, realm borders
seam_c = lin(pal2.SEAM)
coast_c = lin(pal2.COAST)
gold = np.array(pal2.GOLD, np.float32)
REALM_TIE = {k: lin(v) for k, v in pal2.REALM_TIE.items()}
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
            B.running(P(*np.array([a, b]).T), seam_c, on=2.6, off=1.6, r_mm=0.34, seed=5000 + len(done_e), h0=0.35, hamp=0.3)
        if land_a and not land_b:
            a2, b2 = edge_seg(h['q'], h['r'], e, 0.012)
            tag('coast', (h['q'], h['r']), 4.2)
            B.stem(P(*np.array([a2, b2]).T), coast_c, width=1.0, seed=5500 + i * 7 + e, h0=0.4, hamp=0.42, L=3.0)
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
                B.put_poly(qpts.astype(np.float32), gold * (1 + rr_.uniform(-0.06, 0.04)), 0.37, 0.6, 0.4, METAL, ply_mm=0.4, ply_deg=62,
                           taper_mm=0.3, tw_deg=55, seed=6100 + k_, cov=0.0, hbias=0.35)
            seg = np.hypot(*np.diff(pts, axis=0).T); s_ = np.concatenate([[0], np.cumsum(seg)]) / PX
            pos = rr_.uniform(0.5, 2.0)
            tc = REALM_TIE[ra]
            while pos < s_[-1] - 0.4:
                c = np.array([np.interp(pos, s_, pts[:, 0]), np.interp(pos, s_, pts[:, 1])], np.float32)
                qq_ = np.stack([c - nrm * 0.95 * PX, c + nrm * 0.95 * PX]).astype(np.float32)
                B.put_poly(qq_, tc * (1 + rr_.uniform(-0.1, 0.1)), 0.2, 1.0, 0.14, SILK, ply_mm=0.3, taper_mm=0.15, tw_deg=0, seed=6200, cov=0.0, hbias=0.5)
                pos += 2.6 * (1 + rr_.uniform(-0.15, 0.15))
# dashed inner ring of the game's forest / hills / quarry / mountain hexes (dark running stitch, 0.80 hex radius)
dash_c = lin(pal2.DASH)
for i, h in enumerate(HEX):
    if h['t'] not in ('forest', 'hills', 'quarry', 'mountain') or not hv(h['q'], h['r']): continue
    ring = np.array(icons2.dash_ring(h['q'], h['r'], 0.80))
    tag('dash', (h['q'], h['r']), 4.4)
    B.running(P(ring[:, 0], ring[:, 1]), dash_c, on=2.3, off=1.7, r_mm=0.30, seed=5800 + i, h0=0.5, hamp=0.3)
log('seams/coast/borders/dashes', 'events', len(S.RECORD))

# ------------------------------------------------------------------ 5. river (couched cord), hill mounds, mountain peaks, plains tufts
if not TEST:
    rv = P(riv[:, 0], riv[:, 1])
    rv = S.smooth_poly(S.resample(rv, 0.8 * PX), 6)
    tag('river', (-3, -3), 4.5)
    for k_, o in enumerate((-0.9, 0.0, 0.9)):
        d_ = np.gradient(rv, axis=0); d_ /= (np.linalg.norm(d_, axis=1, keepdims=True) + 1e-6)
        nn = np.stack([-d_[:, 1], d_[:, 0]], 1)
        S.cord_path(dict(m, _oxy=(0, 0)), (rv + nn * o * PX).astype(np.float32), lin(pal2.RIVER[k_]), PX,
                    width=1.1, h0=0.5, hamp=0.45, seed=7000 + k_, tie=3.0, tie_col=lin(pal2.RIVER_TIE))
def poly_mask(poly_game, pad=3):
    ppx = P(poly_game[:, 0], poly_game[:, 1])
    x0, y0 = int(ppx[:, 0].min()) - pad, int(ppx[:, 1].min()) - pad; x1, y1 = int(ppx[:, 0].max()) + pad + 1, int(ppx[:, 1].max()) + pad + 1
    if x0 < 0 or y0 < 0 or x1 >= W or y1 >= H: return None
    mk = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillPoly(mk, [np.round(ppx - np.array([x0, y0])).astype(np.int32)], 1)
    return mk > 0, x0, y0, ppx
for mo in MOUNDS:
    pm = poly_mask(mo['poly'])
    if pm is None: continue
    mk, x0, y0, ppx = pm
    if icon_dil[y0:y0 + mk.shape[0], x0:x0 + mk.shape[1]][mk].any(): continue
    lt = poly_mask(mo['light'])
    cb, ct = pal2.MOUND[mo['ci']]
    m['base'][y0:y0 + mk.shape[0], x0:x0 + mk.shape[1]] += (mk * 0.35).astype(np.float32)
    tag('relief', mo['hex'], 2.0 + 0.2 * mo['k'])
    dark = mk.copy()
    if lt is not None:
        lm, lx0, ly0, _ = lt
        full_l = np.zeros_like(mk)
        yy0, xx0 = ly0 - y0, lx0 - x0
        a0, b0 = max(0, yy0), max(0, xx0)
        a1, b1 = min(mk.shape[0], yy0 + lm.shape[0]), min(mk.shape[1], xx0 + lm.shape[1])
        full_l[a0:a1, b0:b1] = lm[a0 - yy0:a1 - yy0, b0 - xx0:b1 - xx0]
        full_l &= mk
        dark = mk & ~cv2.dilate(full_l.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        B.fill_mask(dark, x0, y0, 165.0, shades_around(cb, 4, 0.07, seed=8100 + mo['k'] + len(MOUNDS)), style='laid', pitch=0.7, seed=8200 + mo['k'],
                    matid=SILK, h0=0.25, hamp=0.42, r_fac=0.62, bend=0, hbias=0.2)
        B.fill_mask(full_l, x0, y0, 20.0, shades_around(ct, 4, 0.06, seed=8150 + mo['k']), style='laid', pitch=0.7, seed=8250 + mo['k'],
                    matid=SILK, h0=0.3, hamp=0.42, r_fac=0.62, bend=0, hbias=0.25)
    else:
        B.fill_mask(mk, x0, y0, 160.0, shades_around(cb, 4, 0.07, seed=8100), style='laid', pitch=0.7, seed=8200, matid=SILK, h0=0.25, hamp=0.42, bend=0, hbias=0.2)
    tag('relief_out', mo['hex'], 2.6 + 0.2 * mo['k'])
    B.stem(np.vstack([ppx, ppx[:1]]), lin(pal2.MOUND_O), width=0.7, seed=8300 + mo['k'], h0=0.6, hamp=0.35, L=2.4)
for pk in PEAKS:
    poly = np.array(pk['pts'])
    pm = poly_mask(poly)
    if pm is None: continue
    mk, x0, y0, ppx = pm
    if icon_dil[y0:y0 + mk.shape[0], x0:x0 + mk.shape[1]][mk].any(): continue
    m['base'][y0:y0 + mk.shape[0], x0:x0 + mk.shape[1]] += (mk * 0.3).astype(np.float32)
    ax = float(P(np.array([pk['apex'][0]]), np.array([pk['apex'][1]]))[0, 0]) - x0
    left = mk.copy(); left[:, int(ax):] = False
    right = mk & ~left
    tag('relief', pk['hex'], 2.0 + 0.2 * pk['k'])
    B.fill_mask(left, x0, y0, 62.0, shades_around(pal2.PEAK_LIT, 3, 0.04, seed=8400 + pk['k']), style='laid', pitch=0.7, seed=8500 + pk['k'], matid=SILK, h0=0.3, hamp=0.4, bend=0, hbias=0.2)
    B.fill_mask(right, x0, y0, 118.0, shades_around(pal2.PEAK_SHADE, 3, 0.05, seed=8600 + pk['k']), style='laid', pitch=0.7, seed=8700 + pk['k'], matid=WOOL, h0=0.3, hamp=0.4, bend=0, hbias=0.2)
    tag('relief_out', pk['hex'], 2.6 + 0.2 * pk['k'])
    B.stem(np.vstack([ppx, ppx[:1]]), lin(pal2.PEAK_O), width=0.75, seed=8800 + pk['k'], h0=0.6, hamp=0.35, L=2.4)
tuft_c = lin(pal2.TUFT)
for tf in TUFTS:
    for k, (x, z, s, rot) in enumerate(tf['tufts']):
        tag('tuft', tf['hex'], 2.4 + 0.01 * k)
        for j, a in enumerate((-28, 0, 26)):
            aa = math.radians(a + rot - 90)
            pts = P(np.array([x, x + math.cos(aa) * s * (0.9 + 0.2 * j % 2)]), np.array([z, z + math.sin(aa) * s * (0.9 + 0.2 * j % 2)]))
            B.put_poly(pts, tuft_c * (0.9 + 0.15 * hash1(k * 3 + j, 5)), 0.27, 0.5, 0.3, WOOL, ply_mm=0.5, taper_mm=0.25, tw_deg=10, seed=8900 + k, hbias=0.3)
    if tf['shrub']:
        x, z, rad = tf['shrub']
        pm = poly_mask(np.array([(x + rad * math.cos(t), z + rad * 0.8 * math.sin(t) - rad * 0.2) for t in np.linspace(0, 2 * math.pi, 16, endpoint=False)]))
        if pm is not None and not icon_dil[pm[2]:pm[2] + pm[0].shape[0], pm[1]:pm[1] + pm[0].shape[1]][pm[0]].any():
            mk, x0, y0, ppx = pm
            tag('tuft', tf['hex'], 2.5)
            B.fill_mask(mk, x0, y0, 70.0, shades_around('#4A5F33', 3, 0.07, seed=8950), style='laid', pitch=0.6, seed=8951, matid=WOOL, h0=0.25, hamp=0.4, bend=0, hbias=0.2, maxlen=10)
log('river/relief/tufts', 'events', len(S.RECORD))

# ------------------------------------------------------------------ 6. piece icons: elevations of the game models, tiered trees, re-embroidered figures
DIRS = {'stone': 0, 'plaster': 0, 'cloth': 0, 'wood': 90, 'wood_dark': 90, 'plank': 0, 'window': 90, 'metal': 0, 'gold': 90,
        'white': 90, 'blazon': 90, 'dirt': 0, 'cloth_dark': 0}
def embroider_card_icon(p, ic, seed):
    """figure card -> palette-quantised regions, each filled with contour-following laid strands (needle painting), then a couched outline.
    The game sprite is only the cartoon: no sprite pixel survives, everything is thread."""
    alb, sil = ic['card'], ic['alpha'].astype(np.uint8)
    u, v = ic['u'], ic['v']
    hh_, ww_ = sil.shape
    lab = lin2oklab(srgb2lin(alb)).astype(np.float32)
    ys, xs = np.nonzero(sil)
    if len(xs) < 20: return
    X = lab[ys, xs] * np.array([1.0, 1.7, 1.7], np.float32)
    k = 13
    _, lb, cen = cv2.kmeans(X.astype(np.float32), k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 1e-4), 3, cv2.KMEANS_PP_CENTERS)
    cen = cen / np.array([1.0, 1.7, 1.7], np.float32)
    rank = np.argsort(np.argsort(cen[:, 0]))          # relabel by lightness so the mode/median filter smooths ordinal values
    L_ = -np.ones((hh_, ww_), np.int32); L_[ys, xs] = rank[lb.ravel()]
    cen = cen[np.argsort(cen[:, 0])]
    # mode filter: smooth the label image (removes speckle), keep silhouette
    for _ in range(2):
        tmp = (L_ + 1).astype(np.uint8)
        tmp = cv2.medianBlur(tmp, 3)
        L_ = np.where(sil > 0, tmp.astype(np.int32) - 1, -1)
        L_ = np.where((L_ < 0) & (sil > 0), 0, L_)
    order = np.argsort(-np.array([(L_ == c_).sum() for c_ in range(k)]))
    kk = 0
    for c_ in order:
        mk_all = L_ == c_
        if mk_all.sum() < 4: continue
        nc, cc = cv2.connectedComponents(mk_all.astype(np.uint8), connectivity=4)
        for ci in range(1, nc):
            mk = cc == ci
            n_px = int(mk.sum())
            if n_px < 5: continue
            colr = oklab2lin(cen[c_][None])[0]
            sh = S.ShadeSet(np.array([lin2oklab(colr[None])[0] * np.array([1.0 + 0.03 * t, 1, 1]) for t in (-1, 0, 1)], np.float32), 9500 + kk)
            dt = cv2.distanceTransform(mk.astype(np.uint8), cv2.DIST_L2, 3)
            tag('icon', p['id'], 0.1 * kk)
            if n_px < 26:
                ys_, xs_ = np.nonzero(mk)
                cxp, cyp = xs_.mean() + u, ys_.mean() + v
                ln = max(1.0, (ys_.max() - ys_.min() + 1))
                B.put_poly(np.array([[cxp, cyp - ln / 2 + 0.5], [cxp, cyp + ln / 2 - 0.5]], np.float32), sh.lin[1], max(0.2, min(0.36, (xs_.max() - xs_.min() + 1) / PX / 2)),
                           0.35, 0.35, WOOL, ply_mm=0.4, taper_mm=0.1, tw_deg=10, seed=9100, hbias=0.35)
            else:
                c2, s2, coh = S.orient_tensor(cv2.GaussianBlur(dt, (0, 0), 0.8), 1.2, 3.0, mask=mk)
                nrm_ = np.hypot(c2, s2); weak = nrm_ < 1e-6
                c2 = np.where(weak, -1.0, c2 / (nrm_ + 1e-12)).astype(np.float32); s2 = np.where(weak, 0.0, s2 / (nrm_ + 1e-12)).astype(np.float32)
                B.fill_mask(mk, u, v, 90.0, sh, style='laid', pitch=0.50, seed=9200 + kk, matid=WOOL, h0=0.15, hamp=0.40, r_fac=0.62, bend=0, hbias=0.3, maxlen=14,
                            field=(c2, s2), minlen=0.5)
            kk += 1
    cs_, _ = cv2.findContours(sil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    tag('icon_out', p['id'], 0.8)
    # v3: the couched outline is the figure's OWN darkest dye (a shade deeper), thinner, not a near-black cartoon cel line
    dk = cen[0].copy(); dk[0] *= 0.82
    out_col = oklab2lin(dk[None])[0]
    for c in cs_:
        if len(c) < 8: continue
        pts = S.smooth_poly(S.resample(c[:, 0, :].astype(np.float32), 0.5 * PX), 2) + np.array([u, v], np.float32)
        B.stem(np.vstack([pts, pts[:1]]), out_col, width=0.46, seed=9300 + kk, h0=0.60, hamp=0.32, L=2.0)

# painter's order: far (north) pieces first so nearer icons overlap them
order_p = sorted([p for p in PIECES if not p.get('skip') and keep(*p['hex'])], key=lambda p: (p['kind'] == 'tree', p['z_back']))
for p in order_p:
    ic = ICON[p['id']]
    u, v = ic['u'], ic['v']
    hh_, ww_ = ic['alpha'].shape
    if p['kind'] == 'card':
        embroider_card_icon(p, ic, 0)
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
            if ic['cols'] is not None:
                colh = ic['cols'][mi]
                ang = 62.0 if nm_ == 'crown_lt' else (118.0 if nm_ == 'crown_dk' else 90.0)
            else:
                colh = pcol(nm_, realm)
                if nm_.startswith('roof') or nm_ in ('slate', 'thatch'):
                    ys_, xs_ = np.nonzero(mk)
                    ang = 90.0 if (ys_.max() - ys_.min()) > 0.8 * (xs_.max() - xs_.min()) else 72.0 + 36 * (k_ % 2)
                else:
                    ang = DIRS.get(nm_, 0.0)
            sh = shades_around(colh, 3, 0.06, seed=9000 + k_ + zlib.crc32(p['id'].encode()) % 1000, hue=3)
            tag('icon', p['id'], 0.1 * k_)
            if mk.sum() < 0.6 * PX * PX * 2:
                ys_, xs_ = np.nonzero(mk)
                cxp, cyp = xs_.mean() + u, ys_.mean() + v
                ln = max(1.0, (ys_.max() - ys_.min() + 1))
                B.put_poly(np.array([[cxp, cyp - ln / 2 + 0.5], [cxp, cyp + ln / 2 - 0.5]], np.float32), sh.lin[1], max(0.22, min(0.4, (xs_.max() - xs_.min() + 1) / PX / 2)),
                           0.35, 0.35, WOOL, ply_mm=0.4, taper_mm=0.1, tw_deg=10, seed=9100, hbias=0.35)
            else:
                pitch = 0.62 if p['kind'] in ('tree', 'lumber') else 0.68
                B.fill_mask(mk, u, v, ang, sh, style='laid', pitch=pitch, seed=9200 + k_, matid=WOOL, h0=0.15, hamp=0.4, r_fac=0.62, bend=0,
                            hbias=0.3, maxlen=25)
            k_ += 1
    cs_, _ = cv2.findContours(ic['alpha'].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    tag('icon_out', p['id'], 0.8)
    for c in cs_:
        if len(c) < 8: continue
        pts = S.smooth_poly(S.resample(c[:, 0, :].astype(np.float32), 0.5 * PX), 2) + np.array([u, v], np.float32)
        pts = np.vstack([pts, pts[:1]])
        B.stem(pts, lin('#25301F' if p['kind'] == 'tree' else OUTLINE), width=0.5 if p['kind'] in ('tree', 'lumber') else 0.7, seed=9300 + k_, h0=0.65, hamp=0.35, L=2.0)
    if p['kind'] in ('town', 'site'):
        roofm = np.zeros_like(lab, np.uint8)
        for mi, nm_ in enumerate(names):
            if nm_.startswith('roof') or nm_ in ('slate', 'thatch'): roofm |= (lab == mi).astype(np.uint8)
        cs_, _ = cv2.findContours(roofm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        for c in cs_:
            if len(c) < 12: continue
            pts = S.smooth_poly(S.resample(c[:, 0, :].astype(np.float32), 0.5 * PX), 1) + np.array([u, v], np.float32)
            B.stem(np.vstack([pts, pts[:1]]), lin(OUTLINE), width=0.45, seed=9400 + k_, h0=0.62, hamp=0.3, L=1.8)
    elif p['kind'] == 'tree':
        pass
log('icons stitched', 'events', len(S.RECORD))

# ------------------------------------------------------------------ 7. heal fills (state C): satin closing over the footprints of the big pieces
HEAL_START = len(S.RECORD)
Bh = Baker(mh, W, H)
nheal = 0
for i, h in enumerate(HEX):
    t = h['t']
    if t in ('sea', 'lake') or not keep(h['q'], h['r']) or i not in HEXMETA: continue
    cx, cz = h['x'], h['z']
    u0, v0 = (cx - 1.0 - BX0) * PPU, (cz - 1.05 - BZ0) * PPU
    x0, y0 = int(max(0, u0)), int(max(0, v0)); x1, y1 = int(min(W, u0 + 2.0 * PPU)), int(min(H, v0 + 2.1 * PPU))
    sl = (slice(y0, y1), slice(x0, x1))
    own = (hid[sl] == i) & (dedge[sl] > 0.75 + wob[sl])
    mk = own & (icon_dil[sl] > 0)
    if mk.sum() < 60: continue
    colh, spr = pal2.DYE[t]
    sh = shades_around(colh, 5, spr, seed=100 + i, hue=3.5)
    tag('heal', (h['q'], h['r']), 0.0)
    # same field as the hex's coupon (same angle, same bend field seed): the closing satin continues the existing rows
    Bh.fill_mask(mk, x0, y0, HEXMETA[i]['angle'], sh, style='split', pitch=0.85, L=7.5, seed=200 + i, matid=SILK, h0=0.05, hamp=0.40, r_fac=0.6, bend=3.0)
    nheal += 1
log('heal', nheal, 'events', len(S.RECORD) - HEAL_START)

# ------------------------------------------------------------------ save
rec = S.RECORD; S.RECORD = None
piece_icons = {pid: dict(u=ic['u'], v=ic['v'], h=int(ic['alpha'].shape[0]), w=int(ic['alpha'].shape[1])) for pid, ic in ICON.items()}
pickle.dump(dict(record=rec, plots=PLOTS, W=W, H=H, PX=PX, hexmeta=HEXMETA, heal_start=HEAL_START, piece_icons=piece_icons, waves=WAVES),
            open(f'{OUT}/record.pkl', 'wb'), protocol=4)
np.savez_compressed(f'{OUT}/masks.npz', icon=icon_mask, icon_dil=icon_dil, tree=tree_mask, plot=plot_mask, base=m['base'], base_heal=base_heal, pidmap=pidmap)
json.dump(PIECES, open(f'{POC}/data/pieces.json', 'w'), indent=0)
log('saved', len(rec))
