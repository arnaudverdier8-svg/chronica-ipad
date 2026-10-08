"""Procedural linen tabby ground (after style/tools/stitch_ref.py), any canvas size.
Returns maps dict: h (mm), alb (linear RGB), T (unit tangent xy), mat (uint8), cov (wool coverage 0)."""
import math
import numpy as np, cv2
from .core import hash1, smooth_noise, hex_lin, LINEN


def make_linen(Hpx, Wpx, PX, seed=0, warp_cm=18.5, weft_cm=19.0, td=0.46, age=1.0):
    yy, xx = np.mgrid[0:Hpx, 0:Wpx].astype(np.float32)
    X, Y = xx / PX, yy / PX
    sh = (Hpx, Wpx)
    pw, pf = 10 / warp_cm, 10 / weft_cm
    Xw = X + 0.10 * smooth_noise(sh, 6 * PX, seed + 1) + 0.05 * smooth_noise(sh, 1.5 * PX, seed + 11)
    Yw = Y + 0.10 * smooth_noise(sh, 6 * PX, seed + 2) + 0.05 * smooth_noise(sh, 1.5 * PX, seed + 12)
    xi, yi = Xw / pw, Yw / pf
    i, j = np.floor(xi), np.floor(yi)
    tx, ty = xi - i - 0.5, yi - j - 0.5
    rng = np.random.default_rng(seed + 4)
    n1d = np.convolve(rng.standard_normal(400000), np.hanning(41), 'same').astype(np.float32) / 4.5

    def slub(idx, along, s):
        pos = (along * 4 + hash1(idx, s) * 300000).astype(np.int64) % 399000
        return np.clip(n1d[pos] - 1.45, 0, None)
    slub_w = 1 + 0.16 * (hash1(i, seed + 3) - 0.5) + 0.7 * slub(i, Yw, seed + 4)
    slub_f = 1 + 0.16 * (hash1(j, seed + 5) - 0.5) + 0.7 * slub(j, Xw, seed + 6)
    rw, rf = 0.5 * td * slub_w, 0.5 * td * slub_f
    # thread cross-section + over/under undulation
    hw = 0.8 * rw * np.sqrt(np.clip(1 - (tx * pw / rw) ** 2, 0, 1)) + 0.07 * np.sin(math.pi * (yi + i))
    hf = 0.8 * rf * np.sqrt(np.clip(1 - (ty * pf / rf) ** 2, 0, 1)) - 0.07 * np.sin(math.pi * (xi + j))
    inw, inf = np.abs(tx * pw) < rw, np.abs(ty * pf) < rf
    hw = np.where(inw, hw, -0.2); hf = np.where(inf, hf, -0.2)
    warp_top = hw >= hf
    h = np.maximum(np.maximum(hw, hf), -0.14)
    # fibre streaks along each thread (micro relief)
    st = cv2.resize(np.random.default_rng(seed + 7).standard_normal((Hpx // 3 + 1, Wpx // 3 + 1)).astype(np.float32), (Wpx, Hpx))
    stw = cv2.GaussianBlur(st, (0, 0), sigmaX=0.4, sigmaY=4.0)
    stf = cv2.GaussianBlur(st, (0, 0), sigmaX=4.0, sigmaY=0.4)
    h = h + np.where(warp_top, stw, stf) * 0.012
    gap = (~inw) & (~inf)
    T = np.stack([np.where(warp_top, 0, 1), np.where(warp_top, 1, 0)], -1).astype(np.float32)
    base = hex_lin('#D4BE98')
    alb = np.ones((Hpx, Wpx, 3), np.float32) * base
    per_thread = np.where(warp_top, hash1(i, seed + 7), hash1(j, seed + 8)) - 0.5
    alb *= (1 + 0.07 * per_thread + 0.05 * np.where(warp_top, stw, stf) * 0.5)[..., None]
    alb *= (1 + 0.045 * smooth_noise(sh, 12 * PX, seed + 9, 2))[..., None]
    # slubs are slightly lighter and a touch greener-grey (unbleached flax)
    sl = np.where(warp_top, slub_w, slub_f) - 1
    alb *= (1 + 0.10 * np.clip(sl, 0, 1))[..., None]
    # gaps between threads: backing / shadow shows through
    alb = np.where(gap[..., None], alb * 0.55, alb)
    cov = np.zeros((Hpx, Wpx), np.float32)
    mat = np.zeros((Hpx, Wpx), np.uint8)
    return dict(h=h.astype(np.float32), alb=alb.astype(np.float32), T=T, mat=mat, cov=cov, PX=PX)


def add_ageing(m, seed=0, density=0.3, edge_bias=None):
    """foxing spots, a tideline, soft creases (height). density = fraction of real Bayeux density."""
    H, W = m['h'].shape; PX = m['PX']
    r = np.random.default_rng(seed)
    alb, h = m['alb'], m['h']
    fox = np.zeros((H, W), np.float32)
    area_dm2 = (H / PX) * (W / PX) / 1e4
    n = int(7 * area_dm2 * density * 1.0)
    for _ in range(n):
        cx, cy = r.uniform(0, W), r.uniform(0, H)
        if edge_bias is not None and r.random() > edge_bias(cx / W, cy / H):
            continue
        for _k in range(r.integers(1, 5)):
            rad = r.uniform(0.25, 1.5) * PX
            ox, oy = r.normal(0, 2 * PX, 2)
            cv2.circle(fox, (int(cx + ox), int(cy + oy)), max(1, int(rad)), float(r.uniform(0.4, 1.0)), -1, cv2.LINE_AA)
    fox = cv2.GaussianBlur(fox, (0, 0), 0.35 * PX)
    foxc = hex_lin('#9C7046')
    a = np.clip(fox * 0.30, 0, 0.35)[..., None]
    alb[:] = alb * (1 - a) + alb * (foxc / foxc.max()) * a
    # soft creases (low-frequency height) + subtle large undulation
    cre = np.zeros((H, W), np.float32)
    for _ in range(max(1, int(3 * area_dm2 * density))):
        y0 = r.uniform(0, H); ang = r.normal(0, 0.08); amp = r.uniform(0.15, 0.45); wid = r.uniform(3, 9) * PX
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = (yy - y0) * math.cos(ang) - (xx - W / 2) * math.sin(ang)
        fall = np.clip(1 - np.abs(xx - r.uniform(0, W)) / (r.uniform(0.3, 0.8) * W), 0, 1)
        cre += amp * np.exp(-(d / wid) ** 2) * fall
    h += cre - cre.mean()
    return m
