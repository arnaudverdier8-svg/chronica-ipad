"""Post: the single gold glint on the surviving chronicle thread, optical bloom (energy-conserving, thresholded), grade hand-off."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from s18common import *
from geometry import *
from thread_gold import thread_path

GOLD = np.array([1.0, 0.52, 0.05], np.float32)      # v2: palette gold (#FCD577 highlight / #C47E23 mid), not peach-cream; stays gold through the ACES shoulder


def glint_point(th, info, glint_u):
    u, v, X, Y, tt, gap = thread_path(th, info)
    i = int(np.argmin(np.abs(u - glint_u)))
    d = np.array([X[min(i + 4, len(X) - 1)] - X[max(i - 4, 0)], Y[min(i + 4, len(Y) - 1)] - Y[max(i - 4, 0)]])
    return float(X[i]), float(Y[i]), math.atan2(d[1], d[0])


def add_glint(img, X, Y, ang, peak=6.0, s=S_SCREEN):
    """specular catch on a thin metal thread: a hot core elongated along the thread + a thin slide streak (no flare, no cross)."""
    H, W = img.shape[:2]
    sx, sy = (X + WIN_W / 2) * s, (Y + WIN_H / 2) * s
    R = 48
    x0, y0 = int(round(sx)) - R, int(round(sy)) - R
    yy, xx = np.mgrid[y0:y0 + 2 * R + 1, x0:x0 + 2 * R + 1].astype(np.float32)
    dx, dy = xx - sx, yy - sy
    c, sn = math.cos(ang), math.sin(ang)
    a_ = dx * c + dy * sn; b_ = -dx * sn + dy * c
    core = np.exp(-0.5 * ((a_ / 1.9) ** 2 + (b_ / 0.85) ** 2))
    streak = np.exp(-0.5 * ((a_ / 7.0) ** 2 + (b_ / 0.7) ** 2)) * 0.16
    halo = np.exp(-0.5 * ((a_ / 4.0) ** 2 + (b_ / 3.0) ** 2)) * 0.05
    g = (core + streak + halo)[..., None] * GOLD * peak
    X0, Y0 = max(x0, 0), max(y0, 0); X1, Y1 = min(x0 + 2 * R + 1, W), min(y0 + 2 * R + 1, H)
    img[Y0:Y1, X0:X1] += g[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
    return img


def bloom(img, thr=0.9, k1=0.35, s1=7.0, k2=0.18, s2=26.0):
    """subtle optical bloom of scene highlights only (so the dark table stays clean)."""
    hi = np.maximum(img - thr, 0)
    return img + k1 * cv2.GaussianBlur(hi, (0, 0), s1) + k2 * cv2.GaussianBlur(hi, (0, 0), s2)
