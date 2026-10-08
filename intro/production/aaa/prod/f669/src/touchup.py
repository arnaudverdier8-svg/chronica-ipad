"""v3 touch-up (client round 2): three local fixes on the accepted f669 composition, each one a small function that works
on the shot's own maps / linear frame (no library file is edited).

  (a) tone_emblem(m)        the white horse-head of the green lord's shield (a cream wool charge of albedo 0.5-0.66 on a robe
                            of albedo 0.03-0.08, lit only by the violet night fill) read as a lavender-white blob, the
                            brightest thing in the right third.  It is re-dyed in the albedo window as undyed wool a century
                            old: dun / smoke-brown, ~0.3x, keeping the stitch texture, then ages like everything else.
  (b) (strands: see loose.py / threads3d.py)
  (c) pool_contrast(...)    more contrast inside the candle pool only (a pool-weighted S-curve on scene-linear light) and
      metal_pop(...)        the crown's gold: deep bronze darks, hot narrow glints, so it reads as metal not as cream wool.
"""
import math
import numpy as np, cv2
from chron.color import lin2oklab, oklab2lin

# ------------------------------------------------------------------------------------------------ (a) the emblem
HORSE_BOX_MM = (473.0, 200.0, 497.0, 224.0)          # x0, y0, x1, y1 sheet mm: the shield of the green lord (bare-wool charge inside it)
HORSE_GAIN = np.array([0.46, 0.35, 0.22], np.float32)    # undyed wool, a century of soot and dust: dun, not white (x albedo)


