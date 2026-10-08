"""Analytic linen tabby ground, translation invariant (any window of an infinite sheet, seamless across tiles and pads).
Threads are addressable by index: warp i = floor(x / pitch_warp), weft j = floor(y / pitch_weft) (for fray).
(<- R25 linen.py; grid noise replaced by hash value noise in absolute mm)."""
import math
import numpy as np, cv2
from .util import hash1, _vnoise_grid
from .color import hex_lin
from .config import LINEN

_N1D = {}


def _n1d(seed):
    if seed not in _N1D:
        rng = np.random.default_rng(seed + 4)
        _N1D[seed] = (np.convolve(rng.standard_normal(400000), np.hanning(41), 'same') / 4.5).astype(np.float32)
    return _N1D[seed]


def _vn(x0, y0, H, W, PX, sx, sy, seed, oct_=1):
    return _vnoise_grid(float(x0 / sx), float(y0 / sy), 1.0 / (PX * sx), 1.0 / (PX * sy), int(H), int(W), 1.0, int(seed), int(oct_))


def make_linen(Hpx, Wpx, PX, x0_mm=0.0, y0_mm=0.0, seed=0, warp_cm=18.5, weft_cm=19.0, td=0.46, base_hex='#D4BE98',
               strip_px=3_000_000):
    """maps dict (h mm, alb linear, T, mat, cov, PX) for the window whose top-left pixel is at (x0_mm, y0_mm).
    Large windows are generated in row strips (seamless: the generator is translation invariant) to bound RAM."""
    if Hpx * Wpx <= strip_px:
        return _make_linen(Hpx, Wpx, PX, x0_mm, y0_mm, seed, warp_cm, weft_cm, td, base_hex)
    out = dict(h=np.zeros((Hpx, Wpx), np.float32), alb=np.zeros((Hpx, Wpx, 3), np.float32), T=np.zeros((Hpx, Wpx, 2), np.float32),
               mat=np.zeros((Hpx, Wpx), np.uint8), cov=np.zeros((Hpx, Wpx), np.float32), PX=float(PX), origin_mm=(float(x0_mm), float(y0_mm)))
    hs = max(1, strip_px // Wpx)
    for r0 in range(0, Hpx, hs):
        r1 = min(Hpx, r0 + hs)
        b = _make_linen(r1 - r0, Wpx, PX, x0_mm, y0_mm + r0 / PX, seed, warp_cm, weft_cm, td, base_hex)
        for k in ('h', 'alb', 'T'):
            out[k][r0:r1] = b[k]
    return out


def _make_linen(Hpx, Wpx, PX, x0_mm, y0_mm, seed, warp_cm, weft_cm, td, base_hex):
    sh = (Hpx, Wpx)
    xs = (x0_mm + np.arange(Wpx, dtype=np.float64) / PX).astype(np.float32)
    ys = (y0_mm + np.arange(Hpx, dtype=np.float64) / PX).astype(np.float32)
    X, Y = np.meshgrid(xs, ys)
    pw, pf = 10 / warp_cm, 10 / weft_cm
    Xw = X + 0.10 * 1.4 * _vn(x0_mm, y0_mm, Hpx, Wpx, PX, 6, 6, seed + 1) + 0.05 * 1.4 * _vn(x0_mm, y0_mm, Hpx, Wpx, PX, 1.5, 1.5, seed + 11)
    Yw = Y + 0.10 * 1.4 * _vn(x0_mm, y0_mm, Hpx, Wpx, PX, 6, 6, seed + 2) + 0.05 * 1.4 * _vn(x0_mm, y0_mm, Hpx, Wpx, PX, 1.5, 1.5, seed + 12)
    del X, Y
    xi, yi = Xw / pw, Yw / pf
    i, j = np.floor(xi), np.floor(yi)
    tx, ty = xi - i - 0.5, yi - j - 0.5
    n1d = _n1d(seed)

    def slub(idx, along, s):
        pos = (np.abs(along * 4 + hash1(idx, s) * 300000)).astype(np.int64) % 399000
        return np.clip(n1d[pos] - 1.45, 0, None)
    slub_w = 1 + 0.16 * (hash1(i, seed + 3) - 0.5) + 0.7 * slub(i, Yw, seed + 4)
    slub_f = 1 + 0.16 * (hash1(j, seed + 5) - 0.5) + 0.7 * slub(j, Xw, seed + 6)
    rw, rf = 0.5 * td * slub_w, 0.5 * td * slub_f
    hw = 0.8 * rw * np.sqrt(np.clip(1 - (tx * pw / rw) ** 2, 0, 1)) + 0.07 * np.sin(math.pi * (yi + i))
    hf = 0.8 * rf * np.sqrt(np.clip(1 - (ty * pf / rf) ** 2, 0, 1)) - 0.07 * np.sin(math.pi * (xi + j))
    inw, inf = np.abs(tx * pw) < rw, np.abs(ty * pf) < rf
    hw = np.where(inw, hw, -0.2); hf = np.where(inf, hf, -0.2)
    warp_top = hw >= hf
    h = np.maximum(np.maximum(hw, hf), -0.14)
    del hw, hf
    # fibre streaks along each thread (micro relief)
    stw = 1.5 * _vn(x0_mm, y0_mm, Hpx, Wpx, PX, 0.07, 0.9, seed + 7, 2)
    stf = 1.5 * _vn(x0_mm, y0_mm, Hpx, Wpx, PX, 0.9, 0.07, seed + 17, 2)
    st = np.where(warp_top, stw, stf); del stw, stf
    h = h + st * 0.012
    gap = (~inw) & (~inf)
    T = np.zeros((Hpx, Wpx, 2), np.float32)
    T[..., 0] = np.where(warp_top, 0, 1); T[..., 1] = np.where(warp_top, 1, 0)
    base = hex_lin(base_hex)
    per_thread = np.where(warp_top, hash1(i, seed + 7), hash1(j, seed + 8)) - 0.5
    f = (1 + 0.07 * per_thread + 0.025 * st)
    f *= (1 + 0.045 * 1.6 * _vn(x0_mm, y0_mm, Hpx, Wpx, PX, 12, 12, seed + 9, 2))
    sl = np.where(warp_top, slub_w, slub_f) - 1
    f *= (1 + 0.10 * np.clip(sl, 0, 1))
    f = np.where(gap, f * 0.55, f)
    alb = (f[..., None] * base).astype(np.float32)
    return dict(h=h.astype(np.float32), alb=alb, T=T, mat=np.zeros(sh, np.uint8), cov=np.zeros(sh, np.float32), PX=float(PX),
                origin_mm=(float(x0_mm), float(y0_mm)))


def thread_index(x_mm, y_mm, warp_cm=18.5, weft_cm=19.0):
    """(warp i, weft j) addressing of the tabby at a point (ignores the +/-0.1 mm wander)."""
    return np.floor(np.asarray(x_mm) / (10 / warp_cm)).astype(np.int64), np.floor(np.asarray(y_mm) / (10 / weft_cm)).astype(np.int64)
