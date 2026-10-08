"""emb.py - thread-level embroidery map synthesis (Approach C: hybrid maps -> Blender displaced cloth).

Everything is in millimetres; PX = map pixels per mm.  Maps produced per patch:
  height (mm, float32)       -> low-pass goes to real mesh displacement, high-pass to the normal map
  albedo (linear RGB)        -> base colour (cavity + fuzz halo baked in)
  mat    (R rough, G metal, B sheen, A spec-level)
  tangent (2-ch thread direction, for preview/aniso)
  sid    (stitch order 0..1, for stitch-on animation)
The fills are built from two Poisson phase fields per region (phi across strands, psi along strands)
solved from a thread-direction field, so strands follow curved forms (needle painting) and every
stitch is an individual, separately coloured thread.
"""
import math, numpy as np, cv2
from scipy import fft as sfft

# ------------------------------------------------------------------ colour helpers
def hex_srgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255

def srgb_to_lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)

def lin_to_srgb(c):
    c = np.clip(np.asarray(c, np.float32), 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055).astype(np.float32)

def hex_lin(h):
    return srgb_to_lin(hex_srgb(h))

def lin_to_oklab(c):
    c = np.asarray(c, np.float32)
    l = 0.4122214708 * c[..., 0] + 0.5363325363 * c[..., 1] + 0.0514459929 * c[..., 2]
    m = 0.2119034982 * c[..., 0] + 0.6806995451 * c[..., 1] + 0.1073969566 * c[..., 2]
    s = 0.0883024619 * c[..., 0] + 0.2817188376 * c[..., 1] + 0.6299787005 * c[..., 2]
    l, m, s = np.cbrt(l), np.cbrt(m), np.cbrt(s)
    return np.stack([0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
                     1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
                     0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s], -1).astype(np.float32)

def oklab_to_lin(L):
    L = np.asarray(L, np.float32)
    l_ = L[..., 0] + 0.3963377774 * L[..., 1] + 0.2158037573 * L[..., 2]
    m_ = L[..., 0] - 0.1055613458 * L[..., 1] - 0.0638541728 * L[..., 2]
    s_ = L[..., 0] - 0.0894841775 * L[..., 1] - 1.2914855480 * L[..., 2]
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return np.stack([4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
                     -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
                     -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s], -1).astype(np.float32)

# ------------------------------------------------------------------ noise / hashing
def hash1(i, seed):
    i = np.asarray(i, np.int64)
    v = (i * 374761393 + seed * 668265263) & 0xFFFFFFFF
    v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((v ^ (v >> 16)) & 0xFFFF).astype(np.float32) / 65535.0

def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)

def pnoise(shape, sigma_px, seed):
    """Periodic (tileable) gaussian-filtered noise, unit std."""
    r = np.random.default_rng(seed)
    w = r.standard_normal(shape).astype(np.float32)
    fy = np.fft.fftfreq(shape[0])[:, None]; fx = np.fft.rfftfreq(shape[1])[None, :]
    g = np.exp(-2 * (math.pi ** 2) * (sigma_px ** 2) * (fx ** 2 + fy ** 2))
    n = np.fft.irfft2(np.fft.rfft2(w) * g, s=shape).astype(np.float32)
    return n / (n.std() + 1e-8)

def snoise(shape, scale_px, seed):
    """Non-periodic smooth noise (cubic-upsampled lattice), ~unit std."""
    r = np.random.default_rng(seed)
    gh, gw = int(shape[0] / scale_px) + 4, int(shape[1] / scale_px) + 4
    g = r.standard_normal((gh, gw)).astype(np.float32)
    out = cv2.resize(g, (int(gw * scale_px), int(gh * scale_px)), interpolation=cv2.INTER_CUBIC)
    return out[:shape[0], :shape[1]] * 0.75

