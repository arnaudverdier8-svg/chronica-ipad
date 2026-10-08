"""Finish the chronicle strip for S18: Act-III ageing + dying edges, folds / creases, burn-through at the war|ruin join,
scorched ruin margins, mends, and the frayed cloth boundary (stair-stepped weft runs).  Strip-local coordinates."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from s18common import *
from chron.ageing import apply_age
from chron.color import hex_lin, pal, lin2oklab, oklab2lin
from chron.util import vnoise, sstep
from chron.config import LINEN, WOOL, METAL, SILK
from detail import lic_streaks, slubs, quantise_lots, vn_aniso

HS = 400.0
FOLD_K = float(os.environ.get('F_FOLD', '1.3')); LIC_REL = float(os.environ.get('F_LICREL', '0.14'))
BAND = 78.0
UC = 1830.0           # world x = 0 sits at strip u = UC


def noise1d(n, scale_px, r, octs=1):
    out = np.zeros(n, np.float32); amp = 1.0; tot = 0.0
    for o in range(octs):
        g = r.standard_normal(int(n / scale_px) + 4)
        out += amp * np.interp(np.arange(n) / scale_px, np.arange(len(g)), g); tot += amp; amp *= 0.5; scale_px *= 0.5
    return out / tot


def piecewise(n, seg_px, amp, r):
    """piecewise-constant noise with random run lengths (weft runs of a fraying edge)."""
    out = np.zeros(n, np.float32); i = 0
    while i < n:
        L = int(max(2, r.uniform(*seg_px)))
        out[i:i + L] = r.normal(0, amp); i += L
    return out


def bump(uu, c, w, d):
    x = (uu - c) / w
    return d * np.exp(-np.abs(x) ** 2.2)


def fray_profile(uu, specs, r, seed_scale=1.0):
    p = np.zeros_like(uu)
    for c, w, d in specs:
        p += bump(uu, c, w, d)
    return p


# bites: (centre u, half-width mm, depth mm).  uc=1830 -> window u in [143, 3517]
# v2: three deeper bites that go THROUGH the border into the register at mid-strip (u 1020, 1575, 2335: critic 'edges bite the main register')
# and eat half of the lions at u 2060-2330 (their own red / blue strands stream off in threads.py)
TOP_BITES = [(205, 130, 38), (470, 70, 16), (760, 95, 22), (880, 45, 40), (1030, 52, 92), (1130, 60, 9), (1575, 60, 88), (1790, 50, 30),
             (2060, 62, 56), (2335, 66, 96), (2505, 62, 52), (2780, 100, 26), (3095, 58, 46), (3270, 120, 40), (3450, 90, 70), (3640, 100, 52)]
BOT_BITES = [(150, 150, 52), (430, 90, 20), (690, 60, 10), (1010, 80, 11), (1250, 48, 40), (1700, 70, 8), (2140, 90, 16), (2560, 70, 13),
             (2930, 140, 32), (3200, 100, 28), (3520, 110, 58), (3760, 120, 44)]


def finish(S, PX, seed=5):
    r = np.random.default_rng(seed)
    H, W = S['h'].shape
    uu = (np.arange(W) + 0.5) / PX
    vv = (np.arange(H) + 0.5) / PX
    info = {}
    # ---------------------------------------------------------------- boundary (stair-stepped weft runs)
    bt = fray_profile(uu, TOP_BITES, r) * 1.0
    bb = fray_profile(uu, BOT_BITES, r) * 1.0
    pitch = 0.53
    jt = piecewise(W, (6 * PX, 38 * PX), 1.1, r) * (0.35 + 0.65 * np.clip(bt / 12.0, 0, 1)) + 1.0 * noise1d(W, 5 * PX, r, 2)
    jb = piecewise(W, (6 * PX, 38 * PX), 1.1, r) * (0.35 + 0.65 * np.clip(bb / 12.0, 0, 1)) + 1.0 * noise1d(W, 5 * PX, r, 2)
    # v2: big bites are ragged, not smooth cookie-cutter scallops: run-length steps and fibre-scale wander scaled with the bite depth
    rag_t = piecewise(W, (4 * PX, 28 * PX), 1.0, r) * 0.24 * bt + noise1d(W, 10 * PX, r, 3) * 0.18 * bt + noise1d(W, 3.5 * PX, r, 1) * 0.08 * bt
    rag_b = piecewise(W, (4 * PX, 28 * PX), 1.0, r) * 0.24 * bb + noise1d(W, 10 * PX, r, 3) * 0.18 * bb + noise1d(W, 3.5 * PX, r, 1) * 0.08 * bb
    vt = np.maximum(0.0, bt + jt + rag_t + 0.6)
    vb = HS - np.maximum(0.0, bb + jb + rag_b + 0.6)
    vt = np.round(vt / pitch) * pitch
    vb = HS - np.round((HS - vb) / pitch) * pitch
    info.update(vt=vt.astype(np.float32), vb=vb.astype(np.float32), bt=bt.astype(np.float32), bb=bb.astype(np.float32))
    alpha = np.clip((vv[:, None] - vt[None, :]) * PX + 0.5, 0, 1) * np.clip((vb[None, :] - vv[:, None]) * PX + 0.5, 0, 1)
    # ---------------------------------------------------------------- v2: protruding warp ends (a comb of loose, uneven yarn ends with dark gaps)
    # groups of 1-5 columns share a length; 45-90 % of the groups carry a yarn; lengths grow with the local fray activity
    def comb(edge_act, top):
        L = np.zeros(W, np.float32); x = 0
        while x < W:
            run = int(r.integers(1, 6)); a = float(edge_act[min(x, W - 1)])
            act_p = 0.30 + 0.45 * np.clip(a / 25.0, 0, 1)
            if r.random() < act_p:
                ln = float(np.clip(r.exponential(0.9 + 5.5 * np.clip(a / 40.0, 0, 1)), 0.3, 16.0))
                L[x:x + run] = ln * r.uniform(0.7, 1.25, size=len(L[x:x + run]))
            x += run
        return L
    Lt, Lb = comb(bt, True), comb(bb, False)
    yt = (vt[None, :] - vv[:, None])                 # mm above the top boundary
    yb = (vv[:, None] - vb[None, :])                 # mm below the bottom boundary
    ct = ((yt > 0) & (yt < Lt[None, :])) * np.clip(1.0 - yt / np.maximum(Lt[None, :], 0.2), 0, 1) ** 0.35
    cb = ((yb > 0) & (yb < Lb[None, :])) * np.clip(1.0 - yb / np.maximum(Lb[None, :], 0.2), 0, 1) ** 0.35
    comb_a = np.maximum(ct, cb).astype(np.float32) * 0.82
    # v2: the last ~2 mm inside the cut line is ragged (weft ends of uneven length with dark gaps between them), not a clean cut
    ed_in = np.minimum(vv[:, None] - vt[None, :], vb[None, :] - vv[:, None])
    nzE = vnoise(0.0, 0.0, H, W, PX, 1.1, seed + 97, 2)
    alpha = alpha * np.clip(np.clip(ed_in / 2.4, 0, 1) + 0.55 + 1.1 * nzE, 0, 1)
    alpha = np.maximum(alpha, comb_a)
    # ---------------------------------------------------------------- burn-through at the war | ruin join (v2: ragged edge, thick char crust)
    ub, vbn = 3151.0, 236.0
    uuu, vvv = np.meshgrid(uu, vv)
    nz = vnoise(0.0, 0.0, H, W, PX, 22.0, seed + 31, 3)
    nz2 = vnoise(0.0, 0.0, H, W, PX, 7.0, seed + 32, 2)
    nz3 = vnoise(0.0, 0.0, H, W, PX, 2.4, seed + 33, 2)
    d = np.hypot((uuu - ub) / 50.0, (vvv - vbn) / 92.0) + 0.30 * nz + 0.11 * nz2 + 0.055 * nz3
    hole = (d < 1.0).astype(np.float32)
    hole = cv2.GaussianBlur(hole, (0, 0), 0.35 * PX)
    alpha *= (1 - hole)
    info['hole'] = (ub, vbn)
    dmm = np.maximum(d - 1.0, 0) * 50.0                    # ~mm outside the hole
    crust_w = 5.5 * (0.6 + 0.8 * np.clip(0.5 + nz2 * 1.4, 0, 1))
    char = np.exp(-(dmm / crust_w) ** 1.6) * (d >= 1.0)    # black char crust (4-5 mm)
    scorch = np.exp(-(dmm / 24.0) ** 1.2) * (d >= 1.0)     # brown scorch / soot halo, much wider than v1
    # tangent along the rim (for the dry-carbon sheen) and boundary points + inward normals (blackened thread stubs, threads.py)
    ds = cv2.GaussianBlur(d.astype(np.float32), (0, 0), 1.2 * PX)
    gdx = cv2.Sobel(ds, cv2.CV_32F, 1, 0, ksize=3); gdy = cv2.Sobel(ds, cv2.CV_32F, 0, 1, ksize=3)
    gn = np.hypot(gdx, gdy) + 1e-6
    rimT = np.dstack([-gdy / gn, gdx / gn]).astype(np.float32)
    ring = (np.abs(d - 1.0) < 0.012) & (uuu > ub - 90) & (uuu < ub + 90)
    ys_, xs_ = np.nonzero(ring)
    if len(ys_) > 8:
        sel = r.choice(len(ys_), min(len(ys_), 260), replace=False)
        pts = np.stack([xs_[sel] / PX, ys_[sel] / PX, gdx[ys_[sel], xs_[sel]] / gn[ys_[sel], xs_[sel]], gdy[ys_[sel], xs_[sel]] / gn[ys_[sel], xs_[sel]]], 1)
        pts[:, 2:] *= -1.0                                  # pointing into the hole (decreasing d)
        info['hole_pts'] = pts.astype(np.float32)
    else:
        info['hole_pts'] = np.zeros((0, 4), np.float32)
    # ruin panel margins: a creeping burn from the p6 edges (its right / top / bottom), soot clouds
    p6x0, p6x1 = 3151.2, 3741.6
    in6 = (uuu >= p6x0) & (uuu <= p6x1)
    burn_n = vnoise(0.0, 0.0, H, W, PX, 38.0, seed + 41, 3)
    edge_d = np.minimum(np.minimum(vvv - BAND, HS - vvv), np.maximum(p6x1 - uuu, 0))
    creep = np.clip(1.2 - (edge_d + 22 * burn_n) / 55.0, 0, 1) * in6
    creep = np.maximum(creep, np.clip(1.0 - (uuu - p6x0) / 60.0 - 0.3 * burn_n, 0, 1) * in6 * 0.7)
    scorch = np.maximum(scorch, creep * 0.8)
    # ---------------------------------------------------------------- ageing (Act III state of an Act II-aged cloth)
    amt = np.full((H, W), 1.0, np.float32)
    S['alb'] = apply_age(S['alb'], S['mat'], amt, dict(fox=np.clip(S['fox'] * 1.7, 0, 1), tide=S['tide'], fade=S['fade']), ghost=S['ghost'],
                         linen_k=0.80, dye_k=1.55)
    # Act-III grime: large-scale mottled darkening, deeper toward both ends of the frame; v2: GREY-brown (was orange)
    gm = vnoise(0.0, 0.0, H, W, PX, 160.0, seed + 81, 3) * 1.1 + 0.5 * vnoise(0.0, 0.0, H, W, PX, 38.0, seed + 82, 2)
    gm = np.clip(0.45 + gm, 0, 1) ** 1.4
    end = np.clip((np.abs(uuu - UC) - 800.0) / 1100.0, 0, 1)
    dark = np.clip(0.07 + 0.20 * gm + 0.28 * end ** 1.2, 0, 0.6)
    tintg = np.array([0.90, 0.85, 0.76], np.float32)
    S['alb'] = S['alb'] * (1 - dark[..., None]) + S['alb'] * tintg * dark[..., None]
    lab = lin2oklab(S['alb'])
    mt = S['mat']
    ground = ((mt == 0) | (mt == 7)).astype(np.float32)
    ground = cv2.GaussianBlur(ground, (0, 0), 0.5 * PX)
    ch = (1 - 0.40 * end)[..., None]
    lab[..., 1:] *= ch
    # v2: the cloth must read OATMEAL linen, not a mustard wash: linen chroma x0.55, dyed wool x0.80 (palette narrative chroma .06-.13)
    lab[..., 1:] *= (0.80 * (1 - ground) + 0.48 * ground)[..., None]
    # dye-lot / uneven-ageing patches (linen: +-4 % L, hue +-3 deg; sharp-ish skein boundaries) + weft barre + slubs
    lot = vnoise(0.0, 0.0, H, W, PX, 55.0, seed + 83, 2)
    lot = np.floor(lot * 4.0 + 0.5) / 4.0                               # stepped: skeins / washing patches
    lot = cv2.GaussianBlur(lot, (0, 0), 1.2 * PX)
    barre = vn_aniso(H, W, PX, 70.0, 2.3, seed + 91, 2)
    sl = slubs(H, W, PX, seed + 92)
    lab[..., 0] *= (1 + 0.050 * lot * ground + 0.050 * barre * ground + 0.070 * sl * ground)
    hue = 0.05 * lot * ground
    a_, b_ = lab[..., 1].copy(), lab[..., 2].copy()
    lab[..., 1] = a_ * np.cos(hue) - b_ * np.sin(hue); lab[..., 2] = a_ * np.sin(hue) + b_ * np.cos(hue)
    # ---------------------------------------------------------------- wool: stitch-row streaks along T + discrete colour lots
    wool = np.isin(mt, (1, 2, 4, 5)).astype(np.uint8)
    lic = lic_streaks(S['T'], wool, PX, seed + 95, across_mm=1.7, along_mm=10.0)
    lab[..., 0] = quantise_lots(lab[..., 0], wool, lic, step=0.036, dither=0.80)
    lab[..., 0] *= (1 + 0.070 * lic * wool)
    lab[..., 1:] *= (1 + 0.07 * lic * wool)[..., None]
    lic2 = lic_streaks(S['T'], wool, PX, seed + 96, across_mm=2.6, along_mm=34.0)      # long-and-short irregularity: rows of a different dye lot / tension
    lab[..., 0] *= (1 + 0.065 * lic2 * wool)
    lab[..., 1:] *= (1 + 0.08 * lic2 * wool)[..., None]
    # the war field's few remaining riders: faded and desaturated (they must not look freshly stitched: S13 the figures are gone)
    rid = ((uuu >= 2551) & (uuu <= 3140) & (vvv >= 166) & (vvv <= 246) & (mt == 1)).astype(np.float32)
    rid = cv2.GaussianBlur(rid, (0, 0), 0.8 * PX)
    lab[..., 1:] *= (1 - 0.58 * rid)[..., None]
    lab[..., 0] *= (1 - 0.08 * rid) + 0.0
    # the king-shaped void is protected (fresher) linen: bring it down to the aged ground, not a pale wash
    gh = cv2.GaussianBlur(np.clip(S['ghost'], 0, 1).astype(np.float32), (0, 0), 0.8 * PX) * ((uuu >= 1960) & (uuu <= 2551)).astype(np.float32)
    lab[..., 0] *= (1 - 0.07 * gh)
    lab[..., 1:] *= (1 - 0.06 * gh)[..., None]
    S['alb'] = oklab2lin(lab)
    S['h'] += (LIC_REL * lic * wool).astype(np.float32)                    # the raking light sees the stitch rows
    S['h'] += (0.030 * (0.5 * barre + sl) * ground).astype(np.float32)   # slub / barre relief on the linen
    # dying edges: browning + fade towards both long edges and the ragged parts (tideline colour), dye fade a bit more
    ed = np.minimum(vvv - vt[None, :], vb[None, :] - vvv)            # mm inside the cloth boundary
    act = np.clip((bt[None, :] * (vvv < HS / 2) + bb[None, :] * (vvv >= HS / 2)) / 25.0, 0, 1)
    brown = np.exp(-np.maximum(ed, 0) / (14.0 + 20.0 * act)) * (0.35 + 0.55 * act) * (0.8 + 0.4 * burn_n)
    tc = hex_lin('#6E5C46'); tc = tc / tc.max()
    S['alb'] = S['alb'] * (1 - brown[..., None] * 0.55) + S['alb'] * tc * brown[..., None] * 0.55
    # scorch / soot
    soot = hex_lin('#2A2320'); brn = hex_lin('#5A3A20')
    sc = np.clip(scorch, 0, 1)[..., None]
    S['alb'] = S['alb'] * (1 - 0.55 * sc) + (S['alb'] * 0.45 * brn / brn.max()) * 0.55 * sc
    ch = np.clip(char, 0, 1)[..., None]
    crust_noise = np.clip(0.55 + 0.9 * vnoise(0.0, 0.0, H, W, PX, 3.4, seed + 34, 2), 0, 1)
    ash = hex_lin('#6A645C')
    ashm = np.clip((crust_noise - 0.90) / 0.1, 0, 1)[..., None] * 0.6            # ash-grey flecks on the crust ridges
    crust_col = soot * (0.75 + 1.0 * crust_noise[..., None]) * (1 - ashm) + ash * 0.45 * ashm
    S['alb'] = S['alb'] * (1 - ch) + crust_col * ch
    S['h'] += (1.2 * ch[..., 0] * (0.45 + 0.8 * crust_noise) + 0.15 * sc[..., 0]).astype(np.float32)     # charred crust raised, bumpy
    crust = char > 0.45
    S['mat'][crust] = SILK                                                   # dry carbon sheen at grazing angles
    S['T'][crust] = rimT[crust]
    S['cov'][crust] = 0.0
    # soot smears
    smear = np.clip(vnoise(0.0, 0.0, H, W, PX, 60.0, seed + 51, 3) * 1.4 - 0.55, 0, 1) * in6 * 0.6
    S['alb'] = S['alb'] * (1 - smear[..., None] * 0.6)
    # needle holes along the outline of the unpicked king (dark pricks, 1.3 mm) and anchors for the stray purple / gold strands (threads.py)
    reg = ((np.clip(S['ghost'], 0, 1) > 0.5) & (uuu >= 1960) & (uuu <= 2551)).astype(np.uint8)
    ncc, lbl, stt, _ = cv2.connectedComponentsWithStats(reg, connectivity=8)
    void_pts = np.zeros((0, 4), np.float32)
    if ncc > 1:
        big = 1 + int(np.argmax(stt[1:, cv2.CC_STAT_AREA]))
        vm = (lbl == big).astype(np.uint8)
        edge = cv2.morphologyEx(vm, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
        ey, ex = np.nonzero(edge)
        gsm = cv2.GaussianBlur(vm.astype(np.float32), (0, 0), 2.0 * PX)
        gx_ = cv2.Sobel(gsm, cv2.CV_32F, 1, 0, ksize=3); gy_ = cv2.Sobel(gsm, cv2.CV_32F, 0, 1, ksize=3)
        order = r.permutation(len(ey))
        taken = []
        for i in order:
            x_, y_ = ex[i], ey[i]
            if all((x_ - a) ** 2 + (y_ - b) ** 2 > (4.0 * PX) ** 2 for a, b in taken):
                taken.append((x_, y_))
        holes = np.zeros((H, W), np.float32)
        for (x_, y_) in taken:
            cv2.circle(holes, (int(x_), int(y_)), max(1, int(round(0.65 * PX))), 1.0, -1, cv2.LINE_AA)
        holes = cv2.GaussianBlur(holes, (0, 0), 0.35 * PX)
        S['alb'] *= (1 - 0.55 * np.clip(holes * 1.4, 0, 1))[..., None]
        S['h'] -= (0.18 * holes).astype(np.float32)
        sel = r.permutation(len(taken))[:26]
        vp = []
        for i in sel:
            x_, y_ = taken[i]
            nx_, ny_ = -gx_[y_, x_], -gy_[y_, x_]
            nn = math.hypot(nx_, ny_) + 1e-6
            vp.append((x_ / PX, y_ / PX, nx_ / nn, ny_ / nn))
        void_pts = np.array(vp, np.float32)
    info['void_pts'] = void_pts
    # ---------------------------------------------------------------- mends (faded, mismatched darning); v2: oatmeal / drab, ragged, coarser rows
    def mend(cu, cv, w, h, ang=0.0, pick=None):
        """a darned patch: mismatched faded thread laid in parallel runs, ragged edge, slightly raised."""
        nzm = vnoise(0.0, 0.0, H, W, PX, 5.0, seed + int(cu), 2)
        c, s_ = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        du, dv = (uuu - cu) * c + (vvv - cv) * s_, -(uuu - cu) * s_ + (vvv - cv) * c
        mask = ((np.abs(du) < w / 2 + 4.8 * nzm) & (np.abs(dv) < h / 2 + 4.8 * nzm))
        m = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 0.4 * PX)
        rows = 0.5 + 0.5 * np.sin(dv * 2 * np.pi / 2.4)                     # darning runs, 2.4 mm pitch
        brk = 0.5 + 0.5 * np.sin(du * 2 * np.pi / 9.0 + np.floor(dv / 2.4) * 2.1)   # staggered run ends
        tex = 0.78 + 0.18 * rows + 0.10 * brk
        mm_ = m[..., None] * 0.88
        S['alb'] = S['alb'] * (1 - mm_) + (pick[None, None, :] * tex[..., None]) * mm_
        S['h'] += (0.28 * m + 0.14 * rows * m).astype(np.float32)
        S['mat'][mask] = 1
        S['T'][mask] = (c, s_)
        S['cov'][mask] = 0.6
    mend(2330.0, 150.0, 30, 17, ang=-9.0, pick=hex_lin('#BDB095') * 0.78)
    mend(3010.0, 338.0, 34, 19, ang=11.0, pick=hex_lin('#9A8E78') * 0.75)
    # ---------------------------------------------------------------- folds / creases (low-frequency relief)
    fold = FOLD_K * 3.8 * vnoise(0.0, 0.0, H, W, PX, 95.0, seed + 61, 3) + 0.7 * vnoise(0.0, 0.0, H, W, PX, 30.0, seed + 62, 2)
    cre = np.zeros((H, W), np.float32)
    # v2: wrinkles of a cloth rolled for years: transverse creases AND oblique shear wrinkles, so that the raking light (from below) rakes them
    for k in range(64):
        cu = r.uniform(100, 3900)
        if r.random() < 0.45:
            a = np.deg2rad(r.normal(0, 9))
        else:
            a = np.deg2rad(r.uniform(28, 78) * (1 if r.random() < 0.5 else -1))
        w = r.uniform(4.5, 11); dep = r.uniform(0.45, 1.35) * (1 if r.random() < 0.5 else -1)
        cv_ = r.uniform(60, 340)
        dist = (uuu - cu) * np.cos(a) + (vvv - cv_) * np.sin(a)
        L = r.uniform(70, 260)
        along = np.abs((vvv - cv_) * np.cos(a) - (uuu - cu) * np.sin(a)) / L
        cre += dep * np.exp(-(dist / w) ** 2) * np.exp(-np.clip(along, 0, 5) ** 3)
    cre += -0.35 * np.exp(-((vvv - 40) / 9.0) ** 2) + 0.28 * np.exp(-((vvv - 312) / 12.0) ** 2) * (0.6 + 0.4 * noise1d(W, 90 * PX, r)[None, :])
    # edge buckling: v2 aperiodic (phase wanders, amplitude is noise-modulated, strong only on ~45 % of the length)
    lam = 62 + 52 * np.abs(noise1d(W, 90 * PX, r, 2))
    ph = np.cumsum(2 * np.pi / (lam * PX) * (1 + 0.35 * noise1d(W, 14 * PX, r))).astype(np.float32)
    ed_t = np.maximum(vvv - vt[None, :], 0); ed_b = np.maximum(vb[None, :] - vvv, 0)
    amp_t = np.clip(0.55 + 0.9 * noise1d(W, 130 * PX, r), 0.0, 1.5); amp_b = np.clip(0.55 + 0.9 * noise1d(W, 130 * PX, r), 0.0, 1.5)
    buck = 1.4 * amp_t[None, :] * np.sin(ph)[None, :] * np.exp(-ed_t / 24.0) + 1.1 * amp_b[None, :] * np.sin(ph * 0.83 + 1.7)[None, :] * np.exp(-ed_b / 24.0)
    S['h'] += (fold + cre * 1.0 + buck).astype(np.float32)
    S['alb'] *= (1 + 0.10 * np.clip(cre, -1, 1)[..., None])
    # ---------------------------------------------------------------- edge lift: v2 PATCHY (curls on ~40 % of the length, flat elsewhere)
    ed2 = np.minimum(vvv - vt[None, :], vb[None, :] - vvv)
    ed2 = np.minimum(ed2, np.where(hole > 0.5, 0, 1e3))
    dist_hole = cv2.distanceTransform((hole < 0.5).astype(np.uint8), cv2.DIST_L2, 3) / PX
    curl_u = np.clip(0.5 + 1.6 * noise1d(W, 85 * PX, r, 2), 0, 1) ** 1.4
    lift = (0.15 + 1.5 * act * curl_u[None, :] + 1.0 * curl_u[None, :]) * np.exp(-np.maximum(ed2, 0) / 4.5) + (1.3 * np.exp(-dist_hole / 5.0) * (hole < 0.5))
    S['h'] += (lift * (0.6 + 0.4 * np.clip(vnoise(0.0, 0.0, H, W, PX, 14.0, seed + 71, 2) * 1.5 + 0.5, 0, 1))).astype(np.float32)
    # ---------------------------------------------------------------- the comb of loose yarn ends (v2): raw warp yarn, pale grey-tan
    cm = comb_a > 0
    yarn = hex_lin('#9C917B')
    yv = (0.70 + 0.35 * r.random((H, W)).astype(np.float32))
    S['alb'][cm] = (yarn[None, :] * yv[cm][:, None] * 0.52)
    S['h'][cm] = 0.35 + 0.15 * r.random(int(cm.sum()))
    S['T'][cm] = (0.0, 1.0)
    S['mat'][cm] = 0
    S['cov'][cm] = 0.0
    S['cloth'] = alpha.astype(np.float32)
    S['hole'] = cv2.GaussianBlur(hole, (0, 0), 1.6 * PX).astype(np.float32)
    S['extra'] = np.dstack([act, brown, scorch]).astype(np.float32)
    return S, info


if __name__ == '__main__':
    PX = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    z = np.load(f'{WORK}/strip_raw_{PX:g}.npz')
    S = {k: z[k] for k in z.files}
    t0 = time.time()
    S, info = finish(S, PX)
    np.savez_compressed(f'{WORK}/strip_final_{PX:g}{TAG}.npz', **S)
    np.savez_compressed(f'{WORK}/strip_info_{PX:g}{TAG}.npz', **{k: np.asarray(v) for k, v in info.items()})
    print('finished', time.time() - t0)
