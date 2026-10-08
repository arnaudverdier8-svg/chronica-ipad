"""M2: the game's knight figure card (idle) re-stitched as a padded heraldic embroidery on linen.
Uses the card's albedo (colours), normal map (satin direction + part relief) and mask (R livery, G shield, A outline cord).
Outputs maps/knight_* (the separable figure patch, RGBA) and maps/ghost_* (the linen it leaves behind:
protected unfaded linen, the designer's underdrawing, needle holes) + tether anchor points for the rise.
"""
import sys, os, time, math, json, numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emb
from scipy import ndimage
T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SP = os.path.abspath(os.path.join(ROOT, '../../..'))
A = os.path.join(SP, 'aaa/assets/tex/figures')
OUT = os.path.join(ROOT, os.environ.get('MAPSDIR', 'maps'))
cfg = json.load(open(os.path.join(ROOT, 'scene_layout.json')))
PX = cfg['px']; kc = cfg['knight']
alb_s = cv2.imread(os.path.join(A, 'knight_idle_albedo.png'), cv2.IMREAD_UNCHANGED)          # BGRA 608x640
nrm_s = cv2.imread(os.path.join(A, 'knight_idle_normal.png'), cv2.IMREAD_UNCHANGED)
msk_s = cv2.imread(os.path.join(A, 'knight_idle_mask.png'), cv2.IMREAD_UNCHANGED)
sh0, sw0 = alb_s.shape[:2]
msk_s = np.dstack([cv2.resize(msk_s[..., c], (sw0, sh0), interpolation=cv2.INTER_LINEAR) for c in range(4)])   # per-channel (never PIL RGBA)
rgb = alb_s[..., 2::-1].astype(np.float32) / 255; alpha_s = alb_s[..., 3].astype(np.float32) / 255
mR, mG, mA = msk_s[..., 2] / 255.0, msk_s[..., 1] / 255.0, msk_s[..., 3] / 255.0       # BGRA -> R,G,A
nx_s = nrm_s[..., 2].astype(np.float32) / 127.5 - 1; ny_s = nrm_s[..., 1].astype(np.float32) / 127.5 - 1
SPMM = sh0 / kc['card_mm_h']                       # source px per mm
M = kc['margin_mm']
cwmm, chmm = sw0 / SPMM, sh0 / SPMM
W, H = int(round((cwmm + 2 * M) * PX)), int(round((chmm + 2 * M) * PX))
ox = oy = int(round(M * PX)); cw, ch = int(round(cwmm * PX)), int(round(chmm * PX))
print('knight map', W, H, round(W / PX, 1), 'x', round(H / PX, 1), 'mm', flush=True)
def up(a, interp=cv2.INTER_CUBIC):
    r = cv2.resize(a, (cw, ch), interpolation=interp)
    out = np.zeros((H, W) + r.shape[2:], r.dtype); out[oy:oy + ch, ox:ox + cw] = r
    return out

lab_s = emb.lin_to_oklab(emb.srgb_to_lin(rgb))
Ls, As, Bs = lab_s[..., 0], lab_s[..., 1], lab_s[..., 2]
Cs = np.hypot(As, Bs); hs = (np.degrees(np.arctan2(Bs, As)) + 360) % 360
fig = alpha_s > 0.5
# ---------------------------------------------------------------- stitch plan from the masks + colour
NONE, CORD, SHIELD, LIVERY, METAL, STEEL, IVORY, BROWN, DARK, WOOD = range(10)
st = np.full((sh0, sw0), NONE, np.int16)
gold = (hs > 55) & (hs < 100) & (Cs > 0.07) & (Ls > 0.5)
st[fig & (Cs < 0.035) & (Ls >= 0.30)] = STEEL
st[fig & (Cs < 0.035) & (Ls >= 0.80)] = IVORY
st[fig & (Cs >= 0.035)] = BROWN
st[fig & (Ls < 0.30)] = DARK
st[fig & gold] = METAL
st[fig & (mR > 0.5)] = LIVERY
st[fig & (mG > 0.5)] = SHIELD
# lance shaft: thin warm-brown vertical strip -> wood (laid along its length)
st[fig & (st == BROWN) & (np.arange(sw0)[None, :] > 200) & (np.arange(sw0)[None, :] < 240) & (np.arange(sh0)[:, None] < 520) & (Ls > 0.45)] = WOOD
cord = fig & (mA > 0.45)
def clean(lbl, n, s):
    best = np.zeros(lbl.shape, np.int16); bv = None
    for k in range(n):
        v = cv2.GaussianBlur((lbl == k).astype(np.float32), (0, 0), s)
        if bv is None: bv = v
        else: sel = v > bv; best[sel] = k; bv = np.where(sel, v, bv)
    return best
