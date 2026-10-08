"""Loose ends of the king's unpick (S09): the unpick list is cut into THREADS (consecutive entries one needle walked:
same region / kind, spatially contiguous, up to a thread length), and each thread lives through

    release  (its entries leave the cloth map; the strand lies where it was, barely lifted)
    slacken  (2 frames: it springs up, kinks where it was couched)
    curl     (3 frames: free end lifts 5-20 mm and curls)
    pull     (4 frames: drawn back through its needle hole: the curve slides along itself into the hole, the ply
              twist visibly travels toward the hole, the loop tightens)

Everything is a function of the frame (on twos, like the unpick).  A handful of long purple threads in the king's
lap are 'stubborn': they are pulled slowly through the gap (keyframe dressing for f669 'a few purple strands still
curling off the cloth', continuous with the test sequence)."""
import math
import numpy as np
from chron.stitch import K_LAID, K_SPLIT, K_BAR, K_TIE, K_STEM, K_METAL, K_MTIE, K_CORD, K_CTIE, K_SATIN, K_SQUEEZE
from chron.ageing import apply_age
from chron.color import lin2oklab

COUCH = (K_BAR, K_TIE, K_MTIE, K_CTIE, K_SQUEEZE)
LMAX = {K_LAID: 62.0, K_SATIN: 40.0, K_SPLIT: 16.0, K_STEM: 22.0, K_METAL: 18.0, K_CORD: 18.0}


def _h(i, s):
    x = (int(i) * 374761393 + int(s) * 668265263) & 0xFFFFFFFF
    x = ((x ^ (x >> 13)) * 1274126177) & 0xFFFFFFFF
    return (x ^ (x >> 16)) / 4294967296.0


