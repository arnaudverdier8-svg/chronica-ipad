"""Finish the chronicle strip for S18: Act-III ageing + dying edges, folds / creases, burn-through at the war|ruin join,
scorched ruin margins, mends, and the frayed cloth boundary (stair-stepped weft runs).  Strip-local coordinates."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from s18common import *
from chron.ageing import apply_age
from chron.color import hex_lin, pal, lin2oklab, oklab2lin
from chron.util import vnoise, sstep
from chron.config import LINEN, WOOL, METAL

HS = 400.0
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
TOP_BITES = [(205, 130, 38), (470, 70, 16), (760, 95, 22), (880, 45, 40), (1130, 60, 9), (1520, 55, 8), (2010, 80, 12), (2360, 70, 20),
             (2505, 62, 52), (2780, 100, 26), (3095, 58, 46), (3270, 120, 40), (3450, 90, 70), (3640, 100, 52)]
BOT_BITES = [(150, 150, 52), (430, 90, 20), (690, 60, 10), (1010, 80, 11), (1700, 70, 8), (2140, 90, 16), (2560, 70, 13),
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
    vt = np.maximum(0.0, bt + jt + 0.6)
    vb = HS - np.maximum(0.0, bb + jb + 0.6)
    vt = np.round(vt / pitch) * pitch
    vb = HS - np.round((HS - vb) / pitch) * pitch
    info.update(vt=vt.astype(np.float32), vb=vb.astype(np.float32), bt=bt.astype(np.float32), bb=bb.astype(np.float32))
    alpha = np.clip((vv[:, None] - vt[None, :]) * PX + 0.5, 0, 1) * np.clip((vb[None, :] - vv[:, None]) * PX + 0.5, 0, 1)
    # ---------------------------------------------------------------- burn-through at the war | ruin join
    ub, vbn = 3151.0, 236.0
    uuu, vvv = np.meshgrid(uu, vv)
    nz = vnoise(0.0, 0.0, H, W, PX, 22.0, seed + 31, 3)
    nz2 = vnoise(0.0, 0.0, H, W, PX, 7.0, seed + 32, 2)
    d = np.hypot((uuu - ub) / 52.0, (vvv - vbn) / 96.0) + 0.30 * nz + 0.10 * nz2
    hole = (d < 1.0).astype(np.float32)
    hole = cv2.GaussianBlur(hole, (0, 0), 0.5 * PX)
    alpha *= (1 - hole)
    info['hole'] = (ub, vbn)
    # scorch fields around the hole (distance in noise-warped units -> mm)
    dmm = np.maximum(d - 1.0, 0) * 52.0                    # ~mm outside the hole
    char = np.exp(-(dmm / 2.6) ** 1.5) * (d >= 1.0)        # black char rim
    scorch = np.exp(-(dmm / 13.0) ** 1.3) * (d >= 1.0)     # brown scorch / soot halo
    # ruin panel margins: a creeping burn from the p6 edges (its right / top / bottom), soot clouds
    p6x0, p6x1 = 3151.2, 3741.6
    xr = np.clip((uuu - p6x0) / 590.4, 0, 1)
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
    # Act-III grime: large-scale mottled darkening of the whole cloth, deeper toward both ends of the frame (the dying edges),
    # with the dyes also losing chroma there
    gm = vnoise(0.0, 0.0, H, W, PX, 160.0, seed + 81, 3) * 1.1 + 0.5 * vnoise(0.0, 0.0, H, W, PX, 38.0, seed + 82, 2)
    gm = np.clip(0.45 + gm, 0, 1) ** 1.4
    end = np.clip((np.abs(uuu - UC) - 800.0) / 1100.0, 0, 1)
    dark = np.clip(0.07 + 0.20 * gm + 0.28 * end ** 1.2, 0, 0.6)
    tintg = np.array([0.88, 0.78, 0.62], np.float32)
    S['alb'] = S['alb'] * (1 - dark[..., None]) + S['alb'] * tintg * dark[..., None]
    lab = lin2oklab(S['alb']); ch = (1 - 0.40 * end)[..., None]
    lab[..., 1:] *= ch
    lab[..., 1:] *= 0.90                      # a touch less saturated overall: aged, faded Act-III cloth
    S['alb'] = oklab2lin(lab)
    # dying edges: browning + fade towards both long edges and the ragged parts (tideline colour), dye fade a bit more
    ed = np.minimum(vvv - vt[None, :], vb[None, :] - vvv)            # mm inside the cloth boundary
    act = np.clip((bt[None, :] * (vvv < HS / 2) + bb[None, :] * (vvv >= HS / 2)) / 25.0, 0, 1)
    brown = np.exp(-np.maximum(ed, 0) / (14.0 + 20.0 * act)) * (0.35 + 0.55 * act) * (0.8 + 0.4 * burn_n)
    tc = hex_lin('#7C5A38'); tc = tc / tc.max()
    S['alb'] = S['alb'] * (1 - brown[..., None] * 0.55) + S['alb'] * tc * brown[..., None] * 0.55
    # dye lots dimmer at both ends of the frame (colour fading deeper where the light left first)
    # scorch / soot
    soot = hex_lin('#2A2320'); brn = hex_lin('#5A3A20')
    sc = np.clip(scorch, 0, 1)[..., None]
    S['alb'] = S['alb'] * (1 - 0.55 * sc) + (S['alb'] * 0.45 * brn / brn.max()) * 0.55 * sc
    ch = np.clip(char, 0, 1)[..., None]
    S['alb'] = S['alb'] * (1 - ch) + soot * 0.6 * ch
    S['h'] += (0.55 * ch[..., 0] + 0.15 * sc[..., 0])                    # charred crust raised, scorch slightly crisp
    # soot smears
    smear = np.clip(vnoise(0.0, 0.0, H, W, PX, 60.0, seed + 51, 3) * 1.4 - 0.55, 0, 1) * in6 * 0.6
    S['alb'] = S['alb'] * (1 - smear[..., None] * 0.6)
    # ---------------------------------------------------------------- mends (faded, mismatched darning)
    def mend(cu, cv, w, h, ang=0.0):
        """a darned patch: mismatched faded thread laid in tight parallel runs, ragged edge, slightly raised."""
        nzm = vnoise(0.0, 0.0, H, W, PX, 5.0, seed + int(cu), 2)
        mask = ((np.abs(uuu - cu) < w / 2 + 1.6 * nzm) & (np.abs(vvv - cv) < h / 2 + 1.6 * nzm))
        m = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 0.4 * PX)
        pick = hex_lin('#CFC6AC') * 0.80 if r.random() < 0.6 else hex_lin('#8A9C86') * 0.75
        rows = 0.5 + 0.5 * np.sin(vvv * 2 * np.pi / 1.7)                     # darning runs, 1.7 mm pitch
        brk = 0.5 + 0.5 * np.sin(uuu * 2 * np.pi / 9.0 + np.floor(vvv / 1.7) * 2.1)   # staggered run ends
        tex = 0.80 + 0.14 * rows + 0.08 * brk
        mm_ = m[..., None] * 0.92
        S['alb'] = S['alb'] * (1 - mm_) + (pick[None, None, :] * tex[..., None]) * mm_
        S['h'] += (0.28 * m + 0.10 * rows * m).astype(np.float32)
        S['mat'][mask] = 1
        S['T'][mask] = (1.0, 0.0)
        S['cov'][mask] = 0.6
    mend(2330.0, 150.0, 26, 17); mend(3010.0, 338.0, 30, 19)
    # ---------------------------------------------------------------- folds / creases (low-frequency relief)
    fold = 2.4 * vnoise(0.0, 0.0, H, W, PX, 120.0, seed + 61, 3) + 0.5 * vnoise(0.0, 0.0, H, W, PX, 34.0, seed + 62, 2)
    cre = np.zeros((H, W), np.float32)
    for k in range(26):
        cu = r.uniform(100, 3900)
        a = np.deg2rad(r.normal(0, 9))
        w = r.uniform(5, 12); dep = r.uniform(0.35, 0.9) * (1 if r.random() < 0.5 else -1)
        dist = (uuu - cu) * np.cos(a) + (vvv - 200) * np.sin(a)
        L = r.uniform(120, 330)
        along = np.abs((vvv - 200) * np.cos(a) - (uuu - cu) * np.sin(a)) / L
        cre += dep * np.exp(-(dist / w) ** 2) * np.exp(-np.clip(along, 0, 5) ** 3)
    # one soft long fold along the length (cloth rolled for years): shallow valley near v = 38 and ridge at 300
    cre += -0.35 * np.exp(-((vvv - 40) / 9.0) ** 2) + 0.28 * np.exp(-((vvv - 312) / 12.0) ** 2) * (0.6 + 0.4 * noise1d(W, 90 * PX, r)[None, :])
    # edge buckling (cloth shrunk along its selvages: soft scallops of 45-95 mm wavelength fading over ~30 mm)
    lam = 70 + 28 * noise1d(W, 160 * PX, r)
    ph = np.cumsum(2 * np.pi / (lam * PX)); ph = ph.astype(np.float32)
    ed_t = np.maximum(vvv - vt[None, :], 0); ed_b = np.maximum(vb[None, :] - vvv, 0)
    buck = 1.6 * np.sin(ph)[None, :] * np.exp(-ed_t / 24.0) + 1.3 * np.sin(ph * 0.83 + 1.7)[None, :] * np.exp(-ed_b / 24.0)
    S['h'] += (fold + cre * 1.0 + buck).astype(np.float32)
    S['alb'] *= (1 + 0.10 * cre[..., None] * np.sign(cre[..., None]) * -1 * 0)  # (creases carry relief only)
    # soft wear shading on the creases (abraded ridges lighter, valleys dirt-darker)
    S['alb'] *= (1 + 0.10 * np.clip(cre, -1, 1)[..., None])
    # ---------------------------------------------------------------- edge lift (curling, fraying edges rise)
    ed2 = np.minimum(vvv - vt[None, :], vb[None, :] - vvv)
    ed2 = np.minimum(ed2, np.where(hole > 0.5, 0, 1e3))
    dist_hole = cv2.distanceTransform((hole < 0.5).astype(np.uint8), cv2.DIST_L2, 3) / PX
    lift = (0.5 + 1.2 * act) * np.exp(-np.maximum(ed2, 0) / 5.0) + (1.2 * np.exp(-dist_hole / 6.0) * (hole < 0.5))
    S['h'] += (lift * (0.6 + 0.4 * np.clip(vnoise(0.0, 0.0, H, W, PX, 14.0, seed + 71, 2) * 1.5 + 0.5, 0, 1))).astype(np.float32)
    S['cloth'] = alpha.astype(np.float32)
    S['extra'] = np.dstack([act, brown, scorch]).astype(np.float32)
    return S, info


if __name__ == '__main__':
    PX = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    z = np.load(f'{WORK}/strip_raw_{PX:g}.npz')
    S = {k: z[k] for k in z.files}
    t0 = time.time()
    S, info = finish(S, PX)
    np.savez_compressed(f'{WORK}/strip_final_{PX:g}.npz', **S)
    np.savez_compressed(f'{WORK}/strip_info_{PX:g}.npz', **{k: np.asarray(v) for k, v in info.items()})
    print('finished', time.time() - t0)
