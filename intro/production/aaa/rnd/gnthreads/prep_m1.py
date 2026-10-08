# prep_m1.py - re-embroider the king crop (p1_oath x1100-1700 y380-1000) as thread geometry.
# Output: work/m1_tubes.npz (+ previews). Units mm, motif centred at origin.
import sys, os, time, math, json
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from strandlib import *

AAA = os.path.abspath(os.path.join(HERE, '..', '..'))
W_ = os.path.join(HERE, 'work'); os.makedirs(W_, exist_ok=True)
t0 = time.time()
rng = np.random.default_rng(11)
PPM = 5.0                              # panel native: 5 px/mm
src = cv2.imread(os.path.join(AAA, '..', 'intro', 'p1_oath.png'))[380:1000, 1100:1700]
H, W = src.shape[:2]
rgb = src[..., ::-1].astype(np.float32) / 255
names, pal = load_palette(os.path.join(AAA, 'style', 'palette.json'))

# ---------------------------------------------------------------- segmentation
filt = cv2.pyrMeanShiftFiltering(src, 5, 12)
flab = cv2.cvtColor(filt, cv2.COLOR_BGR2LAB).astype(np.float32)
L = flab[..., 0] * 100 / 255
hsv = cv2.cvtColor(filt, cv2.COLOR_BGR2HSV).astype(np.float32)
hue = hsv[..., 0] * 2; sat = hsv[..., 1] / 255; val = hsv[..., 2] / 255

bgc = np.array([168, 197, 219], np.float32)       # BGR of linen ground in the panel
bglab = cv2.cvtColor(bgc.reshape(1, 1, 3).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)[0, 0]
dbg = np.linalg.norm(flab - bglab, axis=2)
bgm = (dbg < 14).astype(np.uint8)
bgm = cv2.morphologyEx(bgm, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
n, cc, st, _ = cv2.connectedComponentsWithStats(bgm, 8)
keep = np.zeros(n, bool)
for i in range(1, n):
    x, y, w, h, a = st[i]
    if a > 700: keep[i] = True
bg = keep[cc]
bg = cv2.morphologyEx(bg.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
n, cc, st, _ = cv2.connectedComponentsWithStats((~bg).astype(np.uint8), 8)
small = np.zeros(n, bool); small[1:] = st[1:, 4] < 250
bg |= small[cc]
# organic 'work-in-progress' boundary instead of the rectangular crop edge: stitching stops 3-12 mm inside the crop,
# the designer's underdrawing continues on the bare linen (exported as an ink mask for the linen shader)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
d_edge = np.minimum(np.minimum(xx, W - 1 - xx), np.minimum(yy, H - 1 - yy)) / PPM
nz_ = cv2.resize(rng.random((7, 7)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
nz2 = cv2.resize(rng.random((22, 22)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
margin = 2.5 + 9.0 * np.clip(nz_, 0, 1) + 1.5 * nz2
outside = d_edge < margin
OUTSIDE = outside.copy()
bg |= outside

dark = (L < 20) & ~bg
Lraw = cv2.cvtColor(src, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32) * 100 / 255
bh = cv2.morphologyEx(cv2.GaussianBlur(Lraw, (0, 0), 0.8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))) - cv2.GaussianBlur(Lraw, (0, 0), 0.8)
fine_dark = (bh > 16) & (Lraw < 45) & ~bg
fine_dark = cv2.morphologyEx(fine_dark.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)).astype(bool)
dark |= fine_dark
dark = cv2.morphologyEx(dark.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)).astype(bool)
thick = cv2.morphologyEx(dark.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))).astype(bool)
dark &= ~thick                       # thick dark masses are filled with dark wool, thin dark lines become stem stitch
gold = (hue > 28) & (hue < 58) & (sat > 0.42) & (val > 0.55) & ~bg & ~dark
gold = cv2.morphologyEx(gold.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)).astype(bool)
wool = ~bg & ~dark & ~gold

