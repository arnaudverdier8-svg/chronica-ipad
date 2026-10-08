"""The king's unpick on p1' (S09) with a KING-SHAPED void.

Like chron.anim.groupanim.GroupAnim (exact needle-order replay, checkpoint + forward replay), but on a re-partitioned
record (see silhouette.py) and on a ground patch REBUILT from first principles (verified bit-exact against the baked
p1_oath_ground, max |dh| 2.4e-4 mm = fp16 rounding):

    analytic linen (seed 11)  ->  ghost (flattened protected linen over the bake polygon UNION the silhouette,
    stored underdrawing, stored needle holes + new holes at the strand ends of the cape debris)  ->  replay of every
    ground entry except the debris  ->  replay of the kept throne entries of the old king group.

The unpick list U = king entries inside the silhouette + ground cape debris, in needle order (debris slotted in by
height into the king's sweep).  Unpick removes U from the end (couching first, then top -> bottom)."""
import math, json, os
from collections import OrderedDict
import numpy as np, cv2
from chron.record import replay, bbox_of, blank_like
from chron.maps import downsample_key
from chron.linen import make_linen
from chron.color import hex_lin
from chron.stitch import K_LAID, K_SPLIT, K_BAR, K_TIE, K_STEM, K_METAL, K_MTIE, K_CORD, K_CTIE, K_SATIN, K_SQUEEZE
import silhouette as SIL

COUCH = (K_BAR, K_TIE, K_MTIE, K_CTIE, K_SQUEEZE)
LINEN_SEED = 11          # hints/p1_oath.json linen_seed
GHOST_SEED = 101 + 5     # bake seed + 5 (_ghost)


def entry_geometry(R):
    off = R['off']; P = R['P']
    cnt = np.diff(off)
    mids = (np.add.reduceat(P, off[:-1], axis=0) / np.maximum(cnt, 1)[:, None]).astype(np.float32)
    bx0 = np.minimum.reduceat(P[:, 0], off[:-1]); bx1 = np.maximum.reduceat(P[:, 0], off[:-1])
    by0 = np.minimum.reduceat(P[:, 1], off[:-1]); by1 = np.maximum.reduceat(P[:, 1], off[:-1])
    return mids, np.stack([bx0, by0, bx1, by1], 1)


