"""Godot CameraRig model of the game's menu camera (decoded view/camera_rig.gd) and ground back-projection.
World: Godot axes (x right, y up, z toward the viewer). Hex.to_world(q,r) = (sqrt3*(q+r/2), 0, 1.5*r), pointy-top, SIZE 1.
Menu: zoom 11 -> pitch 66.087 deg, distance 20.9, vertical fov 30, focus = Grandbois + (-2.2, 0, 0.5)."""
import math
import numpy as np

SQ3 = 1.7320508


def hex_world(q, r):
    return np.array([SQ3 * (q + r / 2.0), 0.0, 1.5 * r])


def world_hex(x, z):
    r = z / 1.5
    q = x / SQ3 - r / 2
    xf, zf = q, r
    yf = -xf - zf
    rx, ry, rz = np.round(xf), np.round(yf), np.round(zf)
    dx, dy, dz = abs(rx - xf), abs(ry - yf), abs(rz - zf)
    if dx > dy and dx > dz:
        rx = -ry - rz
    elif dy > dz:
        ry = -rx - rz
    else:
        rz = -rx - ry
    return int(rx), int(rz)


def rig(zoom=11.0):
    t = min(max((zoom - 7) / 23.0, 0), 1)
    pitch = math.radians(64 + 12 * t)
    d = zoom * 1.9
    return pitch, d


class Cam:
    """pinhole camera; pos (3,), pitch rad (rotation -pitch about x), fov_v deg, W,H px"""

    def __init__(self, target, pitch, dist, fov_v=30.0, W=1920, H=1080):
        self.p = pitch
        self.C = np.asarray(target, float) + np.array([0, math.sin(pitch) * dist, math.cos(pitch) * dist])
        self.fwd = np.array([0, -math.sin(pitch), -math.cos(pitch)])
        self.up = np.array([0, math.cos(pitch), -math.sin(pitch)])
        self.right = np.array([1.0, 0, 0])
        self.W, self.H = W, H
        self.f = (H / 2) / math.tan(math.radians(fov_v) / 2)

    def project(self, X):
        X = np.asarray(X, float)
        v = X - self.C
        xc = v @ self.right; yc = v @ self.up; zc = v @ self.fwd
        return np.stack([self.W / 2 + self.f * xc / zc, self.H / 2 - self.f * yc / zc], -1), zc

    def ground(self, sx, sy, y=0.0):
        sx = np.asarray(sx, float); sy = np.asarray(sy, float)
        d = self.fwd[None] + ((sx - self.W / 2) / self.f)[..., None] * self.right + (-(sy - self.H / 2) / self.f)[..., None] * self.up
        k = (y - self.C[1]) / d[..., 1]
        return self.C + d * k[..., None]


def menu_cam(W=1920, H=1080, gb=(0.0, 0.0)):
    """menu camera with Grandbois hex centre at world (gb[0], 0, gb[1])"""
    pitch, d = rig(11)
    tgt = np.array([gb[0] - 2.2, 0, gb[1] + 0.5])
    return Cam(tgt, pitch, d, 30, W, H)
