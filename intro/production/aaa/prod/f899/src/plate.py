"""R25-F ground plate for the oblique shot: render the sheet RECTIFIED (frontal relight at s px/mm, with the real camera position
for the view-dependent terms), one pass per light (hearth / cool daylight arc / fill), then warp with the camera homography.
Lights add linearly, so each pass can be multiplied by its own slip shadow ratio (Eevee shadow catcher) before summing."""
import os, sys, math, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bkit                                                           # noqa
import numpy as np, cv2                                               # noqa
from chron import frontal, shade                                      # noqa
from chron.maps import MapSet                                         # noqa
from chron.util import vnoise                                         # noqa
from chron.ageing import apply_age                                    # noqa
from chron.color import hex_lin, light_colour                         # noqa
import camera as CAM                                                  # noqa


def fold_field(m, F):
    """shared low-frequency cloth fold / crease field (frieze mm), added to h in place; linen mottle (same as the f91 look)."""
    amp = F['amp_mm']
    PX = m['PX']; ox, oy = m['origin_mm']
    fx, fy = F.get('frieze_origin_mm', (0.0, 0.0))
    H, W = m['h'].shape
    xs = (ox + fx + (np.arange(W, dtype=np.float32) + 0.5) / PX)[None, :]
    ys = (oy + fy + (np.arange(H, dtype=np.float32) + 0.5) / PX)[:, None]
    f = np.zeros((H, W), np.float32)
    for cr in F['creases']:
        a = math.radians(cr['angle'])
        d = (xs - cr['x']) * (-math.sin(a)) + (ys - cr['y']) * math.cos(a)
        along = (xs - cr['x']) * math.cos(a) + (ys - cr['y']) * math.sin(a)
        f += cr['depth'] * np.exp(-(d / cr['w']) ** 2) * np.exp(-(along / cr['len']) ** 2)
    f += amp * vnoise(ox + fx, oy + fy, H, W, PX, F['scale_mm'], F['seed'], 2)
    m['h'] = (m['h'] + f).astype(np.float32)
    LM = F.get('linen_mottle')
    if LM:
        g = 1 + LM['amp'] * vnoise(ox + fx, oy + fy, H, W, PX, LM['scale_mm'], LM['seed'], 3) \
            + LM.get('amp2', 0) * vnoise(ox + fx, oy + fy, H, W, PX, LM.get('scale2_mm', 9.0), LM['seed'] + 1, 2)
        lin_m = (m['mat'] == 0)[..., None]
        warm = np.array([1.0, 0.985, 0.955], np.float32)
        m['alb'] = np.where(lin_m, m['alb'] * g[..., None] * np.where(g[..., None] < 1, warm, 1.0), m['alb']).astype(np.float32)
    return m


def _warp(a, dx, dy, border=cv2.BORDER_REFLECT):
    H, W = a.shape[:2]
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    return cv2.remap(a, gx + dx, gy + dy, cv2.INTER_LINEAR, borderMode=border)