# ------------------------------------------------------------------ fields
def structure_dir(img_channels, sg, si):
    """Thread (line) direction from structure tensor. Returns (c2, s2, coherence):
    doubled-angle components of the STRAND direction (perpendicular to gradient)."""
    Jxx = Jyy = Jxy = 0
    for ch in img_channels:
        ch = cv2.GaussianBlur(ch.astype(np.float32), (0, 0), sg)
        gx = cv2.Sobel(ch, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(ch, cv2.CV_32F, 0, 1, ksize=3)
        Jxx = Jxx + gx * gx; Jyy = Jyy + gy * gy; Jxy = Jxy + gx * gy
    Jxx = cv2.GaussianBlur(Jxx, (0, 0), si); Jyy = cv2.GaussianBlur(Jyy, (0, 0), si); Jxy = cv2.GaussianBlur(Jxy, (0, 0), si)
    a = Jxx - Jyy; b = 2 * Jxy
    mag = np.sqrt(a * a + b * b); tr = Jxx + Jyy + 1e-9
    coh = mag / tr
    # gradient doubled angle = atan2(b, a); strand direction = gradient + 90deg -> doubled angle + 180deg
    c2 = -a / (mag + 1e-9); s2 = -b / (mag + 1e-9)
    return c2.astype(np.float32), s2.astype(np.float32), coh.astype(np.float32)

def smooth_dir(c2, s2, w, sigma):
    c = cv2.GaussianBlur(c2 * w, (0, 0), sigma); s = cv2.GaussianBlur(s2 * w, (0, 0), sigma)
    m = np.sqrt(c * c + s * s) + 1e-9
    return c / m, s / m, m / (cv2.GaussianBlur(w, (0, 0), sigma) + 1e-9)

def dir_vec(c2, s2):
    th = 0.5 * np.arctan2(s2, c2)
    return np.cos(th).astype(np.float32), np.sin(th).astype(np.float32)

def orient_consistent(dx, dy, mask, cell=8):
    """Choose signs of a line field so it is a smooth vector field inside mask (BFS on a coarse grid)."""
    H, W = mask.shape
    gh, gw = (H + cell - 1) // cell, (W + cell - 1) // cell
    pad = lambda a: np.pad(a, ((0, gh * cell - H), (0, gw * cell - W)))
    m = pad(mask.astype(np.float32)).reshape(gh, cell, gw, cell).mean((1, 3))
    cx = pad(dx * mask).reshape(gh, cell, gw, cell).sum((1, 3)); cy = pad(dy * mask).reshape(gh, cell, gw, cell).sum((1, 3))
    # use doubled angle mean per cell to get the cell's axis
    c2 = pad((dx * dx - dy * dy) * mask).reshape(gh, cell, gw, cell).sum((1, 3))
    s2 = pad((2 * dx * dy) * mask).reshape(gh, cell, gw, cell).sum((1, 3))
    th = 0.5 * np.arctan2(s2, c2); ax, ay = np.cos(th), np.sin(th)
    sign = np.zeros((gh, gw), np.int8)
    valid = m > 0
    from collections import deque
    for seed in zip(*np.nonzero(valid)):
        if sign[seed] != 0: continue
        sign[seed] = 1; q = deque([seed])
        while q:
            i, j = q.popleft(); vx, vy = ax[i, j] * sign[i, j], ay[i, j] * sign[i, j]
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = i + di, j + dj
                if 0 <= a < gh and 0 <= b < gw and valid[a, b] and sign[a, b] == 0:
                    sign[a, b] = 1 if ax[a, b] * vx + ay[a, b] * vy >= 0 else -1
                    q.append((a, b))
    # per-pixel: reference vector = upsampled signed cell axis, flip pixels that disagree
    rx = cv2.resize((ax * sign).astype(np.float32), (gw * cell, gh * cell), interpolation=cv2.INTER_LINEAR)[:H, :W]
    ry = cv2.resize((ay * sign).astype(np.float32), (gw * cell, gh * cell), interpolation=cv2.INTER_LINEAR)[:H, :W]
    f = np.where(dx * rx + dy * ry >= 0, 1.0, -1.0).astype(np.float32)
    return dx * f, dy * f

def poisson_from_grad(gx, gy):
    """Least-squares phi with grad(phi) ~ (gx, gy), Neumann BC, DCT solver. Units: px."""
    H, W = gx.shape
    gxf = 0.5 * (gx[:, :-1] + gx[:, 1:]); gyf = 0.5 * (gy[:-1, :] + gy[1:, :])
    div = np.zeros((H, W), np.float64)
    div[:, :-1] += gxf; div[:, 1:] -= gxf
    div[:-1, :] += gyf; div[1:, :] -= gyf
    F = sfft.dctn(-div, type=2, norm='ortho')
    i = np.arange(H)[:, None]; j = np.arange(W)[None, :]
    lam = (2 * np.cos(math.pi * i / H) - 2) + (2 * np.cos(math.pi * j / W) - 2)
    lam[0, 0] = 1
    P = F / lam; P[0, 0] = 0
    return (-sfft.idctn(P, type=2, norm='ortho')).astype(np.float32)

def phase_fields(dx, dy, mask, px, margin_mm=3.0):
    """Return (phi, psi) in mm for one region: phi across strands, psi along strands."""
    H, W = mask.shape
    ys, xs = np.nonzero(mask)
    m = int(margin_mm * px)
    y0, y1 = max(ys.min() - m, 0), min(ys.max() + m + 1, H); x0, x1 = max(xs.min() - m, 0), min(xs.max() + m + 1, W)
    sub = mask[y0:y1, x0:x1]
    ddx, ddy = orient_consistent(dx[y0:y1, x0:x1], dy[y0:y1, x0:x1], sub)
    # extend field outside the region (nearest inside value) so the solve is not pulled at the boundary
    if (~sub).any():
        from scipy import ndimage
        _, (iy, ix) = ndimage.distance_transform_edt(~sub, return_indices=True)
        ddx = ddx[iy, ix]; ddy = ddy[iy, ix]
    nx, ny = -ddy, ddx     # across-strand unit vector
    phi = poisson_from_grad(nx, ny) / px
    psi = poisson_from_grad(ddx, ddy) / px
    PHI = np.zeros((H, W), np.float32); PSI = np.zeros((H, W), np.float32)
    PHI[y0:y1, x0:x1] = phi; PSI[y0:y1, x0:x1] = psi
    DX = np.zeros((H, W), np.float32); DY = np.zeros((H, W), np.float32)
    DX[y0:y1, x0:x1] = ddx; DY[y0:y1, x0:x1] = ddy
    return PHI, PSI, DX, DY, (y0, y1, x0, x1)

# ------------------------------------------------------------------ morphology
def thin(mask, max_iter=60):
    """Zhang-Suen thinning (vectorised)."""
    img = (mask > 0).astype(np.uint8)
    img = np.pad(img, 1)
    for _ in range(max_iter):
        changed = False
        for step in (0, 1):
            P = img
            p2, p3, p4 = P[:-2, 1:-1], P[:-2, 2:], P[1:-1, 2:]
            p5, p6, p7 = P[2:, 2:], P[2:, 1:-1], P[2:, :-2]
            p8, p9 = P[1:-1, :-2], P[:-2, :-2]
            nb = [p2, p3, p4, p5, p6, p7, p8, p9]
            B = sum(n.astype(np.int32) for n in nb)
            A = sum(((nb[k] == 0) & (nb[(k + 1) % 8] == 1)).astype(np.int32) for k in range(8))
            if step == 0:
                c = (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                c = (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            rm = (P[1:-1, 1:-1] == 1) & (B >= 2) & (B <= 6) & (A == 1) & c
            if rm.any():
                changed = True
                img[1:-1, 1:-1][rm] = 0
        if not changed: break
    return img[1:-1, 1:-1].astype(bool)

def poisson_disk_on(mask, r_px, seed, priority=None):
    ys, xs = np.nonzero(mask)
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(ys)) if priority is None else np.argsort(-priority[ys, xs] + rng.random(len(ys)) * 1e-3)
    cell = r_px / math.sqrt(2)
    grid = {}
    out = []
    r2 = r_px * r_px
    for o in order:
        y, x = ys[o], xs[o]
        gi, gj = int(y / cell), int(x / cell)
        ok = True
        for a in range(gi - 2, gi + 3):
            for b in range(gj - 2, gj + 3):
                q = grid.get((a, b))
                if q is not None and (q[0] - y) ** 2 + (q[1] - x) ** 2 < r2:
                    ok = False; break
            if not ok: break
        if ok:
            grid[(gi, gj)] = (y, x); out.append((y, x))
    return np.array(out, np.float32).reshape(-1, 2)

# ------------------------------------------------------------------ the canvas being built
class Canvas:
    """Height / albedo / material / tangent buffers for one patch."""
    def __init__(self, H, W, px):
        self.H, self.W, self.px = H, W, px
        self.h = np.zeros((H, W), np.float32)
        self.alb = np.zeros((H, W, 3), np.float32)
        self.mat = np.zeros((H, W, 4), np.float32)      # rough, metal, sheen, spec
        self.T = np.zeros((H, W, 2), np.float32); self.T[..., 0] = 1
        self.wool = np.zeros((H, W), np.float32)        # coverage of thread (any) for fuzz / alpha
        self.order = np.full((H, W), -1.0, np.float32)  # stitch order for stitch-on animation (-1 = ground)
        self.kind = np.zeros((H, W), np.uint8)          # 0 linen 1 wool 2 metal 3 silk

    def put(self, on, h, alb, mat, T=None, kind=1, order=None):
        on = on & (h > self.h)
        self.h = np.where(on, h, self.h)
        self.alb = np.where(on[..., None], alb, self.alb)
        self.mat = np.where(on[..., None], np.asarray(mat, np.float32), self.mat)
        if T is not None: self.T = np.where(on[..., None], T, self.T)
        self.kind = np.where(on, kind, self.kind)
        if kind != 0: self.wool = np.where(on, 1.0, self.wool)
        if order is not None: self.order = np.where(on, order, self.order)

MAT_LINEN = (0.78, 0.0, 0.20, 0.30)
MAT_WOOL = (0.86, 0.0, 0.65, 0.35)
MAT_SILK = (0.48, 0.0, 0.35, 0.50)
MAT_METAL = (0.30, 1.0, 0.0, 0.50)

# ------------------------------------------------------------------ linen
def linen_tile(T_mm, px, seed=1, base='#D4BE98', n_warp=None, n_weft=None):
    """Tileable tabby linen: returns dict(h, alb, T). Warp vertical (along y)."""
    S = int(round(T_mm * px))
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    X, Y = xx / px, yy / px
    n_warp = n_warp or int(round(T_mm / 0.667)); n_weft = n_weft or int(round(T_mm / 0.68))
    pw, pf = T_mm / n_warp, T_mm / n_weft
    td = 0.50
    Xw = X + 0.12 * pnoise((S, S), 6 * px / 2, seed + 1)
    Yw = Y + 0.12 * pnoise((S, S), 6 * px / 2, seed + 2)
    xi, yi = Xw / pw, Yw / pf
    i, j = np.floor(xi), np.floor(yi)
    tx, ty = xi - i - 0.5, yi - j - 0.5
    i_m = np.mod(i, n_warp); j_m = np.mod(j, n_weft)
    # periodic slubs: 1-D noise per thread along its length
    L = 4 * int(T_mm * 4)
    rng = np.random.default_rng(seed + 3)
    def slub_tab(n, sd):
        a = rng.standard_normal((n, L)).astype(np.float32)
        f = np.fft.rfftfreq(L)[None, :]
        a = np.fft.irfft(np.fft.rfft(a, axis=1) * np.exp(-2 * (math.pi ** 2) * (40 ** 2) * f ** 2), n=L, axis=1)
        a /= a.std() + 1e-8
        return np.clip(a - 2.0, 0, None).astype(np.float32)
    sw, sf = slub_tab(n_warp, 1), slub_tab(n_weft, 2)
    posw = (np.mod(Yw, T_mm) / T_mm * L).astype(np.int64) % L
    posf = (np.mod(Xw, T_mm) / T_mm * L).astype(np.int64) % L
    slub_w = 1 + 0.16 * (hash1(i_m, 3) - 0.5) + 0.55 * sw[i_m.astype(np.int64), posw]
    slub_f = 1 + 0.16 * (hash1(j_m, 5) - 0.5) + 0.55 * sf[j_m.astype(np.int64), posf]
    rw, rf = 0.5 * td * slub_w, 0.5 * td * slub_f
    hw = 0.8 * rw * np.sqrt(np.clip(1 - (tx * pw / rw) ** 2, 0, 1)) + 0.06 * np.sin(math.pi * (yi + i))
    hf = 0.8 * rf * np.sqrt(np.clip(1 - (ty * pf / rf) ** 2, 0, 1)) - 0.06 * np.sin(math.pi * (xi + j))
    inw = np.abs(tx * pw) < rw; inf = np.abs(ty * pf) < rf
    hw = np.where(inw, hw, -0.2); hf = np.where(inf, hf, -0.2)
    warp_top = hw >= hf
    h = np.maximum(np.maximum(hw, hf), -0.10)
    # fibre streaks along each thread (periodic)
    st = pnoise((S, S), 0.6, seed + 9)
    stw = cv2.GaussianBlur(st, (1, 0), sigmaX=0.3, sigmaY=3.0)
    stf = cv2.GaussianBlur(st, (0, 1), sigmaX=3.0, sigmaY=0.3) if False else cv2.GaussianBlur(st, (0, 0), sigmaX=3.0, sigmaY=0.3)
    stw = cv2.GaussianBlur(st, (0, 0), sigmaX=0.3, sigmaY=3.0)
    h = h + np.where(warp_top, stw, stf) * 0.012 * (h > -0.05)
    T = np.stack([np.where(warp_top, 0, 1), np.where(warp_top, 1, 0)], -1).astype(np.float32)
    lin = hex_lin(base)
    var = 1 + 0.07 * (np.where(warp_top, hash1(i_m, 7), hash1(j_m, 8)) - 0.5) + 0.03 * pnoise((S, S), 12 * px / 2, seed + 10)
    var = var + 0.02 * np.where(warp_top, slub_w - 1, slub_f - 1)    # slubs a touch lighter (less twisted)
    alb = lin[None, None, :] * var[..., None]
    # slight warp/weft hue difference (warp a hair greyer)
    alb = alb * np.where(warp_top[..., None], np.array([0.99, 1.0, 1.01], np.float32), np.array([1.01, 1.0, 0.985], np.float32))
    return dict(h=h.astype(np.float32), alb=alb.astype(np.float32), T=T, S=S)

def tile_sample(tile, x0_mm, y0_mm, H, W, px):
    """Sample a tile map (array SxS[,c]) at world offset (patch top-left at x0,y0 mm)."""
    S = tile.shape[0]
    ox, oy = int(round(x0_mm * px)) % S, int(round(y0_mm * px)) % S
    reps_y = (H + oy) // S + 2; reps_x = (W + ox) // S + 2
    reps = (reps_y, reps_x) + (1,) * (tile.ndim - 2)
    big = np.tile(tile, reps)
    return big[oy:oy + H, ox:ox + W].copy()

# ------------------------------------------------------------------ stitch primitives (phase-field based)
def strand_profile(t):
    """t in [-0.5,0.5] across a strand -> rounded profile 0..1"""
    return np.sqrt(np.clip(1 - (2 * t) ** 2, 0, 1))

def fill_needle(cv, region, PHI, PSI, DX, DY, colour_fn, p=0.7, L=3.5, Ljit=0.35, hgt=0.55, base_h=0.0,
                mat=MAT_WOOL, kind=1, seed=0, order_base=0.0, twist_deg=32, keep_fn=None, pad=None, stagger=True):
    """Long-and-short / split-stitch needle painting along the phase fields.
    colour_fn(stitch_id_array, on_mask) -> per-pixel linear rgb (H,W,3) for pixels in on_mask.
    pad: optional per-pixel padding height (mm) added under the stitches."""
    px = cv.px
    y0, y1, x0, x1 = region['bbox']
    sl = (slice(y0, y1), slice(x0, x1))
    msk = region['mask'][sl]
    phi = PHI[sl]; psi = PSI[sl]
    rng_j = 0.08 * p
    k = np.floor(phi / p); t = phi / p - k - 0.5
    w = 1 + 0.22 * (hash1(k, seed + 1) - 0.5)
    # stitch index along strand, staggered per strand (long-and-short)
    Lk = L * (1 + Ljit * (hash1(k, seed + 2) - 0.5))
    off = hash1(k, seed + 3) if stagger else 0
    u = psi / Lk + off
    m = np.floor(u); s = u - m                      # s in [0,1) along the stitch
    Lm = 1 + 0.25 * (hash1(m * 7919 + k, seed + 4) - 0.5)
    prof = strand_profile(t / w)
    ends = np.clip(np.minimum(s, 1 - s) * (L / 0.35), 0, 1) ** 0.6          # stitch ends dive into the cloth over ~0.35 mm
    twist = 0.5 + 0.5 * np.cos(2 * math.pi * (psi + t * p * math.tan(math.radians(twist_deg))) / 0.7)
    hh = hgt * (0.32 + 0.68 * prof ** 0.8) * (0.25 + 0.75 * ends) * (0.88 + 0.12 * twist)
    hh = hh + base_h
    if pad is not None: hh = hh + pad[sl]
    sid = (k.astype(np.int64) * 100003 + m.astype(np.int64) + region['id'] * 1000000007) & 0x7FFFFFFF
    on = msk.copy()
    if keep_fn is not None: on &= keep_fn(sid, sl)
    col = colour_fn(sid, on, sl)
    col = col * (0.92 + 0.08 * twist[..., None]) * (0.86 + 0.14 * prof[..., None])
    # tangent: strand direction rotated by the ply angle
    dx, dy = DX[sl], DY[sl]
    a = math.radians(18)
    Tx = dx * math.cos(a) - dy * math.sin(a); Ty = dx * math.sin(a) + dy * math.cos(a)
    T = np.stack([Tx, Ty], -1)
    order = order_base + 0.001 * hash1(sid, 5)
    _put_sub(cv, sl, on, hh, col, mat, T, kind, order)
    return sid, on

LIFT = 0.18   # mm: embroidery sits on top of the linen threads

def _put_sub(cv, sl, on, hh, col, mat, T, kind, order):
    H_ = cv.h[sl]
    hh = hh + LIFT
    on = on & ((hh > H_) | (cv.kind[sl] == 0))
    cv.h[sl] = np.where(on, hh, H_)
    cv.alb[sl] = np.where(on[..., None], col, cv.alb[sl])
    cv.mat[sl] = np.where(on[..., None], np.asarray(mat, np.float32), cv.mat[sl])
    if T is not None: cv.T[sl] = np.where(on[..., None], T, cv.T[sl])
    cv.kind[sl] = np.where(on, kind, cv.kind[sl])
    cv.wool[sl] = np.where(on, 1.0, cv.wool[sl])
    if order is not None:
        cv.order[sl] = np.where(on, order, cv.order[sl])

def fill_laid(cv, region, PHI, PSI, DX, DY, colour_fn, p=0.85, hgt=0.5, bar_s=4.5, tie_s=4.0, mat=MAT_WOOL,
              seed=0, order_base=0.0, bar_colour=None, keep_fn=None):
    """Bayeux laid-and-couched work: long laid strands (phi), couching bars across (psi), tie-downs."""
    px = cv.px
    y0, y1, x0, x1 = region['bbox']; sl = (slice(y0, y1), slice(x0, x1))
    msk = region['mask'][sl]; phi = PHI[sl]; psi = PSI[sl]
    sh = msk.shape
    uu = phi + 0.08 * p * snoise(sh, 5 * px, seed + 1)
    k = np.floor(uu / p); t = uu / p - k - 0.5
    w = 1 + 0.24 * (hash1(k, seed) - 0.5)
    prof = strand_profile(t / (1.12 * w))
    twist = 0.5 + 0.5 * np.cos(2 * math.pi * (psi + t * p * math.tan(math.radians(32))) / 0.7)
    hl = hgt * prof * (0.88 + 0.12 * twist)
    # couching bars along psi
    best = np.full(sh, 99.0, np.float32); bidx = np.zeros(sh, np.float32)
    u0 = float(np.median(phi[msk])) if msk.any() else 0.0
    for o in (-1, 0, 1):
        b = np.floor(psi / bar_s) + o
        cb = (b + 0.5) * bar_s + (hash1(b, seed + 2) - 0.5) * 0.40 * bar_s + 0.2 * snoise(sh, 20 * px, seed + 3)
        dd = (psi - cb) + np.tan(math.radians(8) * (hash1(b, seed + 4) - 0.5)) * (phi - u0)
        sel = np.abs(dd) < np.abs(best); best = np.where(sel, dd, best); bidx = np.where(sel, b, bidx)
    rb = 0.42
    hl = hl * (1 - 0.30 * np.exp(-(best / 0.95) ** 2))
    uq = phi + (hash1(bidx, seed + 5) - 0.5) * tie_s
    q = np.floor(uq / tie_s); cq = (q + 0.5 + 0.25 * (hash1(q + 31 * bidx, seed + 6) - 0.5)) * tie_s
    du = uq - cq
    pinch = 1 - 0.40 * np.exp(-(du / 0.6) ** 2)
    hb = hgt * 0.84 + 0.38 * np.sqrt(np.clip(1 - (best / rb) ** 2, 0, 1)) * pinch
    hb = np.where(np.abs(best) < rb, hb, -1)
    tie = (np.abs(du) < 0.26) & (np.abs(best) < 0.72)
    ht = np.where(tie, hgt * 1.24 + 0.22 * np.sqrt(np.clip(1 - (du / 0.26) ** 2, 0, 1)), -1)
    edge = np.clip(cv2.distanceTransform(msk.astype(np.uint8), cv2.DIST_L2, 5) / px / 0.45, 0, 1) ** 0.7
    hfill = np.maximum.reduce([np.maximum(hl, 0.12) * edge, hb * edge, ht * edge])
    sid = (k.astype(np.int64) * 100003 + np.floor(psi / 9.0).astype(np.int64) + region['id'] * 1000000007) & 0x7FFFFFFF
    on = msk
    if keep_fn is not None: on = on & keep_fn(sid, sl)
    col = colour_fn(sid, on, sl)
    if bar_colour is not None:
        bc = np.broadcast_to(np.asarray(bar_colour, np.float32), col.shape)
    else:
        bc = col * 1.04
    isbar = (hb >= hl) | tie
    col = np.where(isbar[..., None], bc, col)
    col = col * (0.93 + 0.07 * twist[..., None]) * np.where(isbar[..., None], 1.0, (0.86 + 0.14 * prof[..., None]))
    dx, dy = DX[sl], DY[sl]
    a = math.radians(18)
    Td = np.stack([dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)], -1)
    Tb = np.stack([-dy, dx], -1)
    T = np.where(isbar[..., None] & ~tie[..., None], Tb, Td)
    order = order_base + np.where(isbar, 0.5, 0.0) + 0.001 * hash1(sid, 6)
    _put_sub(cv, sl, on, hfill, col, mat, T, 1, order)
    return sid, on

def fill_metal_couched(cv, region, PHI, PSI, DX, DY, gold_lin, tie_lin, p=0.5, hgt=0.62, tie_s=2.4, seed=0,
                       order_base=0.0, keep_fn=None, tarnish=0.0, base=None):
    """Underside/surface-couched pairs of metal (silver-gilt) thread with coloured silk tie-downs (opus anglicanum)."""
    px = cv.px
    y0, y1, x0, x1 = region['bbox']; sl = (slice(y0, y1), slice(x0, x1))
    msk = region['mask'][sl]; phi = PHI[sl]; psi = PSI[sl]; sh = msk.shape
    k = np.floor(phi / p); t = phi / p - k - 0.5
    pair = np.floor(k / 2)
    prof = strand_profile(t / 0.96)
    # metal thread = flat strip wrapped on a core -> fine diagonal wraps
    wrap = 0.5 + 0.5 * np.cos(2 * math.pi * (psi + t * p * 2.2) / 0.32)
    hm = hgt * prof * (0.9 + 0.1 * wrap)
    tpos = psi / tie_s + 0.5 * np.mod(pair, 2) + 0.15 * (hash1(pair, seed) - 0.5)
    dt = (tpos - np.round(tpos)) * tie_s
    tie = np.abs(dt) < 0.13
    hm = np.where(tie, hm * 0.80, hm)          # thread pinched under the tie
    htie = np.where(tie & (prof > 0.1), hgt * 0.80 + 0.16 * np.sqrt(np.clip(1 - (dt / 0.13) ** 2, 0, 1)), -1)
    edge = np.clip(cv2.distanceTransform(msk.astype(np.uint8), cv2.DIST_L2, 5) / px / 0.3, 0, 1) ** 0.5
    hh = np.maximum(hm, htie) * edge + LIFT
    if base is not None: hh = hh + (base[sl] if np.ndim(base) == 2 else base)
    on = msk & (prof > 0.05)
    sid = (pair.astype(np.int64) * 7 + region['id'] * 1000003) & 0x7FFFFFFF
    if keep_fn is not None: on &= keep_fn(sid, sl)
    g = np.asarray(gold_lin, np.float32)
    var = 1 + 0.06 * (hash1(pair, seed + 2) - 0.5) + 0.05 * snoise(sh, 6 * px, seed + 3)
    tarn = np.clip(tarnish * (0.5 + 0.5 * snoise(sh, 8 * px, seed + 4)), 0, 1)
    gcol = g[None, None] * var[..., None] * (1 - tarn[..., None]) + hex_lin('#7A5A2A')[None, None] * tarn[..., None]
    col = np.where(tie[..., None], np.asarray(tie_lin, np.float32)[None, None] * (0.9 + 0.2 * hash1(pair, 9))[..., None], gcol)
    mat = np.where(tie[..., None], np.array(MAT_SILK, np.float32), np.array(MAT_METAL, np.float32))
    dx, dy = DX[sl], DY[sl]
    T = np.where(tie[..., None], np.stack([-dy, dx], -1), np.stack([dx, dy], -1))
    kind = np.where(tie, 3, 2).astype(np.uint8)
    H_ = cv.h[sl]; on2 = on & ((hh > H_) | (cv.kind[sl] == 0))
    cv.h[sl] = np.where(on2, hh, H_)
    cv.alb[sl] = np.where(on2[..., None], col, cv.alb[sl])
    cv.mat[sl] = np.where(on2[..., None], mat, cv.mat[sl])
    cv.T[sl] = np.where(on2[..., None], T, cv.T[sl])
    cv.kind[sl] = np.where(on2, kind, cv.kind[sl])
    cv.wool[sl] = np.where(on2, 1.0, cv.wool[sl])
    cv.order[sl] = np.where(on2, order_base + 0.001 * hash1(sid, 3), cv.order[sl])
    return sid, on2

def stamp_stitch(cv, A, B, r, hgt, col, mat, kind=1, base=0.0, order=None, slant_ang=None, twist=True, layer_h=None):
    """One straight stitch (capsule) from A to B (mm). Dips at both ends. Max-composited."""
    px = cv.px
    x0 = int((min(A[0], B[0]) - r - 0.2) * px); x1 = int((max(A[0], B[0]) + r + 0.2) * px) + 2
    y0 = int((min(A[1], B[1]) - r - 0.2) * px); y1 = int((max(A[1], B[1]) + r + 0.2) * px) + 2
    x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, cv.W), min(y1, cv.H)
    if x1 <= x0 or y1 <= y0: return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    X, Y = (xx + 0.5) / px, (yy + 0.5) / px
    AB = np.asarray(B, np.float32) - np.asarray(A, np.float32); ll = float(AB @ AB) + 1e-9
    tt = np.clip(((X - A[0]) * AB[0] + (Y - A[1]) * AB[1]) / ll, 0, 1)
    dx_, dy_ = X - (A[0] + tt * AB[0]), Y - (A[1] + tt * AB[1]); dist = np.hypot(dx_, dy_)
    prof = np.sqrt(np.clip(1 - (dist / r) ** 2, 0, 1))
    along = tt * math.sqrt(ll)
    endf = 0.45 + 0.55 * np.sin(math.pi * tt) ** 0.5
    tw = 0.5 + 0.5 * np.cos(2 * math.pi * (along + dist * 0.6) / 0.7) if twist else np.ones_like(tt)
    hs = LIFT + base + hgt * prof * endf * (0.9 + 0.1 * tw)
    sl = (slice(y0, y1), slice(x0, x1))
    on = (prof > 0.02) & ((hs > cv.h[sl] - 0.03) | (cv.kind[sl] == 0))
    c = np.asarray(col, np.float32)[None, None, :] * (0.92 + 0.08 * tw)[..., None] * (0.84 + 0.16 * prof)[..., None]
    ang = math.atan2(AB[1], AB[0])
    T = np.broadcast_to(np.array([math.cos(ang), math.sin(ang)], np.float32), prof.shape + (2,))
    hnew = np.maximum(hs, cv.h[sl]) if layer_h is None else hs
    cv.h[sl] = np.where(on, hnew, cv.h[sl])
    cv.alb[sl] = np.where(on[..., None], c, cv.alb[sl])
    cv.mat[sl] = np.where(on[..., None], np.asarray(mat, np.float32), cv.mat[sl])
    cv.T[sl] = np.where(on[..., None], T, cv.T[sl])
    cv.kind[sl] = np.where(on, kind, cv.kind[sl])
    cv.wool[sl] = np.where(on, 1.0, cv.wool[sl])
    if order is not None: cv.order[sl] = np.where(on, order, cv.order[sl])

