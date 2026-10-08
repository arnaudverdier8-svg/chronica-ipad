"""Act V light model of the PoC (v2): two candle pools, one source of truth for R25 (2D frames), Eevee (3D crane) and COMP.

Left candle lit on the bass f1664, right candle lit on 'age' f1707. Both are 3200 K practicals low in front of the board
(elevation ~21 deg at Grandbois, so the cloth is lit raking). Each candle is a point source with a directive lobe (the
pierced reflector / holder around the flame): its irradiance on the cloth is
    E(x) = lobe(x) * (d0 / |P_candle - x|)^2        (inverse-square from the 3D candle position, plus an anisotropic Gaussian lobe
                                                       centred on the focal pool around Grandbois, stretched along the azimuth)
so the surround falls toward near-black by physics of the light, not by a screen-space vignette. A cool navy fill carries key:fill 4:1 at the pool peak.
Everything here is a function of the global frame number (candle ignition, flicker <= 3 %, the f1744-1760 swell of the pools themselves).
Board space: game units, x right, z down (image y), Grandbois = origin.  Light vectors follow emb.shade.light_vec (az 0 = from +x)."""
import math, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

FOCUS = (0.0, 0.0)
EL = 21.0
NEUTRAL = bool(int(os.environ.get('CHRON_NEUTRAL', '0')))   # palette check: white light, flat pools (same intensity as the pool peak)
KEY_TINT = 0.40          # bible: 20-50 % tints of the kelvin display colour (3200 K candle)
_FILL = (0.60, 0.72, 1.0)
FILL_COL = (1.0, 1.0, 1.0) if NEUTRAL else _FILL   # cool, navy-dominant fill
FILL_I = 0.52            # relative to key_i ~ 2.6 (key:fill ~ 4:1 on the flat cloth at the pool peak)

CANDLE = {
    'L': dict(az=212.0, el=EL, key_i=2.7, centre=(-1.3, 0.25), Ru=7.0, Rv=3.8, p=1.2, floor=0.004, dist=33.0, t_on=1662.8, tau=1.35),
    'R': dict(az=328.0, el=EL, key_i=2.2, centre=(1.5, 0.0), Ru=5.4, Rv=3.8, p=1.2, floor=0.004, dist=33.0, t_on=1706.8, tau=1.35),
}
FILL_FLOOR = 0.05        # fill never quite vanishes (navy surround)
FILL_GAMMA = 0.75        # the fill is bounce from the pools: it follows their sum


def _hex_lin(h):
    h = h.lstrip('#'); c = np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


def kelvin(K):
    """display colour of a light temperature (palette.json light_kelvin_display), linear RGB normalised to max 1 (pure numpy: also runs inside Blender)"""
    import json as _json
    tab = {int(k[:-1]): v for k, v in _json.load(open(f'{A}/style/palette.json'))['light_kelvin_display'].items()}
    ks = sorted(tab)
    K = float(np.clip(K, ks[0], ks[-1]))
    i = max(0, min(len(ks) - 2, int(np.searchsorted(ks, K)) - 1))
    a, b = ks[i], ks[i + 1]
    t = (K - a) / (b - a)
    c = _hex_lin(tab[a]) * (1 - t) + _hex_lin(tab[b]) * t
    return (c / c.max()).astype(np.float32)


def key_colour(K=3200, tint=KEY_TINT):
    if NEUTRAL: return np.ones(3, np.float32)
    """white mixed with the Kelvin display colour at `tint` (library convention chron.color.light_colour)"""
    c = (1 - tint) * np.ones(3, np.float32) + tint * kelvin(K)
    return (c / float(c @ np.array([0.2126, 0.7152, 0.0722], np.float32))).astype(np.float32)      # luminance-normalised: the warm candle is as bright as the neutral light at the same exposure


def lvec(az, el):
    a, e = math.radians(az), math.radians(el)
    v = np.array([math.cos(a) * math.cos(e), -math.sin(a) * math.cos(e), math.sin(e)], np.float32)
    return v / np.linalg.norm(v)


def candle_pos(name):
    """candle position (game units: x, z, height above the cloth)"""
    c = CANDLE[name]
    L = lvec(c['az'], c['el'])
    d = c['dist']
    return np.array([FOCUS[0] + L[0] * d, FOCUS[1] + L[1] * d, L[2] * d], np.float64)


