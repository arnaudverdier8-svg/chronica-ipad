"""S02 'One realm' kit sheet = frieze section 1 (v2): 800 x 440 mm.  The upper border with the gold chronicle thread, its first
crimson tie-down and the confronted vignette lions; the one realm in Bayeux idiom (hillock bands, paired-line river under
a stone arch bridge, ploughed strips, a far ridge, four unequal towns re-stitched from settle_1 / settle_1_2 / settle_2 +
hand-drawn hamlet, the crowned capital on a padded rise) and ONE road couched in the four house colours.

Coordinates: LOCAL = the f91 composition coordinates (the f91 window is local x 40-552, y 5-293; the 4:3 safe zone is local
x 104-488); SHEET = LOCAL + (OX, 0).  OX = 128 mm of landscape is added on the left so the F0 landing frame (776 x 436 mm,
sheet x 12-788, y 2-438) lies inside the sheet and the capital sits at ~0.60 of it; the cloth ends in a bottom hem at y 440.

    python3 scene_f91.py [--px 7] [--ext] [--out <maps dir>] [--name k1_realm]
      --ext  also stitch the part outside the f91 window (left margin, right continuation, foreground to the lower rules, T1 stub)
"""
import os, sys, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(os.path.dirname(HERE), 'kit')
sys.path.insert(0, KIT)
import bkit                                   # noqa: E402  (sets lib path, threads)
import numpy as np, cv2                       # noqa: E402
from bkit.canvas import Canvas               # noqa: E402
from bkit import motifs as M, geom as G      # noqa: E402

SHEET_MM = (800.0, 440.0)
OX = 128.0                 # SHEET x = LOCAL x + OX
FRIEZE_ORIGIN = (0.0, 0.0)
Y_RULE_TOP = 17.5          # top rule of the upper border = the path of the gold chronicle thread
Y_RULE_BOT = 77.5          # border / main register rules
Y_RULE_LOW = 375.0         # lower register rules (visible at F0 only)
THREAD = dict(x0=122.0, x1=672.0, tie_s=8.0)     # LOCAL: needle hole x0 (frame px 410), first tie-down at x0 + 8 (frame px 450)
FRAME_X0 = 40.0            # LOCAL x of the f91 frame's left edge


def sh(p, dx=None):
    """LOCAL -> SHEET: shift an array of points (n, 2) / a tuple list in x."""
    a = np.array(p, np.float32).copy()
    a[..., 0] += OX if dx is None else dx
    return a


def X(x):
    return x + OX


# towns: (models, x centre, y base, width, pennant colour, style, vstretch)  -- LOCAL mm
WALL_SET = dict(
    river=('stone', 'stone_warm', 'stone_dk'), hill=('stone_warm', 'sand', 'stone'), large=('stone_dk', 'stone', 'clay'))