def line_tangents(mask_f, px, sigma_mm=0.6):
    """Tangent field of a line mask via structure tensor (direction along the line)."""
    c2, s2, coh = structure_dir([mask_f.astype(np.float32)], 0.8, sigma_mm * px)
    return dir_vec(c2, s2)

def stem_along_skeleton(cv, skel, tx, ty, colour_fn, L=3.2, r=0.5, hgt=0.55, base_fn=None, slant=13, seed=0,
                        spacing=None, order_fn=None, mat=MAT_WOOL, Lfn=None, rfn=None):
    """Stem-stitch rope without explicit polylines: overlapping slanted stitches centred on skeleton samples."""
    px = cv.px
    sp = (spacing or L * 0.5) * px
    pts = poisson_disk_on(skel, sp, seed)
    rng = np.random.default_rng(seed)
    for (y, x) in pts:
        iy, ix = int(y), int(x)
        dx, dy = float(tx[iy, ix]), float(ty[iy, ix])
        Ll = (Lfn(iy, ix) if Lfn else L) * (1 + rng.uniform(-0.18, 0.18))
        rr = (rfn(iy, ix) if rfn else r) * (1 + rng.uniform(-0.06, 0.06))
        a = math.atan2(dy, dx) + math.radians(slant) * (1 if rng.random() < 0.85 else -1)
        c = np.array([x / px, y / px])
        d = np.array([math.cos(a), math.sin(a)]) * Ll / 2
        A = c - d + rng.normal(0, 0.05, 2); B = c + d + rng.normal(0, 0.05, 2)
        col = colour_fn(iy, ix, rng)
        base = base_fn(iy, ix) if base_fn else 0.0
        stamp_stitch(cv, A, B, rr, hgt, col, mat, 1, base=base, order=(order_fn(iy, ix) if order_fn else None))

