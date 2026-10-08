"""v2: thread-scale detail synthesis that the 1.5 px/mm working maps cannot carry (the 5 px/mm mips are area-resampled, the weave and the
individual stitches are gone).  Everything here is band-limited so that it SURVIVES the 2:1 down to 0.75 px/mm (>= ~2.7 mm periods across,
longer along): stitch-row streaks following the thread tangent T (line-integral convolution), colour quantisation into discrete wool
lots, linen slubs and weft barre, per-lot dye jitter.  All deterministic (seeded)."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from s18common import *
import math
from numba import njit, prange
from chron.util import _vnoise_grid


def vn_aniso(H, W, PX, sx_mm, sy_mm, seed, octs=1, x0=0.0, y0=0.0):
    """value noise in [-1, 1] with correlation length sx_mm along x and sy_mm along y."""
    return _vnoise_grid(float(x0 / sx_mm), float(y0 / sy_mm), 1.0 / (PX * sx_mm), 1.0 / (PX * sy_mm), int(H), int(W), 1.0, int(seed), int(octs))


@njit(parallel=True, cache=True)
def _lic(noise, T, mask, half, out):
    H, W = noise.shape
    for y in prange(H):
        for x in range(W):
            if mask[y, x] == 0:
                continue
            tx = T[y, x, 0]; ty = T[y, x, 1]
            n = math.sqrt(tx * tx + ty * ty) + 1e-6
            tx /= n; ty /= n
            acc = 0.0; wsum = 0.0
            for dirn in range(2):
                sgn = 1.0 if dirn == 0 else -1.0
                px = float(x); py = float(y)
                cx = tx * sgn; cy = ty * sgn
                for k in range(half + 1):
                    if dirn == 1 and k == 0:
                        continue
                    xi = int(px + 0.5); yi = int(py + 0.5)
                    if xi < 0 or yi < 0 or xi >= W or yi >= H:
                        break
                    w = 0.5 + 0.5 * math.cos(math.pi * k / (half + 1))
                    acc += w * noise[yi, xi]; wsum += w
                    # follow the field (re-sample the tangent, keep the orientation continuous)
                    ux = T[yi, xi, 0]; uy = T[yi, xi, 1]
                    if ux * cx + uy * cy < 0:
                        ux = -ux; uy = -uy
                    nn = math.sqrt(ux * ux + uy * uy) + 1e-6
                    cx = ux / nn; cy = uy / nn
                    px += cx; py += cy
            out[y, x] = acc / (wsum + 1e-6)
    return out


def lic_streaks(T, mask, PX, seed, across_mm=1.6, along_mm=9.0):
    """zero-mean (std ~1) streak texture: stitch rows ~across_mm wide following the thread tangent over ~along_mm."""
    H, W = mask.shape
    r = np.random.default_rng(seed)
    nz = r.standard_normal((H, W)).astype(np.float32)
    sig = max(0.4, across_mm * PX * 0.38)
    nz = cv2.GaussianBlur(nz, (0, 0), sig)
    nz /= (nz.std() + 1e-6)
    out = np.zeros((H, W), np.float32)
    half = max(2, int(round(along_mm * PX * 0.5)))
    _lic(nz, np.ascontiguousarray(T, np.float32), np.ascontiguousarray(mask.astype(np.uint8)), half, out)
    m = mask > 0
    if m.any():
        out[m] /= (out[m].std() + 1e-6)
    return out


def slubs(H, W, PX, seed, per_100cm2=7.0):
    """linen slubs: thick-thread segments (warp: along v, weft: along u), random 4-26 mm long; returns (lum, relief) maps."""
    r = np.random.default_rng(seed)
    lum = np.zeros((H, W), np.float32); rel = np.zeros((H, W), np.float32)
    area_cm2 = H * W / PX / PX / 100.0
    n = int(area_cm2 / 100.0 * per_100cm2 * 100)
    for _ in range(n):
        x, y = r.uniform(0, W), r.uniform(0, H)
        L = float(np.clip(r.lognormal(math.log(9.0), 0.6), 3.0, 30.0)) * PX
        horiz = r.random() < 0.62
        dx, dy = (L, 0.0) if horiz else (0.0, L * 0.8)
        v = float(r.uniform(0.4, 1.0)) * (1 if r.random() < 0.72 else -0.7)
        wd = max(1, int(round(r.uniform(0.9, 1.7) * PX)))
        cv2.line(lum, (int(x), int(y)), (int(x + dx), int(y + dy)), v, wd, cv2.LINE_AA)
    lum = cv2.GaussianBlur(lum, (0, 0), 0.6 * PX)
    return lum


def quantise_lots(L, mask, noise, step=0.040, dither=0.55):
    """discrete wool colour lots: snap OKLab L to steps of `step`, the threshold wandering with the stitch-row noise (|noise| ~1) so that
    lot boundaries run along the stitches (long-and-short blending) instead of smooth continuous-tone gradients."""
    q = np.round(L / step + dither * 0.5 * np.clip(noise, -2.0, 2.0)) * step
    return np.where(mask > 0, q, L)
