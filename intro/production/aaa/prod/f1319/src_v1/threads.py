"""Fringe, loose weft threads and unravelled border strands: generated along the frayed cloth boundary in strip coordinates,
mapped to the table, lit with the same light model / physical pool as the relight, and composited in screen space (2x supersampled
AA polylines, premultiplied-over) with soft contact shadows."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from s18common import *
from geometry import *
from chron.color import hex_lin, light_colour
from chron import shade as _shade
from finish_strip import noise1d


def _path(r, u, v0, sgn, L, head, wefty, a, curl_s):
    n = max(6, int(L / 1.5)); ds = L / n
    ang = head; ou = 0.0
    curl = r.normal(0, curl_s)
    uu, vv = u, v0
    pts = []; z = []
    for i in range(n):
        ou = 0.92 * ou + r.normal(0, 0.11 if wefty else 0.07)
        ang += ou * 0.4 + curl * (1 + 4 * (i / n) ** 3)
        uu += math.sin(ang) * ds
        vv += math.cos(ang) * ds * sgn
        pts.append((uu, vv)); z.append(0.25 + 1.0 * math.exp(-i * ds / 5.0))
    return pts, z


def gen_threads(S, info, PX, Ls=4100.0, seed=17, u_range=(-60.0, 3700.0), dens_scale=1.0):
    r = np.random.default_rng(seed)
    vt, vb, bt, bb = info['vt'], info['vb'], info['bt'], info['bb']
    W = len(vt)
    out = []
    albS = S['alb']
    Hs = albS.shape[0]

    def sample_col(u, v):
        x = int(np.clip(u * PX, 0, W - 1)); y = int(np.clip(v * PX, 0, Hs - 1))
        c = albS[y, x].copy()
        lum = float(c @ np.array([0.2126, 0.7152, 0.0722], np.float32))
        chroma = float(c.max() - c.min())
        k = 0.45 if chroma < 0.12 else 0.12            # raw linen yarn is paler / greyer than the aged surface; dyed wool keeps its colour
        return (c * (1 - k) + lum * k) * 0.82

    def emit(pts, z, u, v0, sgn, col, w, op, kind):
        P = np.array([(u, v0 + sgn * -0.4)] + pts, np.float32)
        Xw, Yw = strip_to_world(P[:, 0], P[:, 1])
        out.append(dict(P=np.stack([Xw, Yw], 1).astype(np.float32), w=w, col=col, z=np.array([1.3] + z, np.float32), op=op, kind=kind))

    for edge in ('top', 'bot'):
        sgn = -1.0 if edge == 'top' else 1.0
        bnd = vt if edge == 'top' else vb
        act = bt if edge == 'top' else bb
        u = max(u_range[0], 0.0) + 10
        while u < u_range[1]:
            ui = int(np.clip(u * PX, 0, W - 1))
            a = float(np.clip(act[ui] / 22.0, 0, 1))
            dens = (0.030 + 0.40 * a ** 1.3) * dens_scale
            u += r.exponential(1.0 / dens)
            ui = int(np.clip(u * PX, 0, W - 1))
            v0 = float(bnd[ui])
            col0 = sample_col(u, v0 - sgn * 3.5)
            chroma = float(col0.max() - col0.min())
            if chroma > 0.055 and a > 0.25 and r.random() < 0.55:        # a wool motif (border beast / flower) coming apart: long coloured strands
                for k in range(1 + r.poisson(1.3)):
                    L = float(np.clip(r.lognormal(math.log(22.0), 0.6), 6.0, 90.0))
                    head = r.normal(0, 0.9)
                    pts, z = _path(r, u + r.normal(0, 1.2), v0, sgn, L, head, True, a, 0.045)
                    emit(pts, z, u, v0, sgn, col0 * r.uniform(0.80, 1.15), r.uniform(0.7, 1.1), float(r.uniform(0.55, 0.9)), 'strand')
            kind = r.random()
            if kind < 0.72:      # fringe clump: a few cut warp ends / pulled bundles splaying from one point
                nc = 1 + r.poisson(0.9 + 2.2 * a)
                head0 = r.normal(0, 0.60)
                Lc = float(np.clip(r.lognormal(math.log(6.5 + 7 * a), 0.55), 2.0, 36.0))
                for k in range(nc):
                    L = float(np.clip(Lc * r.uniform(0.55, 1.35), 1.5, 40.0))
                    head = head0 + r.normal(0, 0.38)
                    pts, z = _path(r, u + r.normal(0, 0.9), v0, sgn, L, head, False, a, 0.020)
                    emit(pts, z, u, v0, sgn, col0 * r.uniform(0.50, 0.98), r.uniform(0.55, 1.0), float(r.uniform(0.35, 0.75)), 'fringe')
            else:
                if kind < 0.93:
                    L = float(r.uniform(28, 170)); w = r.uniform(0.6, 1.0); head = r.choice([-1, 1]) * (math.pi / 2 - r.uniform(0.15, 0.7))
                else:
                    L = float(r.uniform(70, 230)); w = r.uniform(0.7, 1.1); head = r.choice([-1, 1]) * (math.pi / 2 - r.uniform(0.3, 1.1))
                pts, z = _path(r, u, v0, sgn, L, head, True, a, 0.050)
                emit(pts, z, u, v0, sgn, col0 * r.uniform(0.60, 1.0), w, float(r.uniform(0.5, 0.9)), 'weft')
    return out


def irradiance_factors(light, pool_fn):
    """returns f(x, y, tx, ty) -> rgb irradiance factor for a thread lying flat with world tangent (tx, ty) (Kajiya-Kay diffuse)."""
    L = _shade.light_vec(light['az'], light['el'])
    R = _shade.light_vec(light['rim_az'], light['rim_el'])
    Kc = np.asarray(light['key'], np.float32) * light['key_i']
    Rc = np.asarray(light['key'], np.float32) * light['rim_i']
    Fc = np.asarray(light['fill'], np.float32) * light['fill_i']

    def f(x, y, tx, ty):
        E = pool_fn(x, y)
        kk = math.sqrt(max(0.0, 1 - (tx * L[0] + ty * L[1]) ** 2))
        kr = math.sqrt(max(0.0, 1 - (tx * R[0] + ty * R[1]) ** 2))
        return E * (Kc * (0.25 + 0.6 * kk) + Rc * (0.35 + 0.9 * kr) + Fc * 0.85)
    return f


def draw_threads(base_lin, threads, light, pool_fn, s=S_SCREEN, SS=2, shadow_k=0.45, scale_w=1.0, sheen=0.06, occlude=None):
    H, W = base_lin.shape[:2]
    h2, w2 = H * SS, W * SS
    colc = np.zeros((h2, w2, 3), np.uint8); alc = np.zeros((h2, w2), np.uint8); shc = np.zeros((h2, w2), np.uint8)
    f = irradiance_factors(light, pool_fn)
    L = _shade.light_vec(light['az'], light['el'])
    lxy = L[:2] / (np.linalg.norm(L[:2]) + 1e-6)
    tan_el = L[2] / (np.linalg.norm(L[:2]) + 1e-6)
    for th in threads:
        P = th['P']
        X = (P[:, 0] + WIN_W / 2) * s * SS; Y = (P[:, 1] + WIN_H / 2) * s * SS
        if X.max() < -10 or X.min() > w2 + 10 or Y.max() < -10 or Y.min() > h2 + 10: continue
        pts = np.stack([X, Y], 1)
        mid = len(P) // 2
        d = P[min(mid + 1, len(P) - 1)] - P[max(mid - 1, 0)]
        dn = d / (np.linalg.norm(d) + 1e-6)
        irr = f(float(P[mid, 0]), float(P[mid, 1]), float(dn[0]), float(dn[1]))
        lit = th['col'] * irr * 0.72            # fibres sit in the cloth's own AO / mutual shadowing
        lit = lit + sheen * irr.mean() * np.array([1.0, 0.85, 0.65], np.float32) * (0.4 + 0.6 * abs(dn[1]))
        op = th['op']
        thick = max(1, int(round(th['w'] * s * SS * scale_w)))
        enc = np.clip(np.sqrt(np.clip(lit * op, 0, 1)) * 255, 0, 255).astype(np.uint8)
        cv2.polylines(colc, [np.round(pts * 16).astype(np.int32)], False, tuple(int(c) for c in enc), thick, cv2.LINE_AA, shift=4)
        cv2.polylines(alc, [np.round(pts * 16).astype(np.int32)], False, int(255 * op), thick, cv2.LINE_AA, shift=4)
        # contact shadow: thread lifts ~z mm; shadow offset away from the light
        zz = float(np.mean(th['z'][1:]))
        off = -lxy * (zz / max(tan_el, 0.1)) * s * SS
        sp = np.round((pts + off[None, :]) * 16).astype(np.int32)
        cv2.polylines(shc, [sp], False, int(255 * min(1.0, op * 0.9)), thick + 1, cv2.LINE_AA, shift=4)
    colc = cv2.resize(colc, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    alc = cv2.resize(alc, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    shc = cv2.resize(shc, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    shc = cv2.GaussianBlur(shc, (0, 0), 0.8)
    col_lin = colc ** 2
    if occlude is not None:
        vis_t = (1 - np.clip(occlude, 0, 1))
        alc = alc * vis_t; col_lin = col_lin * vis_t[..., None]; shc = shc * vis_t
    out = base_lin * (1 - shadow_k * shc[..., None]) * (1 - alc[..., None]) + col_lin
    return out, dict(alpha=alc)


def gen_stray(info, PX, n=150, seed=29, u_range=(60.0, 3650.0)):
    """lint and fallen fibres lying on the walnut near the cloth (not attached to it)."""
    r = np.random.default_rng(seed)
    out = []
    bt, bb = info['bt'], info['bb']
    W = len(bt)
    while len(out) < n:
        u = r.uniform(*u_range)
        ui = int(np.clip(u * PX, 0, W - 1))
        top = r.random() < 0.55
        a = float(np.clip((bt[ui] if top else bb[ui]) / 22.0, 0, 1))
        if r.random() > 0.25 + 0.75 * a: continue
        off = r.uniform(14, 190) * (0.5 + 0.8 * (1 - a))
        v = -off if top else 400 + off
        L = float(np.clip(r.lognormal(math.log(14.0), 0.6), 4.0, 70.0))
        pts, z = _path(r, u, v, 1.0, L, r.uniform(-3.1, 3.1), True, 0.5, 0.06)
        P = np.array([(u, v)] + pts, np.float32)
        Xw, Yw = strip_to_world(P[:, 0], P[:, 1])
        col = np.array([0.30, 0.22, 0.13], np.float32) * r.uniform(0.55, 1.0)
        out.append(dict(P=np.stack([Xw, Yw], 1).astype(np.float32), w=r.uniform(0.6, 1.0), col=col, z=np.full(len(P), 0.3, np.float32),
                        op=float(r.uniform(0.35, 0.75)), kind='stray'))
    return out
