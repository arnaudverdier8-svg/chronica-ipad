"""Canvas: a kit sheet under construction.  Live raster into analytic linen with the stitch RECORD on, an occupancy
mask for front-to-back occlusion, linen-level layers (underdrawing, needle holes, hem, nail holes), and the final
write: needle-path order -> exact replay into fresh linen -> MapSet (+ optional _ground sheet without some groups,
with their ghost), exactly the contract of aaa/lib (same as motifs/panel.py).

Elements are processed FRONT TO BACK: every fill / outline is clipped by what nearer elements already occupy, then the
element adds its occluder silhouette (canvas.occlude).  Coordinates: sheet mm (origin top-left, y down), canvas px =
mm * PX."""
import os, json, time, math
import numpy as np, cv2
from . import geom as G
from chron import stitch as S
from chron.stitch import Record, CTX
from chron.color import hex_lin, lin2oklab, oklab2lin, ShadeSet, pal
from chron.linen import make_linen
from chron.record import replay, needle_order, apply_flips, blank_like, OUTLINE_REGION
from chron.maps import MapSet
from chron.ageing import bake_age_layers
from chron.config import WOOL, SILK, METAL, LINEN
from chron.util import vnoise


def colour(c):
    """hex '#RRGGBB' | palette role name | linear rgb -> linear rgb float32."""
    if isinstance(c, str):
        return hex_lin(c) if c.startswith('#') else pal(c)
    return np.asarray(c, np.float32)


def chroma_cap(lin, cap):
    lab = lin2oklab(np.asarray(lin, np.float32)[None])[0]
    C = math.hypot(lab[1], lab[2])
    if C > cap:
        lab[1] *= cap / C; lab[2] *= cap / C
    return oklab2lin(lab[None])[0]


def lots(c, n=3, spread=0.055, seed=0, cap=None):
    """dye lots around a colour (OKLab L spread, small hue / chroma drift)."""
    c = colour(c)
    if cap is not None:
        c = chroma_cap(c, cap)
    lab = lin2oklab(c[None])[0]
    r = np.random.default_rng(seed)
    out = []
    for k in range(n):
        t = (k - (n - 1) / 2) / max((n - 1) / 2, 1)
        l2 = lab.copy()
        l2[0] *= 1 + spread * t
        cs = 1 + r.uniform(-0.05, 0.05); a = math.radians(r.uniform(-2.5, 2.5))
        A, B = l2[1] * cs, l2[2] * cs
        l2[1] = A * math.cos(a) - B * math.sin(a); l2[2] = A * math.sin(a) + B * math.cos(a)
        out.append(l2)
    return np.array(out, np.float32)


