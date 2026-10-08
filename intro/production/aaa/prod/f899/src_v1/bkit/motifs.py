"""Bayeux kit motifs.  Each builder stitches into a Canvas (front-to-back: call nearer elements first) and registers
its occluder.  All positions in sheet mm.  Narrative register: matte wool, laid and couched, blue-black stem outlines
(chroma <= .13).  Heraldic register (pennants, crown): padded satin / couched gold, chroma <= .20."""
import math
import numpy as np, cv2
from . import geom as G
from .canvas import colour, lots
from chron import stitch as S
from chron.stitch import CTX
from chron.config import WOOL, SILK, METAL
from chron.record import OUTLINE_REGION

INK = '#22232F'
REDBROWN = '#6E3326'
WARM = '#2B170D'
PAL = dict(terracotta='#B65E43', madder='#7A3B2C', mustard='#C3963F', buff='#D6BE86', sage='#98A068', olive='#6E7343',
           forest='#34432F', woad='#4F6F8A', woad_dark='#2D4460', linen_hi='#E6D7B6', gold='#D79A33', crimson='#CC3A2C',
           blue='#3F72BE', green='#3A8C63', ochre='#CB7A1C', brown='#5A3A22', woad_pale='#7E95A6', madder_lt='#9A5040',
           # deeper neutrals / earths (v13): buff and linen_hi are the SAME value as the linen ground (palette contrast 1.0),
           # so walls and bands in them vanish; these sit 0.07-0.17 OKLab L below the lit linen like p1's wool does
           stone='#B6A07A', stone_dk='#9C8662', stone_warm='#BFA27A', sand='#C4AA74', clay='#B07E58', moss='#7C814E',
           slate='#6E7A86', madder2='#8A3A2C', ochre2='#B8862F', umber='#6B5238',
           # the four house colours as road / pennant dyes (between the narrative and the heraldic register)
           road_gold='#CFA040', road_crimson='#B03A2C', road_blue='#3D669C', road_green='#3D7E56')


def P(name):
    return PAL.get(name, name)


def ink_for(col, light=False):
    """outline ink chosen by the fill's hue (as the re-embroidered panels do): warm dark brown for warm fills,
    navy-black for blues, green-black for greens, blue-black otherwise; 18 % of the fill colour mixed in."""
    from chron.color import lin2oklab
    cl = colour(P(col)) if isinstance(col, str) else np.asarray(col, np.float32)
    lb = lin2oklab(cl[None])[0]
    C = math.hypot(lb[1], lb[2]); h = math.degrees(math.atan2(lb[2], lb[1])) % 360
    if C > 0.03 and (h > 300 or h < 20):
        base = '#2A1730'
    elif C > 0.03 and 20 <= h < 112:
        base = '#3A1D12' if lb[0] < 0.62 else '#4A2818'
    elif C > 0.03 and 112 <= h < 190:
        base = '#20291B'
    elif C > 0.025 and 190 <= h < 300:
        base = '#1C2438'
    else:
        base = '#2A2226'
    return (colour(base) * 0.82 + np.clip(cl, 0, 1) * 0.18).astype(np.float32)


# ---------------------------------------------------------------------------- shared helpers
def _field_along(c, win, paths_mm, smooth_mm=1.2):
    x0, y0, x1, y1 = win
    return G.path_field((y1 - y0, x1 - x0), [np.asarray(p, np.float32) * c.PX - np.array([x0, y0], np.float32) for p in paths_mm],
                        smooth_mm * c.PX)


