# strandlib.py - image -> embroidery thread geometry (centre-lines + cross-section + colour)
# Approach B (true thread geometry). Pure numpy/cv2/numba; output consumed by build_blend.py.
# Units: image px in, mm out. Cloth frame: x right, y up, z out of the cloth (mm).
import numpy as np, cv2, json, math
from numba import njit

# ----------------------------------------------------------------------------- colour utils
def srgb_to_lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def lin_to_srgb(c):
    c = np.clip(np.asarray(c, np.float32), 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)

def srgb_to_oklab(rgb):
    l = srgb_to_lin(rgb)
    M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                   [0.2119034982, 0.6806995451, 0.1073969566],
                   [0.0883024619, 0.2817188376, 0.6299787005]], np.float32)
    M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                   [1.9779984951, -2.4285922050, 0.4505937099],
                   [0.0259040371, 0.7827717662, -0.8086757660]], np.float32)
    lms = l @ M1.T
    return np.cbrt(lms) @ M2.T

def oklab_to_srgb(lab):
    M2i = np.array([[1.0, 0.3963377774, 0.2158037573],
                    [1.0, -0.1055613458, -0.0638541728],
                    [1.0, -0.0894841775, -1.2914855480]], np.float32)
    M1i = np.array([[4.0767416621, -3.3077115913, 0.2309699292],
                    [-1.2684380046, 2.6097574011, -0.3413193965],
                    [-0.0041960863, -0.7034186147, 1.7076147010]], np.float32)
    lms = (np.asarray(lab, np.float32) @ M2i.T) ** 3
    return lin_to_srgb(lms @ M1i.T)

def hex2rgb(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)

def load_palette(path):
    p = json.load(open(path))
    names, cols = [], []
    for k, v in p['cinematic'].items():
        names.append(k); cols.append(hex2rgb(v['hex']))
    for k, v in p['historical_bayeux_dyes'].items():
        names.append('bx_' + k); cols.append(hex2rgb(v['hex']))
    return names, np.array(cols, np.float32)

def nudge_to_palette(rgb, pal_rgb, amount=0.35, cmax=0.17, exclude=None):
    """rgb (n,3) srgb 0..1 -> moved toward nearest palette colour in OKLab, chroma capped."""
    lab = srgb_to_oklab(rgb); plab = srgb_to_oklab(pal_rgb)
    d = ((lab[:, None, :] - plab[None]) ** 2).sum(-1)
    j = d.argmin(1)
    out = lab + amount * (plab[j] - lab)
    C = np.hypot(out[:, 1], out[:, 2]); s = np.minimum(1, cmax / np.maximum(C, 1e-6))
    out[:, 1] *= s; out[:, 2] *= s
    return oklab_to_srgb(out), j

# ----------------------------------------------------------------------------- direction field
def structure_tensor(gray, sd=1.0, si=4.0):
    g = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), sd)
    gx = cv2.Scharr(g, cv2.CV_32F, 1, 0) / 32.0
    gy = cv2.Scharr(g, cv2.CV_32F, 0, 1) / 32.0
    return (cv2.GaussianBlur(gx * gx, (0, 0), si), cv2.GaussianBlur(gx * gy, (0, 0), si),
            cv2.GaussianBlur(gy * gy, (0, 0), si))

def tensor_dir(J11, J12, J22):
    tg = 0.5 * np.arctan2(2 * J12, J11 - J22)
    tmp = np.sqrt((J11 - J22) ** 2 + 4 * J12 ** 2)
    l1 = (J11 + J22 + tmp) / 2; l2 = (J11 + J22 - tmp) / 2
    coh = ((l1 - l2) / (l1 + l2 + 1e-12)) ** 2
    ts = tg + np.pi / 2          # strands run perpendicular to the luminance gradient
    return np.cos(ts).astype(np.float32), np.sin(ts).astype(np.float32), coh.astype(np.float32)

def blend_fields(fields):
    """fields: list of (J11,J12,J22,weight) -> combined tensor (weights may be arrays)."""
    a = sum(w * f[0] for f, w in fields); b = sum(w * f[1] for f, w in fields); c = sum(w * f[2] for f, w in fields)
    return a, b, c

# ----------------------------------------------------------------------------- streamline tracer (Jobard-Lefer style)
@njit(cache=True)
def _bil(a, x, y):
    H, W = a.shape
    if x < 0: x = 0.0
    if y < 0: y = 0.0
    if x > W - 1.001: x = W - 1.001
    if y > H - 1.001: y = H - 1.001
    i = int(y); j = int(x); fy = y - i; fx = x - j
    return (a[i, j] * (1 - fx) * (1 - fy) + a[i, j + 1] * fx * (1 - fy) +
            a[i + 1, j] * (1 - fx) * fy + a[i + 1, j + 1] * fx * fy)

