"""f899 v3 footprint ('ghost') writer (v2 text follows; v3 = sparser, smaller needle holes, fewer bleeds, faint underdrawing: the director found the v2 dot halos noisy)

f899 v2 footprint ('ghost') writer: a runtime replacement of chron.motifs.panel._ghost (the library file is untouched).

Differences from the library version (all in response to the review of the first f899 proof):
  * needle holes are larger and varied (0.20-0.42 mm radius, spacing 0.8-1.4 mm after a variable Poisson thinning), with a raised lip that catches the
    raking light (height +0.12) and a faint red-brown pigment bleed around ~40 % of them (the underdrawing ink wicking into the weave);
  * the protected linen is only FLATTENED here (-30 % relief); the colour match (slightly fresher, never a cool slab) is done in plate.py where the
    surrounding aged linen is known.
"""
import numpy as np, cv2
from chron import stitch as S
from chron.color import hex_lin


def ghost_v3(m, rec, gsel, gmask_canvas, ud_paths, PX, seed=0, ud_col='#6E3326', ud_alpha=0.5, hole_spacing_mm=2.0):
    H, W = m['h'].shape
    r = np.random.default_rng(seed)
    s = cv2.GaussianBlur(gmask_canvas.astype(np.float32), (0, 0), 0.4 * PX)
    m['h'][:] = np.where(m['h'] > 0, m['h'] * (1 - 0.45 * s), m['h'])
    ud = np.zeros((H, W), np.float32)
    for p in ud_paths:
        q = S.smooth_poly(S.resample(p.astype(np.float32), 0.3 * PX), 2) + r.normal(0, 0.10 * PX, 2).astype(np.float32)
        cv2.polylines(ud, [np.round(q).astype(np.int32)], False, float(r.uniform(0.6, 1.0)), max(1, int(round(0.42 * PX))), cv2.LINE_AA)
    ud = cv2.GaussianBlur(ud, (0, 0), sigmaX=0.10 * PX, sigmaY=0.07 * PX)
    ud *= (0.8 + 0.4 * r.random(ud.shape).astype(np.float32))
    ud = np.clip(ud, 0, 1)
    ink = hex_lin(ud_col)
    a = np.clip(ud * ud_alpha, 0, 0.6)[..., None]
    m['alb'][:] = m['alb'] * (1 - a) + (m['alb'] * ink / (m['alb'].mean() + 1e-3) * 0.9) * a
    # candidate holes: (1) the couching ties of the outline cords (every ~3 mm along the figure's silhouette: the one place a footprint is allowed to read
    # as an outline), (2) a thin scatter of the interior strand ends.  Both Poisson-thinned, outline spacing 2.3 mm, interior 3.3 mm.
    pts_o, pts_i = [], []
    for k in gsel:
        if rec['typ'][k] != 0:
            continue
        kd = rec['kind'][k]
        p = rec['P'][rec['off'][k]:rec['off'][k + 1]]
        if kd == S.K_CTIE:
            for e in (p[0], p[-1]):
                if r.random() < 0.42:
                    pts_o.append(e)
            continue
        if kd in (S.K_TIE, S.K_MTIE):
            continue
        if kd == S.K_CORD:
            pts_o.append(p[0]); pts_o.append(p[-1])
            continue
        if kd == S.K_SPLIT and (k % 5) != 0:
            continue
        pts_i.append(p[0]); pts_i.append(p[-1])
    keep = []
    grid = {}
    cellmax = 3.4 * PX

    def thin(pts, spacing_mm):
        if not pts:
            return
        pts = np.array(pts, np.float32)
        pts = pts[r.permutation(len(pts))]
        cell = spacing_mm * PX
        for p in pts:
            if not (0 <= p[0] < W and 0 <= p[1] < H):
                continue
            if not gmask_canvas[int(p[1]), int(p[0])]:
                continue
            md = cell * r.uniform(0.9, 1.5)
            gx, gy = int(p[0] / cellmax), int(p[1] / cellmax)
            ok = True
            for dx in (-2, -1, 0, 1, 2):
                for dy in (-2, -1, 0, 1, 2):
                    for q in grid.get((gx + dx, gy + dy), ()):
                        if (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 < md * md:
                            ok = False; break
                    if not ok:
                        break
                if not ok:
                    break
            if ok:
                grid.setdefault((gx, gy), []).append(p); keep.append(p)
    thin(pts_o, 2.3)
    thin(pts_i, hole_spacing_mm * 1.65)
    hole = np.zeros((H, W), np.float32); bleed = np.zeros((H, W), np.float32)
    if keep:
        for p in keep:
            rad = r.uniform(0.15, 0.30) * PX
            cv2.circle(hole, (int(round(p[0] * 4)), int(round(p[1] * 4))), max(1, int(round(rad * 4))), 1.0, -1, cv2.LINE_AA, shift=2)
            if r.random() < 0.22:
                cv2.circle(bleed, (int(round(p[0] * 4)), int(round(p[1] * 4))), max(1, int(round(rad * 4))), float(r.uniform(0.5, 1.0)), -1, cv2.LINE_AA, shift=2)
    hole = cv2.GaussianBlur(hole, (0, 0), 0.07 * PX)
    rim = np.clip(cv2.GaussianBlur(hole, (0, 0), 0.26 * PX) * 1.7 - hole, 0, 1)
    m['h'][:] = m['h'] - 0.26 * hole + 0.12 * rim
    m['alb'][:] = m['alb'] * (1 - 0.40 * hole[..., None]) * (1 + 0.10 * rim[..., None])
    bl = np.clip(cv2.GaussianBlur(bleed, (0, 0), 0.40 * PX) * 2.2, 0, 1)[..., None]
    m['alb'][:] = m['alb'] * (1 - 0.30 * bl) + (m['alb'] * ink / (m['alb'].mean() + 1e-3) * 0.9) * (0.30 * bl)
    return dict(holes=hole, ud=ud)
