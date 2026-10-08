"""S12 'war' kit sheet (frieze section 3): the war strip in the Bayeux idiom, built on a bkit Canvas.

Sheet 600 x 345 mm (frieze mm = sheet mm).  Contents (front -> back):
  * 8 front-rank figures from the game cards (strike poses, Legion crimson facing right, merchants' blue facing left), each its own
    record group 'slip0..7': the sheet's _ground copy carries their footprints (protected linen, needle holes, underdrawing); the full
    sheet is where the Eevee slips are cut from (exactly the figures that lay there);
  * two ranks of flat figures farther up the cloth (idle / strike cards at 0.66 and 0.5 scale, colours alternating);
  * bare linen field with grass tufts, two hillock bands, a madder-and-woad-grey banded dusk sky (no violet);
  * the upper border of the frieze: hem + nail holes, the gold chronicle thread (couched pair, whole width), compartments with
    diagonal bars, the two confronted game lions, sprigs.

    python3 scene_war.py [--px 10] [--out DIR]
"""
import os, sys, json, time, math, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bkit                                                           # noqa
import numpy as np, cv2                                               # noqa
from bkit.canvas import Canvas                                        # noqa
from bkit import motifs as M, geom as G                               # noqa
import figure as F                                                    # noqa
from chron.color import hex_lin                                       # noqa
from chron import stitch as S                                         # noqa

SHEET_MM = (600.0, 380.0)
Y_RULE_TOP, Y_RULE_BOT = 17.5, 77.5
RED, REDD, BLUE, BLUED = '#A3181A', '#6E2428', '#2F5F9E', '#2D4460'
GOLD_CROSS = dict(kind='cross')

# front rank (nearest first): unit, pose, realm, x (feet centre), y (feet), card px/mm
BASE_PPM = 5.6        # card px per mm: legionary 63 x 86 mm, knight 109 x 114 mm, spearman 71 x 100 mm (hero scale; the register is 267 mm tall)
FRONT = [  # nearest first (stitched front to back)
    ('man_at_arms',  'strike', 'B', 392.0, 318.0),
    ('legionary',    'strike', 'R', 262.0, 316.0),
    ('spearman',     'strike', 'B', 536.0, 310.0),
    ('legionary',    'strike', 'R',  90.0, 306.0),
    ('horse_archer', 'strike', 'B', 462.0, 296.0),
    ('knight',       'strike', 'R', 186.0, 290.0),
    ('mercenary',    'strike', 'R', 328.0, 288.0),
]
# far ranks (flat in the cloth): unit, pose, realm, x, y, scale (relative to the front rank)
FAR_A = [('legionary', 'idle', 'R', 40, 246, .62), ('knight', 'idle', 'R', 118, 249, .56), ('legionary', 'strike', 'R', 208, 247, .62),
         ('mercenary', 'idle', 'R', 276, 244, .62), ('spearman', 'idle', 'B', 348, 246, .62), ('man_at_arms', 'idle', 'B', 432, 248, .62),
         ('horse_archer', 'idle', 'B', 508, 249, .56), ('archer', 'strike', 'B', 566, 246, .62)]
FAR_B = [('knight', 'strike', 'R', 66, 222, .46), ('horse_archer', 'strike', 'B', 148, 222, .46), ('knight', 'idle', 'R', 232, 220, .46),
         ('horse_archer', 'idle', 'B', 312, 221, .46), ('knight', 'strike', 'R', 388, 221, .46), ('horse_archer', 'strike', 'B', 470, 222, .46),
         ('knight', 'idle', 'R', 548, 221, .46)]

SKY = [  # (y_top, height, colour, n_segments)  top -> horizon : woad-grey, dusk, madder, ember terracotta (no violet, no yellow)
    (84.0, 10.5, '#46607A', 1), (96.5, 12.5, '#566B80', 1), (110.5, 11.0, '#5F7283', 2), (123.0, 10.0, '#6C7176', 2),
    (134.5, 13.0, 'dusk_sky', 1), (149.0, 12.0, 'madder', 2), (163.0, 11.5, 'madder_lt', 3), (176.0, 8.5, 'terracotta', 3),
    (186.0, 6.0, '#C98A5E', 2)]