# ------------------------------------------------------------------ finishing: cavity, fuzz, fibres
def finish(cv, fuzz=True, fibres_per_mm2=0.5, seed=7, halo_a=0.33, linen_alb=None, cavity_k=1.4):
    px = cv.px
    h = cv.h
    # cavity / micro-AO baked into albedo (screen-space AO in Eevee cannot see normal-map detail)
    blur = cv2.GaussianBlur(h, (0, 0), 0.5 * px)
    cav = np.clip(1 - cavity_k * np.clip(blur - h, 0, None), 0.45, 1.0)
    blur2 = cv2.GaussianBlur(h, (0, 0), 1.5 * px)
    cav *= np.clip(1 - 0.35 * np.clip(blur2 - h, 0, None), 0.6, 1.0)
    alb = cv.alb * cav[..., None]
    if fuzz:
        wool = (cv.kind == 1).astype(np.float32)
        halo = cv2.GaussianBlur(wool, (0, 0), 0.28 * px)
        halo_col = cv2.GaussianBlur(alb * wool[..., None], (0, 0), 0.28 * px) / (halo[..., None] + 1e-4)
        ha = (np.clip(halo - wool, 0, 1) * halo_a)[..., None]
        alb = alb * (1 - ha) + halo_col * 1.04 * ha
        # fuzz also slightly softens the ground height right at the wool edge (fibres bridging)
        rr = np.random.default_rng(seed)
        edge = cv2.morphologyEx(wool, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8))
        prob = (wool * 0.15 + edge * 2.0).ravel(); s = prob.sum()
        fl = np.zeros(h.shape, np.float32)
        if s > 0:
            prob /= s
            area = cv.H * cv.W / px / px * float((wool > 0).mean() + 0.02)
            nf = int(fibres_per_mm2 * area)
            idx = rr.choice(h.size, nf, p=prob)
            fl8 = np.zeros(h.shape, np.uint8)
            for q in idx:
                y0, x0 = divmod(int(q), cv.W); n = rr.integers(5, 26); a = rr.uniform(0, 2 * math.pi)
                pts = [(x0, y0)]
                step = 0.09 * px
                for _ in range(n):
                    a += rr.normal(0, 0.22); pts.append((pts[-1][0] + math.cos(a) * step, pts[-1][1] + math.sin(a) * step))
                pp = np.round(np.array(pts)).astype(np.int32)
                cv2.polylines(fl8, [pp], False, int(rr.integers(50, 120)), 1, cv2.LINE_AA)
            fl = fl8.astype(np.float32) / 255
        wb = cv2.GaussianBlur(wool, (0, 0), 0.25 * px)
        fcol = cv2.GaussianBlur(alb * wool[..., None], (0, 0), 0.25 * px) / (wb[..., None] + 1e-4)
        fa = fl[..., None]
        alb = alb * (1 - fa) + fcol * 1.12 * fa
        cv.fibres = fl
        # fibres add a hair of height (they sit on top) so the normal map gets a faint trace
        cv.h = cv.h + 0.03 * fl
    cv.alb_final = np.clip(alb, 0, 1)
    return cv