class LooseEnds:
    def __init__(self, kv, f0=561, frames=80, twos=True, stubborn_n=4, seed=9):
        self.kv = kv; R = kv.rec; PX = kv.PX0
        self.f0 = f0; self.frames = frames; self.twos = twos
        self.rate = kv.n / frames
        n = kv.n
        order_un = kv.sel[::-1]                        # unpick order
        blocks = []
        cur = None
        for j, e in enumerate(order_un):
            kd = int(R['kind'][e]); typ = int(R['typ'][e])
            p = R['P'][R['off'][e]:R['off'][e + 1]] / PX
            ln = float(np.hypot(*np.diff(p, axis=0).T).sum()) if len(p) > 1 else 0.0
            if typ != 0 or kd in COUCH:
                if cur is not None: blocks.append(cur); cur = None
                if kd == K_BAR and typ == 0 and _h(e, 3) < 0.25:
                    blocks.append(dict(j0=j, j1=j + 1, ents=[e], kind=kd, L=ln, small=True))
                continue
            reg = int(R['region'][e])
            if cur is not None:
                far = np.hypot(*(p[0] - cur['last'])) > 6.0 and np.hypot(*(p[-1] - cur['last'])) > 6.0
                if reg != cur['reg'] or kd != cur['kind'] or cur['L'] + ln > LMAX.get(kd, 20.0) or far:
                    blocks.append(cur); cur = None
            if cur is None:
                cur = dict(j0=j, j1=j + 1, ents=[], kind=kd, L=0.0, reg=reg, small=False)
            cur['ents'].append(e); cur['j1'] = j + 1; cur['L'] += ln; cur['last'] = p[-1]
        if cur is not None: blocks.append(cur)
        # per block geometry / colour
        for bi, b in enumerate(blocks):
            e_last = b['ents'][-1]                     # first stitched = last unpicked -> its start is the anchor hole
            p = R['P'][R['off'][e_last]:R['off'][e_last + 1]] / PX
            b['anchor'] = p[0].astype(np.float32)
            d = p[min(3, len(p) - 1)] - p[0]
            b['dir'] = math.atan2(d[1], d[0]) if np.hypot(*d) > 1e-3 else 0.0
            cols = R['fpar'][b['ents'], 3:6]
            b['alb'] = np.median(cols, 0).astype(np.float32)
            b['rad'] = float(np.median(R['fpar'][b['ents'], 0]))
            b['id'] = bi
            b['metal'] = b['kind'] in (K_METAL,)
        # aged colours: exactly the robe's dye as the cloth ages (apply_age(age=1) = what the banner / robe stitches get),
        # chroma capped (no neon), a little darker where the strand was sheltered from the light
        A = np.array([b['alb'] for b in blocks], np.float32)[None]
        mat = np.ones(A.shape[:2], np.uint8)
        Aa = apply_age(A, mat, 1.0)[0]
        from chron.color import oklab2lin
        labA = lin2oklab(Aa[None])[0]
        Ch = np.hypot(labA[:, 1], labA[:, 2]) + 1e-9
        capC = np.minimum(Ch, 0.078) / Ch
        labA[:, 1:] *= capC[:, None]
        # dye lot of the robe under a warm 1900 K candle: the plum is rotated toward the blue-purple side so it still reads
        # as the robe's aubergine (not rose) once the candle has warmed it; darker than the faded face of the cloth
        rot = math.radians(-22.0)
        a_, b_ = labA[:, 1].copy(), labA[:, 2].copy()
        labA[:, 1] = a_ * math.cos(rot) - b_ * math.sin(rot); labA[:, 2] = a_ * math.sin(rot) + b_ * math.cos(rot)
        labA[:, 0] *= 0.93
        Aa = np.clip(oklab2lin(labA[None])[0], 0, 1)
        for b, a in zip(blocks, Aa):
            b['alb_aged'] = a
        self.blocks = blocks
        # stubborn purple threads: long laid purple blocks in the lap (y 215-252 mm), spread in x
        lab = lin2oklab(A[0])
        hue = np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360
        C = np.hypot(lab[:, 1], lab[:, 2])
        cand = [i for i, b in enumerate(blocks) if not b['small'] and b['kind'] == K_LAID and b['L'] > 27
                and (hue[i] > 290 or hue[i] < 10) and C[i] > 0.04 and 212 < b['anchor'][1] < 252 and 252 < b['anchor'][0] < 345]
        cand = sorted(cand, key=lambda i: blocks[i]['anchor'][0])
        self.stubborn = {}
        if cand:
            # four strands of different length / place (not mirrored): the nearest long purple laid thread to each target
            tg = [(270.0, 240.0), (290.0, 224.0), (312.0, 245.0), (330.0, 226.0)][:stubborn_n]
            import silhouette as SIL
            def _in(i):                        # the whole strand stays inside the void (anchor and, roughly, its far end)
                b = blocks[i]; a = b['anchor']; e = a + 0.85 * b['L'] * np.array([math.cos(b['dir']), math.sin(b['dir'])])
                d = SIL.signed_dist_mm(np.array([a, 0.5 * (a + e), e]))
                return d.min() > 4.0
            cin = [i for i in cand if _in(i)] or cand
            pick = []
            for tx, ty in tg:
                c2 = [i for i in cin if i not in pick and all(np.hypot(*(blocks[i]['anchor'] - blocks[j]['anchor'])) > 17.0 for j in pick)]
                c2 = c2 or [i for i in cand if i not in pick]
                pick.append(min(c2, key=lambda i: (blocks[i]['anchor'][0] - tx) ** 2 + (blocks[i]['anchor'][1] - ty) ** 2 - 0.4 * blocks[i]['L'] ** 2 / 10))
            for k, i in enumerate(pick):
                # pulled slowly through the gap: pull starts f640 + 6k, lasts 70-95 frames
                self.stubborn[i] = (640 + 7 * k + 2 * (k % 2), 78 + 9 * ((k * 7) % 4))
        self.seed = seed
        # only some threads come out as visible loose ends; the rest are drawn through from the back of the cloth
        PV = {K_LAID: 0.11, K_SATIN: 0.10, K_STEM: 0.05, K_SPLIT: 0.035, K_METAL: 0.10, K_CORD: 0.06}
        for b in blocks:
            p = PV.get(b['kind'], 0.03) * min(1.0, b['L'] / 10.0)
            b['vis'] = (b['id'] in self.stubborn) or (not b['small'] and _h(b['id'], 77) < p)
        self.n_vis = sum(b['vis'] for b in blocks)

    # ------------------------------------------------------------------ timing
    def te(self, f):
        return self.f0 + 2 * math.floor((f - self.f0) / 2) if self.twos else f

    def u_of(self, f):
        """entries removed at frame f (on twos)."""
        return float(np.clip((self.te(f) - self.f0) * self.rate, 0, self.kv.n))

    # ------------------------------------------------------------------ curves
    def curve(self, b, f):
        """3D polyline (k,3) sheet mm + arc offset of the visible material, or None."""
        t = self.te(f)
        fs = self.f0 + b['j0'] / self.rate
        fe = self.f0 + b['j1'] / self.rate
        if t < fs: return None
        rem = float(np.clip((t - fs) / max(fe - fs, 1e-3), 0, 1)) if t < fe else 1.0
        sm = b['small']
        Ts, Tc, Tp = (1.0, 1.5, 2.0) if sm else (2.0, 3.0, 4.0)
        ph_s = float(np.clip((t - fs) / Ts, 0, 1))
        ph_c = float(np.clip((t - fe - Ts * 0.5) / Tc, 0, 1))
        st = self.stubborn.get(b['id'])
        if st is not None:
            ps, dur = st
            ph_p = float(np.clip((f - ps) / dur, 0, 1)) ** 1.15          # slow, on ones (it is a hold)
            if f >= ps:
                ph_c = 1.0
        else:
            ph_p = float(np.clip((t - fe - Ts * 0.5 - Tc) / Tp, 0, 1))
        if ph_p >= 0.999: return None
        i = b['id']; s = self.seed
        L = b['L'] * rem
        if L < 0.6: return None
        Hmax = (1.5 + 6.5 * _h(i, s + 1) ** 2.2) * min(1.0, 0.35 + b['L'] / 30.0)
        if sm: Hmax = 0.8 + 1.2 * _h(i, s + 1)
        if b['id'] in self.stubborn: Hmax = 5.0 + 4.0 * _h(i, s + 1)
        Rc = 6.0 + 14.0 * _h(i, s + 2)
        sg = 1.0 if _h(i, s + 3) < 0.5 else -1.0
        # a released strand falls over: its heading leaves the stitch direction (more so the more it has slackened)
        th0 = b['dir'] + (_h(i, s + 4) - 0.5) * (0.6 + 1.4 * max(ph_s, ph_c))
        if i in self.stubborn:        # the dressing strands stay in the void: they lie toward the middle of the lap, turned a little
            cx_, cy_ = 297.0, 212.0
            th0 = math.atan2(cy_ - b['anchor'][1], cx_ - b['anchor'][0]) + (_h(i, s + 4) - 0.5) * 1.5
        kinksp = 3.4 + 1.6 * _h(i, s + 5)
        kinkph = _h(i, s + 6) * kinksp
        slack = (0.25 + 0.35 * ph_s + 0.40 * ph_c)
        tens = 1 - 0.6 * ph_p                                   # pulling straightens and flattens it
        Lv = L * (1 - ph_p)
        if Lv < 0.5: return None
        ds = 0.2
        k = int(min(400, max(3, Lv / ds + 1)))
        sig = np.linspace(0, Lv, k).astype(np.float64)
        u = sig / max(L, 1e-3)
        # heading: a slow meander, crinkle kinks where it was couched, a curl toward the free end
        kinks = np.floor((sig + kinkph) / kinksp)
        kj = np.array([(_h(i * 131 + int(q), s + 7) - 0.5) for q in kinks]) * 1.25 * (0.3 + 0.7 * ph_s)
        kj = np.convolve(np.pad(kj, 1, mode='edge'), np.ones(3) / 3, 'valid')
        mlen = 12.0 + 12.0 * _h(i, s + 8)
        mea = 0.20 * slack * tens * np.sin(2 * math.pi * sig / mlen + 6.28 * _h(i, s + 9))
        theta = th0 + mea + kj * tens + sg * (1.0 / Rc) * ph_c * tens * sig * np.clip((u - 0.55) / 0.45, 0, 1) ** 2 * 2.2
        # height: lies on the cloth, springs into one or two loose loops, the free end lifts
        z = np.full(k, b['rad'] * 0.95)
        nb = 1 + int(b['L'] > 26)
        for q in range(nb):
            c = (0.30 + 0.35 * _h(i, s + 20 + q) + 0.25 * q) * L
            w = 3.5 + 5.0 * _h(i, s + 30 + q)
            a = Hmax * (0.45 + 0.55 * _h(i, s + 40 + q)) * slack * tens
            z += a * np.exp(-((sig - c) / w) ** 2)
        z += Hmax * 0.8 * slack * tens * np.clip((u - 0.78) / 0.22, 0, 1) ** 1.5
        dz = np.gradient(z, sig) if k > 2 else np.zeros(k)
        hstep = np.sqrt(np.clip(1 - np.clip(dz, -0.95, 0.95) ** 2, 0.1, 1))
        dx = np.cos(theta) * hstep; dy = np.sin(theta) * hstep
        x = b['anchor'][0] + np.concatenate([[0], np.cumsum(0.5 * (dx[1:] + dx[:-1]) * np.diff(sig))])
        y = b['anchor'][1] + np.concatenate([[0], np.cumsum(0.5 * (dy[1:] + dy[:-1]) * np.diff(sig))])
        # wool crimp: small lateral wave
        nx_, ny_ = -np.sin(theta), np.cos(theta)
        cr = 0.16 * (0.4 + 0.6 * ph_s) * np.sin(2 * math.pi * sig / (1.6 + 0.5 * _h(i, s + 11)) + 6.28 * _h(i, s + 12))
        x = x + nx_ * cr; y = y + ny_ * cr
        P = np.stack([x, y, z], 1).astype(np.float32)
        return P, float(ph_p * L)

    def add_to(self, ts, f, alpha=1.0, radius_scale=1.0):
        """add every live loose end at frame f to a threads3d.ThreadSet."""
        t = self.te(f)
        u = self.u_of(f)
        nlive = 0
        for b in self.blocks:
            if not b['vis']: continue
            if b['id'] not in self.stubborn:
                fs = self.f0 + b['j0'] / self.rate
                if fs > t or fs < t - 14: continue
            c = self.curve(b, f)
            if c is None: continue
            P, soff = c
            kind = 1 if b['metal'] else 0
            hr = 0.85 + 0.45 * _h(b['id'], self.seed + 51)             # strands differ in thickness
            stub = b['id'] in self.stubborn
            ts.add(P, b['rad'] * radius_scale * hr * (0.75 if kind else 1.12), b['alb_aged'] * (0.92 + 0.16 * _h(b['id'], self.seed + 52)),
                   kind=kind, alpha=alpha, seed=(b['id'] % 17) / 17.0 + 0.03 * (b['id'] % 7), s_off=soff,
                   slub=0.20 if stub else 0.14, dip=True, fray=(6 if stub else 3) if kind == 0 else 0,
                   halo=0.22, fuzz_k=1.25 if stub else 1.0)
            nlive += 1
        return nlive


