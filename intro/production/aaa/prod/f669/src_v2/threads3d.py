"""3D thread renderer for loose wool ends and gold tethers (screen space, linear light).

Each thread is a polyline in SHEET mm with height z (mm above the cloth).  Per pixel the thread is shaded as a
twisted 2-ply cylinder: wrap-Lambert + Kajiya-Kay toward the candle (a point light: per-point direction and
inverse-square colour supplied by the caller), slanted ply grooves, edge self-occlusion, fill; gold is a smooth
anisotropic metal with a fine wrap pitch.  A soft cast shadow is projected from the candle onto the cloth
(z = 0 plane: S = C + (P - C) * Cz / (Cz - z)) with a penumbra growing with height, and short fuzz fibres stand off
the wool.  Camera: orthographic-frontal above the frame (the 1.3 % parallax of 15 mm is negligible here)."""
import math
import numpy as np
from numba import njit


@njit(cache=True)
def _shadow_pass(buf, Q, R, A, ok, blur):
    """buf: (H,W) max-accumulated shadow alpha.  Q (N,2) screen px, R (N,) radius px, A (N,) alpha, ok (N,) segment i->i+1."""
    H, W = buf.shape
    N = Q.shape[0]
    for i in range(N - 1):
        if not ok[i]: continue
        ax = Q[i, 0]; ay = Q[i, 1]; bx = Q[i + 1, 0]; by = Q[i + 1, 1]
        r0 = R[i]; r1 = R[i + 1]; b0 = blur[i]; b1 = blur[i + 1]
        rr = max(r0, r1) + 2.5 * max(b0, b1) + 2
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
                bl = b0 + (b1 - b0) * t + 0.5
                c = 0.5 - (d - rad) / (2.0 * bl)
                if c <= 0: continue
                if c > 1: c = 1.0
                c = c * c * (3 - 2 * c)
                a = c * (A[i] + (A[i + 1] - A[i]) * t)
                if a > buf[yy, xx]: buf[yy, xx] = a


