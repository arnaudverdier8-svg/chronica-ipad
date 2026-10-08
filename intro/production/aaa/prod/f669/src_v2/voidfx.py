"""Cloth realism for the S09 void and the whole frame (v2): translation-invariant linen enrichment (thread-thickness
runs, slubs, per-thread tone), record-driven needle holes (entry / exit pairs at the real strand ends, anisotropic,
umber, with a displaced-thread rim and a soil halo), pen-pressure underdrawing and the ghosted imprint of the dense
stitching that used to lie here."""
import math
import numpy as np, cv2
from chron.util import vnoise, sstep, hash1
from chron.color import hex_lin
from chron.stitch import K_LAID, K_SPLIT, K_BAR, K_TIE, K_STEM, K_METAL, K_MTIE, K_CORD, K_CTIE, K_SATIN, K_SQUEEZE
from chron.linen import _vn


def aniso(m, sx, sy, seed, octaves=1):
    """value noise with different correlation lengths along x / y (mm), on the window grid of maps m."""
    H, W = m['h'].shape
    PX = m['PX']; ox, oy = m['origin_mm']
    return _vn(ox, oy, H, W, PX, sx, sy, seed, octaves)


def linen_enrich(m, strength=0.5, relief=1.18, strip=480, wander_mm=0.17, margin=8):
    """Break the periodic tabby on every bare-linen pixel of a window:
      * every thread wanders on its own (+-wander_mm, slowly along its length): uneven spacing and local sag, so the weave
        stops being a lattice (the base linen only wanders in broad lens-shaped patches),
      * per-thread thickness / tone with long correlation along the thread, slubs (thick runs),
      * a stronger weave relief for the raking light, a few soft hoop creases.
    Deterministic in sheet mm (identical in every frame and at every mip); processed in row strips with a margin (RAM)."""
    H, W = m['h'].shape
    PX = m['PX']; ox, oy = m['origin_mm']
    for r0 in range(0, H, strip):
        r1 = min(H, r0 + strip)
        a0 = max(0, r0 - margin); a1 = min(H, r1 + margin)
        sub = dict(PX=PX, origin_mm=(ox, oy + a0 / PX), h=m['h'][a0:a1], alb=m['alb'][a0:a1], T=m['T'][a0:a1], mat=m['mat'][a0:a1])
        if not (sub['mat'] == 0).any(): continue
        h2, a2, T2 = _enrich_strip(sub, strength, relief, wander_mm)
        m['h'][r0:r1] = h2[r0 - a0:r1 - a0]
        m['alb'][r0:r1] = a2[r0 - a0:r1 - a0]
        m['T'][r0:r1] = T2[r0 - a0:r1 - a0]
    return m


