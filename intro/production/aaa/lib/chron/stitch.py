"""Stitch synthesis on a maps dict (h, alb, T, mat, cov, sid, sfr, base, stamp, PX) + the stitch RECORD.
All public parameters in mm; converted to px with PX.  (<- R25 stitch.py)

Every stitch is recorded (when REC is set) with absolute canvas px coordinates, its full raster parameters and
context (region, kind, group, unit) so that any subset can be replayed exactly in any order (stitch-on, unpick,
slips).  Couching squeezes are recorded as events (typ 1) inside the bar's unit."""
import math
import numpy as np, cv2
from .strands import trace_region, raster_stitch, squeeze_along
from .config import WOOL, SILK, METAL, INK, LINEN, CORD
from .color import ShadeSet
from .util import smooth_noise1

# stitch kinds (record 'kind')
K_LAID, K_SPLIT, K_BAR, K_TIE, K_STEM, K_METAL, K_MTIE, K_CORD, K_CTIE, K_SATIN, K_SQUEEZE, K_MISC = range(12)
KIND_NAMES = ['laid', 'split', 'bar', 'tie', 'stem', 'metal', 'metal_tie', 'cord', 'cord_tie', 'satin', 'squeeze', 'misc']

_SID = [1]
CTX = dict(region=0, group=0, unit=-1, kind=K_MISC, gmap=None)
REC = None   # set to Record() to record


def next_sid():
    _SID[0] += 1
    return _SID[0]


def reset_sid(v=1):
    _SID[0] = v


class Record:
    def __init__(self):
        self.P, self.typ, self.fpar, self.ipar, self.meta = [], [], [], [], []

    def __len__(self):
        return len(self.typ)

    def add(self, pts_abs, typ, fpar, ipar, meta):
        self.P.append(np.asarray(pts_abs, np.float32)); self.typ.append(typ)
        self.fpar.append(fpar); self.ipar.append(ipar); self.meta.append(meta)

    def arrays(self):
        n = len(self.typ)
        lens = np.array([len(p) for p in self.P], np.int64)
        off = np.zeros(n + 1, np.int64); off[1:] = np.cumsum(lens)
        meta = np.array(self.meta, np.int32).reshape(n, 4)
        return dict(P=np.concatenate(self.P).astype(np.float32) if n else np.zeros((0, 2), np.float32), off=off,
                    typ=np.array(self.typ, np.int8), fpar=np.array(self.fpar, np.float32).reshape(n, 14),
                    ipar=np.array(self.ipar, np.int32).reshape(n, 3), region=meta[:, 0], kind=meta[:, 1],
                    group=meta[:, 2], unit=meta[:, 3])


def ensure(m):
    H, W = m['h'].shape
    m.setdefault('sid', np.zeros((H, W), np.int32))
    m.setdefault('sfr', np.zeros((H, W), np.float32))
    m.setdefault('base', np.zeros((H, W), np.float32))
    m.setdefault('stamp', np.zeros((H, W), np.int32))
    m.setdefault('_oxy', (0, 0))
    return m


def view(m, x0, y0, x1, y1):
    """sub-window of a maps dict (numpy views) with its canvas offset tracked in _oxy."""
    ox, oy = m.get('_oxy', (0, 0))
    v = {k: (a[y0:y1, x0:x1] if isinstance(a, np.ndarray) and a.ndim >= 2 else a) for k, a in m.items()}
    v['_oxy'] = (ox + x0, oy + y0)
    return v


def _group_of(p_abs):
    g = CTX.get('gmap')
    if g is None:
        return CTX['group']
    c = p_abs[len(p_abs) // 2]
    x = int(np.clip(c[0], 0, g.shape[1] - 1)); y = int(np.clip(c[1], 0, g.shape[0] - 1))
    return int(g[y, x])


# ------------------------------------------------------------------ helpers
def smooth_poly(p, it=2):
    for _ in range(it):
        if len(p) < 3: return p
        q = p.copy(); q[1:-1] = 0.25 * p[:-2] + 0.5 * p[1:-1] + 0.25 * p[2:]
        p = q
    return p


def resample(p, step):
    p = np.asarray(p, np.float32)
    seg = np.hypot(*np.diff(p, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)])
    if s[-1] < 1e-6: return p[:1]
    n = max(2, int(s[-1] / step) + 1)
    ss = np.linspace(0, s[-1], n)
    return np.stack([np.interp(ss, s, p[:, 0]), np.interp(ss, s, p[:, 1])], 1).astype(np.float32)


