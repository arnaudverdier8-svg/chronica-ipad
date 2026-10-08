"""M1: re-embroider the king's head (p1_oath crop x1100-1700 y380-1000) as thread-level maps.
Stitch plan = a few authored zone polygons (what an embroiderer would decide) + colour classes from the panel.
Every fill is made of individual stitches following the panel's own thread-direction field; each stitch gets
ONE thread colour (per-stitch mean of the panel, snapped to a restrained thread palette).
Output: maps/king_*.  Usage: python3 make_king.py [PX]
"""
import sys, os, time, math, json, numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emb
from scipy import ndimage

T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SP = os.path.abspath(os.path.join(ROOT, '../../..'))          # scratchpad
OUT = os.path.join(ROOT, os.environ.get('MAPSDIR', 'maps')); os.makedirs(OUT, exist_ok=True)
PX = float(sys.argv[1]) if len(sys.argv) > 1 else 16.0
SCALE = 1.25                       # physical scale vs panel native (5 px/mm) -> crop is 150 x 155 mm
MARGIN = 10.0                      # mm of plain linen around the crop
src = cv2.imread(os.path.join(SP, 'intro/p1_oath.png'))[..., ::-1][380:1000, 1100:1700].astype(np.float32) / 255
sh0, sw0 = src.shape[:2]
f = PX * SCALE / 5.0               # source px -> map px
CW, CH = sw0 * SCALE / 5.0, sh0 * SCALE / 5.0          # crop size in mm
W, H = int(round((CW + 2 * MARGIN) * PX)), int(round((CH + 2 * MARGIN) * PX))
ox, oy = int(round(MARGIN * PX)), int(round(MARGIN * PX))
cw, ch = int(round(CW * PX)), int(round(CH * PX))
print('king map', W, H, 'px  =', W / PX, 'x', H / PX, 'mm', flush=True)

def up(a, interp=cv2.INTER_CUBIC):
    """source-res array -> full canvas (crop placed at margin)."""
    r = cv2.resize(a, (cw, ch), interpolation=interp)
    shp = (H, W) + r.shape[2:]
    out = np.zeros(shp, r.dtype)
    out[oy:oy + ch, ox:ox + cw] = r
    return out

src_d = cv2.bilateralFilter(src, 5, 0.06, 3)
lab_s = emb.lin_to_oklab(emb.srgb_to_lin(src_d))
Ls, As, Bs = lab_s[..., 0], lab_s[..., 1], lab_s[..., 2]
Cs = np.hypot(As, Bs); hs = (np.degrees(np.arctan2(Bs, As)) + 360) % 360

# ---------------------------------------------------------------- zones (authored stitch plan, crop px coords)
Z = {
 'banner': [(70, 0), (482, 0), (482, 160), (275, 4), (70, 160)],
 'crown':  [(166, 88), (200, 84), (232, 62), (262, 56), (274, 38), (288, 56), (320, 62), (352, 84), (384, 88), (368, 186), (352, 208), (198, 208), (182, 186)],
 'face':   [(220, 214), (332, 214), (346, 258), (334, 298), (305, 318), (248, 318), (218, 298), (208, 258)],
 'beard':  [(214, 296), (340, 296), (356, 360), (338, 420), (300, 442), (254, 442), (218, 412), (204, 360)],
 'hair':   [(186, 212), (222, 206), (216, 300), (206, 362), (172, 368), (150, 345), (148, 295), (160, 250)],
 'hair2':  [(330, 206), (372, 212), (398, 255), (406, 320), (398, 352), (372, 372), (346, 360), (340, 300)],
 'collar': [(160, 404), (392, 404), (392, 540), (160, 540)],
 'robe':   [(0, 455), (600, 455), (600, 620), (0, 620)],
 'ermine': [(0, 440), (60, 410), (130, 362), (205, 345), (214, 405), (175, 440), (150, 470), (122, 520), (92, 562), (62, 600), (44, 620), (0, 620)],
 'ermine2': [(345, 345), (420, 355), (500, 400), (560, 440), (600, 450), (600, 620), (540, 620), (500, 565), (468, 520), (425, 470), (385, 440), (350, 405)],
 'throne': [(22, 140), (530, 140), (530, 470), (22, 470)],
}
PRIO = ['crown', 'face', 'beard', 'hair', 'hair2', 'collar', 'ermine', 'ermine2', 'robe', 'banner', 'throne']   # first wins
zone = np.full((sh0, sw0), -1, np.int16)
for zi, name in enumerate(PRIO):
    m = np.zeros((sh0, sw0), np.uint8); cv2.fillPoly(m, [np.array(Z[name], np.int32)], 1)
    zone = np.where((zone < 0) & (m > 0), zi, zone)
