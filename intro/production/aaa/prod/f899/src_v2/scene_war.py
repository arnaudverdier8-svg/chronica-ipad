"""S12 'war' kit sheet (frieze section 3), v2: the war strip in the Bayeux idiom, built on a bkit Canvas.

Sheet 660 x 345 mm (frieze mm = sheet mm; every x of v1 is shifted by DX = 30 mm so the dutch camera never leaves the cloth).
Contents (front -> back):
  * 10 front-rank figures from the game cards (strike poses, Legion crimson facing right, merchants' blue facing left) in two ranks (hero scale
    and 0.83 x), each its own record group 'slip0..9'; they may overlap each other (the occlusion is reset per slip): the sheet's _ground copy
    carries their footprints (protected linen, needle holes, underdrawing); the full sheet is where the Eevee slips are cut from;
  * turf lines (couched earth bands) under every front figure, grass-tuft CLUSTERS (varied scale / lean / colour), bare linen elsewhere;
  * two ranks of flat figures farther up the cloth (idle / strike cards at 0.58 and 0.42 scale, colours alternating, less relief);
  * two rolling hillock ridges (closed mounds with hatched interiors), cloud / glow bars and a NEEDLE-PAINTED madder-and-woad-grey dusk sky
    (long-and-short split stitch, per-row feathered colour, no regular couching ticks);
  * the upper border: hem + nail holes, the gold chronicle thread (couched pair, whole width), compartments with diagonal bars, the two
    confronted game lions, sprigs.

    python3 scene_war.py [--px 10] [--out DIR] [--parts front,far,field,hills,sky,border]
"""
import os, sys, json, time, math, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bkit                                                           # noqa
import numpy as np, cv2                                               # noqa
from bkit.canvas import Canvas, colour                                # noqa
from bkit import motifs as M, geom as G                               # noqa
import figure as F                                                    # noqa
from chron.color import hex_lin, lin2oklab, oklab2lin                 # noqa
from chron import stitch as S                                         # noqa
from chron.stitch import CTX                                          # noqa
from chron.record import OUTLINE_REGION                               # noqa
from chron.util import vnoise                                         # noqa

DX = 30.0
SHEET_MM = (660.0, 345.0)
Y_RULE_TOP, Y_RULE_BOT = 17.5, 77.5
SKY_Y0, SKY_Y1 = 84.0, 160.0
RED, REDD, BLUE, BLUED = '#A3181A', '#6E2428', '#2F5F9E', '#2D4460'
GOLD_CROSS = dict(kind='cross')

# front ranks, nearest first: unit, pose, realm, x (feet centre, v1 frame: add DX), y (feet), card px per mm (5.0 = hero scale, 6.0 = 0.83x)
BASE_PPM = 5.0
FRONT = [
    ('legionary',    'strike', 'R', 282.0, 300.0, 4.6),    # the hero clash: legionary x man-at-arms
    ('man_at_arms',  'strike', 'B', 338.0, 295.0, 4.6),
    ('knight',       'strike', 'R', 129.0, 300.0, 5.0),
    ('horse_archer', 'strike', 'B', 452.0, 278.0, 5.0),
    ('mercenary',    'strike', 'R', 210.0, 283.0, 5.0),
    ('spearman',     'strike', 'B', 394.0, 272.0, 5.0),
    ('legionary',    'strike', 'R', 244.0, 243.0, 5.8),
    ('archer',       'strike', 'B', 427.0, 241.0, 5.8),
    ('archer',       'strike', 'R',  73.0, 261.0, 5.8),
    ('mercenary',    'strike', 'B', 528.0, 247.0, 5.8),
]
# far ranks (flat in the cloth): unit, pose, realm, x, y, scale (relative to the hero scale)
FAR_A = [('mercenary', 'idle', 'R', 2, 214, .56), ('legionary', 'idle', 'R', 40, 213, .58), ('knight', 'idle', 'R', 118, 215, .54), ('legionary', 'strike', 'R', 208, 213, .58),
         ('mercenary', 'idle', 'R', 276, 212, .58), ('spearman', 'idle', 'B', 348, 213, .58), ('man_at_arms', 'idle', 'B', 432, 214, .58),
         ('horse_archer', 'idle', 'B', 508, 215, .54), ('archer', 'strike', 'B', 566, 213, .58), ('knight', 'idle', 'B', 618, 214, .54)]