def path_coords(shape, path_px):
    """per-pixel (s, t): arc length (px) of the nearest sample of path_px and signed normal distance (px)."""
    H, W = shape
    q = G.resample(np.asarray(path_px, np.float32), 0.7)
    s = G.arclen(q); nrm = G.normals(q)
    zero = np.ones((H, W), np.uint8)
    idx = np.full((H, W), -1, np.int64)
    xi = np.round(q[:, 0]).astype(int); yi = np.round(q[:, 1]).astype(int)
    ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
    for k in np.nonzero(ok)[0]:
        zero[yi[k], xi[k]] = 0; idx[yi[k], xi[k]] = k
    _, lab = cv2.distanceTransformWithLabels(zero, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    zy, zx = np.nonzero(zero == 0)
    table = np.concatenate([[0], idx[zy, zx]])
    k = table[lab]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    t = (xx - q[k, 0]) * nrm[k, 0] + (yy - q[k, 1]) * nrm[k, 1]
    return s[k].astype(np.float32), t.astype(np.float32)


def _cut_y(path, y_cut):
    p = np.asarray(path, np.float32)
    if y_cut is None:
        return [p]
    keep = p[:, 1] < y_cut
    runs, cur = [], []
    for k in range(len(p)):
        if keep[k]:
            cur.append(p[k])
        else:
            if len(cur) > 1: runs.append(np.array(cur))
            cur = []
    if len(cur) > 1: runs.append(np.array(cur))
    return runs


# ---------------------------------------------------------------------------- tufts
def scatter_tufts(c, mask_win, win, spacing=19.0, seed=0, col='forest', group=None, size=(3.0, 5.0), margin=7.0, jitter=0.45):
    """small three-blade grass tufts (stem-stitch strokes, the Bayeux 'v' marks) scattered over a filled region:
    jittered grid, tuft height 3-5 mm, blades fanned +-25 deg and curving, drawn ON TOP of the fill (clip against nearer
    elements only)."""
    x0, y0, x1, y1 = win
    PX = c.PX
    r = np.random.default_rng(seed)
    dt = cv2.distanceTransform(mask_win.astype(np.uint8), cv2.DIST_L2, 5) / PX
    gx = np.arange(x0 / PX + spacing * 0.5, x1 / PX, spacing)
    gy = np.arange(y0 / PX + spacing * 0.5, y1 / PX, spacing * 0.8)
    n = 0
    for j, yy in enumerate(gy):
        for i, xx in enumerate(gx):
            px_ = xx + (r.uniform(-1, 1) * jitter + (0.5 if j % 2 else 0.0)) * spacing
            py_ = yy + r.uniform(-1, 1) * jitter * spacing * 0.8
            ix, iy = int(px_ * PX - x0), int(py_ * PX - y0)
            if not (0 <= ix < x1 - x0 and 0 <= iy < y1 - y0) or dt[iy, ix] < margin:
                continue
            h = r.uniform(*size)
            for b in range(3):
                a = math.radians(-90 + (b - 1) * r.uniform(16, 28) + r.uniform(-6, 6))
                hh = h * (1.0 if b == 1 else r.uniform(0.62, 0.85))
                bend = r.uniform(-0.18, 0.18) * hh
                t = np.linspace(0, 1, 7)
                pts = np.stack([px_ + (b - 1) * 0.35 + hh * np.cos(a) * t + bend * t ** 2, py_ + hh * np.sin(a) * t], 1)
                c.outline_mm(pts.astype(np.float32), P(col), width=0.7, L=2.0, seed=seed * 101 + n * 3 + b, group=group, h0=0.42, hamp=0.34,
                             min_len_mm=0.8)
            n += 1
    return n


# ---------------------------------------------------------------------------- hills and ground
def hill(c, contour, bands, y_cut=None, seed=0, group=None, outline=None, outline_w=1.15, name='hill', bar_spacing=4.5,
         couch=True, ud=True, occlude=True, inner_outline=True, couch_cols=None, wob=(1.2, 0.5), width_var=0.22, interior=None,
         interior_angle=None, band_model=0.05, interior_couch=True, interior_model=0.06, interior_grad=0.10, tufts=None):
    """Bayeux hillock: multicolour laid bands following the hill outline (positive offset = inward / down), linen
    inside.  contour: open polyline mm (left foot -> crest(s) -> right foot).  bands: [(width_mm, colour), ...]."""
    Pc = G.resample(contour, 0.5)
    Pc = G.wobble(Pc, wob[0], 34.0, seed)
    Pc = G.resample(G.wobble(Pc, wob[1], 9.0, seed + 1), 0.4)
    n = len(Pc)
    widths = [b[0] * (1 + width_var * G.noise1(n, max(2.0, 45.0 / 0.4), seed * 3 + k)) for k, b in enumerate(bands)]
    offs = [np.zeros(n, np.float32)]
    for w_ in widths:
        offs.append(offs[-1] + w_)
    polys = [G.band(Pc, offs[k], offs[k + 1]) for k in range(len(bands))]
    win = c.win_of_polys(polys + [Pc], 3.0)
    x0, y0, x1, y1 = win
    cut = np.ones((y1 - y0, x1 - x0), bool)
    if y_cut is not None:
        ys = (np.arange(y0, y1) + 0.5) / c.PX
        cut &= (ys < y_cut)[:, None]
    for k, (w, col) in enumerate(bands):
        mk = c.mask([polys[k]], win).astype(bool) & cut
        fld = _field_along(c, win, [G.offset(Pc, 0.5 * (offs[k] + offs[k + 1]))], 1.0)
        bc = None if couch_cols is None else couch_cols[k % len(couch_cols)]
        c.fill(mk, win, P(col), field=fld, couch=couch, bar_spacing=bar_spacing, tie=bar_spacing - 0.5, seed=seed * 17 + k,
               group=group, name=f'{name}_b{k}', erode=(0.28, 0.42), bar_col=bc, maxturn_deg=40, model=band_model, grad=0.0)
    if interior is not None:
        inner = G.offset(Pc, offs[-1])
        Hb = c.h_mm + 5
        ipoly = np.vstack([inner, [[inner[-1, 0], Hb], [inner[0, 0], Hb]]]).astype(np.float32)
        wi = c.win_px(x0, y0, x1, min(c.H, int(Hb * c.PX)))
        mk = c.mask([ipoly], wi).astype(bool)
        if interior_angle is None:
            fld = _field_along(c, wi, [G.offset(Pc, offs[-1] + 6.0)], 3.0)
        else:
            fld = G.const_field(mk.shape, interior_angle)
        c.fill(mk, wi, P(interior), field=fld, couch=interior_couch, bar_spacing=4.5, tie=4.0, seed=seed * 17 + 99, group=group,
               name=f'{name}_in', erode=(0.28, 0.42), maxturn_deg=35, model=interior_model, grad=interior_grad)
        if tufts:
            scatter_tufts(c, mk, wi, seed=seed + 5, group=group, **tufts)
    lines = [offs[0]] + (list(offs[1:]) if inner_outline else [offs[-1]])
    for j, d in enumerate(lines):
        if outline is not None:
            ink = outline
        else:   # the darker of the two bands this line separates
            nb_ = [bands[i][1] for i in (j - 1, j) if 0 <= i < len(bands)]
            from chron.color import lin2oklab
            dk = min(nb_, key=lambda q: float(lin2oklab(colour(P(q))[None])[0][0]))
            ink = ink_for(dk)
        for run in _cut_y(G.offset(Pc, d), y_cut):
            c.outline_mm(run, ink, width=outline_w * (1.0 if j in (0, len(lines) - 1) else 0.9), seed=seed * 31 + j, group=group)
            if ud:
                c.underdraw(G.offset(run, 0.35 * (1 if j % 2 else -1)), 0.7, seed=seed * 7 + j)
    if occlude:
        H = c.h_mm + 5
        occ = np.vstack([Pc, [[Pc[-1, 0], H], [Pc[0, 0], H]]])
        c.occlude_polys([occ], 0.4)
    return Pc


def hill_contour(xc, y_crest, half_w, y_foot, power=1.4, skew=0.0, n=120, x_range=None, bumps=()):
    """mound outline: cos^power bump (power < 1: flatter top), plus optional secondary bumps (xc, half_w, height)."""
    xa, xb = (xc - half_w, xc + half_w) if x_range is None else x_range
    xs = np.linspace(xa, xb, n)
    ys = y_foot - G.bump(xs, xc, half_w, y_foot - y_crest, power, skew)
    for bx, bw, bh in bumps:
        ys = ys - G.bump(xs, bx, bw, bh, 1.5)
    return np.stack([xs, ys], 1).astype(np.float32)


def ridge_contour(x0, x1, y_base, bumps=(), waves=((2.0, 47.0, 0.3),), n=300, y_foot=None):
    """long rolling ground line from x0 to x1: y_base minus bumps (xc, half_w, height, power) plus sine waves
    (amp, wavelength, phase); closed down to y_foot at both ends when given."""
    xs = np.linspace(x0, x1, n)
    ys = np.full(n, float(y_base))
    for b in bumps:
        bx, bw, bh = b[:3]; pw = b[3] if len(b) > 3 else 1.0
        ys -= G.bump(xs, bx, bw, bh, pw)
    for a, wl, ph in waves:
        ys += a * np.sin(2 * math.pi * xs / wl + ph)
    p = np.stack([xs, ys], 1)
    if y_foot is not None:
        p = np.vstack([[[x0, y_foot]], p, [[x1, y_foot]]])
    return p.astype(np.float32)


def arch_bridge(c, x, y_road, r_out=13.0, r_in=8.6, pier_w=4.0, foot_y=None, cols=('madder', 'buff', 'mustard', 'buff'),
                pier_col='olive', seed=0, group=None, n_vous=9):
    """Bayeux arch bridge under the road: a voussoir ring of alternating colours on two piers (call after the road,
    before the river, so the road deck sits on it and the water runs through the arch)."""
    cy = y_road + r_out * 0.92
    foot_y = foot_y if foot_y is not None else cy + 6.0
    ang = np.linspace(math.pi, 2 * math.pi, n_vous + 1)
    polys = []
    for k in range(n_vous):
        a0, a1 = ang[k], ang[k + 1]
        aa = np.linspace(a0, a1, 8)
        outer = np.stack([x + r_out * np.cos(aa), cy + r_out * np.sin(aa)], 1)
        inner = np.stack([x + r_in * np.cos(aa[::-1]), cy + r_in * np.sin(aa[::-1])], 1)
        polys.append(np.vstack([outer, inner]).astype(np.float32))
    for k, pv in enumerate(polys):
        win = c.win_of_polys([pv], 1.5)
        mk = c.mask([pv], win).astype(bool)
        am = 0.5 * (ang[k] + ang[k + 1])
        c.fill(mk, win, P(cols[k % len(cols)]), angle=math.degrees(am) + 90, couch=False, seed=seed * 5 + k, group=group, name='voussoir',
               erode=(0.12, 0.18), min_area_mm2=0.3)
        c.outline_mm(np.vstack([pv, pv[:1]]), ink_for(P(cols[k % len(cols)])), width=0.95, L=2.4, seed=seed * 3 + k, group=group, min_len_mm=0.5)
    for sg in (-1, 1):
        xa, xb = sorted([x + sg * r_in, x + sg * (r_out + pier_w - (r_out - r_in))])
        xa, xb = (x + sg * r_in, x + sg * (r_out + 1.5)) if sg > 0 else (x - r_out - 1.5, x - r_in)
        pr = np.array([(xa, cy), (xb, cy), (xb + sg * 0.8, foot_y), (xa - sg * 0.3, foot_y)], np.float32)
        win = c.win_of_polys([pr], 1.5)
        mk = c.mask([pr], win).astype(bool)
        c.fill(mk, win, P(pier_col), angle=90, couch=False, seed=seed + 20 + (sg > 0), group=group, name='pier', erode=(0.12, 0.18),
               min_area_mm2=0.3)
        c.outline_mm(np.vstack([pr, pr[:1]]), ink_for(P(pier_col)), width=1.0, L=2.6, seed=seed + 30 + (sg > 0), group=group)
        c.occlude(mk, win)
    for pv in polys:
        c.occlude_polys([pv])


# ---------------------------------------------------------------------------- water
def river(c, path, width=17.0, seed=0, group=None, bank_col='olive', wave_cols=('woad', 'olive'), wave_len=13.0,
          wave_amp=1.7, pair_gap=1.45, line_w=1.15, occlude=True, widen=0.0):
    """Bayeux water: each bank a PAIR of olive stem lines, inside two pairs of wavy lines (woad / olive), linen
    between.  widen: extra width (mm) gained along the path (the river opens toward the viewer)."""
    Pp = G.resample(G.catmull(path, 10), 0.4)
    Pp = G.wobble(Pp, 0.4, 25.0, seed)
    s = G.arclen(Pp)
    hw = width / 2 + 0.5 * widen * np.clip(s / min(s[-1], 70.0), 0, 1) ** 0.8
    for j, sgn in enumerate((-1, 1)):
        bank = G.wobble(G.offset(Pp, sgn * hw), 0.3, 9.0, seed + 3 + j)
        c.outline_mm(bank, P(bank_col), width=1.3, seed=seed * 5 + j, group=group)
        c.outline_mm(G.offset(bank, sgn * 1.55), P(bank_col), width=1.05, L=3.0, seed=seed * 5 + 7 + j, group=group, h0=0.45, hamp=0.38)
    for k, (a, col) in enumerate(zip((-0.40, 0.40), wave_cols)):
        ph = k * 1.7 + seed
        wv = a * hw + wave_amp * np.clip(hw / 8.0, 0.25, 1.0) * np.sin(2 * math.pi * s / wave_len + ph)
        for q in (0, 1):
            ln = G.offset(Pp, wv + (q - 0.5) * pair_gap)
            c.outline_mm(ln, P(col), width=line_w, L=2.8, seed=seed * 11 + 2 * k + q, group=group, h0=0.42, hamp=0.36)
    if occlude:
        c.occlude_polys([G.band(Pp, -hw - 2.5, hw + 2.5)])
    return Pp


# ---------------------------------------------------------------------------- road
def road(c, path, width=6.0, cols=('road_gold', 'road_crimson', 'road_blue', 'road_green'), seg=(30.0, 40.0), slant_deg=28.0, seed=0,
         group='road', bar_spacing=3.6, cap=0.15, outline='#2E1E18', occlude=True, start_k=0):
    """ONE road, laid along its length and couched across, in segments that alternate the four house colours
    (Bayeux alternation), blue-black outlines along both edges and across every colour change."""
    Pp = G.resample(G.catmull(path, 12), 0.35)
    Pp = G.wobble(Pp, 0.25, 30.0, seed)
    s = G.arclen(Pp)
    r = np.random.default_rng(seed)
    cuts = [0.0]
    while cuts[-1] < s[-1]:
        cuts.append(cuts[-1] + r.uniform(*seg))
    cuts[-1] = s[-1] + 50
    hw = width / 2
    poly = G.band(Pp, -hw, hw)
    win = c.win_of_polys([poly], 3.0)
    x0, y0, x1, y1 = win
    full = c.mask([poly], win).astype(bool)
    sp, tp = path_coords(full.shape, Pp * c.PX - np.array([x0, y0], np.float32))
    u = sp / c.PX + (tp / c.PX) * math.tan(math.radians(slant_deg))
    fld = _field_along(c, win, [Pp], 1.2)
    for k in range(len(cuts) - 1):
        mk = full & (u >= cuts[k]) & (u < cuts[k + 1])
        col = P(cols[(k + start_k) % len(cols)])
        c.fill(mk, win, col, field=fld, couch=True, bar_spacing=bar_spacing, tie=3.4, seed=seed * 101 + k, group=group,
               name=f'road_{k}', erode=(0.22, 0.38), cap=cap, maxturn_deg=35, min_area_mm2=0.3)
    for j, sgn in enumerate((-1, 1)):
        c.outline_mm(G.offset(Pp, sgn * (hw + 0.1)), outline, width=1.2, seed=seed * 3 + j, group=group)
        c.underdraw(G.offset(Pp, sgn * (hw + 0.45)), 0.6, seed=seed + 40 + j)
    nrm = G.normals(Pp); tng = G.tangents(Pp)
    for k in range(1, len(cuts) - 1):
        i = int(np.clip(np.searchsorted(s, cuts[k]), 0, len(Pp) - 1))
        a = math.radians(slant_deg)
        # separator across the road at the slant: points with s + t*tan = cut
        ts = np.linspace(-hw - 0.2, hw + 0.2, 8)
        pts = np.array([Pp[i] + nrm[i] * t - tng[i] * t * math.tan(a) for t in ts], np.float32)
        c.outline_mm(pts, outline, width=1.0, L=2.6, seed=seed * 7 + k, group=group, min_len_mm=0.5)
    if occlude:
        c.occlude_polys([G.band(Pp, -hw - 0.7, hw + 0.7)])
    return Pp


# ---------------------------------------------------------------------------- ploughed strips
def ploughed(c, poly, angle_deg=62.0, strip_w=(5.0, 7.5), cols=('mustard', 'olive', 'buff', 'madder'), furrows=2, seed=0, group=None,
             outline='#33241A', occlude=True, furrow_cols=('madder', 'forest')):
    """ploughed field: a field outline (poly, mm) cut into narrow strips running at angle_deg (the furrow direction),
    widths jittered, alternating dyes, each strip laid along the furrows with stem-stitched furrow lines."""
    q = np.asarray(G.catmull(poly, 6, closed=True), np.float32)
    r = np.random.default_rng(seed)
    win = c.win_of_polys([q], 3.0)
    x0, y0, x1, y1 = win
    full = c.mask([q], win).astype(bool)
    a = math.radians(angle_deg)
    d = np.array([math.cos(a), math.sin(a)], np.float32); n = np.array([-d[1], d[0]], np.float32)
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32) / c.PX
    u = xs * n[0] + ys * n[1]
    um = u[full]
    u0, u1 = float(um.min()), float(um.max())
    cuts = [u0 - 0.1]
    while cuts[-1] < u1:
        cuts.append(cuts[-1] + r.uniform(*strip_w))
    fld = G.const_field(full.shape, angle_deg)
    cen = q.mean(0)
    span = 2 * float(np.abs((q - cen) @ d).max()) + 10
    for k in range(len(cuts) - 1):
        mk = full & (u >= cuts[k]) & (u < cuts[k + 1])
        c.fill(mk, win, P(cols[k % len(cols)]), field=fld, couch=True, bar_spacing=5.0, tie=4.5, seed=seed * 13 + k, group=group,
               name=f'plough_{k}', erode=(0.25, 0.35), min_area_mm2=1.0)
        # furrows (inside the strip) and the strip edge
        for f in range(furrows):
            t = cuts[k] + (cuts[k + 1] - cuts[k]) * (f + 1) / (furrows + 1)
            base = cen + n * (t - float(cen @ n))
            ln = G.resample(np.stack([base - d * span / 2, base + d * span / 2]), 0.5)
            ln = G.wobble(ln, 0.25, 15.0, seed + 7 * k + f)
            inside = full[np.clip((ln[:, 1] * c.PX - y0).astype(int), 0, y1 - y0 - 1), np.clip((ln[:, 0] * c.PX - x0).astype(int), 0, x1 - x0 - 1)]
            ok = (ln[:, 0] * c.PX >= x0) & (ln[:, 0] * c.PX < x1) & (ln[:, 1] * c.PX >= y0) & (ln[:, 1] * c.PX < y1) & inside
            idx = np.nonzero(ok)[0]
            if len(idx) > 6:
                seg = ln[idx[0] + 2:idx[-1] - 1]
                if len(seg) > 3:
                    c.outline_mm(seg, P(furrow_cols[(k + f) % len(furrow_cols)]), width=0.8, L=2.6, seed=seed * 9 + k * 3 + f, group=group,
                                 h0=0.45, hamp=0.36)
        if k > 0:
            base = cen + n * (cuts[k] - float(cen @ n))
            ln = G.resample(np.stack([base - d * span / 2, base + d * span / 2]), 0.5)
            inside = full[np.clip((ln[:, 1] * c.PX - y0).astype(int), 0, y1 - y0 - 1), np.clip((ln[:, 0] * c.PX - x0).astype(int), 0, x1 - x0 - 1)]
            ok = (ln[:, 0] * c.PX >= x0) & (ln[:, 0] * c.PX < x1) & (ln[:, 1] * c.PX >= y0) & (ln[:, 1] * c.PX < y1) & inside
            idx = np.nonzero(ok)[0]
            if len(idx) > 4:
                c.outline_mm(ln[idx[0]:idx[-1] + 1], outline, width=1.0, L=3.0, seed=seed * 5 + k, group=group)
    c.outline_mm(np.vstack([q, q[:1]]), outline, width=1.2, seed=seed + 77, group=group)
    if occlude:
        c.occlude(full, win)