@njit(cache=True)
def _dir(dx, dy, x, y, px, py):
    # orientation field sampled with sign alignment to (px,py) on each corner (avoids cancellation)
    H, W = dx.shape
    if x < 0: x = 0.0
    if y < 0: y = 0.0
    if x > W - 1.001: x = W - 1.001
    if y > H - 1.001: y = H - 1.001
    i = int(y); j = int(x); fy = y - i; fx = x - j
    vx = 0.0; vy = 0.0
    for (ii, jj, w) in ((i, j, (1 - fx) * (1 - fy)), (i, j + 1, fx * (1 - fy)), (i + 1, j, (1 - fx) * fy), (i + 1, j + 1, fx * fy)):
        ax = dx[ii, jj]; ay = dy[ii, jj]
        if ax * px + ay * py < 0:
            ax = -ax; ay = -ay
        vx += w * ax; vy += w * ay
    n = math.sqrt(vx * vx + vy * vy) + 1e-12
    return vx / n, vy / n

@njit(cache=True)
def _close(x, y, d2, pts, cell_n, cell_idx, cs, rad):
    gh, gw = cell_n.shape
    cx = int(x / cs); cy = int(y / cs)
    for gy in range(max(0, cy - rad), min(gh, cy + rad + 1)):
        for gx in range(max(0, cx - rad), min(gw, cx + rad + 1)):
            for k in range(cell_n[gy, gx]):
                p = cell_idx[gy, gx, k]
                ex = pts[p, 0] - x; ey = pts[p, 1] - y
                if ex * ex + ey * ey < d2:
                    return True
    return False

@njit(cache=True)
def trace_all(dx, dy, lab, seeds, h, dsep, dtest, maxlen, minlen, maxturn_cos, pts, off, cell_n, cell_idx, cs):
    H, W = lab.shape
    K = cell_idx.shape[2]
    rad = int(math.ceil(dsep / cs)) + 1
    npts = 0; nstr = 0
    bufx = np.empty(20000, np.float32); bufy = np.empty(20000, np.float32)
    fx_ = np.empty(10000, np.float32); fy_ = np.empty(10000, np.float32)
    dsep2 = dsep * dsep; dtest2 = dtest * dtest
    for s in range(seeds.shape[0]):
        x0 = seeds[s, 0]; y0 = seeds[s, 1]
        if x0 < 0 or y0 < 0 or x0 >= W - 1 or y0 >= H - 1: continue
        L0 = lab[int(y0 + 0.5), int(x0 + 0.5)]
        if L0 < 0: continue
        if _close(x0, y0, dsep2, pts, cell_n, cell_idx, cs, rad): continue
        v0x = _bil(dx, x0, y0); v0y = _bil(dy, x0, y0)
        nn = math.sqrt(v0x * v0x + v0y * v0y)
        if nn < 1e-6: continue
        v0x /= nn; v0y /= nn
        nb = 0; nf = 0
        for direction in range(2):
            sg = 1.0 if direction == 0 else -1.0
            x = x0; y = y0; px = sg * v0x; py = sg * v0y; length = 0.0
            while True:
                vx, vy = _dir(dx, dy, x, y, px, py)
                mx = x + 0.5 * h * vx; my = y + 0.5 * h * vy
                wx, wy = _dir(dx, dy, mx, my, vx, vy)
                nx = x + h * wx; ny = y + h * wy
                if nx < 0 or ny < 0 or nx >= W - 1 or ny >= H - 1: break
                if lab[int(ny + 0.5), int(nx + 0.5)] != L0: break
                if wx * px + wy * py < maxturn_cos: break
                if _close(nx, ny, dtest2, pts, cell_n, cell_idx, cs, rad): break
                length += h
                if length > maxlen * 0.5: break
                if direction == 0:
                    if nf >= 10000: break
                    fx_[nf] = nx; fy_[nf] = ny; nf += 1
                else:
                    if nb >= 10000: break
                    bufx[nb] = nx; bufy[nb] = ny; nb += 1
                x = nx; y = ny; px = wx; py = wy
        n = nb + 1 + nf
        if n * h < minlen: continue
        if npts + n >= pts.shape[0] or nstr + 2 >= off.shape[0]: break
        k = npts
        for i in range(nb - 1, -1, -1):
            pts[k, 0] = bufx[i]; pts[k, 1] = bufy[i]; k += 1
        pts[k, 0] = x0; pts[k, 1] = y0; k += 1
        for i in range(nf):
            pts[k, 0] = fx_[i]; pts[k, 1] = fy_[i]; k += 1
        for p in range(npts, k):
            gx = int(pts[p, 0] / cs); gy = int(pts[p, 1] / cs)
            c = cell_n[gy, gx]
            if c < K:
                cell_idx[gy, gx, c] = p; cell_n[gy, gx] = c + 1
        off[nstr] = npts; nstr += 1; off[nstr] = k
        npts = k
    return npts, nstr

