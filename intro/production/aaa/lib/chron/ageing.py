"""Dye ageing as a PARAMETER (gate G8 / storyboard S09, S12, S19): aged vs fresh palette in OKLab, fading,
foxing, tidelines, linen yellowing; protected (ghost) linen stays fresher.  Bible 4.7: foxing #9C7046 multiply
15-35 %, clustered at edges; tidelines #7C5A38 20-40 % with a darker 1-2 mm edge; woad fades most.

  layers = bake_age_layers(shape, PX, seed, ...)      # baked once per sheet (stored as age_fox / age_tide / age_fade)
  alb_aged = apply_age(alb, mat, amount, layers)      # amount: scalar or HxW map in [0,1] (0 = as baked/fresh, 1 = aged)
  Revival (S19): amount_map = 1 - smoothstep(front(t) - x) per region, staggered."""
import math
import numpy as np, cv2
from .color import hex_lin, lin2oklab, oklab2lin, pal
from .util import vnoise, sstep


def bake_age_layers(shape, PX, seed=0, density=0.3, margin_px=0, tide=None, origin_mm=(0.0, 0.0)):
    """fox (0..1 spot strength), tide (0..1: 0.3 stain interior, 1 at the 1-2 mm edge), fade (0..1 light exposure).
    tide: optional list of dicts {c: [x_mm, y_mm] sheet mm, r_mm, aspect, seed}."""
    H, W = shape
    r = np.random.default_rng(seed)
    fox = np.zeros((H, W), np.float32)
    area_dm2 = (H / PX) * (W / PX) / 1e4
    n = int(7 * area_dm2 * density * 1.6)
    for _ in range(n):
        # clustered toward the edges: sample until accepted by an edge-weighted probability
        for _try in range(20):
            cx, cy = r.uniform(0, W), r.uniform(0, H)
            e = min(cx, W - cx, cy, H - cy) / (0.5 * min(W, H))
            if r.random() < 0.25 + 0.75 * (1 - e) ** 2:
                break
        for _k in range(r.integers(1, 6)):
            rad = r.uniform(0.25, 1.5) * PX
            ox, oy = r.normal(0, 2.5 * PX, 2)
            cv2.circle(fox, (int(cx + ox), int(cy + oy)), max(1, int(rad)), float(r.uniform(0.4, 1.0)), -1, cv2.LINE_AA)
    fox = cv2.GaussianBlur(fox, (0, 0), 0.35 * PX)
    fox = np.clip(fox, 0, 1)
    tid = np.zeros((H, W), np.float32)
    for t in (tide or []):
        cx, cy = t['c'][0] * PX, t['c'][1] * PX
        R = t['r_mm'] * PX; asp = t.get('aspect', 1.6)
        s = t.get('seed', seed + 3)
        x0, y0 = int(max(cx - R * asp * 1.4, 0)), int(max(cy - R * 1.4, 0))
        x1, y1 = int(min(cx + R * asp * 1.4, W)), int(min(cy + R * 1.4, H))
        if x1 <= x0 or y1 <= y0: continue
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        nz = vnoise(x0 / PX, y0 / PX, y1 - y0, x1 - x0, PX, 25.0, s, 3)
        d = np.hypot((xx - cx) / asp, yy - cy) / R + 0.22 * nz
        inside = sstep(1.0, 0.92, d) * 0.30
        edge = np.exp(-((d - 1.0) * R / (0.9 * PX)) ** 2)            # ~1-2 mm dark edge
        # a second, fainter inner ring (a later, smaller wetting)
        edge2 = 0.45 * np.exp(-((d - 0.72) * R / (0.7 * PX)) ** 2)
        tid[y0:y1, x0:x1] = np.maximum(tid[y0:y1, x0:x1], np.clip(inside + edge + edge2, 0, 1))
    xs = np.linspace(0, 1, W, dtype=np.float32)
    fade = 0.5 + 0.35 * (xs[None, :] - 0.5) + 0.25 * vnoise(origin_mm[0], origin_mm[1], H, W, PX, 120.0, seed + 9, 2)
    fade = np.clip(np.broadcast_to(fade, (H, W)), 0, 1).astype(np.float32)
    return dict(fox=fox.astype(np.float32), tide=tid, fade=fade)


def apply_age(alb, mat, amount, layers=None, ghost=None, linen_k=0.45, dye_k=1.0):
    """aged albedo.  amount scalar or HxW in [0, 1].  layers: dict(fox, tide, fade) (age_* channels of a MapSet)."""
    alb = np.asarray(alb, np.float32)
    H, W = alb.shape[:2]
    a = np.broadcast_to(np.asarray(amount, np.float32), (H, W)).astype(np.float32)
    if layers is None:
        layers = {}
    fade = layers.get('fade', layers.get('age_fade'))
    fade = np.full((H, W), 0.5, np.float32) if fade is None else np.asarray(fade, np.float32)
    fox = layers.get('fox', layers.get('age_fox'))
    tide = layers.get('tide', layers.get('age_tide'))
    lab = lin2oklab(alb)
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]
    C = np.hypot(A, B) + 1e-9
    hue = np.arctan2(B, A)
    blue = sstep(0.0, 1.0, np.cos(hue - math.radians(245)))           # woad fades most
    dye = mat != 0
    k = a * dye_k * dye
    Cn = C * (1 - k * (0.30 + 0.18 * fade + 0.22 * blue))
    Ln = L + k * 0.07 * (0.62 - L)
    # drift toward a warm brown cast (organic browns, yellowed fibre)
    tgt = math.radians(75)
    dh = np.angle(np.exp(1j * (tgt - hue))).astype(np.float32)
    hn = hue + k * 0.10 * dh * (1 - np.clip(C / 0.15, 0, 1))
    lab2 = np.stack([Ln, Cn * np.cos(hn), Cn * np.sin(hn)], -1)
    out = oklab2lin(lab2)
    # linen yellowing / darkening except where protected under stitches (ghost)
    lin_m = (mat == 0)
    prot = 0.0 if ghost is None else np.asarray(ghost, np.float32) * 0.85
    lk = a * linen_k * (0.6 + 0.4 * fade) * (1 - prot) * lin_m
    ratio = pal('linen_lo') / pal('linen')
    out = out * (1 - lk[..., None]) + out * ratio * lk[..., None]
    if fox is not None:
        fc = hex_lin('#9C7046'); fc = fc / fc.max()
        fa = (np.asarray(fox, np.float32) * 0.35 * a)[..., None]
        out = out * (1 - fa) + out * fc * fa
    if tide is not None:
        tc = hex_lin('#7C5A38'); tc = tc / tc.max()
        ta = (np.clip(np.asarray(tide, np.float32), 0, 1) * 0.55 * a)[..., None]
        out = out * (1 - ta) + out * tc * ta
    return out.astype(np.float32)
