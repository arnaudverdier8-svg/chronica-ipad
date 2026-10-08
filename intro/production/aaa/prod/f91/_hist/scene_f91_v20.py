"""S02 'One realm' kit sheet (frieze section 1, the part seen at f91): upper border with the gold chronicle thread and
the confronted vignette lions, the one realm in Bayeux idiom (hillock bands, paired-line river and bridge, ploughed
strips, four unequal towns re-stitched from settle_0 / settle_1 / settle_1_2 / settle_2, the crowned capital from
capital + walls_2, house pennants) and ONE road couched in the four house colours.

Sheet: 600 x 330 mm (sheet mm = frieze mm of section 1 minus FRIEZE_ORIGIN).  f91 sees x 40-552, y 5-293.

    python3 scene_f91.py [--px 10] [--out <maps dir>] [--preview]
"""
import os, sys, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(os.path.dirname(HERE), 'kit')
sys.path.insert(0, KIT)
import bkit                                   # noqa: E402  (sets lib path, threads)
import numpy as np, cv2                       # noqa: E402
from bkit.canvas import Canvas               # noqa: E402
from bkit import motifs as M, geom as G      # noqa: E402

SHEET_MM = (600.0, 330.0)
FRIEZE_ORIGIN = (0.0, 0.0)
Y_RULE_TOP = 17.5          # top rule of the upper border = the path of the gold chronicle thread
Y_RULE_BOT = 77.5          # border / main register rules
THREAD = dict(x0=70.0, x1=606.0, tie_s=7.5)     # one crimson tie-down at the start; the rest of the pair trails off toward the needle (upper right, off frame)

# towns: (models, x centre, y base, width, pennant colour, style overrides); vs = vertical stretch (Bayeux proportions)
TOWNS = dict(
    hamlet=dict(models='settle_0', x=86.0, y=240.0, w=52.0, vs=1.5, pennant='road_green', style=dict(
        timber=('umber', 'clay'), roof=('mustard', 'terracotta'), wall=('clay', 'stone_dk', 'madder_lt'), tower=('mustard', 'madder_lt'))),
    river=dict(models='settle_1', x=196.0, y=231.0, w=100.0, vs=1.6, pennant='road_blue', style=dict(
        roof=('terracotta', 'woad', 'madder2', 'olive', 'mustard', 'terracotta', 'woad'), wall=('stone', 'stone_warm', 'stone_dk'),
        tower=('mustard', 'sand', 'clay', 'stone'))),
    hill=dict(models='settle_1_2', x=284.0, y=196.0, w=78.0, vs=1.6, pennant='road_crimson', style=dict(
        roof=('woad', 'terracotta', 'olive', 'madder2', 'mustard'), tower=('moss', 'sand', 'mustard'), wall=('stone_warm', 'stone_dk', 'stone'))),
    large=dict(models='settle_2', x=488.0, y=208.0, w=124.0, vs=1.55, pennant='road_gold', style=dict(
        roof=('terracotta', 'madder2', 'woad', 'terracotta', 'olive', 'mustard', 'woad'), tower=('sand', 'mustard', 'moss', 'stone'),
        wall=('stone', 'stone_dk', 'stone_warm'))),
)
CAPITAL = dict(x=362.0, y=170.0, walls_w=92.0, keep_w=33.0, walls_vs=1.4, keep_vs=0.95)
TREES = [
         dict(x=250.0, y=228.0, h=94.0, trunk=('road_gold', 'road_crimson', 'road_blue', 'road_green'), leaves=('olive', 'sage', 'forest', 'sage', 'olive'),
              branches=('madder', 'mustard'), lean=0.0, seed=110),
         dict(x=418.0, y=195.0, h=86.0, trunk=('road_green', 'road_gold', 'road_crimson', 'road_blue'), leaves=('sage', 'olive', 'forest', 'olive', 'sage'),
              branches=('terracotta', 'mustard'), lean=-0.02, seed=111)]
TIDE = [dict(c=[548.0, 300.0], r_mm=62.0, aspect=1.5, seed=5)]

