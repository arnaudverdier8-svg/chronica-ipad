"""Procedural Bayeux-stitch reference swatch (numpy + cv2, CPU only, ~20-40 s).

Renders the same 48 x 36 mm patch twice at 20 px/mm:
  LEFT  = 'naive CG'   (perfect spacing, uniform colour, no fuzz, plastic Blinn spec)
  RIGHT = 'recommended' (jittered geometry, dye variation, ply twist, fuzz/halo,
                         Kajiya-Kay anisotropic wool sheen, soft height-field raking shadows)
Patch content: linen tabby 18.5 x 19 threads/cm, two laid-and-couched fills (terracotta, woad)
with couching bars + tie-downs, blue-black stem-stitch outlines, one couched metal-gold line.

Usage: python3 -I stitch_ref.py [out.png] [light_azimuth_deg] [light_elev_deg]
The functions are written so they can be lifted into the production compositor
(all sizes are in millimetres; PX converts to pixels).
"""
import sys, math, os
import numpy as np, cv2

PX = 20.0                      # pixels per millimetre
W, H = 960, 720                # 48 x 36 mm
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'stitch_ref.png')
AZ = float(sys.argv[2]) if len(sys.argv) > 2 else 135.0   # light comes FROM upper-left (screen x right, y down)
EL = float(sys.argv[3]) if len(sys.argv) > 3 else 22.0    # raking elevation in degrees

def hex_lin(h):
    c = np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

LINEN, TERRA, WOAD, INK, GOLD = map(hex_lin, ['#D4BE98', '#B65E43', '#4F6F8A', '#22232F', '#E9BE6A'])

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
X, Y = xx / PX, yy / PX         # mm

def smooth_noise(scale_mm, seed, shape=(H, W)):
    r = np.random.default_rng(seed)
    gh, gw = int(shape[0] / (scale_mm * PX)) + 3, int(shape[1] / (scale_mm * PX)) + 3
    g = r.standard_normal((gh, gw)).astype(np.float32)
    return cv2.resize(g, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC) * 0.7

def hash1(i, seed):
    i = np.asarray(i, np.int64)
    v = (i * 374761393 + seed * 668265263) & 0xFFFFFFFF
    v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((v ^ (v >> 16)) & 0xFFFF).astype(np.float32) / 65535.0

def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

