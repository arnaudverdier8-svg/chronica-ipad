"""Static ground repairs for p1' (S09), rebuilt from first principles like kingvoid.py (analytic linen + replay of the
record), v2:

  * goblet / stitched-candle ghosts: cup, candle, holder reduced to needle holes (entry / exit pairs at the real strand
    ends) and a pen-pressure underdrawing of their own outline.  NO flattened / protected linen any more: the bake's
    hint-polygon 'ghost' read as pale rectangles and is gone (the window is read without the ghost channel).
  * candle_1 / candle_2: the bake's hint rectangles also swallowed the green lord's robe, belt and hand behind them
    (a hard-edged pale rectangle).  Those background entries (darker than L 0.62, above the flame line) are put back
    into the ground; only the candle itself (wax, flame, holder) is unpicked.
  * goblet_1: its hint polygon missed the cup: the bowl's ground entries are removed too.
  * crown tips: the bake's tent polygon clipped the crown's side prongs, which stayed stitched in the ground like small
    brown thorns beside the lifted crown.  They are unpicked here (holes + underdrawing) and added to the crown slip.

Patches are built once and pasted into every window by edit(m)."""
import json, os
import numpy as np, cv2
from chron.record import replay, bbox_of, blank_like
from chron.maps import downsample_key
from chron.linen import make_linen
from chron.color import hex_lin, lin2oklab
from chron.stitch import K_TIE, K_MTIE, K_CTIE, K_SPLIT
from kingvoid import entry_geometry, LINEN_SEED, GHOST_SEED
import voidfx as VFX

BOWL_BOX = (132.5, 242.0, 151.5, 261.8)         # goblet_1 bowl (sheet mm) - ground entries removed
GROUPS = ['goblet_0', 'goblet_1', 'goblet_2', 'goblet_3', 'candle_0', 'candle_1', 'candle_2', 'candle_3']
CUP0_BOX = (69.0, 245.0, 90.0, 267.5)           # goblet_0's cup (the bake's hint polygon missed it; it merged into the gold lord's torso region)

# group entries that are NOT the subject (neighbouring embroidery caught by the bake's hint rectangles) go back into the ground
def _dseg(x, y, a, b):
    """distance (mm) of points to the segment a-b."""
    a = np.asarray(a, float); b = np.asarray(b, float); d = b - a
    t = np.clip(((x - a[0]) * d[0] + (y - a[1]) * d[1]) / (d @ d), 0, 1)
    return np.hypot(x - (a[0] + t * d[0]), y - (a[1] + t * d[1]))


def _rules():
    return {
        'candle_1': lambda x, y, L, C, h: (L < 0.62) & (y < 256.8),            # the green lord's robe / belt behind the flame
        'candle_2': lambda x, y, L, C, h: (L < 0.62) & (y < 255.2),
        'goblet_0': lambda x, y, L, C, h: (y > 282.8) | (_dseg(x, y, (99.0, 272.0), (71.6, 296.0)) < 2.6),   # the tan strap running down-left from the sword: the bake's polygon cut it
        'goblet_1': lambda x, y, L, C, h: (x < 136.8) | (y > 283.3) | ((h > 200) & (h < 300) & (L < 0.4)),   # loaf end, plate rim
    }
# crown prong stubs left in the ground (sheet mm boxes) minus the banner chevron's outline ends
TIP_BOXES = [(272.5, 280.5, 111.0, 124.5), (280.5, 289.0, 110.0, 118.5), (301.5, 310.0, 110.0, 118.0), (310.5, 319.5, 113.0, 124.5)]
TIP_EXCLUDE = [30249, 30250, 30251, 30252, 30216, 30217, 30218]


def _blank(H, W, PX):
    return dict(h=np.full((H, W), -10.0, np.float32), alb=np.zeros((H, W, 3), np.float32), T=np.zeros((H, W, 2), np.float32),
                mat=np.zeros((H, W), np.uint8), cov=np.zeros((H, W), np.float32), sid=np.zeros((H, W), np.int32),
                sfr=np.zeros((H, W), np.float32), base=np.zeros((H, W), np.float32), stamp=np.zeros((H, W), np.int32), PX=PX)