# skein colours (what an embroiderer would buy): k-means on OKLab of the filtered image
from sklearn.cluster import KMeans
ok = srgb_to_oklab(filt[..., ::-1].reshape(-1, 3).astype(np.float32) / 255)
sel = (wool | dark).reshape(-1)
km = KMeans(22, n_init=3, random_state=0).fit(ok[sel][::5])
sk_ok = km.cluster_centers_.astype(np.float32)
sk_rgb = oklab_to_srgb(sk_ok)
sk_rgb_n, sk_pal = nudge_to_palette(sk_rgb, pal, amount=0.2, cmax=0.14)

# coarse zones (strands stop at zone borders; colour changes per stitch inside a zone)
NZ = 8
km2 = KMeans(NZ, n_init=3, random_state=1).fit(ok[wool.reshape(-1)][::5])
cz = km2.predict(ok).reshape(H, W)
best = np.full((H, W), -1.0, np.float32); czm = np.zeros((H, W), np.int32)
for k in range(NZ):
    m = cv2.blur((cz == k).astype(np.float32), (9, 9)); upd = m > best; best[upd] = m[upd]; czm[upd] = k
zc = km2.cluster_centers_
FINE0 = np.zeros((H, W), np.uint8); cv2.ellipse(FINE0, (272, 262), (60, 56), 0, 0, 360, 1, -1); FINE0 = FINE0.astype(bool)
zone_lab = np.full((H, W), -1, np.int32)
laid_mask = np.zeros((H, W), bool)
zid = 0
zinfo = {}
for k in range(NZ):
    hz = (math.degrees(math.atan2(zc[k, 2], zc[k, 1])) + 360) % 360; Cz = math.hypot(zc[k, 1], zc[k, 2])
    Lz = zc[k, 0]
    fabric = ((hz > 200 or hz < 25) and Cz > 0.035) or (25 <= hz <= 80 and Lz < 0.66 and Cz > 0.04)   # cloth + carved wood -> laid & couched
    mk = ((czm == k) & (wool | dark) & ~FINE0).astype(np.uint8)
    mk = cv2.morphologyEx(mk, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    mk = cv2.morphologyEx(mk, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, cc, st, _ = cv2.connectedComponentsWithStats(mk, 4)
    for i in range(1, n):
        if fabric and st[i, 4] / PPM ** 2 > 60:
            m = (cc == i) & wool & (zone_lab < 1000)
            zone_lab[m] = 1000 + zid; laid_mask |= m; zinfo[1000 + zid] = k; zid += 1
    print('zone', k, 'hue', round(hz), 'C', round(Cz, 3), 'L', round(float(Lz), 3), 'fabric', fabric)
split_mask = wool & ~laid_mask
zone_lab[split_mask] = czm[split_mask]
print('laid zones', zid, 'laid frac', laid_mask.mean().round(3), 'split frac', split_mask.mean().round(3),
      'gold', gold.mean().round(3), 'dark', dark.mean().round(3), 'bg', bg.mean().round(3))

# ---------------------------------------------------------------- direction fields
gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
def norm_t(J):
    tr = J[0] + J[2] + 1e-6; return (J[0] / tr, J[1] / tr, J[2] / tr)
Jf = structure_tensor(gray, 1.0, 4.0)
Jm = structure_tensor(gray, 1.5, 7.0)
Jc = structure_tensor(gray, 2.0, 16.0)
cf = tensor_dir(*Jf)[2]
J = blend_fields([(norm_t(Jf), 0.6 * (0.3 + cf)), (norm_t(Jm), 1.0), (norm_t(Jc), 0.6)])
fdx, fdy, fcoh = tensor_dir(*J)
Jl = blend_fields([(norm_t(Jc), 1.0), (norm_t(structure_tensor(gray, 3.0, 30.0)), 1.0)])
ldx, ldy, _ = tensor_dir(*Jl)
# dark lines: orientation from the dark mask itself
dm = cv2.GaussianBlur(dark.astype(np.float32), (0, 0), 1.2)
Jd = blend_fields([(norm_t(structure_tensor(dm, 0.8, 2.5)), 1.0), (norm_t(Jm), 0.25)])
ddx, ddy, _ = tensor_dir(*Jd)

# ---------------------------------------------------------------- tracing
def px2mm(p):
    return np.c_[(p[:, 0] - W / 2) / PPM, -(p[:, 1] - H / 2) / PPM]

T = Tubes()
MAT_WOOL, MAT_GOLD, MAT_SILK, MAT_CORD, MAT_FIBRE, MAT_TIE = 0, 1, 2, 3, 4, 5
lin_rgb = rgb  # srgb 0..1
blur_rgb = cv2.GaussianBlur(rgb, (0, 0), 4.0); blur_rgb_f = cv2.GaussianBlur(rgb, (0, 0), 1.8)

def skein_of(colors):
    okc = srgb_to_oklab(colors)
    d = ((okc[:, None] - sk_ok[None]) ** 2).sum(-1); return d.argmin(1)

# (1) fills
fill_lab = zone_lab.copy()
dxm = np.where(laid_mask, ldx, fdx).astype(np.float32); dym = np.where(laid_mask, ldy, fdy).astype(np.float32)
FINE = np.zeros((H, W), np.uint8)
cv2.ellipse(FINE, (272, 262), (60, 56), 0, 0, 360, 1, -1)          # artist hint: the face gets fine single-ply split stitch
FINE = FINE.astype(bool)
fine_lab = np.where(FINE & (fill_lab >= 0), fill_lab + 500, -1).astype(np.int32)
fill_lab = np.where(FINE, -1, fill_lab).astype(np.int32)
seeds = jitter_seeds(fill_lab >= 0, 2.0, rng)
dsep = 0.64 * PPM
fills = trace_layer(dxm, dym, fill_lab, seeds, 0.6, dsep, 0.5 * dsep, 400.0, 2.5 * PPM, maxturn_deg=50)
fine_fills = trace_layer(fdx, fdy, fine_lab, jitter_seeds(fine_lab >= 0, 1.0, rng), 0.4, 0.46 * PPM, 0.5 * 0.46 * PPM, 200.0, 1.2 * PPM, maxturn_deg=55)
print('fine strands', len(fine_fills))
cov = np.zeros((H, W), np.uint8)
for f_ in fills:
    cv2.polylines(cov, [np.round(f_ * 4).astype(np.int32)], False, 255, int(round(0.8 * PPM)), cv2.LINE_8, shift=2)
gap_lab = np.where((cov == 0) & (fill_lab >= 0), fill_lab, -1).astype(np.int32)
gap_lab = np.where(cv2.dilate((gap_lab >= 0).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0, fill_lab, -1).astype(np.int32)
gaps = trace_layer(dxm, dym, gap_lab, jitter_seeds(gap_lab >= 0, 1.0, rng), 0.5, 0.55 * PPM, 0.38 * PPM, 60.0, 2.0 * PPM, maxturn_deg=60)
print('gap fillers', len(gaps), 'uncovered frac before', ((cov == 0) & (fill_lab >= 0)).sum() / max(1, (fill_lab >= 0).sum()))
fills = fills + gaps
print('fill streamlines', len(fills), time.time() - t0)

# couching bars for laid zones: perpendicular field
bars = []
if laid_mask.any():
    bdx = (-ldy).astype(np.float32); bdy = ldx.astype(np.float32)
    blab = np.where(laid_mask, zone_lab, -1).astype(np.int32)
    bseeds = jitter_seeds(laid_mask, 6.0, rng)
    bsep = 4.5 * PPM
    bars = trace_layer(bdx, bdy, blab, bseeds, 0.8, bsep, 0.75 * bsep, 400.0, 3.0 * PPM, maxturn_deg=30)
print('bars', len(bars))
bar_img = np.zeros((H, W), np.uint8)
for b in bars:
    cv2.polylines(bar_img, [np.round(b * 4).astype(np.int32)], False, 255, 1, cv2.LINE_8, shift=2)
bar_dist = cv2.distanceTransform(255 - bar_img, cv2.DIST_L2, 5) / PPM      # mm to nearest bar

def laid_z(Pmm_px):
    d = sample_img(bar_dist[..., None], Pmm_px)[:, 0]
    return d

# (2) gold metal thread
gsep = 0.58 * PPM
glab = np.where(gold, 1, -1).astype(np.int32)
gold_lines = trace_layer(fdx, fdy, glab, jitter_seeds(gold, 1.5, rng), 0.5, gsep, 0.5 * gsep, 300.0, 0.8 * PPM, maxturn_deg=40)
print('gold lines', len(gold_lines))
gdist = cv2.distanceTransform(gold.astype(np.uint8), cv2.DIST_L2, 5) / PPM

# (3) dark: stem stitch rows; seeds first on ridge centres
ddist = cv2.distanceTransform(dark.astype(np.uint8), cv2.DIST_L2, 5)
ridge = (ddist >= cv2.dilate(ddist, np.ones((3, 3))) - 1e-3) & dark & (ddist > 0.9)
prio = np.stack(np.nonzero(ridge)[::-1], 1).astype(np.float32)
prio = prio[rng.permutation(len(prio))]
dlab = np.where(dark, 1, -1).astype(np.int32)
ssep = 1.15 * PPM
dark_lines = trace_layer(ddx, ddy, dlab, np.concatenate([prio, jitter_seeds(dark, 2.0, rng)]), 0.5, ssep, 0.55 * ssep, 300.0, 1.8 * PPM, maxturn_deg=45)
print('stem lines', len(dark_lines), time.time() - t0)

# ---------------------------------------------------------------- build tubes
RW_L, RH_L = 0.50, 0.21           # laid strand half-width/half-height (mm)
RW_S, RH_S = 0.52, 0.22           # split stitch
LAID_TOP = 2 * RH_L

for poly in fills + [('fine', f_) for f_ in fine_fills]:
    fine = isinstance(poly, tuple)
    if fine: poly = poly[1]
    poly = smooth_poly(poly, 2)
    lab0 = zone_lab[int(poly[len(poly) // 2, 1] + .5), int(poly[len(poly) // 2, 0] + .5)]
    mm = px2mm(poly)
    if lab0 >= 1000 and not fine:          # ---------- laid strand: one colour, long, pinched under bars
        P, s = resample(mm, 0.45)
        pp = np.c_[P[:, 0] * PPM + W / 2, -P[:, 1] * PPM + H / 2]
        sk = skein_of(np.median(sample_img(lin_rgb, pp), 0)[None])[0]
        c = sk_rgb_n[sk] * rng.uniform(0.955, 1.045) * (1 + 0.03 * smooth_noise1d(len(P), 12 / 0.45, rng))[:, None]
        Ls = s[-1]
        prof = tuck_profile(s, Ls, 0.5)
        d = laid_z(pp)
        pinch = 1 - 0.32 * np.exp(-(d / 0.75) ** 2)
        lat = smooth_noise1d(len(P), 8 / 0.45, rng) * 0.05
        tg = tangents2(P); nrm = np.c_[-tg[:, 1], tg[:, 0]]
        P = P + nrm * lat[:, None]
        z = RH_L * pinch * prof - RH_L * 0.9 * (1 - prof)
        T.add(np.c_[P, z], RW_L * (0.7 + 0.3 * prof) * rng.uniform(0.9, 1.1), RH_L * pinch * (0.6 + 0.4 * prof), np.clip(c, 0, 1), MAT_WOOL, 1, 0.78, 6, 1)
    else:                     # ---------- split stitch (needle painting): stitches 2-5.5 mm, colour per stitch
        P, s = resample(mm, 0.1)
        tot = s[-1]
        pos = -rng.uniform(0, 2.0)
        coh = sample_img(fcoh[..., None], np.c_[P[:, 0] * PPM + W / 2, -P[:, 1] * PPM + H / 2])[:, 0]
        while pos < tot - 0.4:
            i0 = max(0, int(pos / 0.1)) if pos > 0 else 0
            ch_ = coh[min(i0, len(coh) - 1)]
            Lk = rng.uniform(3.0, 5.0) if ch_ < 0.25 else (rng.uniform(4.5, 8.0) if ch_ < 0.45 else rng.uniform(7.0, 12.0))
            if fine: Lk = rng.uniform(1.6, 3.0)
            a = max(0.0, pos); b = min(tot, pos + Lk)
            ia = int(a / 0.1); ib = min(len(P) - 1, int(b / 0.1))
            if ib - ia >= 4:
                seg = P[ia:ib + 1]
                spx = np.c_[seg[:, 0] * PPM + W / 2, -seg[:, 1] * PPM + H / 2]
                col = np.median(sample_img(blur_rgb_f if fine else blur_rgb, spx), 0)
                k = skein_of(col[None])[0]
                c = np.clip(sk_rgb_n[k] * rng.uniform(0.96, 1.04), 0, 1)
                rw_, rh_ = (0.27, 0.14) if fine else (RW_S, RH_S)
                add_stitch(T, seg, 0.0, rw_ * rng.uniform(0.9, 1.1), rh_, c, MAT_WOOL, 2, rng, twist=0.5 if fine else 0.75, arch=0.04,
                           tuck=0.7, sides=6, step=0.3, tag=2, end_depth=0.25 if a > 0 else 0.9, end_depth_b=0.25 if b < tot else 0.9)
            if b >= tot - 1e-6: break
            pos = b - (rng.uniform(0.4, 0.7) if fine else rng.uniform(0.7, 1.2))          # next stitch comes up through the previous one (split stitch)

# couching bars + tie-downs
for poly in bars:
    poly = smooth_poly(poly, 3)
    mm = px2mm(poly)
    P, s = resample(mm, 0.35)
    if s[-1] < 2.0: continue
    lab0 = zone_lab[int(poly[len(poly) // 2, 1] + .5), int(poly[len(poly) // 2, 0] + .5)]
    zm = zone_lab == lab0
    sk = skein_of(np.median(lin_rgb[zm], 0)[None])[0]
    base = np.clip(sk_rgb_n[sk] * rng.uniform(0.86, 0.95), 0, 1)
    # bow + angle jitter
    tg = tangents2(P); nrm = np.c_[-tg[:, 1], tg[:, 0]]
    P = P + nrm * (0.18 * smooth_noise1d(len(P), 20 / 0.35, rng))[:, None]
    # tie-down positions
    ties = []; t = rng.uniform(1.0, 3.0)
    while t < s[-1] - 0.8:
        ties.append(t); t += 4.0 * rng.uniform(0.75, 1.25)
    ties = np.array(ties)
    if len(ties):
        dt = np.min(np.abs(s[:, None] - ties[None]), 1)
    else:
        dt = np.full(len(s), 9.0)
    kink = 1 - 0.4 * np.exp(-(dt / 0.35) ** 2)
    prof = tuck_profile(s, s[-1], 0.6)
    RB = 0.21
    z = (LAID_TOP + RB * kink) * prof - 0.2 * (1 - prof)
    T.add(np.c_[P, z], 0.36 * (0.7 + 0.3 * prof), RB * kink, base, MAT_WOOL, 1, 0.78, 6, 3)
    # tie-downs: tiny stitches across the bar
    for tt in ties:
        i = int(np.argmin(np.abs(s - tt)))
        c0 = P[i]; n0 = nrm[i]; t0_ = tg[i]
        q = np.stack([c0 + n0 * u + t0_ * rng.normal(0, 0.05) for u in np.linspace(-0.75, 0.75, 9)])
        bz = np.linspace(-1, 1, 9)
        ztie = (LAID_TOP + 2 * RB * 0.6 + 0.08) * np.sqrt(np.clip(1 - bz ** 2, 0, 1)) ** 0.6 - 0.1
        T.add(np.c_[q, ztie], 0.17, 0.12, np.clip(base * 0.9, 0, 1), MAT_WOOL, 1, 0.5, 5, 4)

# gold: metal thread on a slight padding, tie-downs every ~2.6 mm (brick offset)
GR = 0.27
for poly in gold_lines:
    poly = smooth_poly(poly, 2)
    mm = px2mm(poly)
    P, s = resample(mm, 0.3)
    if s[-1] < 0.8: continue
    pp = np.c_[P[:, 0] * PPM + W / 2, -P[:, 1] * PPM + H / 2]
    pad = 0.35 * np.clip(sample_img(gdist[..., None], pp)[:, 0] / 0.8, 0, 1) ** 0.5
    prof = tuck_profile(s, s[-1], 0.35)
    ties = np.arange(rng.uniform(0.3, 2.6), s[-1] - 0.2, 2.6 * rng.uniform(0.9, 1.1))
    dt = np.min(np.abs(s[:, None] - ties[None]), 1) if len(ties) else np.full(len(s), 9.0)
    kink = 1 - 0.25 * np.exp(-(dt / 0.25) ** 2)
    z = (pad + GR * kink) * prof - 0.2 * (1 - prof)
    tarn = 0.92 + 0.08 * smooth_noise1d(len(P), 10, rng)
    c = hex2rgb('#E9BE6A')[None] * tarn[:, None]
    T.add(np.c_[P, z], GR * (0.7 + 0.3 * prof), GR * kink, c, MAT_GOLD, 3, 0.42, 6, 5)
    tg = tangents2(P); nrm = np.c_[-tg[:, 1], tg[:, 0]]
    for tt in ties:
        i = int(np.argmin(np.abs(s - tt)))
        q = np.stack([P[i] + nrm[i] * u for u in np.linspace(-0.42, 0.42, 7)])
        bz = np.linspace(-1, 1, 7)
        zt = pad[i] + (2 * GR + 0.04) * np.sqrt(np.clip(1 - bz ** 2, 0, 1)) ** 0.5 - 0.05
        T.add(np.c_[q, zt], 0.08, 0.07, hex2rgb('#7A3B2C'), MAT_TIE, 3, 0.3, 4, 6)

# stem stitch on dark lines (outlines, ermine tails, features)
for poly in dark_lines:
    poly = smooth_poly(poly, 2)
    mm = px2mm(poly)
    mid = poly[len(poly) // 2]
    col = np.median(sample_img(lin_rgb, poly), 0)
    k = skein_of(col[None])[0]
    c = sk_rgb_n[k]
    thick = float(np.median(sample_img(ddist[..., None], poly)[:, 0])) / PPM * 2      # mm line width in the source
    if FINE[int(mid[1] + .5), int(mid[0] + .5)]:
        stem_stitch_line(T, mm, 0.0, c, MAT_WOOL, 4, rng, L=1.5, w=0.6, rh=0.15, tag=7)
    elif thick < 0.9:
        stem_stitch_line(T, mm, 0.0, c, MAT_WOOL, 4, rng, L=2.0, w=0.8, rh=0.2, tag=7)
    else:
        Ls = 2.4 if (np.linalg.norm(np.diff(mm, axis=0), axis=1).sum() < 6) else 3.2
        stem_stitch_line(T, mm, 0.0, c, MAT_WOOL, 4, rng, L=Ls, w=1.2, rh=0.27, tag=7)

nv_main = T.nverts()
# ---------------------------------------------------------------- fuzz: flyaway fibres from wool tubes
F = Tubes()
nf = 0
for P, RW, RH, C, m in zip(T.P, T.RW, T.RH, T.C, T.meta):
    if m[0] != MAT_WOOL or len(P) < 4: continue
    Lp = np.linalg.norm(np.diff(P[:, :2], axis=0), axis=1).sum()
    k = rng.poisson(0.35 * Lp)
    for _ in range(k):
        i = rng.integers(1, len(P) - 1)
        t = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]; t[2] = 0; t /= (np.linalg.norm(t) + 1e-9)
        side = np.array([-t[1], t[0], 0]) * rng.choice([-1, 1])
        p0 = P[i] + side * RW[i] * 0.8 + np.array([0, 0, RH[i] * 0.5])
        ang = rng.normal(0, 0.6)
        d = t * math.cos(ang) + side * math.sin(ang) * 0.6
        d[2] = rng.uniform(0.05, 0.45)
        d /= np.linalg.norm(d)
        Lf = rng.uniform(0.5, 2.2); nseg = 5
        pts = [p0]
        for j in range(nseg):
            d = d + rng.normal(0, 0.35, 3) * np.array([1, 1, 0.5]); d[2] -= 0.08; d /= np.linalg.norm(d)
            pts.append(pts[-1] + d * Lf / nseg)
        pts = np.array(pts); pts[:, 2] = np.maximum(pts[:, 2], 0.02)
        F.add(pts, 0.03, 0.03, np.clip(C[i] * 1.15 + 0.03, 0, 1), MAT_FIBRE, 9, 0.2, 3, 8)
        nf += 1
T.extend(F)
print('fibres', nf, 'verts main', nv_main, 'total', T.nverts(), 'tubes', len(T.P), time.time() - t0)
T.save(os.path.join(W_, os.environ.get('M1_OUT', 'm1_tubes.npz')))
json.dump({'w_mm': W / PPM, 'h_mm': H / PPM}, open(os.path.join(W_, 'm1_info.json'), 'w'))
# underdrawing (thin brown ink following the source's line work) where stitching has not reached; fades toward the crop edge
ud = (bh > 14).astype(np.float32) * OUTSIDE
fade = np.clip(d_edge / np.maximum(margin, 1e-3), 0, 1) ** 1.5
ud = ud * fade * (0.6 + 0.4 * cv2.resize(rng.random((40, 40)).astype(np.float32), (W, H)))
np.save(os.path.join(W_, 'm1_underdrawing.npy'), ud.astype(np.float32))

# ---------------------------------------------------------------- 2D preview (draw tubes as lines at 10 px/mm)
S = 10
prev = np.full((int(H / PPM * S), int(W / PPM * S), 3), (152, 190, 212), np.uint8)
order = np.argsort([p[:, 2].mean() for p in T.P])
for i in order:
    P = T.P[i]; m = T.meta[i]
    if m[0] == MAT_FIBRE: continue
    q = np.c_[(P[:, 0] + W / PPM / 2) * S, (-P[:, 1] + H / PPM / 2) * S]
    c = (T.C[i].mean(0)[::-1] * 255).astype(int).tolist()
    th = max(1, int(round(T.RW[i].mean() * 2 * S * 0.8)))
    cv2.polylines(prev, [np.round(q * 4).astype(np.int32)], False, c, th, cv2.LINE_AA, shift=2)
cv2.imwrite(os.path.join(W_, 'm1_preview.png'), prev)
seg = np.zeros((H, W, 3), np.uint8)
seg[bg] = (150, 190, 210); seg[dark] = (40, 30, 30); seg[gold] = (40, 170, 230); seg[laid_mask] = (200, 80, 160); seg[split_mask] = (90, 160, 90)
cv2.imwrite(os.path.join(W_, 'm1_seg.png'), np.concatenate([src, seg], 1))
print('done', time.time() - t0)
if os.environ.get('DUMP_SKEINS'):
    for k in range(len(sk_rgb)):
        a = (sk_rgb[k] * 255).astype(int); b = (sk_rgb_n[k] * 255).astype(int)
        print('skein', k, a, '->', b, names[sk_pal[k]])