ROAD = [(-6, 254.0), (25, 248.0), (52, 244.0), (82, 243.6), (112, 243.0), (126, 240.5), (146, 235.5), (196, 234.6), (246, 234.0),
        (262, 228.0), (284, 219.0), (305, 212.0), (322, 200.0), (338, 187.0), (352, 177.0), (362, 173.6), (378, 174.5),
        (398, 184.0), (416, 198.0), (440, 212.0), (488, 220.0), (530, 222.0), (606, 230.0)]
RIVER = [(129, 176), (125, 198), (128, 218), (124, 238), (127, 258), (122, 280), (125, 300), (120, 334)]


def build(PX=10.0, out=None, preview=False, verbose=True):
    c = Canvas(*SHEET_MM, PX=PX, seed=91, linen_seed=0, name='k1_realm', frieze_origin_mm=FRIEZE_ORIGIN, verbose=verbose)
    W_mm = SHEET_MM[0]
    # ======================= top hem, nail holes (linen-level)
    c.hem(11.0, 0.0, seed=3, run_y_mm=9.3)
    c.nail_hole(156.0, 7.4, seed=1)
    c.nail_hole(404.0, 7.9, seed=2)
    # ======================= upper border
    # the gold chronicle thread: up through the linen at x0, one crimson silk tie-down, laid taut along the
    # underdrawn top rule, down again at x1 (the needle left toward the upper right in S01)
    xs = np.linspace(THREAD['x0'], THREAD['x1'], 1100)
    u = np.clip((xs - THREAD['x0'] - 14.0) / 60.0, 0, 1); u = u * u * (3 - 2 * u)          # 0 at the tie, 1 after ~75 mm: the loose part
    ys = (Y_RULE_TOP + 0.10 * np.sin((xs - xs[0]) / 23.0) - 0.25 * ((xs - xs[0]) / 144.0).clip(0, 1) + 0.35 * np.exp(-(xs - xs[0]) / 2.0)
          + u * (1.35 * np.sin((xs - xs[0]) / 61.0 + 0.4) + 0.45 * np.sin((xs - xs[0]) / 17.0) - 0.0068 * (xs - xs[0] - 14.0).clip(0, None)))
    thr = np.stack([xs, ys], 1).astype(np.float32)
    c.metal_pair(thr, ties_s_mm=[THREAD['tie_s']], tie_col='#C0281F', group='thread', seed=5, tie_len_mm=4.6, tie_r=0.62,
                 thread_r=0.55, sep_mm=1.25, gold=np.array([0.80, 0.40, 0.06], np.float32), ply_mm=1.0, ply_deg=40, hamp=0.55, h0=0.6)
    c.needle_holes([(THREAD['x0'] - 0.3, Y_RULE_TOP + 0.3)], r_mm=(0.30, 0.34), seed=4, depth=0.35)
    c.occlude_polys([G.band(thr, -2.0, 2.0)])
    c.underdraw(np.array([(0, Y_RULE_TOP + 0.15), (W_mm, Y_RULE_TOP - 0.25)]), 0.85, width_mm=0.45, seed=11)
    # beasts: the confronted pair (game vignette lions), off-centre left
    bars_x = [22.0, 100.0, 166.0, 238.0, 312.0, 380.0, 452.0, 522.0, 592.0]
    c.say('border beasts')
    M.beast(c, 'red', (172.0, 25.0, 230.0, 72.5), seed=21, group='border')
    M.beast(c, 'blue', (247.0, 25.5, 305.0, 72.5), seed=22, group='border')
    # sprigs (millefleurs, from the vignettes' flowers) in the other compartments
    spr = [(61.0, ('woad', 'terracotta'), 2, -0.1), (133.0, ('terracotta', 'mustard'), 1, 0.15), (346.0, ('madder', 'woad'), 2, 0.05),
           (416.0, ('woad',), 1, -0.15), (487.0, ('terracotta', 'woad'), 2, 0.1), (557.0, ('mustard', 'madder'), 1, -0.05)]
    for k, (sx, fc, nf, ln) in enumerate(spr):
        M.sprig(c, sx, 73.0, 40.0 + 4 * ((k * 7) % 3), flower_cols=fc, seed=40 + k, group='border', lean=ln, n_flowers=nf)
    bar_cols = ['terracotta', 'olive', 'mustard', 'woad', 'madder', 'moss', 'terracotta', 'olive', 'mustard']
    for k, bx in enumerate(bars_x):
        M.diag_bar(c, bx, Y_RULE_TOP + 1.8, Y_RULE_BOT - 1.6, slant=(1 if k % 2 else -1), col=bar_cols[k], seed=60 + k, group='border',
                   lean_mm=17.0)
    M.border_rules(c, 0.0, W_mm, Y_RULE_BOT, seed=7, group='border')
    c.occlude_polys([np.array([(0, Y_RULE_TOP - 2), (W_mm, Y_RULE_TOP - 2), (W_mm, Y_RULE_BOT + 4), (0, Y_RULE_BOT + 4)])])
    # ======================= the realm (front -> back)
    c.say('capital + crown')
    cap_res = M.town(c, [('capital', 0.0, -0.5, CAPITAL['keep_w'], CAPITAL['keep_vs']), ('walls_2', 0.0, 0.0, CAPITAL['walls_w'], CAPITAL['walls_vs'])],
                     CAPITAL['x'], CAPITAL['y'], CAPITAL['walls_w'], seed=71, group='capital', outline_w=0.85,
                     skip=('gold',), model=0.14,
                     style=dict(roof=('woad', 'woad', 'woad_dark', 'woad'), tower=('sand', 'mustard', 'stone', 'sand'), wall=('stone_warm', 'sand'),
                                gold=('mustard',), cloth=('blue',)))
    # the crown rests above the keep's central parapet (measured on the stitched silhouette)
    px_c = int(round(CAPITAL['x'] * PX)); hw_k = int(0.5 * CAPITAL['keep_w'] * PX)
    col_occ = np.nonzero(c.occ[:, px_c - hw_k:px_c + hw_k].any(1))[0]
    y_top = col_occ[col_occ > int(84 * PX)].min() / PX if len(col_occ) else CAPITAL['y'] - 60
    M.crown(c, CAPITAL['x'], y_top - 4.0, w=27.0, h=17.5, seed=70, group='capital')
    tops = {}
    for k, (nm, T) in enumerate(TOWNS.items()):
        c.say('town', nm)
        if nm == 'hamlet':           # hand-drawn cottages + watch tower (the game's settle_0 palisade reads as hay bales in embroidery)
            tops[nm] = hamlet(c, T)
            continue
        res = M.town(c, T['models'], T['x'], T['y'], T['w'], seed=80 + k, group='towns', style=T['style'], pennant_col=T['pennant'],
                     vstretch=T['vs'], outline_w=0.82)
        tops[nm] = res['top']
    for k, (nm, T) in enumerate(TOWNS.items()):
        tx, ty = tops[nm]
        pl = 10.0 if nm == 'hamlet' else 12.0
        M.pennant(c, tx, ty - pl, pl, T['pennant'], direction=(1 if k % 2 == 0 else -1), length=(13.0 if nm == 'hamlet' else 17.0),
                  height=(5.6 if nm == 'hamlet' else 7.0), seed=90 + k,
                  group='pennants')
    c.say('road, bridge')
    M.road(c, ROAD, width=7.0, seed=101, group='road')
    M.arch_bridge(c, 126.5, 240.6 + 3.0, r_out=12.5, r_in=8.4, foot_y=260.0, seed=95)
    c.say('trees')
    for T in TREES:
        M.tree(c, T['x'], T['y'], T['h'], trunk_cols=T['trunk'], leaf_cols=T['leaves'], branch_cols=T['branches'], seed=T['seed'],
               group='trees', lean=T['lean'])
    c.say('river')
    M.river(c, RIVER, width=5.0, seed=120, group=None, widen=16.0)
    c.say('ploughed strips')
    M.ploughed(c, [(-12, 266), (40, 258), (100, 252), (104, 280), (96, 304), (-12, 306)], angle_deg=64.0, seed=130,
               cols=('ochre2', 'olive', 'stone', 'moss'))
    M.ploughed(c, [(432, 252), (520, 244), (612, 238), (612, 306), (440, 306), (428, 280)], angle_deg=116.0, seed=131,
               cols=('olive', 'stone', 'ochre2', 'moss'))
    c.say('ridges')
    # foreground mound: bands over a laid-and-couched interior (the couching grid in raking light)
    M.hill(c, M.ridge_contour(128, 478, 306, bumps=[(266, 134, 57, 0.8), (400, 62, 8, 1.4)], waves=((1.2, 47.0, 0.4),), y_foot=330),
           [(4.5, 'olive'), (4, 'sand'), (4.5, 'ochre2')], seed=140, interior='moss', interior_angle=-2.0,
           tufts=dict(spacing=21.0, size=(3.2, 5.2), col='forest'))
    # middle ridge: low ground (hamlet, river town) -> hill-town hill -> dip -> large-town mound (muted greens / neutrals so the road is the only
    # saturated multicolour path on it)
    M.hill(c, M.ridge_contour(-10, 610, 238, bumps=[(284, 74, 41, 1.0), (488, 140, 28, 0.75), (196, 55, 5, 1.5), (372, 40, 9, 1.2)],
                              waves=((1.4, 41.0, 1.1),), y_foot=330),
           [(4.5, 'olive'), (4, 'sand'), (4.5, 'moss'), (5.0, 'stone_dk'), (4.0, 'sand')], seed=142)
    # the capital rise
    M.hill(c, M.hill_contour(362, 170, 126, 300, 0.85), [(5.5, 'olive'), (4.5, 'sand'), (5, 'moss'), (4.5, 'stone')], seed=144)
    # back ridge (no blue: the only blue line in the land is the river)
    M.hill(c, M.ridge_contour(-10, 610, 186, bumps=[(36, 84, 40, 1.1), (186, 76, 33, 1.1), (566, 82, 30, 1.0)],
                              waves=((1.5, 61.0, 2.0),), y_foot=330),
           [(4, 'olive'), (4.5, 'stone'), (4, 'sand'), (4.5, 'moss')], seed=145)
    c.say('stitching done')
    if preview:
        return c
    out = out or os.path.join(bkit.AAA, 'cache', 'maps')
    paths = c.finish(out, sheet='k1_realm' if PX >= 10 else f'k1_realm_px{int(PX)}', ground_without=['road'] if PX >= 10 else (), tide=TIDE, age_density=0.9,
                     meta=dict(scene='prod/f91/scene_f91.py', thread=THREAD, towns={k: dict(v, style=None) for k, v in TOWNS.items()}, trees=TREES,
                               capital=CAPITAL, road=ROAD, river=RIVER, y_rule_top=Y_RULE_TOP, y_rule_bot=Y_RULE_BOT))
    return paths


