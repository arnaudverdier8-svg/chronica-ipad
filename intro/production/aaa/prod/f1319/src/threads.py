"""Fringe, loose weft threads and unravelled border strands (v2): generated along the frayed cloth boundary in strip coordinates, mapped to
the table, lit with the same light model / physical pool as the relight, composited in screen space (2x supersampled AA lines,
premultiplied-over) with soft contact shadows.
v2 vs v1: tapered strands with per-chunk tone (slubs), undyed yarn is a grey-tan (not straw-yellow), gentle low-curvature lies (no ring-ended
curls), 1/3 fewer clumps, wider key strands (1.1-1.9 mm), blackened stubs inside the burn-through hole, stronger contact shadows."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from s18common import *
from geometry import *
from chron.color import hex_lin, light_colour
from chron import shade as _shade
from finish_strip import noise1d

YARN = hex_lin('#8E8470')       # raw linen yarn, grey-tan


def _path(r, u, v0, sgn, L, head, k_amp, wl, k0_sd, step=1.2):
    """gentle low-curvature lie: curvature = k0 + k_amp sin(2 pi s / wl + phi); total turning is clamped so nothing curls into a ring."""
    n = max(6, int(L / step)); ds = L / n
    ang = head
    ph = r.uniform(0, 2 * math.pi); k0 = r.normal(0, k0_sd)
    uu, vv = u, v0
    pts = []; z = []; turn = 0.0
    for i in range(n):
        s = i * ds
        k = k0 + k_amp * math.sin(2 * math.pi * s / wl + ph)
        dth = k * ds
        if abs(turn + dth) > 1.25:
            dth = 0.0
        turn += dth; ang += dth
        uu += math.sin(ang) * ds
        vv += math.cos(ang) * ds * sgn
        pts.append((uu, vv)); z.append(0.25 + 1.0 * math.exp(-s / 5.0))
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
        return c, chroma, lum

    def emit(pts, z, u, v0, sgn, col, w, op, kind, taper=0.45, jitter=0.10):
        P = np.array([(u, v0 + sgn * -0.4)] + pts, np.float32)
        Xw, Yw = strip_to_world(P[:, 0], P[:, 1])
        out.append(dict(P=np.stack([Xw, Yw], 1).astype(np.float32), w=w, col=col, z=np.array([1.3] + z, np.float32), op=op, kind=kind,
                        taper=taper, jit=jitter, seed=int(r.integers(1 << 30))))

    for edge in ('top', 'bot'):
        sgn = -1.0 if edge == 'top' else 1.0
        bnd = vt if edge == 'top' else vb
        act = bt if edge == 'top' else bb
        u = max(u_range[0], 0.0) + 10
        while u < u_range[1]:
            ui = int(np.clip(u * PX, 0, W - 1))
            a = float(np.clip(act[ui] / 22.0, 0, 1))
            dens = (0.016 + 0.21 * a ** 1.3) * dens_scale          # v1: .030 + .40 a^1.3 (clumps cut by about a third)
            u += r.exponential(1.0 / dens)
            ui = int(np.clip(u * PX, 0, W - 1))
            v0 = float(bnd[ui])
            c0, chroma, lum = sample_col(u, v0 - sgn * 3.5)
            dyed = chroma > 0.055 and a > 0.25
            if dyed and r.random() < 0.60:        # a wool motif (border beast / flower) coming apart: long coloured strands
                for k in range(1 + r.poisson(1.4)):
                    L = float(np.clip(r.lognormal(math.log(24.0), 0.6), 7.0, 95.0))
                    head = r.normal(0, 0.9)
                    pts, z = _path(r, u + r.normal(0, 1.2), v0, sgn, L, head, 0.010, r.uniform(25, 70), 0.006)
                    emit(pts, z, u, v0, sgn, c0 * r.uniform(0.85, 1.20) * 0.85, r.uniform(1.1, 1.9), float(r.uniform(0.70, 0.95)), 'strand', 0.55, 0.12)
            kind = r.random()
            if kind < 0.72:      # fringe clump: a few cut warp ends / pulled bundles splaying from one point
                nc = 1 + r.poisson(0.5 + 1.2 * a)
                head0 = r.normal(0, 0.70)
                Lc = float(np.clip(r.lognormal(math.log(3.5 + 4.5 * a), 0.55), 1.2, 22.0))
                for k in range(nc):
                    L = float(np.clip(Lc * r.uniform(0.55, 1.35), 1.2, 24.0))
                    head = head0 + r.normal(0, 0.50)
                    pts, z = _path(r, u + r.normal(0, 0.9), v0, sgn, L, head, 0.040, r.uniform(7, 18), 0.080)
                    if dyed and r.random() < 0.45:
                        col = c0 * r.uniform(0.75, 1.1) * 0.85
                    else:
                        col = YARN * r.uniform(0.30, 0.72)
                    emit(pts, z, u, v0, sgn, col, r.uniform(0.55, 0.95), float(r.uniform(0.40, 0.80)), 'fringe', 0.6, 0.16)
            else:                # a loose weft pulled out and lying on the table
                if kind < 0.93:
                    L = float(r.uniform(22, 120)); w = r.uniform(0.85, 1.35); head = r.choice([-1, 1]) * (math.pi / 2 - r.uniform(0.04, 0.38))
                else:
                    L = float(r.uniform(60, 170)); w = r.uniform(0.95, 1.5); head = r.choice([-1, 1]) * (math.pi / 2 - r.uniform(0.10, 0.60))
                pts, z = _path(r, u, v0, sgn, L, head, 0.013, r.uniform(55, 120), 0.009, step=1.5)
                col = (YARN * r.uniform(0.45, 0.90)) if (not dyed or r.random() < 0.6) else c0 * r.uniform(0.8, 1.1) * 0.85
                emit(pts, z, u, v0, sgn, col, w, float(r.uniform(0.55, 0.92)), 'weft', 0.40, 0.10)
    # stray purple / gold / crimson wool left on the cloth around the king-shaped void (the unpicked king: a few strands still curling off)
    vp = info.get('void_pts')
    if vp is not None and len(vp):
        cols = [hex_lin('#5A3F72') * 0.62, hex_lin('#7A3B2C') * 0.75, hex_lin('#8C6A2E') * 0.72, hex_lin('#5A3F72') * 0.50]
        for k in range(len(vp)):
            pu, pv, nu, nv = [float(x) for x in vp[k]]
            L = float(np.clip(r.lognormal(math.log(11.0), 0.55), 4.0, 34.0))
            head = math.atan2(nu, nv) + r.normal(0, 0.9)
            pts, z = _path(r, pu, pv, 1.0, L, head, 0.040, r.uniform(8, 22), 0.045)
            P = np.array([(pu, pv)] + pts, np.float32)
            Xw, Yw = strip_to_world(P[:, 0], P[:, 1])
            out.append(dict(P=np.stack([Xw, Yw], 1).astype(np.float32), w=r.uniform(0.9, 1.5), col=cols[int(r.integers(len(cols)))] * r.uniform(0.8, 1.2),
                            z=np.full(len(P), 0.35, np.float32), op=float(r.uniform(0.70, 0.95)), kind='void', taper=0.35, jit=0.12, seed=int(r.integers(1 << 30))))
    # blackened stubs and crumbling thread ends inside the burn-through hole
    hp = info.get('hole_pts')
    if hp is not None and len(hp):
        for k in range(len(hp)):
            if r.random() > 0.5: continue
            pu, pv, nu, nv = [float(x) for x in hp[k]]
            L = float(r.uniform(1.8, 8.5))
            head = math.atan2(nu, nv * 1.0)
            n = 7
            pts = []; z = []
            ang = head + r.normal(0, 0.35); uu, vv = pu, pv
            for i in range(n):
                ang += r.normal(0, 0.25)
                uu += math.sin(ang) * L / n; vv += math.cos(ang) * L / n
                pts.append((uu, vv)); z.append(0.6)
            P = np.array([(pu - nu * 0.8, pv - nv * 0.8)] + pts, np.float32)
            Xw, Yw = strip_to_world(P[:, 0], P[:, 1])
            ash = np.array([0.045, 0.036, 0.030], np.float32) * r.uniform(0.7, 1.6)
            out.append(dict(P=np.stack([Xw, Yw], 1).astype(np.float32), w=r.uniform(0.9, 1.5), col=ash, z=np.array(z[:1] + z, np.float32),
                            op=float(r.uniform(0.6, 0.9)), kind='char', taper=0.5, jit=0.05, seed=int(r.integers(1 << 30))))
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


def draw_threads(base_lin, threads, light, pool_fn, s=S_SCREEN, SS=2, shadow_k=0.60, scale_w=1.0, sheen=0.02, occlude=None, lit_gain=0.62):
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
        rr = np.random.default_rng(th.get('seed', 0))
        n = len(P)
        op = th['op']; taper = th.get('taper', 0.45); jit = th.get('jit', 0.1)
        chunk = 4
        n_ch = max(1, (n - 1) // chunk)
        tone = 1 + jit * rr.standard_normal(n_ch + 1)
        for ci in range(n_ch):
            a0 = ci * chunk; a1 = min(n, a0 + chunk + 1)
            if a1 - a0 < 2: continue
            frac = (ci + 0.5) / n_ch
            w = th['w'] * (1 - taper * frac ** 1.3) * scale_w
            dd = P[min(a1 - 1, n - 1)] - P[a0]
            dnn = dd / (np.linalg.norm(dd) + 1e-6)
            irr_c = f(float(P[a0, 0]), float(P[a0, 1]), float(dnn[0]), float(dnn[1]))
            lit = th['col'] * irr_c * lit_gain * tone[ci]
            lit = lit + sheen * irr_c.mean() * np.array([1.0, 0.85, 0.65], np.float32) * (0.4 + 0.6 * abs(dnn[1]))
            wpx = w * s * SS
            tk = max(1, int(round(wpx)))
            op_c = op * float(np.clip(wpx / tk, 0.30, 1.0)) * (1 - 0.25 * frac)
            enc = np.clip(np.sqrt(np.clip(lit * op_c, 0, 1)) * 255, 0, 255).astype(np.uint8)
            seg = np.round(pts[a0:a1] * 16).astype(np.int32)
            cv2.polylines(colc, [seg], False, tuple(int(c) for c in enc), tk, cv2.LINE_AA, shift=4)
            cv2.polylines(alc, [seg], False, int(255 * op_c), tk, cv2.LINE_AA, shift=4)
        # contact shadow: thread lifts ~z mm; shadow offset away from the light
        zz = float(np.mean(th['z'][1:]))
        off = -lxy * (zz / max(tan_el, 0.1)) * s * SS
        sp = np.round((pts + off[None, :]) * 16).astype(np.int32)
        wsh = max(1, int(round(th['w'] * s * SS)) + 1)
        cv2.polylines(shc, [sp], False, int(255 * min(1.0, op * 0.9)), wsh, cv2.LINE_AA, shift=4)
    colc = cv2.resize(colc, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    alc = cv2.resize(alc, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    shc = cv2.resize(shc, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    shc = cv2.GaussianBlur(shc, (0, 0), 1.0)
    col_lin = colc ** 2
    if occlude is not None:
        vis_t = (1 - np.clip(occlude, 0, 1))
        alc = alc * vis_t; col_lin = col_lin * vis_t[..., None]; shc = shc * vis_t
    out = base_lin * (1 - shadow_k * shc[..., None]) * (1 - alc[..., None]) + col_lin
    return out, dict(alpha=alc)


def gen_stray(info, PX, n=100, seed=29, u_range=(60.0, 3650.0)):
    """lint and fallen fibres lying on the walnut near the cloth (not attached to it): fewer, thinner, paler than v1."""
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
        pts, z = _path(r, u, v, 1.0, L, r.uniform(-3.1, 3.1), 0.012, r.uniform(20, 60), 0.012)
        P = np.array([(u, v)] + pts, np.float32)
        Xw, Yw = strip_to_world(P[:, 0], P[:, 1])
        col = YARN * r.uniform(0.40, 0.85)
        out.append(dict(P=np.stack([Xw, Yw], 1).astype(np.float32), w=r.uniform(0.6, 1.1), col=col, z=np.full(len(P), 0.3, np.float32),
                        op=float(r.uniform(0.30, 0.65)), kind='stray', taper=0.4, jit=0.10, seed=int(r.integers(1 << 30))))
    return out