def tone_emblem(m, gain=HORSE_GAIN):
    """re-dye the pale charge (the white horse head) in the albedo window m (any mip), before the ageing pass.
    Mask: cream (OKLab L > 0.60, chroma < 0.12) wool inside the shield box, closed and filled (the mane's tan strokes and the
    raven's feet that sit inside the head), then feathered 0.35 mm so the stitch outline keeps its edge but gets no halo."""
    PX = m['PX']; ox, oy = m['origin_mm']
    H, W = m['mat'].shape
    x0, y0, x1, y1 = HORSE_BOX_MM
    a0, b0 = int(math.floor((x0 - ox) * PX)), int(math.floor((y0 - oy) * PX))
    a1, b1 = int(math.ceil((x1 - ox) * PX)), int(math.ceil((y1 - oy) * PX))
    a0, b0, a1, b1 = max(a0, 0), max(b0, 0), min(a1, W), min(b1, H)
    if a1 - a0 < 4 or b1 - b0 < 4: return m
    sub = m['alb'][b0:b1, a0:a1].astype(np.float32)
    mat = m['mat'][b0:b1, a0:a1]
    lab = lin2oklab(sub)
    C = np.hypot(lab[..., 1], lab[..., 2])
    cream = ((lab[..., 0] > 0.60) & (C < 0.12) & (mat == 1)).astype(np.uint8)
    n, cc, st, _ = cv2.connectedComponentsWithStats(cream)
    if n <= 1: return m
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))               # the horse head is the one large cream component
    if st[big, cv2.CC_STAT_AREA] < 3.0 * PX * PX: return m          # < 3 mm2: not the horse head (the window clipped it)
    head = (cc == big).astype(np.uint8)
    k = max(3, int(round(1.1 * PX)) | 1)
    head = cv2.morphologyEx(head, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    cnts, _ = cv2.findContours(head, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(head)
    cv2.drawContours(filled, cnts, -1, 1, -1)
    # the gold border of the shield must not be caught: keep only pixels that are not saturated gold (chroma 0.12+ and hue 60-100)
    hue = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    gold = (C > 0.095) & (hue > 55) & (hue < 100) & (lab[..., 0] > 0.55)
    w = filled.astype(np.float32) * (1 - 0.85 * gold.astype(np.float32))
    w = cv2.GaussianBlur(w, (0, 0), 0.35 * PX)
    # the part of the head's hull that is not wool (dark raven feet, green leaves) is already dark: the gain only matters on bright pixels
    g = 1 + (gain[None, None, :] - 1) * w[..., None]
    m['alb'][b0:b1, a0:a1] = (sub * g).astype(m['alb'].dtype)
    return m


# ------------------------------------------------------------------------------------------------ (c) contrast in the pool
def _E(name, default):
    import os
    return float(os.environ.get(name, default))


POOL_C = dict(cx=_E('F669_PCC_X', 297.0), cy=_E('F669_PCC_Y', 190.0), rx=_E('F669_PCC_RX', 62.0), ry_up=_E('F669_PCC_RYU', 92.0),
              ry_dn=_E('F669_PCC_RYD', 78.0), p=3.0)
K_SHADOW = _E('F669_KSH', 0.26)          # exponent gain below the pivot (deeper shadows)
K_LIGHT = _E('F669_KLT', 0.08)           # above the pivot (a touch more punch, not a brighter pool)
Y_PIVOT = _E('F669_YPIV', 0.075)         # scene-linear luminance of the void's mid-tone (measured, see README)


def pool_weight(view, out_wh):
    """0..1 weight of the contrast boost on the screen: ~1 over the void, the crown and the throne, ~0.02 at the lords' faces
    (x 198 / 396 mm), a super-gaussian so it does not leak onto the red / blue lords at the rim of the pool."""
    s = view['px_per_mm']
    x0 = view['cx_mm'] - out_wh[0] / 2 / s; y0 = view['cy_mm'] - out_wh[1] / 2 / s
    xs = x0 + (np.arange(out_wh[0], dtype=np.float32) + 0.5) / s
    ys = y0 + (np.arange(out_wh[1], dtype=np.float32) + 0.5) / s
    P = POOL_C
    wx = np.exp(-(np.abs(xs - P['cx']) / P['rx']) ** P['p'])
    ry = np.where(ys < P['cy'], P['ry_up'], P['ry_dn'])
    wy = np.exp(-(np.abs(ys - P['cy']) / ry) ** P['p'])
    return (wy[:, None] * wx[None, :]).astype(np.float32)


def pool_contrast(lin, view, out_wh, k_shadow=None, k_light=None, pivot=None):
    """local contrast in scene-linear light, hue preserving, weighted by the pool: Y' = Y (Y / Yp)^(k w): shadows (needle
    holes, underdrawing, weave gaps) go deeper, the mid / high end gains a little punch; highlights above ~4 Yp are left alone
    (the crown gold is handled by metal_pop)."""
    k_shadow = K_SHADOW if k_shadow is None else k_shadow
    k_light = K_LIGHT if k_light is None else k_light
    pv = Y_PIVOT if pivot is None else pivot
    w = pool_weight(view, out_wh)
    Y = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    x = np.clip(Y / pv, 1e-4, None)
    k = np.where(x < 1.0, k_shadow, k_light) * w * (1.0 / (1.0 + (x / 4.0) ** 2))
    fac = np.exp(k * np.log(x))                 # (Y/Yp)^k
    return lin * fac[..., None], w


# ------------------------------------------------------------------------------------------------ (c) the crown's gold
MP = dict(k_dark=_E('F669_MK_DARK', 1.0), k_hot=_E('F669_MK_HOT', 1.4), k_detail=_E('F669_MK_DET', 1.1), q_ref=_E('F669_MK_Q', 55.0), sigma=_E('F669_MK_SIG', 1.4), ramp=_E('F669_MK_RAMP', 0.8), floor=_E('F669_MK_FLOOR', 0.20))


def metal_pop(rgb, metal, alpha, k_dark=None, k_hot=None, k_detail=None, q_ref=None):
    """make the crown's couched gold read as METAL: wrapped Japan gold is a mirror-ish dark amber with narrow hot glints, not a
    uniform cream.  rgb: the slip layer (linear), metal: 0..1 mask of the metal-thread pixels, alpha: slip coverage.
    1. local contrast (thread-scale: Y / blur(Y)) so every wrapped cord has its own dark-to-bright run,
    2. a tone curve around the lit gold's 70th percentile: mids sink toward deep amber / bronze (x^(1+k_dark)), glints above it
       gain (1 + k_hot (x - 1)),
    3. colour follows the tone: darks go orange-bronze (the gold's own absorption), glints go warm yellow-white."""
    k_dark = MP['k_dark'] if k_dark is None else k_dark
    k_hot = MP['k_hot'] if k_hot is None else k_hot
    k_detail = MP['k_detail'] if k_detail is None else k_detail
    q_ref = MP['q_ref'] if q_ref is None else q_ref
    m = np.clip(metal, 0, 1) * (alpha > 0.5)
    if m.sum() < 50: return rgb
    Y = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    ref = float(np.percentile(Y[m > 0.5], q_ref))
    Yb = cv2.GaussianBlur(Y, (0, 0), MP['sigma'])
    det = np.clip(Y / (Yb + 1e-4), 0.35, 2.5)
    x = Y / max(ref, 1e-4) * det ** k_detail
    xc = np.where(x < 1.0, x ** (1.0 + k_dark), 1.0 + k_hot * (x - 1.0) / (1.0 + 0.45 * np.maximum(x - 1.0, 0)))   # soft knee: glints, not a white-out
    xc = np.maximum(xc, MP['floor'])               # the grooves are deep amber-bronze, not black
    Yn = ref * xc
    W709 = np.array([0.2126, 0.7152, 0.0722], np.float32)
    # chromaticity follows the tone like polished gold: dark bronze in the grooves, saturated amber-gold in the body, pale gold and
    # warm white only in the narrow glints (a piecewise-linear ramp over the tone x = Y / reference)
    stops = np.array([0.0, 0.45, 1.00, 2.00, 3.6], np.float32)
    cols = np.array([[1.0, 0.40, 0.10], [1.0, 0.54, 0.16], [1.0, 0.66, 0.24], [1.0, 0.80, 0.40], [1.0, 0.92, 0.66]], np.float32)
    cols = cols / (cols @ W709)[:, None]
    tone = np.clip(x, 0, 3.6)
    ramp = np.stack([np.interp(tone, stops, cols[:, c]) for c in range(3)], -1).astype(np.float32)
    own = rgb / np.maximum(Y, 1e-5)[..., None]
    own = own / np.maximum(own @ W709, 1e-5)[..., None]
    chroma = MP['ramp'] * ramp + (1 - MP['ramp']) * own
    out = chroma * Yn[..., None]
    mm = m[..., None]
    return rgb * (1 - mm) + out * mm
