"""Render keyframe f91 (S02 'realm') from the baked kit sheet k1_realm with the library's R25-F renderer (v2).

Camera: S01->S02 pull-back, an exponential zoom-out about the FRAME CENTRE (shot_f91.json camera.zoom_fixed_px), so the
centre stays sharp and only the frame edges carry a trace of motion blur (180-deg shutter, rate 0.012/frame).  f91 =
5.0 px/mm, frame top-left at sheet (x0, y0) mm.

Light (v2): 3000 K window key from the upper left (az 128, el 22), key:fill 4.6 (storyboard Act I says 3:1; the library's
fill_i = key_i / ratio * 0.35, v1 used 3.6), 22 % rim at az 30 / el 8; the window footprint is a screen-space pool
(`pool_all`: peak on the capital, ~0.4 at the corners) plus a faint directional window gradient (brighter upper left).
Look patches applied here (the library is read-only; they are monkey-patches in this script, reported in README):
  * softer / smaller ambient-occlusion halo around raised wool (v1 AO darkened the linen 40 % up to 1.5 mm from every motif,
    which read as a sticker shadow)                                         -> `ao_v2`, patched into frontal.prepare
  * linen-weave LOD ramp moved to P0 1.8 px (v1 1.2): the near-Nyquist weave lattice is faded earlier
  * low-frequency cloth: stronger creases + sag folds in the height (fold_field), dust in the creases, storage mottle
  * split-tone in linear light before the Act I grade (cool brown-violet shadows, warm highlights)
    python3 render_f91.py [--noblur] [--tag x] [--sheet k1_realm] [--x0 168 --y0 5] [--half]
"""
import os, sys, json, time, math, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'kit'))
import bkit                                                  # noqa
import numpy as np, cv2                                      # noqa
from chron.maps import MapSet                                # noqa
from chron import frontal, shade, grade                      # noqa
from chron.qa.void import check_void                         # noqa
from chron.util import vnoise                                # noqa
from chron.color import lin2srgb, LUMA                       # noqa

MAPS = os.path.join(bkit.AAA, 'cache', 'maps')
SHOT = json.load(open(os.path.join(HERE, os.environ.get('F91_SHOT', 'shot_f91.json'))))
LOOK = SHOT.get('look', {})


# ------------------------------------------------------------------------------------------------ library look patches
def ao_v2(h, PX, k1=None, k2=None, floor=None):
    L = LOOK.get('ao', {})
    k1 = L.get('k1', 0.95) if k1 is None else k1
    k2 = L.get('k2', 0.22) if k2 is None else k2
    floor = L.get('floor', 0.5) if floor is None else floor
    a1 = cv2.GaussianBlur(h, (0, 0), 0.8 * PX) - h
    a2 = cv2.GaussianBlur(h, (0, 0), 3.0 * PX) - h
    return np.clip(1 - k1 * np.clip(a1, 0, None) - k2 * np.clip(a2, 0, None), floor, 1).astype(np.float32)


_prepare_orig = frontal.prepare


def prepare_v2(m, screen_px_per_mm, lod=True):
    _prepare_orig(m, screen_px_per_mm, lod)
    if LOOK.get('ao') is not None:
        m['ao'] = ao_v2(m['h'].astype(np.float32), m['PX'])
    return m


frontal.prepare = prepare_v2
if LOOK.get('lod_p0') is not None:
    shade.LOD_P0 = float(LOOK['lod_p0'])
if LOOK.get('lod_ramp') is not None:
    shade.LOD_RAMP = float(LOOK['lod_ramp'])


# ------------------------------------------------------------------------------------------------ cloth: folds, dust, mottle
def _xy_mm(m):
    PX = m['PX']; ox, oy = m['origin_mm']
    fx, fy = SHOT['folds'].get('frieze_origin_mm', (0.0, 0.0))
    H, W = m['h'].shape
    xs = (ox + fx + (np.arange(W, dtype=np.float32) + 0.5) / PX)[None, :]
    ys = (oy + fy + (np.arange(H, dtype=np.float32) + 0.5) / PX)[:, None]
    return xs, ys, ox + fx, oy + fy, H, W, PX


