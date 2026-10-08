"""The chronicle thread (v2): one continuous two-ply couched gold thread on the border rule, tarnished and dull along its whole length,
with tie-down stitches, a smooth path, and a brighter surviving stretch at the far right.  It is painted into the WORLD maps (not the
strip), so where the cloth has frayed away from under it the thread hangs free and lies on the walnut, unbroken."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from s18common import *
from geometry import *
from chron.color import hex_lin, pal
from chron.config import METAL, SILK, WOOL
from finish_strip import noise1d

THREAD_MM = 3.0          # visible thickness of the two-ply thread (v1 2.5)
SURV_U0 = float(os.environ.get('F_SURV0', '3120')); SURV_U1 = SURV_U0 + 210.0   # the survivor: the dull bronze warms and brightens between these u


def thread_path(th, info, Ls=4100.0, seed=3, du=0.5):
    """world polyline of the thread (and the strip-v actually followed)."""
    r = np.random.default_rng(seed)
    u = np.arange(0, Ls, du, dtype=np.float32)
    PXs = len(th['vc']) / Ls
    vc = np.interp(u, np.arange(len(th['vc'])) / PXs, th['vc'])
    vt = np.interp(u, np.arange(len(info['vt'])) / PXs, info['vt'])
    vt_s = cv2.GaussianBlur(vt.reshape(1, -1), (0, 0), 26.0 / du).ravel()
    gap = np.clip((vt_s - (vc - 1.0)) / 14.0, 0, 1)                 # 1 where the cloth has frayed away from under the thread
    gap = cv2.GaussianBlur(gap.reshape(1, -1).astype(np.float32), (0, 0), 10.0 / du).ravel()
    # v2: smoother, with a gravity-like sag toward the table edge it fell onto (no kinks)
    free = noise1d(len(u), 70.0 / du, r, 2) * 3.0 + noise1d(len(u), 22.0 / du, r, 1) * 0.8
    # a released thread falls and comes to lie along the torn edge it was couched to: it relaxes 55 % of the way into the notch
    dv = gap * ((vt_s - vc) * 0.55 + free)
    v = vc + dv
    v = cv2.GaussianBlur(v.reshape(1, -1).astype(np.float32), (0, 0), 8.0 / du).ravel()
    X, Y = strip_to_world(u, v)
    tt = np.interp(u, np.arange(len(th['t'])) / PXs, th['t'])
    return u, v, X, Y, tt, gap


def tarnish_profile(u, glint_u):
    """0 dull bronze .. 1 bright gold, along the thread: dull everywhere (0.22-0.45), the survivor warms from SURV_U0 on."""
    r = np.random.default_rng(41)
    base = 0.24 + 0.14 * noise1d(len(u), 60.0 / 0.5, r, 2) + 0.06 * noise1d(len(u), 9.0 / 0.5, r, 1)
    base = np.clip(base, 0.08, 0.42)
    t = np.clip((u - SURV_U0) / (SURV_U1 - SURV_U0), 0, 1); t = t * t * (3 - 2 * t)
    surv = 0.46 * t
    glint = np.exp(-((u - glint_u) / 110.0) ** 2) * 0.35
    return np.clip(np.maximum(base, base + surv) + glint, 0, 1)


def paint_gold(m, PX, th, info, glint_u=3262.0, SS=4, seed=3):
    x0, y0 = m['origin_mm']
    H, W = m['h'].shape
    u, v, X, Y, tt, gap = thread_path(th, info, seed=seed)
    tt = tarnish_profile(u, glint_u)
    keep = (X > x0 - 5) & (X < x0 + W / PX + 5) & (Y > y0 - 30) & (Y < y0 + H / PX + 30)
    idx = np.nonzero(keep)[0]
    if len(idx) < 2: return m
    P = np.stack([(X[idx] - x0) * PX, (Y[idx] - y0) * PX], 1)          # world px
    ya, yb = int(max(0, math.floor(P[:, 1].min()) - 14)), int(min(H, math.ceil(P[:, 1].max()) + 14))
    h2 = (yb - ya)
    P = np.stack([P[:, 0] * SS, (P[:, 1] - ya) * SS], 1)
    mask = np.zeros((h2 * SS, W * SS), np.uint8)
    ang = np.zeros((h2 * SS, W * SS), np.uint8)
    colt = np.zeros((h2 * SS, W * SS), np.uint8)
    ply = np.zeros((h2 * SS, W * SS), np.uint8)
    tie = np.zeros((h2 * SS, W * SS), np.uint8)
    thick = max(1, int(round(THREAD_MM * PX * SS)))
    seg = 2
    for k in range(0, len(idx) - seg, seg):
        p0, p1 = P[k], P[k + seg]
        a = math.atan2(p1[1] - p0[1], p1[0] - p0[0]) % math.pi
        q0, q1 = tuple(np.round(p0).astype(int)), tuple(np.round(p1).astype(int))
        cv2.line(mask, q0, q1, 255, thick, cv2.LINE_8)
        cv2.line(ang, q0, q1, int(a / math.pi * 255), thick, cv2.LINE_8)
        cv2.line(colt, q0, q1, int(np.clip(tt[idx[k]], 0, 1) * 255), thick, cv2.LINE_8)
        # two-ply twist: S-shaped lay, phase advancing along the thread (period 2.8 mm)
        ph = u[idx[k]] / 2.8 * 2 * math.pi
        cv2.line(ply, q0, q1, int(128 + 127 * math.sin(ph)), thick, cv2.LINE_8)
    # tie-down stitches (couching): a short stroke across the thread every 22-40 mm where the cloth still holds it
    ties = th['ties'] if 'ties' in th else []
    for tu in ties:
        i = int(round(tu / 0.5))
        if i < 0 or i >= len(u) or not keep[i] or gap[i] > 0.35: continue
        j0, j1 = max(i - 3, 0), min(i + 3, len(u) - 1)
        dX, dY = (X[j1] - X[j0]), (Y[j1] - Y[j0])
        n = math.hypot(dX, dY) + 1e-6
        nxm, nym = -dY / n, dX / n
        cx, cy = (X[i] - x0) * PX * SS, (Y[i] - y0) * PX * SS - ya * SS
        hl = 2.7 * PX * SS
        cv2.line(tie, (int(round(cx - nxm * hl)), int(round(cy - nym * hl))), (int(round(cx + nxm * hl)), int(round(cy + nym * hl))), 255,
                 max(1, int(round(1.3 * PX * SS))), cv2.LINE_8)
    sz = (W, h2)
    cover = cv2.resize(mask, sz, interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    cnt = cover + 1e-6
    angm = np.clip(cv2.resize(ang, sz, interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0 / cnt, 0, 1) * math.pi
    tarn = np.clip(cv2.resize(colt, sz, interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0 / cnt, 0, 1)
    plyv = (cv2.resize(ply, sz, interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0 / cnt - 0.5) * 2.0
    tiev = np.clip(cv2.resize(tie, sz, interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0, 0, 1)
    del mask, ang, colt, ply, tie
    gold_hi, gold_lo = hex_lin('#E6B85E'), hex_lin('#6E5C3C') * 0.80
    col = gold_lo[None, None] * (1 - tarn[..., None]) + gold_hi[None, None] * tarn[..., None]
    col = col * (1 + 0.20 * np.clip(plyv, -1, 1))[..., None]                 # ply banding
    dist = cv2.GaussianBlur(cover, (0, 0), 0.9 * PX)
    tube = 1.25 * np.sqrt(np.clip(dist / max(dist.max(), 1e-3), 0, 1)) * (cover > 0.05)
    tube = tube * (1 + 0.10 * np.clip(plyv, -1, 1))
    a = np.clip(cover * 1.15, 0, 1)
    sl = slice(ya, yb)
    m['alb'][sl] = m['alb'][sl] * (1 - a[..., None]) + col * a[..., None]
    m['h'][sl] = m['h'][sl] + (tube * a).astype(np.float32)
    sel = a > 0.4
    m['mat'][sl][sel] = METAL
    m['T'][sl][sel] = np.stack([np.cos(angm), np.sin(angm)], -1)[sel]
    m['cov'][sl][sel] = 0.0
    m['spec'][sl][sel] = (0.08 + 0.92 * np.clip(tarn, 0, 1) ** 1.4)[sel]
    # tie-down wool stitches over the thread (undyed drab wool, slightly raised)
    tsel = tiev > 0.45
    tcol = hex_lin('#7A6C55')
    m['alb'][sl][tsel] = tcol[None, :] * 0.9
    m['h'][sl][tsel] += 0.55
    m['mat'][sl][tsel] = WOOL
    m['T'][sl][tsel] = np.array([0.0, 1.0], np.float32)
    m['cov'][sl][tsel] = 0.5
    m['spec'][sl][tsel] = 1.0
    return m