class GroundFix:
    def __init__(self, ground, verbose=True):
        G = self.ground = ground
        R = self.rec = G.stitches()
        PX = self.PX0 = float(R['PX'])
        names = json.load(open(os.path.join(G.path, 'groups.json')))['groups']
        mids, bb = entry_geometry(R)
        self._bb = bb
        mm = mids / PX
        self.mm = mm
        bx = BOWL_BOX
        self.bowl = np.nonzero((R['group'] == 0) & (mm[:, 0] > bx[0]) & (mm[:, 0] < bx[2]) & (mm[:, 1] > bx[1]) & (mm[:, 1] < bx[3]))[0]
        self.cup0 = self._cup_entries(R, mm, PX, CUP0_BOX)
        self.extra = {'goblet_1': self.bowl, 'goblet_0': self.cup0}
        # background entries of the candle groups that go back into the ground
        col = np.clip(R['fpar'][:, 3:6], 0, None)
        lab = lin2oklab(col[None])[0]
        Lk = lab[:, 0]; Ck = np.hypot(lab[:, 1], lab[:, 2]); Hk = np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360
        rest = []
        for g, rule in _rules().items():
            sel = np.nonzero(R['group'] == names.index(g))[0]
            rest.append(sel[rule(mm[sel, 0], mm[sel, 1], Lk[sel], Ck[sel], Hk[sel])])
        self.restore = np.concatenate(rest).astype(np.int64)
        tip = np.zeros(len(R['typ']), bool)
        for x0, x1, y0, y1 in TIP_BOXES:
            tip |= (mm[:, 0] > x0) & (mm[:, 0] < x1) & (mm[:, 1] > y0) & (mm[:, 1] < y1)
        tip &= (R['group'] == 0)
        tip[TIP_EXCLUDE] = False
        self.tips = np.nonzero(tip)[0].astype(np.int64)
        self.all_ids = np.nonzero(np.isin(R['group'], [names.index(g) for g in GROUPS]))[0]
        # everything unpicked by the static ghosts: group subjects (minus the restored background) + bowl + crown tips
        rs = np.zeros(len(R['typ']), bool); rs[self.restore] = True
        self.subject = np.concatenate([self.all_ids[~rs[self.all_ids]], self.bowl, self.cup0, self.tips]).astype(np.int64)
        self.patches = []
        for g in GROUPS:
            ids = np.nonzero(R['group'] == names.index(g))[0]
            rem = self.extra.get(g, np.zeros(0, np.int64))
            b = bbox_of(R, np.concatenate([ids, rem]), int(4 * PX))
            self.patches.append(self._build(self._snap(b), g))
        b = bbox_of(R, self.tips, int(4 * PX))
        self.patches.append(self._build(self._snap(b), 'crown_tips'))
        if verbose:
            print(f'[groundfix] {len(self.patches)} ghost patches; bowl {len(self.bowl)}, cup0 {len(self.cup0)}, restored background {len(self.restore)}, crown tips {len(self.tips)}')

    @staticmethod
    def _cup_entries(R, mm, PX, box):
        """ground entries of a cup that is not its own region: the closed loop of its outline strands is filled, and every ground
        entry whose midpoint lies inside it (any region) goes, plus the outline strands."""
        gnd = R['group'] == 0
        inb = gnd & (mm[:, 0] > box[0]) & (mm[:, 0] < box[2]) & (mm[:, 1] > box[1]) & (mm[:, 1] < box[3])
        out = np.nonzero(inb & (R['region'] == 65535))[0]
        x0, y0 = int((box[0] - 6) * PX), int((box[1] - 6) * PX); x1, y1 = int((box[2] + 6) * PX), int((box[3] + 6) * PX)
        H, W = y1 - y0, x1 - x0
        fp = _blank(H, W, PX); replay(fp, R, out, x0, y0)
        m = (fp['h'] > -5).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(2.4 * PX) | 1,) * 2))
        ff = m.copy(); msk = np.zeros((H + 2, W + 2), np.uint8); cv2.floodFill(ff, msk, (0, 0), 2)
        filled = ((ff != 2) | (m > 0)).astype(np.uint8)
        filled = cv2.dilate(filled, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(0.6 * PX) | 1,) * 2))
        cand = np.nonzero(gnd & (mm[:, 0] > box[0] - 3) & (mm[:, 0] < box[2] + 3) & (mm[:, 1] > box[1] - 3) & (mm[:, 1] < box[3] + 3))[0]
        px = np.clip((mm[cand, 0] * PX - x0).astype(int), 0, W - 1); py = np.clip((mm[cand, 1] * PX - y0).astype(int), 0, H - 1)
        ids = cand[filled[py, px] > 0]
        return np.unique(np.concatenate([ids, out])).astype(np.int64)

    @staticmethod
    def _snap(b):
        x0, y0, x1, y1 = b
        x0 -= x0 % 8; y0 -= y0 % 8; x1 += (-x1) % 8; y1 += (-y1) % 8
        return (x0, y0, x1, y1)

    def _build(self, bbox, name):
        G, R, PX = self.ground, self.rec, self.PX0
        rem = self.extra.get(name, np.zeros(0, np.int64))
        x0, y0, x1, y1 = bbox
        M = 40
        H, W = y1 - y0 + 2 * M, x1 - x0 + 2 * M
        ox, oy = x0 - M, y0 - M
        ly = G.read_px(ox, oy, x1 + M, y1 + M, 0, keys=['ud', 'pad'])
        bb = self._bb; pad = 30
        hit = (bb[:, 2] > ox - pad) & (bb[:, 0] < x1 + M + pad) & (bb[:, 3] > oy - pad) & (bb[:, 1] < y1 + M + pad)
        subj = self.subject[hit[self.subject]]
        # footprint of everything unpicked in this window -> where the bake's underdrawing is kept
        fp = _blank(H, W, PX)
        replay(fp, R, subj, ox, oy)
        foot = (fp['h'] > -5).astype(np.uint8)
        foot = cv2.morphologyEx(foot, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(1.6 * PX) | 1,) * 2))
        foot = cv2.dilate(foot, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(1.8 * PX) | 1,) * 2)).astype(np.float32)
        foot = cv2.GaussianBlur(foot, (0, 0), 0.35 * PX)
        lin = make_linen(H, W, PX, ox / PX, oy / PX, seed=LINEN_SEED)
        ud = ly['ud'].astype(np.float32) * foot
        if len(rem):      # the removed cup / bowl's outline
            fb = _blank(H, W, PX); replay(fb, R, rem, ox, oy)
            fbm = cv2.morphologyEx((fb['h'] > -5).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
            cnts, _ = cv2.findContours(fbm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            u2 = np.zeros_like(ud)
            for c in cnts:
                if len(c) > 20:
                    cv2.polylines(u2, [c], True, 0.8, max(1, int(round(0.42 * PX))), cv2.LINE_AA)
            ud = np.maximum(ud, cv2.GaussianBlur(u2, (0, 0), 0.1 * PX))
        ink_a = VFX.ink_alpha(ud, PX, seed=GHOST_SEED + 31, strength=0.95)
        a = np.clip(ink_a * 0.9, 0, 0.8)[..., None]
        ink = hex_lin('#5A2A1B')
        lin['alb'] = lin['alb'] * (1 - a) + (lin['alb'] * ink / (0.4941 * 0.55)) * a
        hole, _ = VFX.holes_from_record(R, subj, PX, ox, oy, H, W, seed=GHOST_SEED + 41)
        VFX.apply_holes(lin, hole, PX, deep=False)          # outside the pool: the v2 hole depth
        for k in ('h', 'alb', 'T', 'cov'):
            lin[k] = lin[k].astype(np.float16)
        for k in ('h', 'alb', 'T', 'mat', 'cov'):
            lin[k] = lin[k][M:-M, M:-M]
        lin['origin_mm'] = (x0 / PX, y0 / PX)
        mm_ = blank_like(lin)
        mm_['base'] = ly['pad'][M:-M, M:-M].astype(np.float32)
        hit2 = (bb[:, 2] > x0 - pad) & (bb[:, 0] < x1 + pad) & (bb[:, 3] > y0 - pad) & (bb[:, 1] < y1 + pad)
        order = R['order']
        gone = np.zeros(len(R['typ']), bool); gone[self.subject] = True
        keepg = np.zeros(len(R['typ']), bool); keepg[self.restore] = True
        sel = order[((R['group'][order] == 0) | keepg[order]) & hit2[order] & ~gone[order]]
        replay(mm_, R, sel, x0, y0)
        return dict(bbox=bbox, st={k: mm_[k] for k in ('h', 'alb', 'T', 'mat', 'cov')}, name=name)

    def edit(self, m):
        f = int(round(self.PX0 / m['PX']))
        ox = int(round(m['origin_mm'][0] * m['PX'])); oy = int(round(m['origin_mm'][1] * m['PX']))
        H, W = m['h'].shape
        for p in self.patches:
            x0, y0, x1, y1 = p['bbox']
            px0, py0 = x0 // f - ox, y0 // f - oy
            pw, ph = (x1 - x0) // f, (y1 - y0) // f
            a0, b0 = max(px0, 0), max(py0, 0)
            a1, b1 = min(px0 + pw, W), min(py0 + ph, H)
            if a1 <= a0 or b1 <= b0: continue
            for k, v in p['st'].items():
                vv = v if f == 1 else downsample_key(k, v, f)
                m[k][b0:b1, a0:a1] = vv[b0 - py0:b1 - py0, a0 - px0:a1 - px0]
        return m
