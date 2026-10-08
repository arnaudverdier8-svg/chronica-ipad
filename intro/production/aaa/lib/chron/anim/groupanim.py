"""Stitch-on and UNPICK of record groups (gate G8; storyboard S07, S09, S13, S15, S19).

A group (e.g. p1 'king') is replayed EXACTLY on top of the sheet's *_ground MapSet (which already carries the group's
ghost: protected linen, needle holes at the real strand ends, red-brown underdrawing).  The stitch order is the
needle-path order baked into stitches.npz ('order'); an unpick runs it backwards.

    ga = GroupAnim(MapSet(MAPS+'/p1_oath_ground'), groups=['king'])
    # stitch-on: u = entries done (float, grows), rate = entries per frame
    fr = frontal.render(ga.ground, view, light, edit=ga.edit(u=ga.n * 0.4, rate=60, mode='on'), overlay=ga.overlay(...))
    # unpick: u = entries REMOVED (0 .. n)
    fr = frontal.render(ga.ground, view, light, edit=ga.edit(u=1200, mode='unpick'), overlay=ga.loose_overlay(u, rate))

Checkpoint + forward replay: level-0 snapshots of the group's bbox every `snap_every` entries (LRU), so any state costs
at most one snapshot copy + snap_every stitches of replay (adding stitches is exact)."""
import math
from collections import OrderedDict
import numpy as np, cv2
from ..record import replay, bbox_of, blank_like
from ..maps import downsample_key
from ..fibres import splat_thick, light_curves
from ..shade import light_vec
from ..util import sstep