FAR_B = [('knight', 'strike', 'R', 36, 188, .42), ('knight', 'strike', 'R', 66, 189, .42), ('horse_archer', 'strike', 'B', 148, 188, .42), ('knight', 'idle', 'R', 232, 187, .42),
         ('horse_archer', 'idle', 'B', 312, 188, .42), ('knight', 'strike', 'R', 388, 187, .42), ('horse_archer', 'strike', 'B', 470, 188, .42),
         ('knight', 'idle', 'R', 548, 187, .42), ('horse_archer', 'idle', 'B', 606, 188, .42)]

# dusk sky, top -> horizon (fraction of the sky height): woad-grey, grey dusk, madder, ember terracotta, pale horizon glow (no violet, chroma <= .125)
SKY_STOPS = [(0.00, '#3C546D'), (0.12, '#46607A'), (0.26, '#54697F'), (0.38, '#657687'), (0.47, '#76777C'), (0.54, '#85706F'),
             (0.62, '#8A5650'), (0.71, '#984842'), (0.80, '#A8533F'), (0.89, '#BC6C48'), (0.96, '#CE8D5E'), (1.00, '#D8A672')]
TUFT_COLS = ['forest', 'olive', 'moss', 'sage', '#5F6B5A', '#7C6E3F', '#46563A']


def wavy(x0, x1, y, amp, wl, seed, n=120):
    xs = np.linspace(x0, x1, n)
    r = np.random.default_rng(seed)
    ph = r.uniform(0, 6.28, 3)
    ys = y + amp * (0.6 * np.sin(xs / wl * 6.283 + ph[0]) + 0.3 * np.sin(xs / (wl * 0.43) * 6.283 + ph[1]) + 0.1 * np.sin(xs / (wl * 0.17) * 6.283 + ph[2]))
    return np.stack([xs, ys], 1).astype(np.float32)


# ------------------------------------------------------------------ sky
def sky_lut(n=2048, chroma_cap=0.125):
    ts = np.array([s[0] for s in SKY_STOPS]); cols = np.array([hex_lin(s[1]) for s in SKY_STOPS], np.float32)
    lab = lin2oklab(cols)
    t = np.linspace(0, 1, n)
    out = np.stack([np.interp(t, ts, lab[:, k]) for k in range(3)], 1).astype(np.float32)
    out[:, 0] = np.clip(out[:, 0] + 0.045 * (1.0 - 0.5 * t), 0, 0.9)         # the dusk threads sit a little lighter than the draft (the hearth pool is low up there)
    C = np.hypot(out[:, 1], out[:, 2]) + 1e-9
    k = np.minimum(1.0, chroma_cap / C)
    out[:, 1] *= k; out[:, 2] *= k
    return out                              # OKLab (n, 3)