def streamlines(lab, rid, c2, s2, PX, pitch, maxlen, minlen, step=None, seed=0, dtest=0.55, maxturn_deg=50, cand_mask=None):
    """Evenly spaced streamlines (Jobard-Lefer) in label region rid. Returns list of (n,2) float32 px polylines."""
    step_px = (step or pitch * 0.35) * PX
    m = (lab == rid) if cand_mask is None else cand_mask
    ys, xs = np.nonzero(m)
    if len(xs) == 0: return []
    pad = 3
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, lab.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, lab.shape[1])
    labc = np.ascontiguousarray(lab[y0:y1, x0:x1]).astype(np.int32)
    c2c = np.ascontiguousarray(c2[y0:y1, x0:x1]).astype(np.float32); s2c = np.ascontiguousarray(s2[y0:y1, x0:x1]).astype(np.float32)
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
    """cut long streamlines into stitches of length L mm (+/- jit), random phase per line."""
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


def sample_col(src_lin_blur, p):
    """mean colour of source along a stitch polyline (px coords in source map space)."""
    H, W, _ = src_lin_blur.shape
    q = p[:: max(1, len(p) // 6)]
    xi = np.clip(np.round(q[:, 0]).astype(int), 0, W - 1); yi = np.clip(np.round(q[:, 1]).astype(int), 0, H - 1)
    return src_lin_blur[yi, xi].mean(0)


def extend_ends(p, ext_px):
    if len(p) < 2 or ext_px <= 0: return p
    d0 = p[0] - p[min(2, len(p) - 1)]; d0 /= (np.linalg.norm(d0) + 1e-6)
    d1 = p[-1] - p[max(-3, -len(p))]; d1 /= (np.linalg.norm(d1) + 1e-6)
    return np.vstack([p[0] + d0 * ext_px, p, p[-1] + d1 * ext_px]).astype(np.float32)


# ------------------------------------------------------------------ the primitive
def put(m, p, col, r_mm, h0, hamp, matid=WOOL, ply_mm=0.7, ply_deg=32, taper_mm=0.5, tw_deg=20, seed=0, cov=1.0, hbias=0.0,
        sid=None, pexp=None, bmul=0.0, kind=None):
    PX = m['PX']
    sid = next_sid() if sid is None else sid
    pexp = float(pexp if pexp is not None else (0.5 if matid == METAL else 0.42))
    p = np.ascontiguousarray(p, np.float32)
    if REC is not None:
        oxy = np.array(m.get('_oxy', (0, 0)), np.float32)
        pa = p + oxy
        REC.add(pa, 0, [r_mm, h0, hamp, float(col[0]), float(col[1]), float(col[2]), ply_mm, ply_deg, taper_mm, tw_deg, cov, hbias,
                        pexp, bmul], [int(matid), int(seed), int(sid)],
                [CTX['region'], CTX['kind'] if kind is None else kind, _group_of(pa), CTX['unit']])
    raster_stitch(m['h'], m['alb'], m['T'], m['mat'], m['cov'], m['sid'], m['sfr'], m['base'], p,
                  float(r_mm * PX), float(h0), float(hamp), float(col[0]), float(col[1]), float(col[2]), int(matid),
                  float(ply_mm * PX), float(math.tan(math.radians(ply_deg))), float(taper_mm * PX), int(sid), int(seed),
                  float(math.radians(tw_deg)), float(PX), float(cov), float(hbias), pexp, float(bmul), 1.0, 1.0)
    return sid


def squeeze(m, p, rad_px, amount, keepmat):
    sid = next_sid()
    p = np.ascontiguousarray(p, np.float32)
    if REC is not None:
        pa = p + np.array(m.get('_oxy', (0, 0)), np.float32)
        REC.add(pa, 1, [rad_px, amount] + [0.0] * 12, [int(keepmat), 0, int(sid)],
                [CTX['region'], K_SQUEEZE, _group_of(pa), CTX['unit']])
    squeeze_along(m['h'], m['mat'], m['stamp'], sid, p, float(rad_px), float(amount), int(keepmat))


def new_unit():
    CTX['unit'] = next_sid()
    return CTX['unit']


# ------------------------------------------------------------------ fills
def _raster_lines(m, sts, src_blur, shades, PX, pitch, L, seed, matid, h0, hamp, r_fac, tw_deg, ply_mm, taper, cov, hbias,
                  colfn, kind, bmul=0.0, order_shuffle=True):
    r = np.random.default_rng(seed + 2)
    order = r.permutation(len(sts)) if order_shuffle else np.arange(len(sts))
    for i in order:
        p = sts[i]
        src = sample_col(src_blur, p)
        col = shades.pick(src) if shades is not None else src
        if colfn is not None: col = colfn(col, p)
        rr = r_fac * pitch * (1 + r.uniform(-0.12, 0.12))
        put(m, p, col, rr, h0, hamp * (1 + r.uniform(-0.1, 0.1)), matid, ply_mm=ply_mm, taper_mm=min(taper, 0.3 * L if L else taper),
            tw_deg=tw_deg, seed=seed, cov=cov, hbias=hbias, kind=kind, bmul=bmul)


def fill_region(m, lab, rid, field, src_blur, shades, PX, style='laid', pitch=0.8, L=None, seed=0, matid=WOOL,
                couch=None, maxlen=70, minlen=0.8, h0=0.05, hamp=0.42, r_fac=0.58, tw_deg=20, ply_mm=0.7, taper=0.5,
                order_shuffle=True, cov=1.0, hbias=0.0, colfn=None, ext=0.35, gapfill=True, bmul=0.0, maxturn_deg=50):
    """Fill a labelled region with strands. style: 'laid' (full-length strands) or 'split' (cut into stitches of L mm)."""
    c2, s2 = field
    kind = K_LAID if style == 'laid' else (K_SATIN if matid == SILK else K_SPLIT)
    CTX['unit'] = -1
    lines = streamlines(lab, rid, c2, s2, PX, pitch, maxlen, minlen, seed=seed, maxturn_deg=maxturn_deg)
    lines = [extend_ends(smooth_poly(resample(p, 0.3 * PX), 2), ext * pitch * PX) for p in lines if len(p) >= 2]
    sts = cut_stitches(lines, PX, L or 3.0, jit=0.3, seed=seed + 1, overlap=0.25 * pitch) if style == 'split' else lines
    kw = dict(seed=seed, matid=matid, h0=h0, hamp=hamp, r_fac=r_fac, tw_deg=tw_deg, ply_mm=ply_mm, taper=taper, cov=cov,
              hbias=hbias, colfn=colfn, kind=kind, bmul=bmul, order_shuffle=order_shuffle)
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


def perp_field(c2, s2):
    return (-c2).astype(np.float32), (-s2).astype(np.float32)


def couch_region(m, lab, rid, field, src_blur, shades, PX, spacing=4.5, tie=4.0, r_mm=0.42, seed=0, colmul=1.0, h0=0.42,
                 hamp=0.36, tie_col=None, matid=WOOL, bar_field=None, jitter_deg=0.0, cov=1.0, bar_col=None):
    """Bayeux couching bars across the laid strands + tie-downs (bars of the same yarn unless bar_col).
    bar_field: optional explicit field for the bars (e.g. diagonal for ermine); jitter_deg: per-bar angle jitter."""
    c2, s2 = bar_field if bar_field is not None else perp_field(*field)
    bars = streamlines(lab, rid, c2, s2, PX, spacing, 200, 1.5, step=0.4, seed=seed, dtest=0.7, maxturn_deg=25)
    r = np.random.default_rng(seed)
    for p in bars:
        p = smooth_poly(resample(p, 0.4 * PX), 4)
        if len(p) > 3:
            t = np.linspace(0, 1, len(p))[:, None]
            chord = p[0] * (1 - t) + p[-1] * t
            p = (0.55 * p + 0.45 * chord).astype(np.float32)
        if jitter_deg > 0 and len(p) > 1:
            c = p.mean(0); a = math.radians(r.normal(0, jitter_deg))
            R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]], np.float32)
            p = ((p - c) @ R.T + c).astype(np.float32)
        p = (p + r.normal(0, 0.06 * PX, 2)).astype(np.float32)
        src = sample_col(src_blur, p)
        col = bar_col if bar_col is not None else (shades.pick(src) if shades is not None else src) * colmul
        new_unit()
        squeeze(m, p, 0.95 * PX, 0.30, matid)
        put(m, p, col, r_mm, h0, hamp, matid, ply_mm=0.7, taper_mm=0.6, tw_deg=20, seed=seed, hbias=0.3, kind=K_BAR, cov=cov)
        seg = np.hypot(*np.diff(p, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)]) / PX
        pos = r.uniform(0.3, 1.0) * tie
        while pos < s[-1] - 0.5:
            i = min(max(np.searchsorted(s, pos), 1), len(p) - 1)
            d = p[i] - p[i - 1]; d /= (np.linalg.norm(d) + 1e-6)
            n = np.array([-d[1], d[0]], np.float32)
            c = np.array([np.interp(pos, s, p[:, 0]), np.interp(pos, s, p[:, 1])], np.float32)
            a = math.radians(r.uniform(-12, 12)); nn = np.array([n[0] * math.cos(a) - n[1] * math.sin(a), n[0] * math.sin(a) + n[1] * math.cos(a)], np.float32)
            q = np.stack([c - nn * 0.75 * PX, c + nn * 0.75 * PX]).astype(np.float32)
            tc = col * 0.92 if tie_col is None else tie_col
            put(m, q, tc, 0.2, h0 + hamp * 0.75, 0.12, matid, ply_mm=0.5, taper_mm=0.25, tw_deg=0, seed=seed, hbias=0.5, kind=K_TIE,
                cov=0.5 * cov)
            pos += tie * (1 + r.uniform(-0.25, 0.25))
    CTX['unit'] = -1
    return bars