class GroupAnim:
    def __init__(self, ground, groups, rec=None, snap_every=1500, pad_mm=3.0):
        self.ground = ground
        self.rec = rec if rec is not None else ground.stitches()
        import json, os
        gj = json.load(open(os.path.join(ground.path, 'groups.json')))
        names = gj['groups']
        gids = [names.index(g) if isinstance(g, str) else int(g) for g in groups]
        R = self.rec
        order = R['order']
        self.sel = order[np.isin(R['group'][order], gids)]
        self.n = len(self.sel)
        self.PX0 = float(R['PX'])
        pad = int(pad_mm * self.PX0)
        self.bbox = bbox_of(R, self.sel, pad)          # level-0 px (x0, y0, x1, y1)
        x0, y0, x1, y1 = self.bbox
        f = 8
        x0 -= x0 % f; y0 -= y0 % f; x1 += (-x1) % f; y1 += (-y1) % f
        self.bbox = (x0, y0, x1, y1)
        self.snap_every = snap_every
        self._snaps = OrderedDict()
        self._base = None

    # ---------------------------------------------------------------- exact states at level 0
    def _ground_patch(self):
        if self._base is None:
            x0, y0, x1, y1 = self.bbox
            keys = ['h', 'alb', 'T', 'mat', 'cov', 'sid'] + (['pad'] if 'pad' in self.ground.channels else [])
            g = self.ground.read_px(x0, y0, x1, y1, 0, keys=keys)
            self._base = blank_like(g)
            self._base['sid'] = g['sid'].astype(np.int32)
        return self._base

    def state(self, k, grow_last=None, hmul_tail=None):
        """level-0 maps of the bbox with the first k entries of the group stitched (k int).  grow_last: growth fraction of
        entry k (in flight).  hmul_tail: array of height multipliers for the last len(hmul_tail) completed entries."""
        k = int(np.clip(k, 0, self.n))
        ks = (k // self.snap_every) * self.snap_every
        if hmul_tail is not None and len(hmul_tail):
            ks = min(ks, max(0, k - len(hmul_tail)) // self.snap_every * self.snap_every)
        if ks in self._snaps:
            st = {kk: (v.copy() if isinstance(v, np.ndarray) else v) for kk, v in self._snaps[ks].items()}
            self._snaps.move_to_end(ks)
        else:
            st = {kk: (v.copy() if isinstance(v, np.ndarray) else v) for kk, v in self._ground_patch().items()}
            if ks > 0:
                replay(st, self.rec, self.sel[:ks], self.bbox[0], self.bbox[1])
            self._snaps[ks] = {kk: (v.copy() if isinstance(v, np.ndarray) else v) for kk, v in st.items()}
            if len(self._snaps) > 4:
                self._snaps.popitem(last=False)
        idx = self.sel[ks:k]
        g = np.ones(len(idx), np.float32); hm = np.ones(len(idx), np.float32)
        if hmul_tail is not None and len(hmul_tail):
            t = min(len(hmul_tail), len(idx))
            hm[len(idx) - t:] = hmul_tail[len(hmul_tail) - t:]
        if grow_last is not None and k < self.n and grow_last > 0:
            idx = np.concatenate([idx, self.sel[k:k + 1]])
            g = np.concatenate([g, [grow_last]]).astype(np.float32); hm = np.concatenate([hm, [1.0]]).astype(np.float32)
        replay(st, self.rec, idx, self.bbox[0], self.bbox[1], grow=g, hmul=hm)
        return st

    # ---------------------------------------------------------------- frontal.render hooks
    def paste(self, m, st):
        """paste a level-0 state patch into a window maps dict m (any level)."""
        f = int(round(self.PX0 / m['PX']))
        x0, y0, x1, y1 = self.bbox
        patch = {}
        for k in ('h', 'alb', 'T', 'mat', 'cov'):
            v = st[k]
            patch[k] = v if f == 1 else downsample_key(k, v, f)
        ox = int(round(m['origin_mm'][0] * m['PX'])); oy = int(round(m['origin_mm'][1] * m['PX']))
        px0, py0 = x0 // f - ox, y0 // f - oy
        ph, pw = patch['h'].shape
        H, W = m['h'].shape
        a0, b0 = max(px0, 0), max(py0, 0)
        a1, b1 = min(px0 + pw, W), min(py0 + ph, H)
        if a1 <= a0 or b1 <= b0: return m
        for k, v in patch.items():
            m[k][b0:b1, a0:a1] = v[b0 - py0:b1 - py0, a0 - px0:a1 - px0]
        return m

    def edit(self, u, mode='unpick', rate=None, pop_frames=3, grow=True):
        """callable for frontal.render(edit=...).  mode 'on': u = entries done (float); 'unpick': u = entries removed."""
        def fn(m):
            if mode == 'unpick':
                k = self.n - int(math.floor(u))
                st = self.state(k)
            else:
                k = int(math.floor(u)); fr = u - k
                tail = None
                if rate:
                    nt = int(min(k, pop_frames * rate))
                    if nt > 0:
                        age = (u - (np.arange(k - nt, k) + 1)) / rate          # frames since completion
                        tail = np.interp(age, [0, 1, 2, 3], [0.55, 1.15, 1.05, 1.0]).astype(np.float32)
                st = self.state(k, grow_last=fr if grow else None, hmul_tail=tail)
            self.paste(m, st)
        return fn

    # ---------------------------------------------------------------- needle tip / glint
    def needle_tip(self, u):
        """(x_mm, y_mm, dir) of the needle at stitch-on progress u (the growing tip), or None."""
        k = int(math.floor(u)); fr = u - k
        if k >= self.n: return None
        e = self.sel[k]
        R = self.rec
        if R['typ'][e] != 0: return None
        p = R['P'][R['off'][e]:R['off'][e + 1]]
        seg = np.hypot(*np.diff(p, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)])
        t = fr * s[-1]
        x = np.interp(t, s, p[:, 0]); y = np.interp(t, s, p[:, 1])
        i = min(max(np.searchsorted(s, t), 1), len(p) - 1)
        d = p[i] - p[i - 1]; d = d / (np.linalg.norm(d) + 1e-6)
        return x / self.PX0, y / self.PX0, d

    def glint_overlay(self, u, strength=0.9, length_mm=1.6):
        """overlay callable drawing a small steel needle glint (capped, L2) at the growing tip."""
        def ov(img, ctx):
            tip = self.needle_tip(u)
            if tip is None: return
            x, y, d = tip
            s = ctx['s']
            X, Y = (x - ctx['x0']) * s, (y - ctx['y0']) * s
            L = max(2.0, length_mm * s)
            H, W, _ = img.shape
            x0, x1 = int(max(X - L - 3, 0)), int(min(X + L + 3, W)); y0, y1 = int(max(Y - L - 3, 0)), int(min(Y + L + 3, H))
            if x1 <= x0 or y1 <= y0: return
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            px, py = xx - X, yy - Y
            along = px * d[0] + py * d[1]; across = -px * d[1] + py * d[0]
            g = np.exp(-(across / max(0.6, 0.06 * s)) ** 2) * np.exp(-(along / (0.45 * L)) ** 2)
            img[y0:y1, x0:x1] += (g * strength)[..., None] * np.array([1.0, 0.97, 0.92], np.float32)
        return ov

    # ---------------------------------------------------------------- loose ends (unpick)
    def loose_overlay(self, u, rate, light, frames=6, lift_mm=(5.0, 20.0), linger=(), seed=0, alpha=1.0):
        """overlay callable: strands removed within the last `frames` frames are drawn as 3D loose ends: kinked where
        they were couched, lifting and curling 5-20 mm off the cloth, then pulled through to their needle hole.
        linger: list of (entry rank in the unpick, fixed phase in [0,1]) strands that stay curling (keyframe dressing)."""
        R = self.rec
        def ov(img, ctx):
            s = ctx['s']; x0, y0 = ctx['x0'], ctx['y0']
            removed_ranks = []
            nmax = int(math.floor(u))
            span = int(math.ceil(frames * rate)) + 1
            for j in range(max(0, nmax - span), min(nmax, self.n)):
                a = (u - (j + 1)) / rate
                if 0 <= a < frames:
                    removed_ranks.append((j, a / frames))
            for j, ph in linger:
                if j < min(nmax, self.n):
                    removed_ranks.append((j, ph))
            curves, cols, rads = [], [], []
            for j, ph in removed_ranks:
                e = self.sel[self.n - 1 - j]
                if R['typ'][e] != 0: continue
                p = R['P'][R['off'][e]:R['off'][e + 1]] / self.PX0
                if len(p) < 2: continue
                rr = np.random.default_rng(seed * 7919 + int(e))
                C = self._curl(p, ph, rr, lift_mm)
                if C is None: continue
                curves.append(C); cols.append(R['fpar'][e, 3:6]); rads.append(R['fpar'][e, 0])
            if not curves: return
            K = 16
            Pc = np.stack([_resample3(c, K) for c in curves]).astype(np.float32)
            A = np.array(cols, np.float32)
            Cl, so = _light_loose(Pc, A, light, s)
            Q = np.stack([(Pc[..., 0] - x0) * s, (Pc[..., 1] - y0) * s], -1).astype(np.float32)
            Rr = (np.array(rads, np.float32)[:, None] * s * np.ones((1, K), np.float32)) * 0.9
            Al = np.full(Rr.shape, alpha, np.float32)
            sa = (0.45 * np.exp(-Pc[..., 2] / 5.0)).astype(np.float32)      # high strands cast faint, soft shadows
            splat_thick(img, Q, Rr, Cl, Al, so, sa, float(max(1.0, 0.15 * s)))
        return ov

    @staticmethod
    def _curl(p, ph, rr, lift_mm):
        """3D loose end for phase ph in [0,1]: anchored at p[0] (its needle hole), free end lifting and curling;
        from ph 0.45 on it is pulled through the hole (visible length shrinks)."""
        seg = np.hypot(*np.diff(p, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)])
        Ltot = s[-1]
        if Ltot < 0.3: return None
        vis = 1.0 - sstep(0.45, 1.0, ph)
        if vis <= 0.02: return None
        n = 24
        t = np.linspace(0, 1, n) * vis
        xy = np.stack([np.interp(t * Ltot, s, p[:, 0]), np.interp(t * Ltot, s, p[:, 1])], 1)
        # pulled through: the remaining strand slides toward the anchor
        slide = (1 - vis) * Ltot
        d0 = p[min(1, len(p) - 1)] - p[0]; d0 = d0 / (np.linalg.norm(d0) + 1e-6)
        xy = xy - d0 * slide * 0.0
        lift = rr.uniform(*lift_mm) * sstep(0.0, 0.5, ph)
        z = lift * (t / max(vis, 1e-3)) ** 1.6 * min(1.0, Ltot / 12.0 + 0.3)
        # curl about the strand axis + kinks where it was couched (every ~4.5 mm)
        nrm = np.array([-d0[1], d0[0]])
        curl = rr.uniform(0.6, 1.6) * sstep(0.1, 0.8, ph) * (t / max(vis, 1e-3)) ** 2 * lift * 0.5 * rr.choice([-1, 1])
        kink = 0.25 * np.sign(np.sin(t * Ltot / 4.5 * math.pi)) * sstep(0.0, 0.3, ph)
        xy = xy + nrm[None, :] * (curl + kink * 0.3)[:, None]
        return np.concatenate([xy, z[:, None] + 0.4], 1).astype(np.float32)