def sky_source(c, win, lut_lab, seed):
    """per-pixel source colour for the needle-painted sky: the gradient, displaced by row-correlated noise (rows ~0.85 mm differ, each row
    wanders along x over ~14 mm) + a large slow swell -> feathered long-and-short colour interleaving between neighbouring shades."""
    x0, y0, x1, y1 = win
    h, w = y1 - y0, x1 - x0
    PX = c.PX
    r = np.random.default_rng(seed)
    ny, nx = int(h / PX / 0.85) + 3, int(w / PX / 14.0) + 3
    g = r.standard_normal((ny, nx)).astype(np.float32)
    row = cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)
    g2 = r.standard_normal((int(h / PX / 3.0) + 3, int(w / PX / 40.0) + 3)).astype(np.float32)
    mid = cv2.resize(g2, (w, h), interpolation=cv2.INTER_CUBIC)
    swell = vnoise(x0 / PX, y0 / PX, h, w, PX, 85.0, seed + 3, 2)
    ys = ((np.arange(h, dtype=np.float32) + y0 + 0.5) / PX)[:, None]
    yeff = ys + 2.1 * row + 1.5 * mid + 7.0 * swell
    t = np.clip((yeff - SKY_Y0) / (SKY_Y1 - SKY_Y0), 0, 1)
    idx = np.clip((t * (len(lut_lab) - 1)).astype(np.int32), 0, len(lut_lab) - 1)
    lab = lut_lab[idx]                        # (h, w, 3) OKLab
    return oklab2lin(lab.reshape(-1, 3)).reshape(h, w, 3).astype(np.float32)


def sky_zone(c, top, bot, L, seed, lut_lab, src_full, win_full, pitch=0.82):
    poly = np.vstack([top, bot[::-1]]).astype(np.float32)
    win = c.win_of_polys([poly], 3.0)
    x0, y0, x1, y1 = win
    fx0, fy0, fx1, fy1 = win_full
    PX = c.PX
    mk = c.mask([poly], win).astype(bool) & ~c.occ[y0:y1, x0:x1]
    dt = cv2.distanceTransform(mk.astype(np.uint8), cv2.DIST_L2, 5) / PX
    nz = vnoise(x0 / PX, y0 / PX, y1 - y0, x1 - x0, PX, 5.0, seed + 5, 2)
    mk = dt > (0.22 + 0.4 * np.clip(0.5 + 1.4 * nz, 0, 1))
    if mk.sum() < 100:
        return
    sb = src_full[y0 - fy0:y1 - fy0, x0 - fx0:x1 - fx0]
    # field: horizontal with a slow swell and a row-scale wobble, stitches follow it
    xs = ((np.arange(x1 - x0, dtype=np.float32) + x0 + 0.5) / PX)[None, :]
    ys = ((np.arange(y1 - y0, dtype=np.float32) + y0 + 0.5) / PX)[:, None]
    th = np.radians(2.4 * np.sin(xs / 83.0 + seed) + 1.4 * np.sin(ys / 6.3 + xs / 131.0 + 0.7 * seed) + 0.6 * np.sin(xs / 23.0 + ys / 3.1))
    fld = (np.cos(2 * th).astype(np.float32), np.sin(2 * th).astype(np.float32))
    shades = lut_lab[np.linspace(0, len(lut_lab) - 1, 18).astype(int)]
    # dye lots: +-2 % L per shade
    rr = np.random.default_rng(seed + 8)
    sh = shades.copy(); sh[:, 0] *= 1 + 0.02 * rr.standard_normal(len(sh))
    from chron.color import ShadeSet
    shd = ShadeSet(sh, seed)
    rid = c.new_region(dict(name='sky', group=0, style='split'))
    lab = np.where(mk, rid, -1).astype(np.int32)
    sub = S.view(c.m, x0, y0, x1, y1)
    CTX['region'] = rid; CTX['group'] = 0; CTX['unit'] = -1
    S.fill_region(sub, lab, rid, fld, sb, shd, PX, style='split', pitch=pitch, L=L, seed=seed, couch=None, h0=0.05, hamp=0.40, r_fac=0.58,
                  maxlen=80, maxturn_deg=30, minlen=0.8, gapfill=True, ply_mm=0.7)
    CTX['region'] = 0