def normal_map(h, px, sigma_hp_mm=None, strength=1.0):
    """Tangent-space normal map (OpenGL, Y up in texture = -y image) of the height (mm).
    If sigma_hp_mm is given, only the high-pass (h - blur) is encoded (the mesh carries the low-pass)."""
    hh = h.astype(np.float32)
    if sigma_hp_mm:
        hh = hh - cv2.GaussianBlur(hh, (0, 0), sigma_hp_mm * px)
    hs = cv2.GaussianBlur(hh, (0, 0), 0.5)
    gx = cv2.Sobel(hs, cv2.CV_32F, 1, 0, ksize=3) / 8 * px * strength
    gy = cv2.Sobel(hs, cv2.CV_32F, 0, 1, ksize=3) / 8 * px * strength
    # image y down; texture v up -> tangent-space y = -(-gy) = +gy? N = (-dh/dx, -dh/dv, 1) with v = -y -> dh/dv = -dh/dy
    N = np.dstack([-gx, gy, np.ones_like(hh)])
    N /= np.linalg.norm(N, axis=2, keepdims=True)
    return N

def save_png16(path, rgb01):
    a = np.clip(rgb01, 0, 1)
    cv2.imwrite(path, (a[..., ::-1] * 65535 + 0.5).astype(np.uint16))