class Canvas:
    def __init__(self, w_mm, h_mm, PX=10.0, seed=7, linen_seed=0, name='kit', frieze_origin_mm=(0.0, 0.0), verbose=True):
        self.PX = float(PX)
        self.W, self.H = int(round(w_mm * PX)), int(round(h_mm * PX))
        self.w_mm, self.h_mm = self.W / PX, self.H / PX
        self.seed = seed; self.linen_seed = linen_seed; self.name = name
        self.frieze_origin_mm = tuple(frieze_origin_mm)
        self.verbose = verbose
        self.t0 = time.time()
        self.m = make_linen(self.H, self.W, PX, 0.0, 0.0, seed=linen_seed)
        S.ensure(self.m)
        self.occ = np.zeros((self.H, self.W), bool)
        self.ud = np.zeros((self.H, self.W), np.float32)          # underdrawing (0..1)
        self.linen_ops = []                                       # callables(lin_maps) applied to the final linen
        self.rec = Record(); S.REC = self.rec; S.reset_sid(1)
        CTX['gmap'] = None; CTX['group'] = 0; CTX['region'] = 0; CTX['unit'] = -1
        self.groups = ['ground']
        self.group_policy = {}
        self.regions = {}
        self._rid = 0
        self.log = []

    # ------------------------------------------------------------------ bookkeeping
    def group(self, name, policy='region'):
        if name is None or name == 'ground':
            return 0
        if name not in self.groups:
            self.groups.append(name)
            self.group_policy[len(self.groups) - 1] = policy
        return self.groups.index(name)

    def new_region(self, info):
        self._rid += 1
        if self._rid >= 65000:
            raise RuntimeError('too many regions')
        self.regions[self._rid] = info
        return self._rid

    def say(self, *a):
        if self.verbose:
            print(f'[kit {self.name} {time.time() - self.t0:6.1f}s]', *a, flush=True)

    # ------------------------------------------------------------------ windows / masks
    def win_px(self, x0, y0, x1, y1, pad_px=0):
        return (max(int(math.floor(x0)) - pad_px, 0), max(int(math.floor(y0)) - pad_px, 0),
                min(int(math.ceil(x1)) + pad_px, self.W), min(int(math.ceil(y1)) + pad_px, self.H))

    def win_of_polys(self, polys_mm, pad_mm=4.0):
        P = np.vstack([np.asarray(p, np.float32) for p in polys_mm]) * self.PX
        return self.win_px(P[:, 0].min(), P[:, 1].min(), P[:, 0].max(), P[:, 1].max(), int(pad_mm * self.PX))

    def mask(self, polys_mm, win):
        x0, y0, x1, y1 = win
        return G.fill_poly((y1 - y0, x1 - x0), [np.asarray(p, np.float32) * self.PX - np.array([x0, y0], np.float32) for p in polys_mm])

    def occlude(self, mask_win, win):
        x0, y0, x1, y1 = win
        self.occ[y0:y1, x0:x1] |= mask_win.astype(bool)

    def occlude_polys(self, polys_mm, pad_mm=0.0):
        win = self.win_of_polys(polys_mm, 2.0)
        mk = self.mask(polys_mm, win)
        if pad_mm > 0:
            k = max(1, int(pad_mm * self.PX))
            mk = cv2.dilate(mk, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1)))
        self.occlude(mk, win)

    # ------------------------------------------------------------------ stitching
    def paint(self, col, win, seed, lot_mm=60.0, amp=0.025, mask=None, model=0.0, grad=0.0, edge_mm=1.8):
        """the 'source' colour image sampled per strand: base colour with dye-lot patches (+/-2.5 % L over 5-20 cm),
        plus optional tonal modelling: `model` darkens toward the region edge (needle-painting depth, as in the
        re-embroidered panels), `grad` darkens toward the bottom of the region."""
        x0, y0, x1, y1 = win
        h, w = y1 - y0, x1 - x0
        nz = vnoise(x0 / self.PX, y0 / self.PX, h, w, self.PX, lot_mm, seed + 31, 2)
        nz = np.tanh(nz * 4.0)          # fairly sharp lot boundaries
        f = 1 + amp * nz
        if mask is not None and (model > 0 or grad != 0):
            mk = mask.astype(np.uint8)
            if model > 0:
                dt = cv2.distanceTransform(mk, cv2.DIST_L2, 5) / self.PX
                f = f * (1 - model * np.exp(-dt / edge_mm))
            if grad != 0:
                ys = np.nonzero(mk.any(1))[0]
                if len(ys) > 1:
                    yy = (np.arange(h, dtype=np.float32) - 0.5 * (ys[0] + ys[-1])) / max(0.5 * (ys[-1] - ys[0]), 1.0)
                    f = f * (1 - grad * np.clip(yy, -1, 1))[:, None]
        return (colour(col)[None, None, :] * f[..., None]).astype(np.float32)

    def fill(self, mask_win, win, col, style='laid', field=None, angle=0.0, axis_bend=0.0, couch=True, pitch=0.85, L=None,
             matid=WOOL, h0=0.05, hamp=0.42, seed=0, erode=(0.30, 0.50), nlots=3, lot_spread=0.06, group=None, cov=1.0,
             bar_spacing=4.5, tie=4.0, r_fac=0.58, maxlen=70, tw_deg=20, ply_mm=0.7, bmul=0.0, hbias=0.0, bar_col=None,
             tie_col=None, bar_field=None, bar_jitter=0.0, cap=0.13, clip=True, name='', maxturn_deg=50, minlen=0.8,
             occlude=False, min_area_mm2=0.6, gapfill=True, shades=None, model=0.10, grad=0.05):
        """fill one region (mask in window px) with laid (+ couched) or split work."""
        x0, y0, x1, y1 = win
        mk = mask_win.astype(bool).copy()
        if clip:
            mk &= ~self.occ[y0:y1, x0:x1]
        if occlude:
            full = mk.copy()
        if erode:
            dt = cv2.distanceTransform(mk.astype(np.uint8), cv2.DIST_L2, 5) / self.PX
            nz = vnoise(x0 / self.PX, y0 / self.PX, y1 - y0, x1 - x0, self.PX, 5.0, seed + 5, 2)
            mk = dt > (erode[0] + erode[1] * np.clip(0.5 + 1.4 * nz, 0, 1))
        if mk.sum() < min_area_mm2 * self.PX * self.PX:
            return None
        gid = self.group(group) if isinstance(group, (str, type(None))) else int(group)
        rid = self.new_region(dict(name=name, group=gid, style=style))
        lab = np.where(mk, rid, -1).astype(np.int32)
        if field is None:
            if axis_bend > 0:
                from chron.fields import region_axis_field
                field = region_axis_field(mk, self.PX, angle, axis_bend, 30.0, seed, (x0 / self.PX, y0 / self.PX))
            else:
                field = G.const_field(mk.shape, angle)
        sub = S.view(self.m, x0, y0, x1, y1)
        sb = self.paint(col, win, seed, mask=mk, model=model, grad=grad)
        if shades is None:
            if model > 0 or grad:
                nl = max(nlots, 5); sp = max(lot_spread, 0.5 * (model + abs(grad)) + 0.03)
            else:
                nl, sp = nlots, lot_spread
            shd = ShadeSet(lots(col, nl, sp, seed, cap), seed)
        else:
            shd = ShadeSet(np.vstack([lots(c, 1, 0, seed + i, cap) for i, c in enumerate(shades)]), seed)
        CTX['region'] = rid; CTX['group'] = gid; CTX['unit'] = -1
        cpl = None
        if couch:
            cpl = dict(spacing=bar_spacing, tie=tie)
            if isinstance(couch, dict):
                cpl.update(couch)
            if bar_col is not None:
                cpl['bar_col'] = colour(bar_col)
            if tie_col is not None:
                cpl['tie_col'] = colour(tie_col)
            if bar_field is not None:
                cpl['bar_field'] = bar_field
            if bar_jitter:
                cpl['jitter_deg'] = bar_jitter
        S.fill_region(sub, lab, rid, field, sb, shd, self.PX, style=style, pitch=pitch, L=L, seed=seed, matid=matid,
                      couch=cpl, h0=h0, hamp=hamp, r_fac=r_fac, maxlen=maxlen, tw_deg=tw_deg, ply_mm=ply_mm, cov=cov,
                      bmul=bmul, hbias=hbias, maxturn_deg=maxturn_deg, minlen=minlen, gapfill=gapfill)
        CTX['region'] = 0
        if occlude:
            self.occlude(full, win)
        return rid

    def ink_near(self, path_px, rad_px=6):
        """mean albedo of what is already stitched around a canvas-px path (for hue-dependent outline inks)."""
        p = np.asarray(path_px, np.float32)[::3]
        xi = np.clip(np.round(p[:, 0]).astype(int), rad_px, self.W - rad_px - 1)
        yi = np.clip(np.round(p[:, 1]).astype(int), rad_px, self.H - rad_px - 1)
        acc, n = np.zeros(3, np.float32), 0
        for dx in (-rad_px, 0, rad_px):
            for dy in (-rad_px, 0, rad_px):
                sel = self.m['mat'][yi + dy, xi + dx] > 0
                if sel.any():
                    acc += self.m['alb'][yi[sel] + dy, xi[sel] + dx].sum(0); n += int(sel.sum())
        return acc / n if n else None

    def outline(self, path_px, col='#22232F', width=1.2, L=3.3, h0=0.5, hamp=0.42, seed=0, group=None, clip=True,
                cov=0.5, mix=None, min_len_mm=1.2, slant=13):
        """stem-stitch outline along a canvas-px polyline (clipped by nearer elements)."""
        p = np.asarray(path_px, np.float32)
        if len(p) < 2:
            return
        c = colour(col)
        if mix is not None:
            c = c * 0.8 + colour(mix) * 0.2
        runs = G.clip_path(p, self.occ, int(min_len_mm * self.PX)) if clip else [p]
        gid = self.group(group) if isinstance(group, (str, type(None))) else int(group)
        CTX['region'] = OUTLINE_REGION; CTX['group'] = gid
        for k, r in enumerate(runs):
            S.stem_path(self.m, r, c, self.PX, L=L, width=width, h0=h0, hamp=hamp, seed=seed * 7 + k, cov=cov, slant_deg=slant)
        CTX['region'] = 0

    def outline_mm(self, path_mm, *a, **k):
        self.outline(np.asarray(path_mm, np.float32) * self.PX, *a, **k)

    def boundary_outlines(self, lab_win, win, col='#22232F', width=1.1, L=3.0, seed=0, group=None, min_len_px=8,
                          inner=True, outer=True, col_fn=None, h0=0.5, hamp=0.42):
        """stem outlines along the boundaries of a label image (0 = empty): inner boundaries between parts and the
        outer silhouette, each traced once (skeleton of the boundary band)."""
        from chron.skel import skeleton_paths, merge_paths
        x0, y0, x1, y1 = win
        L_ = lab_win
        b = np.zeros(L_.shape, bool)
        dx = L_[:, 1:] != L_[:, :-1]; dy = L_[1:, :] != L_[:-1, :]
        if not inner:
            dx &= (L_[:, 1:] == 0) | (L_[:, :-1] == 0); dy &= (L_[1:, :] == 0) | (L_[:-1, :] == 0)
        if not outer:
            dx &= (L_[:, 1:] != 0) & (L_[:, :-1] != 0); dy &= (L_[1:, :] != 0) & (L_[:-1, :] != 0)
        b[:, 1:] |= dx; b[:, :-1] |= dx; b[1:, :] |= dy; b[:-1, :] |= dy
        b = cv2.dilate(b.astype(np.uint8), np.ones((2, 2), np.uint8))
        paths, _ = skeleton_paths(b, 3)
        paths = merge_paths(paths, 0.25 * self.PX)
        n = 0
        for i, p in enumerate(paths):
            p = S.smooth_poly(S.resample(p.astype(np.float32), 0.3 * self.PX), 3)
            if G.arclen(p)[-1] < min_len_px:
                continue
            pc = p + np.array([x0, y0], np.float32)
            c = col if col_fn is None else col_fn(pc)
            self.outline(pc, c, width=width, L=L, seed=seed * 131 + i, group=group, h0=h0, hamp=hamp)
            n += 1
        return n

    def underdraw(self, path_mm, alpha=0.8, width_mm=0.42, seed=0, jitter_mm=0.12, clip=True):
        r = np.random.default_rng(seed)
        q = G.resample(np.asarray(path_mm, np.float32), 0.3) + r.normal(0, jitter_mm, 2).astype(np.float32)
        if len(q) < 2:
            return
        q = G.wobble(q, 0.12, 6.0, seed)
        runs = G.clip_path(q * self.PX, self.occ, 4) if clip else [q * self.PX]
        for run in runs:
            cv2.polylines(self.ud, [np.round(run * 4).astype(np.int32)], False, float(alpha), max(1, int(round(width_mm * self.PX))),
                          cv2.LINE_AA, shift=2)

    def put_path(self, path_mm, col, r_mm, h0, hamp, matid=WOOL, group=None, region=0, kind=None, **kw):
        gid = self.group(group) if isinstance(group, (str, type(None))) else int(group)
        CTX['group'] = gid; CTX['region'] = region
        p = np.asarray(path_mm, np.float32) * self.PX
        sid = S.put(self.m, p, colour(col), r_mm, h0, hamp, matid, kind=kind, **kw)
        CTX['region'] = 0
        return sid

    def metal_pair(self, path_mm, ties_s_mm=(), tie_col='#CC3A2C', group=None, gold=None, sep_mm=0.5, thread_r=0.24, seed=0,
                   h0=0.45, hamp=0.32, tie_len_mm=1.15, tie_r=0.16, ply_mm=0.33, ply_deg=62, tw_deg=55, tie_h=0.85):
        """the couched pair of silver-gilt threads along a path (mm), tied down with coloured silk at arc positions."""
        p = G.resample(np.asarray(path_mm, np.float32), 0.3)
        nrm = G.normals(p)
        gold = colour(gold) if gold is not None else np.array([0.815, 0.515, 0.141], np.float32)
        gid = self.group(group) if isinstance(group, (str, type(None))) else int(group)
        rid = self.new_region(dict(name='metal_pair', group=gid))
        CTX['group'] = gid; CTX['region'] = rid
        r = np.random.default_rng(seed)
        CTX['unit'] = S.next_sid()
        for k, o in enumerate((-0.5, 0.5)):
            q = ((p + nrm * o * sep_mm) * self.PX).astype(np.float32)
            g = gold * (1 + r.uniform(-0.05, 0.04))
            S.put(self.m, q, g, thread_r, h0, hamp, METAL, ply_mm=ply_mm, ply_deg=ply_deg, taper_mm=0.6, tw_deg=tw_deg, seed=seed + k, cov=0.0,
                  hbias=0.05, kind=S.K_METAL)
        s = G.arclen(p)
        for st in ties_s_mm:
            i = int(np.clip(np.searchsorted(s, st), 1, len(p) - 1))
            n = nrm[i]; c = p[i]
            a = math.radians(r.uniform(-8, 8)); n2 = np.array([n[0] * math.cos(a) - n[1] * math.sin(a), n[0] * math.sin(a) + n[1] * math.cos(a)])
            q = (np.stack([c - n2 * tie_len_mm / 2, c + n2 * tie_len_mm / 2]) * self.PX).astype(np.float32)
            S.put(self.m, q, colour(tie_col), tie_r, h0 + hamp * tie_h, 0.08, SILK, ply_mm=0.3, taper_mm=0.15, tw_deg=0, seed=seed,
                  cov=0.0, hbias=0.35, kind=S.K_MTIE)
        CTX['unit'] = -1; CTX['region'] = 0
        return p

    # ------------------------------------------------------------------ linen-level features (applied to the final linen)
    def needle_holes(self, pts_mm, r_mm=(0.17, 0.26), seed=0, lip=0.07, depth=0.28):
        pts = np.asarray(pts_mm, np.float32).reshape(-1, 2)
        PX = self.PX

        def op(lin, pts=pts, seed=seed):
            r = np.random.default_rng(seed)
            hole = np.zeros(lin['h'].shape, np.float32)
            for p in pts:
                rad = r.uniform(*r_mm) * PX
                cv2.circle(hole, (int(round(p[0] * PX * 4)), int(round(p[1] * PX * 4))), max(1, int(round(rad * 4))), 1.0, -1,
                           cv2.LINE_AA, shift=2)
            hole = cv2.GaussianBlur(hole, (0, 0), 0.06 * PX)
            rim = np.clip(cv2.GaussianBlur(hole, (0, 0), 0.22 * PX) * 1.7 - hole, 0, 1)
            lin['h'] -= depth * hole - lip * rim
            lin['alb'] *= (1 - 0.55 * hole[..., None]) * (1 + 0.05 * rim[..., None])
            lin.setdefault('_holes', np.zeros_like(hole))
            lin['_holes'] = np.maximum(lin['_holes'], hole)
        self.linen_ops.append(op)

    def nail_hole(self, x_mm, y_mm, seed=0, r_mm=0.75, halo_mm=3.2):
        PX = self.PX

        def op(lin, x=x_mm, y=y_mm, seed=seed):
            H, W = lin['h'].shape
            R = int(halo_mm * 3 * PX)
            cx, cy = int(x * PX), int(y * PX)
            xa, ya, xb, yb = max(cx - R, 0), max(cy - R, 0), min(cx + R, W), min(cy + R, H)
            if xb <= xa or yb <= ya:
                return
            yy, xx = np.mgrid[ya:yb, xa:xb].astype(np.float32)
            nz = vnoise(xa / PX, ya / PX, yb - ya, xb - xa, PX, 1.2, seed, 3)
            d = np.hypot(xx - x * PX, yy - y * PX) / PX * (1 + 0.35 * nz)
            hole = np.clip((r_mm - d) / 0.15, 0, 1)
            halo = np.exp(-(d / halo_mm) ** 2) * (1 - hole) * (0.75 + 0.5 * nz)
            rust = hex_lin('#7A4A22')
            a = np.clip(halo * 0.55, 0, 0.6)[..., None]
            al = lin['alb'][ya:yb, xa:xb]
            al[:] = al * (1 - a) + (al * rust / (al.mean() + 1e-3) * 0.85) * a
            al[:] = al * (1 - 0.82 * hole[..., None]) + hex_lin('#2A1A10') * 0.25 * hole[..., None]
            ring = np.exp(-((d - r_mm - 0.25) / 0.3) ** 2)
            lin['h'][ya:yb, xa:xb] += -0.5 * hole + 0.18 * ring
        self.linen_ops.append(op)

    def hem(self, y_fold_mm, y_edge_mm=0.0, seed=0, run_y_mm=None, run_col='#CDB990'):
        """turned and stitched top hem: double linen between the edge and the fold line (raised, slightly cooler and
        cleaner), a soft roll at the edge, a sunk line at the fold, and a running stitch in linen thread."""
        PX = self.PX

        def op(lin, yf=y_fold_mm, ye=y_edge_mm):
            H, W = lin['h'].shape
            ys = (np.arange(H, dtype=np.float32) + 0.5) / PX
            nz = vnoise(0, 0, 1, W, PX, 40.0, seed + 3, 2)[0]
            yfx = yf + 0.6 * nz
            Y = ys[:, None]
            inside = np.clip((yfx[None, :] - Y) / 0.5, 0, 1) * np.clip((Y - ye) / 0.3, 0, 1)
            roll = np.exp(-((Y - ye - 1.2) / 1.4) ** 2)
            fold = np.exp(-((Y - yfx[None, :] - 0.15) / 0.35) ** 2)
            lin['h'] += (0.32 * inside + 0.25 * roll * inside - 0.22 * fold).astype(np.float32)
            lin['alb'] *= (1 + 0.025 * inside - 0.10 * fold)[..., None].astype(np.float32)
        self.linen_ops.append(op)
        if run_y_mm is not None:
            r = np.random.default_rng(seed + 9)
            x = r.uniform(0, 3)
            CTX['region'] = OUTLINE_REGION; CTX['group'] = 0
            while x < self.w_mm:
                l = 3.2 * (1 + r.uniform(-0.15, 0.15))
                yy = run_y_mm + r.normal(0, 0.08)
                q = np.array([[x, yy], [x + l, yy + r.normal(0, 0.06)]], np.float32) * PX
                S.put(self.m, q, colour(run_col) * (1 + r.uniform(-0.04, 0.04)), 0.28, 0.40, 0.22, WOOL, ply_mm=0.6, taper_mm=0.4,
                      tw_deg=10, seed=seed, cov=0.25, hbias=0.1, kind=S.K_STEM)
                x += l + 2.6 * (1 + r.uniform(-0.2, 0.2))
            CTX['region'] = 0

    # ------------------------------------------------------------------ final
    def finish(self, out_dir, sheet=None, ground_without=(), meta=None, age_density=0.3, tide=None):
        """needle order -> replay into fresh linen (+ linen ops + underdrawing) -> MapSet(s)."""
        sheet = sheet or self.name
        PX = self.PX
        S.REC = None
        pad_map = self.m['base'].copy()
        R = self.rec.arrays(); R['PX'] = np.float32(PX)
        self.say(f'{len(R["typ"])} record entries, {self._rid} regions; ordering')
        del self.m, self.rec
        gorder = list(range(len(self.groups)))
        ordr, flips = needle_order(R, gorder, self.group_policy, {})
        apply_flips(R, ordr, flips)
        rank = np.full(len(R['typ']), -1, np.int64); rank[ordr] = np.arange(len(ordr))
        R['order'] = ordr; R['rank'] = rank
        lin = make_linen(self.H, self.W, PX, 0.0, 0.0, seed=self.linen_seed)
        for op in self.linen_ops:
            op(lin)
        holes = lin.pop('_holes', np.zeros((self.H, self.W), np.float32))
        # underdrawing (red-brown, no relief) under everything
        ud = cv2.GaussianBlur(self.ud, (0, 0), sigmaX=0.10 * PX, sigmaY=0.08 * PX)
        ud *= (0.8 + 0.4 * np.random.default_rng(self.seed + 3).random(ud.shape).astype(np.float32))
        ud = np.clip(ud, 0, 1)
        ink = hex_lin('#6E3326')
        a = np.clip(ud * 0.72, 0, 0.62)[..., None]
        lin['alb'] = lin['alb'] * (1 - a) + (lin['alb'] * ink / (lin['alb'].mean() + 1e-3) * 0.9) * a
        del a
        self.ud = None
        gm = np.zeros((self.H, self.W), bool)
        gsel_groups = [self.groups.index(g) for g in ground_without if g in self.groups]
        age = bake_age_layers((self.H, self.W), PX, seed=self.seed + 7, density=age_density, margin_px=0, tide=tide)
        n = len(ordr)
        R['P'] = np.ascontiguousarray(R['P'], np.float32)
        sid2idx = np.zeros(int(R['ipar'][:, 2].max()) + 2, np.int32) - 1
        sid2idx[R['ipar'][:, 2]] = np.arange(len(R['typ']))
        extra = dict(age_fox=age['fox'], age_tide=age['tide'], age_fade=age['fade'], ud=ud, holes=holes, pad=pad_map,
                     ghost=gm.astype(np.float32), gpoly=np.zeros((self.H, self.W), np.float32))
        extra = {k: v.astype(np.float16) for k, v in extra.items()}
        del age
        meta_common = dict(kit='bkit', sheet=sheet, linen_seed=self.linen_seed, groups=self.groups, seed=self.seed,
                           frieze_origin_mm=list(self.frieze_origin_mm), regions=self._rid)
        meta_common.update(meta or {})

        def final_maps(sel, base_lin):
            mm = blank_like(base_lin)
            mm['base'] = pad_map
            replay(mm, R, sel, 0, 0)
            del mm['stamp'], mm['base']
            return mm

        def write(maps, name, sel):
            sidm = maps['sid']
            idx = sid2idx[np.clip(sidm, 0, len(sid2idx) - 1)]
            has = (sidm > 0) & (idx >= 0)
            ih = idx[has]
            reg = np.zeros(sidm.shape, np.uint16); grp = np.zeros(sidm.shape, np.uint8); birth = np.zeros(sidm.shape, np.float16)
            reg[has] = np.clip(R['region'][ih], 0, 65535); grp[has] = R['group'][ih]
            birth[has] = ((rank[ih] + maps['sfr'][has]) / max(n, 1)).astype(np.float16)
            del idx, ih, has, maps['sfr']
            maps['reg'] = reg; maps['grp'] = grp; maps['birth'] = birth
            path = os.path.join(out_dir, name)
            MapSet.write(path, maps, meta=dict(meta_common, sheet=name, stitched=int(len(sel))), extra_layers=extra,
                         verbose=self.verbose)
            np.savez_compressed(os.path.join(path, 'stitches.npz'), **{k: v for k, v in R.items()})
            json.dump(dict(groups=self.groups, group_counts={g: int((R['group'] == i).sum()) for i, g in enumerate(self.groups)},
                           n=int(n), sheet_canvas_px=[self.W, self.H], regions=self._rid, built_s=round(time.time() - self.t0, 1),
                           region_info={int(k): v for k, v in list(self.regions.items())}),
                      open(os.path.join(path, 'groups.json'), 'w'), indent=0)
            return path
        self.say('replay full')
        import gc
        full = final_maps(ordr, lin)
        p_full = write(full, sheet, ordr)
        del full
        gc.collect()
        out = [p_full]
        if gsel_groups:
            from chron.motifs.panel import _ghost
            sel_g = np.nonzero(np.isin(R['group'], gsel_groups))[0]
            gmask = np.zeros((self.H, self.W), np.uint8)
            for k in sel_g[R['typ'][sel_g] == 0]:
                p = R['P'][R['off'][k]:R['off'][k + 1]]
                cv2.polylines(gmask, [np.round(p).astype(np.int32)], False, 1, max(1, int(R['fpar'][k, 0] * PX * 2 + 2)))
            gmask = cv2.morphologyEx(gmask, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8)) > 0
            lin2 = lin                      # in place: the full sheet is already written
            layers = _ghost(lin2, R, sel_g, gmask, [], PX, seed=self.seed + 5)
            extra['ghost'] = gmask.astype(np.float16)
            extra['holes'] = np.maximum(holes, layers['holes']).astype(np.float16)
            sel_ground = ordr[~np.isin(R['group'][ordr], gsel_groups)]
            gr = final_maps(sel_ground, lin2)
            out.append(write(gr, sheet + '_ground', sel_ground))
            del gr, lin2
        self.say('written', out)
        return out