ZN = {n: i for i, n in enumerate(PRIO)}

# ---------------------------------------------------------------- colour classes (source res)
gold = (hs > 52) & (hs < 98) & (Cs > 0.085) & (Ls > 0.50)
red = ((hs < 32) | (hs > 352)) & (Cs > 0.085)
purple = (((hs > 280) & (hs <= 352)) & (Cs > 0.025)) | (((hs < 32) | (hs > 340)) & (Ls < 0.42) & (Cs > 0.04))
blue = (hs > 195) & (hs < 290) & (Cs > 0.012) & (Ls < 0.62)
green = (hs > 130) & (hs < 200) & (Cs > 0.035)
white = (Cs < 0.065) & (Ls > 0.70)
dark = Ls < 0.30
bgcol = (np.hypot(As - 0.012, Bs - 0.044) < 0.025) & (Ls > 0.76)

# stitch types
LIN, NEEDLE_F, NEEDLE_L, NEEDLE_M, LAID, LAID_GOLD, METAL, JEWEL, SPOT, LAID_BLUE, WOOD, FACE_DARK = range(12)
st = np.full((sh0, sw0), LIN, np.int16)
zc = lambda n: zone == ZN[n]
yy0, xx0 = np.mgrid[0:sh0, 0:sw0]
# banner
st[zc('banner') & (purple | blue | dark | red)] = LAID
st[zc('banner') & gold] = LAID_GOLD
st[zc('banner') & ~(purple | blue | dark | red | gold) & ~bgcol & (Cs > 0.05)] = LAID_GOLD
# throne
th = zc('throne')
st[th & ~bgcol] = WOOD
st[th & blue] = LAID_BLUE
st[th & (Cs < 0.035) & (Ls < 0.62) & (xx0 > 95) & (xx0 < 460) & (yy0 > 215)] = LAID_BLUE
st[th & bgcol & (xx0 > 100) & (xx0 < 455) & (yy0 > 225)] = LAID_BLUE
st[th & white & (yy0 > 330)] = NEEDLE_L     # ermine edge spilling into throne zone
# crown
cr = zc('crown')
st[cr] = METAL
st[cr & (red | purple) & (yy0 < 168)] = NEEDLE_M
st[cr & (red | green | blue) & (yy0 >= 168)] = JEWEL
st[cr & bgcol] = LIN
# face / beard / hair
st[zc('face')] = NEEDLE_F
st[zc('beard')] = NEEDLE_L
hz = zc('hair') | zc('hair2')
st[hz] = NEEDLE_L
# collar
co = zc('collar')
st[co] = LAID
st[co & gold] = METAL
st[co & (red | green | blue) & ~purple] = JEWEL
st[co & white] = NEEDLE_L
# ermine
er = zc('ermine') | zc('ermine2')
st[er & white] = NEEDLE_L
st[er & dark] = SPOT
st[er & ~white & ~dark] = NEEDLE_L
# robe
ro = zc('robe')
st[ro & (purple | red | dark | blue)] = LAID
st[ro & gold] = LAID_GOLD
st[ro & ~(purple | red | dark | blue | gold)] = LAID
st[(zone < 0)] = LIN
# ermine spots must be compact dark blobs; make ermine area everything not robe
st[er & ~white & ~dark & (purple | red)] = LAID

