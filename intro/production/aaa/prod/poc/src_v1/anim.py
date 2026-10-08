"""Frame-based animation of the 3D part (f1726-1766): piece rise schedule (pop-up hinge on twos), relief growth,
per-hex coupon swell, tether snap times. Pure functions of the global frame number (deterministic)."""
import math, json
import numpy as np
from common import *

RISE_T0 = 1728          # first piece (Grandbois) starts to peel
RISE_LEN = 12           # frames from first lift to settled
TYPE_OFF = {'town': 0.0, 'site': 2.0, 'card': 3.0, 'lumber': 4.0, 'tree': 5.0, 'banner': 8.0}
# hinge keys: (frames since start, angle from upright in deg); lying = 90
HINGE = [(0, 84.0), (2, 70.0), (4, 47.0), (6, 19.0), (8, -7.0), (10, 3.0), (12, 0.0)]


def _h(*a):
    v = 2166136261
    for x in a:
        v = ((v ^ (int(x) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return v / 4294967295.0


def twos(f, f0=F_CRANE0):
    """stop-motion timing: animation sampled on even offsets from f0"""
    return f - ((f - f0) % 2)


def rise_start(p, idx):
    d = math.hypot(p['x'], p['z'])
    j = _h(idx, 77) * (3.0 if p['kind'] in ('tree', 'lumber') else 1.5)
    f = RISE_T0 + 1.05 * d + TYPE_OFF[p['kind']] + j
    f = min(f, 1760 - RISE_LEN)
    return int(twos(int(round(f))))


def hinge_angle(p, start, f):
    """angle from upright (deg); cards end leaning back (62 deg from the cloth)"""
    t = twos(f) - start
    if t < 0: return None
    if t >= HINGE[-1][0]:
        a = 0.0
    else:
        for (t0, a0), (t1, a1) in zip(HINGE[:-1], HINGE[1:]):
            if t0 <= t < t1:
                a = a0 + (a1 - a0) * (t - t0) / (t1 - t0); break
    if p['kind'] == 'card':
        lean = 90.0 - 62.0
        return lean + a * (90.0 - lean) / 90.0
    return a


def depth_scale(angle):
    if angle is None: return 0.02
    return max(0.02, min(1.0, 1 - max(angle, 0) / 90.0)) ** 0.6


def growth(f):
    """baked relief rises from flat (zero-tilt swap) to full as the crane starts (on twos)"""
    t = (twos(f) - (F_CRANE0 + 1)) / 18.0
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def hex_swell_start(q, r):
    x, z = hex_center(q, r)
    return twos(int(round(1730 + 0.95 * math.hypot(x, z) + 2 * _h(q, r, 5))))


def swell(f, start):
    """extra padded-coupon swell (0..1, slight overshoot) on twos"""
    t = (twos(f) - start) / 8.0
    if t <= 0: return 0.0
    if t >= 1.5: return 1.0
    if t <= 1: return 1.12 * (t * t * (3 - 2 * t))
    return 1.12 - 0.12 * (t - 1) / 0.5


def schedule(pieces):
    out = []
    for i, p in enumerate(pieces):
        if p.get('skip'): out.append(None); continue
        out.append(rise_start(p, i))
    return out


def tether_snap_frames(start, n, idx):
    """each tether snaps once stretched, one by one over frames 6..10 of the rise (>= 6 frames of tethers)"""
    return [start + 6 + int(round(4.5 * ((k + _h(idx, k, 3)) / max(1, n)))) for k in range(n)]