st = clean(st, 10, 0.8)
st[~fig] = NONE
# ---------------------------------------------------------------- direction field: the card's satin strands (normal-map ridges + albedo)
c2, s2, coh = emb.structure_dir([nx_s * 1.5, ny_s * 1.5, Ls], 0.7, 2.2)
w = np.clip(coh, 0.05, 1)
C2 = up(c2 * w); S2 = up(s2 * w); Wc = up(w)
ST = up(st.astype(np.float32), cv2.INTER_NEAREST).astype(np.int16)
FIG = up(alpha_s) > 0.5
ST = clean(ST, 10, 0.4 * PX); ST[~FIG] = NONE
hole = FIG & (ST == NONE)
if hole.any():
    _, (iy_, ix_) = ndimage.distance_transform_edt(~(FIG & (ST != NONE)), return_indices=True)
    ST = np.where(hole, ST[iy_, ix_], ST)
LAB = up(lab_s)
CORD = up(cord.astype(np.float32), cv2.INTER_LINEAR) > 0.5
def field(sig):
    c, s, _ = emb.smooth_dir(C2, S2, Wc + 1e-3, sig * PX); return emb.dir_vec(c, s)
DXn, DYn = field(1.2); DXl, DYl = field(4.0)
print('setup', round(time.time() - T0, 1), flush=True)

# ---------------------------------------------------------------- relief: padded parts (distance pillow per part) + card normal detail
pad = np.zeros((H, W), np.float32)
for tp in (SHIELD, LIVERY, METAL, STEEL, IVORY, BROWN, DARK, WOOD):
    m = (ST == tp).astype(np.uint8)
    if not m.any(): continue
    d = cv2.distanceTransform(m, cv2.DIST_L2, 5) / PX
    pad = np.maximum(pad, (0.85 if tp != SHIELD else 1.05) * (1 - np.exp(-d / 1.4)))
# card normal map -> height detail (Frankot-Chellappa), high-passed
gxs, gys = -nx_s / np.maximum(0.2, np.sqrt(np.clip(1 - nx_s ** 2 - ny_s ** 2, 0.04, 1))), ny_s / np.maximum(0.2, np.sqrt(np.clip(1 - nx_s ** 2 - ny_s ** 2, 0.04, 1)))
hfc = emb.poisson_from_grad(gxs * fig, gys * fig)
hfc = hfc - cv2.GaussianBlur(hfc, (0, 0), 6)
hfc = hfc / (np.percentile(np.abs(hfc[fig]), 95) + 1e-6)
pad += 0.25 * np.clip(up(hfc.astype(np.float32)), -1.5, 1.5) * (pad > 0.05)
pad = np.clip(pad, 0, None)

# ---------------------------------------------------------------- canvas: transparent (patch) on an empty ground; linen only for the ghost
cv = emb.Canvas(H, W, PX)
cv.alb[:] = 0; cv.h[:] = -1.0       # nothing yet; kind==0 means empty
def stitch_mean_colour(sid, on, sl, palette, lj=0.03):
    out = np.zeros(on.shape + (3,), np.float32)
    if not on.any(): return out
    ids = sid[on]; u, inv = np.unique(ids, return_inverse=True)
    lab = LAB[sl][on]; cnt = np.bincount(inv).astype(np.float32)
    mean = np.stack([np.bincount(inv, lab[:, c]) / cnt for c in range(3)], -1)
    d = ((mean[:, None, :] - palette[None]) * np.array([1.0, 1.6, 1.6])) ** 2
    pick = palette[np.argmin(d.sum(-1), 1)].copy()
    pick[:, 0] *= 1 + lj * (emb.hash1(u, 17) - 0.5) * 2
    out[on] = np.clip(emb.oklab_to_lin(pick)[inv], 0, 1)
    return out