# ---------------------------------------------------------------------------- heraldic: pennant, crown
def pennant(c, x, y_top, pole_len, col, direction=1, length=17.0, height=7.5, seed=0, group=None, pole_col='#46301C',
            cap=0.20, wave=1.0):
    """house-colour pennant on a couched pole: swallow-tailed, slightly raised padded satin (heraldic register)."""
    PX = c.PX
    pole = np.array([[x, y_top + pole_len], [x, y_top - 1.0]], np.float32)
    gid = c.group(group) if isinstance(group, (str, type(None))) else group
    CTX['group'] = gid; CTX['region'] = OUTLINE_REGION
    S.cord_path(c.m, G.resample(pole, 0.5) * PX, colour(pole_col), PX, width=1.0, h0=0.5, hamp=0.45, seed=seed, tie=3.0)
    CTX['region'] = 0
    L, h = length, height
    us = np.linspace(0, 1, 24)
    top = np.stack([x + direction * us * L, y_top + 0.5 + us * h * 0.30 + wave * np.sin(us * math.pi * 1.6) * 0.9], 1)
    bot = np.stack([x + direction * us * L, y_top + 0.5 + h - us * h * 0.30 + wave * np.sin(us * math.pi * 1.6) * 0.9], 1)
    tip_mid = np.array([[x + direction * L * 0.74, y_top + 0.5 + h * 0.5 + wave * 0.3]], np.float32)
    poly = np.vstack([top, tip_mid, bot[::-1]]).astype(np.float32)
    win = c.win_of_polys([poly], 3.0)
    mk = c.mask([poly], win).astype(bool) & ~c.occ[win[1]:win[3], win[0]:win[2]]
    pad = S.pad_dome(mk, PX, 1.0, 1.4)
    sub = c.m['base'][win[1]:win[3], win[0]:win[2]]
    sub[:] = np.maximum(sub, pad)
    fld = _field_along(c, win, [0.5 * (top + bot)], 1.0)
    c.fill(mk, win, colour(P(col)), field=fld, couch=False, pitch=0.45, matid=SILK, h0=0.08, hamp=0.30, r_fac=0.6, bmul=1.0,
           cov=0.0, seed=seed, group=group, name='pennant', erode=(0.12, 0.2), cap=cap, maxlen=40, nlots=2, lot_spread=0.04)
    c.outline_mm(np.vstack([poly, poly[:1]]), WARM, width=0.95, L=2.4, seed=seed + 5, group=group, h0=0.6, hamp=0.4, clip=False)
    c.occlude(mk, win)
    c.occlude_polys([np.array([[x - 0.8, y_top - 1], [x + 0.8, y_top - 1], [x + 0.8, y_top + pole_len], [x - 0.8, y_top + pole_len]])])
    return poly


