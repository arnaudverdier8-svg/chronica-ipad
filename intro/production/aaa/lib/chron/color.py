"""sRGB/linear/OKLab, palette access, Kelvin display tints, chroma caps, dye-lot ShadeSet.  (<- R25 core.py + stitch.ShadeSet)"""
import math
import numpy as np, cv2
from .config import palette

LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


def srgb2lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


def lin2srgb(c):
    c = np.clip(np.asarray(c, np.float32), 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1 / 2.4) - 0.055).astype(np.float32)


def hex2srgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255


def hex_lin(h):
    return srgb2lin(hex2srgb(h))


def pal(name):
    """linear RGB of a cinematic palette role, e.g. pal('crimson')."""
    return hex_lin(palette()['cinematic'][name]['hex'])


def kelvin(K):
    """display colour of a light temperature (palette.json light_kelvin_display), linear RGB normalised to max 1."""
    tab = {int(k[:-1]): v for k, v in palette()['light_kelvin_display'].items()}
    ks = sorted(tab)
    K = float(np.clip(K, ks[0], ks[-1]))
    i = max(0, min(len(ks) - 2, int(np.searchsorted(ks, K)) - 1))
    a, b = ks[i], ks[i + 1]
    t = (K - a) / (b - a)
    c = hex_lin(tab[a]) * (1 - t) + hex_lin(tab[b]) * t
    return (c / c.max()).astype(np.float32)


def light_colour(K, tint=0.35):
    """key colour used by the relight: white mixed with the Kelvin display colour at `tint` (bible: 20-50 % tints)."""
    c = (1 - tint) * np.ones(3, np.float32) + tint * kelvin(K)
    return (c / c.max()).astype(np.float32)


def lum(lin):
    return (np.asarray(lin, np.float32) * LUMA).sum(-1)


# ---------------- OKLab ----------------
_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                [0.2119034982, 0.6806995451, 0.1073969566],
                [0.0883024619, 0.2817188376, 0.6299787005]], np.float32)
_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                [1.9779984951, -2.4285922050, 0.4505937099],
                [0.0259040371, 0.7827717662, -0.8086757660]], np.float32)
_M2i = np.array([[1.0, 0.3963377774, 0.2158037573],
                 [1.0, -0.1055613458, -0.0638541728],
                 [1.0, -0.0894841775, -1.2914855480]], np.float32)
_M1i = np.array([[4.0767416621, -3.3077115913, 0.2309699292],
                 [-1.2684380046, 2.6097574011, -0.3413193965],
                 [-0.0041960863, -0.7034186147, 1.7076147010]], np.float32)


def lin2oklab(rgb):
    lms = np.asarray(rgb, np.float32) @ _M1.T
    return np.cbrt(np.maximum(lms, 0)) @ _M2.T


def oklab2lin(lab):
    lms = np.asarray(lab, np.float32) @ _M2i.T
    return np.clip((lms ** 3) @ _M1i.T, 0, None).astype(np.float32)


def oklch(lin):
    lab = lin2oklab(lin)
    return lab[..., 0], np.hypot(lab[..., 1], lab[..., 2]), np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360


def chroma_cap(lin, cap):
    """scale OKLab chroma down to <= cap (narrative .13, heraldic .20)."""
    lab = lin2oklab(lin)
    C = np.hypot(lab[..., 1], lab[..., 2]) + 1e-9
    k = np.minimum(1.0, cap / C)
    lab[..., 1] *= k; lab[..., 2] *= k
    return oklab2lin(lab)


# ---------------- dye lots ----------------
class ShadeSet:
    """A limited set of thread shades for a region (dye lots), chosen stochastically per stitch."""

    def __init__(self, lab_cols, seed=0):
        self.lab = np.asarray(lab_cols, np.float32).reshape(-1, 3)
        self.lin = oklab2lin(self.lab)
        self.r = np.random.default_rng(seed)

    @staticmethod
    def from_pixels(lin_pixels, n, pull=None, pull_amt=0.35, seed=0, chroma_max=None):
        lab = lin2oklab(np.asarray(lin_pixels, np.float32).reshape(-1, 3))
        if len(lab) > 20000:
            lab = lab[np.random.default_rng(seed).permutation(len(lab))[:20000]]
        n = max(1, min(n, len(lab) // 20))
        Z = (lab * np.array([1, 1.5, 1.5], np.float32)).astype(np.float32)
        if n == 1 or len(Z) < 4:
            cen = Z.mean(0, keepdims=True)
        else:
            cv2.setRNGSeed(int(seed) & 0x7fffffff)
            _, _, cen = cv2.kmeans(Z, n, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-4), 2,
                                   cv2.KMEANS_PP_CENTERS)
        cen = cen / np.array([1, 1.5, 1.5], np.float32)
        if pull is not None:
            pl = lin2oklab(np.asarray(pull, np.float32).reshape(-1, 3))
            for i in range(len(cen)):
                d = np.hypot(pl[:, 1] - cen[i, 1], pl[:, 2] - cen[i, 2]) + 0.3 * np.abs(pl[:, 0] - cen[i, 0])
                k = int(np.argmin(d))
                cen[i, 1:] = cen[i, 1:] * (1 - pull_amt) + pl[k, 1:] * pull_amt
                cen[i, 0] = cen[i, 0] * (1 - 0.25 * pull_amt) + pl[k, 0] * 0.25 * pull_amt
        if chroma_max is not None:
            C = np.hypot(cen[:, 1], cen[:, 2]) + 1e-9
            k = np.minimum(1, chroma_max / C)
            cen[:, 1] *= k; cen[:, 2] *= k
        cen = cen[np.argsort(cen[:, 0])]
        return ShadeSet(cen, seed)

    def pick(self, lin_col, temp=0.6):
        """stochastic nearest-shade choice (2 nearest, weighted) + per-strand dye jitter -> linear rgb"""
        lab = lin2oklab(np.asarray(lin_col, np.float32)[None])[0]
        d = np.sqrt(((self.lab - lab) ** 2 * np.array([1.0, 2.0, 2.0])).sum(1))
        o = np.argsort(d)
        k = o[0]
        if len(o) > 1:
            d0, d1 = d[o[0]], d[o[1]]
            p1 = (d0 / (d0 + d1 + 1e-6)) * temp * 2
            if self.r.random() < p1 * 0.5:
                k = o[1]
        lab2 = self.lab[k].copy()
        lab2[0] *= 1 + self.r.uniform(-0.045, 0.045)        # L +/-4.5 %
        cs = 1 + self.r.uniform(-0.08, 0.08)                # C +/-8 %
        hrot = math.radians(self.r.uniform(-3, 3))          # h +/-3 deg
        a, b = lab2[1] * cs, lab2[2] * cs
        lab2[1] = a * math.cos(hrot) - b * math.sin(hrot); lab2[2] = a * math.sin(hrot) + b * math.cos(hrot)
        return oklab2lin(lab2[None])[0]