def stem_path(m, poly_px, col, PX, L=3.5, width=1.3, h0=0.55, hamp=0.45, seed=0, matid=WOOL, slant_deg=13, cov=0.5):
    """Stem / outline stitch rope along a polyline (px). Overlapping slanted stitches advancing L/2.
    cov 0.5 = the outline fibre multiplier (fuzz calibration)."""
    r = np.random.default_rng(seed)
    p = resample(poly_px, 0.25 * PX)
    if len(p) < 2: return
    seg = np.hypot(*np.diff(p, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)]) / PX
    def P(x):
        x = np.clip(x, 0, s[-1]); return np.array([np.interp(x, s, p[:, 0]), np.interp(x, s, p[:, 1])], np.float32)
    s0 = 0.0
    off = width * 0.22
    rad = width * 0.36
    CTX['unit'] = next_sid()
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
            seed=seed, hbias=0.2, kind=K_STEM, cov=cov)
        s0 += l / 2
    CTX['unit'] = -1


def mask_contours(mask, PX, min_len_mm=3.0):
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
    """padded satin dome from a mask: rounded profile reaching `height` mm at radius_mm in from the edge."""
    d = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5) / PX
    t = np.clip(d / radius_mm, 0, 1)
    return (height * np.sqrt(1 - (1 - t) ** 2)).astype(np.float32)