def fold_field(m, amp=None):
    """shared low-frequency cloth fold / crease field (bible 4.7: 0.3-1 mm over 5-20 mm), added to h in place, plus
    dust gathered in the creases and a blotchy linen storage tone.  Deterministic in frieze mm (sheet mm + origin)."""
    F = SHOT['folds']
    amp = F['amp_mm'] if amp is None else amp
    xs, ys, ox, oy, H, W, PX = _xy_mm(m)
    f = np.zeros((H, W), np.float32)
    dust = np.zeros((H, W), np.float32)
    for cr in F['creases']:            # long soft creases: (x, y, angle_deg, width_mm, depth_mm, len_mm)
        a = math.radians(cr['angle'])
        d = (xs - cr['x']) * (-math.sin(a)) + (ys - cr['y']) * math.cos(a)
        along = (xs - cr['x']) * math.cos(a) + (ys - cr['y']) * math.sin(a)
        fade = np.exp(-(along / cr['len']) ** 2)
        prof = cr['depth'] * np.exp(-(d / cr['w']) ** 2) * fade
        f += prof
        if cr['depth'] < 0:           # valley folds gather dust
            dust += np.clip(-prof / max(abs(cr['depth']), 1e-3), 0, 1) * min(1.0, abs(cr['depth']) / 0.5)
    f += amp * vnoise(ox, oy, H, W, PX, F['scale_mm'], F['seed'], 2)
    m['h'] = (m['h'] + f).astype(np.float32)
    lin_m = (m['mat'] == 0)[..., None]
    LM = SHOT.get('linen_mottle')
    g = np.ones((H, W), np.float32)
    if LM:   # uneven, slightly blotchy linen tone (storage discolouration), linen only
        g = 1 + LM['amp'] * vnoise(ox, oy, H, W, PX, LM['scale_mm'], LM['seed'], 3) \
            + LM.get('amp2', 0) * vnoise(ox, oy, H, W, PX, LM.get('scale2_mm', 9.0), LM['seed'] + 1, 2)
    dk = 1 - F.get('dust', 0.10) * np.clip(dust, 0, 1)
    FX = SHOT.get('age', {}).get('fox_extra') if isinstance(SHOT.get('age'), dict) else None
    if FX and 'age_fox' in m:      # extra foxing (bible 4.7: brown 0.5-3 mm spots, clustered at the hem): browns linen and, less, wool
        fx = np.clip(m['age_fox'].astype(np.float32), 0, 1) * (FX['base'] + FX['hem'] * np.exp(-np.clip(ys, 0, None) / FX.get('hem_mm', 40.0)))
        brown = np.array([1.0, 0.72, 0.42], np.float32)
        wl = np.where(m['mat'] == 0, 1.0, 0.35).astype(np.float32)
        m['alb'] = (m['alb'] * (1 - (fx * wl)[..., None] * (1 - brown))).astype(np.float32)
    warm = np.array([1.0, 0.985, 0.955], np.float32)
    gg = (g * dk)[..., None]
    m['alb'] = np.where(lin_m, m['alb'] * gg * np.where(gg < 1, warm, 1.0), m['alb']).astype(np.float32)
    return m


def age_map(m):
    """ageing amount per pixel (0 fresh .. 1 aged): base + stronger at the top hem (S01: nail holes, foxing) and
    toward the sides of the frieze section."""
    A = SHOT['age']
    if not isinstance(A, dict):
        return A
    PX = m['PX']; ox, oy = m['origin_mm']
    H, W = m['h'].shape
    xs = (ox + (np.arange(W, dtype=np.float32) + 0.5) / PX)[None, :]
    ys = (oy + (np.arange(H, dtype=np.float32) + 0.5) / PX)[:, None]
    a = A['base'] + A['hem_boost'] * np.exp(-np.clip(ys, 0, None) / A['hem_mm']) \
        + A['side_boost'] * np.clip(((xs - A['xc_mm']) / A['half_w_mm']) ** 2, 0, 1)
    a = np.clip(a, 0, 1).astype(np.float32)
    if 'mat' in m and A.get('metal_keep') is not None:      # gilt thread / crown do not fade like dyes (they tarnish; tie-downs are silk)
        a = a * np.where(m['mat'] == 3, float(A['metal_keep']), 1.0).astype(np.float32)
    return a


