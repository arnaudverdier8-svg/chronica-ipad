"""Oblique / perspective camera for the 2.5D maps: per-pixel ray march through two height-field layers
(0 = canvas, 1 = liftable figure slip with thickness and side walls), mip-filtered colour gather,
cast shadow of the lifted slip onto the canvas, depth-of-field from the depth buffer."""
import math
import numpy as np, cv2
from numba import njit, prange


# ------------------------------------------------------------------ camera
class Camera:
    def __init__(self, target, dist, tilt_deg, yaw_deg, fov_deg, W, H, roll_deg=0.0):
        t = np.asarray(target, np.float64)
        ti, ya = math.radians(tilt_deg), math.radians(yaw_deg)
        d = np.array([math.sin(ya) * math.sin(ti), math.cos(ya) * math.sin(ti), math.cos(ti)])
        self.pos = t + dist * d
        f = -d
        upw = np.array([0.0, -1.0, 0.0]) if tilt_deg > 1e-3 else np.array([0.0, -1.0, 0.0])
        r = np.cross(upw, f); r /= np.linalg.norm(r)
        u = np.cross(f, r)
        if roll_deg:
            a = math.radians(roll_deg); r, u = r * math.cos(a) + u * math.sin(a), -r * math.sin(a) + u * math.cos(a)
        self.f, self.r, self.u = f, r, u
        self.tany = math.tan(math.radians(fov_deg) / 2); self.tanx = self.tany * W / H
        self.W, self.H = W, H
        self.focus = dist

    def project(self, P):
        """P (...,3) mm -> screen px (...,2), depth along forward (mm)"""
        q = P - self.pos
        z = q @ self.f
        x = (q @ self.r) / (z * self.tanx); y = (q @ self.u) / (z * self.tany)
        Q = np.stack([(x + 1) * 0.5 * self.W, (1 - y) * 0.5 * self.H], -1)
        return Q.astype(np.float32), z.astype(np.float32)

    def args(self):
        return (self.pos.astype(np.float32), self.f.astype(np.float32), self.r.astype(np.float32), self.u.astype(np.float32),
                float(self.tanx), float(self.tany))


# ------------------------------------------------------------------ helpers
@njit(cache=True, inline='always')
def _bil(a, x, y):
    H, W = a.shape
    if x < 0: x = 0.0
    if y < 0: y = 0.0
    if x > W - 1.001: x = W - 1.001
    if y > H - 1.001: y = H - 1.001
    x0 = int(x); y0 = int(y); fx = x - x0; fy = y - y0
    return (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy)
            + a[y0 + 1, x0] * (1 - fx) * fy + a[y0 + 1, x0 + 1] * fx * fy)


