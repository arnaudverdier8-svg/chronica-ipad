"""Stitch synthesis on top of a maps dict (h, alb, T, mat, cov, sid, base, PX).
All public parameters in mm; converted to px with PX."""
import math
import numpy as np, cv2
from .strands import trace_region, raster_stitch, squeeze_along
from .core import WOOL, SILK, METAL, INK, LINEN, lin2oklab, oklab2lin

_SID = [1]
TAG = [None]
RECORD = None   # set to a list to record every stitch (for stitch-on / unpick replay)


def next_sid():
    _SID[0] += 1
    return _SID[0]


def ensure(m):
    H, W = m['h'].shape
    m.setdefault('sid', np.zeros((H, W), np.int32))
    m.setdefault('base', np.zeros((H, W), np.float32))
    m.setdefault('stamp', np.zeros((H, W), np.int32))
    return m


# ------------------------------------------------------------------ orientation fields
def orient_tensor(lum, sigma_g_px, sigma_t_px, mask=None):
    """Return (c2, s2, coherence) of the THREAD direction (perpendicular to dominant gradient), doubled-angle.
    If mask is given, normalized convolution inside the mask."""
    g = cv2.GaussianBlur(lum.astype(np.float32), (0, 0), sigma_g_px)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    Jxx, Jxy, Jyy = gx * gx, gx * gy, gy * gy
    if mask is not None:
        mk = mask.astype(np.float32)
        nb = cv2.GaussianBlur(mk, (0, 0), sigma_t_px) + 1e-6
        Jxx = cv2.GaussianBlur(Jxx * mk, (0, 0), sigma_t_px) / nb
        Jxy = cv2.GaussianBlur(Jxy * mk, (0, 0), sigma_t_px) / nb
        Jyy = cv2.GaussianBlur(Jyy * mk, (0, 0), sigma_t_px) / nb
    else:
        Jxx = cv2.GaussianBlur(Jxx, (0, 0), sigma_t_px); Jxy = cv2.GaussianBlur(Jxy, (0, 0), sigma_t_px)
        Jyy = cv2.GaussianBlur(Jyy, (0, 0), sigma_t_px)
    tr = Jxx + Jyy + 1e-9
    c2 = -(Jxx - Jyy); s2 = -2 * Jxy
    coh = np.sqrt(c2 * c2 + s2 * s2) / tr
    return c2.astype(np.float32), s2.astype(np.float32), coh.astype(np.float32)


def blend_fields(fields, weights):
    c = sum(w * f[0] / (np.sqrt(f[0] ** 2 + f[1] ** 2) + 1e-9) for f, w in zip(fields, weights))
    s = sum(w * f[1] / (np.sqrt(f[0] ** 2 + f[1] ** 2) + 1e-9) for f, w in zip(fields, weights))
    return c.astype(np.float32), s.astype(np.float32)


def const_field(shape, angle_deg):
    a = math.radians(angle_deg) * 2
    return np.full(shape, math.cos(a), np.float32), np.full(shape, math.sin(a), np.float32)


def perp_field(c2, s2):
    return (-c2).astype(np.float32), (-s2).astype(np.float32)


# ------------------------------------------------------------------ helpers
def smooth_poly(p, it=2):
    for _ in range(it):
        if len(p) < 3: return p
        q = p.copy(); q[1:-1] = 0.25 * p[:-2] + 0.5 * p[1:-1] + 0.25 * p[2:]
        p = q
    return p


def resample(p, step):
    seg = np.hypot(*np.diff(p, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)])
    if s[-1] < 1e-6: return p[:1]
    n = max(2, int(s[-1] / step) + 1)
    ss = np.linspace(0, s[-1], n)
    return np.stack([np.interp(ss, s, p[:, 0]), np.interp(ss, s, p[:, 1])], 1).astype(np.float32)


