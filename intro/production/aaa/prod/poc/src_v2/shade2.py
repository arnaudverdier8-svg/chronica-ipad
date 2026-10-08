"""Two-candle relight of the board maps (R25 BRDF unchanged: emb.shade.brdf), per-pixel pool maps, per-light shadows.
out = sum_i brdf(key_i * gain_i, km_i, vis_i)  +  brdf(fill_col * fill_i, kF, up-light, vis=1) * ao
The same pool maps (lightmodel) drive Eevee, so R25 and Eevee share one light rig."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
sys.path.insert(0, RND)
import numpy as np, cv2
from numba import njit, prange
from emb.shade import brdf, normals, ambient_occlusion, shadow_march, light_vec
import lightmodel as lm

KEYC = lm.key_colour()
UP = np.array([0.0, 0.0, 1.0], np.float32)
SHADOW_LIFT = 0.22


def relight2(m, kL, kR, kF, gL=1.0, gR=1.0, N=None, ao=None, soft=0.14, spec_scale=1.0, maxd_mm=6.0, with_vis=True):
    """m: maps window (h, alb, T, mat, PX); kL, kR, kF: pool maps in the window; returns linear radiance (and visL, visR)"""
    h = m['h']; PXm = m['PX']
    if N is None: N = m.get('N') if m.get('N') is not None else normals(h, PXm, blur=0.5)
    if ao is None: ao = m.get('ao') if m.get('ao') is not None else ambient_occlusion(h, PXm)
    out = np.zeros(m['alb'].shape, np.float32)
    vis_all = []
    zero = np.zeros(3, np.float32)
    camx = camy = 0.0; camz = -1.0
    for name, g, km in (('L', gL, kL), ('R', gR, kR)):
        if g <= 1e-4:
            vis_all.append(np.ones(h.shape, np.float32)); continue
        c = lm.CANDLE[name]
        L = light_vec(c['az'], c['el'])
        l2 = L[:2] / (np.linalg.norm(L[:2]) + 1e-6)
        tan_el = L[2] / (np.linalg.norm(L[:2]) + 1e-6)
        maxd = min(maxd_mm * PXm, 2.2 / max(tan_el, 0.05) * PXm)
        vis = shadow_march(h, float(l2[0]), float(l2[1]), float(tan_el), float(PXm), float(maxd), 1.25, float(soft))
        vis = cv2.GaussianBlur(vis, (0, 0), 0.12 * PXm).astype(np.float32)
        vis = (SHADOW_LIFT + (1 - SHADOW_LIFT) * vis).astype(np.float32)      # bounce from the pools: shadows never go to black
        kc = (KEYC * c['key_i'] * g).astype(np.float32)
        o = np.empty_like(out)
        brdf(m['alb'], N, m['T'], m['mat'], ao, vis, km.astype(np.float32), L, kc, zero, light_vec(35.0, 11.0), zero, camx, camy, camz, h, float(PXm), o, float(spec_scale))
        out += o
        vis_all.append(vis)
    # fill: bounce from the pools (navy), near-vertical, unshadowed, AO-modulated
    kcF = (np.array(lm.FILL_COL, np.float32) * lm.FILL_I * lm.CANDLE['L']['key_i'] * 0.0 + np.array(lm.FILL_COL, np.float32) * lm.FILL_I).astype(np.float32)
    o = np.empty_like(out)
    one = np.ones(h.shape, np.float32)
    brdf(m['alb'], N, m['T'], m['mat'], ao, one, kF.astype(np.float32), UP, kcF, zero, light_vec(35.0, 11.0), zero, camx, camy, camz, h, float(PXm), o, 0.0)
    out += o * ao[..., None]
    return out, vis_all


@njit(parallel=True, cache=True)
def _light_fibres2(P, A, visL, visR, kLr, kRr, kFr, LL, LR, cL, cR, cF, V, out):
    n, K, _ = P.shape
    for i in prange(n):
        for k in range(K):
            k0 = k if k < K - 1 else K - 2
            tx = P[i, k0 + 1, 0] - P[i, k0, 0]; ty = P[i, k0 + 1, 1] - P[i, k0, 1]; tz = P[i, k0 + 1, 2] - P[i, k0, 2]
            tl = math.sqrt(tx * tx + ty * ty + tz * tz) + 1e-9
            tx /= tl; ty /= tl; tz /= tl
            kf = min(1.0, k / 4.0) * 0.8
            for c in range(3):
                out[i, k, c] = A[i, c] * cF[c] * kFr[i]
            for li in range(2):
                if li == 0:
                    Lx, Ly, Lz = LL[0], LL[1], LL[2]; vv = visL[i] + (1 - visL[i]) * kf; km = kLr[i]
                    cc0, cc1, cc2 = cL[0], cL[1], cL[2]
                else:
                    Lx, Ly, Lz = LR[0], LR[1], LR[2]; vv = visR[i] + (1 - visR[i]) * kf; km = kRr[i]
                    cc0, cc1, cc2 = cR[0], cR[1], cR[2]
                tdl = tx * Lx + ty * Ly + tz * Lz
                sinl = math.sqrt(max(0.0, 1 - tdl * tdl))
                hx = Lx + V[0]; hy = Ly + V[1]; hz = Lz + V[2]
                hl = math.sqrt(hx * hx + hy * hy + hz * hz)
                tdh = (tx * hx + ty * hy + tz * hz) / hl
                sth = math.sqrt(max(0.0, 1 - tdh * tdh))
                w = vv * km * (0.65 * sinl + 0.15)
                s = vv * km * 0.10 * sth ** 12
                out[i, k, 0] += A[i, 0] * cc0 * w + cc0 * s
                out[i, k, 1] += A[i, 1] * cc1 * w + cc1 * s
                out[i, k, 2] += A[i, 2] * cc2 * w + cc2 * s
    return out


def render_fibres2(img, fib, visL, visR, kL, kR, kF, gL, gR, project, V=(0.0, 0.0, 1.0), width=0.9):
    """fibres lit by the two candles + fill; km sampled at each fibre root (map px coords of img)"""
    from emb.fibres import _splat
    if fib is None or len(fib['P']) == 0: return img
    P = fib['P']; rx, ry = fib['root'][:, 0], fib['root'][:, 1]
    cL = (KEYC * lm.CANDLE['L']['key_i'] * gL).astype(np.float32); cR = (KEYC * lm.CANDLE['R']['key_i'] * gR).astype(np.float32)
    cF = (np.array(lm.FILL_COL, np.float32) * lm.FILL_I).astype(np.float32)
    LL = light_vec(lm.CANDLE['L']['az'], lm.CANDLE['L']['el']); LR = light_vec(lm.CANDLE['R']['az'], lm.CANDLE['R']['el'])
    C = np.zeros(P.shape, np.float32)
    _light_fibres2(P, fib['A'], visL[ry, rx].astype(np.float32), visR[ry, rx].astype(np.float32), kL[ry, rx].astype(np.float32),
                   kR[ry, rx].astype(np.float32), kF[ry, rx].astype(np.float32), LL, LR, cL, cR, cF, np.asarray(V, np.float32), C)
    Q, Zc = project(P)
    depth = np.full(img.shape[:2], 1e9, np.float32)
    _splat(img, depth, Q.astype(np.float32), Zc.astype(np.float32), C, fib['alpha'], float(width))
    return img