def metal_couch(m, lab, rid, field, PX, pitch=1.0, thread_r=0.24, tie=2.6, tie_col=None, seed=0, h0=0.45, hamp=0.32,
                col=None, tarnish=None):
    """underside-couched silver-gilt: pairs of metal threads following the field, tied every ~2.6 mm with coloured silk."""
    c2, s2 = field
    lines = streamlines(lab, rid, c2, s2, PX, pitch, 120, 0.8, seed=seed, dtest=0.6, maxturn_deg=60)
    r = np.random.default_rng(seed)
    gold = col if col is not None else np.array([0.815, 0.515, 0.141], np.float32)
    tie_col = tie_col if tie_col is not None else np.array([0.32, 0.06, 0.04], np.float32)
    for p in lines:
        p = smooth_poly(resample(p, 0.3 * PX), 2)
        if len(p) < 2: continue
        CTX['unit'] = next_sid()
        seg = np.diff(p, axis=0); ln = np.hypot(*seg.T) + 1e-6
        nrm = np.stack([-seg[:, 1] / ln, seg[:, 0] / ln], 1); nrm = np.vstack([nrm, nrm[-1:]])
        for k, o in enumerate((-0.25, 0.25)):
            q = (p + nrm * o * pitch * PX).astype(np.float32)
            g = gold * (1 + r.uniform(-0.08, 0.05))
            if tarnish is not None and r.random() < tarnish:
                g = g * np.array([0.55, 0.5, 0.45], np.float32)
            put(m, q, g, thread_r, h0, hamp, METAL, ply_mm=0.33, ply_deg=62, taper_mm=0.3, tw_deg=55, seed=seed + k, cov=0.0,
                hbias=0.05, kind=K_METAL)
        s = np.concatenate([[0], np.cumsum(ln)]) / PX
        pos = r.uniform(0, tie)
        while pos < s[-1]:
            i = min(max(np.searchsorted(s, pos), 1), len(p) - 1)
            n = nrm[i - 1]
            c = np.array([np.interp(pos, s, p[:, 0]), np.interp(pos, s, p[:, 1])], np.float32)
            q = np.stack([c - n * 0.55 * pitch * PX, c + n * 0.55 * pitch * PX]).astype(np.float32)
            put(m, q, tie_col * (1 + r.uniform(-0.1, 0.1)), 0.13, h0 + hamp * 0.8, 0.06, SILK, ply_mm=0.3, taper_mm=0.15, tw_deg=0,
                seed=seed, cov=0.0, hbias=0.3, kind=K_MTIE)
            pos += tie * (1 + r.uniform(-0.2, 0.2))
    CTX['unit'] = -1
    return lines


