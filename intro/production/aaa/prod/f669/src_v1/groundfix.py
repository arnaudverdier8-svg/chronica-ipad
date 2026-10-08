"""Static ground repairs for p1' (S09), rebuilt from first principles like kingvoid.py (linen + ghost + replay):

  * goblet / stitched-candle ghosts: the bake protected (flattened, un-yellowed) the linen over the whole hint
    POLYGON, which shows as pale rectangles under the raking candle.  Rebuilt here with the protection following the
    real stitched footprint of each group (its record entries rasterised, closed by 0.8 mm).
  * goblet_1 (left of the red lord): its hint polygon missed the cup, so the bowl stayed stitched in the ground.  Its
    ground entries are removed here (needle holes at their strand ends, underdrawing of its outline, as for the rest).

Patches are built once and pasted into every window by edit(m)."""
import json, os
import numpy as np, cv2
from chron.record import replay, bbox_of, blank_like
from chron.maps import downsample_key
from chron.linen import make_linen
from chron.color import hex_lin
from chron.stitch import K_TIE, K_MTIE, K_CTIE, K_SPLIT
from kingvoid import entry_geometry, LINEN_SEED, GHOST_SEED

# goblet_1 bowl (sheet mm box) - its ground entries are removed
BOWL_BOX = (132.5, 242.0, 151.5, 261.8)
GROUPS = ['goblet_0', 'goblet_1', 'goblet_2', 'goblet_3', 'candle_0', 'candle_1', 'candle_2', 'candle_3']


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
        bx = BOWL_BOX
        self.bowl = np.nonzero((R['group'] == 0) & (mm[:, 0] > bx[0]) & (mm[:, 0] < bx[2]) & (mm[:, 1] > bx[1]) & (mm[:, 1] < bx[3]))[0]
        self.patches = []
        self.all_ids = np.nonzero(np.isin(R['group'], [names.index(g) for g in GROUPS]))[0]
        for g in GROUPS:
            gi = names.index(g)
            ids = np.nonzero(R['group'] == gi)[0]
            rem = self.bowl if g == 'goblet_1' else np.zeros(0, np.int64)
            b = bbox_of(R, np.concatenate([ids, rem]), int(4 * PX))
            x0, y0, x1, y1 = b
            x0 -= x0 % 8; y0 -= y0 % 8; x1 += (-x1) % 8; y1 += (-y1) % 8
            self.patches.append(self._build((x0, y0, x1, y1), ids, rem, g))
        if verbose:
            print(f'[groundfix] {len(self.patches)} ghost patches rebuilt; goblet_1 bowl entries removed: {len(self.bowl)}')

    def _build(self, bbox, gids, rem, name):
        G, R, PX = self.ground, self.rec, self.PX0
        x0, y0, x1, y1 = bbox
        M = 40
        H, W = y1 - y0 + 2 * M, x1 - x0 + 2 * M
        ly = G.read_px(x0 - M, y0 - M, x1 + M, y1 + M, 0, keys=['ghost', 'ud', 'holes', 'pad'])
        # true footprint of the group (+ removed bowl)
        fp = _blank(H, W, PX)
        bb = self._bb; pad = 30
        hit = (bb[:, 2] > x0 - M - pad) & (bb[:, 0] < x1 + M + pad) & (bb[:, 3] > y0 - M - pad) & (bb[:, 1] < y1 + M + pad)
        fids = self.all_ids[hit[self.all_ids]]
        replay(fp, R, np.concatenate([fids, rem]).astype(np.int64), x0 - M, y0 - M)
        foot = (fp['h'] > -5).astype(np.uint8)
        foot = cv2.morphologyEx(foot, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(1.6 * PX) | 1,) * 2))
        foot = cv2.dilate(foot, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(0.8 * PX) | 1,) * 2)).astype(np.float32)
        gm = np.minimum(ly['ghost'].astype(np.float32), 1.0) * foot
        if len(rem):
            fr = _blank(H, W, PX); replay(fr, R, rem.astype(np.int64), x0 - M, y0 - M)
            fb = cv2.morphologyEx((fr['h'] > -5).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8)).astype(np.float32)
            gm = np.maximum(gm, fb)
        else:
            fb = None
        lin = make_linen(H, W, PX, (x0 - M) / PX, (y0 - M) / PX, seed=LINEN_SEED)
        s = cv2.GaussianBlur(gm, (0, 0), 0.4 * PX)
        lin['h'] = np.where(lin['h'] > 0, lin['h'] * (1 - 0.30 * s), lin['h']).astype(np.float32)
        ud = ly['ud'].astype(np.float32)
        if fb is not None:          # underdrawing of the bowl's outline
            cnts, _ = cv2.findContours(fb.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            u2 = np.zeros_like(ud)
            for c in cnts:
                if len(c) > 20:
                    cv2.polylines(u2, [c], True, 0.8, max(1, int(round(0.42 * PX))), cv2.LINE_AA)
            ud = np.maximum(ud, cv2.GaussianBlur(u2, (0, 0), 0.1 * PX))
        a = np.clip(ud * 0.72, 0, 0.6)[..., None]
        lin['alb'] = lin['alb'] * (1 - a) + (lin['alb'] * hex_lin('#6E3326') / (0.4941 + 1e-3) * 0.9) * a
        hole = ly['holes'].astype(np.float32)
        if len(rem):
            hole = np.maximum(hole, self._holes(rem, hole, x0 - M, y0 - M))
        rim = np.clip(cv2.GaussianBlur(hole, (0, 0), 0.22 * PX) * 1.7 - hole, 0, 1)
        lin['h'] = lin['h'] - 0.28 * hole + 0.07 * rim
        lin['alb'] = lin['alb'] * (1 - 0.5 * hole[..., None]) * (1 + 0.06 * rim[..., None])
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
        rs = np.zeros(len(R['typ']), bool); rs[rem] = True
        sel = order[(R['group'][order] == 0) & hit[order] & ~rs[order]]
        replay(mm, R, sel, x0, y0)
        # feather the ghost (age protection) so no hard edge remains
        gh = 0.6 * cv2.GaussianBlur(gm, (0, 0), 0.6 * PX)[M:-M, M:-M]
        return dict(bbox=bbox, st={k: mm[k] for k in ('h', 'alb', 'T', 'mat', 'cov')}, ghost=gh, name=name)

    def _holes(self, ids, hole_old, ox, oy):
        R, PX = self.rec, self.PX0
        H, W = hole_old.shape
        rr = np.random.default_rng(GHOST_SEED + 91)
        occ = cv2.dilate((hole_old > 0.3).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
        pts = []
        for k in ids:
            if R['typ'][k] != 0 or R['kind'][k] in (K_TIE, K_MTIE, K_CTIE): continue
            if R['kind'][k] == K_SPLIT and (k % 3) != 0: continue
            p = R['P'][R['off'][k]:R['off'][k + 1]]
            pts += [p[0], p[-1]]
        hole = np.zeros((H, W), np.float32)
        if not pts: return hole
        pts = np.array(pts, np.float32) - np.array([ox, oy], np.float32)
        pts = pts[rr.permutation(len(pts))]
        cell = 1.05 * PX; grid = {}
        for p in pts:
            if not (0 <= p[0] < W and 0 <= p[1] < H) or occ[int(p[1]), int(p[0])]: continue
            gx, gy = int(p[0] / cell), int(p[1] / cell)
            if any((q := grid.get((gx + dx, gy + dy))) is not None and (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 < cell * cell
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                continue
            grid[(gx, gy)] = p
            cv2.circle(hole, (int(round(p[0] * 4)), int(round(p[1] * 4))), max(1, int(round(rr.uniform(0.17, 0.26) * PX * 4))), 1.0, -1,
                       cv2.LINE_AA, shift=2)
        return cv2.GaussianBlur(hole, (0, 0), 0.06 * PX)

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
            if 'ghost' in m:
                g = p['ghost'] if f == 1 else downsample_key('ghost', p['ghost'], f)
                gg = m['ghost'].astype(np.float32)
                gg[b0:b1, a0:a1] = g[b0 - py0:b1 - py0, a0 - px0:a1 - px0]
                m['ghost'] = gg
        return m