def cloud_bar(c, xc, yc, length, thick, seed, lut_lab, lift=1.12, jitter=9.0):
    """a lens-shaped laid-and-couched cloud / glow bar lighter than the sky around it; irregular couching (spacing x 1.3-2, random ties)."""
    r = np.random.default_rng(seed)
    xs = np.linspace(xc - length / 2, xc + length / 2, 90)
    u = (xs - xc) / (length / 2)
    env = np.clip(1 - np.abs(u) ** 2.2, 0, 1) ** 0.6
    wob = 0.9 * np.sin(xs / 17.0 + r.uniform(0, 6)) + 0.4 * np.sin(xs / 6.0 + r.uniform(0, 6))
    top = np.stack([xs, yc + wob - 0.5 * thick * env], 1).astype(np.float32)
    bot = np.stack([xs, yc + wob + 0.5 * thick * env + 0.25 * np.sin(xs / 9.0)], 1).astype(np.float32)
    poly = np.vstack([top, bot[::-1]])
    t = np.clip((yc - SKY_Y0) / (SKY_Y1 - SKY_Y0), 0, 1)
    lab = lut_lab[int(t * (len(lut_lab) - 1))].copy()
    lab[0] = min(lab[0] * lift + 0.015, 0.86); lab[1] *= 0.92; lab[2] *= 0.92
    col = oklab2lin(lab[None])[0]
    win = c.win_of_polys([poly], 3.0)
    mk = c.mask([poly], win).astype(bool)
    mid = np.stack([xs, yc + wob], 1).astype(np.float32)
    fld = M._field_along(c, win, [mid], 4.0)
    c.fill(mk, win, col, field=fld, couch=False, bar_spacing=float(r.uniform(8.5, 13.0)), tie=float(r.uniform(6.0, 9.0)), bar_jitter=jitter, seed=seed,
           group=None, name='cloud', erode=None, pitch=0.8, maxturn_deg=30, model=0.05, grad=0.03, nlots=4, lot_spread=0.06, maxlen=80, occlude=True,
           tie_col=col * 0.88)
    ink = M.ink_for(col)
    inkc = (col * 0.62).astype(np.float32)
    c.outline_mm(bot[::-1][::2], inkc, width=0.55, L=3.2, seed=seed + 1, group=None, cov=0.4)
    c.outline_mm(top[::2], inkc * 1.1, width=0.45, L=3.4, seed=seed + 2, group=None, cov=0.35)


def build_sky(c, no_clouds=False):
    W = c.w_mm
    lut = sky_lut()
    # sky window (whole width, a little margin)
    win_full = c.win_px(0, (SKY_Y0 - 6) * c.PX, c.W, (SKY_Y1 + 8) * c.PX)
    src = sky_source(c, win_full, lut, 5)
    # clouds first (nearer than the base)
    if not no_clouds:
        specs = [(0.62, 52, 150, 5.6), (0.80, 138, 118, 4.6), (0.70, 300, 170, 5.2), (0.84, 455, 130, 4.2), (0.60, 598, 120, 5.0), (0.90, 40, 100, 3.8),
                 (0.88, 262, 110, 4.0), (0.93, 520, 110, 3.6), (0.53, 395, 90, 4.0), (0.47, 150, 80, 3.4), (0.93, 400, 80, 3.2)]
        for k, (t, xc, ln, th) in enumerate(specs):
            cloud_bar(c, xc + DX, SKY_Y0 + t * (SKY_Y1 - SKY_Y0), ln, th, 700 + k, lut)
    # three zones with different stitch lengths and wavy, interleaving boundaries
    n = 420
    top0 = wavy(-8, W + 8, SKY_Y0, 0.5, 71.0, 21, n=n)
    b1 = wavy(-8, W + 8, SKY_Y0 + 0.36 * (SKY_Y1 - SKY_Y0), 1.5, 47.0, 22, n=n)
    b2 = wavy(-8, W + 8, SKY_Y0 + 0.72 * (SKY_Y1 - SKY_Y0), 1.7, 39.0, 23, n=n)
    bot = wavy(-8, W + 8, SKY_Y1, 1.3, 53.0, 24, n=n)
    # the zones overlap by 1.6 mm; the later one (lower) is stitched first so the upper zone's rows lie over the seam -> no straight join
    sky_zone(c, b2 - np.array([0, 0.8], np.float32), bot, 7.0, 531, lut, src, win_full)
    sky_zone(c, b1 - np.array([0, 0.8], np.float32), b2 + np.array([0, 0.8], np.float32), 10.5, 532, lut, src, win_full)
    sky_zone(c, top0, b1 + np.array([0, 0.8], np.float32), 15.0, 533, lut, src, win_full)
    ink = M.ink_for(hex_lin('#CE8D5E'))
    c.outline_mm(bot, ink, width=0.8, L=3.0, seed=541, group=None, cov=0.4)
    ink2 = M.ink_for(hex_lin('#3C546D'))
    c.outline_mm(top0 + np.array([0, 0.35], np.float32), ink2, width=0.7, L=3.2, seed=542, group=None, cov=0.4)