# clean small fragments: mode filter via one-hot blur
def clean_labels(lbl, n, sigma):
    best = None; bestv = None
    for k in range(n):
        v = cv2.GaussianBlur((lbl == k).astype(np.float32), (0, 0), sigma)
        if best is None: best = np.zeros(lbl.shape, np.int16); bestv = v
        else:
            s = v > bestv; best[s] = k; bestv = np.where(s, v, bestv)
    return best
st = clean_labels(st, 11, 1.0)

# ---------------------------------------------------------------- outlines (thin dark lines)
Lsrc = Ls.astype(np.float32)
bh = cv2.morphologyEx(Lsrc, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
lines = (bh > 0.085) & (Ls < 0.55)
blob = cv2.morphologyEx(lines.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))) > 0
lines &= ~blob
no_line_zone = zc('beard') | zc('hair') | zc('ermine') | zc('ermine2') | zc('hair2')
lines &= ~no_line_zone
lines &= zone >= 0
n, cc, stats, _ = cv2.connectedComponentsWithStats(lines.astype(np.uint8), 8)
keep = np.zeros(n, bool); keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= 14
lines = keep[cc]
print('line px (src)', int(lines.sum()), flush=True)

# ---------------------------------------------------------------- direction field from the panel's own strands
c2, s2, coh = emb.structure_dir([Lsrc, As * 2, Bs * 2], 0.9, 2.6)
w = np.clip(coh, 0.05, 1).astype(np.float32)
# zone default strand directions (doubled angle): vertical -> (-1,0), horizontal -> (1,0)
dflt = np.zeros((sh0, sw0, 3), np.float32)       # c2, s2, weight
for nm, (cc_, ss_, ww_) in {'beard': (-1, 0, 0.8), 'hair': (-1, 0, 0.6), 'hair2': (-1, 0, 0.6), 'robe': (-1, 0, 0.5),
                             'throne': (-1, 0, 0.5), 'banner': (-1, 0, 0.3), 'ermine': (-0.6, 0.8, 0.15), 'ermine2': (-0.6, -0.8, 0.15)}.items():
    zm = zone == ZN[nm]; dflt[zm] = (cc_, ss_, ww_)
wd = dflt[..., 2] * (1 - np.clip(coh, 0, 1)) ** 2
c2 = c2 * w + dflt[..., 0] * wd; s2 = s2 * w + dflt[..., 1] * wd; w = w + wd
C2 = up(c2); S2 = up(s2); Wc = up(w)
inside = np.zeros((H, W), bool); inside[oy:oy + ch, ox:ox + cw] = True
ST = up(st.astype(np.float32), cv2.INTER_NEAREST).astype(np.int16); ST[~inside] = LIN
ZONE = up(zone.astype(np.float32), cv2.INTER_NEAREST).astype(np.int16); ZONE[~inside] = -1
# smoother boundaries at map res
ST = clean_labels(ST, 11, 0.8 * PX)
ST[~inside] = LIN
# facial features (eyes, brows, nostrils, mouth line): dark split-stitch fills that keep their drawn shape
fd_src = ((bh > 0.10) | (Ls < 0.36)) & (zone == ZN['face'])
fd_src = cv2.dilate(fd_src.astype(np.uint8), np.ones((2, 2), np.uint8)) > 0
FD = up(cv2.GaussianBlur(fd_src.astype(np.float32), (0, 0), 0.6), cv2.INTER_CUBIC) > 0.42
ST[FD & (ZONE == ZN['face'])] = FACE_DARK
LAB = up(lab_s)
COL = emb.oklab_to_lin(LAB)
print('setup', round(time.time() - T0, 1), flush=True)