def trace_layer(dx, dy, lab, seeds, h, dsep, dtest, maxlen, minlen, maxturn_deg=50, cs=None, prior=None):
    """Trace streamlines; returns list of (n,2) px polylines. prior: list of polylines that occupy space first."""
    H, W = lab.shape
    cs = cs or max(dsep, 1.0)
    pts = np.zeros((4_000_000, 2), np.float32); off = np.zeros(600_000, np.int64)
    gh = int(H / cs) + 2; gw = int(W / cs) + 2
    cell_n = np.zeros((gh, gw), np.int32); cell_idx = np.zeros((gh, gw, 64), np.int32)
    npts, nstr = trace_all(dx, dy, lab, seeds.astype(np.float32), np.float32(h), np.float32(dsep), np.float32(dtest),
                           np.float32(maxlen), np.float32(minlen), np.float32(math.cos(math.radians(maxturn_deg))),
                           pts, off, cell_n, cell_idx, np.float32(cs))
    return [pts[off[i]:off[i + 1]].copy() for i in range(nstr)]

def jitter_seeds(mask, spacing, rng, priority=None):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0: return np.zeros((0, 2), np.float32)
    g = np.stack([xs, ys], 1).astype(np.float32)
    # thin to ~1 seed per spacing^2 cell
    keyx = (g[:, 0] / spacing).astype(np.int64); keyy = (g[:, 1] / spacing).astype(np.int64)
    key = keyy * 100000 + keyx
    perm = rng.permutation(len(g)); g = g[perm]; key = key[perm]
    _, first = np.unique(key, return_index=True)
    s = g[first] + rng.uniform(-0.5, 0.5, (len(first), 2)).astype(np.float32)
    s = s[rng.permutation(len(s))]
    if priority is not None and len(priority):
        s = np.concatenate([priority.astype(np.float32), s])
    return s

# ----------------------------------------------------------------------------- polyline utils
def resample(poly, step):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(poly, axis=0), axis=1))]
    L = d[-1]
    if L < 1e-6: return poly[:1], d[:1]
    n = max(2, int(math.ceil(L / step)) + 1)
    s = np.linspace(0, L, n)
    out = np.stack([np.interp(s, d, poly[:, i]) for i in range(poly.shape[1])], 1)
    return out, s

def smooth_poly(p, it=2):
    p = p.copy()
    for _ in range(it):
        if len(p) > 2: p[1:-1] = 0.25 * p[:-2] + 0.5 * p[1:-1] + 0.25 * p[2:]
    return p

def tangents2(p):
    t = np.gradient(p, axis=0)
    n = np.linalg.norm(t, axis=1, keepdims=True) + 1e-9
    return t / n

def smooth_noise1d(n, scale_pts, rng):
    """smooth noise in [-1,1], correlation length ~scale_pts samples"""
    k = max(2, int(n / max(scale_pts, 1)) + 3)
    ctrl = rng.uniform(-1, 1, k)
    x = np.linspace(0, k - 1.001, n)
    i = x.astype(int); f = x - i; f = f * f * (3 - 2 * f)
    return ctrl[i] * (1 - f) + ctrl[i + 1] * f

def sample_img(img, pts_px):
    """bilinear sample (H,W,C) float image at (n,2) px points (x,y)"""
    H, W = img.shape[:2]
    x = np.clip(pts_px[:, 0], 0, W - 1.001); y = np.clip(pts_px[:, 1], 0, H - 1.001)
    i = y.astype(int); j = x.astype(int); fy = (y - i)[:, None]; fx = (x - j)[:, None]
    a = img.reshape(H, W, -1)
    return (a[i, j] * (1 - fx) * (1 - fy) + a[i, j + 1] * fx * (1 - fy) + a[i + 1, j] * (1 - fx) * fy + a[i + 1, j + 1] * fx * fy)

