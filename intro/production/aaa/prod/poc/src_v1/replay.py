"""Stitch-on replay of the board RECORD as a wavefront from Grandbois (f1664 -> last hex closes f1719).
Every recorded stitch gets a start/end frame; strands grow along their length (partial capsule chains),
couching squeezes and card slips are applied when their stitch completes, padding felt goes down first.
Used by r25_frames.py (2D frames) and finalize.py (final A / ghost B states for Eevee)."""
import sys, os, json, math, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
sys.path.insert(0, RND)
import numpy as np, cv2
from emb.strands import raster_stitch, squeeze_along
from emb.core import hash1

ORDER = {'field': (0.04, 0.62), 'sea': (0.02, 0.62), 'plot': (0.45, 0.72), 'plot_out': (0.7, 0.8), 'relief': (0.55, 0.8),
         'wave': (0.62, 0.85), 'grid': (0.6, 0.9), 'seam': (0.66, 0.9), 'coast': (0.66, 0.92), 'river': (0.5, 0.9),
         'border': (0.8, 0.99), 'icon': (0.6, 0.93), 'icon_out': (0.86, 0.99)}
HEX_DUR = 13.0          # frames a hex takes from padding to its last tie-down


def et(e):
    return e[0] if isinstance(e[0], str) else 'PUT'


def load(D):
    R = pickle.load(open(f'{D}/record.pkl', 'rb'))
    cz = np.load(f'{D}/canvas.npz'); mk = np.load(f'{D}/masks.npz'); hm = np.load(f'{D}/hexmap.npz')
    canvas = {k: np.ascontiguousarray(cz[k]) for k in cz.files}
    canvas['base'] = mk['base'].astype(np.float32)
    canvas['stamp'] = np.zeros(canvas['h'].shape, np.int32)
    canvas['PX'] = PX
    return R, canvas, dict(icon=mk['icon'], icon_dil=mk['icon_dil'], plot=mk['plot']), dict(hid=hm['hid'].astype(np.int32), dedge=hm['dedge'].astype(np.float32))


def hex_start_frames(layout, pieces):
    """wavefront: start frame of each hex from its distance to Grandbois (world units), ends by F_LASTHEX"""
    hexes = layout['hexes']
    d = np.array([math.hypot(h['x'], h['z']) for h in hexes])
    # visible-region radius sets the speed; farther hexes (only seen at the crane's end) are compressed in
    dv = 12.5
    t0 = F_STITCH0 + 1.0
    t_last = F_LASTHEX - HEX_DUR
    s = np.clip(d / dv, 0, None)
    f = t0 + (t_last - t0) * np.where(s <= 1, s ** 0.9, 1.0)
    jit = np.array([hash1(int(h['q'] * 131 + h['r'] * 7 + 999), 3) for h in hexes]) - 0.5
    f = np.clip(f + 1.6 * jit, t0, t_last)
    return {(h['q'], h['r']): float(f[i]) for i, h in enumerate(hexes)}


def schedule(R, layout, pieces):
    rec = R['record']
    hs = hex_start_frames(layout, pieces)
    pid_hex = {p['id']: tuple(p['hex']) for p in pieces}
    hidx = {i: (h['q'], h['r']) for i, h in enumerate(layout['hexes'])}
    # group events by (hex, kind) to compute a sweep order within each group
    groups = {}
    for i, e in enumerate(rec):
        if et(e) == 'PAD':
            tg = e[3]
        elif et(e) in ('SQ', 'SLIP'):
            tg = e[-1]
        else:
            tg = e[16]
        kind, key = tg[0], tg[1]
        hk = pid_hex.get(key, key) if kind in ('icon', 'icon_out') else key
        hk = tuple(hk)
        groups.setdefault((hk, kind), []).append(i)
    st = np.zeros(len(rec)); en = np.zeros(len(rec))
    for (hk, kind), idx in groups.items():
        t_hex = hs.get(hk, F_STITCH0 + 20)
        a0, a1 = ORDER[kind]
        # sweep coordinate per event (projection on a per-group axis perpendicular to the mean strand direction)
        cen = []; dirs = []
        for i in idx:
            e = rec[i]
            if et(e) == 'PAD':
                cen.append((0.0, 0.0)); dirs.append((1.0, 0.0)); continue
            if et(e) == 'SLIP':
                cen.append((float(e[3]), float(e[2]))); dirs.append((1.0, 0.0)); continue
            p = e[1] if et(e) == 'SQ' else e[0] + np.array(e[15], np.float32)
            cen.append(tuple(p.mean(0))); d = p[-1] - p[0]; n = np.hypot(*d) + 1e-6; dirs.append((d[0] / n, d[1] / n))
        cen = np.array(cen); dirs = np.array(dirs)
        dd = dirs * np.sign(dirs[:, :1] + 1e-6)
        md = dd.mean(0); md = md / (np.linalg.norm(md) + 1e-6)
        perp = np.array([-md[1], md[0]])
        s = cen @ perp
        if kind in ('icon', 'icon_out'):
            s = cen[:, 1]          # icons stitch bottom-up (ground line first)
            s = -s
        rk = np.argsort(np.argsort(s)) / max(1, len(idx) - 1) if len(idx) > 1 else np.zeros(1)
        for j, i in enumerate(idx):
            e = rec[i]
            if et(e) == 'PAD':
                st[i] = t_hex; en[i] = t_hex + 0.01; continue
            a = a0 + (a1 - a0) * rk[j] * 0.85
            grow = 0.12 if kind in ('field', 'sea') else 0.08
            st[i] = t_hex + a * HEX_DUR
            en[i] = t_hex + (min(a + grow, 0.995)) * HEX_DUR
            if et(e) == 'SQ':       # pinch lands when its couching bar completes
                st[i] = en[i] = t_hex + min(a + grow, 0.995) * HEX_DUR
    en = np.minimum(en, F_LASTHEX - 0.01); st = np.minimum(st, en)
    return st, en