def streamlines(lab, rid, c2, s2, PX, pitch, maxlen, minlen, step=None, seed=0, dtest=0.55, maxturn_deg=50, cand_mask=None):
    """Evenly spaced streamlines in label region rid. Returns list of (n,2) float32 px polylines."""
    step_px = (step or pitch * 0.35) * PX
    m = (lab == rid) if cand_mask is None else cand_mask
    ys, xs = np.nonzero(m)
    if len(xs) == 0: return []
    pad = 3
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, lab.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, lab.shape[1])
    labc = np.ascontiguousarray(lab[y0:y1, x0:x1]).astype(np.int32)
    c2c = np.ascontiguousarray(c2[y0:y1, x0:x1]); s2c = np.ascontiguousarray(s2[y0:y1, x0:x1])
    r = np.random.default_rng(seed)
    idx = r.permutation(len(xs))[: max(64, len(xs) // 6)]
    cand = np.stack([xs[idx] - x0, ys[idx] - y0], 1).astype(np.float32) + r.uniform(-0.5, 0.5, (len(idx), 2)).astype(np.float32)
    area = len(xs)
    est = int(area / (pitch * PX) / step_px * 1.6) + 1000
    out_pts = np.zeros((est, 2), np.float32); out_off = np.zeros(est // 2 + 10, np.int64)
    nl, npt = trace_region(c2c, s2c, labc, int(rid), float(pitch * PX), float(pitch * PX * dtest), float(step_px),
                           float(maxlen * PX), float(minlen * PX), cand, out_pts, out_off, math.cos(math.radians(maxturn_deg)))
    off = np.array([x0, y0], np.float32)
    return [out_pts[out_off[i]:out_off[i + 1]] + off for i in range(nl)]


def cut_stitches(lines, PX, L, jit=0.25, gap=0.0, seed=0, stagger=True, overlap=0.0):
    """cut long streamlines into stitches of length L mm (+/- jit), random phase per line (brick stagger)."""
    r = np.random.default_rng(seed)
    out = []
    for p in lines:
        seg = np.hypot(*np.diff(p, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)]) / PX
        tot = s[-1]
        if tot < 0.3: continue
        pos = -r.uniform(0, L) if stagger else 0.0
        while pos < tot:
            l = L * (1 + r.uniform(-jit, jit))
            a, b = max(pos - overlap, 0), min(pos + l, tot)
            if b - a > 0.25 * L or (a == 0 and b == tot):
                ss = np.linspace(a, b, max(2, int((b - a) / 0.4) + 2))
                out.append(np.stack([np.interp(ss, s, p[:, 0]), np.interp(ss, s, p[:, 1])], 1).astype(np.float32))
            pos += l + gap * r.uniform(0.5, 1.5)
    return out


# ------------------------------------------------------------------ colour choice
class ShadeSet:
    """A limited set of thread shades for a region (dye lots), chosen stochastically per stitch."""

    def __init__(self, lab_cols, seed=0):
        self.lab = np.asarray(lab_cols, np.float32)
        self.lin = oklab2lin(self.lab)
        self.r = np.random.default_rng(seed)

    @staticmethod
    def from_pixels(lin_pixels, n, pull=None, pull_amt=0.35, seed=0, Lspread=1.0):
        lab = lin2oklab(lin_pixels.reshape(-1, 3))
        if len(lab) > 20000:
            lab = lab[np.random.default_rng(seed).permutation(len(lab))[:20000]]
        n = max(1, min(n, len(lab) // 20))
        Z = (lab * np.array([1, 1.5, 1.5], np.float32)).astype(np.float32)
        _, lb, cen = cv2.kmeans(Z, n, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-4), 2, cv2.KMEANS_PP_CENTERS)
        cen = cen / np.array([1, 1.5, 1.5], np.float32)
        if pull is not None:
            pl = lin2oklab(np.asarray(pull, np.float32).reshape(-1, 3))
            for i in range(len(cen)):
                d = np.hypot(pl[:, 1] - cen[i, 1], pl[:, 2] - cen[i, 2]) + 0.3 * np.abs(pl[:, 0] - cen[i, 0])
                k = int(np.argmin(d))
                cen[i, 1:] = cen[i, 1:] * (1 - pull_amt) + pl[k, 1:] * pull_amt
                cen[i, 0] = cen[i, 0] * (1 - 0.25 * pull_amt) + pl[k, 0] * 0.25 * pull_amt
        cen = cen[np.argsort(cen[:, 0])]
        return ShadeSet(cen, seed)

    def pick(self, lin_col, temp=0.6):
        """stochastic nearest-shade choice (2 nearest, weighted) -> linear rgb"""
        lab = lin2oklab(np.asarray(lin_col, np.float32)[None])[0]
        d = np.sqrt(((self.lab - lab) * np.array([1.0, 1.4, 1.4])) ** 2).sum(1)
        d = np.sqrt(((self.lab - lab) ** 2 * np.array([1.0, 2.0, 2.0])).sum(1))
        o = np.argsort(d)
        if len(o) == 1: return self.lin[o[0]]
        d0, d1 = d[o[0]], d[o[1]]
        p1 = (d0 / (d0 + d1 + 1e-6)) * temp * 2
        k = o[1] if self.r.random() < p1 * 0.5 else o[0]
        c = self.lin[k].copy()
        # per-strand dye jitter: L +/-4.5 %, C +/- 8 %, h +/- 3 deg
        lab2 = self.lab[k].copy()
        lab2[0] *= 1 + self.r.uniform(-0.045, 0.045)
        cs = 1 + self.r.uniform(-0.08, 0.08); hrot = math.radians(self.r.uniform(-3, 3))
        a, b = lab2[1] * cs, lab2[2] * cs
        lab2[1] = a * math.cos(hrot) - b * math.sin(hrot); lab2[2] = a * math.sin(hrot) + b * math.cos(hrot)
        return oklab2lin(lab2[None])[0]


def sample_col(src_lin_blur, p):
    """mean colour of source along a stitch polyline (px coords in source map space)."""
    H, W, _ = src_lin_blur.shape
    q = p[:: max(1, len(p) // 6)]
    xi = np.clip(np.round(q[:, 0]).astype(int), 0, W - 1); yi = np.clip(np.round(q[:, 1]).astype(int), 0, H - 1)
    return src_lin_blur[yi, xi].mean(0)


# ------------------------------------------------------------------ rasterising helpers
def put(m, p, col, r_mm, h0, hamp, matid=WOOL, ply_mm=0.7, ply_deg=32, taper_mm=0.5, tw_deg=20, seed=0, cov=1.0, hbias=0.0, sid=None,
        pexp=None):
    PX = m['PX']
    sid = next_sid() if sid is None else sid
    if RECORD is not None:
        RECORD.append((np.array(p, np.float32), np.array(col, np.float32), r_mm, h0, hamp, matid, ply_mm, ply_deg, taper_mm, tw_deg,
                       seed, cov, hbias, sid, pexp, m.get('_oxy', (0, 0)), TAG[0]))
    raster_stitch(m['h'], m['alb'], m['T'], m['mat'], m['cov'], m['sid'], m['base'], np.ascontiguousarray(p, np.float32),
                  float(r_mm * PX), float(h0), float(hamp), float(col[0]), float(col[1]), float(col[2]), int(matid),
                  float(ply_mm * PX), float(math.tan(math.radians(ply_deg))), float(taper_mm * PX), int(sid), int(seed),
                  float(math.radians(tw_deg)), float(PX), float(cov), float(hbias),
                  float(pexp if pexp is not None else (0.5 if matid == METAL else 0.42)))
    return sid


def extend_ends(p, ext_px):
    if len(p) < 2 or ext_px <= 0: return p
    d0 = p[0] - p[min(2, len(p) - 1)]; d0 /= (np.linalg.norm(d0) + 1e-6)
    d1 = p[-1] - p[max(-3, -len(p))]; d1 /= (np.linalg.norm(d1) + 1e-6)
    return np.vstack([p[0] + d0 * ext_px, p, p[-1] + d1 * ext_px]).astype(np.float32)


def _raster_lines(m, sts, src_blur, shades, PX, pitch, L, seed, matid, h0, hamp, r_fac, tw_deg, ply_mm, taper, cov, hbias,
                  colfn, order_shuffle=True):
    r = np.random.default_rng(seed + 2)
    order = r.permutation(len(sts)) if order_shuffle else np.arange(len(sts))
    for i in order:
        p = sts[i]
        src = sample_col(src_blur, p)
        col = shades.pick(src) if shades is not None else src
        if colfn is not None: col = colfn(col, p)
        rr = r_fac * pitch * (1 + r.uniform(-0.12, 0.12))
        put(m, p, col, rr, h0, hamp * (1 + r.uniform(-0.1, 0.1)), matid, ply_mm=ply_mm, taper_mm=min(taper, 0.3 * L if L else taper),
            tw_deg=tw_deg, seed=seed, cov=cov, hbias=hbias)


def fill_region(m, lab, rid, field, src_blur, shades, PX, style='laid', pitch=0.8, L=None, seed=0, matid=WOOL,
                couch=None, maxlen=70, minlen=0.8, h0=0.05, hamp=0.42, r_fac=0.58, tw_deg=20, ply_mm=0.7, taper=0.5,
                order_shuffle=True, cov=1.0, hbias=0.0, colfn=None, ext=0.35, gapfill=True):
    """Fill a labelled region with strands. style: 'laid' (full-length strands) or 'split' (cut into stitches of L mm)."""
    c2, s2 = field
    lines = streamlines(lab, rid, c2, s2, PX, pitch, maxlen, minlen, seed=seed)
    lines = [extend_ends(smooth_poly(resample(p, 0.3 * PX), 2), ext * pitch * PX) for p in lines if len(p) >= 2]
    if style == 'split':
        sts = cut_stitches(lines, PX, L or 3.0, jit=0.3, seed=seed + 1, overlap=0.25 * pitch)
    else:
        sts = lines
    kw = dict(seed=seed, matid=matid, h0=h0, hamp=hamp, r_fac=r_fac, tw_deg=tw_deg, ply_mm=ply_mm, taper=taper, cov=cov,
              hbias=hbias, colfn=colfn)
    _raster_lines(m, sts, src_blur, shades, PX, pitch, L, **kw)
    if gapfill:
        mk = lab == rid
        unc = (mk & (m['mat'] == 0)).astype(np.uint8)
        unc = cv2.morphologyEx(unc, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        if unc.sum() > 2 * (pitch * PX) ** 2:
            lab2 = np.where((cv2.dilate(unc, np.ones((5, 5), np.uint8)) > 0) & mk, rid, -1).astype(np.int32)
            l2 = streamlines(lab2, rid, c2, s2, PX, pitch * 0.85, min(maxlen, 6.0), 0.25, seed=seed + 9, dtest=0.5)
            l2 = [extend_ends(smooth_poly(resample(p, 0.3 * PX), 1), 0.5 * pitch * PX) for p in l2 if len(p) >= 2]
            if style == 'split':
                l2 = cut_stitches(l2, PX, L or 3.0, jit=0.3, seed=seed + 3)
            kw2 = dict(kw); kw2['seed'] = seed + 17; kw2['hbias'] = hbias - 0.05
            _raster_lines(m, l2, src_blur, shades, PX, pitch, L, **kw2)
    if couch is not None:
        couch_region(m, lab, rid, field, src_blur, shades, PX, seed=seed + 5, **couch)
    return lines


def couch_region(m, lab, rid, field, src_blur, shades, PX, spacing=4.5, tie=4.0, r_mm=0.42, seed=0, colmul=1.0, h0=0.42,
                 hamp=0.36, tie_col=None, matid=WOOL):
    """Bayeux couching bars perpendicular to the laid strands + tie-downs. Bars of the same yarn."""
    c2, s2 = perp_field(*field)
    # bars: evenly spaced streamlines of the perpendicular field at `spacing`
    bars = streamlines(lab, rid, c2, s2, PX, spacing, 200, 1.5, step=0.4, seed=seed, dtest=0.7, maxturn_deg=25)
    r = np.random.default_rng(seed)
    for p in bars:
        p = smooth_poly(resample(p, 0.4 * PX), 4)
        # straighten (couching bars are pulled taut) : blend with chord
        if len(p) > 3:
            t = np.linspace(0, 1, len(p))[:, None]
            chord = p[0] * (1 - t) + p[-1] * t
            p = (0.55 * p + 0.45 * chord).astype(np.float32)
        # slight angle/bow jitter
        p = p + r.normal(0, 0.06 * PX, 2).astype(np.float32)
        p = p.astype(np.float32)
        src = sample_col(src_blur, p)
        col = (shades.pick(src) if shades is not None else src) * colmul
        stamp_id = next_sid()
        squeeze_along(m['h'], m['mat'], m['stamp'], stamp_id, p, float(0.95 * PX), 0.30, int(matid))
        # bar ends tuck in: shorten a bit
        put(m, p, col, r_mm, h0, hamp, matid, ply_mm=0.7, taper_mm=0.6, tw_deg=20, seed=seed, hbias=0.3)
        # tie-downs along the bar
        seg = np.hypot(*np.diff(p, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)]) / PX
        pos = r.uniform(0.3, 1.0) * tie
        while pos < s[-1] - 0.5:
            i = np.searchsorted(s, pos)
            i = min(max(i, 1), len(p) - 1)
            d = p[i] - p[i - 1]; d /= (np.linalg.norm(d) + 1e-6)
            n = np.array([-d[1], d[0]], np.float32)
            c = np.array([np.interp(pos, s, p[:, 0]), np.interp(pos, s, p[:, 1])], np.float32)
            a = math.radians(r.uniform(-12, 12)); nn = np.array([n[0] * math.cos(a) - n[1] * math.sin(a), n[0] * math.sin(a) + n[1] * math.cos(a)], np.float32)
            q = np.stack([c - nn * 0.75 * PX, c + nn * 0.75 * PX]).astype(np.float32)
            tc = col * 0.92 if tie_col is None else tie_col
            put(m, q, tc, 0.2, h0 + hamp * 0.75, 0.12, matid, ply_mm=0.5, taper_mm=0.25, tw_deg=0, seed=seed, hbias=0.5)
            pos += tie * (1 + r.uniform(-0.25, 0.25))
    return bars


def stem_path(m, poly_px, col, PX, L=3.5, width=1.3, h0=0.55, hamp=0.45, seed=0, matid=WOOL, slant_deg=13, base_ok=True):
    """Stem / outline stitch rope along a polyline (px). Overlapping slanted stitches advancing L/2."""
    r = np.random.default_rng(seed)
    p = resample(poly_px, 0.25 * PX)
    if len(p) < 2: return
    seg = np.hypot(*np.diff(p, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)]) / PX
    def P(x):
        x = np.clip(x, 0, s[-1]); return np.array([np.interp(x, s, p[:, 0]), np.interp(x, s, p[:, 1])], np.float32)
    s0 = r.uniform(0, L / 2) * 0
    off = width * 0.22
    rad = width * 0.36
    while s0 < s[-1] - 0.3:
        l = L * (1 + r.uniform(-0.18, 0.18))
        a, b = P(s0), P(min(s0 + l, s[-1]))
        t = (b - a); ln = np.linalg.norm(t) + 1e-6; t /= ln; n = np.array([-t[1], t[0]], np.float32)
        A = a - n * off * PX + r.normal(0, 0.06 * PX, 2); B = b + n * off * PX + r.normal(0, 0.06 * PX, 2)
        mid = P(s0 + l / 2) + (r.normal(0, 0.04 * PX, 2))
        q = np.stack([A, 0.5 * (A + B) * 0.5 + mid * 0.5, B]).astype(np.float32)
        q = resample(q, 0.3 * PX)
        c = col * (1 + r.uniform(-0.06, 0.06))
        put(m, q, c, rad * (1 + r.uniform(-0.08, 0.08)), h0, hamp, matid, ply_mm=0.7, ply_deg=32, taper_mm=0.55, tw_deg=15,
            seed=seed, hbias=0.2)
        s0 += l / 2


def mask_contours(mask, PX, min_len_mm=3.0, simplify_mm=0.15):
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in cs:
        c = c[:, 0, :].astype(np.float32)
        if len(c) < 3: continue
        c = np.vstack([c, c[:1]])
        ln = np.hypot(*np.diff(c, axis=0).T).sum() / PX
        if ln < min_len_mm: continue
        out.append(smooth_poly(resample(c, 0.5 * PX), 3))
    return out


def pad_dome(mask, PX, height, radius_mm):
    """stumpwork / padded satin dome from a mask: rounded profile reaching `height` mm at radius_mm in from the edge."""
    d = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5) / PX
    t = np.clip(d / radius_mm, 0, 1)
    return (height * np.sqrt(1 - (1 - t) ** 2)).astype(np.float32)


def metal_couch(m, lab, rid, field, PX, pitch=1.0, thread_r=0.24, tie=2.6, tie_col=None, seed=0, h0=0.45, hamp=0.32,
                col=None, tarnish=None):
    """underside-couched silver-gilt: pairs of metal threads following the field, tied every ~2.6 mm with coloured silk."""
    c2, s2 = field
    lines = streamlines(lab, rid, c2, s2, PX, pitch, 120, 0.8, seed=seed, dtest=0.6)
    r = np.random.default_rng(seed)
    gold = col if col is not None else np.array([0.815, 0.515, 0.141], np.float32)
    tie_col = tie_col if tie_col is not None else np.array([0.32, 0.06, 0.04], np.float32)
    for p in lines:
        p = smooth_poly(resample(p, 0.3 * PX), 2)
        if len(p) < 2: continue
        seg = np.diff(p, axis=0); ln = np.hypot(*seg.T) + 1e-6
        nrm = np.stack([-seg[:, 1] / ln, seg[:, 0] / ln], 1); nrm = np.vstack([nrm, nrm[-1:]])
        for k, o in enumerate((-0.25, 0.25)):
            q = (p + nrm * o * pitch * PX).astype(np.float32)
            g = gold * (1 + r.uniform(-0.08, 0.05))
            if tarnish is not None and r.random() < tarnish:
                g = g * np.array([0.55, 0.5, 0.45], np.float32)
            put(m, q, g, thread_r, h0, hamp, METAL, ply_mm=0.33, ply_deg=62, taper_mm=0.3, tw_deg=55, seed=seed + k, cov=0.0, hbias=0.05)
        # tie-downs
        s = np.concatenate([[0], np.cumsum(ln)]) / PX
        pos = r.uniform(0, tie)
        while pos < s[-1]:
            i = min(max(np.searchsorted(s, pos), 1), len(p) - 1)
            n = nrm[i - 1]
            c = np.array([np.interp(pos, s, p[:, 0]), np.interp(pos, s, p[:, 1])], np.float32)
            q = np.stack([c - n * 0.55 * pitch * PX, c + n * 0.55 * pitch * PX]).astype(np.float32)
            put(m, q, tie_col * (1 + r.uniform(-0.1, 0.1)), 0.13, h0 + hamp * 0.8, 0.06, SILK, ply_mm=0.3, taper_mm=0.15, tw_deg=0,
                seed=seed, cov=0.0, hbias=0.3)
            pos += tie * (1 + r.uniform(-0.2, 0.2)) * (1 if (int(pos / tie) % 2 == 0) else 1.0)
    return lines


def cord_path(m, poly_px, col, PX, width=1.2, h0=0.45, hamp=0.5, seed=0, tie=3.2, tie_col=None, matid=WOOL):
    """Couched 2-ply cord: one continuous twisted rope along the path, tied down every ~tie mm."""
    r = np.random.default_rng(seed)
    p = resample(poly_px, 0.3 * PX)
    if len(p) < 2: return
    p = (p + np.stack([smooth_noise1(len(p), 6, r), smooth_noise1(len(p), 6, r)], 1) * 0.05 * PX).astype(np.float32)
    rad = width * 0.5
    # two plies twisted: strong ply modulation (period ~ 1.3 x width), 38 deg
    put(m, p, col, rad, h0, hamp, matid, ply_mm=1.3 * width, ply_deg=38, taper_mm=0.4, tw_deg=38, seed=seed, hbias=0.25,
        pexp=0.5)
    seg = np.hypot(*np.diff(p, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)]) / PX
    pos = r.uniform(0.3, 1.0) * tie
    tc = col * 0.8 if tie_col is None else tie_col
    while pos < s[-1] - 0.3:
        i = min(max(np.searchsorted(s, pos), 1), len(p) - 1)
        d = p[i] - p[i - 1]; d /= (np.linalg.norm(d) + 1e-6)
        n = np.array([-d[1], d[0]], np.float32)
        c = np.array([np.interp(pos, s, p[:, 0]), np.interp(pos, s, p[:, 1])], np.float32)
        q = np.stack([c - n * (rad + 0.25) * PX + d * 0.2 * PX, c + n * (rad + 0.25) * PX - d * 0.2 * PX]).astype(np.float32)
        put(m, q, tc, 0.16, h0 + hamp * 0.9, 0.08, matid, ply_mm=0.4, taper_mm=0.2, tw_deg=0, seed=seed, hbias=0.6, cov=0.5)
        pos += tie * (1 + r.uniform(-0.2, 0.2))


def smooth_noise1(n, scale, r):
    g = r.standard_normal(int(n / scale) + 3)
    return np.interp(np.arange(n) / scale, np.arange(len(g)), g).astype(np.float32)
