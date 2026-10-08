"""R25 relight of the board maps in texture space (+ halo + texture-space fibres) -> linear radiance texture, and the
top-down camera warp to the 2560x1440 frame. One light rig shared with Eevee (lights.json written by write_lights())."""
import sys, os, json, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
sys.path.insert(0, RND)
import numpy as np, cv2
from emb.shade import relight, normals, ambient_occlusion, light_vec
from emb.fibres import halo, make_fibres, render_fibres
from emb.core import grade as r25_grade, srgb2lin, lin2srgb, hex2srgb

# ---- Act V light rig (palette acts V: key 3200 K elev 20, fill 1:4), raking from upper left
LIGHT = dict(az=200.0, el=24.0, key=(1.0, 0.9, 0.78), key_i=2.6, fill=(0.74, 0.83, 1.0), fill_i=0.44,
             rim_az=35.0, rim_el=11.0, rim_i=0.2, soft=0.14)
POOL = dict(cx=-0.6, cz=0.15, r_mm=430.0, floor=0.5, aspect=1.45)     # key pool (world units centre)


def kmap_for(shape, x0=0, y0=0):
    Hh, Ww = shape
    yy, xx = np.mgrid[0:Hh, 0:Ww].astype(np.float32)
    cxp, czp = (POOL['cx'] - BX0) * PPU - x0, (POOL['cz'] - BZ0) * PPU - y0
    d = np.hypot((xx - cxp) / PX / POOL['aspect'], (yy - czp) / PX) / POOL['r_mm']
    return (POOL['floor'] + (1 - POOL['floor']) * np.exp(-d * d)).astype(np.float32)


def kmap_full(scale=1.0):
    return kmap_for((int(H * scale) + 1, int(W * scale) + 1)) if scale == 1.0 else None


def topdown_view():
    """map-px rect seen by the zero-tilt camera (pitch 90, distance DIST, vfov 30) centred on TARGET"""
    hu = 2 * DIST * math.tan(math.radians(FOV_V / 2))          # visible ground height in game units
    s = 1440 / (hu * PPU)                                        # screen px per map px
    cx, cy = (TARGET[0] - BX0) * PPU, (TARGET[2] - BZ0) * PPU
    w, h = 2560 / s, 1440 / s
    return (cx - w / 2, cy - h / 2, w, h), s


def shade_window(m, reg, light=LIGHT, fib_seed=6, fib_density=0.9, with_fibres=True, N=None, ao=None):
    """reg = (x0,y0,x1,y1) map px. returns linear radiance (h, w, 3) of that window (map resolution)."""
    x0, y0, x1, y1 = reg
    sl = (slice(y0, y1), slice(x0, x1))
    mw = {k: (np.ascontiguousarray(v[sl]) if isinstance(v, np.ndarray) and v.ndim >= 2 else v) for k, v in m.items()}
    mw['PX'] = PX
    if N is None:
        mw['N'] = normals(mw['h'], PX, blur=0.5)
        mw['ao'] = ambient_occlusion(mw['h'], PX)
    else:
        mw['N'] = N[sl]; mw['ao'] = ao[sl]
    km = kmap_for(mw['h'].shape, x0, y0)
    lt = {k: v for k, v in light.items() if k != 'soft'}
    col, vis = relight(mw, kmap=km, cam=None, soft=light.get('soft', 0.12), **lt)
    col = halo(col, mw, 0.3, 0.33)
    if with_fibres:
        fib = make_fibres(mw, density=fib_density, seed=fib_seed, len_mm=(0.4, 2.0), max_fibres=900000)
        if fib is not None:
            fib['A'] = fib['A'] * np.random.default_rng(fib_seed).uniform(0.95, 1.05, (len(fib['A']), 1)).astype(np.float32)
            # calibration (pipeline 4.4): fibres over dark fills fade
            Lr = (mw['alb'][fib['root'][:, 1], fib['root'][:, 0]] @ np.array([0.2126, 0.7152, 0.0722], np.float32))
            fib['alpha'] = fib['alpha'] * np.clip((Lr - 0.03) / 0.12, 0, 1).astype(np.float32) * 0.85
            L = light_vec(light['az'], light['el'])
            key = np.array(light['key'], np.float32) * light['key_i'] * float(np.median(km))
            fill = np.array(light['fill'], np.float32) * light['fill_i']
            def project(P):
                Q = np.empty(P.shape[:2] + (2,), np.float32)
                Q[..., 0] = P[..., 0] * PX; Q[..., 1] = P[..., 1] * PX
                return Q, -P[..., 2]
            render_fibres(col, fib, L, key, fill, vis, project, width=0.9)
    return col.astype(np.float32)


def to_screen(rad, reg, view, s, out_wh=(2560, 1440), prefilter=True):
    """warp a radiance window (map res, origin reg[0:2]) to the screen with the zero-tilt camera."""
    vx, vy, vw, vh = view
    Wo, Ho = out_wh
    sc = Wo / vw
    M = np.array([[sc, 0, -(vx - reg[0]) * sc], [0, sc, -(vy - reg[1]) * sc]], np.float32)
    src = cv2.GaussianBlur(rad, (0, 0), 0.42 / sc * 0.8) if (prefilter and sc < 1) else rad
    return cv2.warpAffine(src, M, (Wo, Ho), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


# ---- grade (pipeline 5.4: ACES fit at exposure, act V grade from palette.json, clamps, grain)
ACT_V = dict(sat=1.0, lift='#05070C', gamma=1.0, gain='#FFF2DC')


def grade(lin_img, exposure=0.63, grain=0.011, seed=0):
    x = lin_img * exposure
    x = np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)
    lum = (x @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    sh = np.clip(1 - lum / 0.18, 0, 1) * 0.12
    tint = srgb2lin(hex2srgb('#1A1620')); tint = tint / tint.mean()
    x = x * (1 - sh) + x * tint * sh
    gain = srgb2lin(hex2srgb(ACT_V['gain'])); lift = srgb2lin(hex2srgb(ACT_V['lift']))
    x = lift + x * (gain - lift)
    black = srgb2lin(hex2srgb('#07070A')); white = srgb2lin(hex2srgb('#F3E8D0'))
    x = black + x * (white - black)
    s_ = lin2srgb(np.clip(x, 0, 1))
    if grain > 0:
        g = np.random.default_rng(seed).standard_normal(s_.shape[:2]).astype(np.float32)
        g = cv2.GaussianBlur(g, (0, 0), 0.7)
        s_ = s_ + grain * g[..., None]
    return np.clip(s_ * 255 + 0.5, 0, 255).astype(np.uint8)


def write_lights(path):
    L = light_vec(LIGHT['az'], LIGHT['el'])
    R = light_vec(LIGHT['rim_az'], LIGHT['rim_el'])
    json.dump(dict(LIGHT, L_board=[float(v) for v in L], rim_board=[float(v) for v in R], pool=POOL,
                   note='board coords: x right, y down (game +z), z up. Blender = (x, -y, z)'), open(path, 'w'), indent=1)
