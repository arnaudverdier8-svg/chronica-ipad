"""M2: the game's knight figure card (idle) re-embroidered as a stitched figure on its own linen 'slip' layer."""
import math, time
import numpy as np, cv2
from .core import *
from .segment import FAM, oklab_lch, majority, components
from . import stitch as S
from .skel import skeleton_paths, merge_paths

D = f'{A}/assets/tex/figures/'
REALM = {'blue': '#2D4460', 'red': '#7A2A1E', 'green': '#3A4F1F', 'gold': '#B8862E'}


def frankot_chellappa(p, q):
    H, W = p.shape
    wx = np.fft.fftfreq(W) * 2 * np.pi; wy = np.fft.fftfreq(H) * 2 * np.pi
    WX, WY = np.meshgrid(wx, wy)
    P, Q = np.fft.fft2(p), np.fft.fft2(q)
    den = WX ** 2 + WY ** 2; den[0, 0] = 1
    Z = (-1j * WX * P - 1j * WY * Q) / den; Z[0, 0] = 0
    return np.real(np.fft.ifft2(Z)).astype(np.float32)


def load_card(unit='knight', pose='idle'):
    a = load_rgba(f'{D}{unit}_{pose}_albedo.png').astype(np.float32) / 255
    n = load_rgba(f'{D}{unit}_{pose}_normal.png').astype(np.float32) / 255
    mk = load_rgba(f'{D}{unit}_{pose}_mask.png').astype(np.float32) / 255
    mk = cv2.resize(mk, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_LINEAR)
    return a, n, mk


