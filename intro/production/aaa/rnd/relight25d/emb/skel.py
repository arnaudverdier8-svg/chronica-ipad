"""Thin dark-line masks to skeletons and trace them into polylines (for stem-stitch outlines)."""
import numpy as np, cv2
from numba import njit


@njit(cache=True)
def zhang_suen(img):
    im = img.copy()
    H, W = im.shape
    changed = True
    while changed:
        changed = False
        for it in range(2):
            rem = []
            for y in range(1, H - 1):
                for x in range(1, W - 1):
                    if im[y, x] == 0: continue
                    p2 = im[y - 1, x]; p3 = im[y - 1, x + 1]; p4 = im[y, x + 1]; p5 = im[y + 1, x + 1]
                    p6 = im[y + 1, x]; p7 = im[y + 1, x - 1]; p8 = im[y, x - 1]; p9 = im[y - 1, x - 1]
                    B = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
                    if B < 2 or B > 6: continue
                    A = ((p2 == 0 and p3 == 1) + (p3 == 0 and p4 == 1) + (p4 == 0 and p5 == 1) + (p5 == 0 and p6 == 1) +
                         (p6 == 0 and p7 == 1) + (p7 == 0 and p8 == 1) + (p8 == 0 and p9 == 1) + (p9 == 0 and p2 == 1))
                    if A != 1: continue
                    if it == 0:
                        if p2 * p4 * p6 != 0 or p4 * p6 * p8 != 0: continue
                    else:
                        if p2 * p4 * p8 != 0 or p2 * p6 * p8 != 0: continue
                    rem.append((y, x))
            for (y, x) in rem:
                im[y, x] = 0
            if len(rem) > 0: changed = True
    return im


@njit(cache=True)
def _nbrs(sk, y, x):
    H, W = sk.shape
    n = 0
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            if dy == 0 and dx == 0: continue
            yy = y + dy; xx = x + dx
            if 0 <= yy < H and 0 <= xx < W and sk[yy, xx]: n += 1
    return n


@njit(cache=True)
def _crossing(sk, y, x):
    H, W = sk.shape
    oy = (-1, -1, 0, 1, 1, 1, 0, -1); ox = (0, 1, 1, 1, 0, -1, -1, -1)
    v = np.zeros(8, np.uint8)
    for k in range(8):
        yy = y + oy[k]; xx = x + ox[k]
        if 0 <= yy < H and 0 <= xx < W and sk[yy, xx]: v[k] = 1
    c = 0
    for k in range(8):
        if v[k] == 0 and v[(k + 1) % 8] == 1: c += 1
    return c


@njit(cache=True)
def trace_skeleton(sk, out, off):
    """trace skeleton pixels into paths; paths stop at junctions. returns (n_paths, n_pts)."""
    H, W = sk.shape
    vis = np.zeros((H, W), np.uint8)
    deg = np.zeros((H, W), np.int32)
    for y in range(H):
        for x in range(W):
            if sk[y, x]:
                n = _nbrs(sk, y, x)
                c = _crossing(sk, y, x)
                deg[y, x] = 1 if n <= 1 else (c if c >= 3 else 2)
    npth = 0; npt = 0; off[0] = 0
    for pas in range(2):
        for y0 in range(H):
            for x0 in range(W):
                if not sk[y0, x0] or vis[y0, x0]: continue
                if pas == 0 and deg[y0, x0] == 2: continue  # first pass start at ends / junctions
                # walk each unvisited branch from this pixel
                for dy0 in range(-1, 2):
                    for dx0 in range(-1, 2):
                        if dy0 == 0 and dx0 == 0: continue
                        y1 = y0 + dy0; x1 = x0 + dx0
                        if not (0 <= y1 < H and 0 <= x1 < W) or not sk[y1, x1] or vis[y1, x1]: continue
                        if npt + 2 >= out.shape[0]: return npth, npt
                        out[npt, 0] = x0; out[npt, 1] = y0; npt += 1
                        y = y1; x = x1
                        while True:
                            vis[y, x] = 1
                            out[npt, 0] = x; out[npt, 1] = y; npt += 1
                            if npt + 2 >= out.shape[0]: break
                            if deg[y, x] > 2 and not (y == y1 and x == x1): break
                            nxt = False
                            for dy in range(-1, 2):
                                for dx in range(-1, 2):
                                    if dy == 0 and dx == 0: continue
                                    yy = y + dy; xx = x + dx
                                    if 0 <= yy < H and 0 <= xx < W and sk[yy, xx] and not vis[yy, xx]:
                                        if not (yy == y0 and xx == x0):
                                            y = yy; x = xx; nxt = True; break
                                if nxt: break
                            if not nxt: break
                        npth += 1; off[npth] = npt
                vis[y0, x0] = 1
    return npth, npt


def skeleton_paths(mask, min_len_px=3):
    sk = zhang_suen((mask > 0).astype(np.uint8))
    out = np.zeros((int(sk.sum()) * 3 + 100, 2), np.float32)
    off = np.zeros(int(sk.sum()) + 10, np.int64)
    n, npt = trace_skeleton(sk, out, off)
    paths = [out[off[i]:off[i + 1]].copy() for i in range(n)]
    return [p for p in paths if len(p) >= min_len_px], sk


def merge_paths(paths, join_px=2.5):
    """greedily join paths whose endpoints touch and directions agree (longer, smoother outlines)."""
    paths = [p for p in paths if len(p) >= 2]
    changed = True
    while changed:
        changed = False
        ends = []
        for i, p in enumerate(paths):
            ends.append((i, 0, p[0], p[min(3, len(p) - 1)] - p[0]))
            ends.append((i, 1, p[-1], p[max(-4, -len(p))] - p[-1]))
        used = set()
        for a in range(len(ends)):
            i, ei, pa, da = ends[a]
            if i in used: continue
            best = None
            for b in range(len(ends)):
                j, ej, pb, db = ends[b]
                if j == i or j in used: continue
                d = np.hypot(*(pa - pb))
                if d > join_px: continue
                na, nb = np.linalg.norm(da) + 1e-6, np.linalg.norm(db) + 1e-6
                cos = (da @ db) / na / nb   # outward directions should be opposite
                if cos > -0.5: continue
                if best is None or d < best[0]: best = (d, j, ej)
            if best is None: continue
            _, j, ej = best
            pi = paths[i] if ei == 1 else paths[i][::-1]
            pj = paths[j] if ej == 0 else paths[j][::-1]
            paths[i] = np.vstack([pi, pj]); paths[j] = np.zeros((0, 2), np.float32)
            used.add(i); used.add(j); changed = True
        paths = [p for p in paths if len(p) >= 2]
    return paths
