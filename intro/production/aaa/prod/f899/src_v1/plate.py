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


def extra_age(m, spec):
    """stronger, art-directed foxing + tideline on the LINEN (the bake's age_fox / age_tide layers scaled): the century has just begun to
    brown the cloth; protected (ghost) linen under the lifted figures stays fresh."""
    from chron.color import hex_lin
    lin_m = (m['mat'] == 0).astype(np.float32)
    prot = 1.0 - 0.85 * np.clip(m.get('ghost', 0.0), 0, 1) if 'ghost' in m else 1.0
    fox = np.clip(m.get('age_fox', 0.0) * spec.get('fox_gain', 1.0), 0, 1) * lin_m * prot
    tide = np.clip(m.get('age_tide', 0.0) * spec.get('tide_gain', 1.0), 0, 1) * lin_m * prot
    fc = hex_lin('#8A5A34'); fc = fc / fc.max() * 0.60
    tc = hex_lin('#7C5A38'); tc = tc / tc.max() * 0.72
    a = (fox * spec.get('fox_k', 0.55))[..., None]
    b = (tide * spec.get('tide_k', 0.5))[..., None]
    alb = m['alb']
    alb = alb * (1 - a) + alb * fc * a
    alb = alb * (1 - b) + alb * tc * b
    m['alb'] = alb.astype(np.float32)
    return m


def tarnish_metal(m, amount, col_hex='#7A5A2A'):
    """couched gold -> tarnished (#E9BE6A -> #7A5A2A) by `amount` (0..1) on metal pixels."""
    if amount <= 0:
        return m
    metal = (m['mat'] == 3)
    if not metal.any():
        return m
    tc = hex_lin(col_hex)
    g = hex_lin('#E9BE6A')
    ratio = tc / g
    k = (amount * metal.astype(np.float32))[..., None]
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
    Hm = CAM.plate_homography(cam, x0, y0, s)
    img = cv2.warpPerspective(lin.astype(np.float32), Hm, out_wh, flags=interp,
                              borderMode=cv2.BORDER_REPLICATE)
    return np.maximum(img, 0)