def rig(L=None):
    L = dict(L or SHOT['light'])
    for k in ('key_i', 'fill_ratio', 'el', 'az'):
        if os.environ.get('F91_' + k.upper()):
            L[k] = float(os.environ['F91_' + k.upper()])
    return shade.rig(az=L['az'], el=L['el'], K=L['K'], key_i=L['key_i'], fill_ratio=L['fill_ratio'], tint=L['tint'],
                     rim_az=L['rim_az'], rim_el=L['rim_el'], rim_i=L['rim_i'], k_env=L.get('k_env', 0.35))


def render_frame(ms, view, out_wh, fib_seed=91, with_folds=True, timing=None, light=None):
    light = light or rig()
    K = SHOT['kmap']
    return frontal.render(ms, view, light, out_wh=out_wh, kmap=dict(cx_mm=K['cx_mm'], cy_mm=K['cy_mm'], r_mm=K['r_mm'], floor=K['floor'],
                          aspect=K.get('aspect', 1.0)), fib_seed=fib_seed, edit=(fold_field if with_folds else None),
                          age=age_map, timing=timing)


def pool_all(shape, s, x0_mm, y0_mm):
    """screen-space room pool (the window footprint) for an image of `shape` at s px/mm whose top-left is (x0, y0) mm:
    elliptical pool with a floor, times a faint directional window gradient (brighter toward the upper left)."""
    P = SHOT.get('pool_all')
    if not P:
        return None
    from chron.shade import spot
    pa = spot(shape, s, P['cx_mm'], P['cy_mm'], P['r_mm'], P['floor'], P.get('aspect', 1.0), (x0_mm, y0_mm))
    for ac in P.get('accents', []):      # secondary local lifts of the window light (e.g. along the gold chronicle thread)
        yy, xx = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float32)
        d = np.hypot((xx / s + x0_mm - ac['cx_mm']) / ac.get('aspect', 1.0), yy / s + y0_mm - ac['cy_mm']) / ac['r_mm']
        pa = pa * (1 + ac['gain'] * np.exp(-d * d)).astype(np.float32)
    gd = P.get('gradient', 0.0)
    if gd:
        H, W = shape
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        u = (xx / W - 0.5) * 2; v = (yy / H - 0.5) * 2
        pa = pa * (1 - gd * 0.5 * (u + 0.6 * v)).astype(np.float32)
    return pa


def split_tone(lin, cfg):
    """cool brown-violet shadows, warm highlights, in linear light (before the act grade)."""
    if not cfg:
        return lin
    L = (lin * LUMA).sum(-1, keepdims=True)
    sh = np.clip(1 - L / cfg.get('sh_knee', 0.30), 0, 1) ** 1.5 * cfg.get('sh_amt', 0.30)
    hi = np.clip((L - cfg.get('hi_lo', 0.45)) / 0.7, 0, 1) * cfg.get('hi_amt', 0.07)
    cool = np.array(cfg.get('cool', [0.78, 0.80, 1.0]), np.float32)
    warm = np.array(cfg.get('warm', [1.0, 0.95, 0.82]), np.float32)
    out = lin * (1 - sh) + lin * cool * sh
    out = out * (1 - hi) + out * warm * hi * 1.0 + out * hi * 0.0
    return out.astype(np.float32)


