"""Procedural dark walnut table top (planks, cathedral figure, pores, seams, scratches, water rings) as 2.5D maps.
Generated in the table frame (s along the grain, t across) and rotated into the world frame."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from s18common import *
from chron.color import hex_lin


def aniso(H, W, cs, ct, seed, octs=1):
    """anisotropic smooth noise in [-1, 1]-ish: correlation length cs px along x (the grain), ct px along y."""
    r = np.random.default_rng(seed)
    out = np.zeros((H, W), np.float32); amp = 1.0; tot = 0.0
    for o in range(octs):
        gh, gw = int(H / max(ct, 1)) + 4, int(W / max(cs, 1)) + 4
        g = r.standard_normal((gh, gw)).astype(np.float32)
        out += amp * cv2.resize(g, (int(gw * max(cs, 1)), int(gh * max(ct, 1))), interpolation=cv2.INTER_CUBIC)[:H, :W]
        tot += amp; amp *= 0.55; cs *= 0.5; ct *= 0.5
    return out / (tot * 1.0)


def make_table_frame(Ht, Wt, PX, seed=7):
    """(Ht x Wt) px table-frame maps.  1 px = 1/PX mm."""
    r = np.random.default_rng(seed)
    P = PX
    tt, ss = np.mgrid[0:Ht, 0:Wt].astype(np.float32)
    t_mm, s_mm = tt / P, ss / P
    # planks: random widths 230-340 mm
    edges = [0.0]
    while edges[-1] < Ht / P + 400:
        edges.append(edges[-1] + r.uniform(230, 340))
    edges = np.array(edges, np.float32)
    off = -r.uniform(30, 120)
    pid = np.clip(np.searchsorted(edges + off, t_mm, side='right') - 1, 0, len(edges) - 1)
    tone = r.uniform(0.80, 1.20, len(edges)).astype(np.float32)
    phase = r.uniform(0, 6.28, len(edges)).astype(np.float32)
    period = r.uniform(28, 50, len(edges)).astype(np.float32)
    dist_edge = np.minimum(t_mm - (edges + off)[pid], (edges + off)[np.minimum(pid + 1, len(edges) - 1)] - t_mm)
    # cathedral figure: growth rings distorted by a slow wobble (arches), crisp latewood lines, per-ring strength
    wob = 55 * aniso(Ht, Wt, 1100 * P, 260 * P, seed + 1, 2) + 8 * aniso(Ht, Wt, 260 * P, 40 * P, seed + 11, 2)
    phi = (t_mm + wob) / period[pid] + phase[pid]
    fr = phi - np.floor(phi)
    latew = np.exp(-((fr - 0.55) / 0.10) ** 2)                      # narrow dark band per ring
    strength = np.clip(0.75 + 0.55 * aniso(Ht, Wt, 300 * P, 150 * P, seed + 12, 2), 0.2, 1.4)
    ring = 1 - latew * strength
    st = (0.40 * aniso(Ht, Wt, 500 * P, 4.5 * P, seed + 3, 3) + 0.22 * aniso(Ht, Wt, 150 * P, 1.6 * P, seed + 4, 2) +
          0.15 * aniso(Ht, Wt, 60 * P, 0.8 * P, seed + 5, 2))
    broad = 0.5 * aniso(Ht, Wt, 700 * P, 120 * P, seed + 13, 2)
    g = 0.62 + 0.30 * (ring - 1) * 1.0 + 0.16 * st + 0.14 * broad
    g = np.clip(g * tone[pid], 0, 1.2)
    dark = np.array([0.0050, 0.0030, 0.0027], np.float32)
    mid = np.array([0.0172, 0.0100, 0.0067], np.float32)
    light = np.array([0.0380, 0.0225, 0.0138], np.float32)
    gg = np.clip(g, 0, 1)[..., None]
    alb = np.where(gg < 0.5, dark + (mid - dark) * (gg / 0.5), mid + (light - mid) * ((gg - 0.5) / 0.5))
    # open pores / dark flecks
    pores = (aniso(Ht, Wt, 14 * P, 0.7 * P, seed + 6) > 1.25).astype(np.float32)
    alb = alb * (1 - 0.45 * cv2.GaussianBlur(pores, (0, 0), 0.6 * P)[..., None])
    # plank seams: dark groove 1.4 mm
    seam = np.exp(-(dist_edge / 1.6) ** 2).astype(np.float32)
    bevel = np.exp(-((dist_edge - 3.2) / 1.2) ** 2).astype(np.float32)
    alb = alb * (1 - 0.85 * seam[..., None]) * (1 + 0.5 * bevel[..., None])
    h = (-0.55 * seam + 0.03 * st).astype(np.float32)
    # worn varnish map: spec strength, lower where the finish is worn / dusty
    wear = np.clip(0.95 + 0.18 * aniso(Ht, Wt, 400 * P, 150 * P, seed + 8, 2), 0.5, 1.4)
    spec = (wear * (1 + 0.7 * np.clip(st, -1, 1) * 0.5)).astype(np.float32)
    # scratches and rings
    sc = np.zeros((Ht, Wt), np.float32)
    for _ in range(int(Ht * Wt / P / P / 26000)):
        x, y = r.uniform(0, Wt), r.uniform(0, Ht)
        L = r.uniform(15, 260) * P
        a = r.normal(0, 0.10) + (0 if r.random() < 0.85 else r.uniform(-0.9, 0.9))
        cv2.line(sc, (int(x), int(y)), (int(x + L * np.cos(a)), int(y + L * np.sin(a))), float(r.uniform(0.15, 0.5)), 1, cv2.LINE_AA)
    alb = alb * (1 + 0.30 * sc[..., None])
    spec = spec * (1 + 0.8 * sc)
    rings = np.zeros((Ht, Wt), np.float32)
    for _ in range(3):
        cx, cy = r.uniform(0.15, 0.85) * Wt, r.uniform(0.15, 0.85) * Ht
        R = r.uniform(34, 46) * P
        cv2.circle(rings, (int(cx), int(cy)), int(R), float(r.uniform(0.5, 1.0)), max(1, int(1.8 * P)), cv2.LINE_AA)
    rings = cv2.GaussianBlur(rings, (0, 0), 1.2 * P) * (0.6 + 0.4 * np.clip(aniso(Ht, Wt, 25 * P, 25 * P, seed + 9), -1, 1))
    alb = alb * (1 + 0.5 * rings[..., None])
    spec = spec * (1 - 0.5 * rings)
    # a long grain tangent with chatoyant waver (+-7 deg)
    ang = 0.12 * aniso(Ht, Wt, 500 * P, 40 * P, seed + 10, 2)
    T = np.dstack([np.cos(ang), np.sin(ang)]).astype(np.float32)
    return dict(h=h, alb=alb.astype(np.float32), T=T, spec=np.clip(spec, 0.1, 3.0).astype(np.float32))


def make_walnut_world(Hpx, Wpx, PX, x0_mm, y0_mm, angle_deg, seed=7, PXT=1.0):
    """world-frame window (Hpx x Wpx at PX px/mm, top-left at x0_mm,y0_mm) with the grain at angle_deg (0 = along +x, +ve = rotating
    clockwise on screen).  The wood itself is generated at PXT <= 1.0 px/mm (finer than the 0.75 px/mm screen) and resampled."""
    a = math.radians(angle_deg)
    PXT = min(PXT, PX)
    s = PXT / PX
    Wp, Hp = int(Wpx * s), int(Hpx * s)               # window size in table-frame px
    Wt = int(abs(math.cos(a)) * Wp + abs(math.sin(a)) * Hp) + 12
    Ht = int(abs(math.cos(a)) * Hp + abs(math.sin(a)) * Wp) + 12
    Tf = make_table_frame(Ht, Wt, PXT, seed)
    cx_t, cy_t = Wt / 2, Ht / 2
    c, sn = math.cos(a), math.sin(a)
    M = np.array([[s * c, s * sn, cx_t - s * (c * Wpx / 2 + sn * Hpx / 2)], [-s * sn, s * c, cy_t - s * (-sn * Wpx / 2 + c * Hpx / 2)]], np.float32)
    out = {}
    for k in ('h', 'alb', 'spec', 'T'):
        out[k] = cv2.warpAffine(Tf[k], M, (Wpx, Hpx), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    del Tf
    Tx, Ty = out['T'][..., 0].copy(), out['T'][..., 1].copy()
    out['T'] = np.dstack([c * Tx - sn * Ty, sn * Tx + c * Ty]).astype(np.float32)
    out['mat'] = np.full((Hpx, Wpx), 6, np.uint8)
    out['cov'] = np.zeros((Hpx, Wpx), np.float32)
    return out