def kind_of(e):
    if et(e) == 'PAD': return e[3][0]
    if et(e) in ('SQ', 'SLIP'): return e[-1][0]
    return e[16][0]


def apply(m, e, frac=1.0, hexmap=None, masks=None):
    """raster one event into maps m (in place); frac < 1 draws a strand grown to that fraction of its length"""
    if et(e) == 'PAD':
        i, col = e[1], e[2]
        hid = hexmap['hid']
        ys, xs = np.nonzero(hid == i)
        if len(xs) == 0: return
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        sl = (slice(y0, y1), slice(x0, x1))
        mk = (hid[sl] == i) & (hexmap['dedge'][sl] > 0.55) & (masks['icon_dil'][sl] == 0)
        nz = (hash1(np.arange(mk.size).reshape(mk.shape) + i * 7919, 11) - 0.5) * 0.12
        felt = col[None, None] * (1 + nz[..., None])
        m['alb'][sl][mk] = felt[mk]
        m['h'][sl][mk] = np.maximum(m['h'][sl][mk], m['base'][sl][mk] * 0.82 + 0.05)
        m['mat'][sl][mk] = 1
        m['cov'][sl][mk] = 0.0
        return
    if et(e) == 'SQ':
        _, pts, rad, amount, keepmat, sid, tg = e
        squeeze_along(m['h'], m['mat'], m['stamp'], int(sid), np.ascontiguousarray(pts, np.float32), float(rad), float(amount), int(keepmat))
        return
    if et(e) == 'SLIP':
        _, pid, v, u, alb, hgt, al, sid, tg = e
        hh, ww = al.shape
        rows = hh if frac >= 1 else int(round(hh * frac))
        if rows <= 0: return
        r0 = hh - rows                       # stitched bottom-up
        sl = (slice(v + r0, v + hh), slice(u, u + ww))
        a = al[r0:]
        sel = a > 0.5
        base = m['base'][sl]
        hn = base + hgt[r0:] + 0.05
        upd = sel & (hn >= m['h'][sl])
        m['alb'][sl][upd] = alb[r0:][upd]
        m['h'][sl][upd] = hn[upd]
        m['mat'][sl][upd] = 1
        m['cov'][sl][upd] = 1.0
        m['sid'][sl][upd] = sid
        Tt = m['T'][sl]; Tt[upd, 0] = 0.0; Tt[upd, 1] = 1.0
        return
    p, col, r_mm, h0, hamp, matid, ply_mm, ply_deg, taper, tw, seed, cov, hbias, sid, pexp, oxy, tag = e
    q = (p + np.array(oxy, np.float32)).astype(np.float32)
    if frac < 1:
        seg = np.hypot(*np.diff(q, axis=0).T); s = np.concatenate([[0], np.cumsum(seg)])
        L = s[-1] * frac
        if L < 0.6: return
        k = int(np.searchsorted(s, L))
        k = min(max(k, 1), len(q) - 1)
        t = (L - s[k - 1]) / max(1e-6, s[k] - s[k - 1])
        q = np.vstack([q[:k], q[k - 1] + (q[k] - q[k - 1]) * t]).astype(np.float32)
        if len(q) < 2: return
    PXm = m['PX']
    raster_stitch(m['h'], m['alb'], m['T'], m['mat'], m['cov'], m['sid'], m['base'], q, float(r_mm * PXm), float(h0), float(hamp),
                  float(col[0]), float(col[1]), float(col[2]), int(matid), float(ply_mm * PXm), float(math.tan(math.radians(ply_deg))),
                  float(taper * PXm), int(sid), int(seed), float(math.radians(tw)), float(PXm), float(cov), float(hbias),
                  float(pexp if pexp is not None else (0.5 if matid == 3 else 0.42)))


def copy_maps(m, keys=('h', 'alb', 'T', 'mat', 'cov', 'sid', 'stamp')):
    o = {k: (m[k].copy() if k in keys else m[k]) for k in m}
    return o