# ----------------------------------------------------------------------------- tube container
class Tubes:
    """Accumulates tubes. Each tube: P (n,3) mm, RW (n), RH (n), C (n,3) srgb, + per-tube mat, group, twist, sides."""
    def __init__(self):
        self.P = []; self.RW = []; self.RH = []; self.C = []; self.meta = []

    def add(self, P, RW, RH, C, mat, group=0, twist=0.75, sides=6, tag=0):
        P = np.asarray(P, np.float32)
        if len(P) < 2: return
        n = len(P)
        RW = np.broadcast_to(np.asarray(RW, np.float32), (n,)).copy()
        RH = np.broadcast_to(np.asarray(RH, np.float32), (n,)).copy()
        C = np.broadcast_to(np.asarray(C, np.float32).reshape(-1, 3), (n, 3)).copy()
        self.P.append(P); self.RW.append(RW); self.RH.append(RH); self.C.append(C)
        self.meta.append((mat, group, twist, sides, tag))

    def nverts(self):
        return sum(len(p) * m[3] for p, m in zip(self.P, self.meta))

    def save(self, path):
        lens = np.array([len(p) for p in self.P], np.int64)
        off = np.r_[0, np.cumsum(lens)]
        meta = np.array(self.meta, np.float32)
        np.savez_compressed(path, P=np.concatenate(self.P), RW=np.concatenate(self.RW), RH=np.concatenate(self.RH),
                            C=np.concatenate(self.C).astype(np.float16), off=off, meta=meta)

    def extend(self, other, dxyz=(0, 0, 0), scale=1.0):
        for P, RW, RH, C, m in zip(other.P, other.RW, other.RH, other.C, other.meta):
            self.P.append(P * scale + np.float32(dxyz)); self.RW.append(RW * scale); self.RH.append(RH * scale)
            self.C.append(C); self.meta.append(m)

# ----------------------------------------------------------------------------- stitch builders (mm space)
def tuck_profile(s, L, t):
    """0 at both ends, 1 inside, smooth ramps of length t"""
    a = np.clip(s / t, 0, 1); b = np.clip((L - s) / t, 0, 1)
    a = a * a * (3 - 2 * a); b = b * b * (3 - 2 * b)
    return a * b

def add_stitch(T, P2, base_z, rw, rh, col, mat, group, rng, twist=0.75, arch=0.06, tuck=0.45, sides=6, step=0.3, lift=0.0, tag=0, end_depth=0.9, end_depth_b=None):
    """one stitch along polyline P2 (n,2 mm) sitting on surface height base_z (callable or array)"""
    P, s = resample(P2, step)
    L = s[-1]
    if L < 0.25: return
    prof = tuck_profile(s, L, min(tuck, L * 0.45))
    bz = base_z(P) if callable(base_z) else np.broadcast_to(base_z, (len(P),))
    edb = end_depth if end_depth_b is None else end_depth_b
    ed = np.where(s < L / 2, end_depth, edb)
    z = bz + (rh * (1 + lift)) * prof - rh * ed * (1 - prof) + arch * np.sin(np.pi * s / L) * prof
    shr = np.where(ed < 0.5, 0.85, 0.65)
    rwv = rw * (shr + (1 - shr) * prof); rhv = rh * (shr - 0.05 + (1.05 - shr) * prof)
    T.add(np.c_[P, z], rwv, rhv, col, mat, group, twist, sides, tag)

def stem_stitch_line(T, poly_mm, base_z, col, mat, group, rng, L=3.2, w=1.25, rh=0.3, sides=6, wobble=0.06, tag=0):
    """stem stitch rope along a polyline: overlapping slanted stitches, advancing L/2 each"""
    P, s = resample(poly_mm, 0.1)
    tot = s[-1]
    if tot < 0.8:
        return
    tg = tangents2(P); nrm = np.c_[-tg[:, 1], tg[:, 0]]
    pos = 0.0; k = 0
    rw = w * 0.30
    while pos < tot - 0.3:
        Lk = L * rng.uniform(0.82, 1.18)
        a = pos; b = min(tot, pos + Lk)
        ia = int(a / tot * (len(P) - 1)); ib = int(b / tot * (len(P) - 1))
        if ib - ia < 2:
            break
        seg = P[ia:ib + 1].copy(); nn = nrm[ia:ib + 1]
        u = np.linspace(0, 1, len(seg))
        off = (u - 0.5) * (w * 0.42) * -1.0          # slant: start on one side, end on the other
        seg = seg + nn * off[:, None] + rng.normal(0, wobble, (1, 2))
        lift = 0.25 + 0.15 * (k % 2)
        c = np.clip(col * rng.uniform(0.93, 1.07), 0, 1)
        add_stitch(T, seg, base_z, rw, rh, c, mat, group, rng, twist=0.6, arch=0.08, tuck=0.5, sides=sides, step=0.25, lift=lift, tag=tag)
        pos += Lk * 0.5 * rng.uniform(0.9, 1.1); k += 1