def render(rec):
    J = 1.0 if rec else 0.0     # jitter switch
    # ---------------- linen tabby ----------------
    pw, pf, td = 10 / 18.5, 10 / 19.0, 0.42          # warp pitch, weft pitch, thread dia (mm)
    Xw = X + J * 0.10 * smooth_noise(6, 1)            # wandering threads / uneven spacing
    Yw = Y + J * 0.10 * smooth_noise(6, 2)
    xi, yi = Xw / pw, Yw / pf
    i, j = np.floor(xi), np.floor(yi)
    tx, ty = xi - i - 0.5, yi - j - 0.5
    n1d = np.convolve(np.random.default_rng(4).standard_normal(200000), np.hanning(41), 'same').astype(np.float32) / 4.5
    def slub(idx, along, seed):          # 1-D noise along each thread, decorrelated per thread
        pos = (along * 4 + hash1(idx, seed) * 150000).astype(np.int64) % 199000   # 0.25 mm/sample -> slubs ~3-10 mm long
        return np.clip(n1d[pos] - 1.5, 0, None)                                  # rare: ~5% of thread length
    slub_w = 1 + J * (0.16 * (hash1(i, 3) - 0.5) + 0.6 * slub(i, Yw, 4))
    slub_f = 1 + J * (0.16 * (hash1(j, 5) - 0.5) + 0.6 * slub(j, Xw, 6))
    rw, rf = 0.5 * td * slub_w, 0.5 * td * slub_f
    hw = 0.8 * rw * np.sqrt(np.clip(1 - (tx * pw / rw) ** 2, 0, 1)) + 0.07 * np.sin(math.pi * (yi + i))
    hf = 0.8 * rf * np.sqrt(np.clip(1 - (ty * pf / rf) ** 2, 0, 1)) - 0.07 * np.sin(math.pi * (xi + j))
    hw = np.where(np.abs(tx * pw) < rw, hw, -0.2); hf = np.where(np.abs(ty * pf) < rf, hf, -0.2)
    warp_top = hw >= hf
    h = np.maximum(np.maximum(hw, hf), -0.12)
    T = np.stack([np.where(warp_top, 0, 1), np.where(warp_top, 1, 0)], -1).astype(np.float32)
    alb = np.ones((H, W, 3), np.float32) * LINEN
    alb *= (1 + J * 0.05 * (np.where(warp_top, hash1(i, 7), hash1(j, 8)) - 0.5))[..., None]
    alb *= (1 + J * 0.05 * smooth_noise(12, 9))[..., None]
    mat = np.zeros((H, W), np.uint8)                   # 0 linen 1 wool 2 metal
    ksp = np.full((H, W), 0.05, np.float32); pexp = np.full((H, W), 24.0, np.float32)

    # ---------------- shapes ----------------
    def blob(cx, cy, R, seed, n=7):
        r = np.random.default_rng(seed); ang = np.linspace(0, 2 * math.pi, 400, endpoint=False)
        rad = R * (1 + sum(r.uniform(-.12, .12) * np.cos(k * ang + r.uniform(0, 6.28)) for k in range(2, n)))
        return np.stack([cx + rad * np.cos(ang), cy + 0.8 * rad * np.sin(ang)], 1)
    outer = blob(25, 18, 15, 11)
    m = np.zeros((H, W), np.uint8); cv2.fillPoly(m, [np.round(outer * PX).astype(np.int32)], 255)
    sdf = (cv2.distanceTransform(m, cv2.DIST_L2, 5) - cv2.distanceTransform(255 - m, cv2.DIST_L2, 5)) / PX
    divx = np.linspace(5, 45, 200); divy = 19 + 3.5 * np.sin(divx / 6.0) + 0.06 * (divx - 25)
    below = Y > np.interp(X, divx, divy)
    dist_div = np.abs(Y - np.interp(X, divx, divy))
    fill_sdf = np.minimum(sdf, dist_div) - 0.55 + J * 0.28 * smooth_noise(2.5, 12)   # fills stop short of / overlap the outline
    regions = [(~below, TERRA, math.radians(78), 21), (below, WOAD, math.radians(14), 31)]

    for reg, col, th0, sd in regions:
        th = th0 + J * math.radians(2.5) * smooth_noise(10, sd)
        d = np.stack([np.cos(th), np.sin(th)], -1)
        u = -X * np.sin(th) + Y * np.cos(th)          # across strands
        v = X * np.cos(th) + Y * np.sin(th)           # along strands
        p = 1.0                                       # laid strand pitch (mm) ~ yarn dia
        uu = u + J * 0.08 * p * smooth_noise(5, sd + 1)
        k = np.floor(uu / p); t = uu / p - k - 0.5
        wk = 1 + J * 0.24 * (hash1(k, sd) - 0.5)
        r = 0.56 * p * wk
        hl = 0.5 * np.sqrt(np.clip(1 - (t * p / r) ** 2, 0, 1))         # laid strand ~0.5 mm high
        twist = 0.5 + 0.5 * np.cos(2 * math.pi * (v + t * p * math.tan(math.radians(32))) / 0.7)
        hl *= 0.88 + 0.12 * twist                                          # S-ply ridges
        # couching bars (perpendicular to laid strands)
        s = 4.5
        u0 = float(np.median(u[reg & (sdf > 0)]))
        best = np.full((H, W), 99.0, np.float32); bidx = np.zeros((H, W), np.float32)
        for o in (-1, 0, 1):
            b = np.floor(v / s) + o
            cb = (b + 0.5) * s + J * (hash1(b, sd + 2) - 0.5) * 0.40 * s + J * 0.20 * smooth_noise(20, sd + 3)
            dd = (v - cb) + J * np.tan(math.radians(8) * (hash1(b, sd + 4) - 0.5)) * (u - u0)
            sel = np.abs(dd) < np.abs(best); best = np.where(sel, dd, best); bidx = np.where(sel, b, bidx)
        rb = 0.45
        hl *= 1 - 0.30 * np.exp(-(best / 0.95) ** 2)                      # laid strands squeezed by bar
        # tie-downs along each bar
        st = 4.0
        uq = u + J * (hash1(bidx, sd + 5) - 0.5) * st
        q = np.floor(uq / st); cq = (q + 0.5 + J * 0.25 * (hash1(q + 31 * bidx, sd + 6) - 0.5)) * st
        du = uq - cq
        pinch = 1 - 0.40 * np.exp(-(du / 0.6) ** 2)
        hb = 0.42 + 0.40 * np.sqrt(np.clip(1 - (best / rb) ** 2, 0, 1)) * pinch
        hb = np.where(np.abs(best) < rb, hb, -1)
        tie = (np.abs(du) < 0.26) & (np.abs(best) < 0.75)
        ht = np.where(tie, 0.62 + 0.25 * np.sqrt(np.clip(1 - (du / 0.26) ** 2, 0, 1)), -1)
        streak = cv2.remap(np.random.default_rng(sd + 7).standard_normal((256, 256)).astype(np.float32),
                           ((u / 0.09) % 255).astype(np.float32), ((v / 0.9) % 255).astype(np.float32), cv2.INTER_LINEAR)
        edge = sstep(0.0, 0.5, fill_sdf)
        inside = reg & (fill_sdf > 0)
        hfill = np.maximum.reduce([np.maximum(hl, 0.16) * edge + 0.05, hb * edge, ht * edge]) + J * 0.025 * streak * edge   # fibre-scale micro relief
        # tangents
        bar_dir = np.stack([-np.sin(th), np.cos(th)], -1)
        tw = math.radians(20) * J                                    # surface fibres follow ply helix
        def rot(vv, a): return np.stack([vv[..., 0] * math.cos(a) - vv[..., 1] * math.sin(a), vv[..., 0] * math.sin(a) + vv[..., 1] * math.cos(a)], -1)
        Tw = np.where((hb >= hl)[..., None] & ~tie[..., None], rot(bar_dir, tw), rot(d, tw))
        # albedo with dye variation (per strand, along strand, streaks, dye-lot)
        var = 1 + J * (0.09 * (hash1(k, sd + 8) - 0.5) + 0.035 * smooth_noise(8, sd + 9) + 0.06 * streak + 0.03 * smooth_noise(25, sd + 10))
        a = col[None, None, :] * var[..., None]
        a = a * (0.94 + 0.06 * twist[..., None]) if rec else a
        a = a * np.where((hl < 0.16) & (hb < 0)[..., None] if False else ((hl < 0.16) & (hb < 0))[..., None], 0.8, 1.0)
        on = inside & (hfill > h)
        h = np.where(on, hfill, h); alb = np.where(on[..., None], a, alb); T = np.where(on[..., None], Tw, T)
        mat = np.where(on, 1, mat)

    # ---------------- couched metal-gold line (underside-couching look) ----------------
    gx_ = np.linspace(12, 38, 300); gy_ = 26 + 2.2 * np.sin(gx_ / 3.2)
    for off in (-0.3, 0.3):
        pts = np.stack([gx_, gy_ + off], 1)
        mm = np.zeros((H, W), np.uint8)
        cv2.polylines(mm, [np.round(pts * PX).astype(np.int32)], False, 255, int(0.5 * PX), cv2.LINE_AA)
        dmet = cv2.distanceTransform(255 - (mm > 127).astype(np.uint8) * 255, cv2.DIST_L2, 5) / PX
        core = cv2.distanceTransform((mm > 127).astype(np.uint8), cv2.DIST_L2, 5) / PX
        hm = np.where(mm > 127, 0.75 + 0.22 * np.sqrt(np.clip(core / 0.25, 0, 1)), -1)
        along = gx_[np.clip(((X - 12) / 26 * 299).astype(int), 0, 299)]
        tie = (np.abs((along % 2.6) - 1.3) < 0.18)
        hm = np.where(tie & (mm > 127), hm - 0.12, hm)
        on = (hm > h) & (sdf > 1.0)
        h = np.where(on, hm, h); alb = np.where(on[..., None], np.where(tie[..., None], TERRA[None, None] * 1.1, GOLD[None, None]), alb)
        T = np.where(on[..., None], np.stack([np.ones_like(X), 0.6875 * np.cos(X / 3.2)], -1) / np.sqrt(1 + (0.6875 * np.cos(X / 3.2)) ** 2)[..., None], T)
        mat = np.where(on, np.where(tie, 1, 2), mat)

    # ---------------- stem-stitch outlines ----------------
    def stem(poly, seed):
        nonlocal h, alb, T, mat
        rr = np.random.default_rng(seed)
        seg = np.diff(poly, axis=0); sl = np.hypot(seg[:, 0], seg[:, 1]); s_cum = np.concatenate([[0], np.cumsum(sl)])
        def P(s):
            s = np.clip(s, 0, s_cum[-1]); return np.stack([np.interp(s, s_cum, poly[:, 0]), np.interp(s, s_cum, poly[:, 1])], -1)
        s0 = 0.0; off = 0.28; r = 0.45
        while s0 < s_cum[-1] - 0.5:
            L = 3.5 * (1 + J * rr.uniform(-0.18, 0.18))
            a, b = P(s0), P(s0 + L)
            tvec = (b - a) / (np.linalg.norm(b - a) + 1e-6); n = np.array([-tvec[1], tvec[0]])
            A = a - n * off + J * rr.normal(0, 0.06, 2); B = b + n * off + J * rr.normal(0, 0.06, 2)
            x0, x1 = int((min(A[0], B[0]) - 1) * PX), int((max(A[0], B[0]) + 1) * PX) + 1
            y0, y1 = int((min(A[1], B[1]) - 1) * PX), int((max(A[1], B[1]) + 1) * PX) + 1
            x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
            if x1 > x0 and y1 > y0:
                px_, py_ = X[y0:y1, x0:x1], Y[y0:y1, x0:x1]
                AB = B - A; ll = AB @ AB
                tt = np.clip(((px_ - A[0]) * AB[0] + (py_ - A[1]) * AB[1]) / ll, 0, 1)
                dx, dy = px_ - (A[0] + tt * AB[0]), py_ - (A[1] + tt * AB[1]); dist = np.hypot(dx, dy)
                rr_ = r * (1 + J * 0.12 * (rr.random() - 0.5))
                prof = np.sqrt(np.clip(1 - (dist / rr_) ** 2, 0, 1)) * (0.55 + 0.45 * np.sin(math.pi * tt) ** 0.5)
                along = np.hypot(px_ - A[0], py_ - A[1])
                tw = 0.5 + 0.5 * np.cos(2 * math.pi * (along + (dist) * 0.6) / 0.7)
                hs = 0.55 + 0.5 * prof * (0.88 + 0.12 * tw)
                on = (prof > 0.02) & (hs > h[y0:y1, x0:x1] - 0.05)
                c = INK * (1 + J * rr.uniform(-0.06, 0.06)) * (1 + J * 0.05 * (tw - 0.5))[..., None]
                h[y0:y1, x0:x1] = np.where(on, np.maximum(hs, h[y0:y1, x0:x1]), h[y0:y1, x0:x1])
                alb[y0:y1, x0:x1] = np.where(on[..., None], c, alb[y0:y1, x0:x1])
                ang = math.atan2(AB[1], AB[0]) + J * math.radians(15)
                T[y0:y1, x0:x1] = np.where(on[..., None], np.array([math.cos(ang), math.sin(ang)], np.float32), T[y0:y1, x0:x1])
                mat[y0:y1, x0:x1] = np.where(on, 1, mat[y0:y1, x0:x1])
            s0 += L / 2
    stem(np.vstack([outer, outer[:1]]), 41)
    dv = np.stack([divx, divy], 1); keep = sdf[np.clip((divy * PX).astype(int), 0, H - 1), np.clip((divx * PX).astype(int), 0, W - 1)] > 0.2
    stem(dv[keep], 42)

    # ---------------- shading ----------------
    h = h.astype(np.float32); alb = alb.astype(np.float32); T = T.astype(np.float32)
    hs = cv2.GaussianBlur(h, (0, 0), 0.6)
    gxh = cv2.Sobel(hs, cv2.CV_32F, 1, 0, ksize=3) / 8 * PX
    gyh = cv2.Sobel(hs, cv2.CV_32F, 0, 1, ksize=3) / 8 * PX
    N = np.dstack([-gxh, -gyh, np.ones_like(h)]); N /= np.linalg.norm(N, axis=2, keepdims=True)
    az, el = math.radians(AZ), math.radians(EL)
    L = np.array([math.cos(az) * math.cos(el), -math.sin(az) * math.cos(el), math.sin(el)], np.float32)  # y-down screen
    L /= np.linalg.norm(L)
    V = np.array([0, 0, 1], np.float32)
    ndl = N @ L
    wrap = 0.25
    diff = np.clip((ndl + wrap) / (1 + wrap), 0, 1)
    # soft height-field shadow (march toward the light)
    l2 = L[:2] / (np.linalg.norm(L[:2]) + 1e-6); tan_el = L[2] / np.linalg.norm(L[:2])
    pad = 80; hp = cv2.copyMakeBorder(h, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
    excess = np.zeros_like(h)
    for sstep_ in range(1, 61):
        dpx = sstep_ * 1.25
        ox, oy = int(round(l2[0] * dpx)), int(round(l2[1] * dpx))
        sh = hp[pad + oy:pad + oy + H, pad + ox:pad + ox + W]
        excess = np.maximum(excess, sh - (h + dpx / PX * tan_el))
    vis = np.clip(1 - excess / 0.12, 0, 1)
    vis = cv2.GaussianBlur(vis, (0, 0), 1.2)
    ao = np.clip(1 - 1.6 * np.clip(cv2.GaussianBlur(h, (0, 0), 0.8 * PX) - h, 0, None), 0.4, 1)
    Hh = (L + V); Hh /= np.linalg.norm(Hh)
    if rec:
        T3 = np.dstack([T[..., 0], T[..., 1], np.zeros_like(h)])
        T3 -= (np.sum(T3 * N, 2, keepdims=True)) * N; T3 /= np.linalg.norm(T3, axis=2, keepdims=True) + 1e-6
        tdh = np.sum(T3 * Hh, 2); sin_th = np.sqrt(np.clip(1 - tdh ** 2, 0, 1))
        p1 = np.select([mat == 0, mat == 1, mat == 2], [24.0, 8.0, 180.0])
        k1 = np.select([mat == 0, mat == 1, mat == 2], [0.05, 0.045, 1.4])
        spec = (k1 * sin_th ** p1)[..., None] * np.where((mat == 2)[..., None], GOLD / GOLD.max(), 0.6 + 0.4 * alb / (alb.max(2, keepdims=True) + 1e-6))
        spec += ((np.where(mat == 1, 0.06, 0.0) * sin_th ** 3)[..., None]) * alb * 1.5     # TRT-like coloured lobe
        sheen = (np.where(mat == 1, 0.12, 0.04) * (1 - N[..., 2]) ** 2)[..., None] * (alb * 0.8 + 0.08)
        spec *= sstep(-0.1, 0.25, ndl)[..., None]
        metal_diff = np.where((mat == 2)[..., None], 0.25, 1.0)
    else:
        ndh = np.clip(N @ Hh, 0, 1)
        spec = (0.35 * ndh ** 40)[..., None] * np.ones(3)
        sheen = 0; metal_diff = np.where((mat == 2)[..., None], 0.5, 1.0)
    key = np.array([1.0, 0.92, 0.80], np.float32) * 2.3
    fill = np.array([0.80, 0.86, 1.0], np.float32) * 0.30
    col = alb * metal_diff * (fill * ao[..., None] + key * (diff * vis)[..., None]) + (spec + sheen) * key * vis[..., None]

    # ---------------- fuzz + halo (recommended only) ----------------
    if rec:
        wool = (mat == 1).astype(np.float32)
        halo = cv2.GaussianBlur(wool, (0, 0), 0.30 * PX)
        halo_col = cv2.GaussianBlur(col * wool[..., None], (0, 0), 0.30 * PX) / (halo[..., None] + 1e-4)
        hal_a = (np.clip(halo - wool, 0, 1) * 0.35)[..., None]
        col = col * (1 - hal_a) + halo_col * 1.05 * hal_a
        rr = np.random.default_rng(99)
        edge = cv2.morphologyEx(wool, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8))
        prob = (wool * 0.25 + edge * 2.0).ravel(); prob /= prob.sum()
        nf = int(0.7 * (W / PX) * (H / PX))                                # ~0.7 fibres / mm^2 of patch
        idx = rr.choice(H * W, nf, p=prob)
        fl = np.zeros((H, W), np.uint8)
        for q in idx:
            y0, x0 = divmod(int(q), W); n = rr.integers(4, 22); a = rr.uniform(0, 2 * math.pi)
            pts = [(x0, y0)]
            for _ in range(n):
                a += rr.normal(0, 0.25); pts.append((pts[-1][0] + math.cos(a) * 1.5, pts[-1][1] + math.sin(a) * 1.5))
            pp = np.round(np.array(pts)).astype(np.int32)
            cv2.polylines(fl, [pp], False, int(rr.integers(60, 130)), 1, cv2.LINE_AA)
        # fibre colour: local wool colour, brightened (fibres catch the raking light)
        wb = cv2.GaussianBlur(wool, (0, 0), 3.0)
        fcol = cv2.GaussianBlur(col * wool[..., None], (0, 0), 3.0) / (wb[..., None] + 1e-4)
        fa = (fl.astype(np.float32) / 255)[..., None]
        col = col * (1 - fa) + fcol * 1.15 * fa
    # tone map (ACES fit) + sRGB
    x = col * 0.85
    y = np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)
    srgb = np.where(y <= 0.0031308, 12.92 * y, 1.055 * y ** (1 / 2.4) - 0.055)
    return (srgb * 255 + 0.5).astype(np.uint8), h

a, ha = render(False)
b, hb = render(True)
img = np.hstack([a, np.full((H, 8, 3), 20, np.uint8), b])
from PIL import Image, ImageDraw
im = Image.fromarray(img); d = ImageDraw.Draw(im)
d.rectangle([0, 0, 380, 26], fill=(20, 18, 22)); d.text((8, 7), 'NAIVE CG: regular, uniform, plastic, no fuzz', fill=(235, 225, 205))
d.rectangle([W + 8, 0, W + 8 + 470, 26], fill=(20, 18, 22)); d.text((W + 16, 7), 'RECOMMENDED: jitter, dye variation, ply twist, aniso sheen, fuzz', fill=(235, 225, 205))
d.text((8, H - 18), f'48 x 36 mm @ 20 px/mm  light az {AZ:.0f} el {EL:.0f}', fill=(40, 30, 25))
im.save(OUT)
np.save(OUT.replace('.png', '_height_mm.npy'), hb.astype(np.float16))
print('wrote', OUT, 'height range mm', float(hb.min()), float(hb.max()))