TOWNS = dict(
    hamlet=dict(x=128.0, y=240.0, pennant='green'),
    river=dict(models='settle_1', x=224.0, y=231.0, w=76.0, vs=1.7, pennant='blue', style=dict(
        roof=('terracotta', 'ochre2', 'tile', 'madder2', 'terracotta', 'ochre2'), wall=WALL_SET['river'],
        tower=('sand', 'mustard', 'clay', 'stone'), plaster=('sand', 'stone_warm'))),
    hill=dict(models='settle_1_2', x=292.0, y=196.0, w=62.0, vs=1.7, pennant='crimson', style=dict(
        roof=('slate', 'madder2', 'moss', 'slate', 'tile'), tower=('moss', 'sand', 'mustard'), wall=WALL_SET['hill'],
        plaster=('sand', 'stone'))),
    large=dict(models='settle_2', x=450.0, y=208.0, w=76.0, vs=1.45, pennant='gold', style=dict(
        roof=('ochre2', 'tile_dk', 'mustard', 'madder2', 'ochre2', 'tile'), tower=('sand', 'mustard', 'clay', 'stone'),
        wall=WALL_SET['large'], plaster=('sand', 'stone'))),
)
PAD_TOWN = dict(wall=(0.45, 1.8), tower=(0.70, 2.2), roof=(0.60, 2.5), plaster=(0.45, 1.8), default=(0.40, 1.5))
PAD_CAP = dict(wall=(0.80, 2.0), tower=(1.15, 2.6), roof=(0.95, 3.0), plaster=(0.8, 2.0), default=(0.7, 2.0))
CAPITAL = dict(x=362.0, y=184.0, walls_w=96.0, keep_w=38.0, walls_vs=1.28, keep_vs=0.92)
TREES = [dict(x=250.0, y=233.0, h=76.0, trunk=('terracotta', 'madder', 'terracotta'), leaves=('olive', 'sage', 'forest', 'sage', 'olive'),
              branches=('madder', 'mustard'), lean=0.0, seed=110),
         dict(x=70.0, y=216.0, h=66.0, trunk=('terracotta', 'madder', 'terracotta'), leaves=('sage', 'olive', 'forest', 'olive', 'sage'),
              branches=('madder', 'ochre2'), lean=0.03, seed=112),
         dict(x=516.0, y=222.0, h=60.0, trunk=('madder', 'clay', 'madder'), leaves=('olive', 'sage', 'forest', 'sage', 'olive'),
              branches=('terracotta', 'mustard'), lean=-0.03, seed=113),
         dict(x=418.0, y=204.0, h=70.0, trunk=('madder', 'clay', 'madder'), leaves=('sage', 'olive', 'forest', 'olive', 'sage'),
              branches=('terracotta', 'mustard'), lean=-0.02, seed=111)]
TIDE = [dict(c=[X(548.0), 300.0], r_mm=62.0, aspect=1.5, seed=5), dict(c=[X(-70.0), 330.0], r_mm=40.0, aspect=1.3, seed=6)]

ROAD = [(-132, 264.0), (-82, 258.0), (-30, 251.0), (30, 247.0), (90, 244.8), (130, 243.8), (170, 243.4), (206, 240.0), (238, 236.0),
        (262, 231.0), (284, 223.0), (304, 217.0), (322, 207.0), (338, 197.0), (352, 190.0), (362, 187.0), (378, 188.0),
        (398, 194.0), (416, 203.0), (440, 213.0), (470, 218.0), (520, 222.0), (580, 227.0), (640, 232.0), (676, 236.0)]
RIVER = [(168, 176), (164, 198), (168, 222), (170, 243), (173, 264), (168, 286), (172, 308), (166, 338), (164, 372)]
BRIDGE_X = 170.0