def _blur_big(a, sigma_px, down=8):
    """large-sigma gaussian via downsampling (a: (H, W) or (H, W, 3))."""
    h, w = a.shape[:2]
    sm = cv2.resize(a, (max(w // down, 2), max(h // down, 2)), interpolation=cv2.INTER_AREA)
    sm = cv2.GaussianBlur(sm, (0, 0), sigma_px / down)
    return cv2.resize(sm, (w, h), interpolation=cv2.INTER_LINEAR)


def extra_age(m, spec, arc=None):
    """art-directed ageing of the LINEN and wool in the plate (the century has just begun):
      * foxing: the bake's age_fox discs, domain-warped into irregular blots with a darker core and a yellow-brown halo, in a range of sizes,
        clustered along the tidelines and the hem (never a uniform disc);
      * tideline: warped, wicked into the weave (soft, uneven edge), pale tea-brown;
      * bleach front (arc): dyes fade toward grey-white (madder toward pink-grey, woad toward grey-white), linen toward ivory, to the LEFT of the arc's edge;
      * protected (footprint) linen: matched to the surrounding aged linen (slightly fresher), never a cool slab;
      * needle-hole pigment bleed is baked (ghost_v2)."""
    from chron.color import hex_lin, lin2oklab, oklab2lin
    PX = m['PX']; ox, oy = m['origin_mm']
    H, W = m['h'].shape
    xs = (ox + (np.arange(W, dtype=np.float32) + 0.5) / PX); ys = (oy + (np.arange(H, dtype=np.float32) + 0.5) / PX)
    lin_m = (m['mat'] == 0).astype(np.float32)
    ghost = np.clip(m['ghost'], 0, 1).astype(np.float32) if 'ghost' in m else np.zeros((H, W), np.float32)
    prot = 1.0 - 0.85 * ghost
    seed0 = spec.get('seed', 11)
    fox0 = np.clip(m.get('age_fox', 0.0) * spec.get('fox_gain', 1.0), 0, 1) if 'age_fox' in m else np.zeros((H, W), np.float32)
    tide0 = np.clip(m.get('age_tide', 0.0) * spec.get('tide_gain', 1.0), 0, 1) if 'age_tide' in m else np.zeros((H, W), np.float32)
    fox0 = np.asarray(fox0, np.float32); tide0 = np.asarray(tide0, np.float32)
    # ---------- foxing
    if fox0.max() > 0:
        dxn = vnoise(ox, oy, H, W, PX, 3.4, seed0, 2) * 1.2 * PX; dyn = vnoise(ox + 57.0, oy + 31.0, H, W, PX, 3.4, seed0 + 1, 2) * 1.2 * PX
        fw = _warp(fox0, dxn.astype(np.float32), dyn.astype(np.float32))
        fw = np.clip(fw + 0.25 * vnoise(ox, oy, H, W, PX, 1.1, seed0 + 2, 1) * (fw > 0.05), 0, 1)
        core = np.clip(fw ** 1.6 * 1.25, 0, 1)
        halo = np.clip(cv2.GaussianBlur(fw, (0, 0), 1.0 * PX) * 1.6, 0, 1) * 0.55
        tide_near = _blur_big(tide0, 5.0 * PX)
        hem = np.exp(-np.clip(ys, 0, None) / 28.0)[:, None]
        cl = np.clip(0.35 + 2.4 * tide_near + 0.9 * hem, 0, 1.6)
        fk = spec.get('fox_k', 0.6)
        a_core = (core * cl * fk * 1.15 * lin_m * prot)[..., None]
        a_halo = (np.maximum(halo - core * 0.5, 0) * cl * fk * lin_m * prot)[..., None]
        cc = hex_lin('#6B4325'); cc = cc / cc.max() * 0.52
        hc = hex_lin('#A9793C'); hc = hc / hc.max() * 0.74
        alb = m['alb']
        alb = alb * (1 - a_halo) + alb * hc * a_halo
        alb = alb * (1 - a_core) + alb * cc * a_core
        m['alb'] = alb.astype(np.float32)
    # ---------- tideline (wicked, uneven)
    if tide0.max() > 0:
        dxn = vnoise(ox + 11.0, oy + 5.0, H, W, PX, 7.0, seed0 + 3, 2) * 2.0 * PX; dyn = vnoise(ox + 71.0, oy + 9.0, H, W, PX, 7.0, seed0 + 4, 2) * 2.0 * PX
        tw = _warp(tide0, dxn.astype(np.float32), dyn.astype(np.float32))
        tw = cv2.GaussianBlur(tw, (0, 0), 0.5 * PX)
        tw = np.clip(tw * (0.75 + 0.5 * (0.5 + vnoise(ox, oy, H, W, PX, 2.2, seed0 + 5, 2))), 0, 1)
        tc = hex_lin('#9A7A52'); tc = tc / tc.max() * 0.80
        b = (tw * spec.get('tide_k', 0.5) * lin_m * prot)[..., None]
        m['alb'] = (m['alb'] * (1 - b) + m['alb'] * tc * b).astype(np.float32)
    # ---------- bleach front
    if arc is not None and spec.get('bleach', 0) > 0:
        import arc as ARC
        XX, YY = np.meshgrid(xs, ys)
        _, bw = ARC.weights(XX, YY, arc)
        bw = (bw * spec['bleach']).astype(np.float32)
        alb = m['alb']
        lab = lin2oklab(alb.reshape(-1, 3)).reshape(H, W, 3)
        wool = ((m['mat'] == 1) | (m['mat'] == 2) | (m['mat'] == 4) | (m['mat'] == 5)).astype(np.float32)
        lin_k = lin_m
        kw = bw * wool; kl = bw * lin_k
        L0 = lab[..., 0].copy()
        lab[..., 0] = L0 + 0.34 * kw * (0.93 - L0) + 0.07 * kl * (0.95 - L0)
        lab[..., 1] *= (1 - 0.66 * kw - 0.45 * kl)
        lab[..., 2] *= (1 - 0.66 * kw - 0.40 * kl)
        m['alb'] = np.maximum(oklab2lin(lab.reshape(-1, 3)).reshape(H, W, 3), 0).astype(np.float32)
    # ---------- protected linen: matched to the surrounding (aged) linen, a touch fresher
    if ghost.max() > 0 and spec.get('ghost_match', 1.0) > 0:
        inl = lin_m * (1 - ghost); gl = lin_m * ghost
        alb = m['alb']
        so = _blur_big(alb * inl[..., None], 28.0 * PX) / (_blur_big(inl, 28.0 * PX)[..., None] + 1e-4)
        si = _blur_big(alb * gl[..., None], 28.0 * PX) / (_blur_big(gl, 28.0 * PX)[..., None] + 1e-4)
        ratio = np.clip(so / np.maximum(si, 1e-3), 0.6, 1.3)
        gk = (ghost * lin_m)[..., None] * spec.get('ghost_match', 1.0)
        fresh = np.array([1.045, 1.04, 1.03], np.float32)
        m['alb'] = (alb * (1 - gk) + alb * ratio * fresh * gk).astype(np.float32)
    return m


def tarnish_metal(m, amount, col_hex='#7A5A2A', front=None):
    """couched gold -> tarnished (#E9BE6A -> #7A5A2A) by `amount` (0..1) on metal pixels; front = dict(x0, x1, hi, lo, rag): the tarnish advances left to
    right (amount hi at x <= x0 down to lo at x >= x1, with a ragged hand-off)."""
    if amount <= 0 and front is None:
        return m
    metal = (m['mat'] == 3)
    if not metal.any():
        return m
    tc = hex_lin(col_hex)
    g = hex_lin('#E9BE6A')
    ratio = tc / g
    H, W = m['h'].shape
    if front is not None:
        PX = m['PX']; ox, oy = m['origin_mm']
        xs = (ox + (np.arange(W, dtype=np.float32) + 0.5) / PX)[None, :]
        n = 0.5 + 0.5 * np.sin(xs / 9.0 + 1.3) * np.sin(xs / 23.0 + 0.4)
        t = np.clip((xs - front['x0'] + front.get('rag', 0.0) * (n - 0.5)) / (front['x1'] - front['x0']), 0, 1)
        t = t * t * (3 - 2 * t)
        amt = front['hi'] + (front['lo'] - front['hi']) * t
        amt = np.broadcast_to(amt, (H, W))
    else:
        amt = amount
    k = (amt * metal.astype(np.float32))[..., None]
    m['alb'] = (m['alb'] * (1 - k) + m['alb'] * ratio * k).astype(np.float32)
    return m


def age_amount_fn(spec):
    """age amount map (0 fresh .. 1 aged) in sheet mm: base + left bleach front + hem boost."""
    def fn(m):
        PX = m['PX']; ox, oy = m['origin_mm']
        H, W = m['h'].shape
        xs = (ox + (np.arange(W, dtype=np.float32) + 0.5) / PX)[None, :]
        ys = (oy + (np.arange(H, dtype=np.float32) + 0.5) / PX)[:, None]
        a = spec['base'] + spec['left_boost'] * np.exp(-np.clip(xs, 0, None) / spec['left_mm']) + spec['hem_boost'] * np.exp(-np.clip(ys, 0, None) / spec['hem_mm'])
        return np.clip(a, 0, 1).astype(np.float32)
    return fn


def render_pass(ms, cam, rect, s, light, kmap, folds, age_fn, tarnish, fib=None, fib_seed=7, level=None, timing=None, cam_pos=None):
    """rectified relight of the window rect=(x0, y0, w, h) mm at s px/mm -> linear plate (h*s, w*s, 3)."""
    x0, y0, w, h = rect
    view = dict(x0_mm=x0, y0_mm=y0, px_per_mm=s)
    out_wh = (int(round(w * s)), int(round(h * s)))

    def edit(m):
        if folds is not None:
            fold_field(m, folds)
        if tarnish > 0:
            tarnish_metal(m, tarnish)
    fr = frontal.render(ms, view, light, out_wh=out_wh, level=level, fib=fib, fib_seed=fib_seed, kmap=kmap, edit=edit, age=age_fn,
                        cam=cam_pos, timing=timing)
    return fr


def warp_plate(lin, cam, x0, y0, s, out_wh=(CAM.W, CAM.H), interp=cv2.INTER_LANCZOS4):
    """homography warp of a rectified plate to the screen.  Lanczos keeps the stitch detail, but its negative lobes ring (a pale rim hugging every dark
    cord); v3 clamps the result to the local min / max of the bilinear warp (3 x 3), which keeps the sharpness and removes the rim."""
    Hm = CAM.plate_homography(cam, x0, y0, s)
    src = lin.astype(np.float32)
    img = cv2.warpPerspective(src, Hm, out_wh, flags=interp, borderMode=cv2.BORDER_REPLICATE)
    if interp == cv2.INTER_LANCZOS4:
        bl = cv2.warpPerspective(src, Hm, out_wh, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        k = np.ones((3, 3), np.uint8)
        img = np.minimum(np.maximum(img, cv2.erode(bl, k)), cv2.dilate(bl, k))
    return np.maximum(img, 0)