def _light_loose(Pc, A, light, s):
    """per-curve Kajiya-Kay colour lit by the DOMINANT light at the curve (directional key or a point practical with
    inverse-square falloff) + fill; matching cast-shadow offsets (screen px)."""
    from ..color import light_colour
    n, K, _ = Pc.shape
    fill = np.asarray(light['fill'], np.float32) * light['fill_i']
    Lk = light_vec(light['az'], light['el']); ck = np.asarray(light['key'], np.float32) * light['key_i']
    C = np.zeros(Pc.shape, np.float32); so = np.zeros((n, K, 2), np.float32)
    for i in range(n):
        c = Pc[i].mean(0)
        L, col = Lk, ck
        for p in light.get('points', []):
            d = np.asarray(p['pos_mm'], np.float32) - c
            dist = float(np.linalg.norm(d)) + 1e-3
            pc = np.asarray(p.get('col', light_colour(p.get('K', 1900), p.get('tint', 0.5))), np.float32) * p['i'] * (p.get('ref_mm', 200.0) / dist) ** 2
            if pc.sum() > col.sum():
                L, col = (d / dist).astype(np.float32), pc
        C[i] = light_curves(Pc[i:i + 1], A[i:i + 1], L, col, fill)[0]
        l2 = L[:2] / (np.linalg.norm(L[:2]) + 1e-6); tan_el = max(L[2] / (np.linalg.norm(L[:2]) + 1e-6), 0.08)
        so[i, :, 0] = -l2[0] * Pc[i, :, 2] / tan_el * s; so[i, :, 1] = -l2[1] * Pc[i, :, 2] / tan_el * s
    return C, so


def _resample3(c, K):
    seg = np.linalg.norm(np.diff(c, axis=0), axis=1); s = np.concatenate([[0], np.cumsum(seg)])
    if s[-1] < 1e-6:
        return np.repeat(c[:1], K, 0)
    ss = np.linspace(0, s[-1], K)
    return np.stack([np.interp(ss, s, c[:, i]) for i in range(3)], 1)