def save_png8(path, rgb01, alpha=None):
    a = np.clip(rgb01, 0, 1)
    if alpha is None:
        cv2.imwrite(path, (a[..., ::-1] * 255 + 0.5).astype(np.uint8))
    else:
        rgba = np.dstack([a[..., ::-1], np.clip(alpha, 0, 1)[..., None]])
        cv2.imwrite(path, (rgba * 255 + 0.5).astype(np.uint8))

# ------------------------------------------------------------------ quick numpy preview shader (for iteration only)
def preview(h, alb, mat, T, px, az=135, el=22, march=True):
    H, W = h.shape
    hs = cv2.GaussianBlur(h, (0, 0), 0.6)
    gxh = cv2.Sobel(hs, cv2.CV_32F, 1, 0, ksize=3) / 8 * px
    gyh = cv2.Sobel(hs, cv2.CV_32F, 0, 1, ksize=3) / 8 * px
    N = np.dstack([-gxh, -gyh, np.ones_like(h)]); N /= np.linalg.norm(N, axis=2, keepdims=True)
    a, e = math.radians(az), math.radians(el)
    L = np.array([math.cos(a) * math.cos(e), -math.sin(a) * math.cos(e), math.sin(e)], np.float32)
    ndl = N @ L
    diff = np.clip((ndl + 0.25) / 1.25, 0, 1)
    vis = np.ones_like(h)
    if march:
        l2 = L[:2] / (np.linalg.norm(L[:2]) + 1e-6); tan_el = L[2] / np.linalg.norm(L[:2])
        pad = 70; hp = cv2.copyMakeBorder(h, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
        ex = np.zeros_like(h)
        for s in range(1, 50):
            dpx = s * 1.3
            ox, oy = int(round(l2[0] * dpx)), int(round(l2[1] * dpx))
            sh = hp[pad + oy:pad + oy + H, pad + ox:pad + ox + W]
            ex = np.maximum(ex, sh - (h + dpx / px * tan_el))
        vis = cv2.GaussianBlur(np.clip(1 - ex / 0.12, 0, 1), (0, 0), 1.0)
    V = np.array([0, 0, 1], np.float32); Hh = (L + V) / np.linalg.norm(L + V)
    T3 = np.dstack([T[..., 0], T[..., 1], np.zeros_like(h)])
    T3 -= np.sum(T3 * N, 2, keepdims=True) * N; T3 /= np.linalg.norm(T3, axis=2, keepdims=True) + 1e-6
    sin_th = np.sqrt(np.clip(1 - np.sum(T3 * Hh, 2) ** 2, 0, 1))
    metal = mat[..., 1]
    expo = np.where(metal > 0.5, 160.0, np.where(mat[..., 0] < 0.6, 40.0, 8.0))
    ks = np.where(metal > 0.5, 1.2, np.where(mat[..., 0] < 0.6, 0.15, 0.05))
    spec = (ks * sin_th ** expo)[..., None] * np.where((metal > 0.5)[..., None], alb / (alb.max(2, keepdims=True) + 1e-6), 1.0)
    spec *= sstep(-0.1, 0.25, ndl)[..., None]
    key = np.array([1.0, 0.92, 0.80], np.float32) * 2.3
    fill = np.array([0.80, 0.86, 1.0], np.float32) * 0.32
    md = np.where((metal > 0.5)[..., None], 0.3, 1.0)
    col = alb * md * (fill + key * (diff * vis)[..., None]) + spec * key * vis[..., None]
    x = col * 0.85
    y = np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)
    return (lin_to_srgb(y) * 255 + 0.5).astype(np.uint8)

