# linen_tex.py - procedural tabby linen (albedo sRGB 8-bit + height 16-bit) at R px/mm, no tiling.
# usage: python3 linen_tex.py AW_mm AH_mm R out_prefix [imprint_mask.png x0 y0 w h]  (imprint placed in mm, linen frame origin = centre)
import sys, numpy as np, cv2, math
AW, AH, R = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]); OUT = sys.argv[4]
rng = np.random.default_rng(7)
W, H = int(AW * R), int(AH * R)
p = 0.67                       # thread pitch mm (15/cm)
r0 = 0.295                     # thread half-width mm (flattened linen yarn)
ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
x = xs / R; y = ys / R         # mm

def noise1(n, length_mm, corr_mm, amp, seed):
    """per-thread smooth 1D noise along the thread (rows: threads)"""
    g = np.random.default_rng(seed)
    k = int(length_mm / corr_mm) + 3
    ctrl = g.normal(0, amp, (n, k)).astype(np.float32)
    return ctrl

def eval_noise(ctrl, idx, t_mm, corr_mm):
    u = t_mm / corr_mm
    i = np.floor(u).astype(np.int32); f = u - i; f = f * f * (3 - 2 * f)
    i = np.clip(i, 0, ctrl.shape[1] - 2)
    return ctrl[idx, i] * (1 - f) + ctrl[idx, i + 1] * f

nwarp = int(AW / p) + 3; nweft = int(AH / p) + 3
# wander + radius + slub noise
wv_w = noise1(nwarp, AH, 6.0, 0.05, 1); wv_f = noise1(nweft, AW, 6.0, 0.07, 2)        # weft wanders more
rd_w = noise1(nwarp, AH, 2.0, 0.10, 3); rd_f = noise1(nweft, AW, 2.0, 0.12, 4)
# slubs: sparse thick stretches 3-10 mm
def slubs(n, length, seed):
    g = np.random.default_rng(seed)
    ctrl = np.zeros((n, int(length / 1.0) + 3), np.float32)
    for t in range(n):
        for _ in range(g.poisson(length / 120.0)):
            c = g.uniform(0, length); L = g.uniform(3, 10); a = g.uniform(0.25, 0.6)
            i0 = int((c - L / 2) / 1.0); i1 = int((c + L / 2) / 1.0)
            for i in range(max(0, i0), min(ctrl.shape[1], i1 + 1)):
                tt = (i - i0) / max(1, i1 - i0); ctrl[t, i] = max(ctrl[t, i], a * math.sin(math.pi * tt))
    return ctrl
sl_w = slubs(nwarp, AH, 5); sl_f = slubs(nweft, AW, 6)
cl_w = noise1(nwarp, AH, 9.0, 0.022, 8); cl_f = noise1(nweft, AW, 9.0, 0.022, 9)   # per-thread colour

# warp (vertical threads)
iw = np.clip(np.round(x / p).astype(np.int32), 0, nwarp - 1)
cxw = iw * p + eval_noise(wv_w, iw, y, 6.0)
rw = r0 * (1 + eval_noise(rd_w, iw, y, 2.0) + eval_noise(sl_w, iw, y, 1.0))
dxw = (x - cxw) / rw
prof_w = np.sqrt(np.clip(1 - dxw ** 2, 0, 1))
# weft (horizontal)
jf = np.clip(np.round(y / p).astype(np.int32), 0, nweft - 1)
cyf = jf * p + eval_noise(wv_f, jf, x, 6.0)
rf = r0 * (1 + eval_noise(rd_f, jf, x, 2.0) + eval_noise(sl_f, jf, x, 1.0))
dyf = (y - cyf) / rf
prof_f = np.sqrt(np.clip(1 - dyf ** 2, 0, 1))
# over/under modulation
mw = 0.5 + 0.5 * np.cos(np.pi * (y - cxw * 0) / p - np.pi * iw)
mf = 0.5 + 0.5 * np.cos(np.pi * x / p - np.pi * jf - np.pi)
hw = prof_w * rw * (0.35 + 0.65 * mw)
hf = prof_f * rf * (0.35 + 0.65 * mf)
top_w = hw >= hf
h = np.maximum(hw, hf)                      # mm
# fibre streaks along each thread
streak = np.where(top_w, eval_noise(noise1(nwarp, AH, 0.15, 1.0, 11), iw, y, 0.15) * 0 +
                  np.sin(dxw * 9.0 + iw * 1.7) * 0.5, np.sin(dyf * 9.0 + jf * 2.3) * 0.5)
h = h + 0.012 * streak * (h > 0)

# albedo
base = np.array([0.831, 0.745, 0.596], np.float32)        # #D4BE98
gap = np.array([0.60, 0.51, 0.38], np.float32)
tc = np.where(top_w, eval_noise(cl_w, iw, y, 9.0), eval_noise(cl_f, jf, x, 9.0))
# large-scale mottling
mott = cv2.resize(rng.normal(0, 1, (int(AH / 12) + 2, int(AW / 12) + 2)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC) * 0.02
lit = (1 + tc + mott + 0.04 * streak * (h > 0))[..., None] * base[None, None]
cov = np.clip(h / 0.08, 0, 1)[..., None]
alb = lit * cov + gap * (1 - cov)
# thread shading at edges (cylinder self-shadow baked lightly)
edge = np.where(top_w, prof_w, prof_f)
alb *= (0.86 + 0.14 * edge)[..., None]
# ageing: foxing spots + one faint tideline
for _ in range(int(AW * AH / 900)):
    cx, cy = rng.uniform(0, AW), rng.uniform(0, AH); rr = rng.uniform(0.3, 1.6)
    d = np.hypot(x - cx, y - cy)
    if d.min() > rr * 3: continue
    m = np.exp(-(d / rr) ** 2) * rng.uniform(0.12, 0.3)
    alb *= (1 - m[..., None] * (1 - np.array([0.61, 0.44, 0.27], np.float32)))
cx, cy, rr = AW * 0.08, AH * 0.10, 30.0
d = np.hypot(x - cx, (y - cy) * 1.3)
ring = np.exp(-((d - rr) / 0.9) ** 2) * 0.10 + (d < rr) * 0.02
alb *= (1 - ring[..., None] * (1 - np.array([0.49, 0.35, 0.22], np.float32)))

# optional imprint (needle holes + pressed linen under a lifted figure)
if len(sys.argv) > 5:
    m = cv2.imread(sys.argv[5], cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
    if m.ndim == 3: m = m[..., -1]
    ix0, iy0, iw_, ih_ = map(float, sys.argv[6:10])      # mm, in linen-centred coords (y up)
    px0 = int((ix0 + AW / 2) * R); py0 = int((AH / 2 - (iy0 + ih_)) * R)
    mm_ = cv2.resize(m, (int(iw_ * R), int(ih_ * R)), interpolation=cv2.INTER_AREA)
    imp = np.zeros((H, W), np.float32); imp[py0:py0 + mm_.shape[0], px0:px0 + mm_.shape[1]] = mm_
    cv2.imwrite(OUT + '_imprint.png', np.clip(imp * 255, 0, 255).astype(np.uint8))

def to_srgb(c):
    c = np.clip(c, 0, 1); return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)
cv2.imwrite(OUT + '_albedo.png', (np.clip(alb, 0, 1) * 255 + 0.5).astype(np.uint8)[..., ::-1])   # albedo values authored in display space
cv2.imwrite(OUT + '_height.png', (np.clip(h / 0.4, 0, 1) * 65535).astype(np.uint16))
print('linen', W, H, 'h max', float(h.max()))
