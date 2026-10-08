# prep_knight.py - the game's knight figure card (idle) re-made as padded satin + couched cord + gold thread on linen.
# Outputs work/knight_tubes.npz, work/knight_backing.npz, work/knight_rig.json, work/linen_imprint.png
import sys, os, time, math, json
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from strandlib import *
AAA = os.path.abspath(os.path.join(HERE, '..', '..'))
W_ = os.path.join(HERE, 'work')
t0 = time.time()
rng = np.random.default_rng(23)
KX, KY = float(os.environ.get('KX', 70)), float(os.environ.get('KY', -4))     # placement in the cloth (mm)
LIN_W, LIN_H, LIN_R = 300, 180, 16
HEIGHT_MM = 118.0
alb = cv2.imread(os.path.join(AAA, 'assets', 'tex_tinted', 'knight_idle_red.png'), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
H, W = alb.shape[:2]
PPM = H / HEIGHT_MM
rgb = alb[..., 2::-1].copy(); A = alb[..., 3]
alb0 = cv2.imread(os.path.join(AAA, 'assets', 'tex', 'figures', 'knight_idle_albedo.png'), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
mk = cv2.imread(os.path.join(AAA, 'assets', 'tex', 'figures', 'knight_idle_mask.png'), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
mk = np.stack([cv2.resize(mk[..., c], (W, H), interpolation=cv2.INTER_LINEAR) for c in range(4)], -1)   # per channel (no premultiply)
nm = cv2.imread(os.path.join(AAA, 'assets', 'tex', 'figures', 'knight_idle_normal.png'), cv2.IMREAD_UNCHANGED).astype(np.float32) / 255
nx = nm[..., 2] * 2 - 1; ny = nm[..., 1] * 2 - 1; nz = np.maximum(nm[..., 0] * 2 - 1, 0.2)
names, pal = load_palette(os.path.join(AAA, 'style', 'palette.json'))

fig = A > 0.5
team = cv2.GaussianBlur(mk[..., 2], (0, 0), 1.0) > 0.5          # cv2 loads BGRA: R channel = team livery
lum0 = cv2.cvtColor((alb0[..., :3] * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
def _ramp(t):
    stops = [(0.0, hex2rgb('#56100E')), (0.45, hex2rgb('#A3181A')), (1.0, hex2rgb('#CC3A2C'))]
    t = np.clip(t, 0, 1)[..., None]; out = np.zeros(t.shape[:-1] + (3,), np.float32)
    for (a, ca), (b, cb) in zip(stops[:-1], stops[1:]):
        m = (t >= a) & (t <= b); u = (t - a) / (b - a)
        out = np.where(m, ca * (1 - u) + cb * u, out)
    return out
lo, hi = np.percentile(lum0[team], 5), np.percentile(lum0[team], 95)
rgb = np.where(team[..., None], _ramp((lum0 - lo) / (hi - lo + 1e-6)), rgb).astype(np.float32)
# ------------------------------------------------------------------ padding height from the game's normal map (Frankot-Chellappa)
p = -nx / nz; q = ny / nz                      # dz/dx, dz/dy (image y down, normal map is OpenGL y-up)
p *= fig; q *= fig
fy = np.fft.fftfreq(H)[:, None] * 2 * np.pi; fx = np.fft.fftfreq(W)[None, :] * 2 * np.pi
den = fx ** 2 + fy ** 2; den[0, 0] = 1
Z = np.real(np.fft.ifft2((-1j * fx * np.fft.fft2(p) - 1j * fy * np.fft.fft2(q)) / den))
Z = cv2.GaussianBlur(Z.astype(np.float32), (0, 0), 3.0)
Z -= np.percentile(Z[fig], 2)
# combine with a distance-based dome (keeps edges grounded), then scale to mm
dist = cv2.distanceTransform(fig.astype(np.uint8), cv2.DIST_L2, 5) / PPM
dome = np.clip(dist / 2.5, 0, 1) ** 0.6
pad = np.clip(Z / np.percentile(Z[fig], 98), 0, 1.2) * 0.75 + dome * 0.55
pad = cv2.GaussianBlur(pad.astype(np.float32), (0, 0), 1.5) * fig
pad_mm = pad * 1.0                              # ~1.0-1.4 mm padded relief (heraldic register)
print('pad max', float(pad_mm.max()))

# ------------------------------------------------------------------ regions
hsv = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
hue = hsv[..., 0] * 2; sat = hsv[..., 1] / 255; val = hsv[..., 2] / 255
cord = (mk[..., 3] > 0.45) & fig
gold = (hue > 30) & (hue < 58) & (sat > 0.45) & (val > 0.55) & fig & ~cord
gold = cv2.morphologyEx(gold.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)).astype(bool)
fill = fig & ~cord & ~gold
ok = srgb_to_oklab(rgb.reshape(-1, 3))
from sklearn.cluster import KMeans
km = KMeans(22, n_init=3, random_state=0).fit(ok[fill.reshape(-1)][::3])
sk_rgb = oklab_to_srgb(km.cluster_centers_.astype(np.float32))
sk_rgb_n, sk_pal = nudge_to_palette(sk_rgb, pal, amount=0.35, cmax=0.17)
sk_ok = km.cluster_centers_.astype(np.float32)
km2 = KMeans(7, n_init=3, random_state=1).fit(ok[fill.reshape(-1)][::3])
cz = km2.predict(ok).reshape(H, W)
best = np.full((H, W), -1.0, np.float32); czm = np.zeros((H, W), np.int32)
for k in range(7):
    m = cv2.blur((cz == k).astype(np.float32), (7, 7)); upd = m > best; best[upd] = m[upd]; czm[upd] = k
zone = np.where(fill, czm, -1).astype(np.int32)

rgb_blur = cv2.GaussianBlur(rgb, (0, 0), 5.0)
def skein_of(colors):
    okc = srgb_to_oklab(colors); d = ((okc[:, None] - sk_ok[None]) ** 2).sum(-1); return d.argmin(1)

gray = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
def norm_t(J):
    tr = J[0] + J[2] + 1e-6; return (J[0] / tr, J[1] / tr, J[2] / tr)
J = blend_fields([(norm_t(structure_tensor(gray, 1.0, 3.0)), 0.35), (norm_t(structure_tensor(gray, 1.5, 8.0)), 1.0), (norm_t(structure_tensor(gray, 2.0, 16.0)), 0.6)])
fdx, fdy, fcoh = tensor_dir(*J)
cm = cv2.GaussianBlur(cord.astype(np.float32), (0, 0), 1.5)
Jc = blend_fields([(norm_t(structure_tensor(cm, 1.0, 4.0)), 1.0)])
cdx, cdy, _ = tensor_dir(*Jc)

def px2mm(pp): return np.c_[(pp[:, 0] - W / 2) / PPM, -(pp[:, 1] - H / 2) / PPM]
def mm2px(P): return np.c_[P[:, 0] * PPM + W / 2, -P[:, 1] * PPM + H / 2]
def padz(P): return sample_img(pad_mm[..., None], mm2px(P))[:, 0]

T = Tubes()
MAT_WOOL, MAT_GOLD, MAT_SILK, MAT_CORD, MAT_FIBRE, MAT_TIE = 0, 1, 2, 3, 4, 5
# ------------------------------------------------------------------ satin fills
dsep = 0.6 * PPM
fills = trace_layer(fdx, fdy, zone, jitter_seeds(fill, 1.5, rng), 0.5, dsep, 0.5 * dsep, 300.0, 1.5 * PPM, maxturn_deg=50)
cov = np.zeros((H, W), np.uint8)
for f_ in fills: cv2.polylines(cov, [np.round(f_ * 4).astype(np.int32)], False, 255, int(round(0.75 * PPM)), cv2.LINE_8, shift=2)
gl = np.where((cov == 0) & fill, zone, -1).astype(np.int32)
gl = np.where(cv2.dilate((gl >= 0).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0, zone, -1).astype(np.int32)
fills += trace_layer(fdx, fdy, gl, jitter_seeds(gl >= 0, 1.0, rng), 0.5, 0.55 * PPM, 0.4 * PPM, 40.0, 1.5 * PPM, maxturn_deg=60)
print('satin strands', len(fills))
RW, RH = 0.5, 0.2
for poly in fills:
    poly = smooth_poly(poly, 2); mm = px2mm(poly)
    P, s = resample(mm, 0.1); tot = s[-1]; pos = -rng.uniform(0, 3.0)
    while pos < tot - 0.4:
        Lk = rng.uniform(6.0, 11.0)
        a = max(0.0, pos); b = min(tot, pos + Lk)
        ia = int(a / 0.1); ib = min(len(P) - 1, int(b / 0.1))
        if ib - ia >= 4:
            seg = P[ia:ib + 1]
            col = np.median(sample_img(rgb_blur, mm2px(seg)), 0)
            c = np.clip(sk_rgb_n[skein_of(col[None])[0]] * rng.uniform(0.96, 1.04), 0, 1)
            add_stitch(T, seg, padz, RW * rng.uniform(0.92, 1.08), RH, c, MAT_SILK, 2, rng, twist=0.9, arch=0.03, tuck=0.6,
                       sides=6, step=0.3, tag=2, end_depth=0.3 if a > 0 else 1.2, end_depth_b=0.3 if b < tot else 1.2)
        if b >= tot - 1e-6: break
        pos = b - rng.uniform(0.6, 1.0)

# ------------------------------------------------------------------ gold couched metal thread
GR = 0.26
glines = trace_layer(fdx, fdy, np.where(gold, 1, -1).astype(np.int32), jitter_seeds(gold, 1.2, rng), 0.4, 0.55 * PPM, 0.27 * PPM, 200.0, 0.7 * PPM, maxturn_deg=45)
for poly in glines:
    poly = smooth_poly(poly, 2); P, s = resample(px2mm(poly), 0.3)
    if s[-1] < 0.7: continue
    prof = tuck_profile(s, s[-1], 0.35)
    ties = np.arange(rng.uniform(0.3, 2.4), s[-1] - 0.2, 2.4 * rng.uniform(0.9, 1.1))
    dt = np.min(np.abs(s[:, None] - ties[None]), 1) if len(ties) else np.full(len(s), 9.0)
    kink = 1 - 0.25 * np.exp(-(dt / 0.25) ** 2)
    bz = padz(P)
    z = bz + (GR * kink) * prof - 0.25 * (1 - prof)
    T.add(np.c_[P, z], GR * (0.7 + 0.3 * prof), GR * kink, hex2rgb('#E9BE6A')[None] * (0.93 + 0.07 * smooth_noise1d(len(P), 10, rng))[:, None], MAT_GOLD, 3, 0.42, 6, 5)
    tg = tangents2(P); nrm = np.c_[-tg[:, 1], tg[:, 0]]
    for tt in ties:
        i = int(np.argmin(np.abs(s - tt)))
        q = np.stack([P[i] + nrm[i] * u for u in np.linspace(-0.4, 0.4, 7)])
        zz = bz[i] + (2 * GR + 0.04) * np.sqrt(np.clip(1 - np.linspace(-1, 1, 7) ** 2, 0, 1)) ** 0.5 - 0.05
        T.add(np.c_[q, zz], 0.08, 0.07, hex2rgb('#7A3B2C'), MAT_TIE, 3, 0.3, 4, 6)

# ------------------------------------------------------------------ couched outline cord (2-ply, 1.3 mm) with tie-downs
cl = trace_layer(cdx, cdy, np.where(cord, 1, -1).astype(np.int32),
                 np.concatenate([np.stack(np.nonzero(cv2.distanceTransform(cord.astype(np.uint8), cv2.DIST_L2, 5) > 2.6)[::-1], 1).astype(np.float32)[::7],
                                 jitter_seeds(cord, 2.0, rng)]), 0.5, 1.25 * PPM, 0.6 * PPM, 600.0, 1.2 * PPM, maxturn_deg=60)
cord_col = np.array([0.20, 0.12, 0.07], np.float32)
cord_polys = []
for poly in cl:
    poly = smooth_poly(poly, 4); P, s = resample(px2mm(poly), 0.25)
    if s[-1] < 1.2: continue
    cord_polys.append(P)
    prof = tuck_profile(s, s[-1], 0.6)
    ties = np.arange(rng.uniform(0.5, 3.0), s[-1] - 0.3, 3.0 * rng.uniform(0.85, 1.15))
    dt = np.min(np.abs(s[:, None] - ties[None]), 1) if len(ties) else np.full(len(s), 9.0)
    kink = 1 - 0.18 * np.exp(-(dt / 0.3) ** 2)
    bz = padz(P) * 0.6
    RC = 0.55
    z = bz + RC * kink * prof - 0.3 * (1 - prof)
    col = cord_col[None] * (1 + 0.06 * smooth_noise1d(len(P), 20, rng))[:, None]
    T.add(np.c_[P, z], 0.66 * (0.75 + 0.25 * prof), RC * kink, col, MAT_CORD, 4, 1.1, 8, 7)
    tg = tangents2(P); nrm = np.c_[-tg[:, 1], tg[:, 0]]
    for tt in ties:
        i = int(np.argmin(np.abs(s - tt)))
        q = np.stack([P[i] + nrm[i] * u + tg[i] * u * 0.25 for u in np.linspace(-0.9, 0.9, 9)])
        zz = bz[i] + (2 * RC + 0.05) * np.sqrt(np.clip(1 - np.linspace(-1, 1, 9) ** 2, 0, 1)) ** 0.6 - 0.1
        T.add(np.c_[q, zz], 0.1, 0.08, np.array([0.12, 0.07, 0.05]), MAT_TIE, 4, 0.3, 4, 6)
print('cord lines', len(cord_polys))

# ------------------------------------------------------------------ fuzz
for P, RW_, RH_, C, m in list(zip(T.P, T.RW, T.RH, T.C, T.meta)):
    if m[0] not in (MAT_WOOL, MAT_SILK, MAT_CORD) or len(P) < 4: continue
    Lp = np.linalg.norm(np.diff(P[:, :2], axis=0), axis=1).sum()
    for _ in range(rng.poisson((0.18 if m[0] == MAT_SILK else 0.35) * Lp)):
        i = rng.integers(1, len(P) - 1)
        t = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]; t[2] = 0; t /= (np.linalg.norm(t) + 1e-9)
        side = np.array([-t[1], t[0], 0]) * rng.choice([-1, 1])
        p0 = P[i] + side * RW_[i] * 0.8 + np.array([0, 0, RH_[i] * 0.5])
        ang = rng.normal(0, 0.6); d = t * math.cos(ang) + side * math.sin(ang) * 0.6; d[2] = rng.uniform(0.05, 0.45); d /= np.linalg.norm(d)
        Lf = rng.uniform(0.5, 2.0); pts = [p0]
        for j in range(5):
            d = d + rng.normal(0, 0.35, 3) * np.array([1, 1, 0.5]); d[2] -= 0.08; d /= np.linalg.norm(d); pts.append(pts[-1] + d * Lf / 5)
        pts = np.array(pts); pts[:, 2] = np.maximum(pts[:, 2], P[i, 2] - RH_[i])
        T.add(pts, 0.03, 0.03, np.clip(C[i] * 1.15 + 0.03, 0, 1), MAT_FIBRE, 9, 0.2, 3, 8)
print('knight verts', T.nverts(), 'tubes', len(T.P), round(time.time() - t0, 1))
T.save(os.path.join(W_, 'knight_tubes.npz'))

# ------------------------------------------------------------------ backing patch (cut linen that lifts with the figure)
figd = cv2.dilate(fig.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
cnts, _ = cv2.findContours(figd, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cnt = max(cnts, key=cv2.contourArea)[:, 0, :].astype(np.float32)
cnt = cv2.approxPolyDP(cnt, 0.8, True)[:, 0, :].astype(np.float32)
poly = px2mm(cnt)
# triangulate (ear clipping via cv2 subdiv is unreliable for concave; use a simple fan-free method: constrained by mask)
import itertools
def ear_clip(P):
    idx = list(range(len(P))); tris = []
    def area(a, b, c): return (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
    sgn = 1 if sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P))) > 0 else -1
    guard = 0
    while len(idx) > 3 and guard < 100000:
        guard += 1; found = False
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = P[i0], P[i1], P[i2]
            if sgn * area(a, b, c) <= 1e-9: continue
            ok_ = True
            for j in idx:
                if j in (i0, i1, i2): continue
                pp = P[j]
                if sgn * area(a, b, pp) >= 0 and sgn * area(b, c, pp) >= 0 and sgn * area(c, a, pp) >= 0: ok_ = False; break
            if ok_:
                tris.append((i0, i1, i2)); idx.pop(k); found = True; break
        if not found: break
    if len(idx) == 3: tris.append(tuple(idx))
    return tris
tris = ear_clip(poly.tolist())
n = len(poly)
Vtop = np.c_[poly + [KX, KY], np.full(n, 0.03)]; Vbot = np.c_[poly + [KX, KY], np.full(n, -0.3)]
V = np.concatenate([Vtop, Vbot])
F = [list(t) for t in tris] + [[t[2] + n, t[1] + n, t[0] + n] for t in tris] + [[i, (i + 1) % n, (i + 1) % n + n, i + n] for i in range(n)]
np.savez(os.path.join(W_, 'knight_backing.npz'), V=V.astype(np.float32), F=np.array([f + [-1] * (4 - len(f)) for f in F]), tris=len(tris))
print('backing poly', n, 'tris', len(tris))

# ------------------------------------------------------------------ rig: pivot, tether anchors/holes
ys, xs = np.nonzero(fig)
ymin_mm = -(ys.max() - H / 2) / PPM
pivot = [KX, KY + ymin_mm, 0.0]
anc = []; holes = []; cols = []
allc = np.concatenate(cord_polys)
lowc = allc[allc[:, 1] < ymin_mm + 0.55 * HEIGHT_MM]
sel = lowc[rng.choice(len(lowc), size=min(34, len(lowc)), replace=False)]
for pnt in sel:
    w_ = np.array([pnt[0] + KX, pnt[1] + KY, 0.35])
    anc.append((w_ - np.array(pivot)).tolist())
    h_ = w_.copy(); h_[2] = 0.0; h_[:2] += rng.normal(0, 0.3, 2); holes.append(h_.tolist())
    cols.append(cord_col.tolist() if rng.random() < 0.7 else [0.62, 0.15, 0.10])
rig = dict(pivot=pivot, anchor_local=anc, holes=holes, colors=cols, snap_at=sorted(rng.uniform(0.15, 0.95, len(anc)).tolist()),
           kx=KX, ky=KY, w_mm=W / PPM, h_mm=H / PPM)
json.dump(rig, open(os.path.join(W_, 'knight_rig.json'), 'w'))

# ------------------------------------------------------------------ imprint on the linen (pressed area, needle holes, underdrawing)
R = LIN_R
imp = np.zeros((LIN_H * R, LIN_W * R), np.float32)
def w2px(P): return np.c_[(P[:, 0] + KX + LIN_W / 2) * R, (LIN_H / 2 - (P[:, 1] + KY)) * R]
fm = np.zeros_like(imp, np.uint8)
cv2.fillPoly(fm, [np.round(w2px(px2mm(cnt)) * 4).astype(np.int32)], 1, cv2.LINE_8, shift=2)
imp += cv2.GaussianBlur(fm.astype(np.float32), (0, 0), 3) * 0.10
und = np.zeros_like(imp)
for P in cord_polys:
    q = w2px(P) + rng.normal(0, 1.2, (1, 2))
    cv2.polylines(und, [np.round(q * 4).astype(np.int32)], False, 1.0, 2, cv2.LINE_AA, shift=2)
imp += cv2.GaussianBlur(und, (0, 0), 0.8) * 0.35
for P in cord_polys:
    P2, s = resample(P, 1.4)
    for pp in w2px(P2[::1]):
        cv2.circle(imp, (int(pp[0] + rng.normal(0, 3)), int(pp[1] + rng.normal(0, 3))), int(rng.uniform(1.5, 3)), 0.75, -1, cv2.LINE_AA)
cv2.imwrite(os.path.join(W_, 'linen_imprint.png'), np.clip(imp * 255, 0, 255).astype(np.uint8))
print('done', round(time.time() - t0, 1))