PALX = dict(dusk_sky='#6A3A38')


def col(c):
    return PALX.get(c, c)


def wavy(x0, x1, y, amp, wl, seed, n=120):
    xs = np.linspace(x0, x1, n)
    r = np.random.default_rng(seed)
    ph = r.uniform(0, 6.28, 3)
    ys = y + amp * (0.6 * np.sin(xs / wl * 6.283 + ph[0]) + 0.3 * np.sin(xs / (wl * 0.43) * 6.283 + ph[1]) + 0.1 * np.sin(xs / (wl * 0.17) * 6.283 + ph[2]))
    return np.stack([xs, ys], 1).astype(np.float32)


def sky_band(c, y0, hgt, colr, seed, group=None, gap_hi=0.0, nseg=1):
    W = c.w_mm
    r = np.random.default_rng(seed)
    hgt = hgt * r.uniform(0.9, 1.12)
    cuts = [-8.0, W + 8.0]
    if nseg > 1:
        pos = np.sort(r.uniform(40, W - 40, nseg - 1))
        cuts = [-8.0]
        for q in pos:
            cuts += [q - r.uniform(3, 9), q + r.uniform(3, 9)]
        cuts += [W + 8.0]
    top_full = wavy(-8, W + 8, y0, 0.9, 71.0, seed, n=420)
    bot_full = wavy(-8, W + 8, y0 + hgt - gap_hi, 1.1, 53.0, seed + 1, n=420)
    mid_full = wavy(-8, W + 8, y0 + 0.5 * hgt, 0.9, 71.0, seed + 2, n=420)
    ink = M.ink_for(M.P(col(colr)))
    for j in range(0, len(cuts), 2):
        xa, xb = cuts[j], cuts[j + 1]
        sel = (top_full[:, 0] >= xa) & (top_full[:, 0] <= xb)
        top, bot, mid = top_full[sel], bot_full[sel], mid_full[sel]
        if len(top) < 6:
            continue
        poly = np.vstack([top, bot[::-1]]).astype(np.float32)
        win = c.win_of_polys([poly], 3.0)
        mk = c.mask([poly], win).astype(bool)
        fld = M._field_along(c, win, [mid], 5.0)
        c.fill(mk, win, M.P(col(colr)), field=fld, couch=True, bar_spacing=4.5, tie=4.0, seed=seed + 11 * j, group=group, name='sky',
               erode=(0.25, 0.4), maxturn_deg=30, model=0.06, grad=0.05, maxlen=90, nlots=4, lot_spread=0.07)
        c.outline_mm(top, ink, width=0.95, L=3.0, seed=seed + 3 + j, group=group, clip=True)
        c.outline_mm(bot, ink, width=0.95, L=3.0, seed=seed + 4 + j, group=group, clip=True)
        if xa > 0 or xb < W:      # ends: stem strokes closing the band
            for xe, ta in ((xa, top[0]), (xb, top[-1])):
                if 0 < xe < W:
                    i = 0 if xe == xa else -1
                    c.outline_mm(np.array([top[i], bot[i]], np.float32), ink, width=0.9, L=2.4, seed=seed + 9 + j, group=group, clip=True)