def crown(c, cx, y_base, w=26.0, h=17.0, seed=0, group=None, jewels=('crimson', 'blue', 'crimson')):
    """heraldic crown: couched gold (contour-parallel pairs, crimson silk ties) on a padded base, padded satin jewels."""
    from chron.fields import contour_parallel_field
    PX = c.PX
    bh = 0.36 * h
    pts = [(-w / 2, 0), (-w / 2, -bh), (-w / 2 - 1.5, -h * 0.92), (-w / 4, -bh - 1.5), (-w / 9, -bh - 2.0), (0, -h), (w / 9, -bh - 2.0),
           (w / 4, -bh - 1.5), (w / 2 + 1.5, -h * 0.92), (w / 2, -bh), (w / 2, 0)]
    poly = np.array([(cx + a, y_base + b) for a, b in pts], np.float32)
    poly = G.catmull(np.vstack([poly]), 3, closed=True)
    win = c.win_of_polys([poly], 3.0)
    x0, y0, x1, y1 = win
    mk = c.mask([poly], win).astype(bool)
    base = S.pad_dome(mk, PX, 0.8, 1.6)
    c.m['base'][y0:y1, x0:x1] = np.maximum(c.m['base'][y0:y1, x0:x1], base)
    gid = c.group(group) if isinstance(group, (str, type(None))) else group
    rid = c.new_region(dict(name='crown', group=gid))
    CTX['group'] = gid; CTX['region'] = rid
    fld = contour_parallel_field(mk, PX, 0.5)
    lab = np.where(mk, rid, -1).astype(np.int32)
    sub = S.view(c.m, x0, y0, x1, y1)
    S.metal_couch(sub, lab, rid, fld, PX, pitch=1.0, seed=seed, tie_col=colour('#8E1E18'), h0=0.55, hamp=0.32, tarnish=0.04)
    CTX['region'] = 0
    # jewels on the band
    for k, jc in enumerate(jewels):
        jx = cx + (k - (len(jewels) - 1) / 2) * w * 0.3
        jy = y_base - bh * 0.5
        circ = np.stack([jx + 1.5 * np.cos(np.linspace(0, 6.28, 20)), jy + 1.3 * np.sin(np.linspace(0, 6.28, 20))], 1)
        jw = c.win_of_polys([circ], 2.0)
        jm = c.mask([circ], jw).astype(bool)
        pd = S.pad_dome(jm, PX, 1.3, 1.0)
        c.m['base'][jw[1]:jw[3], jw[0]:jw[2]] = np.maximum(c.m['base'][jw[1]:jw[3], jw[0]:jw[2]], pd)
        c.fill(jm, jw, P(jc), field=G.const_field(jm.shape, 70), couch=False, pitch=0.42, matid=SILK, h0=0.1, hamp=0.3, r_fac=0.6,
               bmul=1.0, cov=0.0, seed=seed + 10 + k, group=group, name='jewel', erode=None, clip=False, cap=0.2, min_area_mm2=0.2,
               hbias=0.4)
    c.outline_mm(np.vstack([poly, poly[:1]]), WARM, width=0.9, L=2.2, seed=seed + 3, group=group, h0=0.65, hamp=0.4, clip=False)
    c.occlude(mk, win)
    return poly


