"""Wool fuzz with the gate-G3 calibration (pipeline 4.4):
- halo 0.3 mm sigma, strength 35 % x coverage (fills cov 1.0; stem outlines 0.5 -> ~17 %; cords 0.3 -> ~10 %);
- fibre density x coverage (fills 1.0, stem 0.5, cords 0.3, metal/silk 0) and NO sid-edge boost on outlines (no chenille);
- fibre colour = parent albedo x U(0.95, 1.05) (tinted toward the parent thread, never whitened);
- alpha x smoothstep(0.03, 0.15, lum(albedo under the fibre)) and a contrast term: pale fibres over dark fills fade;
- self-shadow: radiance x (0.55 + 0.45 vis_root) x exp(-2.5 max(0, h_surface(tip) - z_tip));
- slip clip: fibres whose tip leaves a slip alpha are dropped (clip_keep = 0).
Also: thick lit curves for loose ends / unpicked strands (Kajiya-Kay, AA capsules)."""
import math
import numpy as np, cv2
from numba import njit, prange
from .color import LUMA
from .util import sstep


def halo(col, m, sigma_mm=0.3, strength=0.35):
    """soft wool halo in texture space; strength scales with coverage (cov map)."""
    PX = m['PX']
    mt = m['mat']
    cov = np.clip(m['cov'], 0, 1).astype(np.float32) * (((mt == 1) | (mt == 4) | (mt == 5)).astype(np.float32))
    sig = max(0.5, sigma_mm * PX)
    hb = cv2.GaussianBlur(cov, (0, 0), sig)
    hc = cv2.GaussianBlur(col * cov[..., None], (0, 0), sig) / (hb[..., None] + 1e-4)
    a = (np.clip(hb - cov, 0, 1) * strength)[..., None]
    return col * (1 - a) + hc * 1.0 * a


