"""Thread-direction fields (doubled-angle c2, s2 = cos 2a, sin 2a) and the gate-G6 per-region decision:
  1. structure tensor if coherence >= 0.35 over >= 70 % of the region,
  2. else for laid-and-couched regions: a region-axis field (constant angle from the principal axis or a hint,
     bent by <= 15 deg over ~30 mm by smooth noise) -> straight / gently curved parallel strands, no whorls,
  3. else (needle painting: faces, small forms): tensor blended with the region shape (R25 behaviour),
  4. metal motifs: contour-parallel (isolines of the distance transform)."""
import math
import numpy as np, cv2
from .util import vnoise


def orient_tensor(lum, sigma_g_px, sigma_t_px, mask=None):
    """(c2, s2, coherence) of the THREAD direction (perpendicular to the dominant gradient)."""
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


def angle_field(ang_rad):
    return np.cos(2 * ang_rad).astype(np.float32), np.sin(2 * ang_rad).astype(np.float32)


def principal_angle(mask):
    """angle (deg, image coords, y down) of the region's long axis."""
    ys, xs = np.nonzero(mask)
    if len(xs) < 3: return 90.0
    x = xs - xs.mean(); y = ys - ys.mean()
    cxx, cyy, cxy = (x * x).mean(), (y * y).mean(), (x * y).mean()
    return math.degrees(0.5 * math.atan2(2 * cxy, cxx - cyy))


def region_axis_field(mask, PX, angle_deg=None, bend_deg=12.0, scale_mm=30.0, seed=0, origin_mm=(0.0, 0.0)):
    """constant angle (principal axis or hint) bent by <= bend_deg with smooth noise of ~scale_mm."""
    if angle_deg is None:
        angle_deg = principal_angle(mask)
    H, W = mask.shape
    nz = vnoise(origin_mm[0], origin_mm[1], H, W, PX, scale_mm, seed, 1)       # ~[-1, 1]
    ang = np.radians(angle_deg + bend_deg * np.clip(nz * 2.2, -1, 1)).astype(np.float32)
    return angle_field(ang)


def contour_parallel_field(mask, PX, smooth_mm=0.6):
    """thread direction along the isolines of the distance transform (couched gold follows the shape)."""
    d = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5).astype(np.float32)
    d = cv2.GaussianBlur(d, (0, 0), smooth_mm * PX)
    gx = cv2.Sobel(d, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(d, cv2.CV_32F, 0, 1, ksize=3)
    # gradient direction g; thread = perpendicular: doubled angle of perp = -(doubled angle of g)
    Jxx, Jxy, Jyy = gx * gx, gx * gy, gy * gy
    s = smooth_mm * PX
    Jxx = cv2.GaussianBlur(Jxx, (0, 0), s); Jxy = cv2.GaussianBlur(Jxy, (0, 0), s); Jyy = cv2.GaussianBlur(Jyy, (0, 0), s)
    return (-(Jxx - Jyy)).astype(np.float32), (-2 * Jxy).astype(np.float32)


def coherent_fraction(coh, mask, thr=0.35):
    v = coh[mask > 0]
    return float((v >= thr).mean()) if len(v) else 0.0


def select_field(lum_c, mask_c, PX, mode='auto', laid=True, angle_deg=None, sig_t_mm=3.0, w_shape=0.3, seed=0,
                 origin_mm=(0.0, 0.0), coh_thr=0.35, coh_frac=0.70, bend_deg=12.0):
    """returns (field (c2, s2), chosen_mode).  mode: auto | tensor | axis | blend | contour | const."""
    if mode == 'contour':
        return contour_parallel_field(mask_c, PX), 'contour'
    if mode == 'const':
        return const_field(mask_c.shape, angle_deg or 0.0), 'const'
    if mode == 'axis':
        return region_axis_field(mask_c, PX, angle_deg, bend_deg, 30.0, seed, origin_mm), 'axis'
    a = orient_tensor(lum_c, 0.35 * PX, sig_t_mm * PX, mask=mask_c)
    if mode == 'tensor':
        return (a[0], a[1]), 'tensor'
    mb = cv2.GaussianBlur(mask_c.astype(np.float32), (0, 0), 1.5 * PX)
    b = orient_tensor(mb, 0.5 * PX, 2.5 * PX, mask=mask_c)
    if mode == 'blend':
        return blend_fields([a, b], [1.0, w_shape]), 'blend'
    frac = coherent_fraction(a[2], mask_c, coh_thr)
    if frac >= coh_frac:
        return blend_fields([a, b], [1.0, 0.15]), 'tensor'
    if laid:
        return region_axis_field(mask_c, PX, angle_deg, bend_deg, 30.0, seed, origin_mm), 'axis'
    return blend_fields([a, b], [1.0, w_shape]), 'blend'
