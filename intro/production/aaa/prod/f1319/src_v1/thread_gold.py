"""The chronicle thread: one continuous two-ply couched gold thread on the border rule.  It is painted into the WORLD maps (not
the strip), so where the cloth has frayed away from under it the thread hangs free and lies on the walnut, unbroken."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from s18common import *
from geometry import *
from chron.color import hex_lin, pal
from chron.config import METAL, SILK
from finish_strip import noise1d


def thread_path(th, info, Ls=4100.0, seed=3, du=0.5):
    """world polyline of the thread (and the strip-v actually followed)."""
    r = np.random.default_rng(seed)
    u = np.arange(0, Ls, du, dtype=np.float32)
    PXs = len(th['vc']) / Ls
    vc = np.interp(u, np.arange(len(th['vc'])) / PXs, th['vc'])
    vt = np.interp(u, np.arange(len(info['vt'])) / PXs, info['vt'])
    vt_s = cv2.GaussianBlur(vt.reshape(1, -1), (0, 0), 14.0 / du).ravel()
    gap = np.clip((vt_s - (vc - 1.0)) / 9.0, 0, 1)                 # 1 where the cloth has frayed away from under the thread
    free = noise1d(len(u), 55.0 / du, r, 2) * 9.0 + noise1d(len(u), 14.0 / du, r, 2) * 2.0
    # a free thread relaxes toward the table edge it fell onto (slightly outward) and wanders
    dv = gap * (free - 3.0 * gap)
    v = vc + dv
    X, Y = strip_to_world(u, v)
    tt = np.interp(u, np.arange(len(th['t'])) / PXs, th['t'])
    return u, v, X, Y, tt, gap


def paint_gold(m, PX, th, info, glint_u=3390.0, SS=4, seed=3):
    x0, y0 = m['origin_mm']
    H, W = m['h'].shape
    u, v, X, Y, tt, gap = thread_path(th, info, seed=seed)
    # glint stretch stays bright (the survivor): u in glint_u +- 90 mm
    tt = np.maximum(tt, np.exp(-((u - glint_u) / 120.0) ** 2) * 1.0)
    keep = (X > x0 - 5) & (X < x0 + W / PX + 5) & (Y > y0 - 30) & (Y < y0 + H / PX + 30)
    idx = np.nonzero(keep)[0]
    if len(idx) < 2: return m
    P = np.stack([(X[idx] - x0) * PX, (Y[idx] - y0) * PX], 1)          # world px
    ya, yb = int(max(0, math.floor(P[:, 1].min()) - 10)), int(min(H, math.ceil(P[:, 1].max()) + 10))
    h2 = (yb - ya)
    P = np.stack([P[:, 0] * SS, (P[:, 1] - ya) * SS], 1)
    mask = np.zeros((h2 * SS, W * SS), np.uint8)
    ang = np.zeros((h2 * SS, W * SS), np.uint8)
    colt = np.zeros((h2 * SS, W * SS), np.uint8)
    thick = max(1, int(round(2.5 * PX * SS)))
    seg = 3
    for k in range(0, len(idx) - seg, seg):
        p0, p1 = P[k], P[k + seg]
        a = math.atan2(p1[1] - p0[1], p1[0] - p0[0]) % math.pi
        cv2.line(mask, tuple(np.round(p0).astype(int)), tuple(np.round(p1).astype(int)), 255, thick, cv2.LINE_8)
        cv2.line(ang, tuple(np.round(p0).astype(int)), tuple(np.round(p1).astype(int)), int(a / math.pi * 255), thick, cv2.LINE_8)
        cv2.line(colt, tuple(np.round(p0).astype(int)), tuple(np.round(p1).astype(int)), int(np.clip(tt[idx[k]], 0, 1) * 255), thick, cv2.LINE_8)
    sz = (W, h2)
    cover = cv2.resize(mask, sz, interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    cnt = cv2.resize(mask, sz, interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0 + 1e-6      # = cover
    angm = np.clip(cv2.resize(ang, sz, interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0 / cnt, 0, 1) * math.pi
    tarn = np.clip(cv2.resize(colt, sz, interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0 / cnt, 0, 1)
    del mask, ang, colt
    gold_hi, gold_lo = hex_lin('#E9BE6A'), hex_lin('#7A5A2A') * 0.75
    col = gold_lo[None, None] * (1 - tarn[..., None]) + gold_hi[None, None] * tarn[..., None]
    dist = cv2.GaussianBlur(cover, (0, 0), 0.9 * PX)
    tube = 0.95 * np.sqrt(np.clip(dist / max(dist.max(), 1e-3), 0, 1)) * (cover > 0.05)
    a = np.clip(cover * 1.15, 0, 1)
    sl = slice(ya, yb)
    m['alb'][sl] = m['alb'][sl] * (1 - a[..., None]) + col * a[..., None]
    m['h'][sl] = m['h'][sl] + (tube * a).astype(np.float32)
    sel = a > 0.4
    m['mat'][sl][sel] = METAL
    m['T'][sl][sel] = np.stack([np.cos(angm), np.sin(angm)], -1)[sel]
    m['cov'][sl][sel] = 0.0
    m['spec'][sl][sel] = (0.10 + 0.90 * np.clip(tarn, 0, 1) ** 1.3)[sel]
    return m