def cord_path(m, poly_px, col, PX, width=1.2, h0=0.45, hamp=0.5, seed=0, tie=3.2, tie_col=None, matid=WOOL, cov=0.3):
    """Couched 2-ply cord: one continuous twisted rope along the path, tied down every ~tie mm (fibre multiplier 0.3)."""
    r = np.random.default_rng(seed)
    p = resample(poly_px, 0.3 * PX)
    if len(p) < 2: return
    p = (p + np.stack([smooth_noise1(len(p), 6, r), smooth_noise1(len(p), 6, r)], 1) * 0.05 * PX).astype(np.float32)
    rad = width * 0.5
    CTX['unit'] = next_sid()
    put(m, p, col, rad, h0, hamp, matid, ply_mm=1.3 * width, ply_deg=38, taper_mm=0.4, tw_deg=38, seed=seed, hbias=0.25,
        pexp=0.5, kind=K_CORD, cov=cov)
    seg = np.hypot(*np.diff(p, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)]) / PX
    pos = r.uniform(0.3, 1.0) * tie
    tc = col * 0.8 if tie_col is None else tie_col
    while pos < s[-1] - 0.3:
        i = min(max(np.searchsorted(s, pos), 1), len(p) - 1)
        d = p[i] - p[i - 1]; d /= (np.linalg.norm(d) + 1e-6)
        n = np.array([-d[1], d[0]], np.float32)
        c = np.array([np.interp(pos, s, p[:, 0]), np.interp(pos, s, p[:, 1])], np.float32)
        q = np.stack([c - n * (rad + 0.25) * PX + d * 0.2 * PX, c + n * (rad + 0.25) * PX - d * 0.2 * PX]).astype(np.float32)
        put(m, q, tc, 0.16, h0 + hamp * 0.9, 0.08, matid, ply_mm=0.4, taper_mm=0.2, tw_deg=0, seed=seed, hbias=0.6, cov=0.15,
            kind=K_CTIE)
        pos += tie * (1 + r.uniform(-0.2, 0.2))
    CTX['unit'] = -1