def build(PX=10.0, out=None, verbose=True, only=None, no_far=False, no_sky=False):
    c = Canvas(*SHEET_MM, PX=PX, seed=899, linen_seed=0, name='war', frieze_origin_mm=(1800.0, 0.0), verbose=verbose)
    W_mm, H_mm = SHEET_MM
    slips = []
    # ======================= front rank (record groups slip0..)
    c.say('front rank')
    for k, (unit, pose, realm, x, y) in enumerate(FRONT):
        if only is not None and k not in only:
            continue
        team, deep = (RED, REDD) if realm == 'R' else (BLUE, BLUED)
        card = F.load_card(unit, pose, team, flip=(realm == 'B'), shield=team, deep_hex=deep)
        shc = GOLD_CROSS if realm == 'R' else dict(kind='chevron', col='#D6BE86')
        gname = f'slip{k}'
        info = F.embroider(c, card, x, y, ppm=BASE_PPM, group=gname, seed=100 + k, shield_cross=shc, name=f'{unit}{k}')
        slips.append(dict(group=gname, unit=unit, pose=pose, realm=realm, x_mm=x, y_mm=y, flip=(realm == 'B'), bbox_mm=info['bbox_mm'],
                          ppm=BASE_PPM))
        c.say(gname, unit, info['regions'], 'regions', [round(v, 1) for v in info['bbox_mm']])
    # ======================= far ranks (flat)
    if not no_far:
        for rank, FAR in (('A', FAR_A), ('B', FAR_B)):
            for k, (unit, pose, realm, x, y, sc) in enumerate(FAR):
                team, deep = (RED, REDD) if realm == 'R' else (BLUE, BLUED)
                card = F.load_card(unit, pose, team, flip=(realm == 'B'), shield=team, deep_hex=deep)
                shc = GOLD_CROSS if realm == 'R' else dict(kind='chevron', col='#D6BE86')
                F.embroider(c, card, x, y, ppm=BASE_PPM / sc, group=None, seed=300 + k + (50 if rank == 'B' else 0), shield_cross=shc,
                            name=f'far{rank}{k}', outline_w=0.9 if rank == 'A' else 0.8)
            c.say('far rank', rank)
    # ======================= field: grass tufts on bare linen (below the far ranks)
    c.say('field tufts')
    fy0, fy1 = 250.0, H_mm - 2.0
    win = c.win_px(0, fy0 * PX, c.W, fy1 * PX)
    mk = np.ones((win[3] - win[1], win[2] - win[0]), np.uint8)
    M.scatter_tufts(c, mk, win, spacing=26.0, seed=21, col='forest', group=None, size=(3.4, 5.6), margin=3.0, jitter=0.5)
    M.scatter_tufts(c, mk, win, spacing=30.0, seed=22, col='olive', group=None, size=(3.0, 4.8), margin=3.0, jitter=0.5)
    # ======================= hillocks (two ridges, banded, linen below)
    c.say('hills')
    M.hill(c, M.ridge_contour(-45, W_mm + 45, 235.0, bumps=[(120, 90, 8, 1.2), (340, 130, 7, 1.0), (520, 80, 9, 1.3)],
                              waves=((1.2, 61.0, 0.7),), y_foot=H_mm), [(4.2, 'forest'), (3.6, 'olive'), (3.8, 'moss')], seed=240,
           outline=None, y_cut=None)
    M.hill(c, M.ridge_contour(-45, W_mm + 45, 213.0, bumps=[(60, 80, 10, 1.1), (260, 110, 8, 1.2), (470, 100, 11, 1.1)],
                              waves=((1.4, 73.0, 2.1),), y_foot=H_mm), [(4.5, 'woad_dark'), (4.0, 'slate'), (3.8, 'forest')], seed=241)
    # ======================= sky
    if not no_sky:
        c.say('sky')
        for k, (y0, h, cc, ns) in enumerate(SKY):
            sky_band(c, y0, h, cc, 500 + 7 * k, gap_hi=2.6 if k % 2 == 0 else 1.6, nseg=ns)
    # ======================= border: hem, nail holes, gold chronicle thread, compartments
    c.say('border')
    c.hem(11.0, 0.0, seed=3, run_y_mm=9.3)
    c.nail_hole(172.0, 5.4, seed=11)
    c.nail_hole(438.0, 5.7, seed=12)
    xs = np.linspace(-4.0, W_mm + 4.0, 420)
    ys = Y_RULE_TOP + 0.12 * np.sin(xs / 31.0) - 0.4 * (xs / W_mm) + 0.05 * np.sin(xs / 7.3)
    thr = np.stack([xs, ys], 1).astype(np.float32)
    ties = list(np.arange(5.0, W_mm, 6.5) + np.random.default_rng(4).uniform(-0.8, 0.8, len(np.arange(5.0, W_mm, 6.5))))
    c.metal_pair(thr, ties_s_mm=ties, tie_col='#8A2A1C', group='thread', seed=7, tie_len_mm=2.4, tie_r=0.27, thread_r=0.31, sep_mm=0.64,
                 gold=np.array([0.78, 0.46, 0.115], np.float32))
    c.occlude_polys([G.band(thr, -1.2, 1.2)])
    c.underdraw(np.array([(0, Y_RULE_TOP + 0.15), (W_mm, Y_RULE_TOP - 0.25)]), 0.85, width_mm=0.45, seed=11)
    bars_x = [30.0, 108.0, 176.0, 303.0, 386.0, 446.0, 518.0, 592.0]
    M.beast(c, 'red', (228.0, 25.0, 292.0, 72.5), flip=False, seed=31, group='border')
    M.beast(c, 'blue', (318.0, 25.5, 378.0, 72.5), flip=False, seed=32, group='border')
    spr = [(69.0, ('woad', 'terracotta'), 2, -0.1), (142.0, ('terracotta', 'mustard'), 1, 0.15), (203.0, ('madder', 'woad'), 1, 0.1),
           (412.0, ('woad',), 1, -0.15), (482.0, ('terracotta', 'woad'), 2, 0.1), (555.0, ('mustard', 'madder'), 1, -0.05)]
    for k, (sx, fc, nf, ln) in enumerate(spr):
        M.sprig(c, sx, 73.0, 40.0 + 4 * ((k * 7) % 3), flower_cols=fc, seed=50 + k, group='border', lean=ln, n_flowers=nf)
    bar_cols = ['madder', 'olive', 'woad', 'terracotta', 'mustard', 'sage', 'woad', 'madder']
    for k, bx in enumerate(bars_x):
        M.diag_bar(c, bx, Y_RULE_TOP + 1.8, Y_RULE_BOT - 1.6, slant=(1 if k % 2 else -1), col=bar_cols[k], seed=70 + k, group='border', lean_mm=17.0)
    M.border_rules(c, 0.0, W_mm, Y_RULE_BOT, seed=7, group='border')
    c.say('stitching done')
    # footprints: needle holes at the real strand ends + red-brown underdrawing of each slip's outline + protected linen
    import chron.motifs.panel as PP
    _orig = PP._ghost

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
        kw.update(ud_alpha=1.0, hole_spacing_mm=0.8)
        return _orig(m, rec, gsel, gmask, paths, PX_, **kw)
    PP._ghost = ghost2
    out = out or os.path.join(bkit.AAA, 'prod', 'f899', 'maps')
    gw = [s['group'] for s in slips]
    tide = [dict(c=[88.0, 318.0], r_mm=58.0, aspect=1.5, seed=5), dict(c=[560.0, 150.0], r_mm=36.0, aspect=1.3, seed=8)]
    paths = c.finish(out, sheet='war', ground_without=gw, tide=tide, age_density=0.9,
                     meta=dict(scene='prod/f899/src/scene_war.py', slips=slips, thread=dict(y=Y_RULE_TOP)))
    json.dump(dict(slips=slips, sheet_mm=SHEET_MM), open(os.path.join(out, 'war_slips.json'), 'w'), indent=1)
    return paths


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--px', type=float, default=10.0)
    ap.add_argument('--out', default=None)
    ap.add_argument('--only', type=int, nargs='*', default=None)
    ap.add_argument('--nofar', action='store_true')
    ap.add_argument('--nosky', action='store_true')
    a = ap.parse_args()
    t0 = time.time()
    print(build(a.px, a.out, only=a.only, no_far=a.nofar, no_sky=a.nosky))
    print(f'built in {time.time() - t0:.1f}s')