class HoleResidue:
    """wisps of the king's wool left caught in his needle holes (a few % of the holes inside the void), each one
    appearing when the last strand around that hole has been pulled out."""

    def __init__(self, kv, frac=0.07, seed=5, f0=561, frames=80):
        import cv2
        from scipy.spatial import cKDTree
        from chron.ageing import apply_age
        from chron.color import lin2oklab, oklab2lin
        R = kv.rec; PX = kv.PX0
        x0, y0 = kv.bbox[0], kv.bbox[1]
        hb = (kv.holes > 0.5).astype(np.uint8)
        n, lab, stats, cen = cv2.connectedComponentsWithStats(hb)
        cen = cen[1:]
        inside = kv.ghost_ext[np.clip(cen[:, 1].astype(int), 0, hb.shape[0] - 1), np.clip(cen[:, 0].astype(int), 0, hb.shape[1] - 1)] > 0.5
        cen = cen[inside]
        rr = np.random.default_rng(seed)
        pick = cen[rr.random(len(cen)) < frac]
        pmm = (pick + np.array([x0, y0])) / PX
        full = kv.state(kv.n)
        col = full['alb'][np.clip(pick[:, 1].astype(int), 0, hb.shape[0] - 1), np.clip(pick[:, 0].astype(int), 0, hb.shape[1] - 1)]
        col = apply_age(col[None].astype(np.float32), np.ones((1, len(col)), np.uint8), 1.0)[0]
        lab_ = lin2oklab(col[None])[0]; lab_[:, 1:] *= 0.9
        col = np.clip(oklab2lin(lab_[None])[0], 0, 1)
        # appear when the strands within 1.6 mm are all out
        mids = kv.mids_mm[kv.sel]
        tree = cKDTree(mids)
        urank = np.empty(kv.n); urank[:] = kv.n - 1 - np.arange(kv.n)    # unpick rank of sel[i]
        near = tree.query_ball_point(pmm, 1.6)
        self.u_at = np.array([urank[q].max() + 1 if len(q) else 0 for q in near])
        self.f0, self.rate = f0, kv.n / frames
        fib = []
        for i, (p, c) in enumerate(zip(pmm, col)):
            for k in range(int(rr.integers(1, 4))):
                L = float(np.clip(rr.lognormal(np.log(0.9), 0.5), 0.3, 2.6))
                a = rr.uniform(0, 2 * np.pi); cv_ = rr.normal(0, 0.9)
                m = 7
                t = np.linspace(0, 1, m)
                ang = a + cv_ * t
                xy = p + np.stack([np.cumsum(np.cos(ang)), np.cumsum(np.sin(ang))], 1) * (L / m)
                xy = np.vstack([p, xy[:-1]])
                z = 0.05 + rr.uniform(0.05, 0.5) * t ** 2
                fib.append((i, np.c_[xy, z].astype(np.float32), c * rr.uniform(0.9, 1.1)))
        self.fib = fib

    def add_to(self, ts, u):
        n = 0
        for i, P, c in self.fib:
            if u >= self.u_at[i]:
                ts.add(P, 0.085, c * 0.8, kind=2, alpha=0.85, shadow=0.35, taper=False)
                n += 1
        return n
