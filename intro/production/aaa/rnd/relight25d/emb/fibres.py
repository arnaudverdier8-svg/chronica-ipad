"""Wool fuzz: soft halo (texture space) + individual flyaway fibres as 3D curves, lit per frame
(Kajiya-Kay on the fibre tangent) and splatted with anti-aliasing (+ optional depth test)."""
import math
import numpy as np, cv2
from numba import njit, prange


def halo(col, m, sigma_mm=0.3, strength=0.35):
    PX = m['PX']
    wool = ((m['mat'] == 1) | (m['mat'] == 4)).astype(np.float32) * (m['cov'] > 0)
    hb = cv2.GaussianBlur(wool, (0, 0), sigma_mm * PX)
    hc = cv2.GaussianBlur(col * wool[..., None], (0, 0), sigma_mm * PX) / (hb[..., None] + 1e-4)
    a = (np.clip(hb - wool, 0, 1) * strength)[..., None]
    return col * (1 - a) + hc * 1.05 * a


def make_fibres(m, density=0.7, edge_boost=8.0, seed=0, len_mm=(0.5, 2.6), max_fibres=400000, region=None, clip_region=None,
                clip_keep=0.25):
    """returns dict: P (n, K, 3) mm (x,y,z), A (n,3) albedo, alpha (n,), root (n,2) px"""
    PX = m['PX']; H, W = m['h'].shape
    wool = ((m['mat'] == 1) | (m['mat'] == 4)) & (m['cov'] > 0)
    if region is not None: wool &= region
    sid = m['sid']
    e = np.zeros((H, W), bool)
    e[:, 1:] |= sid[:, 1:] != sid[:, :-1]; e[1:, :] |= sid[1:, :] != sid[:-1, :]
    edge = (e & wool).astype(np.float32)
    outer = cv2.morphologyEx(wool.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).astype(np.float32)
    prob = (wool * 0.25 + edge * 0.6 + outer * 2.0 * (edge_boost / 8.0)).ravel().astype(np.float64)
    if prob.sum() <= 0: return None
    area_mm2 = wool.sum() / PX / PX
    nf = int(min(max_fibres, density * area_mm2 * (1 + 0.15 * edge_boost)))
    r = np.random.default_rng(seed)
    idx = r.choice(H * W, nf, p=prob / prob.sum())
    ys, xs = np.divmod(idx, W)
    K = 10
    T = m['T']; h = m['h']; alb = m['alb']
    tx, ty = T[ys, xs, 0], T[ys, xs, 1]
    a = np.arctan2(ty, tx) + np.where(r.random(nf) < 0.5, math.pi, 0) + r.normal(0, 0.55, nf)
    L = np.clip(r.lognormal(math.log(0.85), 0.5, nf), len_mm[0], len_mm[1])
    st = L / (K - 1)
    lift = r.uniform(0.04, 0.35, nf)
    px = xs / PX + r.uniform(-0.5, 0.5, nf) / PX; py = ys / PX + r.uniform(-0.5, 0.5, nf) / PX
    pz = h[ys, xs] - 0.02
    curv = r.normal(0, 0.28, nf)
    P = np.zeros((nf, K, 3), np.float32)
    for k in range(K):
        P[:, k, 0] = px; P[:, k, 1] = py; P[:, k, 2] = pz
        a = a + curv + r.normal(0, 0.18, nf)
        px = px + np.cos(a) * st; py = py + np.sin(a) * st
        pz = pz + lift * st * (1.0 - k / K) - 0.01 * k * st
    A = alb[ys, xs] * r.uniform(0.9, 1.12, (nf, 1)).astype(np.float32)
    alpha = r.uniform(0.12, 0.38, nf).astype(np.float32)
    out = dict(P=P, A=A.astype(np.float32), alpha=alpha, root=np.stack([xs, ys], 1).astype(np.int32))
    if clip_region is not None:   # fibres overhanging the edge of a liftable slip: keep only a fraction
        tx_ = np.clip((P[:, -1, 0] * PX).astype(int), 0, W - 1); ty_ = np.clip((P[:, -1, 1] * PX).astype(int), 0, H - 1)
        keep = clip_region[ty_, tx_] | (r.random(nf) < clip_keep)
        out = {k: v[keep] for k, v in out.items()}
    return out