def make_fibres(m, density=0.7, edge_boost=3.0, seed=0, len_mm=(0.5, 2.4), max_fibres=600000, region=None, clip_region=None,
                clip_keep=0.0, origin_px=(0, 0)):
    """calibrated fibre set.  returns dict P (n,K,3) mm in the maps' own frame (+origin_px/PX), A (n,3), alpha (n,), root (n,2) px."""
    PX = m['PX']; H, W = m['h'].shape
    mt = m['mat']
    covm = np.clip(m['cov'], 0, 1).astype(np.float32)
    wool = ((mt == 1) | (mt == 4) | (mt == 5)) & (covm > 0)
    if region is not None: wool &= region
    if not wool.any(): return None
    woolf = wool.astype(np.float32)
    # outer silhouette of the wool mass (not every stitch boundary -> no chenille outlines)
    outer = cv2.morphologyEx(wool.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).astype(np.float32)
    prob = (woolf * 0.6 + outer * 0.25 * edge_boost) * covm ** 1.5
    prob = prob.ravel().astype(np.float64)
    if prob.sum() <= 0: return None
    area_mm2 = (woolf * covm).sum() / PX / PX
    nf = int(min(max_fibres, density * area_mm2 * 1.3))
    if nf < 1: return None
    r = np.random.default_rng(seed)
    idx = r.choice(H * W, nf, p=prob / prob.sum())
    ys, xs = np.divmod(idx, W)
    K = 10
    T = m['T']; h = m['h']; alb = m['alb']
    tx, ty = T[ys, xs, 0], T[ys, xs, 1]
    a = np.arctan2(ty, tx) + np.where(r.random(nf) < 0.5, math.pi, 0) + r.normal(0, 0.55, nf)
    L = np.clip(r.lognormal(math.log(0.8), 0.5, nf), len_mm[0], len_mm[1])
    st = L / (K - 1)
    lift = r.uniform(0.04, 0.30, nf)
    px = (xs + origin_px[0]) / PX + r.uniform(-0.5, 0.5, nf) / PX; py = (ys + origin_px[1]) / PX + r.uniform(-0.5, 0.5, nf) / PX
    pz = h[ys, xs] - 0.02
    curv = r.normal(0, 0.28, nf)
    P = np.zeros((nf, K, 3), np.float32)
    for k in range(K):
        P[:, k, 0] = px; P[:, k, 1] = py; P[:, k, 2] = pz
        a = a + curv + r.normal(0, 0.18, nf)
        px = px + np.cos(a) * st; py = py + np.sin(a) * st
        pz = pz + lift * st * (1.0 - k / K) - 0.01 * k * st
    A = (alb[ys, xs] * r.uniform(0.95, 1.05, (nf, 1))).astype(np.float32)
    alpha = r.uniform(0.15, 0.40, nf).astype(np.float32)
    # dark-fill attenuation + contrast term, evaluated under the fibre tip and middle
    tipx = np.clip((P[:, -1, 0] * PX - origin_px[0]).astype(int), 0, W - 1); tipy = np.clip((P[:, -1, 1] * PX - origin_px[1]).astype(int), 0, H - 1)
    midx = np.clip((P[:, K // 2, 0] * PX - origin_px[0]).astype(int), 0, W - 1); midy = np.clip((P[:, K // 2, 1] * PX - origin_px[1]).astype(int), 0, H - 1)
    lu = np.minimum((alb[tipy, tipx] * LUMA).sum(-1), (alb[midy, midx] * LUMA).sum(-1))
    lf = (A * LUMA).sum(-1)
    alpha *= sstep(0.03, 0.15, lu) * (1 - 0.7 * sstep(0.08, 0.35, lf - lu))
    # cheap occlusion: tip dipping under the neighbouring strands
    occ = np.exp(-2.5 * np.maximum(0, h[tipy, tipx] - P[:, -1, 2]))
    out = dict(P=P, A=A, alpha=alpha.astype(np.float32), root=np.stack([xs, ys], 1).astype(np.int32), occ=occ.astype(np.float32))
    if clip_region is not None:
        keep = clip_region[tipy, tipx] | (r.random(nf) < clip_keep)
        out = {k: v[keep] for k, v in out.items()}
    keep = out['alpha'] > 0.01
    return {k: v[keep] for k, v in out.items()}


@njit(parallel=False, cache=True)
def _splat(img, depth, Q, Zc, C, alpha, width):
    H, W, _ = img.shape
    n, K, _ = Q.shape
    for i in range(n):
        a0 = alpha[i]
        for k in range(K - 1):
            x0 = Q[i, k, 0]; y0 = Q[i, k, 1]; x1 = Q[i, k + 1, 0]; y1 = Q[i, k + 1, 1]
            L = math.hypot(x1 - x0, y1 - y0)
            if L > 200: continue
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
                tip = 1.0 - (k + t) / (K - 1) * 0.6
                aa = a0 * tip * min(1.0, L / 0.5 / ns) * width
                for dy in range(2):
                    for dx in range(2):
                        X = xi + dx; Y = yi + dy
                        if X < 0 or Y < 0 or X >= W or Y >= H: continue
                        wgt = (fx if dx else 1 - fx) * (fy if dy else 1 - fy)
                        if depth[Y, X] < z - 0.3: continue
                        a = aa * wgt
                        if a > 1: a = 1.0
                        img[Y, X, 0] = img[Y, X, 0] * (1 - a) + cr * a
                        img[Y, X, 1] = img[Y, X, 1] * (1 - a) + cg * a
                        img[Y, X, 2] = img[Y, X, 2] * (1 - a) + cb * a


@njit(parallel=True, cache=True)
def _light_fibres(P, A, vis_root, occ, L, kc, fc, V, out):
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
            v = vis_root[i] + (1 - vis_root[i]) * min(1.0, k / 4.0) * 0.8
            ss = (0.55 + 0.45 * vis_root[i]) * (1.0 + (occ[i] - 1.0) * k / (K - 1))
            for c in range(3):
                out[i, k, c] = ss * (A[i, c] * (fc[c] + kc[c] * v * (0.65 * sinl + 0.15)) + kc[c] * v * 0.08 * sth ** 12)
    return out


def render_fibres(img, fib, L, key, fill, vis_tex, project, V=(0.0, 0.0, 1.0), depth=None, width=1.0, root_offset=(0, 0)):
    """project(P(n,K,3) mm) -> (Q (n,K,2) screen px, Zc (n,K) depth mm). vis_tex: key visibility in the maps' frame
    (root px - root_offset). Modifies img in place."""
    if fib is None or len(fib['P']) == 0: return img
    P = fib['P']
    rx = np.clip(fib['root'][:, 0] - root_offset[0], 0, vis_tex.shape[1] - 1)
    ry = np.clip(fib['root'][:, 1] - root_offset[1], 0, vis_tex.shape[0] - 1)
    vr = vis_tex[ry, rx].astype(np.float32)
    C = np.zeros(P.shape, np.float32)
    _light_fibres(P, fib['A'], vr, fib.get('occ', np.ones(len(P), np.float32)), np.asarray(L, np.float32),
                  np.asarray(key, np.float32), np.asarray(fill, np.float32), np.asarray(V, np.float32), C)
    Q, Zc = project(P)
    if depth is None:
        depth = np.full(img.shape[:2], 1e9, np.float32)
    _splat(img, depth, Q.astype(np.float32), Zc.astype(np.float32), C, fib['alpha'], float(width))
    return img


# ---------------------------------------------------------------- thick lit curves (loose ends, tethers)
@njit(cache=True)
def splat_thick(img, Q, R, C, A, shadow_off, shadow_a, shadow_blur):
    """Q: (n,K,2) screen px; R: (n,K) radius px; C: (n,K,3) lit colour; A: (n,K) alpha.
    A soft contact/cast shadow is first drawn offset by shadow_off (dx, dy px) with alpha shadow_a."""
    H, W, _ = img.shape
    n, K, _ = Q.shape
    for pas in range(2):
        for i in range(n):
            for k in range(K - 1):
                ax = Q[i, k, 0]; ay = Q[i, k, 1]; bx = Q[i, k + 1, 0]; by = Q[i, k + 1, 1]
                if pas == 0:
                    ax += shadow_off[i, k, 0]; ay += shadow_off[i, k, 1]; bx += shadow_off[i, k + 1, 0]; by += shadow_off[i, k + 1, 1]
                r0 = R[i, k]; r1 = R[i, k + 1]
                rr = max(r0, r1) + (shadow_blur if pas == 0 else 0.0) + 1.5
                x0 = max(0, int(min(ax, bx) - rr)); x1 = min(W, int(max(ax, bx) + rr + 1))
                y0 = max(0, int(min(ay, by) - rr)); y1 = min(H, int(max(ay, by) + rr + 1))
                abx = bx - ax; aby = by - ay; ll = abx * abx + aby * aby + 1e-9
                for yy in range(y0, y1):
                    for xx in range(x0, x1):
                        px = xx + 0.5 - ax; py = yy + 0.5 - ay
                        t = (px * abx + py * aby) / ll
                        if t < 0: t = 0.0
                        if t > 1: t = 1.0
                        dx = px - t * abx; dy = py - t * aby
                        d = math.sqrt(dx * dx + dy * dy)
                        rad = r0 + (r1 - r0) * t
                        if pas == 0:
                            sb = shadow_blur + 0.5
                            cov = 1.0 - (d - rad + sb) / (2 * sb)
                            if cov <= 0: continue
                            if cov > 1: cov = 1.0
                            a = cov * shadow_a[i, k]
                            img[yy, xx, 0] *= 1 - a; img[yy, xx, 1] *= 1 - a; img[yy, xx, 2] *= 1 - a
                        else:
                            cov = rad + 0.5 - d
                            if cov <= 0: continue
                            if cov > 1: cov = 1.0
                            a = cov * (A[i, k] + (A[i, k + 1] - A[i, k]) * t)
                            q = d / (rad + 1e-6)
                            shade = 0.75 + 0.25 * math.sqrt(max(0.0, 1 - q * q))
                            for c in range(3):
                                col = (C[i, k, c] + (C[i, k + 1, c] - C[i, k, c]) * t) * shade
                                img[yy, xx, c] = img[yy, xx, c] * (1 - a) + col * a


def light_curves(P, A, L, key, fill, V=(0.0, 0.0, 1.0), vis=None):
    """Kajiya-Kay colour for 3D curves P (n,K,3) mm with albedo A (n,3) -> (n,K,3)."""
    n, K, _ = P.shape
    C = np.zeros(P.shape, np.float32)
    vr = np.ones(n, np.float32) if vis is None else np.asarray(vis, np.float32)
    _light_fibres(P.astype(np.float32), A.astype(np.float32), vr, np.ones(n, np.float32), np.asarray(L, np.float32),
                  np.asarray(key, np.float32), np.asarray(fill, np.float32), np.asarray(V, np.float32), C)
    return C
