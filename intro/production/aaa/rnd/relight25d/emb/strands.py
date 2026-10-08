"""Numba kernels: evenly-spaced streamlines (Jobard-Lefer) inside a labelled region following an
orientation field, and a capsule-chain stitch rasterizer that writes height/albedo/tangent/material.
"""
import math
import numpy as np
from numba import njit


# ------------------------------------------------------------------ field sampling
@njit(cache=True, inline='always')
def _bil(a, x, y):
    H, W = a.shape
    if x < 0: x = 0.0
    if y < 0: y = 0.0
    if x > W - 1.001: x = W - 1.001
    if y > H - 1.001: y = H - 1.001
    x0 = int(x); y0 = int(y); fx = x - x0; fy = y - y0
    return (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy)
            + a[y0 + 1, x0] * (1 - fx) * fy + a[y0 + 1, x0 + 1] * fx * fy)


@njit(cache=True, inline='always')
def _dir(c2, s2, x, y, px, py):
    c = _bil(c2, x, y); s = _bil(s2, x, y)
    th = 0.5 * math.atan2(s, c)
    dx = math.cos(th); dy = math.sin(th)
    if dx * px + dy * py < 0:
        dx = -dx; dy = -dy
    return dx, dy


@njit(cache=True, inline='always')
def _inreg(lab, rid, x, y):
    H, W = lab.shape
    xi = int(x + 0.5); yi = int(y + 0.5)
    if xi < 0 or yi < 0 or xi >= W or yi >= H:
        return False
    return lab[yi, xi] == rid


@njit(cache=True)
def _too_close(gcnt, gpts, gsid, cell, x, y, sid, dmin):
    GH, GW = gcnt.shape
    cx = int(x / cell); cy = int(y / cell)
    d2 = dmin * dmin
    for yy in range(cy - 1, cy + 2):
        if yy < 0 or yy >= GH: continue
        for xx in range(cx - 1, cx + 2):
            if xx < 0 or xx >= GW: continue
            for k in range(gcnt[yy, xx]):
                if gsid[yy, xx, k] == sid: continue
                ddx = gpts[yy, xx, k, 0] - x; ddy = gpts[yy, xx, k, 1] - y
                if ddx * ddx + ddy * ddy < d2:
                    return True
    return False


@njit(cache=True)
def _grid_add(gcnt, gpts, gsid, cell, x, y, sid):
    GH, GW, CAP = gsid.shape
    cx = int(x / cell); cy = int(y / cell)
    if cx < 0 or cy < 0 or cx >= GW or cy >= GH: return
    k = gcnt[cy, cx]
    if k < CAP:
        gpts[cy, cx, k, 0] = x; gpts[cy, cx, k, 1] = y; gsid[cy, cx, k] = sid
        gcnt[cy, cx] = k + 1


@njit(cache=True)
def _trace_dir(c2, s2, lab, rid, x0, y0, sx, sy, step, maxlen, dtest, gcnt, gpts, gsid, cell, sid, maxturn, buf):
    n = 0; x = x0; y = y0; px = sx; py = sy; L = 0.0
    while L < maxlen and n < buf.shape[0]:
        d1x, d1y = _dir(c2, s2, x, y, px, py)
        mx = x + 0.5 * step * d1x; my = y + 0.5 * step * d1y
        d2x, d2y = _dir(c2, s2, mx, my, d1x, d1y)
        nx = x + step * d2x; ny = y + step * d2y
        if not _inreg(lab, rid, nx, ny): break
        if _too_close(gcnt, gpts, gsid, cell, nx, ny, sid, dtest): break
        if d2x * px + d2y * py < maxturn: break
        buf[n, 0] = nx; buf[n, 1] = ny; n += 1
        x = nx; y = ny; px = d2x; py = d2y; L += step
    return n