@njit(parallel=True, cache=True)
def raymarch(pos, fw, rt, up, tanx, tany, Wo, Ho, sub_x, sub_y,
             h0, PX, hmin0, hmax0,
             use1, h1, a1, lift1, ox1, oy1, th1, zmin1, zmax1,
             lay, U, V, T):
    H0, W0 = h0.shape
    H1, W1 = h1.shape
    for py in prange(Ho):
        for px in range(Wo):
            sx = (2 * (px + sub_x) / Wo - 1) * tanx
            sy = (1 - 2 * (py + sub_y) / Ho) * tany
            dx = fw[0] + sx * rt[0] + sy * up[0]; dy = fw[1] + sx * rt[1] + sy * up[1]; dz = fw[2] + sx * rt[2] + sy * up[2]
            dl = math.sqrt(dx * dx + dy * dy + dz * dz); dx /= dl; dy /= dl; dz /= dl
            best_t = 1e30; bl = -1; bu = 0.0; bv = 0.0
            hs = math.sqrt(dx * dx + dy * dy) + 1e-6
            dt = 0.5 / PX / hs
            dtv = 0.06 / (abs(dz) + 1e-6)     # also limit vertical travel per step (rays near the nadir)
            if dtv < dt: dt = dtv
            # ---------------- layer 1 (figure slip)
            if use1 and dz < -1e-4:
                t0 = (zmax1 - pos[2]) / dz; t1 = (zmin1 - pos[2]) / dz
                if t0 < 0: t0 = 0.0
                prev_above = False; prev_valid = False
                t = t0
                while t <= t1:
                    x = (pos[0] + t * dx) * PX - ox1; y = (pos[1] + t * dy) * PX - oy1; z = pos[2] + t * dz
                    if x >= 0 and y >= 0 and x < W1 - 1 and y < H1 - 1:
                        a = _bil(a1, x, y)
                        if a >= 0.5:
                            L = _bil(lift1, x, y)
                            top = L + _bil(h1, x, y); bot = L - th1
                            if z <= top and z >= bot:
                                if prev_valid and prev_above:
                                    ta = t - dt; tb = t
                                    for it in range(6):
                                        tm = 0.5 * (ta + tb)
                                        xm = (pos[0] + tm * dx) * PX - ox1; ym = (pos[1] + tm * dy) * PX - oy1; zm = pos[2] + tm * dz
                                        if zm <= _bil(lift1, xm, ym) + _bil(h1, xm, ym): tb = tm
                                        else: ta = tm
                                    best_t = tb; bl = 1
                                    bu = (pos[0] + tb * dx) * PX - ox1; bv = (pos[1] + tb * dy) * PX - oy1
                                else:
                                    ta = t - dt; tb = t
                                    for it in range(6):
                                        tm = 0.5 * (ta + tb)
                                        xm = (pos[0] + tm * dx) * PX - ox1; ym = (pos[1] + tm * dy) * PX - oy1
                                        if _bil(a1, xm, ym) >= 0.5: tb = tm
                                        else: ta = tm
                                    best_t = tb; bl = 2
                                    bu = (pos[0] + tb * dx) * PX - ox1; bv = (pos[1] + tb * dy) * PX - oy1
                                break
                            prev_above = z > top
                        else:
                            prev_above = False
                        prev_valid = True
                    t += dt
            # ---------------- layer 0 (canvas)
            if dz < -1e-4:
                t0 = (hmax0 - pos[2]) / dz; t1 = (hmin0 - pos[2]) / dz
                if t0 < 0: t0 = 0.0
                if t1 > best_t: t1 = best_t
                t = t0
                while t <= t1 + dt:
                    if t > t1: t = t1
                    x = (pos[0] + t * dx) * PX; y = (pos[1] + t * dy) * PX; z = pos[2] + t * dz
                    if x < 0 or y < 0 or x >= W0 - 1 or y >= H0 - 1:
                        if t >= t1: break
                        t += dt; continue
                    if z <= _bil(h0, x, y):
                        ta = t - dt; tb = t
                        for it in range(6):
                            tm = 0.5 * (ta + tb)
                            if pos[2] + tm * dz <= _bil(h0, (pos[0] + tm * dx) * PX, (pos[1] + tm * dy) * PX): tb = tm
                            else: ta = tm
                        if tb < best_t:
                            best_t = tb; bl = 0
                            bu = (pos[0] + tb * dx) * PX; bv = (pos[1] + tb * dy) * PX
                        break
                    if t >= t1: break
                    t += dt
            lay[py, px] = bl; U[py, px] = bu; V[py, px] = bv; T[py, px] = best_t


@njit(cache=True, inline='always')
def _tri(pyr0, pyr1, pyr2, pyr3, pyr4, u, v, lod, c):
    if lod < 0: lod = 0.0
    if lod > 3.999: lod = 3.999
    l = int(lod); f = lod - l
    s0 = 1.0 / (1 << l); s1 = 0.5 * s0
    if l == 0: a = pyr0; b = pyr1
    elif l == 1: a = pyr1; b = pyr2
    elif l == 2: a = pyr2; b = pyr3
    else: a = pyr3; b = pyr4
    va = _bil(a[:, :, c], u * s0 - 0.5 + 0.5 * s0, v * s0 - 0.5 + 0.5 * s0)
    vb = _bil(b[:, :, c], u * s1 - 0.5 + 0.5 * s1, v * s1 - 0.5 + 0.5 * s1)
    return va * (1 - f) + vb * f