# ------------------------------------------------------------------ ground dressing
def tuft(c, x, y, h, seed, cols, lean=0.0, nblade=None, wid=0.7):
    r = np.random.default_rng(seed)
    nb = nblade or int(r.integers(2, 6))
    base_col = cols[int(r.integers(len(cols)))]
    for b in range(nb):
        a = math.radians(-90 + lean + (b - (nb - 1) / 2) * r.uniform(11, 24) + r.uniform(-7, 7))
        hh = h * r.uniform(0.55, 1.0)
        bend = r.uniform(-0.28, 0.28) * hh
        t = np.linspace(0, 1, 7)
        pts = np.stack([x + (b - (nb - 1) / 2) * 0.32 + hh * np.cos(a) * t + bend * t ** 2, y + hh * np.sin(a) * t], 1)
        cc = base_col if r.random() < 0.7 else cols[int(r.integers(len(cols)))]
        cl = colour(M.P(cc)) * r.uniform(0.9, 1.22)
        c.outline_mm(pts.astype(np.float32), np.clip(cl, 0, 1), width=wid * r.uniform(0.85, 1.2), L=2.0, seed=seed * 13 + b, group=None, h0=0.42, hamp=0.34, min_len_mm=0.7)


def tuft_clusters(c, seed, region, n_clusters, near=None):
    """Neyman-Scott clumps of tufts: varied height (2.2-6.6 mm), lean, blade count and colour; a few singles; more near the feet."""
    r = np.random.default_rng(seed)
    x0, y0, x1, y1 = region
    cols = TUFT_COLS
    pts = []
    for k in range(n_clusters):
        px_, py_ = r.uniform(x0, x1), r.uniform(y0, y1)
        n = int(r.integers(2, 7)); sig = r.uniform(4.0, 11.0)
        lean0 = r.uniform(-14, 14)
        for j in range(n):
            pts.append((px_ + r.normal(0, sig), py_ + r.normal(0, sig * 0.7), lean0 + r.normal(0, 7), r.uniform(0.35, 1.0)))
    for (nx, ny, nn) in (near or []):
        for j in range(nn):
            pts.append((nx + r.normal(0, 14), ny + r.normal(0, 5), r.normal(0, 14), r.uniform(0.3, 0.9)))
    n = 0
    for (x, y, lean, hs) in pts:
        if not (x0 < x < x1 and y0 < y < y1):
            continue
        h = 2.2 + 4.4 * hs ** 1.3
        tuft(c, x, y, h, seed * 1000 + n, cols, lean=lean)
        n += 1
    return n