def field(sig_mm):
    c, s, _ = emb.smooth_dir(C2, S2, Wc + 1e-3, sig_mm * PX)
    return emb.dir_vec(c, s)
DXf, DYf = field(1.7)
DXc, DYc = field(0.8)      # face: follow the form closely
DXl, DYl = field(5.0)

# ---------------------------------------------------------------- linen ground (shared tile -> seamless with the ground plane)
TILE = np.load(os.path.join(OUT, 'linen_tile.npz')) if os.path.exists(os.path.join(OUT, 'linen_tile.npz')) else None
cfg = json.load(open(os.path.join(ROOT, 'scene_layout.json')))
KX, KY = cfg['king']['x0'], cfg['king']['y0']        # world mm of the patch top-left
cv = emb.Canvas(H, W, PX)
cv.h = emb.tile_sample(TILE['h'], KX, KY, H, W, PX)
cv.alb = emb.tile_sample(TILE['alb'], KX, KY, H, W, PX)
cv.T = emb.tile_sample(TILE['T'], KX, KY, H, W, PX)
cv.mat[:] = emb.MAT_LINEN

# frontier (embroidery "in progress" towards the crop edges)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
dedge = np.minimum.reduce([xx - ox, ox + cw - xx, yy - oy, oy + ch - yy]) / PX      # mm inside crop
dedge_eff = dedge - (5.0 + 3.5 * emb.snoise((H, W), 9 * PX, 77) + 1.5 * emb.snoise((H, W), 2.5 * PX, 78))
# underdrawing on the linen: the designer's brush lines (faint, warm grey-brown), visible in gaps and past the frontier
ud = up(np.clip(bh / 0.12, 0, 1).astype(np.float32) * (Ls < 0.6))
ud = cv2.GaussianBlur(ud, (0, 0), 0.6) * np.clip(1 - (-np.clip(dedge_eff, None, 0)) / 14, 0, 1) * inside
ink = emb.hex_lin('#5B4A44')
cv.alb = cv.alb * (1 - 0.35 * ud[..., None]) + ink * 0.35 * ud[..., None]

rng_seed = [100]
def stitch_mean_colour(sid, on, sl, palette, chroma=1.0, lj=0.035):
    """per-stitch mean of the panel colour -> nearest thread in palette (OKLab) + small per-stitch jitter."""
    out = np.zeros(on.shape + (3,), np.float32)
    if not on.any(): return out
    ids = sid[on]
    u, inv = np.unique(ids, return_inverse=True)
    lab = LAB[sl][on]
    cnt = np.bincount(inv).astype(np.float32)
    mean = np.stack([np.bincount(inv, lab[:, c]) / cnt for c in range(3)], -1)
    P = palette
    d = ((mean[:, None, :] - P[None, :, :]) * np.array([1.0, 1.6, 1.6])) ** 2
    pick = P[np.argmin(d.sum(-1), 1)].copy()
    j = emb.hash1(u, 17)
    pick[:, 0] *= 1 + lj * (j - 0.5) * 2
    pick[:, 1:] *= chroma
    rgb = emb.oklab_to_lin(pick)
    out[on] = np.clip(rgb[inv], 0, 1)
    return out

