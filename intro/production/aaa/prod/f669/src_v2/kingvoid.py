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
import voidfx as VFX
import json as _json

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


def _blank(H, W, PX):
    return dict(h=np.full((H, W), -10.0, np.float32), alb=np.zeros((H, W, 3), np.float32), T=np.zeros((H, W, 2), np.float32),
                mat=np.zeros((H, W), np.uint8), cov=np.zeros((H, W), np.float32), sid=np.zeros((H, W), np.int32),
                sfr=np.zeros((H, W), np.float32), base=np.zeros((H, W), np.float32), stamp=np.zeros((H, W), np.int32), PX=PX)


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
        ins[idx] = SIL.inside_ragged(self.mids_mm[idx])
        king = R['group'] == gk
        gnd = R['group'] == 0
        order = R['order']
        rank = np.empty(len(order), np.int64); rank[order] = np.arange(len(order))
        self.keep = order[np.isin(order, np.nonzero(king & ~ins)[0])]          # throne pieces of the old king group
        # the grey blocks of the throne's inner padding that sat beside the head: unpicked too (ragged: ~85 %), not left as
        # flat polygons with a cut edge
        from chron.color import lin2oklab
        lab_ = lin2oklab(np.clip(R['fpar'][:, 3:6], 0, None)[None])[0]
        C_ = np.hypot(lab_[:, 1], lab_[:, 2]); h_ = np.degrees(np.arctan2(lab_[:, 2], lab_[:, 1])) % 360
        box = (mids[:, 0] > 2450) & (mids[:, 0] < 3450) & (mids[:, 1] > 1300) & (mids[:, 1] < 2000)
        grey = gnd & box & ~ins & (C_ < 0.065) & (h_ > 190) & (h_ < 320) & (lab_[:, 0] > 0.15) & (lab_[:, 0] < 0.78)
        grey &= np.array([VFX._hh(i, 91) < 0.92 for i in range(len(grey))])
        # a ragged unpicked border: the bake clipped the throne's stitch rows on the hint polygon (a ruler-straight edge);
        # a few stitches just outside the silhouette come out too, fewer with distance (cut-away ends, loose stitches)
        nib = np.zeros(len(mids), bool)
        cand = np.nonzero(gnd & ~ins & near)[0]
        if len(cand):
            dout = -SIL.signed_dist_mm(self.mids_mm[cand])
            pr = 0.70 * np.exp(-np.clip(dout, 0, None) / 1.8)
            hh = np.array([VFX._hh(int(i), 133) for i in cand])
            nib[cand[(dout < 4.0) & (hh < pr)]] = True
        self.debris = np.nonzero((gnd & ins) | grey | nib)[0]
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
    def _poly_band(self, x0w, y0w, H, W, PX, half_mm=1.15):
        """mask (0..1) of the bake's hint-polygon outlines (crown + king): the bake drew its underdrawing along them."""
        hints = _json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'lib', 'hints', 'p1_oath.json')))
        m = np.zeros((H, W), np.uint8)
        for g in hints['groups']:
            if g['name'] not in ('crown', 'king'): continue
            p = (np.array(g['poly'], np.float32) / 5.0 + 20.0) * PX - np.array([x0w, y0w], np.float32)
            cv2.polylines(m, [np.round(p * 4).astype(np.int32)], True, 1, int(round(2 * half_mm * PX)), cv2.LINE_AA, shift=2)
        return cv2.GaussianBlur(m.astype(np.float32), (0, 0), 0.25 * PX)

    def _build_base(self, verbose):
        G, R, PX = self.ground, self.rec, self.PX0
        x0, y0, x1, y1 = self.bbox
        M = 40
        ly = G.read_px(x0 - M, y0 - M, x1 + M, y1 + M, 0, keys=['ghost', 'ud', 'holes', 'pad'])
        H, W = y1 - y0 + 2 * M, x1 - x0 + 2 * M
        ox, oy = x0 - M, y0 - M
        lin = make_linen(H, W, PX, ox / PX, oy / PX, seed=LINEN_SEED)          # NOT flattened / protected: ages like the cloth
        sil = SIL.sil_mask(ox, oy, W, H, PX).astype(np.float32)
        self.ghost_ext = cv2.GaussianBlur(sil, (0, 0), 0.5 * PX)[M:-M, M:-M].copy()
        # --- underdrawing: the bake's contour drawing (face, beard, folds, hands) without its polygon-edge lines,
        # plus the traced flank lines; a pen line with pressure and breaks
        ud_b = ly['ud'].astype(np.float32) * (1 - np.clip(self._poly_band(ox, oy, H, W, PX) * 1.6, 0, 1))
        ud_s = SIL.draw_underdrawing(H, W, ox, oy, PX, seed=GHOST_SEED + 3)
        ud = np.maximum(ud_b, ud_s)
        ink_a = VFX.ink_alpha(ud, PX, seed=GHOST_SEED + 11, strength=1.0)
        a = np.clip(ink_a * (0.78 + 0.22 * cv2.GaussianBlur(sil, (0, 0), 2.0 * PX)), 0, 0.82)[..., None]
        amean = 0.4941
        ink = hex_lin('#5A2A1B')
        lin['alb'] = lin['alb'] * (1 - a) + (lin['alb'] * ink / (amean * 0.55)) * a
        # --- needle holes: entry / exit pairs at the real strand ends of everything unpicked here
        # no holes along the bake's hint-polygon edges (its clipped row ends line up there: a ruler-straight line of holes)
        hole, keep_h = VFX.holes_from_record(R, self.sel, PX, ox, oy, H, W, seed=GHOST_SEED + 21,
                                             exclude=(self._poly_band(ox, oy, H, W, PX, half_mm=0.8) > 0.35))
        # the crown ghost (above the head, y < 141 mm) keeps the bake's holes
        yy = (np.arange(H, dtype=np.float32) + oy) / PX
        top = (yy < 141.0)[:, None].astype(np.float32)
        hole = np.maximum(hole, ly['holes'].astype(np.float32) * top)
        # ragged border: the area the bleed holes thin out from is the silhouette displaced by cloth-scale noise
        gyy, gxx = np.mgrid[0:H, 0:W].astype(np.float32)
        nx_ = VFX.vnoise(ox / PX, oy / PX, H, W, PX, 7.0, 71, 2) * 3.0 * PX + VFX.vnoise(ox / PX, oy / PX, H, W, PX, 2.2, 72, 1) * 1.4 * PX
        ny_ = VFX.vnoise(ox / PX, oy / PX, H, W, PX, 7.0, 73, 2) * 3.0 * PX + VFX.vnoise(ox / PX, oy / PX, H, W, PX, 2.2, 74, 1) * 1.4 * PX
        sil_r = cv2.remap(sil, gxx + nx_, gyy + ny_, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        del gyy, gxx, nx_, ny_
        hole = np.maximum(hole, VFX.bleed_holes(sil_r, PX, seed=GHOST_SEED + 61, band_mm=7.5, tau=3.0))
        VFX.apply_holes(lin, hole, PX)
        # --- ghosted imprint of the dense stitching (compression of the weave, faint tone change)
        bl = _blank(H, W, PX)
        replay(bl, R, self.sel, ox, oy)
        cov = (bl['h'] > -5).astype(np.float32)
        hh = np.clip(np.where(cov > 0, bl['h'], 0.0), 0, 1.2)
        imp_h = cv2.GaussianBlur(hh, (0, 0), 0.13 * PX)
        imp_c = cv2.GaussianBlur(cov, (0, 0), 0.35 * PX)
        imk = float(os.environ.get('F669_IMPRINT', 1.0))
        lin['h'] = lin['h'] - 0.050 * imk * imp_h
        lin['alb'] = lin['alb'] * (1 - 0.060 * imk * imp_c[..., None])
        del bl, cov, hh
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
            print(f'[kingvoid] base rebuilt: {W - 2 * M}x{H - 2 * M} px, {len(gsel)} ground + {len(self.keep)} throne entries, {len(keep_h)} needle holes')
        return mm

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