def pool(name, gx, gz, scale=1.0, shift=(0.0, 0.0)):
    """irradiance factor of candle `name` on the cloth at world points (gx, gz) (game units); ~1 at the pool centre"""
    c = CANDLE[name]
    L = lvec(c['az'], c['el'])
    u = np.array([L[0], L[1]], np.float64); u /= np.linalg.norm(u)
    v = np.array([-u[1], u[0]])
    dx = np.asarray(gx, np.float64) - (c['centre'][0] + shift[0]); dz = np.asarray(gz, np.float64) - (c['centre'][1] + shift[1])
    a = dx * u[0] + dz * u[1]; b = dx * v[0] + dz * v[1]
    r2 = (a / (c['Ru'] * scale)) ** 2 + (b / (c['Rv'] * scale)) ** 2
    lobe = c['floor'] + (1 - c['floor']) * np.exp(-r2 ** c['p'])
    P = candle_pos(name)
    d2 = (np.asarray(gx) - P[0]) ** 2 + (np.asarray(gz) - P[1]) ** 2 + P[2] ** 2
    d0 = c['dist']
    inv = (d0 * d0) / d2
    return (lobe * inv).astype(np.float32)


def ignite(f, t_on, tau):
    return 1.0 - math.exp(-max(0.0, f - t_on) / tau) if f >= t_on else 0.0


def flicker(f, seed):
    """local candle flicker, <= ~2.5 % (bible: candles <= 3 %); smooth, deterministic"""
    t = f / FPS
    ph = [(seed * 1.713 + k * 2.399) for k in range(3)]
    return 1.0 + 0.009 * math.sin(2 * math.pi * 5.3 * t + ph[0]) + 0.007 * math.sin(2 * math.pi * 8.1 * t + ph[1]) \
        + 0.005 * math.sin(2 * math.pi * 3.4 * t + ph[2])


def swell(f):
    """candle swell into the climax: the pools themselves brighten (+0.28 EV peak at f1760) and widen slightly; settles by f1782"""
    if f <= 1744: return 0.0
    if f <= 1760:
        t = (f - 1744) / 16.0; return t * t * (3 - 2 * t)
    t = min(1.0, (f - 1760) / 22.0)
    return 1.0 - 0.55 * (t * t * (3 - 2 * t))


def gain(name, f, with_swell=True):
    c = CANDLE[name]
    g = ignite(f, c['t_on'], c['tau']) * flicker(f, 1 if name == 'L' else 2)
    if with_swell:
        g *= 2.0 ** (0.28 * swell(f))
    return g


def pool_scale(f):
    return 1.0 + 0.07 * swell(f)


def fill_map(kL, kR, gL=1.0, gR=1.0):
    """navy fill = bounce from the pools: follows their (gain-weighted) sum so the surround sinks to near-black"""
    wl, wr = CANDLE['L']['key_i'], CANDLE['R']['key_i']
    tot = (wl * gL * kL + wr * gR * kR) / (wl + wr)
    return (FILL_FLOOR + (1 - FILL_FLOOR) * np.clip(tot, 0, 4) ** FILL_GAMMA).astype(np.float32)


def kmaps(shape, x0=0, y0=0, step=1, f=None):
    """float32 pool maps (L, R, F) on the board-pixel grid (x0, y0 origin, `step` px per sample).
    f None -> base pools (the state R25 radiance is baked in, both candles at gain 1)"""
    Hh, Ww = shape
    xs = (np.arange(Ww) * step + x0 + 0.5 * step) / PPU + BX0
    zs = (np.arange(Hh) * step + y0 + 0.5 * step) / PPU + BZ0
    GX, GZ = np.meshgrid(xs, zs)
    sc = 1.0 if f is None else pool_scale(f)
    if NEUTRAL:
        o = np.ones(GX.shape, np.float32)
        return o, o.copy(), o.copy()
    kL, kR = pool('L', GX, GZ, sc), pool('R', GX, GZ, sc)
    return kL, kR, fill_map(kL, kR)


def light_table():
    """everything Eevee / R25 need to know about the rig (written to data/eevee/lights.json)"""
    col = [float(v) for v in key_colour()]
    out = dict(el=EL, key_colour=col, fill_colour=list(FILL_COL), fill_i=FILL_I, candles={})
    for n, c in CANDLE.items():
        L = lvec(c['az'], c['el'])
        out['candles'][n] = dict(c, L_board=[float(v) for v in L], pos=[float(v) for v in candle_pos(n)])
    return out