@njit(parallel=True, cache=True)
def gather(lay, U, V, T, pix_ang, PX, p00, p01, p02, p03, p04, p10, p11, p12, p13, p14, edge_rgb, a1, L, kc, fc, bg, out,
           lod_bias):
    Ho, Wo = lay.shape
    for py in prange(Ho):
        for px in range(Wo):
            l = lay[py, px]
            if l < 0:
                out[py, px, 0] = bg[0]; out[py, px, 1] = bg[1]; out[py, px, 2] = bg[2]; continue
            fp = T[py, px] * pix_ang * PX
            lod = math.log2(fp) + lod_bias if fp > 1 else lod_bias
            u = U[py, px]; v = V[py, px]
            if l == 0:
                for c in range(3): out[py, px, c] = _tri(p00, p01, p02, p03, p04, u, v, lod, c)
            elif l == 1:
                for c in range(3): out[py, px, c] = _tri(p10, p11, p12, p13, p14, u, v, lod, c)
            else:
                gx = _bil(a1, u + 1, v) - _bil(a1, u - 1, v); gy = _bil(a1, u, v + 1) - _bil(a1, u, v - 1)
                gl = math.sqrt(gx * gx + gy * gy) + 1e-6
                nx = -gx / gl; ny = -gy / gl
                ndl = nx * L[0] + ny * L[1]
                if ndl < 0: ndl = 0.0
                for c in range(3):
                    out[py, px, c] = edge_rgb[c] * (fc[c] * 0.8 + kc[c] * ndl * 0.7)


@njit(parallel=True, cache=True)
def slab_shadow(h0, PX, x0, y0, x1, y1, lx, ly, tan_el, h1, a1, lift1, ox1, oy1, th1, zmax1, ksoft, vis, zmin1=0.0, sc1=1.0):
    """visibility of canvas texels (window x0..x1,y0..y1) w.r.t. the figure slab (top=lift+h1, bottom=lift-th)."""
    H1, W1 = h1.shape
    for y in prange(y0, y1):
        for x in range(x0, x1):
            z0 = h0[y, x]
            if zmax1 <= z0: continue
            smax = (zmax1 - z0) / tan_el * PX
            smin = (zmin1 - z0) / tan_el * PX - 2.0
            res = 1.0
            s = 1.0 if smin < 1.0 else smin
            while s < smax:
                xs = (x + lx * s) * sc1 - ox1; ys = (y + ly * s) * sc1 - oy1
                if xs >= 0 and ys >= 0 and xs < W1 - 1 and ys < H1 - 1:
                    a = _bil(a1, xs, ys)
                    if a > 0.05:
                        zr = z0 + s / PX * tan_el
                        Lf = _bil(lift1, xs, ys)
                        top = Lf + _bil(h1, xs, ys); bot = Lf - th1
                        if zr <= top and zr >= bot and a >= 0.5:
                            res = 0.0; break
                        clr = zr - top if zr > top else bot - zr
                        if clr < 0: clr = 0.0
                        cand = ksoft * clr / (s / PX) + (1 - a) * 0.0
                        # edge softness: partially covered alpha counts as partial occluder
                        cand = min(1.0, cand) * 1.0
                        if a >= 0.5 and cand < res: res = cand
                s += 1.0
            vis[y, x] = res


def pyramid(img, n=5):
    p = [np.ascontiguousarray(img, np.float32)]
    for i in range(n - 1):
        p.append(cv2.pyrDown(p[-1]))
    return p


def dof(img, depth, focus, strength_px, max_px=12.0):
    """mip-style depth of field: per-pixel blend of pre-blurred images by circle of confusion."""
    coc = np.clip(strength_px * np.abs(1 - focus / np.maximum(depth, 1e-3)), 0, max_px).astype(np.float32)
    coc = cv2.GaussianBlur(coc, (0, 0), 2.0)
    sig = [0, 1.0, 2.0, 4.0, 8.0, 16.0]
    stack = [img] + [cv2.GaussianBlur(img, (0, 0), s) for s in sig[1:]]
    out = np.zeros_like(img)
    s = coc * 0.5   # sigma ~ coc/2
    for i in range(len(sig) - 1):
        a, b = sig[i], sig[i + 1]
        w = np.clip((s - a) / (b - a), 0, 1)
        sel = (s >= a) & (s < b) if i < len(sig) - 2 else (s >= a)
        blend = stack[i] * (1 - w[..., None]) + stack[i + 1] * w[..., None]
        out[sel] = blend[sel]
    return out, coc