def pal_from(mask, n, roles, pull, cmax):
    Z = lab_s[mask].reshape(-1, 3).astype(np.float32)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 1e-4)
    _, _, cen = cv2.kmeans(Z * np.array([1, 2, 2], np.float32), n, None, crit, 2, cv2.KMEANS_PP_CENTERS)
    cen = cen / np.array([1, 2, 2], np.float32)
    R = np.array([emb.lin_to_oklab(emb.hex_lin(h)) for h in roles])
    for i in range(n):
        r = R[np.argmin(((R[:, 1:] - cen[i, 1:]) ** 2).sum(1) + 0.3 * (R[:, 0] - cen[i, 0]) ** 2)]
        cen[i, 1:] = cen[i, 1:] * (1 - pull) + r[1:] * pull
    C = np.hypot(cen[:, 1], cen[:, 2]); s = np.minimum(1, cmax / (C + 1e-6)); cen[:, 1:] *= s[:, None]
    return cen.astype(np.float32)
P_STEEL = pal_from(st == STEEL, 5, ['#B9BCC2', '#6D717A', '#4F6F8A'], 0.5, 0.025)
P_IVORY = pal_from(st == IVORY, 3, ['#E6D7B6', '#D4BE98'], 0.6, 0.03)
P_BROWN = pal_from(st == BROWN, 6, ['#7A3B2C', '#B65E43', '#6E3326', '#C3963F'], 0.4, 0.10)
P_DARK = np.array([emb.lin_to_oklab(emb.hex_lin(h)) for h in ['#22232F', '#2B170D', '#3B2219']], np.float32)
P_WOOD = np.array([emb.lin_to_oklab(emb.hex_lin(h)) for h in ['#97591A', '#7A3B2C', '#C3963F']], np.float32)
# livery: crimson (Legion) restrained to the heraldic crimson ramp, keeping the card's light/shade
liv_L = lab_s[..., 0][st == LIVERY]
P_LIV = np.array([emb.lin_to_oklab(emb.hex_lin(h)) for h in ['#3E0D0C', '#5A1311', '#741A16', '#8A2019', '#9A2C22']], np.float32)
MAT_SATIN = (0.62, 0.0, 0.5, 0.42)
gold_lin = emb.hex_lin('#E9BE6A'); tie_col = emb.hex_lin('#6E3326')
rid = 0
for tp in (WOOD, BROWN, STEEL, IVORY, DARK, LIVERY, SHIELD, METAL):
    m = ST == tp
    if not m.any(): continue
    n, cc, stats, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 4)
    for c in range(1, n):
        if stats[c, cv2.CC_STAT_AREA] < (0.25 * PX) ** 2: continue
        rid += 1; rm = cc == c
        DX, DY = (DXl, DYl) if tp in (WOOD, METAL, SHIELD) else (DXn, DYn)
        if tp == SHIELD:
            DX = np.full((H, W), 0.0, np.float32); DY = np.full((H, W), 1.0, np.float32)   # vertical satin field
        PHI, PSI, DXo, DYo, bb = emb.phase_fields(DX, DY, rm, PX)
        reg = dict(mask=rm, bbox=bb, id=rid)
        if tp == METAL:
            emb.fill_metal_couched(cv, reg, PHI, PSI, DXo, DYo, gold_lin, tie_col, p=0.5, hgt=0.6, seed=rid, order_base=0.8, tarnish=0.15, base=pad * 0.7)
            continue
        if tp == WOOD:
            emb.fill_laid(cv, reg, PHI, PSI, DXo, DYo, lambda sid, on, sl: stitch_mean_colour(sid, on, sl, P_WOOD),
                          p=0.7, hgt=0.5, bar_s=3.5, seed=rid * 3, order_base=0.2)
            continue
        pal = {BROWN: P_BROWN, STEEL: P_STEEL, IVORY: P_IVORY, DARK: P_DARK, LIVERY: P_LIV, SHIELD: P_LIV}[tp]
        L_ = {BROWN: 4.5, STEEL: 3.2, IVORY: 5.0, DARK: 2.5, LIVERY: 6.0, SHIELD: 60}[tp]
        mat = emb.MAT_WOOL if tp in (BROWN, DARK) else MAT_SATIN
        emb.fill_needle(cv, reg, PHI, PSI, DXo, DYo, lambda sid, on, sl, pal=pal: stitch_mean_colour(sid, on, sl, pal),
                        p=0.52, L=L_, Ljit=0.45, hgt=0.42, seed=rid * 7, order_base=0.3, pad=pad, mat=mat, kind=1,
                        stagger=tp != SHIELD)