# ---------------------------------------------------------------------------- trees
def leaf_poly(base, tip, width, n=28, fat=0.42):
    """lanceolate leaf polygon from base to tip (mm), widest at `fat` of its length."""
    base = np.asarray(base, np.float32); tip = np.asarray(tip, np.float32)
    ax = tip - base; L = float(np.linalg.norm(ax)) + 1e-6
    t = ax / L; nrm = np.array([-t[1], t[0]], np.float32)
    u = np.linspace(0, 1, n)
    k = np.where(u < fat, np.sin(0.5 * math.pi * u / fat), np.clip(np.cos(0.5 * math.pi * (u - fat) / (1 - fat)), 0, 1) ** 0.9)
    hw = 0.5 * width * k
    s1 = base + u[:, None] * ax + nrm * hw[:, None]
    s2 = base + u[:, None] * ax - nrm * hw[:, None]
    return np.vstack([s1, s2[::-1][1:-1]]).astype(np.float32)


def palmette(c, base, ang_deg, length, n=5, spread=110.0, width=None, cols=('olive', 'sage'), seed=0, group=None, outline=None,
             vein='forest'):
    """a fan of lanceolate lobes radiating from `base` (mm) around direction ang_deg (image coords, y down):
    the Bayeux tree leaf.  Returns the lobe polygons."""
    r = np.random.default_rng(seed)
    width = width or 0.30 * length
    polys = []
    for k in range(n):
        t = (k - (n - 1) / 2) / max((n - 1) / 2, 1)
        a = math.radians(ang_deg + t * spread / 2 + r.uniform(-4, 4))
        L = length * (1.0 - 0.28 * abs(t)) * r.uniform(0.94, 1.06)
        b0 = np.asarray(base, np.float32)
        tip = b0 + np.array([math.cos(a), math.sin(a)], np.float32) * L
        lp = leaf_poly(b0 + (tip - b0) * 0.06, tip, width * (1.0 - 0.2 * abs(t)), fat=0.55)
        polys.append((lp, tip, a))
    # centre lobe last = nearest? draw outer first into occupancy so the centre overlaps them: process centre first
    order = sorted(range(n), key=lambda k: abs(k - (n - 1) / 2))
    for j, k in enumerate(order):
        lp, tip, a = polys[k]
        win = c.win_of_polys([lp], 1.5)
        mk = c.mask([lp], win).astype(bool)
        col = P(cols[k % len(cols)])
        c.fill(mk, win, col, angle=math.degrees(a), couch=True, bar_spacing=3.4, tie=3.0, seed=seed * 7 + k, group=group, name='lobe',
               erode=(0.18, 0.25), maxturn_deg=25, min_area_mm2=0.4, model=0.14)
        c.outline_mm(np.vstack([lp, lp[:1]]), outline if outline is not None else ink_for(col), width=0.85, L=2.4,
                     seed=seed * 3 + k, group=group, min_len_mm=0.8)
        c.occlude(mk, win)
    return [p[0] for p in polys]


def tree(c, x, y_base, h, trunk_cols=('terracotta', 'mustard', 'woad', 'olive'), leaf_cols=('olive', 'sage', 'forest', 'sage', 'olive'),
         branch_cols=('madder', 'mustard'), seed=0, group=None, outline=None, lean=0.0, leaf_w=0.12):
    """Bayeux interlace tree: a banded trunk; at the top two branches cross in a knot and curl outward; palmette
    leaves (fans of lanceolate lobes) at the branch ends and one crowning palmette; branches as narrow laid bands."""
    PX = c.PX
    T = lambda pts: np.array([(x + (a - lean * b) * h, y_base + b * h) for a, b in pts], np.float32)
    lc = list(leaf_cols)
    # palmettes (nearest): crown, upper pair, lower drooping pair
    pal_specs = [((0.0, -0.80), -90, 0.24, 5, 100), ((-0.20, -0.70), -140, 0.20, 5, 95), ((0.20, -0.70), -40, 0.20, 5, 95),
                 ((-0.27, -0.55), 172, 0.17, 4, 80), ((0.27, -0.55), 8, 0.17, 4, 80)]
    for k, (bp, ang, ln, nl, spr) in enumerate(pal_specs):
        base = T([bp])[0]
        palmette(c, base, ang + math.degrees(lean) * 0, ln * h, n=nl, spread=spr, width=0.30 * ln * h,
                 cols=(lc[k % len(lc)], lc[(k + 1) % len(lc)]), seed=seed * 11 + k, group=group)
    # branches: lyre curves from the trunk top to each palmette base, the first two crossing (interlace knot)
    S0 = (0.0, -0.44)
    branches = [[S0, (0.06, -0.52), (-0.05, -0.60), (-0.20, -0.70)],
                [S0, (-0.06, -0.52), (0.05, -0.60), (0.20, -0.70)],
                [S0, (-0.04, -0.50), (-0.16, -0.50), (-0.27, -0.55)],
                [S0, (0.04, -0.50), (0.16, -0.50), (0.27, -0.55)],
                [S0, (0.0, -0.60), (0.0, -0.80)]]
    for k, ctrl in enumerate(branches):
        b = G.resample(G.catmull(T(ctrl), 12), 0.35)
        bw = 0.032 * h * (1.0 if k < 2 else 0.85)
        poly = G.band(b, -bw / 2, bw / 2)
        win = c.win_of_polys([poly], 2.0)
        mk = c.mask([poly], win).astype(bool)
        fld = _field_along(c, win, [b], 0.6)
        bc = P(branch_cols[k % len(branch_cols)])
        c.fill(mk, win, bc, field=fld, couch=False, seed=seed * 5 + 20 + k, group=group, name='branch', erode=(0.12, 0.18), maxlen=120,
               min_area_mm2=0.3, model=0.0, grad=0.0)
        for sg in (-1, 1):
            c.outline_mm(G.offset(b, sg * (bw / 2 + 0.05)), outline or ink_for(bc), width=0.85, L=2.5, seed=seed * 9 + 2 * k + (sg > 0),
                         group=group, min_len_mm=0.8)
        c.occlude(mk, win)
    # trunk: banded, slightly curved
    sp = G.catmull(T([(0.0, 0.0), (0.012, -0.22), (0.0, -0.45)]), 10)
    nb = len(trunk_cols)
    wb, wt = 0.075 * h, 0.048 * h
    ws = np.linspace(wb, wt, len(sp))
    poly = np.vstack([G.offset(sp, -ws / 2), G.offset(sp, ws / 2)[::-1]])
    win = c.win_of_polys([poly], 2.0)
    x0, y0, x1, y1 = win
    full = c.mask([poly], win).astype(bool)
    ys = (np.arange(y0, y1)[:, None] + 0.5) / PX
    xs = (np.arange(x0, x1)[None, :] + 0.5) / PX
    tt = (y_base - ys + (xs - x) * 0.30) / (0.45 * h)
    for k in range(nb):
        mk = full & (tt >= k / nb) & ((tt < (k + 1) / nb) if k < nb - 1 else True)
        c.fill(mk, win, P(trunk_cols[k]), angle=90, couch=False, seed=seed * 11 + k, group=group, name='trunk', erode=(0.15, 0.2),
               min_area_mm2=0.3)
    for sg in (-1, 1):
        c.outline_mm(G.offset(sp, sg * (ws / 2 + 0.05)), outline or ink_for(P('madder')), width=0.95, seed=seed + 60 + (sg > 0), group=group)
    for k in range(1, nb):
        i = int(k / nb * (len(sp) - 1)); p0 = sp[i]; w_ = ws[i] / 2 + 0.3
        c.outline_mm(np.array([(p0[0] - w_, p0[1] - w_ * 0.30), (p0[0] + w_, p0[1] + w_ * 0.30)], np.float32), outline or ink_for(P('madder')),
                     width=0.8, L=2.2, seed=seed + 70 + k, group=group, min_len_mm=0.5)
    c.occlude(full, win)