class KingVoid:
    def __init__(self, ground, snap_every=1200, pad_mm=4.0, verbose=True):
        self.ground = G = ground
        self.rec = R = G.stitches()
        self.PX0 = PX = float(R['PX'])
        names = json.load(open(os.path.join(G.path, 'groups.json')))['groups']
        gk = names.index('king')
        mids, bb = entry_geometry(R)
        self.mids_mm = mids / PX
        near = (mids[:, 0] > 2200) & (mids[:, 0] < 3800) & (mids[:, 1] > 1250) & (mids[:, 1] < 2900)
        ins = np.zeros(len(mids), bool)
        idx = np.nonzero(near)[0]
        ins[idx] = SIL.inside(self.mids_mm[idx])
        king = R['group'] == gk
        gnd = R['group'] == 0
        order = R['order']
        rank = np.empty(len(order), np.int64); rank[order] = np.arange(len(order))
        self.keep = order[np.isin(order, np.nonzero(king & ~ins)[0])]          # throne pieces of the old king group
        self.debris = np.nonzero(gnd & ins)[0]
        kin = order[np.isin(order, np.nonzero(king & ins)[0])]                  # king entries, needle order
        # slot the debris into the king's sweep by height (fills with fills, couching with couching)
        tkey = np.arange(len(kin), dtype=np.float64)
        ky = mids[kin, 1]; kc = np.isin(R['kind'][kin], COUCH)
        dkeys = []
        for d in self.debris[np.argsort(rank[self.debris])]:
            blk = np.isin(R['kind'][d], COUCH)
            cand = np.nonzero(kc == blk)[0]
            j = cand[np.argmin(np.abs(ky[cand] - mids[d, 1]))]
            dkeys.append(j + 0.5 + 1e-4 * len(dkeys))
        allk = np.concatenate([tkey, np.array(dkeys)])
        allid = np.concatenate([kin, self.debris[np.argsort(rank[self.debris])]])
        self.sel = allid[np.argsort(allk, kind='stable')]
        self.n = len(self.sel)
        if verbose:
            print(f'[kingvoid] unpick {self.n} (king {len(kin)} + debris {len(self.debris)}), kept throne {len(self.keep)}')
        # bbox (level-0 px)
        b = bbox_of(R, np.concatenate([self.sel, self.keep]), int(pad_mm * PX))
        f = 8
        x0, y0, x1, y1 = b
        x0 -= x0 % f; y0 -= y0 % f; x1 += (-x1) % f; y1 += (-y1) % f
        self.bbox = (x0, y0, x1, y1)
        self._bb = bb
        self._snaps = OrderedDict()
        self.snap_every = snap_every
        self._base = self._build_base(verbose)

    # ------------------------------------------------------------------ ground patch rebuilt without the debris
    def _build_base(self, verbose):
        G, R, PX = self.ground, self.rec, self.PX0
        x0, y0, x1, y1 = self.bbox
        M = 40
        ly = G.read_px(x0 - M, y0 - M, x1 + M, y1 + M, 0, keys=['ghost', 'ud', 'holes', 'pad'])
        H, W = y1 - y0 + 2 * M, x1 - x0 + 2 * M
        lin = make_linen(H, W, PX, (x0 - M) / PX, (y0 - M) / PX, seed=LINEN_SEED)
        sil = SIL.sil_mask(x0 - M, y0 - M, W, H, PX).astype(np.float32)
        gm = np.maximum(ly['ghost'].astype(np.float32), sil)
        self.ghost_ext = gm[M:-M, M:-M].copy()
        s = cv2.GaussianBlur(gm, (0, 0), 0.4 * PX)
        lin['h'] = np.where(lin['h'] > 0, lin['h'] * (1 - 0.30 * s), lin['h']).astype(np.float32)
        ink = hex_lin('#6E3326')
        amean = 0.4941                                   # global mean linen albedo of the bake canvas (measured)
        ud = np.maximum(ly['ud'].astype(np.float32), SIL.draw_underdrawing(H, W, x0 - M, y0 - M, PX, seed=GHOST_SEED + 3))
        # inside the void the designer's drawing is the subject: ink a little stronger than the bake's 0.72 / 0.6 cap
        ink_k = 0.72 + 0.23 * cv2.GaussianBlur(sil, (0, 0), 2.0 * PX)
        a = np.clip(ud * ink_k, 0, 0.6 + 0.12 * sil)[..., None]
        lin['alb'] = lin['alb'] * (1 - a) + (lin['alb'] * ink / (amean + 1e-3) * 0.9) * a
        hole = ly['holes'].astype(np.float32)
        hole = np.maximum(hole, self._debris_holes(hole, x0 - M, y0 - M, sil))
        rim = np.clip(cv2.GaussianBlur(hole, (0, 0), 0.22 * PX) * 1.7 - hole, 0, 1)
        lin['h'] = lin['h'] - 0.28 * hole + 0.07 * rim
        lin['alb'] = lin['alb'] * (1 - 0.5 * hole[..., None]) * (1 + 0.06 * rim[..., None])
        self.holes = hole[M:-M, M:-M].copy()
        for k in ('h', 'alb', 'T', 'cov'):
            lin[k] = lin[k].astype(np.float16)
        for k in ('h', 'alb', 'T', 'mat', 'cov'):
            lin[k] = lin[k][M:-M, M:-M]
        lin['origin_mm'] = (x0 / PX, y0 / PX)
        mm = blank_like(lin)
        mm['base'] = ly['pad'][M:-M, M:-M].astype(np.float32)
        bb = self._bb; pad = 30
        hit = (bb[:, 2] > x0 - pad) & (bb[:, 0] < x1 + pad) & (bb[:, 3] > y0 - pad) & (bb[:, 1] < y1 + pad)
        order = R['order']
        dset = np.zeros(len(R['typ']), bool); dset[self.debris] = True
        gsel = order[(R['group'][order] == 0) & hit[order] & ~dset[order]]
        replay(mm, R, gsel, x0, y0)
        replay(mm, R, self.keep, x0, y0)
        if verbose:
            print(f'[kingvoid] base rebuilt: {W - 2 * M}x{H - 2 * M} px, {len(gsel)} ground + {len(self.keep)} throne entries')
        return mm

    def _debris_holes(self, hole_old, ox, oy, sil):
        """needle holes (bake recipe: strand ends, Poisson 1.05 mm, 0.17-0.26 mm pits) for the debris strands, only
        where the bake had no ghost (outside its polygon)."""
        R, PX = self.rec, self.PX0
        H, W = hole_old.shape
        rr = np.random.default_rng(GHOST_SEED + 77)
        occ = cv2.dilate((hole_old > 0.3).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
        pts = []
        for k in self.debris:
            if R['typ'][k] != 0: continue
            kd = R['kind'][k]
            if kd in (K_TIE, K_MTIE, K_CTIE): continue
            if kd == K_SPLIT and (k % 3) != 0: continue
            p = R['P'][R['off'][k]:R['off'][k + 1]]
            pts.append(p[0]); pts.append(p[-1])
        hole = np.zeros((H, W), np.float32)
        if not pts: return hole
        pts = np.array(pts, np.float32) - np.array([ox, oy], np.float32)
        pts = pts[rr.permutation(len(pts))]
        cell = 1.05 * PX; grid = {}; keep = []
        for p in pts:
            if not (0 <= p[0] < W and 0 <= p[1] < H): continue
            if occ[int(p[1]), int(p[0])]: continue
            gx, gy = int(p[0] / cell), int(p[1] / cell)
            ok = True
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = grid.get((gx + dx, gy + dy))
                    if q is not None and (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 < cell * cell:
                        ok = False; break
                if not ok: break
            if ok:
                grid[(gx, gy)] = p; keep.append(p)
        for p in keep:
            rad = rr.uniform(0.17, 0.26) * PX
            cv2.circle(hole, (int(round(p[0] * 4)), int(round(p[1] * 4))), max(1, int(round(rad * 4))), 1.0, -1, cv2.LINE_AA, shift=2)
        return cv2.GaussianBlur(hole, (0, 0), 0.06 * PX)

    # ------------------------------------------------------------------ exact states
    def state(self, k, ripple=0, ripple_h=0.5):
        """maps with the first k unpick-list entries stitched.  ripple: the last `ripple` of them (the next to come
        out) are slackened - replayed with their height raised up to (1 + ripple_h) toward the unpick front."""
        k = int(np.clip(k, 0, self.n))
        r = int(min(ripple, k))
        ks = ((k - r) // self.snap_every) * self.snap_every
        if ks in self._snaps:
            st = {kk: (v.copy() if isinstance(v, np.ndarray) else v) for kk, v in self._snaps[ks].items()}
            self._snaps.move_to_end(ks)
        else:
            st = {kk: (v.copy() if isinstance(v, np.ndarray) else v) for kk, v in self._base.items()}
            if ks > 0:
                replay(st, self.rec, self.sel[:ks], self.bbox[0], self.bbox[1])
            self._snaps[ks] = {kk: (v.copy() if isinstance(v, np.ndarray) else v) for kk, v in st.items()}
            if len(self._snaps) > 3:
                self._snaps.popitem(last=False)
        if k - r > ks:
            replay(st, self.rec, self.sel[ks:k - r], self.bbox[0], self.bbox[1])
        if r > 0:
            t = (np.arange(r, dtype=np.float32) + 1) / r
            replay(st, self.rec, self.sel[k - r:k], self.bbox[0], self.bbox[1], hmul=(1 + ripple_h * t ** 1.5).astype(np.float32))
        return st

    def paste(self, m, st):
        f = int(round(self.PX0 / m['PX']))
        x0, y0, x1, y1 = self.bbox
        patch = {}
        for k in ('h', 'alb', 'T', 'mat', 'cov'):
            v = st[k]
            patch[k] = v if f == 1 else downsample_key(k, v, f)
        gh = self.ghost_ext if f == 1 else downsample_key('ghost', self.ghost_ext, f)
        ox = int(round(m['origin_mm'][0] * m['PX'])); oy = int(round(m['origin_mm'][1] * m['PX']))
        px0, py0 = x0 // f - ox, y0 // f - oy
        ph, pw = patch['h'].shape
        H, W = m['h'].shape
        a0, b0 = max(px0, 0), max(py0, 0)
        a1, b1 = min(px0 + pw, W), min(py0 + ph, H)
        if a1 <= a0 or b1 <= b0: return m
        for k, v in patch.items():
            m[k][b0:b1, a0:a1] = v[b0 - py0:b1 - py0, a0 - px0:a1 - px0]
        if 'ghost' in m:     # protected linen for apply_age: extend to the silhouette
            g = m['ghost'].astype(np.float32)
            g[b0:b1, a0:a1] = np.maximum(g[b0:b1, a0:a1], gh[b0 - py0:b1 - py0, a0 - px0:a1 - px0])
            m['ghost'] = g
        return m

    def edit(self, u, ripple=0, ripple_h=0.5):
        """frontal.render edit: u = entries REMOVED (0..n)."""
        def fn(m):
            rp = ripple if 0 < u < self.n else 0
            st = self.state(self.n - int(math.floor(u)), ripple=rp, ripple_h=ripple_h)
            self.paste(m, st)
        return fn

    # ------------------------------------------------------------------ threads (for loose ends)
    def threads(self, max_gap_mm=1.8):
        """chains of consecutive unpick entries (stitch-on order) that one needle walked: same region & kind and the
        next strand starts near the previous end.  Returns list of (i0, i1) index ranges into self.sel."""
        R = self.rec; PX = self.PX0
        out = []; i0 = 0
        def ends(k):
            p = R['P'][R['off'][k]:R['off'][k + 1]]
            return p[0] / PX, p[-1] / PX
        prev = None
        for i, k in enumerate(self.sel):
            ok = False
            if prev is not None and R['typ'][k] == 0 and R['typ'][prev] == 0 and R['region'][k] == R['region'][prev] \
                    and R['kind'][k] == R['kind'][prev] and R['kind'][k] not in COUCH:
                a, _ = ends(k); _, b = ends(prev)
                ok = np.hypot(*(a - b)) < max_gap_mm
            if not ok and i > 0:
                out.append((i0, i)); i0 = i
            prev = k
        out.append((i0, self.n))
        return out