def build(PX=7.0, out=None, preview=False, ext=False, name='k1_realm', verbose=True):
    c = Canvas(*SHEET_MM, PX=PX, seed=91, linen_seed=0, name=name, frieze_origin_mm=FRIEZE_ORIGIN, verbose=verbose)
    W_mm = SHEET_MM[0]
    XL, XR = (-128.0, 672.0) if ext else (6.0, 606.0)         # LOCAL x extent of the stitched land
    YB = 372.0 if ext else 306.0                              # bottom of the stitched land (local y)
    # ======================= top hem, nail holes (linen-level)
    c.hem(11.0, 0.0, seed=3, run_y_mm=9.3)
    c.nail_hole(X(156.0), 7.4, seed=1)
    c.nail_hole(X(404.0), 7.9, seed=2)
    if ext:
        c.nail_hole(X(-40.0), 8.1, seed=7)
        c.nail_hole(X(640.0), 7.6, seed=8)
        c.hem_bottom(429.0, seed=5, run_y_mm=431.0)
    # ======================= the gold chronicle thread: up through the linen at the needle hole, ONE crimson silk lashing, then slack
    x0, x1 = X(THREAD['x0']), X(THREAD['x1'])
    xs = np.linspace(x0, x1, 1400)
    d = xs - x0
    u = np.clip((d - 12.0) / 70.0, 0, 1); u = u * u * (3 - 2 * u)          # 0 at the tie, 1 after ~80 mm: the loose part
    ys = (Y_RULE_TOP + 0.10 * np.sin(d / 23.0) - 0.25 * (d / 144.0).clip(0, 1) + 1.9 * np.exp(-d / 4.5)
          + u * (3.1 * np.sin(d / 71.0 + 0.5) + 0.9 * np.sin(d / 19.0) + 0.9 * np.sin(d / 197.0 + 1.0) - 0.004 * (d - 12.0).clip(0, None)))
    thr = np.stack([xs, ys], 1).astype(np.float32)
    gold = np.array([0.80, 0.46, 0.115], np.float32)
    c.metal_pair(thr, ties_s_mm=[THREAD['tie_s']], tie_col='#B02A20', group='thread', seed=5, tie_len_mm=5.8, tie_r=0.40, tie_turns=3,
                 tie_pitch_mm=1.7, tail_mm=6.0, thread_r=0.55, sep_mm=1.25, gold=gold, ply_mm=1.5, ply_deg=44, hamp=0.55, h0=0.6)
    c.needle_holes([(x0 - 0.3, Y_RULE_TOP + 1.9)], r_mm=(0.30, 0.34), seed=4, depth=0.35)
    c.occlude_polys([G.band(thr, -2.2, 2.2)])
    c.underdraw(np.array([(0, Y_RULE_TOP + 0.15), (W_mm, Y_RULE_TOP - 0.25)]), 0.85, width_mm=0.45, seed=11)
    # ======================= upper border: irregular compartments, two big confronted lions, three kinds of millefleurs
    c.say('border')
    bars = [(-118, 'terracotta', -1, 4.6), (-66, 'olive', 1, 4.0), (-14, 'mustard', -1, 5.2), (38, 'woad', -1, 4.4), (96, 'madder', 1, 4.0),
            (148, 'moss', 1, 4.8), (247, 'terracotta', -1, 5.0), (346, 'olive', 1, 4.2), (402, 'mustard', -1, 5.4), (458, 'woad', 1, 4.0),
            (520, 'sand', 1, 4.6), (568, 'madder', -1, 4.2), (626, 'olive', -1, 5.0), (668, 'terracotta', 1, 4.4)]
    if not ext:
        bars = [b for b in bars if XL - 40 <= b[0] <= XR + 40]
    M.beast(c, 'red', (X(150.0), 21.0, X(238.0), 75.0), seed=21, group='border')
    M.beast(c, 'blue', (X(256.0), 21.5, X(344.0), 75.0), seed=22, group='border')
    spr = [(-92, ('woad', 'terracotta'), 2, -0.10, 'round'), (-40, ('terracotta', 'mustard'), 1, 0.15, 'bud'),
           (12, ('woad', 'madder'), 1, -0.08, 'daisy'), (67, ('mustard', 'madder'), 2, 0.10, 'round'),
           (122, ('terracotta', 'woad'), 1, -0.12, 'bud'), (374, ('madder', 'woad'), 2, 0.05, 'round'),
           (430, ('woad',), 1, -0.15, 'daisy'), (489, ('terracotta', 'woad'), 2, 0.10, 'bud'),
           (544, ('mustard', 'madder'), 1, -0.05, 'round'), (597, ('woad', 'terracotta'), 2, 0.12, 'daisy'), (647, ('mustard',), 1, 0.0, 'bud')]
    for k, (sx, fc, nf, ln, kind) in enumerate(spr):
        if not ext and not (XL - 40 <= sx <= XR + 40):
            continue
        M.sprig(c, X(sx), 73.0, 38.0 + 5 * ((k * 7) % 3), flower_cols=fc, seed=40 + k, group='border', lean=ln, n_flowers=nf, kind=kind)
    for k, (bx, col, slant, wd) in enumerate(bars):
        M.diag_bar(c, X(bx), Y_RULE_TOP + 1.8, Y_RULE_BOT - 1.6, slant=slant, width=wd, col=col, seed=60 + k, group='border', lean_mm=15.0 + 3 * ((k * 5) % 3))
    M.border_rules(c, 0.0, W_mm, Y_RULE_BOT, seed=7, group='border')
    c.occlude_polys([np.array([(0, Y_RULE_TOP - 2), (W_mm, Y_RULE_TOP - 2), (W_mm, Y_RULE_BOT + 4), (0, Y_RULE_BOT + 4)])])
    # ======================= the realm (front -> back)
    c.say('capital + crown')
    cap_res = M.town(c, [('capital', 0.0, -0.5, CAPITAL['keep_w'], CAPITAL['keep_vs']), ('walls_2', 0.0, 0.0, CAPITAL['walls_w'], CAPITAL['walls_vs'])],
                     X(CAPITAL['x']), CAPITAL['y'], CAPITAL['walls_w'], seed=71, group='capital', outline_w=0.9, skip=('gold',), model=0.14,
                     style=dict(roof=('woad', 'woad', 'woad_dark', 'woad'), tower=('sand', 'mustard', 'stone', 'sand'), wall=('stone_warm', 'sand', 'stone'),
                                plaster=('sand', 'stone_warm'), gold=('mustard',), cloth=('blue',)), pad=PAD_CAP, roof_stripe=2.0)
    # the crown rests above the keep's central parapet (measured on the stitched silhouette) and is moored to the two flanking spire tips
    px_c = int(round(X(CAPITAL['x']) * PX)); hw_k = int(0.5 * CAPITAL['keep_w'] * PX)
    col_occ = np.nonzero(c.occ[:, px_c - hw_k:px_c + hw_k].any(1))[0]
    y_top = col_occ[col_occ > int(84 * PX)].min() / PX if len(col_occ) else CAPITAL['y'] - 60
    cw = 34.0
    tg = []
    for sgn in (-1, 1):                                       # the highest stitched point on each side of the keep = the spire tips
        xa = int(round((X(CAPITAL['x']) + sgn * CAPITAL['keep_w'] * 0.12) * PX)); xb = int(round((X(CAPITAL['x']) + sgn * CAPITAL['keep_w'] * 0.75) * PX))
        xa, xb = min(xa, xb), max(xa, xb)
        sub = c.occ[int(84 * PX):int(CAPITAL['y'] * PX), xa:xb]
        rows = np.where(sub.any(0), sub.argmax(0), 10 ** 6)
        j = int(np.argmin(rows))
        if rows[j] < 10 ** 6:
            tg.append(((xa + j) / PX, int(84 * PX) / PX + rows[j] / PX - 0.8))
    c.say('crown tethers to', tg)
    yc = y_top - 6.5                                          # crown base: 6.5 mm above the spire tips (moored by two tethers)
    M.crown(c, X(CAPITAL['x']), yc, w=cw, h=21.5, seed=70, group='capital')
    if len(tg) == 2:
        M.crown_tethers(c, X(CAPITAL['x']), yc, cw, tg, seed=75, group='capital', gold=gold)
    tops = {}
    for k, (nm, T) in enumerate(TOWNS.items()):
        c.say('town', nm)
        if nm == 'hamlet':           # hand-drawn cottages + watch tower (the game's settle_0 palisade reads as hay bales in embroidery)
            tops[nm] = hamlet(c, T)
            continue
        res = M.town(c, T['models'], X(T['x']), T['y'], T['w'], seed=80 + k, group='towns', style=T['style'], pennant_col=T['pennant'],
                     vstretch=T['vs'], outline_w=0.85, pad=PAD_TOWN, roof_stripe=1.8)
        tops[nm] = res['top']
    for k, (nm, T) in enumerate(TOWNS.items()):
        tx, ty = tops[nm]
        pl = 9.0 if nm in ('hamlet', 'large') else 11.0
        M.pennant(c, tx, ty - pl, pl, T['pennant'], direction=(1 if k % 2 == 0 else -1), length=(12.0 if nm == 'hamlet' else 16.0),
                  height=(5.2 if nm == 'hamlet' else 6.6), seed=90 + k, group='pennants')
    c.say('road, bridge')
    M.road(c, [(X(a), b) for a, b in ROAD if (XL - 10 <= a <= XR + 10)], width=7.0, seed=101, group='road',
           break_x=(X(BRIDGE_X - 21.0), X(BRIDGE_X + 21.0)))
    bx, bcy = M.arch_bridge2(c, X(BRIDGE_X), 243.4, half_span=23.0, r_in=11.5, ring_w=5.0, drop=8.0, seed=95, group='bridge')
    c.say('trees')
    for T in TREES:
        M.tree(c, X(T['x']), T['y'], T['h'], trunk_cols=T['trunk'], leaf_cols=T['leaves'], branch_cols=T['branches'], seed=T['seed'], group='trees',
               lean=T['lean'])
    if ext:      # T1: the divider interlace tree (trunk banded in the four house colours), standing at the road side before the frieze continues
        M.tree(c, X(630.0), 262.0, 104.0, trunk_cols=('road_gold', 'road_crimson', 'road_blue', 'road_green'), leaf_cols=('olive', 'sage', 'forest', 'sage', 'olive'),
               branch_cols=('madder', 'mustard'), seed=140, group='t1', lean=0.0)
    c.say('river')
    rv = [(X(a), b) for a, b in RIVER if b <= YB + 12]
    M.river(c, rv, width=13.0, seed=120, group=None, widen=22.0)
    c.say('ploughed strips')
    PL = [(XL - 8, 266), (40, 261), (112, 256), (150, 262), (146, 290), (138, YB), (XL - 8, YB)]
    M.ploughed(c, [(X(a), b) for a, b in PL], angle_deg=64.0, seed=130, cols=('ochre2', 'olive', 'stone_dk', 'moss', 'sand'), furrow_cols=('umber', 'forest'))
    PR = [(440, 252), (520, 246), (XR + 6, 240), (XR + 6, YB), (452, YB), (434, 282)]
    M.ploughed(c, [(X(a), b) for a, b in PR], angle_deg=116.0, seed=131, cols=('olive', 'stone_dk', 'ochre2', 'moss', 'sand'), furrow_cols=('umber', 'forest'))
    c.say('ridges')
    # foreground mound: bands over a laid-and-couched interior with millefleurs (the couching grid in raking light)
    M.hill(c, M.ridge_contour(X(188), X(500), 306, bumps=[(X(352), 146, 58, 0.8), (X(466), 58, 8, 1.4)], waves=((1.2, 47.0, 0.4),), y_foot=YB + 30),
           [(4.5, 'olive'), (4, 'sand'), (4.5, 'ochre2')], seed=140, interior='moss', interior_angle=-2.0, pad=(0.20, 1.4), interior_bar=7.5,
           tufts=dict(spacing=21.0, size=(3.2, 5.2), col='forest'), flowers=dict(spacing=32.0, size=(11.0, 15.0)), y_end=YB, y_cut=YB)
    # middle ridge: low ground (hamlet, river town) -> hill-town hill -> dip -> large-town mound (muted greens / neutrals: the road is the only
    # saturated multicolour path)
    M.hill(c, M.ridge_contour(X(XL), X(XR), 238, bumps=[(X(280), 62, 41, 1.0), (X(448), 112, 28, 0.75), (X(222), 55, 5, 1.5), (X(372), 40, 9, 1.2)],
                              waves=((1.4, 41.0, 1.1),), y_foot=YB + 30),
           [(4.5, 'olive'), (4, 'sand'), (4.5, 'moss'), (5.0, 'stone_dk'), (4.0, 'sand')], seed=142, pad=(0.20, 1.4), interior='stone_dk', y_end=YB, y_cut=YB,
           interior_plough=dict(angle_deg=4.0, strip_w=(5.0, 7.0), cols=('stone_dk', 'olive', 'umber', 'moss', 'sand'), furrow_cols=('umber', 'forest')))
    # the capital rise: a visibly raised padded mound
    M.hill(c, M.hill_contour(X(362), 184, 126, 300, 0.85), [(5.5, 'olive'), (4.5, 'sand'), (5, 'moss'), (4.5, 'stone')], seed=144, pad=(0.95, 2.4), interior='moss', interior_angle=-4.0,
           interior_model=0.05, interior_grad=0.10, y_end=YB, y_cut=YB, interior_bar=7.0, tufts=dict(spacing=26.0, size=(3.0, 4.8), col='forest', margin=9.0))
    # back ridge, higher on the left so the sky above the hamlet is not an empty field (no blue: the only blue line in the land is the river)
    M.hill(c, M.ridge_contour(X(XL), X(XR), 186, bumps=[(X(36), 88, 54, 1.1), (X(186), 60, 34, 1.1), (X(566), 82, 34, 1.0), (X(-80), 70, 40, 1.0)],
                              waves=((1.5, 61.0, 2.0),), y_foot=YB + 30),
           [(4, 'olive'), (4.5, 'stone'), (4, 'sand'), (4.5, 'moss')], seed=145, pad=(0.20, 1.4), interior='olive', interior_angle=2.0,
           interior_model=0.05, interior_grad=0.10, y_end=YB, y_cut=YB, interior_bar=7.0, tufts=dict(spacing=24.0, size=(3.2, 5.2), col='forest', margin=9.0))
    # far ridge: two narrow pale bands, only visible where the back ridge is low
    M.hill(c, M.ridge_contour(X(XL), X(XR), 158, bumps=[(X(100), 120, 34, 1.1), (X(520), 110, 26, 1.0)], waves=((1.2, 70.0, 0.8),), y_foot=YB + 30),
           [(3.0, 'sage'), (3.4, 'stone')], seed=146, pad=(0.20, 1.0), y_cut=YB)
    if ext:
        c.say('lower rules')
        M.border_rules(c, 0.0, W_mm, Y_RULE_LOW, seed=9, group='border')
    c.say('stitching done')
    if preview:
        return c
    out = out or os.path.join(bkit.AAA, 'cache', 'maps')
    paths = c.finish(out, sheet=name if PX >= 6.5 else f'{name}_px{int(PX)}', ground_without=['road'] if PX >= 6.5 else (), tide=TIDE, age_density=1.8,
                     meta=dict(scene='prod/f91/scene_f91.py', thread=THREAD, OX=OX, ext=ext, towns={k: dict(v, style=None) for k, v in TOWNS.items()}, trees=TREES,
                               capital=CAPITAL, road=ROAD, river=RIVER, y_rule_top=Y_RULE_TOP, y_rule_bot=Y_RULE_BOT))
    return paths