@njit(parallel=False, cache=True)
def _splat(img, depth, Q, Zc, C, alpha, width):
    """Q: (n,K,2) screen px; Zc: (n,K) camera depth; C: (n,K,3) lit colour; alpha (n,)."""
    H, W, _ = img.shape
    n, K, _ = Q.shape
    for i in range(n):
        a0 = alpha[i]
        for k in range(K - 1):
            x0 = Q[i, k, 0]; y0 = Q[i, k, 1]; x1 = Q[i, k + 1, 0]; y1 = Q[i, k + 1, 1]
            L = math.hypot(x1 - x0, y1 - y0)
            ns = int(L / 0.5) + 1
            for s in range(ns):
                t = (s + 0.5) / ns
                x = x0 + (x1 - x0) * t; y = y0 + (y1 - y0) * t
                z = Zc[i, k] + (Zc[i, k + 1] - Zc[i, k]) * t
                cr = C[i, k, 0] + (C[i, k + 1, 0] - C[i, k, 0]) * t
                cg = C[i, k, 1] + (C[i, k + 1, 1] - C[i, k, 1]) * t
                cb = C[i, k, 2] + (C[i, k + 1, 2] - C[i, k, 2]) * t
                xi = int(math.floor(x - 0.5)); yi = int(math.floor(y - 0.5))
                fx = x - 0.5 - xi; fy = y - 0.5 - yi
                # fade toward the tip
                tip = 1.0 - (k + t) / (K - 1) * 0.6
                aa = a0 * tip * min(1.0, L / 0.5 / ns * 1.0) * width
                for dy in range(2):
                    for dx in range(2):
                        X = xi + dx; Y = yi + dy
                        if X < 0 or Y < 0 or X >= W or Y >= H: continue
                        wgt = (fx if dx else 1 - fx) * (fy if dy else 1 - fy)
                        if depth[Y, X] < z - 0.3: continue  # hidden behind nearer surface (mm)
                        a = aa * wgt
                        if a > 1: a = 1.0
                        img[Y, X, 0] = img[Y, X, 0] * (1 - a) + cr * a
                        img[Y, X, 1] = img[Y, X, 1] * (1 - a) + cg * a
                        img[Y, X, 2] = img[Y, X, 2] * (1 - a) + cb * a


@njit(parallel=True, cache=True)
def _light_fibres(P, A, vis_root, L, kc, fc, V, out):
    n, K, _ = P.shape
    for i in prange(n):
        for k in range(K):
            k0 = k if k < K - 1 else K - 2
            tx = P[i, k0 + 1, 0] - P[i, k0, 0]; ty = P[i, k0 + 1, 1] - P[i, k0, 1]; tz = P[i, k0 + 1, 2] - P[i, k0, 2]
            tl = math.sqrt(tx * tx + ty * ty + tz * tz) + 1e-9
            tx /= tl; ty /= tl; tz /= tl
            tdl = tx * L[0] + ty * L[1] + tz * L[2]
            sinl = math.sqrt(max(0.0, 1 - tdl * tdl))
            hx = L[0] + V[0]; hy = L[1] + V[1]; hz = L[2] + V[2]
            hl = math.sqrt(hx * hx + hy * hy + hz * hz)
            tdh = (tx * hx + ty * hy + tz * hz) / hl
            sth = math.sqrt(max(0.0, 1 - tdh * tdh))
            # fibres higher up escape the surface shadow
            v = vis_root[i] + (1 - vis_root[i]) * min(1.0, k / 4.0) * 0.8
            for c in range(3):
                out[i, k, c] = A[i, c] * (fc[c] + kc[c] * v * (0.65 * sinl + 0.15)) + kc[c] * v * 0.10 * sth ** 12
    return out


def render_fibres(img, fib, L, key, fill, vis_tex, project, V=(0.0, 0.0, 1.0), depth=None, width=1.0):
    """project(P(n,K,3) mm) -> (Q (n,K,2) screen px, Zc (n,K) depth in mm). Modifies img in place."""
    if fib is None: return img
    P = fib['P']
    vr = vis_tex[fib['root'][:, 1], fib['root'][:, 0]].astype(np.float32)
    C = np.zeros(P.shape, np.float32)
    _light_fibres(P, fib['A'], vr, np.asarray(L, np.float32), np.asarray(key, np.float32), np.asarray(fill, np.float32),
                  np.asarray(V, np.float32), C)
    Q, Zc = project(P)
    if depth is None:
        depth = np.full(img.shape[:2], 1e9, np.float32)
    _splat(img, depth, Q.astype(np.float32), Zc.astype(np.float32), C, fib['alpha'], float(width))
    return img