@njit(cache=True)
def trace_region(c2, s2, lab, rid, dsep, dtest, step, maxlen, minlen, cand, out_pts, out_off, maxturn):
    """Evenly spaced streamlines in region `rid`. cand: (N,2) shuffled candidate seeds inside the region.
    Returns (n_lines, n_pts); polylines are out_pts[out_off[i]:out_off[i+1]]."""
    H, W = lab.shape
    cell = dsep
    GH = int(H / cell) + 2; GW = int(W / cell) + 2
    CAP = 48
    gcnt = np.zeros((GH, GW), np.int32)
    gpts = np.zeros((GH, GW, CAP, 2), np.float32)
    gsid = np.zeros((GH, GW, CAP), np.int32)
    maxp = int(maxlen / step) + 4
    fbuf = np.zeros((maxp, 2), np.float32); bbuf = np.zeros((maxp, 2), np.float32)
    queue = np.zeros((out_pts.shape[0] // 2 + 16, 2), np.float32)
    qh = 0; qt = 0; ci = 0
    nl = 0; npt = 0
    out_off[0] = 0
    while True:
        # next seed: from queue or global candidates
        found = False
        while qh < qt:
            x = queue[qh, 0]; y = queue[qh, 1]; qh += 1
            if _inreg(lab, rid, x, y) and not _too_close(gcnt, gpts, gsid, cell, x, y, -1, dsep * 0.98):
                found = True; break
        if not found:
            while ci < cand.shape[0]:
                x = cand[ci, 0]; y = cand[ci, 1]; ci += 1
                if _inreg(lab, rid, x, y) and not _too_close(gcnt, gpts, gsid, cell, x, y, -1, dsep * 0.98):
                    found = True; break
        if not found: break
        sid = nl + 1
        d0x, d0y = _dir(c2, s2, x, y, 1.0, 0.0)
        nf = _trace_dir(c2, s2, lab, rid, x, y, d0x, d0y, step, maxlen * 0.5, dtest, gcnt, gpts, gsid, cell, sid, maxturn, fbuf)
        nb = _trace_dir(c2, s2, lab, rid, x, y, -d0x, -d0y, step, maxlen * 0.5, dtest, gcnt, gpts, gsid, cell, sid, maxturn, bbuf)
        tot = nf + nb + 1
        if tot * step < minlen:
            continue
        if npt + tot >= out_pts.shape[0] or nl + 2 >= out_off.shape[0]: break
        k = npt
        for i in range(nb - 1, -1, -1):
            out_pts[k, 0] = bbuf[i, 0]; out_pts[k, 1] = bbuf[i, 1]; k += 1
        out_pts[k, 0] = x; out_pts[k, 1] = y; k += 1
        for i in range(nf):
            out_pts[k, 0] = fbuf[i, 0]; out_pts[k, 1] = fbuf[i, 1]; k += 1
        # register + enqueue neighbours
        every = max(1, int(dsep / step * 0.5))
        for i in range(npt, k):
            _grid_add(gcnt, gpts, gsid, cell, out_pts[i, 0], out_pts[i, 1], sid)
        for i in range(npt, k, max(1, int(dsep / step))):
            if i + 1 < k:
                tx = out_pts[i + 1, 0] - out_pts[i, 0]; ty = out_pts[i + 1, 1] - out_pts[i, 1]
            else:
                tx = out_pts[i, 0] - out_pts[i - 1, 0]; ty = out_pts[i, 1] - out_pts[i - 1, 1]
            ln = math.sqrt(tx * tx + ty * ty) + 1e-9
            nx = -ty / ln; ny = tx / ln
            if qt + 2 < queue.shape[0]:
                queue[qt, 0] = out_pts[i, 0] + nx * dsep; queue[qt, 1] = out_pts[i, 1] + ny * dsep; qt += 1
                queue[qt, 0] = out_pts[i, 0] - nx * dsep; queue[qt, 1] = out_pts[i, 1] - ny * dsep; qt += 1
        npt = k; nl += 1; out_off[nl] = npt
    return nl, npt


# ------------------------------------------------------------------ hashing / noise
@njit(cache=True, inline='always')
def _h(i, j, s):
    v = (i * 374761393 + j * 668265263 + s * 2147483647) & 0xFFFFFFFF
    v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((v ^ (v >> 16)) & 0xFFFF) / 65535.0


@njit(cache=True, inline='always')
def _vnoise(x, y, s):
    xi = math.floor(x); yi = math.floor(y); fx = x - xi; fy = y - yi
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    a = _h(int(xi), int(yi), s); b = _h(int(xi) + 1, int(yi), s)
    c = _h(int(xi), int(yi) + 1, s); d = _h(int(xi) + 1, int(yi) + 1, s)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


# ------------------------------------------------------------------ rasterizer
@njit(cache=True)
def raster_stitch(h, alb, T, mat, cov, sidm, base, pts, r, h0, hamp, cr, cg, cb, matid, ply_per, ply_tan, taper,
                  sid, seed, tw, PX, fuzzcov, hbias, pexp):
    """Rasterize one stitch (polyline pts in px) as a rounded yarn.
    r: radius px; h0: lift above base (mm) at the crown of the yarn's lowest point; hamp: profile amplitude (mm);
    taper: end dip length px; ply_per: px; ply_tan: tan(ply angle); tw: surface fibre tilt (rad)."""
    H, W = h.shape
    n = pts.shape[0]
    if n < 2: return
    # total length
    tot = 0.0
    for i in range(n - 1):
        tot += math.hypot(pts[i + 1, 0] - pts[i, 0], pts[i + 1, 1] - pts[i, 1])
    if tot < 1e-3: return
    ph = _h(sid, 7, seed) * 6.283
    lv1 = _h(sid, 11, seed) * 6.283; lv2 = _h(sid, 13, seed) * 6.283
    s0 = 0.0
    ctw = math.cos(tw); stw = math.sin(tw)
    for i in range(n - 1):
        ax = pts[i, 0]; ay = pts[i, 1]; bx = pts[i + 1, 0]; by = pts[i + 1, 1]
        abx = bx - ax; aby = by - ay; ll = abx * abx + aby * aby
        seg = math.sqrt(ll)
        if seg < 1e-6: continue
        ux = abx / seg; uy = aby / seg
        x0 = int(min(ax, bx) - r - 1); x1 = int(max(ax, bx) + r + 2)
        y0 = int(min(ay, by) - r - 1); y1 = int(max(ay, by) + r + 2)
        if x0 < 0: x0 = 0
        if y0 < 0: y0 = 0
        if x1 > W: x1 = W
        if y1 > H: y1 = H
        # tangent of surface fibres (ply helix tilt)
        tx = ux * ctw - uy * stw; ty = ux * stw + uy * ctw
        for yy in range(y0, y1):
            for xx in range(x0, x1):
                px = xx - ax; py = yy - ay
                t = (px * abx + py * aby) / ll
                if t < 0: t = 0.0
                if t > 1: t = 1.0
                dx = px - t * abx; dy = py - t * aby
                dist = math.sqrt(dx * dx + dy * dy)
                s = s0 + t * seg
                e = min(s, tot - s)
                tap = e / taper if taper > 0 else 1.0
                if tap > 1: tap = 1.0
                tap = tap * tap * (3 - 2 * tap)
                re = r * (0.55 + 0.45 * tap)
                if dist >= re: continue
                sgn = ux * dy - uy * dx  # signed across
                q = dist / re
                prof = (1 - q * q) ** pexp
                tws = 0.5 + 0.5 * math.cos(6.2832 * (s + sgn * ply_tan) / ply_per + ph)
                streak = _vnoise(s / (0.9 * PX), sgn / (0.09 * PX) + sid * 3.1, seed) - 0.5
                hn = base[yy, xx] + (h0 + hamp * prof) * (0.25 + 0.75 * tap)
                hn *= (0.86 + 0.14 * tws)
                hn += 0.02 * streak
                if hn + hbias > h[yy, xx]:
                    h[yy, xx] = hn
                    along = 1.0 + 0.03 * math.sin(s / (7.0 * PX) * 6.283 + lv1) + 0.02 * math.sin(s / (2.3 * PX) * 6.283 + lv2)
                    shade = along * (0.94 + 0.06 * tws) * (1.0 + 0.07 * streak)
                    alb[yy, xx, 0] = cr * shade; alb[yy, xx, 1] = cg * shade; alb[yy, xx, 2] = cb * shade
                    T[yy, xx, 0] = tx; T[yy, xx, 1] = ty
                    mat[yy, xx] = matid
                    cov[yy, xx] = fuzzcov
                    sidm[yy, xx] = sid
        s0 += seg


@njit(cache=True)
def squeeze_along(h, mat, stamp, sid, pts, rad, amount, keepmat):
    """Pinch laid strands under a couching bar: h *= 1 - amount*exp(-(d/rad)^2) for pixels of material keepmat."""
    H, W = h.shape
    n = pts.shape[0]
    R = rad * 2.5
    for i in range(n - 1):
        ax = pts[i, 0]; ay = pts[i, 1]; bx = pts[i + 1, 0]; by = pts[i + 1, 1]
        abx = bx - ax; aby = by - ay; ll = abx * abx + aby * aby + 1e-9
        x0 = max(0, int(min(ax, bx) - R - 1)); x1 = min(W, int(max(ax, bx) + R + 2))
        y0 = max(0, int(min(ay, by) - R - 1)); y1 = min(H, int(max(ay, by) + R + 2))
        for yy in range(y0, y1):
            for xx in range(x0, x1):
                if mat[yy, xx] != keepmat or stamp[yy, xx] == sid: continue
                px = xx - ax; py = yy - ay
                t = (px * abx + py * aby) / ll
                if t < 0 or t > 1: continue
                dx = px - t * abx; dy = py - t * aby
                d2 = (dx * dx + dy * dy) / (rad * rad)
                if d2 < 6.25:
                    stamp[yy, xx] = sid
                    f = 1 - amount * math.exp(-d2)
                    if h[yy, xx] > 0.05:
                        h[yy, xx] = 0.05 + (h[yy, xx] - 0.05) * f