def zoom_blur(lin_big, big_wh, out_wh, s, Zs, rate, shutter=0.5, n=9, pad=(0, 0)):
    """average of the frame zoomed about screen point Zs over sub-frame offsets tau in [-shutter/2, shutter/2]
    (scale factor exp(-rate * tau)); lin_big is rendered with `pad` extra px on each side at the same px/mm."""
    W, H = out_wh
    acc = np.zeros((H, W, 3), np.float32)
    taus = (np.arange(n) + 0.5) / n * shutter - shutter / 2
    for t in taus:
        k = math.exp(-rate * t)
        if abs(t) < 1e-9:
            k = 1.0
        M = np.array([[k, 0, Zs[0] - k * Zs[0] - k * pad[0]], [0, k, Zs[1] - k * Zs[1] - k * pad[1]]], np.float32)
        acc += cv2.warpAffine(lin_big, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    return acc / n


def finish_frame(lin, view, s, out_wh, big_wh, pad, noblur, seed=91):
    pa = pool_all(lin.shape[:2], s, view['x0_mm'], view['y0_mm'])
    if pa is not None:
        lin = lin * pa[..., None]
    lin = split_tone(lin, SHOT.get('split_tone'))
    C = SHOT['camera']
    if not noblur:
        Zs = (C['zoom_fixed_px'][0] * out_wh[0] / 2560, C['zoom_fixed_px'][1] * out_wh[1] / 1440)
        rate = float(os.environ.get('F91_ZOOM_RATE', C['zoom_rate_per_frame']))
        lin = zoom_blur(lin, big_wh, out_wh, s, Zs, rate, shutter=C['shutter_frames'], n=C.get('blur_samples', 11), pad=pad)
    G = SHOT['grade']
    img16 = grade.grade(lin, exposure=G['exposure'], act=G['act'], seed=seed, out_u16=True, grain=G.get('grain', 0.012))
    img8 = grade.grade(lin, exposure=G['exposure'], act=G['act'], seed=seed, out_u16=False, grain=G.get('grain', 0.012))   # dithered by the grade's grain
    return img16, img8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--noblur', action='store_true')
    ap.add_argument('--tag', default='')
    ap.add_argument('--sheet', default='k1_realm')
    ap.add_argument('--x0', type=float, default=None)
    ap.add_argument('--y0', type=float, default=None)
    ap.add_argument('--half', action='store_true', help='1280x720 quick look')
    a = ap.parse_args()
    t0 = time.time()
    ms = MapSet(os.path.join(MAPS, a.sheet))
    C = SHOT['camera']
    s = C['px_per_mm'] * (0.5 if a.half else 1.0)
    out_wh = (1280, 720) if a.half else (2560, 1440)
    pad = (0, 0) if a.noblur else (int(0.035 * out_wh[0]), int(0.035 * out_wh[1]))
    big_wh = (out_wh[0] + 2 * pad[0], out_wh[1] + 2 * pad[1])
    x0 = C['x0_mm'] if a.x0 is None else a.x0
    y0 = C['y0_mm'] if a.y0 is None else a.y0
    view = dict(x0_mm=x0 - pad[0] / s, y0_mm=y0 - pad[1] / s, px_per_mm=s)
    tm = {}
    fr = render_frame(ms, view, big_wh, timing=tm)
    check_void(fr['lin'], fr['alpha'], name='f91')
    img16, img8 = finish_frame(fr['lin'], view, s, out_wh, big_wh, pad, a.noblur)
    tag = ('_' + a.tag) if a.tag else ''
    name = f'keyframe_f91_{out_wh[0]}x{out_wh[1]}{tag}.png'
    out = os.path.join(HERE, 'look2' if a.tag else '', name)
    cv2.imwrite(out, cv2.cvtColor(img16, cv2.COLOR_RGB2BGR))
    cv2.imwrite(out.replace('.png', '_8bit.png'), cv2.cvtColor(img8, cv2.COLOR_RGB2BGR))
    print(json.dumps(dict(out=out, level=fr['level'], map_px=fr['map_px'], s=s, timing={k: round(v, 1) if isinstance(v, float) else v for k, v in tm.items()},
                          total_s=round(time.time() - t0, 1))))


if __name__ == '__main__':
    main()