def fill_cord(cv, skel, tx, ty, r=0.75, hgt=0.8, base=None, cols=None, pitch=1.7, tie_s=4.2, seed=0, order=0.95,
              tie_col=None):
    """Couched two-ply twisted cord along a skeleton (clean rope, regular twist, tie-downs every tie_s mm)."""
    from scipy import ndimage
    px = cv.px
    band = cv2.dilate(skel.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(2 * r * px) + 3,) * 2)) > 0
    dist, (iy, ix) = ndimage.distance_transform_edt(~skel, return_indices=True)
    TX, TY = tx[iy, ix], ty[iy, ix]
    yy, xx = np.mgrid[0:cv.H, 0:cv.W].astype(np.float32)
    PHI, PSI, DXo, DYo, bb = phase_fields(tx, ty, band, px, margin_mm=1.0)
    # signed across coordinate (mm) w.r.t. the oriented tangent
    across = ((xx - ix) * (-DYo[iy, ix]) + (yy - iy) * DXo[iy, ix]) / px
    d = dist / px
    prof = np.sqrt(np.clip(1 - (d / r) ** 2, 0, 1))
    ph = (PSI + across * math.tan(math.radians(48))) / pitch
    ply = np.floor(2 * ph); fr = 2 * ph - ply
    plyp = np.sin(math.pi * fr) ** 0.6                       # each ply a rounded strand crossing the cord diagonally
    tw = 0.5 + 0.5 * np.cos(2 * math.pi * (PSI * 9 + across * 3.0))   # fibre twist inside each ply
    hh = hgt * prof * (0.62 + 0.38 * plyp) * (0.96 + 0.04 * tw)
    # tie-down stitches across the cord
    tq = PSI / tie_s + 0.13 * snoise(PSI.shape, 30 * px, seed + 1)
    dt = (tq - np.round(tq)) * tie_s
    tie = (np.abs(dt) < 0.14) & (np.abs(across) < r * 1.05)
    hh = np.where(tie, np.maximum(hh * 0.85, hgt * 0.9 + 0.12 * np.sqrt(np.clip(1 - (dt / 0.14) ** 2, 0, 1))), hh)
    if base is not None: hh = hh + base
    cols = cols or [hex_lin('#4A2A17'), hex_lin('#5E3822')]
    ca, cb = np.asarray(cols[0], np.float32), np.asarray(cols[1], np.float32)
    pc = np.where((np.mod(ply, 2) == 0)[..., None], ca, cb) * (0.80 + 0.20 * plyp[..., None]) * (0.95 + 0.05 * tw[..., None])
    tc = np.asarray(tie_col if tie_col is not None else hex_lin('#2B170D'), np.float32)
    col = np.where(tie[..., None], tc * (0.9 + 0.1 * prof[..., None]), pc)
    on = band & (prof > 0.02)
    T = np.where(tie[..., None], np.stack([-DYo, DXo], -1), np.stack([DXo * 0.67 - DYo * 0.74, DXo * 0.74 + DYo * 0.67], -1))
    sl = (slice(0, cv.H), slice(0, cv.W))
    _put_sub(cv, sl, on, hh, col, MAT_WOOL, T, 1, np.full(on.shape, order, np.float32))