def hamlet(c, T):
    """small hamlet: three cottages round a church-like watch tower; returns the tower apex (SHEET mm)."""
    x, y = X(T['x']), T['y']
    k = 1.2
    M.cottage(c, x - 17.0 * k, y + 0.3, 12.0 * k, 8.0 * k, 6.5 * k, wall_col='stone', roof_col='terracotta', seed=1, group='towns')
    M.cottage(c, x + 10.0 * k, y + 1.3, 14.0 * k, 9.0 * k, 7.5 * k, wall_col='clay', roof_col='ochre2', seed=2, group='towns')
    M.cottage(c, x + 23.0 * k, y - 0.2, 9.0 * k, 7.0 * k, 6.0 * k, wall_col='stone_warm', roof_col='tile_dk', seed=3, group='towns')
    return M.watch_tower(c, x, y + 0.5, w=6.6 * k, h=17.0 * k, roof_h=8.5 * k, seed=4, group='towns')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--px', type=float, default=7.0)
    ap.add_argument('--out', default=None)
    ap.add_argument('--ext', action='store_true')
    ap.add_argument('--name', default='k1_realm')
    a = ap.parse_args()
    t0 = time.time()
    print(build(a.px, a.out, ext=a.ext, name=a.name))
    print(f'built in {time.time() - t0:.1f}s')