print('fills', rid, round(time.time() - T0, 1), flush=True)
# ---------------------------------------------------------------- shield charge: a couched-gold cross over the crimson satin
ys, xs = np.nonzero(ST == SHIELD)
if len(ys):
    cx, cy = xs.mean(), ys.mean() - 0.04 * (ys.max() - ys.min())
    sw_, shh = (xs.max() - xs.min()), (ys.max() - ys.min())
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    arm = 0.11 * sw_
    cross = ((np.abs(xx - cx) < arm) & (np.abs(yy - cy) < 0.36 * shh)) | ((np.abs(yy - cy + 0.08 * shh) < arm) & (np.abs(xx - cx) < 0.36 * sw_))
    cross &= cv2.erode((ST == SHIELD).astype(np.uint8), np.ones((int(1.2 * PX), int(1.2 * PX)), np.uint8)) > 0
    rid += 1
    # threads along each arm: vertical arm vertical, horizontal arm horizontal
    vert = (np.abs(xx - cx) < arm)
    DX = np.where(vert, 0.0, 1.0).astype(np.float32); DY = np.where(vert, 1.0, 0.0).astype(np.float32)
    PHI, PSI, DXo, DYo, bb = emb.phase_fields(DX, DY, cross, PX)
    emb.fill_metal_couched(cv, dict(mask=cross, bbox=bb, id=rid), PHI, PSI, DXo, DYo, gold_lin, tie_col, p=0.48, hgt=0.6, seed=rid, order_base=0.85, tarnish=0.1, base=pad + 0.45)
# ---------------------------------------------------------------- outline: couched twisted cord (game idiom) on the card's outline band
skel = emb.thin(CORD)
n3, cc3, st3, _ = cv2.connectedComponentsWithStats(skel.astype(np.uint8), 8)
k3 = np.zeros(n3, bool); k3[1:] = st3[1:, cv2.CC_STAT_AREA] >= 2 * PX; skel = k3[cc3]
tx, ty = emb.line_tangents(cv2.GaussianBlur(CORD.astype(np.float32), (0, 0), 1.2), PX, 0.6)
cord_cols = [emb.hex_lin(h) for h in ['#4A2A17', '#5A3420', '#3E2214']]
padb = cv2.GaussianBlur(pad, (0, 0), 0.6 * PX)
emb.fill_cord(cv, skel, tx, ty, r=0.78, hgt=0.85, base=padb * 0.6, cols=[emb.hex_lin('#4A2A17'), emb.hex_lin('#62402A')], pitch=1.8, seed=9)
print('cord', round(time.time() - T0, 1), flush=True)
# ---------------------------------------------------------------- finish the figure patch
cov = (cv.kind > 0)
cv.h = np.where(cov, cv.h, 0.0).astype(np.float32)
emb.finish(cv, fuzz=False, cavity_k=1.2)
# fuzz: soft alpha fringe (fibres stand off the cut edge) + halo colour
covf = cov.astype(np.float32)
fr = cv2.GaussianBlur(covf, (0, 0), 0.22 * PX)
halo_col = cv2.GaussianBlur(cv.alb_final * covf[..., None], (0, 0), 0.22 * PX) / (fr[..., None] + 1e-4)
noise = 0.5 + 0.5 * emb.snoise((H, W), 0.12 * PX, 3)
alpha = np.clip(np.maximum(covf, np.clip(fr - covf, 0, 1) * 0.55 * noise * 2.0), 0, 1)
albf = np.where(cov[..., None], cv.alb_final, halo_col * 1.05)
np.save(os.path.join(OUT, 'knight_height.npy'), cv.h)
emb.save_png8(os.path.join(OUT, 'knight_albedo.png'), emb.lin_to_srgb(albf), alpha=alpha)
emb.save_png16(os.path.join(OUT, 'knight_normal.png'), emb.normal_map(cv.h, PX, sigma_hp_mm=cfg['mesh_hp_sigma_mm']) * 0.5 + 0.5)
matx = cv.mat.copy(); matx[~cov] = emb.MAT_WOOL
emb.save_png8(os.path.join(OUT, 'knight_mat.png'), matx[..., :3], alpha=matx[..., 3])
np.save(os.path.join(OUT, 'knight_cov.npy'), cov)

