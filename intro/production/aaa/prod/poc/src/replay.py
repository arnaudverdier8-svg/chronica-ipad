"""Stitch-on replay of the board RECORD (v2): a needle-path schedule from Grandbois (first stitch on f1664, last tie-down f1718.9).

Every recorded stitch gets (start, end, reversed) in frames. Rules (director note 3):
 * hex starts follow a ragged ring around Grandbois (distance + azimuth ripples + noise, +-3-5 frames); the sea floods continuously by
   position across the hex seams (no per-hex pads);
 * in a hex the padding rows (low-chroma felt, laid across the satin) grow along their length just ahead of the satin frontier and are
   pressed down as the satin arrives; the satin rows sweep across the coupon perpendicular to the strands, boustrophedon: each row grows
   along its length in alternating directions (a needle path), the frontier wobbles with low-frequency noise;
 * crop plots, mounds, peaks, trees, huts, towns and figures are stitched region by region (sweeps bottom-up, 4+ states for the big ones),
   paths (seams, coast, borders, rings, waves, river) are run sequentially by arclength;
 * couching squeezes apply when their bar completes.
apply() rasterises one event (optionally grown to `frac` of its length) into the maps, with the library's raster_stitch."""
import sys, os, json, math, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
sys.path.insert(0, RND)
import numpy as np, cv2
from emb.strands import raster_stitch, squeeze_along
from emb.core import hash1
from common import smoothstep

T_FIRST = 1664.0
T_END = F_LASTHEX - 0.06           # last tie-down lands at f1718.9
RV = 12.4
T1 = 1711.0               # v3: the ring reaches radius RV at f1711 (v2: 1704): the satin sweeps of the lit hexes run to ~f1717, so the film has no dead hold before the swap
EAST_DELAY = 4.0       # v3: the east (sea side) is stitched while the right candle is being lit (f1707), so the wave is still visible when it ignites
FILL = {'pad', 'field', 'plot', 'relief', 'icon', 'heal', 'sea'}
PATH = {'plot_out', 'wave', 'grid', 'seam', 'coast', 'border', 'river', 'dash', 'tuft', 'fence', 'relief_out', 'icon_out'}


def et(e):
    return e[0] if isinstance(e[0], str) else 'PUT'


def etag(e):
    return e[-1] if et(e) == 'SQ' else e[16]