def turf_line(c, x, y, width, seed, cols=('olive', 'moss')):
    """a couched earth / turf strip under a figure's feet (Bayeux ground line): two wavy bands + stem outline, tapering ends."""
    r = np.random.default_rng(seed)
    xs = np.linspace(x - width / 2, x + width / 2, 60)
    u = (xs - x) / (width / 2)
    env = np.clip(1 - np.abs(u) ** 3, 0, 1) ** 0.5
    ys = y + 0.9 * np.sin(xs / 11.0 + r.uniform(0, 6)) + 0.4 * np.sin(xs / 4.1 + r.uniform(0, 6))
    wid = [2.2, 1.7]
    off = 0.0
    for k, (col, w) in enumerate(zip(cols, wid)):
        top = np.stack([xs, ys + off * env], 1); bot = np.stack([xs, ys + (off + w) * env + 0.05], 1)
        poly = np.vstack([top, bot[::-1]]).astype(np.float32)
        win = c.win_of_polys([poly], 2.0)
        mk = c.mask([poly], win).astype(bool)
        mid = np.stack([xs, ys + (off + 0.5 * w) * env], 1).astype(np.float32)
        fld = M._field_along(c, win, [mid], 2.0)
        c.fill(mk, win, M.P(col), field=fld, couch=True, bar_spacing=float(r.uniform(5.5, 8.0)), bar_jitter=9.0, tie=float(r.uniform(4.5, 6.5)), seed=seed * 7 + k,
               group=None, name='turf', erode=(0.15, 0.22), model=0.05, grad=0.0, maxlen=40, min_area_mm2=0.3)
        off += w
    low = np.stack([xs, ys + off * env + 0.15], 1).astype(np.float32)
    c.outline_mm(low, M.ink_for(M.P(cols[-1])), width=0.75, L=2.8, seed=seed + 3, group=None, cov=0.4)


