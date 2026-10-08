"""Frame-based animation of the 3D part (f1726-1782), v2: piece rise schedule (pop-up hinge on twos, staggered outward from Grandbois so the
last tethers snap into the f1760 peak), height unfolding (foreshortened elevation -> full height), relief growth, per-hex coupon swell,
tether snap times, heal of the footprints.  Pure functions of the global frame number (deterministic)."""
import math, json
import numpy as np
from common import *

STEP = 1                # v3: everything on ones (the critics: pieces on twos stutter against the smooth crane)
RISE_T0 = 1726          # first piece (Grandbois) starts to peel ON the 'remembered' bass (f1726), decisively
RISE_LEN = 12           # frames from first lift to settled (towns / camps; trees and cards pop faster)
LAST_START = 1751       # the last pieces start here: their tethers snap f1756-1760, settled f1761-1763
# hinge keys: (frames since start, angle from upright in deg); lying = 90
HINGE = [(0, 80.0), (2, 66.0), (4, 44.0), (6, 18.0), (8, -7.0), (10, 3.0), (12, 0.0)]
HINGE_BIG = [(0, 78.0), (2, 62.0), (4, 40.0), (6, 17.0), (8, -1.5), (10, 1.2), (12, 0.0)]   # towns / camps: a hair of overshoot only (a deep floor must never dip under the cloth)
HERO = {'town_Grandbois': 1726, 'town_Hautecouronne': 1733, 'town_Brumecourt': 1740, 'town_Vaugrise': 1746, 'town_Sablon': 1750, 'banner_Grandbois': 1751}
HINGE_HERO = [(0, 64.0), (2, 47.0), (4, 30.0), (6, 13.0), (8, -2.0), (10, 2.0), (12, 0.0)]    # Grandbois: a decisive first step on the bass (v2: 78 deg at the first frame)
RISE_DUR = {'town': 12.0, 'site': 11.0, 'lumber': 10.0, 'banner': 12.0, 'card': 9.0, 'tree': 8.0}


def _h(*a):
    v = 2166136261
    for x in a:
        v = ((v ^ (int(x) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return v / 4294967295.0


def twos(f, f0=F_CRANE0):
    """animation clock: v3 samples every frame (STEP = 1); STEP = 2 gives the v2 stop-motion"""
    return f - ((f - f0) % STEP)


TYPE_OFF = {'town': 0.0, 'site': 1.0, 'card': 1.5, 'lumber': 1.5, 'tree': 2.0, 'banner': 5.0}


def rise_start(p, idx, rank_frac=None):
    """staggered outward from Grandbois: the start follows the piece's rank by distance (so the peeling is spread over f1727-1751 with more pieces late,
    i.e. it keeps going into the f1755-1760 peak), plus per-piece jitter and a type offset.  The five towns and the banner follow the HERO table."""
    if p['id'] in HERO: return HERO[p['id']]
    d = math.hypot(p['x'], p['z'])
    j = _h(idx, 77) * (3.0 if p['kind'] in ('tree', 'lumber') else 1.5)
    if rank_frac is None:
        f = RISE_T0 + 1.9 * d + TYPE_OFF[p['kind']] + j
    else:
        f = RISE_T0 + 1.0 + (LAST_START - RISE_T0 - 4.0) * rank_frac ** 1.12 + TYPE_OFF[p['kind']] + j
    f = min(f, LAST_START)
    return int(twos(int(round(f))))


def hinge_angle(p, start, f):
    """angle from upright (deg); cards end leaning back (62 deg from the cloth)"""
    if f < start: return None
    HG = HINGE_BIG if p['kind'] in ('town', 'site', 'lumber', 'banner') else HINGE
    if p.get('id') == 'town_Grandbois': HG = HINGE_HERO
    D = RISE_DUR.get(p['kind'], 12.0)
    t = (f - start) * 12.0 / D          # v3: per-kind rise length (ones); the hinge keys are defined on a 12-frame clock
    if t >= HG[-1][0]:
        a = 0.0
    else:
        for (t0, a0), (t1, a1) in zip(HG[:-1], HG[1:]):
            if t0 <= t < t1:
                a = a0 + (a1 - a0) * (t - t0) / (t1 - t0); break
    if p['kind'] == 'card':
        lean = 90.0 - 62.0
        return lean + a * (90.0 - lean) / 90.0
    return a


def depth_scale(angle):
    if angle is None: return 0.02
    return max(0.02, min(1.0, 1 - max(angle, 0) / 90.0)) ** 0.6


def height_scale(angle, k):
    """the lying elevation is foreshortened by k; the piece grows to its full height as it stands up"""
    if angle is None: return k
    u = 1 - min(max(angle, 0.0), 90.0) / 90.0
    u = u * u * (3 - 2 * u)
    return k + (1 - k) * u


def growth(f):
    """baked relief rises from flat (zero-tilt swap) to full as the crane starts (on twos)"""
    t = (twos(f) - (F_CRANE0 + 1)) / 18.0
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def hex_swell_start(q, r):
    x, z = hex_center(q, r)
    return twos(int(round(1726 + 1.15 * math.hypot(x, z) + 2 * _h(q, r, 5))))       # v3: the capitonnage swell ripples outward from Grandbois starting ON the f1726 bass


def swell(f, start):
    """extra padded-coupon swell (0..1, slight overshoot) on twos"""
    t = (twos(f) - start) / 8.0
    if t <= 0: return 0.0
    if t >= 1.5: return 1.0
    if t <= 1: return 1.12 * (t * t * (3 - 2 * t))
    return 1.12 - 0.12 * (t - 1) / 0.5


def schedule(pieces):
    live = [i for i, p in enumerate(pieces) if not p.get('skip')]
    order = sorted(live, key=lambda i: math.hypot(pieces[i]['x'], pieces[i]['z']))
    rank = {i: k / max(1, len(order) - 1) for k, i in enumerate(order)}
    out = []
    for i, p in enumerate(pieces):
        if p.get('skip'): out.append(None); continue
        out.append(rise_start(p, i, rank[i]))
    return out


def tether_snap_frames(start, n, idx, kind='tree'):
    """each tether snaps once stretched, one by one over frames 6..10 of the rise (>= 6 frames of tethers); never later than f1760"""
    D = RISE_DUR.get(kind, 12.0)
    sn = [start + int(round(D * 0.50)) + int(round(0.36 * D * ((k + _h(idx, k, 3)) / max(1, n)))) for k in range(n)]
    return [min(v, 1760) for v in sn]


HEAL_DELAY = 14         # footprints stay open this many frames after the piece starts to rise (>= 12 shown), then the satin closes on twos
HEAL_SPAN = 7           # needle sweep across the footprint