def class_palette(mask_src, n, role_hexes=None, pull=0.45, cmax=0.13, lscale=(1.0, 0.0)):
    """k-means thread shades from the panel pixels of this class, pulled toward the restrained palette roles."""
    Zs = lab_s[mask_src].reshape(-1, 3).astype(np.float32)
    if len(Zs) < n * 4:
        Zs = lab_s.reshape(-1, 3)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 1e-4)
    _, _, cen = cv2.kmeans(Zs * np.array([1, 2, 2], np.float32), n, None, crit, 2, cv2.KMEANS_PP_CENTERS)
    cen = cen / np.array([1, 2, 2], np.float32)
    if role_hexes:
        roles = np.array([emb.lin_to_oklab(emb.hex_lin(h)) for h in role_hexes])
        for i in range(n):
            # pull hue/chroma toward the nearest role (keep the shade's lightness)
            r = roles[np.argmin(((roles[:, 1:] - cen[i, 1:]) ** 2).sum(1) + 0.3 * (roles[:, 0] - cen[i, 0]) ** 2)]
            cen[i, 1:] = cen[i, 1:] * (1 - pull) + r[1:] * pull
    C = np.hypot(cen[:, 1], cen[:, 2]); s = np.minimum(1, cmax / (C + 1e-6))
    cen[:, 1] *= s; cen[:, 2] *= s
    cen[:, 0] = cen[:, 0] * lscale[0] + lscale[1]
    return cen.astype(np.float32)

PAL = {
    'purple': class_palette(purple & (zone >= 0), 6, ['#4E2F5E', '#71508A', '#4E2F5E'], 0.5, 0.11),
    'gold_wool': class_palette(gold, 4, ['#C3963F', '#D79A33', '#97591A'], 0.5, 0.12),
    'white': class_palette(white & (zone >= 0), 5, ['#E6D7B6', '#D6BE86', '#B49C74'], 0.6, 0.035, (0.98, 0.0)),
    'flesh': class_palette(zone == ZN['face'], 7, ['#E2C7A2', '#B65E43', '#7A4632', '#E6D7B6'], 0.35, 0.10),
    'wood': class_palette((st == WOOD), 3, ['#7A3B2C', '#C3963F', '#6E3326', '#34432F'], 0.45, 0.10),
    'blue': class_palette((st == LAID_BLUE), 4, ['#4F6F8A', '#2D4460', '#22232F'], 0.6, 0.06),
    'red': class_palette(red & (zone >= 0), 4, ['#A3181A', '#CC3A2C', '#56100E'], 0.4, 0.15),
    'grey': class_palette((zone == ZN['beard']) | (zone == ZN['hair']), 7, ['#E6D7B6', '#B49C74', '#7E6A4C', '#22232F'], 0.45, 0.04),
}
PAL['flesh'] = np.concatenate([PAL['flesh'], [emb.lin_to_oklab(emb.hex_lin('#3B2219')), emb.lin_to_oklab(emb.hex_lin('#6E3326'))]]).astype(np.float32)
PAL['feat'] = np.array([emb.lin_to_oklab(emb.hex_lin(h)) for h in ['#2A1812', '#3B2219', '#5A2E22', '#7A4632', '#9A6A4E']], np.float32)
PAL['jewel'] = np.array([emb.lin_to_oklab(emb.hex_lin(h)) for h in ['#A3181A', '#CC3A2C', '#1E6440', '#3A8C63', '#1F4E96', '#56100E']], np.float32)
PAL['spot'] = np.array([emb.lin_to_oklab(emb.hex_lin(h)) for h in ['#22232F', '#25293A', '#2B170D']], np.float32)
PAL['robe_all'] = np.concatenate([PAL['purple'], PAL['red'][:1]])
PAL['erm'] = np.concatenate([PAL['white'], PAL['grey'][:3]])

ORDER = {LAID_BLUE: 0.05, WOOD: 0.10, LAID: 0.25, LAID_GOLD: 0.35, NEEDLE_L: 0.45, SPOT: 0.55, NEEDLE_F: 0.65, NEEDLE_M: 0.72, METAL: 0.8, JEWEL: 0.88}

def keep_fn_factory():
    def kf(sid, sl):
        d = dedge_eff[sl]
        on = np.ones(sid.shape, bool)
        u, inv = np.unique(sid, return_inverse=True)
        md = np.bincount(inv.ravel(), d.ravel()) / np.bincount(inv.ravel())
        r = emb.hash1(u, 33)
        ok = (md > 0) & ~((md < 4) & (r < 0.35 * (1 - md / 4)))
        return ok[inv].reshape(sid.shape)
    return kf
