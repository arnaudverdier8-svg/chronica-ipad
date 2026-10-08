"""Vector helpers for the kit (all coordinates in sheet mm unless the name says px).  y points down."""
import math
import numpy as np, cv2


def catmull(pts, n_per=12, closed=False):
    """Catmull-Rom spline through pts (k,2)."""
    P = np.asarray(pts, np.float64)
    if len(P) < 3:
        return P.astype(np.float32)
    if closed:
        Q = np.vstack([P[-1:], P, P[:2]])
    else:
        Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    t = np.linspace(0, 1, n_per, endpoint=False)[:, None]
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(Q[-2][None])
    return np.vstack(out).astype(np.float32)


def resample(p, step):
    p = np.asarray(p, np.float64)
    seg = np.hypot(*np.diff(p, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    if s[-1] < 1e-9:
        return p[:1].astype(np.float32)
    n = max(2, int(math.ceil(s[-1] / step)) + 1)
    ss = np.linspace(0, s[-1], n)
    return np.stack([np.interp(ss, s, p[:, 0]), np.interp(ss, s, p[:, 1])], 1).astype(np.float32)


def arclen(p):
    p = np.asarray(p, np.float64)
    return np.concatenate([[0], np.cumsum(np.hypot(*np.diff(p, axis=0).T))])


def tangents(p):
    p = np.asarray(p, np.float64)
    d = np.gradient(p, axis=0)
    d /= (np.linalg.norm(d, axis=1, keepdims=True) + 1e-12)
    return d


def normals(p):
    t = tangents(p)
    return np.stack([-t[:, 1], t[:, 0]], 1)        # for a rightward curve: (0, 1) = down


def offset(p, d):
    """offset polyline by d (scalar or per-point array) along normals (positive = below a rightward curve)."""
    p = np.asarray(p, np.float64)
    d = np.broadcast_to(np.asarray(d, np.float64), (len(p),))
    return (p + normals(p) * d[:, None]).astype(np.float32)


def band(p, d0, d1):
    """closed polygon between offsets d0 and d1 of polyline p."""
    a = offset(p, d0); b = offset(p, d1)
    return np.vstack([a, b[::-1]]).astype(np.float32)


def noise1(n, scale_pts, seed, octaves=2):
    """smooth 1D noise ~[-1, 1] over n samples with feature size scale_pts samples."""
    r = np.random.default_rng(seed)
    out = np.zeros(n, np.float64); amp = 1.0; tot = 0.0; sc = scale_pts
    for _ in range(octaves):
        g = r.uniform(-1, 1, int(n / max(sc, 1)) + 4)
        xs = np.arange(n) / max(sc, 1) + r.uniform(0, 1)
        i = np.floor(xs).astype(int); f = xs - i; f = f * f * (3 - 2 * f)
        out += amp * (g[i] * (1 - f) + g[i + 1] * f)
        tot += amp; amp *= 0.5; sc *= 0.5
    return (out / tot).astype(np.float32)


def wobble(p, amp_mm, scale_mm, seed, step=None):
    """hand-drawn wander: offset along the normal by smooth noise (amp_mm, feature scale_mm)."""
    p = np.asarray(p, np.float32)
    s = arclen(p)
    if s[-1] < 1e-6:
        return p
    n = noise1(len(p), max(2.0, scale_mm / max(s[-1] / max(len(p) - 1, 1), 1e-3)), seed)
    return offset(p, amp_mm * n)


def bump(x, xc, half_w, height, power=1.6, skew=0.0):
    """smooth hill profile: height at xc, 0 at xc +/- half_w (cos^power), optional skew (-1..1)."""
    u = (np.asarray(x, np.float64) - xc) / half_w
    u = np.where(u < 0, u * (1 + skew), u * (1 - skew))
    v = np.where(np.abs(u) < 1, np.cos(0.5 * math.pi * np.clip(u, -1, 1)) ** power, 0.0)
    return height * v


def to_px(p_mm, PX, origin_px=(0, 0)):
    return (np.asarray(p_mm, np.float32) * PX - np.asarray(origin_px, np.float32)).astype(np.float32)


def fill_poly(shape, polys_px, val=1, shift=4):
    m = np.zeros(shape, np.uint8)
    ps = [np.round(np.asarray(p, np.float64) * (1 << shift)).astype(np.int32) for p in polys_px if len(p) >= 3]
    if ps:
        cv2.fillPoly(m, ps, int(val), cv2.LINE_8, shift=shift)
    return m


def path_field(shape, paths_px, smooth_px=3.0):
    """doubled-angle thread field (c2, s2) running ALONG the nearest of the given polylines (px)."""
    H, W = shape
    zero = np.ones((H, W), np.uint8)
    ang = np.zeros((H, W), np.float32)
    for p in paths_px:
        p = np.asarray(p, np.float32)
        if len(p) < 2:
            continue
        q = resample(p, 0.7)
        t = tangents(q)
        a = np.arctan2(t[:, 1], t[:, 0]).astype(np.float32)
        xi = np.round(q[:, 0]).astype(int); yi = np.round(q[:, 1]).astype(int)
        ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H)
        zero[yi[ok], xi[ok]] = 0
        ang[yi[ok], xi[ok]] = a[ok]
    if zero.min() > 0:
        return np.ones((H, W), np.float32), np.zeros((H, W), np.float32)
    _, lab = cv2.distanceTransformWithLabels(zero, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    zy, zx = np.nonzero(zero == 0)
    table = np.concatenate([[0.0], ang[zy, zx]]).astype(np.float32)
    a = table[lab]
    c2, s2 = np.cos(2 * a).astype(np.float32), np.sin(2 * a).astype(np.float32)
    if smooth_px > 0:
        c2 = cv2.GaussianBlur(c2, (0, 0), smooth_px); s2 = cv2.GaussianBlur(s2, (0, 0), smooth_px)
    return c2, s2


def const_field(shape, angle_deg):
    a = math.radians(angle_deg) * 2
    return np.full(shape, math.cos(a), np.float32), np.full(shape, math.sin(a), np.float32)


def clip_path(p_px, blocked, min_len_px=6):
    """split a px polyline into runs whose points are not in the boolean mask `blocked` (canvas px)."""
    p = np.asarray(p_px, np.float32)
    H, W = blocked.shape
    xi = np.clip(np.round(p[:, 0]).astype(int), 0, W - 1); yi = np.clip(np.round(p[:, 1]).astype(int), 0, H - 1)
    inside = (p[:, 0] >= 0) & (p[:, 0] < W) & (p[:, 1] >= 0) & (p[:, 1] < H)
    ok = inside & ~blocked[yi, xi]
    runs, cur = [], []
    for k in range(len(p)):
        if ok[k]:
            cur.append(p[k])
        else:
            if len(cur) >= 2:
                runs.append(np.array(cur, np.float32))
            cur = []
    if len(cur) >= 2:
        runs.append(np.array(cur, np.float32))
    return [r for r in runs if arclen(r)[-1] >= min_len_px]
