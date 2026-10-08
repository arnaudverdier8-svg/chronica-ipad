"""Noise and small helpers.  vnoise() is translation-invariant (hash lattice in absolute mm), so any window of an
infinite sheet can be generated independently and tiles/pads are seamless."""
import math
import numpy as np, cv2
from numba import njit, prange


def hash1(i, seed):
    i = np.asarray(i, np.int64)
    v = (i * 374761393 + seed * 668265263) & 0xFFFFFFFF
    v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((v ^ (v >> 16)) & 0xFFFF).astype(np.float32) / 65535.0


def sstep(e0, e1, x):
    t = np.clip((np.asarray(x, np.float32) - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


@njit(cache=True, inline='always')
def _hh(i, j, s):
    v = (i * 374761393 + j * 668265263 + s * 1442695041) & 0xFFFFFFFF
    v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
    return (((v ^ (v >> 16)) & 0xFFFF) / 65535.0) * 2.0 - 1.0


@njit(parallel=True, cache=True)
def _vnoise_grid(x0, y0, dx, dy, H, W, scale, seed, octaves):
    out = np.zeros((H, W), np.float32)
    for yy in prange(H):
        for xx in range(W):
            amp = 1.0; sc = scale; tot = 0.0; acc = 0.0
            for o in range(octaves):
                x = (x0 + xx * dx) / sc; y = (y0 + yy * dy) / sc
                xi = math.floor(x); yi = math.floor(y); fx = x - xi; fy = y - yi
                fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
                ix = int(xi); iy = int(yi); s = seed + o * 7919
                a = _hh(ix, iy, s); b = _hh(ix + 1, iy, s); c = _hh(ix, iy + 1, s); d = _hh(ix + 1, iy + 1, s)
                acc += amp * ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy)
                tot += amp; amp *= 0.5; sc *= 0.5
            out[yy, xx] = acc / tot
    return out


def vnoise(x0_mm, y0_mm, H, W, PX, scale_mm, seed, octaves=1):
    """value noise in [-1,1] (std ~0.33) on the pixel grid of a window whose top-left pixel centre is at (x0_mm, y0_mm)."""
    return _vnoise_grid(float(x0_mm), float(y0_mm), 1.0 / PX, 1.0 / PX, int(H), int(W), float(scale_mm), int(seed), int(octaves))


def smooth_noise(shape, scale_px, seed, octaves=1):
    """legacy grid noise (NOT translation invariant): only for one-off local textures."""
    r = np.random.default_rng(seed)
    out = np.zeros(shape, np.float32)
    amp, sc, tot = 1.0, scale_px, 0
    for o in range(octaves):
        gh, gw = int(shape[0] / sc) + 3, int(shape[1] / sc) + 3
        g = r.standard_normal((gh, gw)).astype(np.float32)
        out += amp * cv2.resize(g, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC) * 0.7
        tot += amp; amp *= 0.5; sc /= 2
    return out / tot


def smooth_noise1(n, scale, r):
    g = r.standard_normal(int(n / scale) + 3)
    return np.interp(np.arange(n) / scale, np.arange(len(g)), g).astype(np.float32)


def bbox(mask, pad=0, shape=None):
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        return None
    H, W = shape or mask.shape
    return (max(int(xs.min()) - pad, 0), max(int(ys.min()) - pad, 0), min(int(xs.max()) + pad + 1, W), min(int(ys.max()) + pad + 1, H))


def save_rgb(path, u8):
    cv2.imwrite(path, cv2.cvtColor(u8, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 94] if path.endswith('.jpg') else [])


def load_rgb(path):
    im = cv2.imread(path, cv2.IMREAD_COLOR)
    return cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
