"""R25 relight of the board maps in texture space (two candle pools + navy fill + halo + fibres) -> linear radiance, the top-down
camera warp to the 2560x1440 frame, and the ONE grade shared with Eevee frames (act V)."""
import sys, os, json, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
sys.path.insert(0, RND)
import numpy as np, cv2
from emb.shade import normals, ambient_occlusion, light_vec
from emb.fibres import halo, make_fibres
from emb.core import srgb2lin, lin2srgb, hex2srgb, lin2oklab, oklab2lin
import lightmodel as lm
import shade2

EXPOSURE = float(os.environ.get('CHRON_EXPO', '0.29'))
ACT_V = dict(sat=1.0, lift='#05070C', gamma=1.0, gain='#FFF2DC')
CLASS_GRADE = os.path.join(POC, 'data', 'class_grade.json')


def topdown_view():
    """map-px rect seen by the zero-tilt camera (pitch 90, distance DIST, vfov 30) centred on TARGET"""
    hu = 2 * DIST * math.tan(math.radians(FOV_V / 2))
    s = 1440 / (hu * PPU)
    cx, cy = (TARGET[0] - BX0) * PPU, (TARGET[2] - BZ0) * PPU
    w, h = 2560 / s, 1440 / s
    return (cx - w / 2, cy - h / 2, w, h), s


def shade_window(m, reg, gL=1.0, gR=1.0, f_for_pools=None, fib=None, N=None, ao=None, with_halo=True):
    """reg = (x0,y0,x1,y1) map px; m = full-board maps (or already windowed with reg=None). Returns linear radiance of the window (map res)."""
    x0, y0, x1, y1 = reg
    sl = (slice(y0, y1), slice(x0, x1))
    mw = {k: (np.ascontiguousarray(v[sl]) if isinstance(v, np.ndarray) and v.ndim >= 2 else v) for k, v in m.items()}
    mw['PX'] = PX
    mw['N'] = normals(mw['h'], PX, blur=0.5) if N is None else N[sl]
    mw['ao'] = ambient_occlusion(mw['h'], PX) if ao is None else ao[sl]
    kL, kR, kF = lm.kmaps(mw['h'].shape, x0, y0, 1, f_for_pools)
    kF = lm.fill_map(kL, kR, gL, gR)
    col, vis = shade2.relight2(mw, kL, kR, kF, gL, gR, N=mw['N'], ao=mw['ao'])
    if with_halo:
        col = halo(col, mw, 0.3, 0.33)
    if fib is not None:
        def project(P):
            Q = np.empty(P.shape[:2] + (2,), np.float32); Q[..., 0] = P[..., 0] * PX; Q[..., 1] = P[..., 1] * PX
            return Q, -P[..., 2]
        shade2.render_fibres2(col, fib, vis[0], vis[1], kL, kR, kF, gL, gR, project)
    return col


def to_screen(rad, reg, view, s, out_wh=(2560, 1440), prefilter=True):
    vx, vy, vw, vh = view
    Wo, Ho = out_wh
    sc = Wo / vw
    M = np.array([[sc, 0, -(vx - reg[0]) * sc], [0, sc, -(vy - reg[1]) * sc]], np.float32)
    src = cv2.GaussianBlur(rad, (0, 0), 0.42 / sc * 0.8) if (prefilter and sc < 1) else rad
    return cv2.warpAffine(src, M, (Wo, Ho), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def grade(lin_img, exposure=None, grain=0.011, seed=0, neutral=False):
    """pipeline 5.4: ACES fit at exposure, act V grade from palette.json (lift/gain), clamps, cool shadow tint, grain.
    neutral=True skips the act V lift/gain/shadow tint (used by the palette check against the menu)"""
    x = lin_img * (EXPOSURE if exposure is None else exposure)
    x = np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)
    if not neutral:
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
