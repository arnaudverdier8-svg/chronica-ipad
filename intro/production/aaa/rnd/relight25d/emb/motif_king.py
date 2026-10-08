"""M1: re-embroider the king crop of p1_oath.png (x1100-1700, y380-1000; 5 px/mm panel-native)."""
import math, time
import numpy as np, cv2
from .core import *
from .segment import FAM, oklab_lch, majority, components
from . import stitch as S
from .skel import skeleton_paths, merge_paths

SRC = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/intro/p1_oath.png'
CROP = (1100, 380, 1700, 1000)
SRC_PX = 5.0
# art-direction hints in crop pixel coords
BEARD = np.array([(205, 200), (160, 240), (138, 300), (148, 352), (185, 372), (205, 398), (228, 428), (265, 447), (305, 449),
                  (347, 430), (366, 398), (398, 376), (442, 348), (447, 290), (422, 236), (388, 200)], np.int32)
FACE_C, FACE_AX = (285, 262), (68, 55)
METAL_BOXES = [(170, 40, 385, 220), (160, 398, 378, 532)]
GOLD_OK = [(40, 0, 520, 168), (170, 40, 385, 220), (160, 398, 378, 532), (228, 425, 322, 620), (0, 470, 600, 620)]
ARCH = dict(x0=18, x1=582, cy=298, r=282, y1=618)


def arch_mask(shape, scale=1.0, inset=0.0):
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32) / scale
    a = ARCH; cx = (a['x0'] + a['x1']) / 2
    inside = (xx > a['x0'] + inset) & (xx < a['x1'] - inset) & (yy < a['y1'] - inset)
    top = (yy < a['cy']) & (np.hypot(xx - cx, yy - a['cy']) > a['r'] - inset)
    return inside & ~top


def arch_poly(scale, inset=0.0, n=200):
    a = ARCH; cx = (a['x0'] + a['x1']) / 2; r = a['r'] - inset
    angs = np.linspace(math.pi, 2 * math.pi, n)
    arc = np.stack([cx + r * np.cos(angs), a['cy'] + r * np.sin(angs)], 1)
    p = np.vstack([[a['x0'] + inset, a['y1'] - inset], arc, [a['x1'] - inset, a['y1'] - inset], [a['x0'] + inset, a['y1'] - inset]])
    return (p * scale).astype(np.float32)


def segment_king():
    src = load_rgba(SRC)[CROP[1]:CROP[3], CROP[0]:CROP[2], :3].copy()
    ms = cv2.pyrMeanShiftFiltering(cv2.cvtColor(src, cv2.COLOR_RGB2BGR), 5, 16, maxLevel=1)
    ms = cv2.bilateralFilter(cv2.cvtColor(ms, cv2.COLOR_BGR2RGB), 7, 30, 5)
    lab, L, C, h = oklab_lch(ms)
    H, W = L.shape
    yy, xx = np.mgrid[0:H, 0:W]
    hue = lambda a, b: ((h - a) % 360) <= ((b - a) % 360)
    def inbox(boxes):
        mk = np.zeros((H, W), bool)
        for x0, y0, x1, y1 in boxes: mk[y0:y1, x0:x1] = True
        return mk
    beard = np.zeros((H, W), np.uint8); cv2.fillPoly(beard, [BEARD], 1); beard = beard > 0
    face = ((xx - FACE_C[0]) / FACE_AX[0]) ** 2 + ((yy - FACE_C[1]) / FACE_AX[1]) ** 2 < 1
    fam = np.full((H, W), FAM['brown'], np.int32)
    fam[(C < 0.045) & (L > 0.5)] = FAM['light']
    fam[(C < 0.04) & (L >= 0.25) & (L <= 0.5)] = FAM['midgrey']
    fam[hue(180, 275) & (C >= 0.012) & (L < 0.62) & (L > 0.25)] = FAM['blue']
    fam[hue(290, 25) & (C >= 0.03) & (L < 0.66)] = FAM['purple']
    crown = inbox([METAL_BOXES[0]])
    fam[crown & hue(340, 40) & (C > 0.08) & (L < 0.6)] = FAM['red']
    fam[hue(48, 105) & (C >= 0.075) & (L >= 0.53) & inbox(GOLD_OK)] = FAM['gold']
    ink = ((L < 0.25) & (C < 0.045)) | (L < 0.17)
    fam[ink] = FAM['ink']
    fam[(C > 0.12) & ~hue(40, 105) & (L > 0.3) & inbox(METAL_BOXES)] = FAM['jewel']
    fam[face & hue(25, 80) & (C > 0.035) & (L > 0.5)] = FAM['skin']
    # linen ground: flood from border over linen-coloured pixels, never into beard / ermine zone
    sh = np.zeros((H, W), np.uint8)
    cv2.fillPoly(sh, [np.array([(30, 620), (25, 470), (60, 400), (150, 350), (230, 335), (370, 335), (455, 355), (520, 400),
                               (560, 470), (585, 560), (600, 620)], np.int32)], 1)
    keep_out = beard | (sh > 0) | face
    lin_like = (L > 0.70) & (C < 0.08) & (C > 0.015) & hue(50, 105) & ~keep_out
    nc, cc = cv2.connectedComponents(lin_like.astype(np.uint8))
    border = set(np.unique(np.concatenate([cc[0], cc[-1], cc[:, 0], cc[:, -1]]))) - {0}
    # also any big linen-like component (enclosed linen windows, e.g. inside the banner V)
    big = [c for c in range(1, nc) if (cc == c).sum() > 400]
    fam[np.isin(cc, list(border | set(big)))] = FAM['bg']
    fam = majority(fam, 5, 2, n=21)
    # midgrey -> light inside beard/ermine; elsewhere midgrey stays (throne shadow)
    fam[(fam == FAM['midgrey']) & (beard | (yy > 335))] = FAM['light']
    # light outside beard and below 335 -> ermine
    fam[(fam == FAM['light']) & ~beard & ~face & (yy > 300) & (sh > 0)] = FAM['ermine']
    fam[(fam == FAM['gold']) & inbox(METAL_BOXES)] = FAM['metal']
    fam[~arch_mask((H, W))] = FAM['bg']
    return src, ms, fam, dict(beard=beard, face=face)