KEEP = keep_fn_factory()

# ---------------------------------------------------------------- regions -> fills
gold_lin = emb.hex_lin('#E9BE6A'); tie_red = emb.hex_lin('#7A2A1E')
rid = 0
types_order = [LAID_BLUE, WOOD, LAID, LAID_GOLD, NEEDLE_L, SPOT, NEEDLE_F, FACE_DARK, NEEDLE_M, METAL, JEWEL]
for tp in types_order:
  for zz in range(-1, len(PRIO)):
    m = (ST == tp) & inside & (ZONE == zz)
    if not m.any(): continue
    n, cc, stats, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 4)
    for c in range(1, n):
        if stats[c, cv2.CC_STAT_AREA] < (0.8 * PX) ** 2: continue
        x, y, w_, h_ = stats[c, :4]
        rm = cc == c
        # inside the crop only; and only if the region reaches inside the frontier at all
        rid += 1
        DX, DY = (DXl, DYl) if tp in (LAID, LAID_BLUE, LAID_GOLD, WOOD) else ((DXc, DYc) if tp in (NEEDLE_F, FACE_DARK) else ((DXl, DYl) if tp == METAL else (DXf, DYf)))
        if tp == JEWEL or tp == SPOT:
            # satin across the blob's short axis
            ys_, xs_ = np.nonzero(rm[y:y + h_, x:x + w_])
            cov = np.cov(np.stack([xs_, ys_])) if len(xs_) > 3 else np.eye(2)
            ev, evec = np.linalg.eigh(cov)
            ax_ = evec[:, 0] if tp == JEWEL else evec[:, 1]          # jewel: strands along short axis; spot: along long axis
            DX = np.full((H, W), ax_[0], np.float32); DY = np.full((H, W), ax_[1], np.float32)
        PHI, PSI, DXo, DYo, bb = emb.phase_fields(DX, DY, rm, PX)
        region = dict(mask=rm, bbox=bb, id=rid)
        ob = ORDER.get(tp, 0.5)
        if tp in (LAID, LAID_BLUE, LAID_GOLD):
            pal = {LAID: PAL['robe_all'], LAID_BLUE: PAL['blue'], LAID_GOLD: PAL['gold_wool']}[tp]
            bar = None
            if tp == LAID_GOLD: bar = emb.hex_lin('#B07A2E')
            emb.fill_laid(cv, region, PHI, PSI, DXo, DYo, lambda sid, on, sl, pal=pal: stitch_mean_colour(sid, on, sl, pal),
                          p=0.85, hgt=0.48, seed=rid * 13, order_base=ob, bar_colour=bar, keep_fn=KEEP)
        elif tp == WOOD:
            emb.fill_laid(cv, region, PHI, PSI, DXo, DYo, lambda sid, on, sl: stitch_mean_colour(sid, on, sl, PAL['wood']),
                          p=0.85, hgt=0.46, seed=rid * 13, order_base=ob, bar_colour=None, keep_fn=KEEP)
        elif tp == NEEDLE_L:
            zname = PRIO[int(np.bincount(np.clip(ZONE[rm], 0, None)).argmax())]
            pal = PAL['erm'] if zname in ('ermine', 'ermine2', 'collar', 'throne') else PAL['grey']
            emb.fill_needle(cv, region, PHI, PSI, DXo, DYo, lambda sid, on, sl, pal=pal: stitch_mean_colour(sid, on, sl, pal, lj=0.05),
                            p=0.62, L=5.2, Ljit=0.5, hgt=0.55, seed=rid * 7, order_base=ob, keep_fn=KEEP)
        elif tp == NEEDLE_F:
            emb.fill_needle(cv, region, PHI, PSI, DXo, DYo, lambda sid, on, sl: stitch_mean_colour(sid, on, sl, PAL['flesh'], lj=0.02),
                            p=0.42, L=1.7, Ljit=0.4, hgt=0.40, seed=rid * 7, order_base=ob, keep_fn=KEEP)
        elif tp == FACE_DARK:
            emb.fill_needle(cv, region, PHI, PSI, DXo, DYo, lambda sid, on, sl: stitch_mean_colour(sid, on, sl, PAL['feat'], lj=0.02),
                            p=0.34, L=1.3, Ljit=0.3, hgt=0.42, seed=rid * 7, order_base=0.7, keep_fn=KEEP)
        elif tp == NEEDLE_M:
            emb.fill_needle(cv, region, PHI, PSI, DXo, DYo, lambda sid, on, sl: stitch_mean_colour(sid, on, sl, PAL['red']),
                            p=0.6, L=3.2, hgt=0.6, seed=rid * 7, order_base=ob, keep_fn=KEEP)
        elif tp == METAL:
            emb.fill_metal_couched(cv, region, PHI, PSI, DXo, DYo, gold_lin, tie_red, p=0.52, hgt=0.68, seed=rid,
                                   order_base=ob, keep_fn=KEEP, tarnish=0.25)
        elif tp in (JEWEL, SPOT):
            dist = cv2.distanceTransform(rm.astype(np.uint8), cv2.DIST_L2, 5) / PX
            dm = max(float(dist.max()), 0.3)
            pad = (1.15 if tp == JEWEL else 0.35) * np.sqrt(np.clip(dist / dm, 0, 1)) + (0.45 if tp == JEWEL else 0.2)
            pal = PAL['jewel'] if tp == JEWEL else PAL['spot']
            emb.fill_needle(cv, region, PHI, PSI, DXo, DYo, lambda sid, on, sl, pal=pal: stitch_mean_colour(sid, on, sl, pal, lj=0.02),
                            p=0.38 if tp == JEWEL else 0.5, L=60, Ljit=0.0, hgt=0.3, seed=rid * 7, order_base=ob,
                            mat=emb.MAT_SILK if tp == JEWEL else emb.MAT_WOOL, kind=3 if tp == JEWEL else 1, keep_fn=KEEP, pad=pad, stagger=False)
