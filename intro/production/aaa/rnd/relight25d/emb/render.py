"""Frontal (rostrum) camera: relight in texture space, halo, crop/scale to screen, fibres at screen res, grade."""
import math, time
import numpy as np, cv2
from .shade import relight, normals, ambient_occlusion, light_vec
from .fibres import halo, render_fibres
from .core import grade


def prepare(m):
    m['N'] = normals(m['h'], m['PX'])
    m['ao'] = ambient_occlusion(m['h'], m['PX'])
    return m


def spot(shape, PX, cx_mm, cy_mm, r_mm, floor=0.55, aspect=1.0):
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot((xx / PX - cx_mm) / aspect, yy / PX - cy_mm) / r_mm
    return (floor + (1 - floor) * np.exp(-d * d)).astype(np.float32)


def frontal(m, view, out_wh, light, fib=None, extra_vis=None, kmap=None, exposure=0.85, grain=0.012, seed=0,
            return_linear=False, timing=None, undul=None):
    """view: (x0, y0, w, h) in map px (may be fractional). light: dict for relight()."""
    t0 = time.time()
    H, W = m['h'].shape
    reg = (max(int(view[0]) - 80, 0), max(int(view[1]) - 80, 0), min(int(view[0] + view[2]) + 80, W), min(int(view[1] + view[3]) + 80, H))
    if undul is not None:
        x0r, y0r, x1r, y1r = reg
        Nf = m['N'].copy()
        hU = (m['h'] + undul).astype(np.float32)
        Nf[y0r:y1r, x0r:x1r] = normals(hU[y0r:y1r, x0r:x1r], m['PX'])
        m = dict(m, h=hU, N=Nf)
    col, vis = relight(m, N=m.get('N'), ao=m.get('ao'), kmap=kmap, extra_vis=extra_vis, region=reg, **light)
    col = halo(col, m)
    t1 = time.time()
    x0, y0, w, h = view
    Wo, Ho = out_wh
    sx, sy = Wo / w, Ho / h
    M = np.array([[sx, 0, -x0 * sx], [0, sy, -y0 * sy]], np.float32)
    if sx < 1:  # prefilter for minification
        sig = 0.5 / sx
        colf = cv2.GaussianBlur(col, (0, 0), sig * 0.8)
    else:
        colf = col
    img = cv2.warpAffine(colf, M, (Wo, Ho), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    t2 = time.time()
    if fib is not None:
        PX = m['PX']
        L = light_vec(light.get('az', 135), light.get('el', 22))
        key = np.array(light.get('key', (1.0, 0.92, 0.80)), np.float32) * light.get('key_i', 2.3)
        fill = np.array(light.get('fill', (0.80, 0.86, 1.0)), np.float32) * light.get('fill_i', 0.30)
        if kmap is not None:
            key = key * float(np.median(kmap))
        def project(P):
            Q = np.empty(P.shape[:2] + (2,), np.float32)
            Q[..., 0] = (P[..., 0] * PX - x0) * sx; Q[..., 1] = (P[..., 1] * PX - y0) * sy
            return Q, -P[..., 2]
        render_fibres(img, fib, L, key, fill, vis, project, width=min(1.0, sx * 1.1))
    t3 = time.time()
    if timing is not None:
        timing.update(relight=t1 - t0, warp=t2 - t1, fibres=t3 - t2)
    if return_linear:
        return img
    return grade(img, exposure=exposure, grain=grain, seed=seed)


def undulation(shape, PX, t=0.0, amp=0.9, seed=3, sway=1.0):
    """low-frequency height (mm) of a hanging linen: mostly vertical folds + soft diagonal waves; t in seconds sways it."""
    H, W = shape
    r = np.random.default_rng(seed)
    x = np.arange(W, dtype=np.float32) / PX; y = np.arange(H, dtype=np.float32) / PX
    X, Y = np.meshgrid(x, y)
    U = np.zeros((H, W), np.float32)
    for k in range(5):
        lam = r.uniform(45, 120); ang = r.normal(0, 0.18); ph = r.uniform(0, 6.28)
        w = 2 * np.pi / lam; per = r.uniform(3.0, 6.0)
        a = amp * r.uniform(0.35, 1.0) / (1 + 0.4 * k)
        U += a * np.sin(w * (X * math.cos(ang) + Y * math.sin(ang)) + ph + sway * 0.35 * math.sin(2 * math.pi * t / per + ph))
    # folds fade toward the top (hanging rod) and grow toward the bottom
    U *= (0.55 + 0.45 * Y / Y.max())
    return U.astype(np.float32)