# ---------------------------------------------------------------------------- border
def border_rules(c, x0, x1, y_bot, seed=0, group=None):
    """the pair of rules between the upper border and the main register (blue-black + red-brown stem lines)."""
    for k, (dy, col, w) in enumerate([(0.0, INK, 1.35), (2.6, REDBROWN, 1.25)]):
        xs = np.linspace(x0, x1, int((x1 - x0) / 1.0))
        ys = y_bot + dy + 0.35 * np.sin(xs / 37.0 + seed) + 0.2 * np.sin(xs / 11.0 + 2 * seed)
        c.outline_mm(np.stack([xs, ys], 1), col, width=w, seed=seed * 10 + k, group=group)
        c.underdraw(np.stack([xs, ys + 0.4], 1), 0.6, seed=seed + k)


def diag_bar(c, bx, y_top, y_bot, slant=1, width=4.6, col='terracotta', seed=0, group=None, lean_mm=None):
    lean = lean_mm if lean_mm is not None else 0.42 * (y_bot - y_top)
    a = np.array([bx - slant * lean / 2, y_top], np.float32); b = np.array([bx + slant * lean / 2, y_bot], np.float32)
    ln = G.resample(np.stack([a, b]), 0.5)
    poly = G.band(ln, -width / 2, width / 2)
    win = c.win_of_polys([poly], 2.0)
    mk = c.mask([poly], win).astype(bool)
    ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    c.fill(mk, win, P(col), angle=ang, couch=True, bar_spacing=4.5, tie=4.0, seed=seed, group=group, name='diag_bar', erode=(0.2, 0.3))
    for sg in (-1, 1):
        c.outline_mm(G.offset(ln, sg * (width / 2 + 0.1)), ink_for(P(col)), width=1.05, seed=seed * 3 + (sg > 0), group=group)
    c.occlude(mk, win)