print('fills done', rid, 'regions', round(time.time() - T0, 1), flush=True)

# ---------------------------------------------------------------- stem-stitch outlines on top
# (a) boundaries between stitch types / stitched-vs-linen (not across same-type, not around spots/jewels)
STk = ST.copy(); STk[(cv.kind == 0) & (ST != LIN)] = LIN          # where frontier dropped the stitches -> linen
grp = STk.copy(); grp[np.isin(grp, [JEWEL, SPOT])] = 99
grp[np.isin(grp, [NEEDLE_L, NEEDLE_F, FACE_DARK])] = 98                      # hair/beard/face flow into each other
gmax = cv2.dilate(grp.astype(np.float32), np.ones((3, 3), np.uint8)); gmin = cv2.erode(grp.astype(np.float32), np.ones((3, 3), np.uint8))
B = (gmax != gmin)
B &= ~cv2.dilate(np.isin(STk, [JEWEL, SPOT]).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
B = cv2.dilate(B.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
B &= dedge_eff > 1.0
# (b) face features from the panel (strong dark lines only, inside the face zone)
fl = (bh > 0.11) & (zone == ZN['face'])
n2, cc2, st2, _ = cv2.connectedComponentsWithStats(fl.astype(np.uint8), 8)
k2 = np.zeros(n2, bool); k2[1:] = st2[1:, cv2.CC_STAT_AREA] >= 10
FL = up(k2[cc2].astype(np.float32), cv2.INTER_LINEAR) > 0.45
LM = B
skel = emb.thin(LM)
n3, cc3, st3, _ = cv2.connectedComponentsWithStats(skel.astype(np.uint8), 8)
k3 = np.zeros(n3, bool); k3[1:] = st3[1:, cv2.CC_STAT_AREA] >= 4 * PX
skel = k3[cc3]
tx, ty = emb.line_tangents(cv2.GaussianBlur(LM.astype(np.float32), (0, 0), 1.0), PX, 0.5)
inkb = emb.hex_lin('#22232F'); inkr = emb.hex_lin('#6E3326'); inkw = emb.hex_lin('#3B2219')
face_m = ZONE == ZN['face']
crown_m = (ZONE == ZN['crown']) | (ZONE == ZN['collar'])
def col_fn(iy, ix, rng):
    if face_m[iy, ix]: c = emb.hex_lin('#5A2E22')
    elif crown_m[iy, ix]: c = emb.hex_lin('#4A2410')
    elif ZONE[iy, ix] == ZN['throne']: c = inkw
    else: c = inkb
    return c * (1 + rng.uniform(-0.08, 0.08))
def L_fn(iy, ix): return 1.6 if face_m[iy, ix] else (2.4 if crown_m[iy, ix] else 3.2)
def r_fn(iy, ix): return 0.30 if face_m[iy, ix] else (0.38 if crown_m[iy, ix] else 0.48)
hbase = cv2.GaussianBlur(cv.h, (0, 0), 0.8 * PX)
def base_fn(iy, ix): return float(hbase[iy, ix]) * 0.6
emb.stem_along_skeleton(cv, skel, tx, ty, col_fn, L=3.2, r=0.48, hgt=0.5, base_fn=base_fn, slant=14, seed=5,
                        spacing=None, order_fn=lambda iy, ix: 0.96, Lfn=L_fn, rfn=r_fn)
print('outlines done', round(time.time() - T0, 1), flush=True)

# ---------------------------------------------------------------- finish + write
emb.finish(cv, fuzz=True, fibres_per_mm2=0.45, seed=11)
# exact match with the ground plane at the patch border: blend the outer band to the tile-baked linen
LB = emb.tile_sample(np.load(os.path.join(OUT, 'linen_alb_baked.npy')), KX, KY, H, W, PX)
band = np.clip((np.minimum.reduce([xx, W - 1 - xx, yy, H - 1 - yy]) / PX - 1.0) / 3.0, 0, 1)[..., None]
cv.alb_final = cv.alb_final * band + LB * (1 - band)
np.save(os.path.join(OUT, 'king_height.npy'), cv.h.astype(np.float32))
alb_s = emb.lin_to_srgb(cv.alb_final)
emb.save_png8(os.path.join(OUT, 'king_albedo.png'), alb_s)
N = emb.normal_map(cv.h, PX, sigma_hp_mm=cfg['mesh_hp_sigma_mm'])
emb.save_png16(os.path.join(OUT, 'king_normal.png'), N * 0.5 + 0.5)
emb.save_png8(os.path.join(OUT, 'king_mat.png'), cv.mat[..., :3], alpha=cv.mat[..., 3])
np.save(os.path.join(OUT, 'king_order.npy'), cv.order.astype(np.float16))
np.save(os.path.join(OUT, 'king_kind.npy'), cv.kind)
json.dump(dict(W=W, H=H, px=PX, w_mm=W / PX, h_mm=H / PX), open(os.path.join(OUT, 'king_meta.json'), 'w'))
# quick numpy preview (raking light) for iteration
pv = emb.preview(cv.h, cv.alb_final, cv.mat, cv.T, PX)
cv2.imwrite(os.path.join(ROOT, 'work', 'king_preview.jpg'), pv[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 92])
cv2.imwrite(os.path.join(ROOT, 'work', 'king_preview_zoom.png'), pv[int(H * 0.28):int(H * 0.28) + 900, int(W * 0.35):int(W * 0.35) + 1400, ::-1])
print('done', round(time.time() - T0, 1), 's', flush=True)