# ---------------------------------------------------------------- the ghost left on the ground when the figure rises
TILE = np.load(os.path.join(OUT, 'linen_tile.npz'))
gh_ = emb.tile_sample(TILE['h'], kc['x0'], kc['y0'], H, W, PX)
ga = emb.tile_sample(np.load(os.path.join(OUT, 'linen_alb_baked.npy')), kc['x0'], kc['y0'], H, W, PX)
sil = cv2.GaussianBlur(cov.astype(np.float32), (0, 0), 0.5 * PX)
# protected from light for centuries -> brighter, less yellow linen in the silhouette
prot = emb.lin_to_oklab(ga); prot[..., 0] += 0.035 * sil; prot[..., 1:] *= (1 - 0.25 * sil)[..., None]
ga2 = emb.oklab_to_lin(prot)
# underdrawing: the designer's brush outline (cord skeleton) + a few interior construction lines (part boundaries)
part_b = (cv2.morphologyEx(ST.astype(np.float32), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0) & FIG
ud = np.clip(cv2.GaussianBlur(skel.astype(np.float32), (0, 0), 0.9) * 3.0, 0, 1) * 0.55 + np.clip(cv2.GaussianBlur(part_b.astype(np.float32), (0, 0), 0.7) * 2, 0, 1) * 0.22
ud *= 0.75 + 0.25 * emb.snoise((H, W), 4 * PX, 12)
ink = emb.hex_lin('#4F5A6E')        # faded blue-grey wash
ga2 = ga2 * (1 - 0.45 * ud[..., None]) + ink * 0.45 * ud[..., None]
# needle holes along the outline (where the cord tie-downs went through), slightly opened weave
holes = emb.poisson_disk_on(skel, 2.4 * PX, 21)
hz = np.zeros((H, W), np.float32)
for (y, x) in holes:
    cv2.circle(hz, (int(x), int(y)), int(0.22 * PX), 1.0, -1, cv2.LINE_AA)
hz = cv2.GaussianBlur(hz, (0, 0), 0.08 * PX)
gh_ = gh_ - 0.35 * hz
ga2 = ga2 * (1 - 0.55 * hz[..., None])
# fine strand imprint: flattened linen where the padding pressed (tiny height loss, darker by 2%)
gh_ = gh_ - 0.05 * sil
gcv = emb.Canvas(H, W, PX); gcv.h = gh_.astype(np.float32); gcv.alb = ga2
emb.save_png8(os.path.join(OUT, 'ghost_albedo.png'), emb.lin_to_srgb(np.clip(ga2, 0, 1)))
emb.save_png16(os.path.join(OUT, 'ghost_normal.png'), emb.normal_map(gh_, PX) * 0.5 + 0.5)
# tether anchors: points along the outline (mm, patch-local), the tie-downs that hold the figure to the cloth
anc = emb.poisson_disk_on(skel, 7.0 * PX, 5)
json.dump(dict(W=W, H=H, px=PX, w_mm=W / PX, h_mm=H / PX, anchors_mm=[[float(x) / PX, float(y) / PX] for (y, x) in anc],
               centroid_mm=[float(np.nonzero(cov)[1].mean() / PX), float(np.nonzero(cov)[0].mean() / PX)]),
          open(os.path.join(OUT, 'knight_meta.json'), 'w'))
# previews
bg = emb.tile_sample(np.load(os.path.join(OUT, 'linen_alb_baked.npy')), kc['x0'], kc['y0'], H, W, PX)
hcomp = np.where(cov, cv.h + 0.1, gh_); acomp = albf * alpha[..., None] + ga2 * (1 - alpha[..., None])
mcomp = np.where(cov[..., None], cv.mat, np.array(emb.MAT_LINEN, np.float32))
Tcomp = np.where(cov[..., None], cv.T, emb.tile_sample(TILE['T'], kc['x0'], kc['y0'], H, W, PX))
pv = emb.preview(hcomp.astype(np.float32), acomp, mcomp, Tcomp, PX)
cv2.imwrite(os.path.join(ROOT, 'work', 'knight_preview.jpg'), pv[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 92])
pv2 = emb.preview(gh_.astype(np.float32), ga2, np.broadcast_to(np.array(emb.MAT_LINEN, np.float32), (H, W, 4)), emb.tile_sample(TILE['T'], kc['x0'], kc['y0'], H, W, PX), PX)
cv2.imwrite(os.path.join(ROOT, 'work', 'ghost_preview.jpg'), pv2[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 88])
print('done', round(time.time() - T0, 1), flush=True)