# ------------------------------------------------------------------ build
def build(PX=10.0, out=None, verbose=True, parts=('front', 'far', 'field', 'hills', 'sky', 'border'), only=None):
    c = Canvas(*SHEET_MM, PX=PX, seed=899, linen_seed=0, name='war', frieze_origin_mm=(1800.0, 0.0), verbose=verbose)
    W_mm, H_mm = SHEET_MM
    slips = []
    # ======================= front ranks (record groups slip0..)
    if 'front' in parts:
        c.say('front ranks')
        occ_union = c.occ.copy(); occ_base = c.occ.copy()
        for k, (unit, pose, realm, x, y, ppm) in enumerate(FRONT):
            if only is not None and k not in only:
                continue
            x = x + DX
            team, deep = (RED, REDD) if realm == 'R' else (BLUE, BLUED)
            card = F.load_card(unit, pose, team, flip=(realm == 'B'), shield=team, deep_hex=deep, sat=1.10 + 0.04 * (k % 3), val=0.93 + 0.03 * (k % 4))
            shc = GOLD_CROSS if realm == 'R' else dict(kind='chevron', col='#D6BE86')
            gname = f'slip{k}'
            c.occ = occ_base.copy()                 # slips may overlap each other on the sheet: each is stitched whole
            info = F.embroider(c, card, x, y, ppm=ppm, group=gname, seed=100 + k, shield_cross=shc, name=f'{unit}{k}', outline_mode='tonal', fill_pitch=0.8, gap_prob=0.62)
            occ_union |= c.occ
            slips.append(dict(group=gname, unit=unit, pose=pose, realm=realm, x_mm=x, y_mm=y, flip=(realm == 'B'), bbox_mm=info['bbox_mm'], ppm=ppm))
            c.say(gname, unit, info['regions'], 'regions', [round(v, 1) for v in info['bbox_mm']])
        c.occ = occ_union
    # ======================= far ranks (flat)
    if 'far' in parts:
        for rank, FAR in (('A', FAR_A), ('B', FAR_B)):
            for k, (unit, pose, realm, x, y, sc) in enumerate(FAR):
                team, deep = (RED, REDD) if realm == 'R' else (BLUE, BLUED)
                card = F.load_card(unit, pose, team, flip=(realm == 'B'), shield=team, deep_hex=deep)
                shc = GOLD_CROSS if realm == 'R' else dict(kind='chevron', col='#D6BE86')
                F.embroider(c, card, x + DX, y, ppm=BASE_PPM / sc, group=None, seed=300 + k + (50 if rank == 'B' else 0), shield_cross=shc,
                            name=f'far{rank}{k}', outline_w=0.8 if rank == 'A' else 0.7, hamp_mul=0.72)
            c.say('far rank', rank)
    # ======================= field: turf lines under the front figures, tuft clusters on the bare linen
    if 'field' in parts:
        c.say('field')
        for k, (unit, pose, realm, x, y, ppm) in enumerate(FRONT):
            wf = {'legionary': 62, 'knight': 112, 'mercenary': 58, 'man_at_arms': 56, 'spearman': 70, 'horse_archer': 88, 'archer': 52}[unit] * 5.0 / ppm * 1.0
            turf_line(c, x + DX, y + 2.4, wf, 900 + k, cols=('moss', 'ochre2') if k % 2 else ('olive', 'clay'))
        near = [(x + DX, y + 8, 3) for (_, _, _, x, y, _) in FRONT[:6]]
        n = tuft_clusters(c, 21, (14.0, 230.0, W_mm - 14.0, H_mm - 3.0), 30, near=near)
        c.say('tufts', n)
    # ======================= hillocks: two ridges as closed mounds (banded outline, hatched interior)
    if 'hills' in parts:
        c.say('hills')
        M.hill(c, M.ridge_contour(-45, W_mm + 45, 209.0, bumps=[(105 + DX, 62, 15, 1.3), (250 + DX, 46, 11, 1.5), (400 + DX, 72, 17, 1.2), (545 + DX, 56, 13, 1.4)],
                                  waves=((1.2, 61.0, 0.7),), y_foot=None), [(3.6, 'olive'), (3.2, 'moss'), (3.4, 'sage')], seed=240,
               outline=None, y_cut=None, interior='#9AA36E', interior_angle=-24.0, interior_couch=False, interior_depth=15.0, interior_style='split', interior_L=6.0,
               bar_jitter=8.0, bar_spacing=6.0, interior_model=0.10, interior_grad=0.12)
        M.hill(c, M.ridge_contour(-45, W_mm + 45, 188.0, bumps=[(55 + DX, 70, 21, 1.3), (200 + DX, 55, 14, 1.4), (335 + DX, 90, 23, 1.2), (475 + DX, 60, 17, 1.4), (600 + DX, 70, 21, 1.3)],
                                  waves=((1.4, 73.0, 2.1),), y_foot=None), [(3.8, 'woad_pale'), (3.4, 'slate'), (3.4, 'olive')], seed=241,
               interior='#7B8660', interior_angle=62.0, interior_couch=False, interior_depth=21.0, interior_style='split', interior_L=5.0,
               bar_jitter=8.0, bar_spacing=6.0, interior_model=0.10, interior_grad=0.12)
    # ======================= sky
    if 'sky' in parts:
        c.say('sky')
        build_sky(c)
    # ======================= border: hem, nail holes, gold chronicle thread, compartments
    if 'border' in parts:
        c.say('border')
        c.hem(11.0, 0.0, seed=3, run_y_mm=9.3)
        c.nail_hole(172.0 + DX, 5.4, seed=11)
        c.nail_hole(438.0 + DX, 5.7, seed=12)
        xs = np.linspace(-4.0, W_mm + 4.0, 470)
        ys = Y_RULE_TOP + 0.12 * np.sin(xs / 31.0) - 0.4 * (xs / W_mm) + 0.05 * np.sin(xs / 7.3)
        thr = np.stack([xs, ys], 1).astype(np.float32)
        ties = list(np.arange(5.0, W_mm, 6.5) + np.random.default_rng(4).uniform(-0.8, 0.8, len(np.arange(5.0, W_mm, 6.5))))
        c.metal_pair(thr, ties_s_mm=ties, tie_col='#8A2A1C', group='thread', seed=7, tie_len_mm=2.9, tie_r=0.30, thread_r=0.42, sep_mm=0.86,
                     gold=np.array([0.78, 0.46, 0.115], np.float32))
        c.occlude_polys([G.band(thr, -1.2, 1.2)])
        c.underdraw(np.array([(0, Y_RULE_TOP + 0.15), (W_mm, Y_RULE_TOP - 0.25)]), 0.85, width_mm=0.45, seed=11)
        bars_x = [8.0, 30.0, 108.0, 176.0, 303.0, 386.0, 446.0, 518.0, 592.0, 628.0]
        M.beast(c, 'red', (228.0 + DX, 25.0, 292.0 + DX, 72.5), flip=False, seed=31, group='border')
        M.beast(c, 'blue', (318.0 + DX, 25.5, 378.0 + DX, 72.5), flip=False, seed=32, group='border')
        spr = [(69.0, ('woad', 'terracotta'), 2, -0.1, 41.0), (142.0, ('terracotta', 'mustard'), 1, 0.15, 47.0), (203.0, ('madder', 'woad'), 1, 0.1, 38.0),
               (412.0, ('woad',), 1, -0.15, 44.0), (482.0, ('terracotta', 'woad'), 2, 0.1, 36.0), (555.0, ('mustard', 'madder'), 1, -0.05, 49.0),
               (19.0, ('madder',), 1, 0.12, 40.0), (610.0, ('woad', 'mustard'), 2, -0.1, 42.0)]
        for k, (sx, fc, nf, ln, hh) in enumerate(spr):
            M.sprig(c, sx + DX, 73.0, hh, flower_cols=fc, seed=50 + k, group='border', lean=ln, n_flowers=nf)
        bar_cols = ['olive', 'madder', 'olive', 'woad', 'terracotta', 'mustard', 'sage', 'woad', 'madder', 'olive']
        for k, bx in enumerate(bars_x):
            M.diag_bar(c, bx + DX, Y_RULE_TOP + 1.8, Y_RULE_BOT - 1.6, slant=(1 if k % 2 else -1), col=bar_cols[k], seed=70 + k, group='border', lean_mm=17.0)
        M.border_rules(c, 0.0, W_mm, Y_RULE_BOT, seed=7, group='border')
    c.say('stitching done')
    # footprints: needle holes at the real strand ends + red-brown underdrawing of each slip's outline + protected linen
    import chron.motifs.panel as PP
    from ghost_v2 import ghost_v2 as _orig

    def ghost2(m, rec, gsel, gmask, ud_paths, PX_, **kw):
        paths = []
        sel = np.asarray(gsel)
        sel = sel[rec['kind'][sel] == S.K_STEM]
        for u in np.unique(rec['unit'][sel]):
            ks = sel[rec['unit'][sel] == u]
            if len(ks) < 3:
                continue
            pts = np.array([rec['P'][rec['off'][k]:rec['off'][k + 1]].mean(0) for k in ks], np.float32)
            paths.append(pts)
        kw.update(ud_alpha=0.92, hole_spacing_mm=0.95)
        return _orig(m, rec, gsel, gmask, paths, PX_, **kw)
    PP._ghost = ghost2
    out = out or os.path.join(bkit.AAA, 'prod', 'f899', 'maps_v2')
    gw = [s['group'] for s in slips]
    tide = [dict(c=[118.0 + DX, 318.0], r_mm=58.0, aspect=1.5, seed=5), dict(c=[560.0 + DX, 150.0], r_mm=36.0, aspect=1.3, seed=8)]
    paths = c.finish(out, sheet='war', ground_without=gw, tide=tide, age_density=0.9,
                     meta=dict(scene='prod/f899/src/scene_war.py', slips=slips, thread=dict(y=Y_RULE_TOP), dx=DX))
    json.dump(dict(slips=slips, sheet_mm=SHEET_MM), open(os.path.join(out, 'war_slips.json'), 'w'), indent=1)
    return paths


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--px', type=float, default=10.0)
    ap.add_argument('--out', default=None)
    ap.add_argument('--only', type=int, nargs='*', default=None)
    ap.add_argument('--parts', default='front,far,field,hills,sky,border')
    a = ap.parse_args()
    t0 = time.time()
    print(build(a.px, a.out, only=a.only, parts=tuple(a.parts.split(','))))
    print(f'built in {time.time() - t0:.1f}s')