def _enrich_strip(m, strength, relief, wander_mm):
    mat = m['mat']
    lin0 = (mat == 0)
    h = m['h'].astype(np.float32); alb = m['alb'].astype(np.float32); T = m['T'].astype(np.float32)
    H, W = h.shape; PX = m['PX']
    pw, pf = 10 / 18.5, 10 / 19.0
    # --- per-thread wander: remap the cloth maps (linen pixels only)
    dx = wander_mm * PX * (1.2 * aniso(m, pw * 1.05, 20.0, 311) + 0.6 * aniso(m, pw * 3.1, 7.0, 313))
    dy = wander_mm * PX * (1.2 * aniso(m, 20.0, pf * 1.05, 312) + 0.6 * aniso(m, 7.0, pf * 3.1, 314))
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    mx, my = gx + dx, gy + dy
    h_r = cv2.remap(h, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    a_r = cv2.remap(alb, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    T_r = cv2.remap(T, mx, my, cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE)
    m_r = cv2.remap(mat, mx, my, cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE)
    use = lin0 & (m_r == 0)
    h = np.where(use, h_r, h); alb = np.where(use[..., None], a_r, alb); T = np.where(use[..., None], T_r, T)
    del h_r, a_r, T_r, m_r, mx, my, gx, gy, dx, dy
    lin = lin0
    wv = np.clip(T[..., 1], 0, 1)                    # 1 where a warp thread (vertical) is on top
    n_w = aniso(m, pw * 0.9, 14.0, 301)                  # per warp thread: slow thick / thin along its length
    n_f = aniso(m, 14.0, pf * 0.9, 302)
    s_w = np.clip(aniso(m, pw * 0.8, 9.0, 303, 2) - 0.30, 0, None) * 1.05    # slubs: longer, rarer, softer thick runs
    s_f = np.clip(aniso(m, 9.0, pf * 0.8, 304, 2) - 0.30, 0, None) * 1.05
    t_w = aniso(m, pw * 0.55, 30.0, 305)                 # whole-thread tone (a lighter / darker thread across the cloth)
    t_f = aniso(m, 30.0, pf * 0.55, 306)
    kw = 1 + strength * (0.9 * n_w + 0.9 * s_w)
    kf = 1 + strength * (0.9 * n_f + 0.9 * s_f)
    k = (wv * kw + (1 - wv) * kf)
    tone = 1 + strength * (0.09 * (wv * (0.8 * n_w + t_w) + (1 - wv) * (0.8 * n_f + t_f))) + 0.07 * strength * (wv * s_w + (1 - wv) * s_f)
    ck = aniso(m, 55.0, 55.0, 307, 2)
    crease = np.exp(-(aniso(m, 90.0, 140.0, 308) * 9.0) ** 2)      # a few soft creases across the cloth
    h2 = np.where(lin, np.where(h > 0, h * relief * np.clip(k, 0.3, 2.2), h * (0.8 + 0.2 * relief)), h) + np.where(lin, 0.07 * ck + 0.10 * crease, 0)
    a2 = np.where(lin[..., None], alb * np.clip(tone, 0.5, 1.6)[..., None] * (1 - 0.06 * crease[..., None]), alb)
    return h2.astype(m['h'].dtype), a2.astype(m['alb'].dtype), T.astype(m['T'].dtype)


def umber_ratio():
    """albedo multiplier (per channel) of a needle-hole interior / soil halo: a dark umber, never black."""
    return np.array([0.27, 0.19, 0.14], np.float32)


def _hh(i, s):
    x = (int(i) * 374761393 + int(s) * 668265263) & 0xFFFFFFFF
    x = ((x ^ (x >> 13)) * 1274126177) & 0xFFFFFFFF
    return (x ^ (x >> 16)) / 4294967296.0


def holes_from_record(R, ids, PX, x0w, y0w, H, W, seed, min_sp_mm=0.46, exclude=None):
    """needle holes at the real strand ends of the entries `ids` (record entries removed from the cloth): entry / exit
    pairs along the stitch rows, denser along contours (stem outlines), couching tie pairs, thinned to a minimum
    spacing.  Every random draw is a hash of (entry, end, seed), so overlapping patches agree.
    Returns (hole strength map (H,W) float32 0..1, list of centres in window px)."""
    off = R['off']; P = R['P']; kind = R['kind']; typ = R['typ']
    cand = []
    for k in ids:
        if typ[k] != 0: continue
        kd = kind[k]
        p = P[off[k]:off[k + 1]]
        if len(p) < 2: continue
        prob = 1.0
        if kd in (K_TIE, K_MTIE, K_CTIE): prob = 0.55
        elif kd == K_SPLIT: prob = 0.50
        elif kd in (K_STEM, K_CORD): prob = 0.85
        for ei, e in enumerate((0, -1)):
            hs = seed * 7 + ei
            if _hh(k, hs) > prob: continue
            q = p[e]
            d = p[min(2, len(p) - 1)] - p[0] if e == 0 else p[-1] - p[max(-3, -len(p))]
            ang = math.atan2(d[1], d[0]) if (d ** 2).sum() > 1e-6 else _hh(k, hs + 1) * math.pi
            jx = (_hh(k, hs + 2) - 0.5) * 0.12 * PX; jy = (_hh(k, hs + 3) - 0.5) * 0.12 * PX
            cand.append((q[0] - x0w + jx, q[1] - y0w + jy, ang, _hh(k, hs + 4), _hh(k, hs + 5), _hh(k, hs + 6)))
    cand = [c for c in cand if 1 <= c[0] < W - 1 and 1 <= c[1] < H - 1]
    cand.sort(key=lambda c: c[3])
    cell = min_sp_mm * PX
    grid = {}; keep = []
    for x, y, a, _, rs, ss in cand:
        if exclude is not None and exclude[int(y), int(x)]: continue
        gx, gy = int(x / cell), int(y / cell); ok = True
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = grid.get((gx + dx, gy + dy))
                if q is not None and (q[0] - x) ** 2 + (q[1] - y) ** 2 < cell * cell:
                    ok = False; break
            if not ok: break
        if ok:
            grid[(gx, gy)] = (x, y); keep.append((x, y, a, rs, ss))
    S = 4
    big = np.zeros((H, W), np.float32)
    for x, y, a, rs, ss in keep:
        # radius (px at L0): lognormal-ish via a smooth map of one uniform
        r = float(np.clip(0.19 * PX * math.exp(0.30 * (rs * 2 - 1) * 1.7), 0.12 * PX, 0.36 * PX))
        st = 0.55 + 0.45 * ss
        cv2.ellipse(big, (int(round(x * S)), int(round(y * S))), (max(1, int(round(r * 1.45 * S))), max(1, int(round(r * 0.78 * S)))),
                    math.degrees(a), 0, 360, st, -1, cv2.LINE_AA, shift=2)
    hole = cv2.GaussianBlur(big, (0, 0), 0.09 * PX)
    return np.clip(hole, 0, 1), keep


def apply_holes(lin, hole, PX, depth=0.15):
    """write holes into a linen window dict: shallow pit (so the AO does not crush it to black), dark umber interior,
    displaced-thread rim (one-sided: the needle pushed the weave aside), soil halo."""
    rim = np.clip(cv2.GaussianBlur(hole, (0, 0), 0.20 * PX) * 1.9 - hole, 0, 1)
    halo = cv2.GaussianBlur(hole, (0, 0), 0.55 * PX)
    halo = np.clip(halo * 2.2, 0, 1)
    lin['h'] = lin['h'] - depth * hole + 0.11 * rim
    um = umber_ratio()
    lin['alb'] = lin['alb'] * (1 - 0.85 * hole[..., None]) + lin['alb'] * um * 0.85 * hole[..., None]
    lin['alb'] = lin['alb'] * (1 - 0.10 * halo[..., None]) * (1 + 0.05 * rim[..., None])
    return lin


def ink_alpha(ud, PX, seed, strength=1.0):
    """underdrawing opacity from a line map: a broader soft pen line with pressure variation and breaks."""
    H, W = ud.shape
    rr = np.random.default_rng(seed)
    line = cv2.GaussianBlur(ud, (0, 0), 0.10 * PX)
    line = np.clip(line * 1.9, 0, 1)
    # pen pressure (long, slow) and pen lifts (short breaks)
    ox = 0.0
    n1 = vnoise(0, 0, H, W, PX, 9.0, seed, 2) * 1.6
    n2 = vnoise(0, 0, H, W, PX, 2.4, seed + 3, 2) * 1.6
    press = np.clip(0.80 + 0.45 * n1, 0.35, 1.2)
    lift = 1 - 0.55 * sstep(0.35, 0.8, n2)
    return np.clip(line * press * lift * strength, 0, 1)


def bleed_holes(sil, PX, seed, band_mm=6.5, tau=2.4, p0=0.5, cell_mm=0.8):
    """a ragged border: needle holes that thin out OUTSIDE the unpicked area (where the bake's polygon clipped the
    stitch rows there is no hole row, so the pitted area would stop on a ruler-straight line).  sil: 0/1 mask of the
    unpicked area; returns a hole strength map drawn like the record holes."""
    H, W = sil.shape
    dist = cv2.distanceTransform((sil == 0).astype(np.uint8), cv2.DIST_L2, 5) / PX
    cell = cell_mm * PX
    big = np.zeros((H, W), np.float32)
    S = 4
    gy, gx = np.mgrid[0:int(H / cell), 0:int(W / cell)]
    for iy, ix in zip(gy.ravel(), gx.ravel()):
        k = iy * 100003 + ix
        x = (ix + 0.15 + 0.7 * _hh(k, seed)) * cell; y = (iy + 0.15 + 0.7 * _hh(k, seed + 1)) * cell
        if not (1 <= x < W - 1 and 1 <= y < H - 1): continue
        d = dist[int(y), int(x)]
        if d <= 0.0 or d > band_mm: continue
        if _hh(k, seed + 2) > p0 * math.exp(-d / tau): continue
        r = float(np.clip(0.19 * PX * math.exp(0.30 * (_hh(k, seed + 3) * 2 - 1) * 1.7), 0.12 * PX, 0.36 * PX))
        a = _hh(k, seed + 4) * math.pi
        cv2.ellipse(big, (int(round(x * S)), int(round(y * S))), (max(1, int(round(r * 1.45 * S))), max(1, int(round(r * 0.78 * S)))),
                    math.degrees(a), 0, 360, 0.55 + 0.45 * _hh(k, seed + 5), -1, cv2.LINE_AA, shift=2)
    return np.clip(cv2.GaussianBlur(big, (0, 0), 0.09 * PX), 0, 1)