def build_king(m, ox, oy, seed=0, verbose=True, stats=None):
    """Re-embroider the king into maps m (views ok) with crop origin at canvas px (ox, oy)."""
    PX = m['PX']; sc = PX / SRC_PX
    t0 = time.time()
    src, ms, fam_s, hints = segment_king()
    Hs, Ws = fam_s.shape
    Hm, Wm = int(round(Hs * sc)), int(round(Ws * sc))
    # upsample labels with a soft vote (smooth edges at map res)
    fam = cv2.resize(fam_s.astype(np.uint8), (Wm, Hm), interpolation=cv2.INTER_NEAREST).astype(np.int32)
    fam = majority(fam, 5, 1, n=21)
    src_lin = srgb2lin(cv2.resize(src, (Wm, Hm), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255)
    src_blur = cv2.GaussianBlur(src_lin, (0, 0), 0.45 * PX)
    lum = cv2.cvtColor((np.clip(src_lin, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    lab, info = components(fam, int(1.2 * PX * PX))
    beard = cv2.resize(hints['beard'].astype(np.uint8), (Wm, Hm), interpolation=cv2.INTER_NEAREST) > 0
    face = cv2.resize(hints['face'].astype(np.uint8), (Wm, Hm), interpolation=cv2.INTER_NEAREST) > 0
    mm = {k: (v[oy:oy + Hm, ox:ox + Wm] if isinstance(v, np.ndarray) else v) for k, v in m.items()}
    if verbose: print(f'  king: segment+setup {time.time() - t0:.1f}s, {len(info)} regions')
    P = {k: hex_lin(v['hex']) for k, v in PAL['cinematic'].items()}
    pulls = {
        FAM['purple']: [P['royal_purple'], P['royal_purple_hi'], P['madder_dark'], hex_lin('#2E1A36')],
        FAM['red']: [P['crimson'], P['crimson_hi'], P['crimson_deep']],
        FAM['gold']: [P['gold'], P['gold_hi'], P['gold_lo'], P['mustard']],
        FAM['brown']: [P['madder_dark'], P['gold_lo'], P['gold_deep'], hex_lin('#5A3A22'), hex_lin('#8A6238')],
        FAM['skin']: [P['flesh_fill'], P['linen_hi'], P['flesh_line'], P['terracotta']],
        FAM['light']: [P['linen_hi'], P['steel'], P['steel_lo'], hex_lin('#EFE8DA')],
        FAM['ermine']: [P['linen_hi'], hex_lin('#EFE8DA'), P['buff']],
        FAM['blue']: [P['woad'], P['woad_dark']],
        FAM['midgrey']: [P['steel_lo'], P['woad_dark']],
        FAM['ink']: [P['ink_blueblack'], hex_lin('#1A1418')],
        FAM['jewel']: [P['crimson'], P['heraldic_green'], P['royal_blue'], P['crimson_hi']],
        FAM['metal']: [P['metal_gold_f0']],
    }
    order = [FAM['blue'], FAM['midgrey'], FAM['brown'], FAM['purple'], FAM['red'], FAM['ermine'], FAM['gold'], FAM['skin'],
             FAM['light'], FAM['ink'], FAM['metal'], FAM['jewel']]
    rids = sorted(info.keys(), key=lambda r: (order.index(info[r]['fam']) if info[r]['fam'] in order else 99, -info[r]['area']))
    cnt = {}
    for rid in rids:
        f = info[rid]['fam']
        if f == FAM['bg']: continue
        mk = lab == rid
        ys, xs = np.nonzero(mk)
        if len(ys) < 0.6 * PX * PX: continue
        area_mm2 = len(ys) / PX / PX
        y0, y1 = max(ys.min() - 30, 0), min(ys.max() + 31, Hm); x0, x1 = max(xs.min() - 30, 0), min(xs.max() + 31, Wm)
        sub = {k: (v[y0:y1, x0:x1] if isinstance(v, np.ndarray) and v.ndim >= 2 else v) for k, v in mm.items()}
        lab_c = lab[y0:y1, x0:x1]; mk_c = mk[y0:y1, x0:x1]
        lum_c = lum[y0:y1, x0:x1]; sb = src_blur[y0:y1, x0:x1]
        cy, cx = ys.mean(), xs.mean()
        in_face = face[int(cy), int(cx)]
        in_beard = beard[int(cy), int(cx)]
        pix = src_lin[mk]
        sd = seed * 1000 + rid
        # thread direction field: source strands (structure tensor) blended with region shape
        def field(sig_t, w_shape=0.25):
            a = S.orient_tensor(lum_c, 0.35 * PX, sig_t * PX, mask=mk_c)
            mb = cv2.GaussianBlur(mk_c.astype(np.float32), (0, 0), 1.5 * PX)
            b = S.orient_tensor(mb, 0.5 * PX, 2.5 * PX, mask=mk_c)
            return S.blend_fields([a, b], [1.0, w_shape])
        nsh = int(np.clip(area_mm2 / 40, 2, 6))
        if f == FAM['metal']:
            fld = field(2.5, 0.6)
            S.metal_couch(sub, lab_c, rid, fld, PX, pitch=1.0, seed=sd, tarnish=0.08)
        elif f == FAM['jewel']:
            pad = S.pad_dome(mk_c, PX, 1.2, 1.2)
            sub['base'][:] = np.maximum(sub['base'], pad)
            shd = S.ShadeSet.from_pixels(pix, 2, pulls[f], 0.5, sd)
            S.fill_region(sub, lab_c, rid, field(1.0, 1.0), sb, shd, PX, style='laid', pitch=0.45, seed=sd, matid=SILK,
                          h0=0.05, hamp=0.3, r_fac=0.6, maxlen=12)
            sub['base'][:] = np.where(mk_c, 0, sub['base'])
        elif f == FAM['ink']:
            thick = cv2.morphologyEx(mk_c.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(1.6 * PX), int(1.6 * PX))))
            if thick.sum() < 2 * PX * PX: continue
            lab_c = np.where(thick > 0, rid, -1).astype(np.int32)
            fld = field(0.8, 1.2)
            shd = S.ShadeSet.from_pixels(pix, 2, pulls[f], 0.6, sd)
            S.fill_region(sub, lab_c, rid, fld, sb, shd, PX, style='split', L=3.2, pitch=0.85, seed=sd, h0=0.18,
                          hamp=0.42, r_fac=0.62, tw_deg=15, maxlen=60, minlen=0.6, hbias=0.15)
        elif f == FAM['skin'] or in_face:
            shd = S.ShadeSet.from_pixels(pix, max(nsh, 4), pulls.get(f, pulls[FAM['skin']]), 0.3, sd)
            S.fill_region(sub, lab_c, rid, field(1.0, 0.15), sb, shd, PX, style='split', L=2.2, pitch=0.45, seed=sd,
                          h0=0.05, hamp=0.28, r_fac=0.62, ply_mm=0.45, taper=0.3)
        elif f == FAM['light'] and in_beard:
            shd = S.ShadeSet.from_pixels(pix, 5, pulls[FAM['light']], 0.3, sd)
            S.fill_region(sub, lab_c, rid, field(1.2, 0.1), sb, shd, PX, style='split', L=6.5, pitch=0.6, seed=sd,
                          h0=0.08, hamp=0.36, r_fac=0.6)
        elif f in (FAM['purple'], FAM['red'], FAM['ermine'], FAM['blue']) and area_mm2 > 60:
            shd = S.ShadeSet.from_pixels(pix, nsh, pulls[f], 0.35, sd)
            S.fill_region(sub, lab_c, rid, field(5.0, 0.3), sb, shd, PX, style='laid', pitch=0.85, seed=sd,
                          couch=dict(spacing=4.5, tie=4.0), h0=0.05, hamp=0.42)
        elif f == FAM['gold'] and area_mm2 > 60:
            shd = S.ShadeSet.from_pixels(pix, nsh, pulls[f], 0.55, sd)
            S.fill_region(sub, lab_c, rid, field(2.0, 0.6), sb, shd, PX, style='laid', pitch=0.75, seed=sd,
                          couch=dict(spacing=3.5, tie=3.0), h0=0.05, hamp=0.42)
        else:
            shd = S.ShadeSet.from_pixels(pix, nsh, pulls.get(f, pulls[FAM['brown']]), 0.3, sd)
            S.fill_region(sub, lab_c, rid, field(1.6, 0.4), sb, shd, PX, style='split', L=4.0, pitch=0.7, seed=sd,
                          h0=0.06, hamp=0.4)
        cnt[f] = cnt.get(f, 0) + 1
    if verbose: print(f'  king: fills done {time.time() - t0:.1f}s')
    # ---- stem-stitch outlines from the source's dark lines (skeletons)
    g = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    gs = cv2.GaussianBlur(g, (0, 0), 0.7)
    bh = cv2.morphologyEx(gs, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
    thr = np.where(hints['beard'] & ~hints['face'], 0.17, 0.11)
    ln = ((bh > thr) & (gs < 0.45)) | (fam_s == FAM['ink'])
    ln &= arch_mask(g.shape) & (fam_s != FAM['bg'])
    ln = cv2.morphologyEx(ln.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    up = cv2.GaussianBlur(cv2.resize(ln.astype(np.float32), (Wm, Hm), interpolation=cv2.INTER_LINEAR), (0, 0), 0.1 * PX) > 0.45
    dt = cv2.distanceTransform(up.astype(np.uint8), cv2.DIST_L2, 5) / PX
    paths, _ = skeleton_paths(up, 4)
    paths = merge_paths(paths, 0.3 * PX)
    src_dark = cv2.erode(src_lin, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(0.6 * PX) | 1, int(0.6 * PX) | 1)))
    def ink_for(c, inf):
        lb = lin2oklab(np.asarray(c, np.float32)[None])[0]
        C = math.hypot(lb[1], lb[2]); hh = math.degrees(math.atan2(lb[2], lb[1])) % 360
        if inf: base = hex_lin('#55291D')
        elif C > 0.03 and (hh > 290 or hh < 20): base = hex_lin('#2A1730')
        elif C > 0.035 and 20 <= hh < 100: base = hex_lin('#3A1D12') if lb[0] < 0.4 else hex_lin('#5C2C1C')
        else: base = P['ink_blueblack']
        return base * 0.8 + np.clip(c, 0, 1) * 0.2
    r = np.random.default_rng(seed + 11)
    nst = 0
    for pth in paths:
        pth = S.smooth_poly(S.resample(pth.astype(np.float32), 0.3 * PX), 3)
        ln_mm = np.hypot(*np.diff(pth, axis=0).T).sum() / PX
        xi = np.clip(pth[:, 0].astype(int), 0, Wm - 1); yi = np.clip(pth[:, 1].astype(int), 0, Hm - 1)
        inf = face[yi, xi].mean() > 0.5
        if ln_mm < (0.8 if inf else 1.5): continue
        w = float(np.clip(2.0 * np.median(dt[yi, xi]) + 0.25, 0.55 if inf else 0.8, 1.7))
        col = ink_for(S.sample_col(src_dark, pth), inf) * (1 + r.uniform(-0.08, 0.08))
        S.stem_path(mm, pth, col, PX, L=(2.2 if inf else 3.3), width=w, h0=(0.3 if inf else 0.5), hamp=(0.3 if inf else 0.42),
                    seed=int(r.integers(1 << 30)))
        nst += 1
    if verbose: print(f'  king: {nst} outlines {time.time() - t0:.1f}s')
    # arch border: two stem-stitch lines (blue-black outside, red-brown inside) + inner couched gold line
    S.stem_path(mm, arch_poly(sc, -2.0), hex_lin(PAL['cinematic']['ink_blueblack']['hex']), PX, seed=seed + 7, width=1.4)
    S.stem_path(mm, arch_poly(sc, 2.6), hex_lin(PAL['cinematic']['ink_redbrown']['hex']), PX, seed=seed + 8, width=1.3)
    if verbose: print(f'  king: done {time.time() - t0:.1f}s')
    alpha = arch_mask((Hm, Wm), sc, -4.0)
    return dict(lab=lab, info=info, fam=fam, alpha=alpha, shape=(Hm, Wm), origin=(ox, oy), src=src_lin)