def build_knight(base_linen, PX, height_mm=135.0, realm='blue', seed=0, verbose=True, margin_mm=1.6):
    """base_linen: maps dict (window of canvas linen, will be copied). Returns layer dict (maps + alpha + ghost info)."""
    t0 = time.time()
    a, n, mk = load_card()
    Hc, Wc = a.shape[:2]
    sc = height_mm * PX / Hc
    Hm, Wm = int(round(Hc * sc)), int(round(Wc * sc))
    Hb, Wb = base_linen['h'].shape
    oy, ox = (Hb - Hm) // 2, (Wb - Wm) // 2
    up = lambda x, interp=cv2.INTER_CUBIC: cv2.resize(x, (Wm, Hm), interpolation=interp)
    alb = np.clip(up(a[..., :3]), 0, 1); alpha = np.clip(up(a[..., 3], cv2.INTER_LINEAR), 0, 1)
    nm = up(n[..., :3]) * 2 - 1
    mku = np.clip(up(mk, cv2.INTER_LINEAR), 0, 1)
    src_lin = srgb2lin(alb)
    src_blur = cv2.GaussianBlur(src_lin, (0, 0), 0.4 * PX)
    lum = cv2.cvtColor((alb * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    # ---- relief from the game normal map (low frequency = padding of parts)
    nz = np.clip(nm[..., 2], 0.2, 1)
    p, q = -nm[..., 0] / nz, nm[..., 1] / nz          # GL y-up -> screen y-down
    hgt = frankot_chellappa(cv2.GaussianBlur(p, (0, 0), 2.0), cv2.GaussianBlur(q, (0, 0), 2.0))
    hgt = cv2.GaussianBlur(hgt, (0, 0), 1.2 * PX)
    inside = alpha > 0.5
    hgt -= np.percentile(hgt[inside], 5); hgt = np.clip(hgt / (np.percentile(hgt[inside], 98) + 1e-6), 0, 1.2)
    hgt *= cv2.GaussianBlur(inside.astype(np.float32), (0, 0), 0.8 * PX)
    # ---- families
    ms = cv2.pyrMeanShiftFiltering(cv2.cvtColor((alb * 255).astype(np.uint8), cv2.COLOR_RGB2BGR), int(0.5 * PX), 18, maxLevel=1)
    ms = cv2.cvtColor(ms, cv2.COLOR_BGR2RGB)
    lab_, L, C, h = oklab_lch(ms)
    hue = lambda lo, hi: ((h - lo) % 360) <= ((hi - lo) % 360)
    fam = np.full((Hm, Wm), FAM['horse'], np.int32)
    fam[(C < 0.03) & (L > 0.40)] = FAM['steel']
    fam[(C < 0.045) & (L > 0.74)] = FAM['white']
    fam[hue(60, 105) & (C > 0.07) & (L > 0.56)] = FAM['gold']
    fam[hue(30, 80) & (C > 0.04) & (L <= 0.56) & (L > 0.33)] = FAM['horse']
    fam[(L <= 0.36) & (C > 0.03)] = FAM['horse_dark']
    fam[L < 0.26] = FAM['black']
    fam[mku[..., 0] > 0.5] = FAM['team']
    fam[mku[..., 1] > 0.5] = FAM['jewel']   # shield field
    cord = (mku[..., 3] > 0.45) & inside
    fam = majority(fam, 5, 1, n=21)
    fam[~inside] = FAM['bg']
    fam[cord] = FAM['cord']
    lab, info = components(fam, int(1.0 * PX * PX))
    # ---- layer maps: copy of the canvas linen under the figure (seamless when flat)
    m = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in base_linen.items()}
    S.ensure(m)
    mm = {k: (v[oy:oy + Hm, ox:ox + Wm] if isinstance(v, np.ndarray) else v) for k, v in m.items()}
    mm['_oxy'] = (ox, oy)
    base_relief = (0.35 * hgt).astype(np.float32)        # flat-stitched state: subtle padding (mm)
    mm['base'][:] = base_relief
    P = {k: hex_lin(v['hex']) for k, v in PAL['cinematic'].items()}
    team = hex_lin(REALM[realm])
    pulls = {FAM['horse']: [P['madder_dark'], P['terracotta'], hex_lin('#5A3A22'), hex_lin('#8A5A34')],
             FAM['horse_dark']: [hex_lin('#3A2216'), P['madder_dark']],
             FAM['steel']: [P['steel'], P['steel_lo'], hex_lin('#8E9196'), P['woad_dark']],
             FAM['white']: [P['linen_hi'], hex_lin('#EFE8DA'), P['steel']],
             FAM['gold']: [P['mustard'], P['gold'], P['gold_lo']],
             FAM['black']: [P['ink_blueblack'], hex_lin('#2A1A12')],
             FAM['team']: [team, team * 1.5, team * 0.6],
             FAM['jewel']: [P['crimson'], P['crimson_hi'], P['crimson_deep']]}
    if verbose: print(f'  knight: setup {time.time() - t0:.1f}s, {len(info)} regions, {Wm}x{Hm}')
    order = [FAM['team'], FAM['horse'], FAM['horse_dark'], FAM['white'], FAM['steel'], FAM['gold'], FAM['black'], FAM['jewel']]
    rids = sorted(info.keys(), key=lambda r: (order.index(info[r]['fam']) if info[r]['fam'] in order else 99, -info[r]['area']))
    for rid in rids:
        f = info[rid]['fam']
        if f in (FAM['bg'], FAM['cord']): continue
        mkr = lab == rid
        ys, xs = np.nonzero(mkr)
        if len(ys) < 0.6 * PX * PX: continue
        area_mm2 = len(ys) / PX / PX
        y0, y1 = max(ys.min() - 30, 0), min(ys.max() + 31, Hm); x0, x1 = max(xs.min() - 30, 0), min(xs.max() + 31, Wm)
        sub = {k: (v[y0:y1, x0:x1] if isinstance(v, np.ndarray) and v.ndim >= 2 else v) for k, v in mm.items()}
        sub['_oxy'] = (ox + x0, oy + y0); S.TAG[0] = ('fill', int(rid), int(f))
        lab_c = lab[y0:y1, x0:x1]; mk_c = mkr[y0:y1, x0:x1]; sb = src_blur[y0:y1, x0:x1]
        lum_c = lum[y0:y1, x0:x1]
        sd = seed * 1000 + rid
        pix = src_lin[mkr]
        def field(sig_t, w_shape=0.25):
            a1 = S.orient_tensor(lum_c, 0.3 * PX, sig_t * PX, mask=mk_c)
            mb = cv2.GaussianBlur(mk_c.astype(np.float32), (0, 0), 1.5 * PX)
            b1 = S.orient_tensor(mb, 0.5 * PX, 2.5 * PX, mask=mk_c)
            return S.blend_fields([a1, b1], [1.0, w_shape])
        nsh = int(np.clip(area_mm2 / 40, 2, 5))
        if f == FAM['team']:
            pix_t = np.clip(team * (src_lin[mkr].mean(-1, keepdims=True) / 0.42), 0, 1)
            shd = S.ShadeSet.from_pixels(pix_t, 4, pulls[f], 0.3, sd)
            sbt = np.clip(team * (sb.mean(-1, keepdims=True) / 0.42), 0, 1)
            S.fill_region(sub, lab_c, rid, field(3.0, 0.3), sbt, shd, PX, style='laid', pitch=0.85, seed=sd, ext=0.7,
                          couch=dict(spacing=4.2, tie=3.8) if area_mm2 > 50 else None)
        elif f == FAM['jewel']:   # shield: padded silk satin (heraldic register)
            pad = S.pad_dome(mk_c, PX, 1.3, 3.0)
            sub['base'][:] = np.maximum(sub['base'], pad + sub['base'] * 0.5)
            shc = P['crimson'] * 0.66
            shd = S.ShadeSet.from_pixels(np.tile(shc, (50, 1)) * np.random.default_rng(sd).uniform(0.8, 1.15, (50, 1)), 3, None, 0.2, sd)
            S.fill_region(sub, lab_c, rid, S.const_field(lab_c.shape, 100), np.tile(shc, lab_c.shape + (1,)), shd, PX,
                          style='laid', pitch=0.55, seed=sd, matid=SILK, h0=0.05, hamp=0.32, r_fac=0.6, maxlen=60)
        elif f in (FAM['horse'], FAM['white']) and area_mm2 > 80:
            shd = S.ShadeSet.from_pixels(pix, nsh + 1, pulls[f], 0.45, sd)
            S.fill_region(sub, lab_c, rid, field(2.5, 0.3), sb, shd, PX, style='laid', pitch=0.85, seed=sd, ext=0.7,
                          couch=dict(spacing=4.5, tie=4.0))
        elif f == FAM['steel']:
            shd = S.ShadeSet.from_pixels(pix, nsh + 1, pulls[f], 0.4, sd)
            S.fill_region(sub, lab_c, rid, field(1.2, 0.3), sb, shd, PX, style='split', L=2.6, pitch=0.6, seed=sd,
                          h0=0.06, hamp=0.36, matid=WOOL)
        elif f == FAM['gold']:
            shd = S.ShadeSet.from_pixels(pix, nsh, pulls[f], 0.5, sd)
            S.fill_region(sub, lab_c, rid, field(1.2, 0.5), sb, shd, PX, style='laid', pitch=0.6, seed=sd, maxlen=40)
        else:
            shd = S.ShadeSet.from_pixels(pix, nsh, pulls.get(f, pulls[FAM['horse']]), 0.4, sd)
            S.fill_region(sub, lab_c, rid, field(1.5, 0.4), sb, shd, PX, style='split', L=3.5, pitch=0.7, seed=sd)
    if verbose: print(f'  knight: fills {time.time() - t0:.1f}s')
    # ---- cord outline (mask.A) -> stem stitch rope in dark warm brown
    dtc = cv2.distanceTransform(cord.astype(np.uint8), cv2.DIST_L2, 5) / PX
    paths, _ = skeleton_paths(cv2.GaussianBlur(cord.astype(np.float32), (0, 0), 0.08 * PX) > 0.5, 4)
    paths = merge_paths(paths, 0.6 * PX)
    r = np.random.default_rng(seed + 5)
    cols = [hex_lin('#3A1D12'), hex_lin('#4A2616'), P['outline_warm']]
    S.TAG[0] = ('cord', 0, 0)
    for pth in paths:
        pth = S.smooth_poly(S.resample(pth.astype(np.float32), 0.3 * PX), 3)
        if np.hypot(*np.diff(pth, axis=0).T).sum() / PX < 1.2: continue
        xi = np.clip(pth[:, 0].astype(int), 0, Wm - 1); yi = np.clip(pth[:, 1].astype(int), 0, Hm - 1)
        w = float(np.clip(2.0 * np.median(dtc[yi, xi]) + 0.45, 0.9, 1.6))
        S.cord_path(mm, pth, cols[int(r.integers(3))] * (1 + r.uniform(-0.1, 0.1)), PX, width=w, h0=0.42, hamp=0.5,
                    seed=int(r.integers(1 << 30)))
    if verbose: print(f'  knight: cord {time.time() - t0:.1f}s')
    # ---- slip alpha: silhouette + margin with frayed edge
    sil = (alpha > 0.5).astype(np.uint8)
    sil_full = np.zeros((Hb, Wb), np.uint8); sil_full[oy:oy + Hm, ox:ox + Wm] = sil
    dout = cv2.distanceTransform(1 - sil_full, cv2.DIST_L2, 5) / PX
    fray = smooth_noise((Hb, Wb), 0.8 * PX, seed + 9) * 0.35 + smooth_noise((Hb, Wb), 0.2 * PX, seed + 10) * 0.15
    slip = np.clip((margin_mm + fray - dout) * PX * 0.7, 0, 1).astype(np.float32)
    slip = np.where(sil_full > 0, 1.0, slip).astype(np.float32)      # never punch holes inside the figure
    relief_full = np.zeros((Hb, Wb), np.float32); relief_full[oy:oy + Hm, ox:ox + Wm] = hgt
    return dict(maps=m, alpha=slip, sil=sil_full.astype(bool), relief=relief_full, offset=(ox, oy), size=(Wm, Hm),
                cord=cord, lab=lab)
