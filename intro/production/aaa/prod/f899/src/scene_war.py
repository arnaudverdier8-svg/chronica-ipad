"""S12 'war' kit sheet (frieze section 3), v3: the war strip in the Bayeux idiom, built on a bkit Canvas.

v3 (director rework of the v2 proof, 'chaotic: too many small figures, ghost-dot noise, airbrushed sky, no focal point'):
  * FIVE standing front-rank figures (layout_v3.FRONT; record groups 'slip0..4', the Eevee slips are cut from them) face each other across a clear
    central gap: the legion's crimson left (facing right), the merchants' blue right (facing left); the focal pair (crimson rider x blue spearman) sits
    right of centre.  Everything behind them lies FLAT in the cloth as a Bayeux frieze row (layout_v3.FLAT_A on the near ground line, FLAT_B on the far ridge):
    stitched, not standing, no footprints.
  * Figures: laid + couched fills, couched 2-ply outline CORDS (tied down every ~3 mm) with stem stitch for the short inner lines, bare-linen flesh
    (faces, hands, legs) whose features (eyes, brows, nose, mouth) are traced in stem stitch from the card's dark marks, couched-gold crosses on the crimson shields.
  * Sky: laid-and-couched horizontal BANDS (woad-grey, buff, madder; no violet) with visible couching bars (jittered 5-7 mm), thin linen slivers and ragged,
    wavering band edges (underdrawn); no gradient, no clouds.
  * Footprints only under the standing figures (sparse small needle holes, protected linen, red-brown underdrawing, snipped thread ends lying in the weave);
    nothing under the flat figures.
  * Ground: a few tuft clusters, turf lines under the standing feet, two ridges (far / near) carrying the two flat rows, the upper border (hem, gold
    chronicle thread, compartments, confronted lions, sprigs) as in v2.

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
import layout_v3 as LAY                                               # noqa
from chron.color import hex_lin, lin2oklab, oklab2lin                 # noqa
from chron import stitch as S                                         # noqa
from chron.stitch import CTX                                          # noqa
from chron.record import OUTLINE_REGION                               # noqa
from chron.util import vnoise                                         # noqa
from chron.config import WOOL                                         # noqa

DX = 30.0                                  # frame shift of the border / hill elements (kept from v2); the figure layout is in final sheet mm
SHEET_MM = (660.0, 345.0)
Y_RULE_TOP, Y_RULE_BOT = 17.5, 77.5
SKY_Y0, SKY_Y1 = LAY.SKY_Y0, LAY.SKY_Y1
RED, REDD, BLUE, BLUED = LAY.RED, LAY.REDD, LAY.BLUE, LAY.BLUED
GOLD_CROSS = dict(kind='cross')
FRONT, FLAT_A, FLAT_B = LAY.FRONT, LAY.FLAT_A, LAY.FLAT_B

# the sky, top -> horizon: (name, hex, thickness mm, bar contrast: +lighter / -darker OKLab L).  Woad-grey (cold, high), buff glints, madder (warm, low).
SKY_BANDS = [('woad_d', '#324559', 11.0, +0.07), ('woad', '#4E687F', 8.0, +0.065), ('buff', '#B4A17F', 3.6, -0.06), ('woad_l', '#6F8597', 9.5, +0.065),
             ('madder_d', '#68382F', 8.5, +0.07), ('buff', '#BAA37F', 5.4, -0.06), ('terra', '#8F5040', 11.5, -0.055), ('buff', '#C4AB86', 3.8, -0.06),
             ('madder_l', '#A2594A', 9.5, -0.055), ('glow', '#CDB693', 9.0, -0.06)]
TUFT_COLS = ['forest', 'olive', 'moss', 'sage', '#5F6B5A', '#7C6E3F', '#46563A']


def wavy(x0, x1, y, amp, wl, seed, n=120):
    xs = np.linspace(x0, x1, n)
    r = np.random.default_rng(seed)
    ph = r.uniform(0, 6.28, 3)
    ys = y + amp * (0.6 * np.sin(xs / wl * 6.283 + ph[0]) + 0.3 * np.sin(xs / (wl * 0.43) * 6.283 + ph[1]) + 0.1 * np.sin(xs / (wl * 0.17) * 6.283 + ph[2]))
    return np.stack([xs, ys], 1).astype(np.float32)


# ------------------------------------------------------------------ sky: laid-and-couched bands
def shift_L(hexcol, dL, cscale=0.92):
    lab = lin2oklab(hex_lin(hexcol)[None])[0].copy()
    lab[0] = float(np.clip(lab[0] + dL, 0.05, 0.92)); lab[1] *= cscale; lab[2] *= cscale
    return oklab2lin(lab[None])[0]


def build_sky(c):
    """ten horizontal bands of laid wool, couched across with visible bars; every band edge wanders on its own (amplitude 0.8-1.9 mm, three scales), the
    bands are stitched from the horizon upward and clipped by what is in front; a faint red-brown underdrawing line follows each edge."""
    W = c.w_mm
    thick = np.array([b[2] for b in SKY_BANDS], np.float64) * np.random.default_rng(31).uniform(0.82, 1.2, len(SKY_BANDS))
    tops = np.concatenate([[SKY_Y0], SKY_Y0 + np.cumsum(thick) * (SKY_Y1 - SKY_Y0) / thick.sum()])
    n = 460
    edges = []
    for i, y in enumerate(tops):
        r = np.random.default_rng(900 + i)
        amp = r.uniform(0.9, 1.9) * (0.35 if i == 0 else 1.0)
        e = wavy(-8, W + 8, y, amp, r.uniform(38.0, 85.0), 910 + i, n=n)
        e[:, 1] += 0.55 * G.noise1(n, 9.0, 930 + i)
        edges.append(e)
    r = np.random.default_rng(88)
    for k in range(len(SKY_BANDS) - 1, -1, -1):                     # horizon first
        name, hx, th, dL = SKY_BANDS[k]
        top = edges[k]; bot = edges[k + 1] + np.array([0, 0.5 if k < len(SKY_BANDS) - 1 else 0.0], np.float32)
        poly = np.vstack([top, bot[::-1]]).astype(np.float32)
        win = c.win_of_polys([poly], 3.0)
        mk = c.mask([poly], win).astype(bool)
        mid = np.stack([top[:, 0], 0.5 * (top[:, 1] + bot[:, 1])], 1).astype(np.float32)
        fld = M._field_along(c, win, [mid], 6.0)
        col = hex_lin(hx)
        barc = shift_L(hx, 0.72 * dL)
        # the couching bars lean in drifting patches (a hand ties a run of bars at one slant, then another): +-14 deg slow drift + 5 deg ripple, never ruler-straight
        xs_ = ((np.arange(win[2] - win[0], dtype=np.float32) + win[0] + 0.5) / c.PX)[None, :]
        ph = r.uniform(0, 6.28, 3)
        th = np.radians(90.0 + 11.0 * np.sin(xs_ / 43.0 + ph[0]) + 6.0 * np.sin(xs_ / 14.0 + ph[1]) + 3.0 * np.sin(xs_ / 5.3 + ph[2]))
        th = np.broadcast_to(th, (win[3] - win[1], win[2] - win[0]))
        bfld = (np.cos(2 * th).astype(np.float32), np.sin(2 * th).astype(np.float32))
        c.fill(mk, win, col, field=fld, couch=dict(r_mm=0.36, hamp=0.33), bar_spacing=float(r.uniform(5.4, 8.6)), tie=float(r.uniform(4.2, 5.8)), bar_jitter=9.0,
               bar_field=bfld, seed=980 + k, group=None, name=f'sky_{name}', erode=(0.10, 0.34), pitch=0.84, maxturn_deg=24, maxlen=150, model=0.0, grad=0.0,
               nlots=5, lot_spread=0.085, bar_col=barc, tie_col=barc * 0.9, h0=0.05, hamp=0.40, minlen=1.0, r_fac=0.58)
        c.underdraw(np.stack([top[:, 0], top[:, 1] - 0.5], 1)[10:-10:2], 0.30, width_mm=0.35, seed=950 + k)
    return tops


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


def tuft_clusters(c, seed, region, n_clusters, near=None, avoid=None):
    """Neyman-Scott clumps of tufts: varied height (2.2-6.6 mm), lean, blade count and colour; a few singles; more near the feet.  `avoid`: [(x0,y0,x1,y1)]."""
    r = np.random.default_rng(seed)
    x0, y0, x1, y1 = region
    cols = TUFT_COLS
    pts = []
    for k in range(n_clusters):
        px_, py_ = r.uniform(x0, x1), r.uniform(y0, y1)
        n = int(r.integers(2, 6)); sig = r.uniform(4.0, 10.0)
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
        if avoid and any(a0 < x < a2 and a1 < y < a3 for (a0, a1, a2, a3) in avoid):
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


def snipped_ends(c, info, seed, n=11, min_gap=7.0):
    """the threads of the figure that stood up were snipped, not pulled: short curled ends of the figure's own wool still lie in the weave of its footprint
    (group 0 = ground, so they stay in the ground sheet).  Poisson-thinned inside the silhouette, colour from the card at that spot."""
    PX = c.PX
    sil = info['sil']; lin = info['lin']; ox, oy = info['ox'], info['oy']
    Hc, Wc = sil.shape
    inner = cv2.erode(sil.astype(np.uint8), np.ones((int(1.2 * PX) | 1, int(1.2 * PX) | 1), np.uint8)) > 0
    ys, xs = np.nonzero(inner)
    if len(xs) == 0:
        return 0
    r = np.random.default_rng(seed)
    order = r.permutation(len(xs))
    kept = []
    for i in order:
        p = np.array([xs[i], ys[i]], np.float32) / PX
        if all(np.hypot(*(p - q)) > min_gap * r.uniform(0.8, 1.3) for q in kept):
            kept.append(p)
        if len(kept) >= n:
            break
    CTX['group'] = 0; CTX['region'] = 0; CTX['unit'] = -1
    for k, p in enumerate(kept):
        ix, iy = int(p[0] * PX), int(p[1] * PX)
        patch = lin[max(iy - 6, 0):iy + 7, max(ix - 6, 0):ix + 7].reshape(-1, 3)
        col = np.clip(np.median(patch, 0) * r.uniform(1.0, 1.35), 0.04, 0.9)       # lighter than the dark cords: a thread end, not a speck
        L = r.uniform(1.6, 3.8)
        a0 = r.uniform(0, 2 * math.pi); curl = r.uniform(-1.8, 1.8)
        t = np.linspace(0, 1, 12)
        ang = a0 + curl * t
        d = np.stack([np.cos(ang), np.sin(ang)], 1)
        pts = p[None] + np.cumsum(d * (L / 12), 0)
        pts = np.vstack([p[None], pts]) + np.array([ox, oy], np.float32) / PX
        S.put(c.m, (pts * PX).astype(np.float32), col.astype(np.float32), r.uniform(0.15, 0.21), 0.36, 0.20, WOOL, ply_mm=0.5,
              taper_mm=0.6, tw_deg=25, seed=seed + k, cov=0.6, hbias=0.1, kind=S.K_STEM)
    return len(kept)


# ------------------------------------------------------------------ build
def build(PX=10.0, out=None, verbose=True, parts=('front', 'far', 'field', 'hills', 'sky', 'border'), only=None):
    c = Canvas(*SHEET_MM, PX=PX, seed=899, linen_seed=0, name='war', frieze_origin_mm=(1800.0, 0.0), verbose=verbose)
    W_mm, H_mm = SHEET_MM
    slips = []
    out = out or os.path.join(bkit.AAA, 'prod', 'f899', 'maps')
    os.makedirs(out, exist_ok=True)
    infos = []
    # ======================= front ranks (record groups slip0..)
    if 'front' in parts:
        c.say('front ranks')
        occ_union = c.occ.copy(); occ_base = c.occ.copy()
        for k, (unit, pose, realm, x, y, ppm, yaw, tilt) in enumerate(FRONT):
            if only is not None and k not in only:
                continue
            team, deep = LAY.realm_cols(realm)
            card = F.load_card(unit, pose, team, flip=(realm == 'B'), shield=team, deep_hex=deep, sat=1.22 + 0.03 * (k % 3), val=0.96 + 0.02 * (k % 4))
            shc = GOLD_CROSS if realm == 'R' else dict(kind='chevron', col='#D6BE86')
            gname = f'slip{k}'
            c.occ = occ_base.copy()                 # slips may overlap each other on the sheet: each is stitched whole
            info = F.embroider(c, card, x, y, ppm=ppm, group=gname, seed=100 + k, shield_cross=shc, name=f'{unit}{k}', outline_mode='tonal', fill_pitch=0.74,
                               gap_prob=0.0, skin_mode='bare', cord_outline=True, cord_w=1.0, cord_tie=3.0, outline_w=1.0)
            occ_union |= c.occ
            np.savez_compressed(os.path.join(out, f'slipmask_{gname}.npz'), sil=info['sil'], skin=info['skin'], ox=info['ox'], oy=info['oy'])
            info['lin'] = None
            slips.append(dict(group=gname, unit=unit, pose=pose, realm=realm, x_mm=x, y_mm=y, flip=(realm == 'B'), bbox_mm=info['bbox_mm'], ppm=ppm,
                              yaw=yaw, tilt=tilt))
            infos.append((gname, info, card))
            c.say(gname, unit, info['regions'], 'regions', info['features'], 'feature strokes', [round(v, 1) for v in info['bbox_mm']])
        c.occ = occ_union
    # ======================= flat rows (lying in the cloth: Bayeux frieze)
    if 'far' in parts:
        for rank, ROW in (('A', FLAT_A), ('B', FLAT_B)):
            for k, (unit, pose, realm, x, y, sc) in enumerate(ROW):
                team, deep = LAY.realm_cols(realm)
                card = F.load_card(unit, pose, team, flip=(realm == 'B'), shield=team, deep_hex=deep, sat=1.10, val=0.94)
                shc = GOLD_CROSS if realm == 'R' else dict(kind='chevron', col='#D6BE86')
                F.embroider(c, card, x, y, ppm=5.0 / sc, group=None, seed=300 + k + (50 if rank == 'B' else 0), shield_cross=shc, name=f'flat{rank}{k}',
                            outline_w=0.9 if rank == 'A' else 0.8, hamp_mul=0.8, outline_mode='tonal', gap_prob=0.0, skin_mode='bare', cord_outline=True,
                            cord_w=0.85, cord_tie=2.6, cord_min_mm=5.0, feat_w=0.46, fill_pitch=0.8)
            c.say('flat row', rank)
    # ======================= field: turf lines under the standing figures, a few tuft clusters on the bare linen
    if 'field' in parts:
        c.say('field')
        for k, (unit, pose, realm, x, y, ppm, yaw, tilt) in enumerate(FRONT):
            wf = {'legionary': 70, 'knight': 118, 'mercenary': 62, 'man_at_arms': 60, 'spearman': 78, 'horse_archer': 88, 'archer': 52}[unit] * 5.0 / ppm * 0.9
            turf_line(c, x, y + 2.4, wf, 900 + k, cols=('moss', 'ochre2') if k % 2 else ('olive', 'clay'))
        near = [(x, y + 8, 3) for (_, _, _, x, y, _, _, _) in FRONT]
        n = tuft_clusters(c, 21, (14.0, 245.0, W_mm - 14.0, H_mm - 3.0), 13, near=near)
        c.say('tufts', n)
    # ======================= ridges: far (carries FLAT_B) and near (carries FLAT_A), closed mounds with hatched interiors
    if 'hills' in parts:
        c.say('hills')
        M.hill(c, M.ridge_contour(-45, W_mm + 45, 188.0, bumps=[(55 + DX, 70, 16, 1.3), (200 + DX, 55, 11, 1.4), (335 + DX, 90, 15, 1.2), (475 + DX, 60, 12, 1.4),
                                                                (600 + DX, 70, 15, 1.3)],
                                  waves=((1.4, 73.0, 2.1),), y_foot=None), [(3.8, 'woad_pale'), (3.4, 'slate'), (3.4, 'olive')], seed=241,
               interior='#7B8660', interior_angle=62.0, interior_couch=False, interior_depth=14.0, interior_style='split', interior_L=5.0,
               bar_jitter=8.0, bar_spacing=6.0, interior_model=0.10, interior_grad=0.12)
        M.hill(c, M.ridge_contour(-45, W_mm + 45, 228.0, bumps=[(105 + DX, 62, 9, 1.3), (250 + DX, 46, 7, 1.5), (400 + DX, 72, 10, 1.2), (545 + DX, 56, 8, 1.4)],
                                  waves=((1.2, 61.0, 0.7),), y_foot=None), [(3.6, 'olive'), (3.2, 'moss'), (3.4, 'sage')], seed=240,
               outline=None, y_cut=None, interior='#9AA36E', interior_angle=-24.0, interior_couch=False, interior_depth=12.0, interior_style='split', interior_L=6.0,
               bar_jitter=8.0, bar_spacing=6.0, interior_model=0.10, interior_grad=0.12)
    # ======================= sky: laid-and-couched bands
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
    # ======================= snipped thread ends in the footprints (ground group, after everything)
    nsn = 0
    for gname, info, card in infos:
        if info.get('sil') is None:
            continue
        # card colours at canvas resolution for the stub colour
        lin_c = cv2.resize(card['lin'], (info['sil'].shape[1], info['sil'].shape[0]), interpolation=cv2.INTER_AREA)
        info['lin'] = lin_c
        nsn += snipped_ends(c, info, 7000 + int(gname[4:]))
    c.say('stitching done; snipped ends', nsn)
    # footprints: SPARSE needle holes at the real strand ends + faint red-brown underdrawing of each slip's outline + protected linen (v3: only behind the standing figures)
    import chron.motifs.panel as PP
    from ghost_v3 import ghost_v3 as _orig

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
        kw.update(ud_alpha=0.55, hole_spacing_mm=2.0)
        return _orig(m, rec, gsel, gmask, paths, PX_, **kw)
    PP._ghost = ghost2
    gw = [s['group'] for s in slips]
    tide = [dict(c=[118.0 + DX, 318.0], r_mm=48.0, aspect=1.5, seed=5), dict(c=[560.0 + DX, 150.0], r_mm=30.0, aspect=1.3, seed=8)]
    paths = c.finish(out, sheet='war', ground_without=gw, tide=tide, age_density=0.55,
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
