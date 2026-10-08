"""Figure re-embroiderer (f899): game figure cards -> stitched figures on a bkit Canvas (laid + couched fills, split-stitch
faces, stem-stitch outlines from the card's cord mask, couched-gold shield cross).

The card (albedo + mask) is only a colour / region guide: every region is re-stitched as real strands (no sprite pixels, no cream
die-cut border).  Used twice with identical parameters: the front-rank figures are stitched into the war sheet as record
groups (so the sheet's _ground copy carries their footprints), and are later cut back out of the full sheet as the Eevee slips.

    card = load_card('legionary', 'strike', '#A3181A', flip=False, shield='#A3181A')
    info = embroider(canvas, card, x_mm=95, y_mm=282, ppm=8.0, group='slip0', seed=11)
"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bkit                                                           # noqa  (library path, threads)
import numpy as np, cv2                                               # noqa
from PIL import Image                                                 # noqa
from chron import stitch as S                                         # noqa
from chron.stitch import CTX                                          # noqa
from chron.color import srgb2lin, lin2srgb, lin2oklab, oklab2lin, hex_lin, ShadeSet, pal, LUMA   # noqa
from chron.segment import FAM, FAM_NAMES, oklab_lch, classify, components, majority            # noqa
from chron.fields import select_field, region_axis_field, const_field                          # noqa
from chron.skel import skeleton_paths, merge_paths                                              # noqa
from chron.record import OUTLINE_REGION                                                         # noqa
from chron.motifs.panel import merge_similar, _pulls                                            # noqa
from chron.config import WOOL, SILK, METAL                                                      # noqa
from bkit import geom as G                                                                      # noqa
from bkit.motifs import ink_for                                                                 # noqa

AAA = bkit.AAA
ASSETS = os.path.join(AAA, 'assets')
sys.path.insert(0, ASSETS)
import figure_tint as ft                                                                        # noqa

SHIELD, LIVERY, CORD = 40, 41, 42   # extra family ids (shield field = mask G, livery zone = mask R, cord = mask A)


def _hue_remap(rgb_lin, sel, target_hex, keep_l=True, cscale=1.0):
    """recolour the selected pixels to the hue/chroma of target_hex keeping their lightness structure."""
    lab = lin2oklab(rgb_lin)
    tl = lin2oklab(hex_lin(target_hex)[None])[0]
    ta, tb = tl[1], tl[2]
    L = lab[..., 0]
    k = np.clip(L / max(tl[0], 1e-3), 0.55, 1.5)
    out = lab.copy()
    out[..., 1] = np.where(sel, ta * k * cscale, lab[..., 1])
    out[..., 2] = np.where(sel, tb * k * cscale, lab[..., 2])
    if not keep_l:
        out[..., 0] = np.where(sel, tl[0] * (0.6 + 0.4 * L / max(L[sel].mean(), 1e-3)) if sel.any() else L, L)
    return oklab2lin(out.reshape(-1, 3)).reshape(rgb_lin.shape)


def load_card(unit, pose, team_hex, flip=False, shield=None, deep_hex=None, sat=1.15, val=0.95, redye_purple=True):
    """-> dict(lin (H,W,3) linear colour, alpha, cord, shield, livery, sheen) at card resolution (flipped if asked)."""
    im = ft.tint(unit, pose, team_hex, sat=sat, val=val, shield=shield)
    a = np.asarray(im).astype(np.float32) / 255
    rgb = srgb2lin(a[..., :3])
    alpha = a[..., 3]
    m = np.asarray(Image.open(os.path.join(ASSETS, 'tex', 'figures', f'{unit}_{pose}_mask.png')).convert('RGBA')).astype(np.float32) / 255
    m = cv2.resize(m, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_LINEAR)
    livery, shd, sheen, cord = m[..., 0], m[..., 1], m[..., 2], m[..., 3]
    # fill transparent pixels with the surrounding colour (no dark fringe when resampled)
    op = (alpha > 0.5)
    kf = op.astype(np.float32)
    fillc = cv2.GaussianBlur(rgb * kf[..., None], (0, 0), 5) / (cv2.GaussianBlur(kf, (0, 0), 5)[..., None] + 1e-4)
    rgb = np.where(op[..., None], rgb, fillc)
    if redye_purple:      # purple belongs to the king alone: the legion's purple trim becomes deep madder / deep woad
        lab = lin2oklab(rgb)
        C = np.hypot(lab[..., 1], lab[..., 2]); h = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
        sel = (C > 0.03) & (((h > 285) & (h < 350)) | (h < 4)) & (livery < 0.5) & op
        rgb = _hue_remap(rgb, sel, deep_hex or '#6E2428')
    out = dict(lin=rgb.astype(np.float32), alpha=alpha, cord=cord, shield=shd, livery=livery, sheen=sheen, unit=unit, pose=pose)
    if flip:
        for k in ('lin', 'alpha', 'cord', 'shield', 'livery', 'sheen'):
            out[k] = np.ascontiguousarray(out[k][:, ::-1])
    return out


def _upscale_labels(lab, ids, s, sigma=0.8):
    """label image (card res) -> canvas res (x s): soft one-hot, cubic upsample, argmax (rounded boundaries)."""
    H, W = lab.shape
    Hc, Wc = int(round(H * s)), int(round(W * s))
    best = np.full((Hc, Wc), -1.0, np.float32); out = np.zeros((Hc, Wc), np.int32)
    for r in ids:
        v = cv2.GaussianBlur((lab == r).astype(np.float32), (0, 0), sigma)
        v = cv2.resize(v, (Wc, Hc), interpolation=cv2.INTER_CUBIC)
        sel = v > best
        out[sel] = r; best[sel] = v[sel]
    return out, best


def embroider(c, card, x_mm, y_mm, ppm=8.0, group=None, seed=0, name='fig', shield_cross=None, min_region_mm2=1.4, cord_col=None,
              laid_big_mm2=26.0, couch_min_mm2=34.0, occlude=True, pull_amt=0.28, chroma_max=0.17, outline_w=1.0, fill_pitch=0.85,
              palette_pull=None, verbose=False, outline_mode='ink', hamp_mul=1.0, gap_prob=0.5):
    """stitch one figure into canvas c with its feet (alpha bbox bottom) at (x_mm, y_mm) and horizontal centre at x_mm.
    ppm = card px per mm.  Returns info dict (bbox_mm, silhouette mask window, region count)."""
    PX = c.PX
    s = PX / ppm
    lin = card['lin']; alpha = card['alpha']
    H0, W0 = alpha.shape
    ys, xs = np.nonzero(alpha > 0.5)
    x_ref, y_feet = 0.5 * (xs.min() + xs.max()), ys.max()
    ox = int(round(x_mm * PX - x_ref * s)); oy = int(round(y_mm * PX - y_feet * s))
    Wc, Hc = int(round(W0 * s)), int(round(H0 * s))
    win = (ox, oy, ox + Wc, oy + Hc)
    # ---------------- segmentation at card res
    u8 = (np.clip(lin2srgb(lin), 0, 1) * 255 + 0.5).astype(np.uint8)
    ms = cv2.pyrMeanShiftFiltering(cv2.cvtColor(u8, cv2.COLOR_RGB2BGR), 3, 10, maxLevel=0)
    ms = cv2.cvtColor(ms, cv2.COLOR_BGR2RGB)
    lab_, L, C, h = oklab_lch(ms)
    fam = classify(L, C, h)
    skin = (h > 18) & (h < 72) & (C > 0.022) & (C < 0.095) & (L > 0.62)
    fam[skin] = FAM['skin']
    cord = cv2.GaussianBlur(card['cord'], (0, 0), 0.6) > 0.5
    shield_m = (card['shield'] > 0.5)
    livery_m = (card['livery'] > 0.5)
    fam[cord] = CORD
    fam[shield_m & ~cord] = SHIELD
    fam[livery_m & ~cord & ~shield_m] = LIVERY
    fam = majority(np.where(alpha > 0.5, fam, FAM['bg']), 3, 1, n=64)
    fam[alpha <= 0.5] = FAM['bg']
    grp = np.where((fam == SHIELD) | (fam == LIVERY), 1, 0).astype(np.int32)
    grp[fam == CORD] = 2
    combo = fam * 64 + grp
    lab_s, info = components(combo, int(min_region_mm2 * ppm * ppm), protect={CORD})
    for rid, inf in info.items():
        inf['group'] = inf['fam'] % 64; inf['fam'] = inf['fam'] // 64
    ok = lin2oklab(lin)
    lab_s, info = merge_similar(lab_s, info, ok, 0.065)
    ids = [r for r, inf in info.items() if inf['fam'] not in (FAM['bg'], CORD)]
    lab_c, conf = _upscale_labels(lab_s, ids, s)
    sil_c = cv2.resize(cv2.GaussianBlur(alpha, (0, 0), 0.8), (Wc, Hc), interpolation=cv2.INTER_CUBIC) > 0.5
    cord_c = cv2.resize(cv2.GaussianBlur(card['cord'], (0, 0), 0.7), (Wc, Hc), interpolation=cv2.INTER_CUBIC) > 0.5
    lin_c = cv2.resize(lin, (Wc, Hc), interpolation=cv2.INTER_CUBIC).clip(0, 1)
    lum_c = (np.clip(lin_c, 0, 1) ** (1 / 2.2) * LUMA).sum(-1).astype(np.float32)
    # clip to the canvas
    cx0, cy0 = max(ox, 0), max(oy, 0)
    cx1, cy1 = min(ox + Wc, c.W), min(oy + Hc, c.H)
    gid = c.group(group) if isinstance(group, (str, type(None))) else int(group)
    pulls = _pulls()
    if palette_pull:
        pulls.update(palette_pull)
    order = [FAM[f] for f in ('navy', 'blue', 'grey', 'darkgrey', 'brown', 'purple', 'red', 'darkred', 'green', 'orange', 'buff', 'ermine',
                              'gold', 'skin', 'light', 'white', 'ink', 'metal', 'jewel', 'flame')] + [SHIELD, LIVERY]
    rids = sorted(ids, key=lambda r: (order.index(info[r]['fam']) if info[r]['fam'] in order else 99, -info[r]['area']))
    nreg = 0; stats = {}
    occ_free = ~c.occ                                   # nearer elements already stitched are never overwritten
    for rid in rids:
        f = info[rid]['fam']
        mk_full = (lab_c == rid) & sil_c & ~cord_c
        if not mk_full.any():
            continue
        yy, xx = np.nonzero(mk_full)
        x0, y0, x1, y1 = max(xx.min() - 14, 0), max(yy.min() - 14, 0), min(xx.max() + 15, Wc), min(yy.max() + 15, Hc)
        # canvas window
        wx0, wy0, wx1, wy1 = max(ox + x0, 0), max(oy + y0, 0), min(ox + x1, c.W), min(oy + y1, c.H)
        if wx1 <= wx0 or wy1 <= wy0:
            continue
        sx0, sy0 = wx0 - ox, wy0 - oy
        mk = mk_full[sy0:sy0 + (wy1 - wy0), sx0:sx0 + (wx1 - wx0)] & occ_free[wy0:wy1, wx0:wx1]
        area = float(mk.sum()) / PX / PX
        if area < 0.5:
            continue
        sb_lin = lin_c[sy0:sy0 + (wy1 - wy0), sx0:sx0 + (wx1 - wx0)]
        lum = lum_c[sy0:sy0 + (wy1 - wy0), sx0:sx0 + (wx1 - wx0)]
        sb = cv2.GaussianBlur(sb_lin, (0, 0), 0.28 * PX)
        pix = sb_lin[mk]
        sd = seed * 1000 + int(rid)
        sub = S.view(c.m, wx0, wy0, wx1, wy1)
        rr = c.new_region(dict(name=f'{name}_{FAM_NAMES.get(f, f)}', group=gid, style='fig'))
        lab_r = np.where(mk, rr, -1).astype(np.int32)
        CTX['region'] = rr; CTX['group'] = gid; CTX['unit'] = -1
        origin = (wx0 / PX, wy0 / PX)
        nsh = int(np.clip(area / 14, 2, 5))
        pull = pulls.get(f, pulls[FAM['brown']]) if f not in (SHIELD, LIVERY) else None
        pa = pull_amt if f not in (FAM['red'], FAM['blue'], FAM['navy'], FAM['darkred'], SHIELD, LIVERY) else 0.1
        cmax = 0.20 if f in (SHIELD, LIVERY, FAM['red'], FAM['darkred'], FAM['blue'], FAM['navy']) else chroma_max
        if f == FAM['skin']:
            shd = ShadeSet.from_pixels(pix, max(nsh, 4), pulls[FAM['skin']], 0.3, sd, chroma_max=0.12)
            fld, md = select_field(lum, mk, PX, mode='blend', w_shape=0.15, sig_t_mm=0.9)
            S.fill_region(sub, lab_r, rr, fld, sb, shd, PX, style='split', L=2.0, pitch=0.42, seed=sd, h0=0.05, hamp=0.28 * hamp_mul,
                          r_fac=0.62, ply_mm=0.45, taper=0.3, minlen=0.5)
        elif f in (FAM['metal'],):
            fld, md = select_field(lum, mk, PX, mode='contour')
            S.metal_couch(sub, lab_r, rr, fld, PX, pitch=0.9, seed=sd)
        elif area >= laid_big_mm2 or f in (SHIELD, LIVERY):
            shd = ShadeSet.from_pixels(pix, nsh, pull, pa, sd, chroma_max=cmax)
            ang = None
            fld, md = select_field(lum, mk, PX, mode='auto', laid=True, angle_deg=ang, seed=sd, origin_mm=origin, sig_t_mm=4.0,
                                   w_shape=0.3, bend_deg=14.0)
            cp = dict(spacing=3.6, tie=3.2) if area >= couch_min_mm2 else None
            S.fill_region(sub, lab_r, rr, fld, sb, shd, PX, style='laid', pitch=fill_pitch, seed=sd, couch=cp, h0=0.05, hamp=0.42 * hamp_mul,
                          maxturn_deg=35 if md == 'axis' else 50, minlen=0.6, maxlen=40)
        else:
            shd = ShadeSet.from_pixels(pix, nsh, pull, pa, sd, chroma_max=cmax)
            fld, md = select_field(lum, mk, PX, mode='blend', laid=False, seed=sd, origin_mm=origin, sig_t_mm=1.4, w_shape=0.4)
            S.fill_region(sub, lab_r, rr, fld, sb, shd, PX, style='split', L=3.2, pitch=0.72, seed=sd, h0=0.06, hamp=0.4 * hamp_mul, minlen=0.5)
        stats[md] = stats.get(md, 0) + 1
        sub['base'][:] = np.where(mk, 0, sub['base'])
        nreg += 1
        CTX['region'] = 0
    if verbose:
        print(f'[{name}] {nreg} regions, fields {stats}', flush=True)
    # ---------------- stem-stitch outline along the cord skeleton (silhouette + internal lines)
    ink = cord_c & ((cv2.dilate(sil_c.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0))
    ink = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    dt = cv2.distanceTransform(ink, cv2.DIST_L2, 5) / PX
    paths, _ = skeleton_paths(ink > 0, 4)
    paths = merge_paths(paths, 0.35 * PX)
    r = np.random.default_rng(seed + 77)
    CTX['region'] = OUTLINE_REGION; CTX['group'] = gid
    nst = 0
    tonal = (outline_mode == 'tonal')
    if tonal:       # fill colour next to the cord: the card colour with the cord pixels filled in from their neighbours
        keep = (sil_c & ~(cv2.dilate(ink.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0)).astype(np.float32)
        sg = 0.5 * PX
        loc_num = cv2.GaussianBlur(lin_c * keep[..., None], (0, 0), sg); loc_den = cv2.GaussianBlur(keep, (0, 0), sg)[..., None] + 1e-4

    def run_colour(ix, iy):
        if not tonal:
            return hex_lin('#33201A')
        c0 = np.median((loc_num / loc_den)[iy, ix], 0)
        lb = lin2oklab(c0[None].astype(np.float32))[0]
        lb[0] = max(0.21, lb[0] * 0.64); lb[1] *= 0.95; lb[2] *= 0.95
        return oklab2lin(lb[None])[0]
    for pth in paths:
        pth = S.smooth_poly(S.resample(pth.astype(np.float32), 0.3 * PX), 3)
        if len(pth) < 3:
            continue
        ln_mm = float(np.hypot(*np.diff(pth, axis=0).T).sum()) / PX
        if ln_mm < 1.1:
            continue
        # break the line: runs of 8-26 mm with gaps of 0.7-2.0 mm (the fill thread overruns), tonal outlines only
        segs = [pth]
        if tonal and ln_mm > 6.0 and gap_prob > 0:
            segs = []; pos = 0; seg_len = np.hypot(*np.diff(pth, axis=0).T); cum = np.concatenate([[0], np.cumsum(seg_len)]) / PX
            while pos < ln_mm - 0.8:
                a = pos; b = min(pos + r.uniform(8.0, 26.0), ln_mm)
                ia, ib = np.searchsorted(cum, a), np.searchsorted(cum, b)
                if ib - ia >= 3:
                    segs.append(pth[ia:ib + 1])
                pos = b + (r.uniform(0.7, 2.0) if r.random() < gap_prob else 0.0)
        for sg_ in segs:
            if len(sg_) < 3:
                continue
            xi = np.clip(sg_[:, 0].astype(int), 0, Wc - 1); yi = np.clip(sg_[:, 1].astype(int), 0, Hc - 1)
            w = float(np.clip(2.0 * np.median(dt[yi, xi]) * 0.9 + 0.2, 0.55, 1.35)) * outline_w * (0.66 if tonal else 1.0)
            col = run_colour(xi, yi)
            pc = sg_ + np.array([ox, oy], np.float32)
            S.stem_path(c.m, pc, col * (1 + r.uniform(-0.08, 0.08)), PX, L=2.6, width=max(w, 0.45), h0=0.5, hamp=0.4, seed=int(r.integers(1 << 30)), cov=0.5)
            nst += 1
    CTX['region'] = 0
    # ---------------- shield device
    if shield_cross is not None and shield_m.any():
        sy, sx = np.nonzero(shield_m)
        scx, scy = (sx.min() + sx.max()) / 2 * s + ox, (sy.min() + sy.max()) / 2 * s + oy
        sw, sh_ = (sx.max() - sx.min()) * s, (sy.max() - sy.min()) * s
        kind = shield_cross.get('kind', 'cross')
        arm_h, arm_w = 0.34 * sh_ / PX, 0.30 * sw / PX
        cm = (scx / PX, scy / PX)
        if kind == 'cross':
            vline = np.array([[cm[0], cm[1] - arm_h], [cm[0], cm[1] + arm_h]], np.float32)
            hline = np.array([[cm[0] - arm_w, cm[1] - 0.04 * arm_h], [cm[0] + arm_w, cm[1] - 0.04 * arm_h]], np.float32)
            for k, ln in enumerate((vline, hline)):
                c.metal_pair(ln, ties_s_mm=list(np.arange(1.6, G.arclen(ln)[-1], 3.0)), tie_col=shield_cross.get('tie', '#5A1410'),
                             group=group, gold=shield_cross.get('gold'), sep_mm=0.62, thread_r=0.27, seed=seed + 5 + k, tie_len_mm=1.5, tie_r=0.15)
        elif kind == 'chevron':
            pts = np.array([[cm[0] - arm_w, cm[1] - 0.25 * arm_h], [cm[0], cm[1] + 0.2 * arm_h], [cm[0] + arm_w, cm[1] - 0.25 * arm_h]], np.float32)
            c.outline_mm(pts, shield_cross.get('col', '#D6BE86'), width=1.3, L=2.4, seed=seed + 9, group=group, clip=False)
    # ---------------- occlusion for what is stitched behind (front-to-back)
    sil_win = np.zeros((c.H, c.W), bool)
    if occlude:
        k = max(1, int(0.25 * PX))
        sdil = cv2.dilate(sil_c.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))) > 0
        c.occ[cy0:cy1, cx0:cx1] |= sdil[cy0 - oy:cy1 - oy, cx0 - ox:cx1 - ox]
    return dict(win=win, bbox_mm=(ox / PX, oy / PX, (ox + Wc) / PX, (oy + Hc) / PX), regions=nreg, outlines=nst, feet_mm=(x_mm, y_mm),
                sil=sil_c, ox=ox, oy=oy)