@njit(cache=True)
def _thread_pass(img, segs, Q, P, R, S, ALB, LD, LC, FILL, KIND, ALPHA, PITCH, SEED):
    """segs: segment start indices in draw order.  Q (N,2) screen px; P (N,3) mm; R radius px; S arc length mm;
    ALB (N,3); LD (N,3) unit dir to light; LC (N,3) light colour at the point; FILL (3,); KIND 0 wool 1 gold 2 fibre."""
    H, W, _ = img.shape
    for si in range(segs.shape[0]):
        i = segs[si]
        ax = Q[i, 0]; ay = Q[i, 1]; bx = Q[i + 1, 0]; by = Q[i + 1, 1]
        r0 = R[i]; r1 = R[i + 1]
        rr = max(r0, r1) + 1.5
        x0 = max(0, int(min(ax, bx) - rr)); x1 = min(W, int(max(ax, bx) + rr + 1))
        y0 = max(0, int(min(ay, by) - rr)); y1 = min(H, int(max(ay, by) + rr + 1))
        abx = bx - ax; aby = by - ay; ll = abx * abx + aby * aby + 1e-9
        sl = math.sqrt(ll)
        # 3D tangent
        tx = P[i + 1, 0] - P[i, 0]; ty = P[i + 1, 1] - P[i, 1]; tz = P[i + 1, 2] - P[i, 2]
        tn = math.sqrt(tx * tx + ty * ty + tz * tz) + 1e-9
        tx /= tn; ty /= tn; tz /= tn
        # screen-perp side vector, made perpendicular to T
        sx = -aby / sl; sy = abx / sl; sz = 0.0
        d0 = sx * tx + sy * ty
        sx -= d0 * tx; sy -= d0 * ty; sz -= d0 * tz
        sn = math.sqrt(sx * sx + sy * sy + sz * sz) + 1e-9
        sx /= sn; sy /= sn; sz /= sn
        # front vector (toward the viewer, perpendicular to T and side)
        fx = ty * sz - tz * sy; fy = tz * sx - tx * sz; fz = tx * sy - ty * sx
        if fz < 0:
            fx = -fx; fy = -fy; fz = -fz
        kind = KIND[i]
        for yy in range(y0, y1):
            for xx in range(x0, x1):
                px = xx + 0.5 - ax; py = yy + 0.5 - ay
                t = (px * abx + py * aby) / ll
                if t < 0: t = 0.0
                if t > 1: t = 1.0
                dx = px - t * abx; dy = py - t * aby
                d = math.sqrt(dx * dx + dy * dy)
                rad = r0 + (r1 - r0) * t
                cov = rad + 0.5 - d
                if cov <= 0: continue
                if cov > 1: cov = 1.0
                q = (dx * (-aby) + dy * abx) / sl / max(rad, 0.3)
                if q > 1: q = 1.0
                if q < -1: q = -1.0
                cq = math.sqrt(max(0.0, 1 - q * q))
                nx = q * sx + cq * fx; ny = q * sy + cq * fy; nz = q * sz + cq * fz
                lx = LD[i, 0] + (LD[i + 1, 0] - LD[i, 0]) * t
                ly = LD[i, 1] + (LD[i + 1, 1] - LD[i, 1]) * t
                lz = LD[i, 2] + (LD[i + 1, 2] - LD[i, 2]) * t
                lnn = math.sqrt(lx * lx + ly * ly + lz * lz) + 1e-9
                lx /= lnn; ly /= lnn; lz /= lnn
                ndl = nx * lx + ny * ly + nz * lz
                tdl = tx * lx + ty * ly + tz * lz
                # half vector with V = (0,0,1)
                hx = lx; hy = ly; hz = lz + 1.0
                hn = math.sqrt(hx * hx + hy * hy + hz * hz) + 1e-9
                tdh = (tx * hx + ty * hy + tz * hz) / hn
                sth = math.sqrt(max(0.0, 1 - tdh * tdh))
                ndh = (nx * hx + ny * hy + nz * hz) / hn
                if ndh < 0: ndh = 0.0
                s_arc = S[i] + (S[i + 1] - S[i]) * t
                a = cov * (ALPHA[i] + (ALPHA[i + 1] - ALPHA[i]) * t)
                for c in range(3):
                    alb = ALB[i, c] + (ALB[i + 1, c] - ALB[i, c]) * t
                    lc = LC[i, c] + (LC[i + 1, c] - LC[i, c]) * t
                    if kind == 0:      # wool, 2-ply twist (long irregular pitch, ply colours, fibre streaks)
                        pit = PITCH[i] * (1.0 + 0.28 * math.sin(2 * math.pi * s_arc / (PITCH[i] * 5.3) + 6.0 * SEED[i])
                                          + 0.12 * math.sin(2 * math.pi * s_arc / (PITCH[i] * 1.9) + 11.0 * SEED[i]))
                        ph = 2 * math.pi * (s_arc / pit + 0.20 * q) + 0.7 * math.sin(2 * math.pi * s_arc / (PITCH[i] * 7.7) + 3.0 * SEED[i])
                        g = 0.5 + 0.5 * math.cos(ph)
                        depth = 0.34 + 0.12 * math.sin(2 * math.pi * s_arc / (PITCH[i] * 6.1) + 17.0 * SEED[i])
                        ply = 1.0 - depth * g ** 3
                        # fibre-scale streaks along the thread (finer, stronger)
                        ph2 = 2 * math.pi * (s_arc / (PITCH[i] * 0.17) + 2.3 * q + SEED[i])
                        ph3 = 2 * math.pi * (s_arc / (PITCH[i] * 0.071) + 5.1 * q + 3.0 * SEED[i])
                        ply *= 0.86 + 0.09 * math.cos(ph2) + 0.05 * math.cos(ph3)
                        # two plies of slightly different dye lots
                        pc = math.cos(ph + 1.7)
                        dye = 1.0 + 0.07 * pc * (1.0 if c == 0 else (0.5 if c == 1 else -0.6))
                        diff = (ndl + 0.35) / 1.35
                        if diff < 0: diff = 0.0
                        sinl = math.sqrt(max(0.0, 1 - tdl * tdl))
                        kk = 0.012 * sth ** 8 + 0.010 * sth ** 3 * alb / (alb + 0.05)
                        rim = 0.20 * (1 - cq) ** 2 * max(0.0, (ndl + 0.2))
                        edge = 0.66 + 0.34 * cq
                        col = alb * dye * (lc * diff * (0.75 + 0.25 * sinl) * ply + FILL[c] * (0.55 + 0.45 * nz)) * edge \
                            + lc * (kk * ply + rim * alb * 0.8)
                    elif kind == 3:    # couched gold cord: two plies of Japan gold wound round a silk core (visible twist)
                        pit = PITCH[i] * (1.0 + 0.10 * math.sin(2 * math.pi * s_arc / (PITCH[i] * 6.3) + 5.0 * SEED[i]))
                        ph = 2 * math.pi * (s_arc / pit + 0.30 * q)
                        g = 0.5 + 0.5 * math.cos(ph)
                        groove = 0.40 + 0.60 * g ** 0.7
                        diff = max(0.0, ndl) * 0.30
                        spec = (2.6 * sth ** 40 * ndh ** 3 + 0.8 * sth ** 10 * ndh ** 2) * (0.30 + 0.70 * g)
                        env = 0.55 * (0.4 + 0.6 * max(0.0, nz)) * (0.45 + 0.55 * g)
                        silk = 0.16 * (1.0 - g)
                        col = alb * (lc * (diff * groove + spec) + FILL[c] * 0.5 * groove + lc * env) + lc * silk * alb * 0.3
                    elif kind == 1:    # smooth gold (kept for compatibility)
                        ph = 2 * math.pi * (s_arc / PITCH[i] + 0.55 * q)
                        wrap = 0.62 + 0.38 * (0.5 + 0.5 * math.cos(ph)) ** 0.5
                        diff = max(0.0, ndl) * 0.22
                        spec = 2.0 * sth ** 70 * ndh ** 4 + 0.5 * sth ** 14 * ndh ** 2 + 0.35 * ndh ** 30
                        env = 0.42 * (0.4 + 0.6 * max(0.0, nz))
                        col = alb * (lc * (diff + spec * wrap) + FILL[c] * 0.6 + lc * env * wrap)
                    else:              # stray fibre
                        diff = (ndl + 0.5) / 1.5
                        if diff < 0: diff = 0.0
                        col = alb * (lc * (0.35 + 0.65 * diff) + FILL[c])
                    img[yy, xx, c] = img[yy, xx, c] * (1 - a) + col * a


