"""Shared constants for the CHRONICA PoC 'the cloth becomes the board' (f1664-1782).
Board space: R25 maps in 'board px' (x right = game +x, y down = game +z), PX px/mm, MMU mm per game unit.
Game/world: Godot axes, Grandbois hex centre = origin. Blender: (x, y, z) = (gx, -gz, gy), 1 BU = 1 game unit."""
import math, os
import numpy as np
A = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa'
POC = f'{A}/prod/poc'
RND = f'{A}/rnd/relight25d'
PX = 6.0            # map px per mm (screen top-down is ~4.7 px/mm -> 1.28x, inside the 1.0-1.4x LOD rule)
MMU = 27.5          # mm per game unit (hex circumradius); hex = 47.6 mm across flats
PPU = PX * MMU      # map px per game unit (165)
BX0, BX1, BZ0, BZ1 = -15.6, 11.6, -8.6, 8.0
W = int(round((BX1 - BX0) * PPU)); H = int(round((BZ1 - BZ0) * PPU))
SQ3 = math.sqrt(3.0)
FPS = 30
F0, F1 = 1664, 1782
F_STITCH0, F_LASTHEX, F_SWAP0, F_SWAP1, F_CRANE0, F_CRANE1 = 1664, 1719, 1720, 1725, 1726, 1766
# menu camera (decoded camera_rig.gd at zoom 11): pitch 66.087 deg, distance 20.9, vfov 30; focus = Grandbois + (-2.2, 0, 0.5)
ZOOM = 11.0
PITCH_MENU = 64 + 12 * (ZOOM - 7) / 23.0
DIST = ZOOM * 1.9
TARGET = (-2.2, 0.0, 0.5)
FOV_V = 30.0


def w2px(x, z):
    return (np.asarray(x) - BX0) * PPU, (np.asarray(z) - BZ0) * PPU


def px2w(u, v):
    return BX0 + np.asarray(u) / PPU, BZ0 + np.asarray(v) / PPU


def hex_center(q, r):
    return SQ3 * (q + r / 2.0), 1.5 * r


def hex_corners(q, r, rad=1.0):
    cx, cz = hex_center(q, r)
    return [(cx + rad * math.cos(math.radians(60 * i - 30)), cz + rad * math.sin(math.radians(60 * i - 30))) for i in range(6)]


def axial_round(x, z):
    """vectorised world -> axial (q, r)"""
    r = z / 1.5
    q = x / SQ3 - r / 2
    xf, zf = q, r
    yf = -xf - zf
    rx, ry, rz = np.round(xf), np.round(yf), np.round(zf)
    dx, dy, dz = np.abs(rx - xf), np.abs(ry - yf), np.abs(rz - zf)
    c1 = (dx > dy) & (dx > dz)
    c2 = (~c1) & (dy > dz)
    rx = np.where(c1, -ry - rz, rx)
    rz = np.where(~c1 & ~c2, -rx - ry, rz)
    return rx.astype(np.int32), rz.astype(np.int32)


def edge_dist(x, z, cx, cz):
    """distance (game units) from point to the nearest edge of the pointy-top unit hex centred at (cx, cz); >0 inside"""
    dx, dz = x - cx, z - cz
    a = np.abs(dx); b = np.abs(0.5 * dx + 0.8660254 * dz); c = np.abs(-0.5 * dx + 0.8660254 * dz)
    return 0.8660254 - np.maximum(a, np.maximum(b, c))


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, np.float64) - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def ease_io(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def camera_pose(f):
    """returns dict(pitch_deg, target(3), dist) of the PoC camera at global frame f (on ones)."""
    if f <= F_CRANE0:
        pitch = 90.0
    elif f >= F_CRANE1:
        pitch = PITCH_MENU
    else:
        t = (f - F_CRANE0) / (F_CRANE1 - F_CRANE0)
        # ease-in (slow start) + long ease-out landing: within 0.3 deg by f1760, exact at f1766
        tau = 1 - (1 - t) ** 1.8                      # front-load the move (long ease-out landing)
        s = tau ** 3 * (tau * (6 * tau - 15) + 10)       # smootherstep: zero velocity + acceleration at both ends
        pitch = 90.0 + (PITCH_MENU - 90.0) * s
    return dict(pitch=pitch, target=TARGET, dist=DIST)
