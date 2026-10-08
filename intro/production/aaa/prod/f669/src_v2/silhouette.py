"""Art direction for S09 / f669: the KING-SHAPED VOID.

The baked 'king' group was cut by a coarse hint polygon (hints/p1_oath.json), so a plain unpick leaves the polygon's
straight sides (throne backrest and wood inside the polygon are removed too) and some ermine / cape stitches just
outside it stay behind as debris.  This module re-partitions the record with a hand-traced silhouette of the king
(hair, ermine cape, sleeves, robe and the hand on the table), traced on the source panel (source px, 5 px/mm):

  * king entries whose midpoint lies OUTSIDE the silhouette are KEPT (throne backrest / wood: the throne stays),
  * ground entries whose midpoint lies INSIDE the silhouette are UNPICKED with the king (his cape debris).
"""
import numpy as np, cv2

# hand-traced on p1_oath.png (source px), clockwise from the left end of the crown band
KING_SIL_SRC = np.array([
    (1254.3, 604.3), (1250.7, 645.7), (1245.7, 695.7), (1243.6, 738.6), (1211.4, 751.4), (1175.7, 772.9),
    (1140.0, 792.0), (1117.0, 822.0), (1112.0, 852.9), (1104.3, 888.6), (1090.0, 938.6), (1079.3, 988.6),
    (1075.7, 1024.3), (1100.7, 1052.9), (1111.4, 1102.9), (1129.3, 1152.9), (1147.1, 1188.6), (1160.0, 1188.6),
    (1165.0, 1240.0), (1172.1, 1255.0), (1290.0, 1255.0), (1298.6, 1240.0), (1300.7, 1196.0), (1597.1, 1196.0),
    (1598.6, 1102.9), (1607.9, 1060.0), (1647.1, 1040.0), (1677.9, 1024.3), (1679.3, 995.7), (1668.6, 945.7),
    (1654.3, 895.7), (1632.9, 845.7), (1604.3, 795.7), (1557.9, 754.3), (1511.4, 738.6), (1507.9, 688.6),
    (1504.3, 638.6), (1497.1, 604.3)], np.float32)


def sil_mm():
    """silhouette in sheet mm."""
    return KING_SIL_SRC / 5.0 + 20.0


def sil_mask(x0_px, y0_px, w, h, PX):
    """filled silhouette mask (uint8 0/1) for a window whose pixel (0,0) is sheet px (x0_px, y0_px) at PX px/mm."""
    p = (sil_mm() * PX - np.array([x0_px, y0_px], np.float32)) * 8
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [np.round(p).astype(np.int32)], 1, cv2.LINE_8, shift=3)
    return m


def inside(pts_mm):
    """bool per point (sheet mm)."""
    poly = sil_mm().astype(np.float32)
    return np.array([cv2.pointPolygonTest(poly, (float(x), float(y)), False) >= 0 for x, y in pts_mm], bool)


def _chaikin(p, it=3):
    for _ in range(it):
        q = np.empty((2 * len(p) - 2, 2), np.float32)
        q[0::2] = 0.75 * p[:-1] + 0.25 * p[1:]
        q[1::2] = 0.25 * p[:-1] + 0.75 * p[1:]
        p = np.vstack([p[:1], q, p[-1:]])
    return p


def underdrawing_paths_mm():
    """the designer's ink line of the king's silhouette (sheet mm): left flank from the hair to the table, right flank
    from the table to the hair (the crown hides the top; the hem and the hand on the table are not outlined)."""
    P = KING_SIL_SRC
    left = P[0:17]            # (1254,604) .. (1147,1189)
    right = P[23:38]          # (1597,1196) .. (1497,604)
    return [(_chaikin(left) / 5.0 + 20.0), (_chaikin(right) / 5.0 + 20.0)]


def draw_underdrawing(H, W, x0_px, y0_px, PX, seed=0):
    """ud layer (0..1) in the bake's style: 0.42 mm line, small wobble, uneven ink, slight bleed."""
    r = np.random.default_rng(seed)
    ud = np.zeros((H, W), np.float32)
    for p in underdrawing_paths_mm():
        q = p * PX - np.array([x0_px, y0_px], np.float32)
        seg = np.linalg.norm(np.diff(q, axis=0), axis=1); sa = np.concatenate([[0], np.cumsum(seg)])
        ss = np.arange(0, sa[-1], 0.3 * PX)
        q = np.stack([np.interp(ss, sa, q[:, 0]), np.interp(ss, sa, q[:, 1])], 1)
        wob = np.convolve(r.normal(0, 1.0 * PX, len(q)), np.ones(15) / 15, 'same') * 1.6 + 0.25 * PX * np.sin(np.arange(len(q)) * 0.21 + r.uniform(0, 6))
        nrm = np.gradient(q, axis=0)[:, ::-1] * np.array([-1, 1]); nrm /= (np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-6)
        q = q + nrm * wob[:, None]
        # broken into strokes (the designer lifts the pen)
        i = 0
        while i < len(q) - 2:
            L = int(r.integers(22, 80))
            seg_q = q[i:i + L]
            if len(seg_q) >= 2:
                cv2.polylines(ud, [np.round(seg_q * 4).astype(np.int32)], False, float(r.uniform(0.55, 1.0)),
                              max(1, int(round(0.50 * PX))) * 4 // 4, cv2.LINE_AA, shift=2)
            i += L + int(r.integers(1, 5))
    ud = cv2.GaussianBlur(ud, (0, 0), sigmaX=0.10 * PX, sigmaY=0.07 * PX)
    ud *= (0.8 + 0.4 * r.random(ud.shape).astype(np.float32))
    return np.clip(ud, 0, 1)


# ---------------------------------------------------------------------------------------------- v2: ragged boundary
def _hash2(ix, iy, seed):
    v = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
    return (((v ^ (v >> 16)) & 0xFFFF) / 65535.0) * 2.0 - 1.0


def vn_pts(x, y, scale, seed):
    """value noise in [-1,1] at arbitrary points (mm), lattice cell = scale mm (translation invariant)."""
    x = np.asarray(x, np.float64) / scale; y = np.asarray(y, np.float64) / scale
    xi, yi = np.floor(x), np.floor(y); fx, fy = x - xi, y - yi
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    a = _hash2(xi, yi, seed); b = _hash2(xi + 1, yi, seed); c = _hash2(xi, yi + 1, seed); d = _hash2(xi + 1, yi + 1, seed)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def signed_dist_mm(pts_mm):
    """distance (mm) of points to the silhouette outline, positive inside."""
    poly = sil_mm().astype(np.float32)
    return np.array([cv2.pointPolygonTest(poly, (float(x), float(y)), True) for x, y in pts_mm], np.float64)


def inside_ragged(pts_mm, amp=2.2, scale=6.5, seed=17, jitter=0.9):
    """like inside(), but the cut line wanders (+-amp mm over ~scale mm) and each strand gets its own +-jitter mm:
    a hand-unpicked edge, not a ruler-straight one."""
    pts = np.asarray(pts_mm, np.float64)
    d = signed_dist_mm(pts)
    n = 0.65 * vn_pts(pts[:, 0], pts[:, 1], scale, seed) + 0.35 * vn_pts(pts[:, 0], pts[:, 1], scale * 0.37, seed + 5)
    j = _hash2(np.floor(pts[:, 0] * 20), np.floor(pts[:, 1] * 20), seed + 9)
    return (d + amp * n + jitter * j) >= 0