class ThreadSet:
    """collect threads, then render(img, view_ctx, candle) -> img (in place)."""

    def __init__(self):
        self.th = []

    def add(self, pts_mm, radius_mm, albedo, kind=0, alpha=1.0, pitch_mm=None, seed=0.0, shadow=1.0, taper=True, s_off=0.0,
            slub=0.0, dip=False, fray=0, halo=0.16, fuzz_k=1.0, dip_end=False):
        """slub: thick-thin variation of the radius (0.18 = +-18 %); dip: the first mm goes down into a needle hole
        (radius and opacity ramp); fray: number of splayed fibres at the free end; halo / fuzz_k: fuzz strength."""
        p = np.asarray(pts_mm, np.float32)
        if len(p) < 2: return
        n = len(p)
        r = np.full(n, radius_mm, np.float32)
        if slub > 0 and kind in (0, 3):
            arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
            ph0 = 6.28 * (seed * 13.7 % 1.0)
            r *= (1 + slub * (0.62 * np.sin(2 * np.pi * arc / (6.0 + 3.0 * (seed % 1.0)) + ph0)
                              + 0.38 * np.sin(2 * np.pi * arc / (2.1 + 0.9 * (seed * 3.1 % 1.0)) + 2.0 * ph0))).astype(np.float32)
        if taper and kind == 0:
            if fray:       # the free end: plies come apart, the body thins over the last ~3 mm
                arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
                tl = np.clip((arc[-1] - arc) / 3.2, 0, 1)
                r *= (0.45 + 0.55 * tl ** 0.8).astype(np.float32)
            else:
                r[-1] *= 0.55; r[-2] *= 0.8
        al = np.broadcast_to(np.asarray(albedo, np.float32), (n, 3)).astype(np.float32).copy()
        a = np.broadcast_to(np.asarray(alpha, np.float32), (n,)).astype(np.float32).copy()
        if dip:
            arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
            u = np.clip(arc / 0.9, 0, 1)
            r *= (0.5 + 0.5 * u).astype(np.float32); a *= (0.15 + 0.85 * u ** 0.7).astype(np.float32)
            al *= (0.55 + 0.45 * u)[:, None]
        if dip_end:
            arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))])
            u = np.clip((arc[-1] - arc) / 1.1, 0, 1)
            r *= (0.45 + 0.55 * u).astype(np.float32); a *= (0.1 + 0.9 * u ** 0.6).astype(np.float32)
            al *= (0.5 + 0.5 * u)[:, None]
        if pitch_mm is None:
            pitch_mm = (3.6 * radius_mm * 2.0) if kind == 0 else (0.42 if kind == 1 else 4.4 * radius_mm)
        self.th.append(dict(P=p, R=r, A=al, kind=kind, alpha=a, pitch=pitch_mm, seed=seed, shadow=shadow, soff=s_off,
                            fray=fray, halo=halo, fuzz_k=fuzz_k))

    def render(self, img, ctx, candle_pos, light_col_fn, fill, shadow_strength=0.8, flame_r_mm=4.0,
               fuzz=True, fuzz_seed=0, shadow_only=False, shadow_decay_mm=3.4, fuzz_per_mm=9.0):
        """ctx: dict(x0, y0, s) (sheet mm of the screen origin, px per mm).  light_col_fn(P (N,3) mm) -> (N,3) light
        colour reaching each point (inverse-square, pool).  fill: (3,) linear.  Cast shadows: the candle is an extended
        source (flame_r_mm), penumbra = flame_r * z / (Cz - z); a thin strand's shadow thins out with its penumbra and
        with height (exp(-z / shadow_decay_mm)): contact shadows hug the strand, the long streaks of raised parts fade."""
        if not self.th: return img
        x0, y0, s = ctx['x0'], ctx['y0'], ctx['s']
        H, W, _ = img.shape
        C = np.asarray(candle_pos, np.float32)
        allP, allR, allA, allK, allAl, allPi, allSe, allS, ok, shA = [], [], [], [], [], [], [], [], [], []
        rng = np.random.default_rng(fuzz_seed)
        fibres = []
        halos = []
        for t in self.th:
            P = t['P']; n = len(P)
            seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
            sarc = (t['soff'] + np.concatenate([[0], np.cumsum(seg)])).astype(np.float32)
            allP.append(P); allR.append(t['R']); allA.append(t['A']); allK.append(np.full(n, t['kind'], np.int32))
            allAl.append(t['alpha']); allPi.append(np.full(n, t['pitch'], np.float32)); allSe.append(np.full(n, t['seed'], np.float32))
            allS.append(sarc)
            o = np.ones(n, bool); o[-1] = False
            ok.append(o)
            shA.append(np.full(n, t['shadow'], np.float32) * t['alpha'])
            if t['kind'] == 0 and t['halo'] > 0:
                halos.append((P, t['R'] * 1.9, t['A'], t['alpha'] * t['halo']))
            if fuzz and t['kind'] == 0 and sarc[-1] - sarc[0] > 1.0:
                sarc0 = sarc - sarc[0]
                nf = int(sarc0[-1] * fuzz_per_mm * t['fuzz_k'])
                for _ in range(nf):
                    sa = rng.uniform(0, sarc0[-1])
                    j = min(np.searchsorted(sarc0, sa), n - 1); j0 = max(j - 1, 0)
                    base = P[j0] + (P[j] - P[j0]) * (0 if j == j0 else (sa - sarc0[j0]) / max(sarc0[j] - sarc0[j0], 1e-6))
                    tang = P[j] - P[j0]; tang = tang / (np.linalg.norm(tang) + 1e-6)
                    ang = rng.uniform(0, 2 * np.pi)
                    perp = np.cross(tang, np.array([0, 0, 1.0], np.float32)); perp /= (np.linalg.norm(perp) + 1e-6)
                    up = np.cross(perp, tang)
                    out = perp * math.cos(ang) + up * math.sin(ang)
                    L = rng.lognormal(math.log(0.75), 0.55)
                    k = 6
                    pts = [base + out * t['R'][j] * 0.8]
                    d = out * 0.75 + tang * rng.normal(0, 0.5)
                    for q in range(k):
                        d = d + rng.normal(0, 0.55, 3); d /= np.linalg.norm(d) + 1e-6
                        pts.append(pts[-1] + d * L / k)
                    pts = np.array(pts, np.float32)
                    fibres.append((pts, t['A'][0] * rng.uniform(1.0, 1.3), 0.085))
                if t['fray']:      # splayed plies and loose fibres at the free end
                    tip = P[-1]; tdir = P[-1] - P[max(-4, -n)]; tdir /= (np.linalg.norm(tdir) + 1e-6)
                    for _ in range(int(t['fray'])):
                        ang = rng.uniform(0, 2 * np.pi)
                        perp = np.cross(tdir, np.array([0, 0, 1.0], np.float32)); perp /= (np.linalg.norm(perp) + 1e-6)
                        up = np.cross(perp, tdir)
                        spread = perp * math.cos(ang) + up * math.sin(ang)
                        L = rng.uniform(1.4, 4.2)
                        k = 6
                        pts = [tip + spread * 0.05]
                        d = tdir * 0.8 + spread * rng.uniform(0.15, 0.55)
                        for q in range(k):
                            d = d + rng.normal(0, 0.22, 3) + np.array([0, 0, -0.10], np.float32); d /= np.linalg.norm(d) + 1e-6
                            pts.append(pts[-1] + d * L / k)
                        pts = np.array(pts, np.float32)
                        pts[:, 2] = np.maximum(pts[:, 2], 0.05)
                        fibres.append((pts, t['A'][-1] * rng.uniform(1.0, 1.35), 0.11))
        for Ph, Rh, Ah, ah in halos:
            n = len(Ph)
            allP.append(Ph - np.array([0, 0, 0.02], np.float32)); allR.append(Rh.astype(np.float32)); allA.append(Ah)
            allK.append(np.full(n, 2, np.int32)); allAl.append(ah.astype(np.float32))
            allPi.append(np.ones(n, np.float32)); allSe.append(np.zeros(n, np.float32))
            allS.append(np.zeros(n, np.float32)); o = np.ones(n, bool); o[-1] = False; ok.append(o)
            shA.append(np.zeros(n, np.float32))
        for pts, col, rad in fibres:
            n = len(pts)
            allP.append(pts); allR.append(np.full(n, rad, np.float32)); allA.append(np.tile(col, (n, 1)).astype(np.float32))
            allK.append(np.full(n, 2, np.int32)); allAl.append(np.linspace(0.75 if rad < 0.1 else 0.8, 0.18, n).astype(np.float32))
            allPi.append(np.ones(n, np.float32)); allSe.append(np.zeros(n, np.float32))
            allS.append(np.zeros(n, np.float32)); o = np.ones(n, bool); o[-1] = False; ok.append(o)
            shA.append(np.full(n, 0.15, np.float32))
        P = np.concatenate(allP).astype(np.float32); R = np.concatenate(allR); A = np.concatenate(allA).astype(np.float32)
        K = np.concatenate(allK); AL = np.concatenate(allAl); PI = np.concatenate(allPi); SE = np.concatenate(allSe)
        S = np.concatenate(allS).astype(np.float32); OK = np.concatenate(ok); SH = np.concatenate(shA)
        # lighting
        Ld = C[None, :] - P
        Ld /= np.linalg.norm(Ld, axis=1, keepdims=True) + 1e-6
        LC = np.asarray(light_col_fn(P), np.float32)
        Q = np.stack([(P[:, 0] - x0) * s, (P[:, 1] - y0) * s], 1).astype(np.float32)
        Rpx = (R * s).astype(np.float32)
        # cast shadows (from the candle onto the cloth), extended source
        z = np.clip(P[:, 2], 0, C[2] - 1)
        k = C[2] / (C[2] - z)
        Sxy = C[None, :2] + (P[:, :2] - C[None, :2]) * k[:, None]
        Qs = np.stack([(Sxy[:, 0] - x0) * s, (Sxy[:, 1] - y0) * s], 1).astype(np.float32)
        pen = (flame_r_mm * z / (C[2] - z) + 0.12) * s
        Rs = (R * s * k).astype(np.float32)
        dens = np.clip(2.2 * Rs / (2.2 * Rs + 1.6 * pen), 0.0, 1.0) * np.exp(-z / shadow_decay_mm)
        As = (SH * shadow_strength * np.clip(dens, 0.0, 1.0)).astype(np.float32)
        buf = np.zeros((H, W), np.float32)
        _shadow_pass(buf, Qs, Rs, As, OK, pen.astype(np.float32))
        img *= (1 - buf)[..., None]
        if shadow_only:
            return img
        # draw order: by height (low first), fibres after their thread
        idx = np.nonzero(OK)[0]
        zm = 0.5 * (P[idx, 2] + P[idx + 1, 2]) + (K[idx] == 2) * (R[idx] < 0.15) * 0.05
        segs = idx[np.argsort(zm, kind='stable')].astype(np.int64)
        _thread_pass(img, segs, Q, P, Rpx, S, A, Ld.astype(np.float32), LC, np.asarray(fill, np.float32), K, AL, PI, SE)
        return img
