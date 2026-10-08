"""Render keyframe f91 (S02 'realm') from the baked kit sheet k1_realm with the library's R25-F renderer.

Camera: the S01->S02 pull-back at f91 is an exponential zoom-out about a fixed screen point Z (upper left, near the
thread's tie-down) easing out toward F0 at f114.  At f91: 5.0 px/mm, frame top-left at sheet (40, 5) mm,
d(ln s)/df = -ZOOM_RATE.  Motion blur = 180-deg shutter: the linear frame is averaged over sub-frame zooms about Z
(content shrinking toward Z), so the centre stays sharp and only the frame edges carry a trace of blur.

Light: 3000 K window key from the upper left (az 128, el 22), key:fill 3:1, 25 % rim at az 30 el 8 (hero frame),
window pool (kmap) centred on the realm; Act I grade.  The cloth's shared low-frequency fold field is added to the
height before relighting (frieze-mm function, same for every sheet).

    python3 render_f91.py [--noblur] [--out keyframe_f91_2560x1440.png] [--tag v1]
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
from chron.color import lin2srgb                             # noqa

MAPS = os.path.join(bkit.AAA, 'cache', 'maps')
SHOT = json.load(open(os.path.join(HERE, 'shot_f91.json')))


def fold_field(m, amp=None):
    """shared low-frequency cloth fold / crease field (bible 4.7: 0.3-1 mm over 5-20 mm), added to h in place.
    Deterministic in frieze mm (sheet mm + frieze origin)."""
    F = SHOT['folds']
    amp = F['amp_mm'] if amp is None else amp
    PX = m['PX']; ox, oy = m['origin_mm']
    fx, fy = F.get('frieze_origin_mm', (0.0, 0.0))
    H, W = m['h'].shape
    xs = (ox + fx + (np.arange(W, dtype=np.float32) + 0.5) / PX)[None, :]
    ys = (oy + fy + (np.arange(H, dtype=np.float32) + 0.5) / PX)[:, None]
    f = np.zeros((H, W), np.float32)
    for cr in F['creases']:            # long soft creases: (x0, y0, angle_deg, width_mm, depth_mm)
        a = math.radians(cr['angle'])
        d = (xs - cr['x']) * (-math.sin(a)) + (ys - cr['y']) * math.cos(a)
        along = (xs - cr['x']) * math.cos(a) + (ys - cr['y']) * math.sin(a)
        fade = np.exp(-(along / cr['len']) ** 2)
        f += cr['depth'] * np.exp(-(d / cr['w']) ** 2) * fade
    f += amp * vnoise(ox + fx, oy + fy, H, W, PX, F['scale_mm'], F['seed'], 2)
    m['h'] = (m['h'] + f).astype(np.float32)
    LM = SHOT.get('linen_mottle')
    if LM:   # uneven, slightly blotchy linen tone (storage discolouration), linen only
        g = 1 + LM['amp'] * vnoise(ox + fx, oy + fy, H, W, PX, LM['scale_mm'], LM['seed'], 3) \
            + LM.get('amp2', 0) * vnoise(ox + fx, oy + fy, H, W, PX, LM.get('scale2_mm', 9.0), LM['seed'] + 1, 2)
        lin_m = (m['mat'] == 0)[..., None]
        warm = np.array([1.0, 0.985, 0.955], np.float32)
        m['alb'] = np.where(lin_m, m['alb'] * g[..., None] * np.where(g[..., None] < 1, warm, 1.0), m['alb']).astype(np.float32)
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


def rig():
    L = dict(SHOT['light'])
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
    """screen-space room pool (the window footprint) for an image of `shape` at s px/mm whose top-left is (x0, y0) mm."""
    P = SHOT.get('pool_all')
    if not P:
        return None
    from chron.shade import spot
    return spot(shape, s, P['cx_mm'], P['cy_mm'], P['r_mm'], P['floor'], P.get('aspect', 1.0), (x0_mm, y0_mm))


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
        # output px p_out = Zs + k * (p_ref - Zs);  p_ref (frame-at-tau=0 coords) = big px - pad
        M = np.array([[k, 0, Zs[0] - k * Zs[0] - k * pad[0]], [0, k, Zs[1] - k * Zs[1] - k * pad[1]]], np.float32)
        acc += cv2.warpAffine(lin_big, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    return acc / n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--noblur', action='store_true')
    ap.add_argument('--tag', default='')
    ap.add_argument('--sheet', default='k1_realm')
    ap.add_argument('--half', action='store_true', help='1280x720 quick look')
    a = ap.parse_args()
    t0 = time.time()
    ms = MapSet(os.path.join(MAPS, a.sheet))
    C = SHOT['camera']
    s = C['px_per_mm'] * (0.5 if a.half else 1.0)
    out_wh = (1280, 720) if a.half else (2560, 1440)
    pad = (0, 0) if a.noblur else (int(0.035 * out_wh[0]), int(0.035 * out_wh[1]))
    big_wh = (out_wh[0] + 2 * pad[0], out_wh[1] + 2 * pad[1])
    view = dict(x0_mm=C['x0_mm'] - pad[0] / s, y0_mm=C['y0_mm'] - pad[1] / s, px_per_mm=s)
    tm = {}
    fr = render_frame(ms, view, big_wh, timing=tm)
    lin = fr['lin']
    check_void(lin, fr['alpha'], name='f91')
    pa = pool_all(lin.shape[:2], s, view['x0_mm'], view['y0_mm'])
    if pa is not None:
        lin = lin * pa[..., None]
    if not a.noblur:
        Zs = (C['zoom_fixed_px'][0] * out_wh[0] / 2560, C['zoom_fixed_px'][1] * out_wh[1] / 1440)
        rate = float(os.environ.get('F91_ZOOM_RATE', C['zoom_rate_per_frame']))
        lin = zoom_blur(lin, big_wh, out_wh, s, Zs, rate, shutter=C['shutter_frames'], n=C.get('blur_samples', 11),
                        pad=pad)
    G = SHOT['grade']
    img16 = grade.grade(lin, exposure=G['exposure'], act=G['act'], seed=91, out_u16=True, grain=G.get('grain', 0.012))
    tag = ('_' + a.tag) if a.tag else ''
    name = f'keyframe_f91_{out_wh[0]}x{out_wh[1]}{tag}.png'
    cv2.imwrite(os.path.join(HERE, name), cv2.cvtColor(img16, cv2.COLOR_RGB2BGR))
    np.save(os.path.join(HERE, 'work', f'lin_f91{tag}.npy'), lin.astype(np.float16)) if os.path.isdir(os.path.join(HERE, 'work')) else None
    print(json.dumps(dict(out=name, level=fr['level'], s=s, timing={k: round(v, 1) if isinstance(v, float) else v for k, v in tm.items()},
                          total_s=round(time.time() - t0, 1))))


if __name__ == '__main__':
    main()
