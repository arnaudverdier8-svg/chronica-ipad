"""v2 icon generators: the board's own idiom (as seen in the live menu capture), but never the same icon twice.
All geometry in game units (x right, z down, hex circumradius 1, Grandbois at the origin) unless a function says px.
Deterministic: every random draw comes from a hash of (hex, role), so a re-bake reproduces the board.
  forests   2-4 clusters of 5-12 conifers / broadleaf, a hut + woodpile slot, free centre for the units, dashed inner ring
  fields    2-3 cols x 1-2 rows of crop plots (rows along / across), greens / wheat / ploughed, a long pole and a stook
  hills     3-6 lumpy ochre mounds, two tonal bands each, brown outline
  mountains 4-8 peaks, lit / shade halves, painter's order
  plains    sparse grass tufts, a shrub
  sea       hand-placed wave marks: blue-noise darts, denser toward coasts, three mark types, irregular size and tilt"""
import math, sys, os
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

K_FORE = {'town': 0.62, 'site': 0.8, 'lumber': 0.8, 'banner': 0.55, 'tree': 0.62, 'card': 0.92}   # foreshortening of the lying elevations


def rng_of(*a):
    v = 2166136261
    for x in a:
        v = ((v ^ (int(x) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return np.random.default_rng(v)


def inside_hex(x, z, hc, margin):
    return float(edge_dist(np.array(x), np.array(z), hc[0], hc[1])) >= margin


# ------------------------------------------------------------------ trees
def tree_dims(sp, rng):
    """(rad, height) in game units; heights are the true standing heights of the 3D piece"""
    if sp == 'spruce':
        return float(rng.uniform(0.095, 0.125)), float(rng.uniform(0.62, 0.90))
    if sp == 'fir':
        return float(rng.uniform(0.125, 0.16)), float(rng.uniform(0.44, 0.62))
    return float(rng.uniform(0.13, 0.17)), float(rng.uniform(0.40, 0.55))        # round / broadleaf


def tree_lab(sp, rad, ht, seed, ppu=PPU):
    """lying elevation icon of a tree, foreshortened to K_FORE['tree']: label image (0 dark crown, 1 lit crown, 2 trunk) + tier polygons (px)"""
    r = rng_of(seed, 11)
    hh = ht * K_FORE['tree']
    w, h = max(8, int(round(2 * rad * ppu))), max(10, int(round(hh * ppu)))
    lab = -np.ones((h, w), np.int32)
    cx = w / 2.0
    trunk_h = max(2, int(0.12 * h))
    crown_h = h - trunk_h
    tiers = []
    if sp in ('spruce', 'fir'):
        n = 5 if sp == 'spruce' else 3
        hw = w / 2.0 * 0.98
        step = crown_h / (n + 0.45)
        for k in range(n - 1, -1, -1):          # lower tiers first, upper tiers overlap them
            y_a = k * step * 0.95
            y_b = y_a + step * 1.55
            wk = hw * (0.38 + 0.62 * (k + 1) / n)
            pts = [(cx + r.uniform(-0.04, 0.04) * w, y_a)]
            nz = 3
            for j in range(nz + 1):
                t = j / nz
                pts.append((cx - wk + 2 * wk * t, y_b - (0.14 * step if j % 2 else 0) + r.uniform(-0.05, 0.05) * step))
            pts.append((cx + wk * 1.0, y_b))
            pts = [(x, min(y, crown_h)) for x, y in pts]
            poly = np.round(np.array(pts)).astype(np.int32)
            cv2.fillPoly(lab, [poly], 0)
            tiers.append(poly)
        # lit left half of every tier (candle side), kept 1 stitch inside the outline
        lit = np.zeros_like(lab, np.uint8)
        for poly in tiers:
            half = poly.copy().astype(np.float32)
            half[:, 0] = np.minimum(half[:, 0], cx - 0.08 * w)
            cv2.fillPoly(lit, [np.round(half).astype(np.int32)], 1)
        lit = cv2.erode(lit, np.ones((3, 3), np.uint8))
        lab[(lit > 0) & (lab == 0)] = 1
    else:
        # broadleaf: three overlapping lobes + trunk
        for (ox, oy, rr) in [(-0.22, 0.55, 0.52), (0.24, 0.52, 0.5), (0.0, 0.3, 0.6)]:
            cv2.ellipse(lab, (int(cx + ox * w / 2), int(oy * crown_h)), (int(rr * w / 2 * 1.45), int(rr * crown_h * 0.55)), 0, 0, 360, 0, -1)
        lit = np.zeros(lab.shape, np.uint8)
        cv2.ellipse(lit, (int(cx - 0.16 * w), int(0.36 * crown_h)), (int(0.30 * w), int(0.22 * crown_h)), 0, 0, 360, 1, -1)
        lab[(lit > 0) & (lab == 0)] = 1
        tiers = []
    # trunk
    tw = max(2, int(0.16 * w))
    lab[crown_h - 1:, int(cx - tw / 2):int(cx + tw / 2) + 1] = np.where(lab[crown_h - 1:, int(cx - tw / 2):int(cx + tw / 2) + 1] < 0, 2,
                                                                           lab[crown_h - 1:, int(cx - tw / 2):int(cx + tw / 2) + 1])
    names = ['crown_dk', 'crown_lt', 'trunk']
    return lab, names, tiers


def forest_trees(hc, key, n_avoid):
    """tree specs of one forest hex: [(x, z_base, sp, rad, ht)] placed on the game's idiom: clusters around the inside of the dashed ring,
    free centre, a gap for the hut. n_avoid: list of (x, z, r) discs to keep clear (hut slot, units)."""
    r = rng_of(*key, 5)
    n = int(r.integers(7, 14))
    n_cl = int(r.integers(2, 4))
    mix = r.random()
    sp_main = 'spruce' if mix < 0.62 else 'fir'
    ang0 = r.uniform(0, 2 * math.pi)
    anchors = [(ang0 + k * 2 * math.pi / n_cl + r.uniform(-0.5, 0.5), r.uniform(0.50, 0.74)) for k in range(n_cl)]
    out = []
    tries = 0
    while len(out) < n and tries < 400:
        tries += 1
        if r.random() < 0.8:
            a0, rr0 = anchors[int(r.integers(0, n_cl))]
            a = a0 + r.normal(0, 0.36); rad = rr0 + r.normal(0, 0.10)
        else:
            a = r.uniform(0, 2 * math.pi); rad = r.uniform(0.42, 0.78)
        x = hc[0] + rad * math.cos(a); z = hc[1] + rad * 0.92 * math.sin(a)
        sp = sp_main if r.random() < 0.72 else ('round' if r.random() < 0.55 else ('fir' if sp_main == 'spruce' else 'spruce'))
        rd, ht = tree_dims(sp, r)
        ht *= r.uniform(0.85, 1.12)
        # the elevation icon (foreshortened) lies north of the base: keep it inside its own hex
        top = z - rd - ht * K_FORE['tree']
        if not (inside_hex(x, z + rd * 0.5, hc, 0.07) and inside_hex(x, top, hc, 0.07)): continue
        if math.hypot(x - hc[0], z - hc[1] - 0.15) < 0.30: continue
        if any(math.hypot(x - ax, z - az) < ar for ax, az, ar in n_avoid): continue
        if any(math.hypot(x - o[0], (z - o[1]) * 1.2) < 0.17 for o in out): continue
        out.append((x, z, sp, rd, ht))
    out.sort(key=lambda t: t[1])
    return out


def hut_slot(hc, key):
    r = rng_of(*key, 9)
    a = r.choice([-2.35, -0.85, 0.35, 2.55]) + r.uniform(-0.25, 0.25)
    rr = r.uniform(0.40, 0.50)
    return hc[0] + rr * math.cos(a), hc[1] + rr * 0.75 * math.sin(a) + 0.3


# ------------------------------------------------------------------ farm plots
def farm_plots(hc, key, avoid_rects=()):
    """crop plots of a farm hex -> list of dict(pts (4,2) game units, ang (furrow direction, deg), kind, colour index) + a pole and a stook"""
    r = rng_of(*key, 21)
    ang = float(r.choice([-31, -24, -17, 17, 24, 31])) + r.uniform(-4, 4)
    nc = int(r.choice([2, 2, 3]))
    nr = int(r.choice([1, 2, 2]))
    w0 = {2: 0.66, 3: 0.47}[nc] * r.uniform(0.92, 1.08)
    h0 = {1: 0.70, 2: 0.41}[nr] * r.uniform(0.92, 1.08)
    gap = 0.06 + r.uniform(0, 0.03)
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    plots = []
    off = np.array([r.uniform(-0.05, 0.05), r.uniform(-0.12, 0.05)])
    for j in range(nr):
        for i in range(nc):
            if r.random() < 0.10 and nc * nr > 3: continue
            ux = (i - (nc - 1) / 2) * (w0 + gap) + r.uniform(-0.02, 0.02)
            uz = (j - (nr - 1) / 2) * (h0 + gap) + r.uniform(-0.02, 0.02)
            w_ = w0 * r.uniform(0.9, 1.06); h_ = h0 * r.uniform(0.9, 1.06)
            cs = []
            for dx, dz in [(-w_ / 2, -h_ / 2), (w_ / 2, -h_ / 2), (w_ / 2, h_ / 2), (-w_ / 2, h_ / 2)]:
                dx += r.uniform(-0.015, 0.015); dz += r.uniform(-0.015, 0.015)
                x = hc[0] + off[0] + ux + ca * dx - sa * dz
                z = hc[1] + off[1] + uz + sa * dx + ca * dz
                cs.append((x, z))
            if not all(inside_hex(x, z, hc, 0.10) for x, z in cs): continue
            q = r.random()
            kind = 'green' if q < 0.66 else ('wheat' if q < 0.86 else 'plough')
            furrow = ang + (90 if (r.random() < 0.28) else 0) + r.uniform(-4, 4)
            plots.append(dict(pts=cs, furrow=float(furrow), kind=kind, ci=int(r.integers(0, 4))))
    # long pole (log) along the plots' low edge and a stook at its end, as in the game
    pole = None
    if plots:
        a = math.radians(ang)
        p0 = np.array([hc[0] + off[0] - 0.46 * math.cos(a) + 0.24 * (-math.sin(a)) * (1 if r.random() < 0.5 else -1) * 0,
                       hc[1] + off[1] + 0.50])
        p0 = np.array([hc[0] + off[0] - 0.30, hc[1] + off[1] + 0.50])
        p1 = p0 + np.array([math.cos(a), math.sin(a)]) * r.uniform(0.40, 0.55)
        if inside_hex(p0[0], p0[1], hc, 0.1) and inside_hex(p1[0], p1[1], hc, 0.1):
            pole = (tuple(p0), tuple(p1))
    stook = None
    if plots and r.random() < 0.8:
        sx, sz = hc[0] + r.uniform(-0.1, 0.2), hc[1] + r.uniform(0.30, 0.55)
        if inside_hex(sx, sz, hc, 0.12): stook = (sx, sz, r.uniform(0.07, 0.10), r.uniform(0.12, 0.17))
    return plots, pole, stook


# ------------------------------------------------------------------ hills / mountains / plains
def hill_mounds(hc, key):
    r = rng_of(*key, 31)
    out = []
    n = int(r.integers(3, 7))
    for _ in range(40):
        if len(out) >= n: break
        ox, oz = r.uniform(-0.62, 0.62), r.uniform(-0.55, 0.62)
        x, z = hc[0] + ox, hc[1] + oz
        w = r.uniform(0.30, 0.56); h = w * r.uniform(0.42, 0.62)
        if not (inside_hex(x - w / 2, z, hc, 0.08) and inside_hex(x + w / 2, z, hc, 0.08) and inside_hex(x, z - h, hc, 0.08) and inside_hex(x, z + 0.04, hc, 0.08)):
            continue
        if any(math.hypot((x - o['x']) / (0.5 * (w + o['w'])), (z - o['z']) / (0.5 * (h + o['h']) + 0.12)) < 0.85 for o in out): continue
        ph = r.uniform(0, 6.28); lump = r.uniform(0.15, 0.32)
        u = np.linspace(0, 1, 34)
        topx = x + (u - 0.5) * w
        topz = z - h * np.sin(math.pi * u) ** 0.78 * (1 + lump * np.sin(3 * math.pi * u + ph))
        botx = topx[::-1]
        botz = z + 0.07 * h * np.sin(math.pi * (1 - u)) + 0.0
        poly = np.stack([np.concatenate([topx, botx]), np.concatenate([topz, botz])], 1)
        # light band: polygon above a wavy line at ~42 % of the mound height
        hl = z - h * (0.42 + 0.10 * np.sin(2 * math.pi * u * 1.6 + ph))
        lt = np.stack([np.concatenate([topx, topx[::-1]]), np.concatenate([topz, np.maximum(hl, topz)[::-1]])], 1)
        out.append(dict(x=x, z=z, w=w, h=h, poly=poly, light=lt, ci=int(r.integers(0, 3))))
    out.sort(key=lambda m: m['z'])
    return out


def mountain_peaks(hc, key):
    r = rng_of(*key, 41)
    out = []
    n = int(r.integers(4, 9))
    for _ in range(50):
        if len(out) >= n: break
        x, z = hc[0] + r.uniform(-0.62, 0.62), hc[1] + r.uniform(-0.40, 0.60)
        w = r.uniform(0.24, 0.46); h = w * r.uniform(0.85, 1.25)
        apex = (x + r.uniform(-0.05, 0.05) * w, z - h)
        pts = [(x - w / 2, z), apex, (x + w / 2, z)]
        if not all(inside_hex(px, pz, hc, 0.07) for px, pz in pts): continue
        if any(math.hypot(x - o['x'], (z - o['z']) * 1.4) < 0.17 for o in out): continue
        out.append(dict(x=x, z=z, w=w, h=h, pts=pts, apex=apex))
    out.sort(key=lambda p: p['z'])
    return out


def plain_tufts(hc, key):
    r = rng_of(*key, 51)
    out = []
    for _ in range(int(r.integers(5, 11))):
        x, z = hc[0] + r.uniform(-0.65, 0.65), hc[1] + r.uniform(-0.6, 0.6)
        if inside_hex(x, z, hc, 0.14):
            out.append((x, z, float(r.uniform(0.045, 0.085)), float(r.uniform(-18, 18))))
    shrub = None
    if r.random() < 0.55:
        x, z = hc[0] + r.uniform(-0.45, 0.45), hc[1] + r.uniform(-0.4, 0.4)
        if inside_hex(x, z, hc, 0.2): shrub = (x, z, float(r.uniform(0.08, 0.13)))
    return out, shrub


# ------------------------------------------------------------------ sea waves
def wave_marks(sea_hexes, land_hexes, seed=77):
    """hand-placed rhythm: dart-throwing blue noise with a local radius that is small near the coast and large in open water,
    three mark types, size / tilt jitter. sea_hexes: list of (x, z) centres; returns [(x, z, kind, span, tilt_deg)]"""
    r = np.random.default_rng(seed)
    land = np.array(land_hexes, np.float64).reshape(-1, 2)
    pts = []
    for (cx, cz) in sea_hexes:
        for _ in range(int(r.integers(2, 6))):
            x, z = cx + r.uniform(-0.8, 0.8), cz + r.uniform(-0.8, 0.8)
            if float(edge_dist(np.array(x), np.array(z), cx, cz)) < 0.14: continue
            dl = np.min(np.hypot(land[:, 0] - x, land[:, 1] - z)) if len(land) else 9.0
            rmin = 0.55 + 0.20 * min(dl, 5.0) + r.uniform(0, 0.35)       # open sea is sparser
            if any(math.hypot(x - p[0], z - p[1]) < min(rmin, 0.5 * (rmin + p[5])) for p in pts[-60:]): continue
            if any(math.hypot(x - p[0], z - p[1]) < 0.42 for p in pts): continue
            q = r.random()
            kind = 'arc' if q < 0.52 else ('twin' if q < 0.76 else ('dash' if q < 0.92 else 'swell'))
            span = r.uniform(0.16, 0.42) * (1.15 if kind == 'swell' else 1.0)
            pts.append((x, z, kind, span, float(r.normal(0, 7)), rmin))
    return [(x, z, k, s, t) for x, z, k, s, t, _ in pts]


def wave_paths(x, z, kind, span, tilt, seed):
    """polylines (game units) of one wave mark"""
    r = rng_of(seed, int(x * 100), int(z * 100))
    ca, sa = math.cos(math.radians(tilt)), math.sin(math.radians(tilt))
    def mk(cx, cz, sp, ph, amp):
        t = np.linspace(-0.5, 0.5, 20)
        xs = t * sp
        zs = amp * np.sin(t * 2 * math.pi * 1.0 + ph) * (1 - 0.3 * np.abs(t))
        return [(cx + ca * a - sa * b, cz + sa * a + ca * b) for a, b in zip(xs, zs)]
    if kind == 'arc':
        return [mk(x, z, span, r.uniform(0, 1), 0.024 + 0.012 * r.random())]
    if kind == 'twin':
        return [mk(x - 0.03, z, span, 0.3, 0.02), mk(x + span * 0.18, z + 0.075, span * 0.7, 1.1, 0.02)]
    if kind == 'swell':
        return [mk(x, z, span, 0.2, 0.03), mk(x + 0.05, z + 0.07, span * 0.8, 0.9, 0.025), mk(x - 0.04, z + 0.14, span * 0.55, 0.5, 0.02)]
    return [[(x + ca * a, z + sa * a) for a in (-span / 2, -span / 6)], [(x + ca * a, z + sa * a) for a in (span / 6, span / 2)]]


def dash_ring(q, r_, rad=0.80):
    cs = hex_corners(q, r_, rad)
    return cs + cs[:1]
