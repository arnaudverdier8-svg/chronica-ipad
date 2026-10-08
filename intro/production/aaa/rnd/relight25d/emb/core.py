"""Core helpers for the 2.5D re-embroider + relight pipeline (approach A).
Units: maps are in pixels at PX px/mm; heights in mm; screen x right, y down, z toward viewer.
"""
import json, math, os
import numpy as np, cv2

A = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa'
PAL = json.load(open(f'{A}/style/palette.json'))

# material ids
LINEN, WOOL, SILK, METAL, INK = 0, 1, 2, 3, 4


def srgb2lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


def lin2srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1 / 2.4) - 0.055).astype(np.float32)


def hex2srgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255


def hex_lin(h):
    return srgb2lin(hex2srgb(h))


def pal(name):
    return hex_lin(PAL['cinematic'][name]['hex'])


# ---------------- OKLab ----------------
def lin2oklab(rgb):
    rgb = np.asarray(rgb, np.float32)
    M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                   [0.2119034982, 0.6806995451, 0.1073969566],
                   [0.0883024619, 0.2817188376, 0.6299787005]], np.float32)
    M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                   [1.9779984951, -2.4285922050, 0.4505937099],
                   [0.0259040371, 0.7827717662, -0.8086757660]], np.float32)
    lms = rgb @ M1.T
    lms = np.cbrt(np.maximum(lms, 0))
    return lms @ M2.T


def oklab2lin(lab):
    lab = np.asarray(lab, np.float32)
    M2i = np.array([[1.0, 0.3963377774, 0.2158037573],
                    [1.0, -0.1055613458, -0.0638541728],
                    [1.0, -0.0894841775, -1.2914855480]], np.float32)
    M1i = np.array([[4.0767416621, -3.3077115913, 0.2309699292],
                    [-1.2684380046, 2.6097574011, -0.3413193965],
                    [-0.0041960863, -0.7034186147, 1.7076147010]], np.float32)
    lms = lab @ M2i.T
    return np.clip((lms ** 3) @ M1i.T, 0, None)


# ---------------- noise ----------------
def smooth_noise(shape, scale_px, seed, octaves=1):
    r = np.random.default_rng(seed)
    out = np.zeros(shape, np.float32)
    amp, sc, tot = 1.0, scale_px, 0
    for o in range(octaves):
        gh, gw = int(shape[0] / sc) + 3, int(shape[1] / sc) + 3
        g = r.standard_normal((gh, gw)).astype(np.float32)
        out += amp * cv2.resize(g, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC) * 0.7
        tot += amp; amp *= 0.5; sc /= 2
    return out / tot


def hash1(i, seed):
    i = np.asarray(i, np.int64)
    v = (i * 374761393 + seed * 668265263) & 0xFFFFFFFF
    v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((v ^ (v >> 16)) & 0xFFFF).astype(np.float32) / 65535.0


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# ---------------- tone / grade ----------------
def aces(x):
    return np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)


BLACK = srgb2lin(hex2srgb('#07070A'))
WHITE = srgb2lin(hex2srgb('#F3E8D0'))
SHADOW_TINT = srgb2lin(hex2srgb('#1A1620'))


def grade(lin, exposure=0.85, grain=0.0, seed=0, sat=1.0):
    """linear scene colour -> sRGB uint8, with bible grade: black/white clip, cool shadows, warm highlights."""
    x = aces(lin * exposure)
    if sat != 1.0:
        l = (x * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
        x = l + (x - l) * sat
    lum = (x * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(-1, keepdims=True)
    sh = np.clip(1 - lum / 0.18, 0, 1) * 0.14
    x = x * (1 - sh) + (x * SHADOW_TINT / SHADOW_TINT.mean()) * sh
    x = BLACK + x * (WHITE - BLACK)
    s = lin2srgb(x)
    if grain > 0:
        r = np.random.default_rng(seed)
        g = r.standard_normal(s.shape[:2]).astype(np.float32)
        g = cv2.GaussianBlur(g, (0, 0), 0.7)
        s = s + grain * g[..., None]
    return np.clip(s * 255 + 0.5, 0, 255).astype(np.uint8)


def save_rgb(path, u8):
    cv2.imwrite(path, cv2.cvtColor(u8, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 95] if path.endswith('.jpg') else [])


def load_rgba(path):
    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im.ndim == 2:
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    if im.shape[2] == 3:
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    else:
        im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA)
    return im
