"""Bake helpers (v2): region fills that tag every stitch with its needle-path group, padding rows, outlines, running stitch,
couched gold, the figure re-embroidery. Thin layer over the R25 emb.stitch primitives (unchanged); the RECORD hook of emb.stitch
captures every put() with S.TAG[0] = (kind, key, order, gid)."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
sys.path.insert(0, RND)
import numpy as np, cv2
from emb.core import hex_lin, smooth_noise, hash1, WOOL, SILK, METAL, INK, LINEN, lin2oklab, oklab2lin, srgb2lin
from emb import stitch as S

GID = [0]
CUR_OXY = [(0, 0)]


def new_gid():
    GID[0] += 1
    return GID[0]


def tag(kind, key, order=0.0, gid=None):
    S.TAG[0] = (kind, key, float(order), new_gid() if gid is None else gid)
    return S.TAG[0][3]


def shades_around(hexcol, n=5, spread=0.055, seed=0, hue=4.0, lin_col=None):
    base = lin2oklab((hex_lin(hexcol) if lin_col is None else np.asarray(lin_col, np.float32))[None])[0]
    r = np.random.default_rng(seed)
    labs = []
    for k in range(n):
        t = (k - (n - 1) / 2) / max(1, (n - 1) / 2)
        L_ = base[0] * (1 + spread * t + r.uniform(-0.01, 0.01))
        a, b = base[1], base[2]
        ang = math.radians(r.uniform(-hue, hue)); cs = 1 + r.uniform(-0.07, 0.07)
        labs.append([L_, (a * math.cos(ang) - b * math.sin(ang)) * cs, (a * math.sin(ang) + b * math.cos(ang)) * cs])
    return S.ShadeSet(np.array(labs, np.float32), seed)


def cut_stitches_rows(lines, PX, L, jit=0.3, seed=0, overlap=0.0):
    """like emb.stitch.cut_stitches (brick-staggered stitches of ~L mm along each streamline) but also returns the row (streamline) index"""
    r = np.random.default_rng(seed)
    out, rows = [], []
    for li, p in enumerate(lines):
        seg = np.hypot(*np.diff(p, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)]) / PX
        tot = s[-1]
        if tot < 0.3: continue
        pos = -r.uniform(0, L)
        while pos < tot:
            l = L * (1 + r.uniform(-jit, jit))
            a, b = max(pos - overlap, 0), min(pos + l, tot)
            if b - a > 0.25 * L or (a == 0 and b == tot):
                ss = np.linspace(a, b, max(2, int((b - a) / 0.4) + 2))
                out.append(np.stack([np.interp(ss, s, p[:, 0]), np.interp(ss, s, p[:, 1])], 1).astype(np.float32))
                rows.append(li)
            pos += l
    return out, rows


def raster_lines(m, sts, src_blur, shades, PX, pitch, L, seed, matid, h0, hamp, r_fac, tw_deg, ply_mm, taper, cov, hbias, colfn):
    r = np.random.default_rng(seed + 2)
    for p in sts:
        src = S.sample_col(src_blur, p)
        col = shades.pick(src) if shades is not None else src
        if colfn is not None: col = colfn(col, p)
        rr = r_fac * pitch * (1 + r.uniform(-0.12, 0.12))
        S.put(m, p, col, rr, h0, hamp * (1 + r.uniform(-0.1, 0.1)), matid, ply_mm=ply_mm, taper_mm=min(taper, 0.3 * L if L else taper),
              tw_deg=tw_deg, seed=seed, cov=cov, hbias=hbias)


def fill_region2(m, lab, rid, field, src_blur, shades, PX, style='laid', pitch=0.8, L=None, seed=0, matid=WOOL,
                 couch=None, maxlen=70, minlen=0.8, h0=0.05, hamp=0.42, r_fac=0.58, tw_deg=20, ply_mm=0.7, taper=0.5,
                 cov=1.0, hbias=0.0, colfn=None, ext=0.35, gapfill=True):
    """port of emb.stitch.fill_region without the shuffle: stitches are put in streamline order (the replay re-orders them by the
    needle path of the group anyway)"""
    c2, s2 = field
    lines = S.streamlines(lab, rid, c2, s2, PX, pitch, maxlen, minlen, seed=seed)
    lines = [S.extend_ends(S.smooth_poly(S.resample(p, 0.3 * PX), 2), ext * pitch * PX) for p in lines if len(p) >= 2]
    if style == 'split':
        sts, _ = cut_stitches_rows(lines, PX, L or 3.0, jit=0.3, seed=seed + 1, overlap=0.25 * pitch)
    else:
        sts = lines
    kw = dict(seed=seed, matid=matid, h0=h0, hamp=hamp, r_fac=r_fac, tw_deg=tw_deg, ply_mm=ply_mm, taper=taper, cov=cov, hbias=hbias, colfn=colfn)
    raster_lines(m, sts, src_blur, shades, PX, pitch, L, **kw)
    if gapfill:
        mk = lab == rid
        unc = (mk & (m['mat'] == 0)).astype(np.uint8)
        unc = cv2.morphologyEx(unc, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        if unc.sum() > 2 * (pitch * PX) ** 2:
            lab2 = np.where((cv2.dilate(unc, np.ones((5, 5), np.uint8)) > 0) & mk, rid, -1).astype(np.int32)
            l2 = S.streamlines(lab2, rid, c2, s2, PX, pitch * 0.85, min(maxlen, 6.0), 0.25, seed=seed + 9, dtest=0.5)
            l2 = [S.extend_ends(S.smooth_poly(S.resample(p, 0.3 * PX), 1), 0.5 * pitch * PX) for p in l2 if len(p) >= 2]
            if style == 'split':
                l2, _ = cut_stitches_rows(l2, PX, L or 3.0, jit=0.3, seed=seed + 3)
            kw2 = dict(kw); kw2['seed'] = seed + 17; kw2['hbias'] = hbias - 0.05
            raster_lines(m, l2, src_blur, shades, PX, pitch, L, **kw2)
    if couch is not None:
        S.couch_region(m, lab, rid, field, src_blur, shades, PX, seed=seed + 5, **couch)
    return lines


class Baker:
    """holds the map dict `m`, the record offset bookkeeping and the convenience drawing calls used by board_bake / figure embroidery"""

    def __init__(self, m, W, H):
        self.m = m; self.W = W; self.H = H
        self.oxy = (0, 0)

    def window_maps(self, x0, y0, h, w):
        mw = {k: (v[y0:y0 + h, x0:x0 + w] if isinstance(v, np.ndarray) and v.ndim >= 2 else v) for k, v in self.m.items()}
        mw['_oxy'] = (x0, y0)
        CUR_OXY[0] = (x0, y0)
        return mw

    def fill_mask(self, mask_win, x0, y0, field_angle, shades, style='split', pitch=0.85, L=7.0, seed=0, matid=SILK, h0=0.06, hamp=0.42,
                  r_fac=0.6, couch=None, maxlen=70, bend=4.0, hbias=0.0, colfn=None, tw=18, minlen=0.8, field=None, dye_noise=14.0, gapfill=True):
        mw = self.window_maps(x0, y0, mask_win.shape[0], mask_win.shape[1])
        lab = np.where(mask_win, 1, 0).astype(np.int32)
        Hh, Ww = lab.shape
        if field is None:
            if bend > 0:
                n = smooth_noise((Hh, Ww), 25 * PX, seed + 3)
                a2 = math.radians(field_angle) * 2 + np.radians(bend) * 2 * n
                c2, s2 = np.cos(a2).astype(np.float32), np.sin(a2).astype(np.float32)
            else:
                c2, s2 = S.const_field((Hh, Ww), field_angle)
        else:
            c2, s2 = field
        base_col = shades.lin[len(shades.lin) // 2]
        Ls = shades.lab[:, 0]; spread = float(Ls.max() - Ls.min()) / max(1e-3, float(Ls.mean()))
        nz = smooth_noise((Hh, Ww), dye_noise * PX, seed + 77, 2)
        srcimg = (base_col[None, None] * (1 + 0.9 * spread * np.clip(nz * 1.6, -1, 1))[..., None]).astype(np.float32)
        return fill_region2(mw, lab, 1, (c2, s2), srcimg, shades, PX, style=style, pitch=pitch, L=L, seed=seed, matid=matid,
                            couch=couch, maxlen=maxlen, minlen=minlen, h0=h0, hamp=hamp, r_fac=r_fac, tw_deg=tw, cov=1.0, hbias=hbias, colfn=colfn,
                            gapfill=gapfill)

    def put_poly(self, pts_px, colr, r_mm, h0, hamp, matid=WOOL, **kw):
        mm = dict(self.m); mm['_oxy'] = (0, 0)
        return S.put(mm, np.asarray(pts_px, np.float32), colr, r_mm, h0, hamp, matid, **kw)

    def stem(self, pts_px, colr, width=1.2, seed=0, h0=0.55, hamp=0.45, L=3.5, matid=WOOL):
        mm = dict(self.m); mm['_oxy'] = (0, 0)
        S.stem_path(mm, np.asarray(pts_px, np.float32), colr, PX, L=L, width=width, h0=h0, hamp=hamp, seed=seed, matid=matid)

    def running(self, pts_px, colr, on=2.6, off=1.5, r_mm=0.34, seed=0, h0=0.5, hamp=0.32, phase=0.0, matid=WOOL):
        q = S.resample(np.asarray(pts_px, np.float32), 0.2 * PX)
        seg = np.hypot(*np.diff(q, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)]) / PX
        rr_ = np.random.default_rng(seed)
        pos = phase
        while pos < s[-1] - 0.5:
            a, b = pos, min(pos + on * (1 + rr_.uniform(-0.15, 0.15)), s[-1])
            ss = np.linspace(a, b, max(2, int((b - a) / 0.4) + 2))
            pp = np.stack([np.interp(ss, s, q[:, 0]), np.interp(ss, s, q[:, 1])], 1) + rr_.normal(0, 0.05 * PX, 2)
            self.put_poly(pp, colr * (1 + rr_.uniform(-0.05, 0.05)), r_mm, h0, hamp, matid, ply_mm=0.6, taper_mm=0.35, tw_deg=15, seed=seed, hbias=0.25)
            pos = b + off * (1 + rr_.uniform(-0.2, 0.2))