def sprig(c, x, y_base, h, flower_cols=('woad', 'terracotta'), seed=0, group=None, lean=0.0, n_flowers=2):
    """millefleurs plant (border filler): stem-stitched stalk, laid leaves, five-petal flowers with a satin heart."""
    r = np.random.default_rng(seed)
    stalk = G.catmull([(x, y_base), (x + lean * h * 0.3 + r.uniform(-1, 1), y_base - 0.45 * h), (x + lean * h * 0.5, y_base - 0.85 * h)], 10)
    tops = [stalk[-1]]
    branches = []
    if n_flowers > 1:
        for sgn in (-1, 1)[:n_flowers - 1]:
            st = stalk[len(stalk) // 2]
            bp = G.catmull([st, st + np.array([sgn * 0.22 * h, -0.18 * h]), st + np.array([sgn * 0.30 * h, -0.36 * h])], 8)
            branches.append(bp); tops.append(bp[-1])
    # flowers (nearest)
    for k, tp in enumerate(tops):
        fc = P(flower_cols[k % len(flower_cols)])
        rp = 0.085 * h
        for j in range(5):
            a = j * 2 * math.pi / 5 + r.uniform(-0.15, 0.15) - math.pi / 2
            pc = tp + np.array([math.cos(a), math.sin(a)]) * rp * 1.05
            ang = np.linspace(0, 2 * math.pi, 18, endpoint=False)
            pet = np.stack([pc[0] + rp * 0.75 * np.cos(ang), pc[1] + rp * 0.75 * np.sin(ang)], 1)
            win = c.win_of_polys([pet], 1.5)
            mk = c.mask([pet], win).astype(bool)
            c.fill(mk, win, fc, angle=math.degrees(a), couch=False, pitch=0.7, seed=seed * 31 + k * 7 + j, group=group, name='petal',
                   erode=(0.12, 0.15), min_area_mm2=0.3)
            c.outline_mm(np.vstack([pet, pet[:1]]), ink_for(fc), width=0.8, L=2.0, seed=seed * 3 + j + 10 * k, group=group, min_len_mm=0.5)
            c.occlude(mk, win)
        ang = np.linspace(0, 2 * math.pi, 14, endpoint=False)
        hrt = np.stack([tp[0] + rp * 0.5 * np.cos(ang), tp[1] + rp * 0.5 * np.sin(ang)], 1)
        win = c.win_of_polys([hrt], 1.5)
        mk = c.mask([hrt], win).astype(bool)
        c.fill(mk, win, P('mustard'), angle=30, couch=False, pitch=0.5, matid=WOOL, seed=seed + 90 + k, group=group, name='heart',
               erode=None, clip=False, min_area_mm2=0.2, hbias=0.2, h0=0.15)
        c.occlude(mk, win)
    # leaves along the stalk
    for j, t in enumerate((0.35, 0.6)):
        i = int(t * (len(stalk) - 1)); bp = stalk[i]
        for sgn in (-1, 1):
            tipv = np.array([sgn * 0.20 * h, -0.08 * h * (1 + j * 0.3)])
            u = np.linspace(0, 1, 16)
            nrm = np.array([-tipv[1], tipv[0]]) / (np.linalg.norm(tipv) + 1e-6)
            wv = 0.05 * h * np.sin(u * math.pi)
            side1 = bp + u[:, None] * tipv + nrm * wv[:, None]
            side2 = bp + u[:, None] * tipv - nrm * wv[:, None]
            leaf = np.vstack([side1, side2[::-1]]).astype(np.float32)
            win = c.win_of_polys([leaf], 1.5)
            mk = c.mask([leaf], win).astype(bool)
            c.fill(mk, win, P('sage' if (j + (sgn > 0)) % 2 else 'olive'), angle=math.degrees(math.atan2(tipv[1], tipv[0])), couch=False,
                   pitch=0.75, seed=seed * 17 + j * 2 + (sgn > 0), group=group, name='leaf', erode=(0.12, 0.15), min_area_mm2=0.3)
            c.outline_mm(np.vstack([leaf, leaf[:1]]), ink_for(P('olive')), width=0.8, L=2.0, seed=seed + 40 + j * 2 + (sgn > 0), group=group, min_len_mm=0.5)
            c.occlude(mk, win)
    for k, b in enumerate([stalk] + branches):
        c.outline_mm(b, P('olive'), width=1.15, L=2.8, seed=seed + 70 + k, group=group)


def beast(c, which, box, flip=False, col=None, detail_col=None, seed=0, group=None, outline=None, src_path=None):
    """border beast from the game's vignette (vignette_red / vignette_blue lion): silhouette + interior detail lines
    extracted from the art, re-stitched as laid-and-couched wool with stem outlines.  box = (x0, y0, x1, y1) mm."""
    from .beasts import lion_from_vignette
    from chron.fields import select_field
    PX = c.PX
    x0m, y0m, x1m, y1m = box
    Wpx, Hpx = int((x1m - x0m) * PX), int((y1m - y0m) * PX)
    B = lion_from_vignette(which, Wpx, Hpx, flip=flip)
    ox, oy = int(x0m * PX + (Wpx - B['mask'].shape[1]) / 2), int(y0m * PX + (Hpx - B['mask'].shape[0]) / 2)
    hh, ww = B['mask'].shape
    win = (ox, oy, ox + ww, oy + hh)
    col = col or ('terracotta' if which == 'red' else 'woad')
    detail_col = detail_col or ('madder' if which == 'red' else 'woad_dark')
    mk = B['mask'] > 0
    from chron.fields import region_axis_field
    fld = region_axis_field(mk, PX, -8.0 if not flip else 8.0, 16.0, 22.0, seed, (ox / PX, oy / PX))
    c.fill(mk, win, P(col), field=fld, couch=True, bar_spacing=3.8, tie=3.4, seed=seed, group=group, name=f'lion_{which}',
           erode=(0.3, 0.35), maxturn_deg=40)
    outline = ink_for(P(col)) if outline is None else outline
    for k, p in enumerate(B['details']):
        c.outline(p + np.array([ox, oy], np.float32), P(detail_col), width=0.85, L=2.4, seed=seed * 13 + k, group=group, h0=0.45,
                  hamp=0.38, clip=False, min_len_mm=1.0)
    for k, p in enumerate(B['contours']):
        c.outline(p + np.array([ox, oy], np.float32), outline, width=1.15, L=3.0, seed=seed * 7 + k, group=group, clip=False)
    if B.get('eye') is not None:
        e = B['eye'] / PX + np.array([ox, oy]) / PX
        ang = np.linspace(0, 2 * math.pi, 12, endpoint=False)
        circ = np.stack([e[0] + 0.7 * np.cos(ang), e[1] + 0.6 * np.sin(ang)], 1)
        w2 = c.win_of_polys([circ], 1.0)
        c.fill(c.mask([circ], w2).astype(bool), w2, P('mustard'), angle=0, couch=False, pitch=0.45, seed=seed + 3, group=group,
               erode=None, clip=False, min_area_mm2=0.1, hbias=0.6, h0=0.3)
    c.occlude(mk, win)
    return B


# ---------------------------------------------------------------------------- towns from game-model elevations
CLASS = dict(stone='wall', stone_dark='wall', plaster='plaster', roof_civic='roof', roof_shingle='roof', roof_thatch='roof',
             roof_thatch_old='roof', roof_moss='roof', roof_tile='roof', roof_tile_old='roof', roof_slate='roof', roof_lead='roof',
             slate='roof', thatch='roof', window='opening', wood_dark='timber', black='opening', cloth='cloth', team='cloth',
             white='cloth', gold='gold', wood='timber', plank='timber', fire='skip')


def town(c, models, x_center, y_base, width_mm, seed=0, group=None, style=None, tilt_deg=0.0, front='+z', min_part_mm2=2.2,
         outline=None, outline_w=0.95, pennant_col=None, pennant_dir=1, pennant_pole=13.0, return_info=False, vstretch=1.0,
         wobble=(0.38, 0.70), skip=(), model=0.16, grad=0.07):
    """a walled town re-stitched from game-model elevations.  models: name or list of (name, dx_mm, dy_mm, width_mm)
    composed back -> front (later entries in front).  style: colour cycles per part class (Bayeux alternation)."""
    from .elevation import elevation
    PX = c.PX
    st = dict(wall=('stone', 'stone_warm', 'stone_dk'), tower=('mustard', 'sand', 'moss', 'stone'), plaster=('sand', 'stone'),
              roof=('terracotta', 'woad', 'madder', 'olive', 'terracotta', 'mustard'), opening=('woad_dark',), timber=('madder', 'brown'),
              cloth=('crimson',), gold=('mustard',), roof_bars=None)
    st.update(style or {})
    if isinstance(models, str):
        models = [(models, 0.0, 0.0, width_mm)]
    # compose label images on a common canvas-px grid
    Es = []
    for mdl in models:
        name, dx, dy, wmm = mdl[:4]
        vs = mdl[4] if len(mdl) > 4 else vstretch
        from .elevation import load_obj
        V, _, _, _ = load_obj(name)
        span = V[:, 0].max() - V[:, 0].min()
        E = elevation(name, wmm * PX / span, tilt_deg=tilt_deg, front=front, pad_px=4, vstretch=vs)
        Es.append((E, dx, dy))
    xs0, ys0, xs1, ys1 = [], [], [], []
    for E, dx, dy in Es:
        W_, H_ = E['size']
        ox = x_center * PX + dx * PX - E['origin_px'][0]
        oy = (y_base + dy) * PX - E['ground_y_px']
        xs0.append(ox); ys0.append(oy); xs1.append(ox + W_); ys1.append(oy + H_)
    gx0, gy0 = int(math.floor(min(xs0))), int(math.floor(min(ys0)))
    gx1, gy1 = int(math.ceil(max(xs1))), int(math.ceil(max(ys1)))
    Hh, Ww = gy1 - gy0, gx1 - gx0
    lab = np.zeros((Hh, Ww), np.int32)            # part key: model*100000 + island*64 + mat + 1
    cls_of = {}
    for mi, (E, dx, dy) in enumerate(Es):
        ox = int(round(x_center * PX + dx * PX - E['origin_px'][0])) - gx0
        oy = int(round((y_base + dy) * PX - E['ground_y_px'])) - gy0
        H_, W_ = E['mat'].shape
        sel = E['mat'] >= 0
        key = mi * 100000 + E['island'] * 64 + E['mat'] + 1
        sub = lab[oy:oy + H_, ox:ox + W_]
        sub[sel[:sub.shape[0], :sub.shape[1]]] = key[:sub.shape[0], :sub.shape[1]][sel[:sub.shape[0], :sub.shape[1]]]
        for m_i, nm in enumerate(E['names']):
            cls_of[(mi, m_i)] = CLASS.get(nm, 'wall')
    # hand-drawn wobble: verticals waver, roofs tilt a little (the game geometry is too exact for embroidery)
    if wobble:
        from chron.util import vnoise
        yy, xx = np.mgrid[0:Hh, 0:Ww].astype(np.float32)
        dx = (vnoise(gx0 / PX, gy0 / PX, Hh, Ww, PX, 7.0, seed + 11, 2) * wobble[0] + vnoise(gx0 / PX, gy0 / PX, Hh, Ww, PX, 35.0, seed + 12, 1) * wobble[1]) * PX
        dy = (vnoise(gx0 / PX, gy0 / PX, Hh, Ww, PX, 7.0, seed + 13, 2) * wobble[0] + vnoise(gx0 / PX, gy0 / PX, Hh, Ww, PX, 35.0, seed + 14, 1) * wobble[1]) * PX
        lab = cv2.remap(lab.astype(np.float32), xx + dx * 2.2, yy + dy * 2.2, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT,
                        borderValue=0).astype(np.int32)
        del yy, xx, dx, dy
    # drop 'skip' parts, clean labels (mode filter), split into connected parts, merge tiny ones into neighbours
    def cls(key):
        if key <= 0: return None
        mi = key // 100000; m_ = (key % 100000) % 64 - 1
        return cls_of.get((mi, m_), 'wall')
    for k in np.unique(lab):
        if k > 0 and (cls(k) == 'skip' or cls(k) in skip):
            lab[lab == k] = 0
    # close tiny gaps between faces of the same island
    sil = (lab > 0).astype(np.uint8)
    sil = cv2.morphologyEx(sil, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    parts = np.zeros((Hh, Ww), np.int32)
    info = {}
    nid = 0
    for k in np.unique(lab):
        if k <= 0: continue
        n, cc, stt, _ = cv2.connectedComponentsWithStats((lab == k).astype(np.uint8), connectivity=4)
        for j in range(1, n):
            nid += 1
            parts[cc == j] = nid
            info[nid] = dict(key=int(k), cls=cls(k), area=int(stt[j, 4]))
    # merge small parts into the neighbour with the longest shared border (openings keep >= 0.9 mm2)
    minpx = min_part_mm2 * PX * PX
    for it in range(4):
        changed = False
        for pid in sorted(info, key=lambda q: info[q]['area']):
            if pid not in info: continue
            a = info[pid]['area']
            lim = 0.9 * PX * PX if info[pid]['cls'] in ('opening', 'gold') else minpx
            if a >= lim: continue
            m = (parts == pid).astype(np.uint8)
            ring = (cv2.dilate(m, np.ones((3, 3), np.uint8)) > 0) & (m == 0)
            nb = parts[ring]; nb = nb[nb > 0]
            if len(nb) == 0:
                parts[m > 0] = 0; info.pop(pid); changed = True; continue
            vals, cnts = np.unique(nb, return_counts=True)
            tgt = int(vals[np.argmax(cnts)])
            parts[m > 0] = tgt; info[tgt]['area'] += a; info.pop(pid); changed = True
        if not changed: break
    # fill holes inside the silhouette left by the cleaning
    holes = (sil > 0) & (parts == 0)
    if holes.any():
        d, li = cv2.distanceTransformWithLabels((parts == 0).astype(np.uint8), cv2.DIST_L2, 3, labelType=cv2.DIST_LABEL_PIXEL)
        zy, zx = np.nonzero(parts != 0)
        tab = np.concatenate([[0], parts[zy, zx]])
        parts[holes] = tab[li[holes]]
    # smooth part boundaries (majority) to remove pixel steps
    if parts.max() < 65535:
        parts = cv2.medianBlur(parts.astype(np.uint16), 5).astype(np.int32)
        parts[sil == 0] = 0
    win = (gx0, gy0, gx1, gy1)
    # clip to the canvas
    cx0, cy0, cx1, cy1 = max(gx0, 0), max(gy0, 0), min(gx1, c.W), min(gy1, c.H)
    parts = parts[cy0 - gy0:cy1 - gy0, cx0 - gx0:cx1 - gx0]
    win = (cx0, cy0, cx1, cy1)
    parts[c.occ[cy0:cy1, cx0:cx1]] = 0
    # per-part recipe
    cyc = {}
    ids = sorted([p for p in info if (parts == p).any()], key=lambda p: (info[p]['key'] // 64, p))
    isl_col = {}
    for pid in ids:
        mk = parts == pid
        ys, xs = np.nonzero(mk)
        hgt, wid = ys.max() - ys.min() + 1, xs.max() - xs.min() + 1
        cl = info[pid]['cls']
        if cl == 'wall' and hgt > 1.25 * wid:
            cl = 'tower'
        island = info[pid]['key'] // 64
        ck = (cl, island)
        if ck not in isl_col:
            cyc[cl] = cyc.get(cl, -1) + 1
            isl_col[ck] = st[cl][cyc[cl] % len(st[cl])] if st.get(cl) else 'buff'
        col = isl_col[ck]
        sd = seed * 1000 + pid
        if cl in ('opening',):
            c.fill(mk, win, P(col), angle=90, couch=False, style='split', L=2.2, pitch=0.6, seed=sd, group=group, name='opening',
                   erode=(0.08, 0.1), min_area_mm2=0.3, cap=0.13)
        elif cl == 'gold':
            c.fill(mk, win, P(col), angle=45, couch=False, pitch=0.5, matid=SILK, seed=sd, group=group, name='finial', erode=(0.05, 0.1),
                   min_area_mm2=0.2, cov=0.0, h0=0.15, hamp=0.3)
        else:
            if cl == 'roof':
                ang = 90.0 if hgt > 0.55 * wid else 0.0
            elif cl in ('tower', 'timber'):
                ang = 90.0
            else:
                ang = 0.0 if wid > hgt else 90.0
            area_mm2 = mk.sum() / PX / PX
            couch = area_mm2 > 18
            bar_col = None
            if cl == 'roof' and st.get('roof_bars'):
                bar_col = P(st['roof_bars'].get(col, col)) if isinstance(st['roof_bars'], dict) else None
            c.fill(mk, win, P(col), angle=ang, couch=couch, bar_spacing=3.6 if cl == 'roof' else 4.2, tie=3.4, seed=sd, group=group,
                   name=f'town_{cl}', erode=(0.15, 0.22), min_area_mm2=0.4, bar_col=bar_col, axis_bend=0.0,
                   model=model, grad=grad)
    lab_out = parts.copy()
    col_fn = None
    if outline is None:
        def col_fn(pc):
            a = c.ink_near(pc, int(0.6 * PX))
            return ink_for(a) if a is not None else colour('#2A2226')
    n_out = c.boundary_outlines(lab_out, win, outline or '#2A2226', width=outline_w, L=2.8, seed=seed, group=group,
                                min_len_px=int(1.2 * PX), col_fn=col_fn)
    # underdraw the silhouette (peeks out in the outline gaps)
    from chron import stitch as S_
    cs, _ = cv2.findContours((lab_out > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for k, cc in enumerate(cs):
        if len(cc) > 20:
            pts = (cc[:, 0, :].astype(np.float32) + np.array([cx0, cy0])) / PX
            c.underdraw(G.offset(G.resample(pts, 0.5), 0.3), 0.55, seed=seed + 300 + k)
    # pennant on the highest point
    top = None
    if pennant_col is not None:
        ys, xs = np.nonzero(lab_out > 0)
        i = np.argmin(ys)
        top = ((xs[i] + cx0) / PX, (ys[i] + cy0) / PX)
    occ = cv2.dilate((lab_out > 0).astype(np.uint8), np.ones((5, 5), np.uint8))
    c.occlude(occ, win)
    res = dict(win=win, top=top, n_parts=len(ids), n_outlines=n_out)
    return res