def hamlet(c, T):
    """four-cottage hamlet round a church-like watch tower; returns the tower apex (mm)."""
    x, y = T['x'], T['y']
    M.cottage(c, x - 17.0, y + 0.3, 13.0, 8.0, 6.5, wall_col='stone', roof_col='terracotta', seed=1, group='towns')
    M.cottage(c, x + 12.0, y + 1.3, 15.0, 9.0, 7.5, wall_col='clay', roof_col='mustard', seed=2, group='towns')
    M.cottage(c, x + 26.0, y - 0.2, 10.0, 7.0, 6.0, wall_col='stone_warm', roof_col='woad', seed=3, group='towns')
    return M.watch_tower(c, x, y + 0.5, seed=4, group='towns')


def bridge(c, x, y_deck, span, seed=0, group=None):
    """Bayeux bridge from the game 'bridge' elevation: an arched deck of planks in alternating colours on two piers."""
    M.town(c, [('bridge', 0.0, 0.0, span, 2.2)], x, y_deck + 3.0, span, seed=seed, group=group,
           style=dict(timber=('mustard', 'terracotta', 'buff', 'madder'), wall=('mustard',)), min_part_mm2=0.8)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--px', type=float, default=10.0)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    t0 = time.time()
    print(build(a.px, a.out))
    print(f'built in {time.time() - t0:.1f}s')