def hh(*a):
    v = 2166136261
    for x in a:
        v = ((v ^ (int(x) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return v / 4294967295.0


def vnoise(x, z, seed=0, scale=1.0):
    """smooth value noise in [-1, 1] (game units)"""
    x = np.asarray(x, np.float64) / scale; z = np.asarray(z, np.float64) / scale
    xi, zi = np.floor(x), np.floor(z)
    fx, fz = x - xi, z - zi
    fx = fx * fx * (3 - 2 * fx); fz = fz * fz * (3 - 2 * fz)
    def g(i, j): return hash1((i * 7919 + j * 104729).astype(np.int64), seed) * 2 - 1
    a, b, c, d = g(xi, zi), g(xi + 1, zi), g(xi, zi + 1), g(xi + 1, zi + 1)
    return a * (1 - fx) * (1 - fz) + b * fx * (1 - fz) + c * (1 - fx) * fz + d * fx * fz


def arrival(x, z):
    """frame at which the needle front reaches (x, z): ragged ring from Grandbois"""
    x = np.asarray(x, np.float64); z = np.asarray(z, np.float64)
    r = np.hypot(x, z); az = np.arctan2(z, x)
    reff = r * (1 + 0.10 * np.sin(2 * az + 0.8) + 0.07 * np.sin(5 * az + 2.1)) + 1.1 * vnoise(x, z, 3, 1.6)
    s = np.clip(reff / RV, 0, 1)
    east = EAST_DELAY * smoothstep(1.5, 5.5, x)
    return T_FIRST + (T1 - T_FIRST) * s ** 1.0 + east


def arrival_sea(x, z):
    """v3: smooth arrival of the sea flood: the same ragged ring as `arrival` but with only low-frequency noise (5-unit scale), so the stitches of a row
    are timed monotonically along it (a comb of strand tips, not a dissolve of scattered 13 mm dashes)"""
    x = np.asarray(x, np.float64); z = np.asarray(z, np.float64)
    r = np.hypot(x, z); az = np.arctan2(z, x)
    reff = r * (1 + 0.10 * np.sin(2 * az + 0.8) + 0.07 * np.sin(5 * az + 2.1)) + 0.7 * vnoise(x, z, 3, 5.0)
    s = np.clip(reff / RV, 0, 1)
    return T_FIRST + (T1 - T_FIRST) * s + EAST_DELAY * smoothstep(1.5, 5.5, x)


def load(D):
    R = pickle.load(open(f'{D}/record.pkl', 'rb'))
    cz = np.load(f'{D}/canvas.npz'); mk = np.load(f'{D}/masks.npz'); hm = np.load(f'{D}/hexmap.npz')
    canvas = {k: np.ascontiguousarray(cz[k]) for k in cz.files}
    canvas['base'] = mk['base'].astype(np.float32)
    canvas['stamp'] = np.zeros(canvas['h'].shape, np.int32)
    canvas['PX'] = PX
    masks = {k: mk[k] for k in mk.files}
    return R, canvas, masks, dict(hid=hm['hid'].astype(np.int32), dedge=hm['dedge'].astype(np.float32))


def ev_pts(e):
    """polyline of an event in board px (None for squeezes -> their path)"""
    if et(e) == 'SQ':
        return np.asarray(e[1], np.float32)
    return (e[0] + np.array(e[15], np.float32)).astype(np.float32)


def schedule(R, layout, pieces):
    """-> st, en (frames), rev (bool: draw the polyline end-to-start), plus info dict"""
    rec = R['record']; n = len(rec)
    hexes = layout['hexes']
    HK = {(h['q'], h['r']): i for i, h in enumerate(hexes)}
    gpx = np.array([(0 - BX0) * PPU, (0 - BZ0) * PPU])
    hexc = np.array([[(h['x'] - BX0) * PPU, (h['z'] - BZ0) * PPU] for h in hexes])
    piece_hex = {p['id']: tuple(p['hex']) for p in pieces}
    hexmeta = R.get('hexmeta', {})
    dur_h = np.array([13.0 + 6.0 * hh(h['q'], h['r'], 41) for h in hexes])
    t0_h = np.array([float(arrival(h['x'], h['z'])) + 3.0 * (hh(h['q'], h['r'], 7) - 0.5) for h in hexes])
    t0_h[HK[(0, 0)]] = T_FIRST
    for i in range(len(hexes)):
        t0_h[i] = min(t0_h[i], T_END - 1.14 * dur_h[i])
    st = np.zeros(n); en = np.zeros(n); rev = np.zeros(n, bool)
    # group events
    groups = {}
    for i, e in enumerate(rec):
        tg = etag(e)
        groups.setdefault(tg[3], []).append(i)
    heal_start = R.get('heal_start', n)
    info = dict(t0_h=t0_h, dur_h=dur_h)
    for gid, idx in groups.items():
        e0 = rec[idx[0]]
        kind, key = etag(e0)[0], etag(e0)[1]
        # hex of the group
        if kind in ('icon', 'icon_out'): hk = piece_hex.get(key)
        elif kind in ('sea', 'wave', 'grid', 'river'): hk = None
        else: hk = tuple(key)
        hi = HK.get(hk) if hk is not None else None
        pts = [ev_pts(rec[i]) for i in idx]
        cen = np.array([p.mean(0) for p in pts])
        # ---------------------------------------------------------------- sea flood + positional path kinds
        if kind in ('sea', 'wave', 'grid', 'river'):
            gx_ = BX0 + cen[:, 0] / PPU; gz_ = BZ0 + cen[:, 1] / PPU
            T = arrival_sea(gx_, gz_)
            if kind == 'sea':
                for j, i in enumerate(idx):
                    e = rec[i]
                    p = pts[j]
                    d0 = np.hypot(*(p[0] - gpx)); d1 = np.hypot(*(p[-1] - gpx))
                    rev[i] = bool(d1 < d0) and et(e) != 'SQ'
                    # rows of laid denim: one jitter per row (0.9 mm quantised y), a smooth low-frequency front, stitches grow along their length
                    row_j = 2.0 * (hh(int(cen[j][1] / (0.9 * PX)), 31) - 0.5)        # +-1 frame per row (v3): tips of neighbouring rows stagger by up to ~15 mm
                    t = T[j] + row_j + 0.6
                    L_mm = float(np.hypot(*np.diff(p, axis=0).T).sum() / PX) if len(p) > 1 else 0
                    g = max(1.3, min(L_mm, 40) / 6.5)           # the needle runs along the row: a stitch grows at ~6.5 mm per frame
                    st[i] = t; en[i] = t + g
                continue
            # waves / grid / river: sequential along the path, starting when the flood arrives
            lens = np.array([np.hypot(*np.diff(p, axis=0).T).sum() / PX if len(p) > 1 else 0.0 for p in pts])
            tot = max(lens.sum(), 1e-3)
            start = float(T[0]) + 2.0 + 2.5 * hh(gid, 3)
            dur = float(np.clip(tot / 3.0, 1.2, 9.0))
            c = np.concatenate([[0], np.cumsum(lens)]) / tot
            for j, i in enumerate(idx):
                st[i] = start + dur * c[j]; en[i] = start + dur * c[j + 1] if lens[j] > 0 else st[i]
            continue
        dur = float(dur_h[hi]); t0 = float(t0_h[hi]); hc = hexc[hi]
        if kind in ('pad', 'field'):
            meta = hexmeta.get(hi, dict(angle=90.0))
            th = math.radians(meta['angle'])
            d = np.array([math.cos(th), math.sin(th)]); nn = np.array([-math.sin(th), math.cos(th)])
            out = hc - gpx
            sg = 1.0 if (nn @ out) >= 0 else -1.0
            if abs(nn @ out) < 0.25 * (np.hypot(*out) + 1e-6): sg = 1.0 if hh(hi, 3) < 0.5 else -1.0
            RR = 26.0 * PX
            if kind == 'pad':
                lead = 1.0
                for j, i in enumerate(idx):
                    p = pts[j]
                    # pad rows run across the satin rows (along the sweep axis): start at the sweep origin and keep a little ahead of the satin
                    s0 = sg * (nn @ (p[0] - hc)); s1 = sg * (nn @ (p[-1] - hc))
                    rev[i] = bool(s1 < s0)
                    off = 1.2 * (hh(gid, j, 5) - 0.5) + 1.3 * vnoise((cen[j][0] - gpx[0]) / PPU, (cen[j][1] - gpx[1]) / PPU, 21 + hi, 1.1)
                    st[i] = t0 + 0.10 * dur - lead + off
                    en[i] = t0 + 0.66 * dur - lead + off + 1.0
                continue
            # satin rows: sweep + needle direction
            pitch = 0.85 * PX
            g_row = 1.9
            for j, i in enumerate(idx):
                e = rec[i]; p = pts[j]
                s_c = sg * (nn @ (cen[j] - hc))
                sn = np.clip((s_c + RR) / (2 * RR), 0, 1)
                row = int(np.floor((s_c + RR) / pitch))
                a0 = d @ (p[0] - hc); a1 = d @ (p[-1] - hc)
                sgn_a = 1.0 if row % 2 == 0 else -1.0
                q0 = sgn_a * a0; q1 = sgn_a * a1
                rev[i] = bool(q0 > q1) and et(e) != 'SQ'
                qa, qb = (min(q0, q1), max(q0, q1)) if et(e) != 'SQ' else (q0, q1)
                qa = np.clip((qa + RR) / (2 * RR), 0, 1); qb = np.clip((qb + RR) / (2 * RR), 0, 1)
                wob = 1.3 * vnoise((cen[j][0] - gpx[0]) / PPU, (cen[j][1] - gpx[1]) / PPU, 9 + hi, 1.3)
                tr = t0 + dur * (0.10 + 0.56 * sn) + wob
                st[i] = tr + g_row * qa; en[i] = tr + g_row * qb
                if et(e) == 'SQ': st[i] = en[i] = tr + g_row
            continue
        if kind in FILL:     # plot, relief, icon, heal: region sweeps
            if kind == 'icon':
                ps = {'town': (0.40, 1.02), 'site': (0.45, 1.0), 'lumber': (0.50, 0.95), 'banner': (0.60, 1.05), 'card': (0.55, 1.0), 'tree': (0.58, 1.0)}
                pk = next((p['kind'] for p in pieces if p['id'] == key), 'tree')
                a, b = ps[pk]
                a += 0.08 * (hh(gid, 2) - 0.5); b += 0.04 * (hh(gid, 4) - 0.5)
                t_a = t0 + a * dur; t_b = t0 + b * dur
                # bottom-up sweep (ground line first); materials stitched in tag order
                y = cen[:, 1]
                sn = (y.max() - y) / max(y.max() - y.min(), 1.0)
                sn = np.clip(sn, 0, 1)
                for j, i in enumerate(idx):
                    g = 1.4
                    t = t_a + (t_b - t_a - g) * sn[j] + 0.4 * (hh(gid, j, 6) - 0.5)
                    st[i] = t; en[i] = t + g
                continue
            if kind == 'heal':
                continue          # scheduled in finalize (heal sweep after the rise of the piece)
            # plot / relief: sweep perpendicular to the mean strand direction, boustrophedon rows
            w = {'plot': (0.40 + 0.20 * hh(gid, 1), 0.30), 'relief': (0.50 + 0.15 * hh(gid, 1), 0.22)}[kind]
            t_a = t0 + w[0] * dur; t_dur = w[1] * dur
            dirs = []
            for p in pts:
                dv = p[-1] - p[0]; nrm = np.hypot(*dv) + 1e-6
                a2 = 2 * math.atan2(dv[1], dv[0]); dirs.append((math.cos(a2), math.sin(a2)))
            dm = np.mean(dirs, 0); ang = 0.5 * math.atan2(dm[1], dm[0])
            d = np.array([math.cos(ang), math.sin(ang)]); nn = np.array([-math.sin(ang), math.cos(ang)])
            s_ = (cen - cen.mean(0)) @ nn; a_ = (cen - cen.mean(0)) @ d
            Rs = max(np.abs(s_).max(), 1.0); Ra = max(np.abs(a_).max() + 12, 1.0)
            pitch = 0.75 * PX
            g_row = max(0.7, min(1.6, t_dur * 0.3))
            for j, i in enumerate(idx):
                p = pts[j]
                sn = (s_[j] + Rs) / (2 * Rs)
                row = int(np.floor((s_[j] + Rs) / pitch))
                sgn_a = 1.0 if row % 2 == 0 else -1.0
                q0 = sgn_a * (d @ (p[0] - cen.mean(0))); q1 = sgn_a * (d @ (p[-1] - cen.mean(0)))
                rev[i] = bool(q0 > q1) and et(rec[i]) != 'SQ'
                qa, qb = min(q0, q1), max(q0, q1)
                qa = np.clip((qa + Ra) / (2 * Ra), 0, 1); qb = np.clip((qb + Ra) / (2 * Ra), 0, 1)
                tr = t_a + (t_dur - g_row) * sn
                st[i] = tr + g_row * qa; en[i] = tr + g_row * qb
                if et(rec[i]) == 'SQ': st[i] = en[i] = tr + g_row
            continue
        # ---------------------------------------------------------------- path kinds: sequential by arclength inside a window of the hex timeline
        win = {'plot_out': (0.62, 0.9), 'seam': (0.62, 0.92), 'coast': (0.66, 0.95), 'border': (0.80, 1.12), 'dash': (0.50, 0.82),
               'tuft': (0.42, 0.78), 'fence': (0.74, 0.9), 'relief_out': (0.66, 0.92), 'icon_out': (0.74, 1.12)}[kind]
        lens = np.array([np.hypot(*np.diff(p, axis=0).T).sum() / PX if len(p) > 1 else 0.0 for p in pts])
        tot = max(lens.sum(), 1e-3)
        a = win[0] + (win[1] - win[0]) * 0.55 * hh(gid, 8)
        start = t0 + a * dur
        if kind == 'border':
            # v3: the couched gold realm borders are the LAST act of the stitch-on: a second, slower pass that follows the satin wave (f1692 at Grandbois ... f1716 at the
            # rim), so the lit board is still being stitched (gold thread, ties) through f1718 instead of idling after the satin is done
            start = 1692.0 + 0.52 * (t0 - T_FIRST) + 2.0 * hh(gid, 8)
        dd = float(np.clip(tot / 2.8, 1.2, 7.0)) if kind != 'icon_out' else float(np.clip(tot / 4.0, 1.5, 4.0))
        if kind == 'icon_out':
            start = t0 + win[0] * dur + 0.6 * dur * (hh(gid, 9) * 0.3 + 0.55)
        c = np.concatenate([[0], np.cumsum(lens)]) / tot
        for j, i in enumerate(idx):
            st[i] = start + dd * c[j]; en[i] = start + dd * c[j + 1] if lens[j] > 0 else st[i]
    # squeeze events complete with the bar that follows them in the record
    for i in range(n):
        if et(rec[i]) == 'SQ' and etag(rec[i])[0] == 'sea':
            j = i + 1
            while j < n and et(rec[j]) == 'SQ': j += 1
            if j < n and etag(rec[j])[3] == etag(rec[i])[3]:
                st[i] = en[i] = en[j]
    en = np.minimum(en, T_END); st = np.minimum(st, en)
    # heal events: never part of the 2D film (they are state C)
    st[heal_start:] = en[heal_start:] = 1e6
    return st, en, rev, info


def kind_of(e):
    return etag(e)[0]


def apply(m, e, frac=1.0, rev=False, hexmap=None, masks=None):
    """raster one event into maps m (in place); frac < 1 draws a strand grown to that fraction of its length (from its start,
    or from its end if rev)"""
    if et(e) == 'SQ':
        _, pts, rad, amount, keepmat, sid, tg = e
        squeeze_along(m['h'], m['mat'], m['stamp'], int(sid), np.ascontiguousarray(pts, np.float32), float(rad), float(amount), int(keepmat))
        return
    p, col, r_mm, h0, hamp, matid, ply_mm, ply_deg, taper, tw, seed, cov, hbias, sid, pexp, oxy, tag = e
    q = (p + np.array(oxy, np.float32)).astype(np.float32)
    if rev: q = q[::-1].copy()
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
    if frac < 1:
        taper = max(taper, 0.9 * min(1.0, 0.3 + frac))          # v3: a strand being pulled through tapers to a soft tip (the needle end), not a blunt capsule
        hamp = hamp * (0.55 + 0.45 * frac)                         # and settles to full height as it is pulled tight
    raster_stitch(m['h'], m['alb'], m['T'], m['mat'], m['cov'], m['sid'], m['base'], q, float(r_mm * PXm), float(h0), float(hamp),
                  float(col[0]), float(col[1]), float(col[2]), int(matid), float(ply_mm * PXm), float(math.tan(math.radians(ply_deg))),
                  float(taper * PXm), int(sid), int(seed), float(math.radians(tw)), float(PXm), float(cov), float(hbias),
                  float(pexp if pexp is not None else (0.5 if matid == 3 else 0.42)))


def copy_maps(m, keys=('h', 'alb', 'T', 'mat', 'cov', 'sid', 'stamp')):
    return {k: (m[k].copy() if k in keys else m[k]) for k in m}
