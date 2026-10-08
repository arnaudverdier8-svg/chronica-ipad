"""Whole-panel re-embroidery (p1 / p3 / p6) into a MapSet: the tiled, generalised version of R25 motif_king.

Pipeline: inpaint painted glows -> OKLCh family segmentation (+ hint zones) -> regions (cut by group polygons) ->
per-region recipe (laid+couched / split / metal / ermine / satin) with the G6 field decision -> stem outlines from
dark lines (suppressed in busy zones) -> RECORD -> needle-path order -> ghost (protected linen, needle holes at the
real strand ends, red-brown underdrawing) under every group -> exact replay -> MapSets:
   <sheet>          everything (Act I state)
   <sheet>_ground   without the hint groups (king, crown, goblets, candles ...) but with their ghosts
   + stitches.npz (record, order, groups), layers (age_*), group masks."""
import os, json, time, math
import numpy as np, cv2
from .. import stitch as S
from ..stitch import Record, CTX
from ..color import srgb2lin, lin2oklab, oklab2lin, hex_lin, pal, ShadeSet, LUMA
from ..segment import FAM, FAM_NAMES, NFAM, oklab_lch, classify, components, majority, poly_mask, ellipse_mask, box_mask, hue_in
from ..fields import select_field, orient_tensor, blend_fields, region_axis_field, const_field
from ..skel import skeleton_paths, merge_paths
from ..linen import make_linen
from ..record import replay, needle_order, apply_flips, blank_like, OUTLINE_REGION
from ..maps import MapSet
from ..ageing import bake_age_layers
from ..config import SRC_PX, WOOL, SILK, METAL, LINEN, sheet_dir
from ..util import bbox


# ------------------------------------------------------------------ glows
def inpaint_glows(src_u8, glows):
    """remove painted candle glows: radial per-channel gain profile measured on background-like pixels around each
    flame, divided out (flame core kept)."""
    lin = srgb2lin(src_u8.astype(np.float32) / 255)
    H, W, _ = lin.shape
    for g in glows:
        cx, cy = g['c']; R = g['r']; rf = g['r_flame']
        x0, y0, x1, y1 = max(int(cx - R - 40), 0), max(int(cy - R - 40), 0), min(int(cx + R + 40), W), min(int(cy + R + 40), H)
        sub = lin[y0:y1, x0:x1]
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        d = np.hypot(xx - cx, yy - cy)
        lab = lin2oklab(sub)
        L = lab[..., 0]; C = np.hypot(lab[..., 1], lab[..., 2])
        hh = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
        bgm = (C < 0.14) & (L > 0.55) & (hh > 40) & (hh < 115)
        ann = bgm & (d > R) & (d < R + 40)
        if ann.sum() < 50: continue
        base = np.median(sub[ann], 0)
        prof = np.ones((int(R) + 41, 3), np.float32)
        for r in range(int(rf), int(R) + 1, 3):
            ring = bgm & (d >= r) & (d < r + 3)
            if ring.sum() > 15:
                prof[r:r + 3] = np.median(sub[ring], 0) / (base + 1e-6)
        for c in range(3):
            prof[:, c] = cv2.GaussianBlur(prof[:, c][None], (0, 0), 4).ravel()
        prof = np.maximum(prof, 1.0)
        valid = np.nonzero(np.abs(prof - 1).sum(1) > 1e-4)[0]
        if len(valid):
            prof[: valid[0]] = prof[valid[0]]
        di = np.clip(d.astype(int), 0, len(prof) - 1)
        gain = prof[di]
        w = np.clip((d - rf * 0.9) / (rf * 0.6), 0, 1)[..., None]          # keep the flame core itself
        w *= np.clip((R + 30 - d) / 30, 0, 1)[..., None]
        lin[y0:y1, x0:x1] = sub / (1 + (gain - 1) * w)
    from ..color import lin2srgb
    return (lin2srgb(lin) * 255 + 0.5).astype(np.uint8)


# ------------------------------------------------------------------ segmentation
def segment_panel(src, H):
    """family map at source res with hint rules."""
    Hs, Ws = src.shape[:2]
    ms = cv2.pyrMeanShiftFiltering(cv2.cvtColor(src, cv2.COLOR_RGB2BGR), 5, 16, maxLevel=1)
    ms = cv2.bilateralFilter(cv2.cvtColor(ms, cv2.COLOR_BGR2RGB), 7, 30, 5)
    lab, L, C, h = oklab_lch(ms)
    fam = classify(L, C, h)
    faces = ellipse_mask((Hs, Ws), H.get('faces', []))
    beard = poly_mask((Hs, Ws), H.get('beards', []))
    metal = box_mask((Hs, Ws), H.get('metal', []))
    ermine = poly_mask((Hs, Ws), H.get('ermine', []))
    gpolys = {g['name']: poly_mask((Hs, Ws), [g['poly']]) for g in H.get('groups', [])}
    for gname in H.get('metal_groups', []):
        if gname in gpolys: metal |= gpolys[gname]
    if H.get('metal_candles'):
        for gname, gm in gpolys.items():
            if gname.startswith('candle'):
                metal |= gm & (fam == FAM['gold'])
    fam[faces & hue_in(h, 25, 85) & (C > 0.03) & (L > 0.48)] = FAM['skin']
    # linen ground: flood from the border over linen-like pixels (+ big linen-like windows), never into beards / faces
    keep_out = beard | faces | ermine | poly_mask((Hs, Ws), H.get('keep_out_bg', []))
    lin_like = (L > 0.68) & (C < 0.085) & (C > 0.008) & hue_in(h, 45, 110) & ~keep_out
    lin_like = cv2.morphologyEx(lin_like.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    nc, cc, st, _ = cv2.connectedComponentsWithStats(lin_like.astype(np.uint8))
    border = set(np.unique(np.concatenate([cc[0], cc[-1], cc[:, 0], cc[:, -1]]))) - {0}
    big = {c for c in range(1, nc) if st[c, 4] > H.get('bg_big_px', 3000)}
    bg = np.isin(cc, list(border | big))
    fam[bg] = FAM['bg']
    for z in H.get('zones', []):
        if z.get('as_bg_if_linen'):
            zm = poly_mask((Hs, Ws), [z['poly']])
            fam[zm & lin_like] = FAM['bg']
        if z.get('remap'):
            zm = poly_mask((Hs, Ws), [z['poly']])
            fam[zm & np.isin(fam, [FAM[f] for f in z.get('families', [])])] = FAM[z['remap']]
        if z.get('force_bg'):
            zm = poly_mask((Hs, Ws), [z['poly']])
            fam[zm & np.isin(fam, [FAM[f] for f in z.get('families', [])])] = FAM['bg']
    fam = majority(fam, 5, 2, n=NFAM)
    fam[(fam == FAM['grey']) & beard] = FAM['light']
    fam[(fam == FAM['white']) & beard] = FAM['light']
    fam[((fam == FAM['light']) | (fam == FAM['white']) | (fam == FAM['buff'])) & ermine] = FAM['ermine']
    fam[(fam == FAM['gold']) & metal] = FAM['metal']
    fam[(fam == FAM['orange']) & metal] = FAM['metal']
    return ms, fam, dict(faces=faces, beard=beard, metal=metal, ermine=ermine, gpolys=gpolys, L=L, C=C, h=h)


# ------------------------------------------------------------------ region merging
NOMERGE = None


def merge_similar(lab, info, oklab_img, thr=0.075):
    """union adjacent regions of 'laid' families within the same group whose mean OKLab colours are within thr
    (one garment = one laid region with several dye lots, instead of a patchwork of family fragments)."""
    nomerge = {FAM['bg'], FAM['ink'], FAM['metal'], FAM['skin'], FAM['jewel'], FAM['ermine']}
    n = int(lab.max()) + 1
    cnt = np.bincount(lab.ravel(), minlength=n).astype(np.float64)
    mean = np.stack([np.bincount(lab.ravel(), weights=oklab_img[..., c].ravel(), minlength=n) for c in range(3)], 1) / np.maximum(cnt, 1)[:, None]
    a = np.concatenate([lab[:, :-1].ravel(), lab[:-1, :].ravel()]); b = np.concatenate([lab[:, 1:].ravel(), lab[1:, :].ravel()])
    d = a != b
    pairs = np.unique(np.stack([np.minimum(a[d], b[d]), np.maximum(a[d], b[d])], 1), axis=0)
    parent = np.arange(n)
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    w = {}
    for i, j in pairs:
        if i == 0 or j == 0 or i not in info or j not in info: continue
        fi, fj = info[i], info[j]
        if fi['fam'] in nomerge or fj['fam'] in nomerge or fi['group'] != fj['group']: continue
        dd = mean[i] - mean[j]
        dE = float(np.sqrt(dd[0] ** 2 + (1.4 * dd[1]) ** 2 + (1.4 * dd[2]) ** 2))
        if dE < thr:
            ri, rj = find(i), find(j)
            if ri != rj:
                # running colour of the merged set
                ci, cj = cnt[ri], cnt[rj]
                mean[ri] = (mean[ri] * ci + mean[rj] * cj) / (ci + cj); cnt[ri] = ci + cj
                parent[rj] = ri
    roots = np.array([find(x) for x in range(n)])
    lab2 = roots[lab].astype(np.int32)
    info2 = {}
    for rid, inf in info.items():
        r = int(roots[rid])
        if r not in info2:
            info2[r] = dict(fam=info[r]['fam'] if r in info else inf['fam'], group=inf['group'], area=0, bbox=inf['bbox'], famarea={})
        t = info2[r]
        t['area'] += inf['area']
        t['famarea'][inf['fam']] = t['famarea'].get(inf['fam'], 0) + inf['area']
        bx0, by0, bx1, by1 = t['bbox']; ax0, ay0, ax1, ay1 = inf['bbox']
        t['bbox'] = (min(bx0, ax0), min(by0, ay0), max(bx1, ax1), max(by1, ay1))
    for t in info2.values():
        t['fam'] = max(t['famarea'].items(), key=lambda kv: kv[1])[0]
    return lab2, info2


# ------------------------------------------------------------------ build
PULLS = None


def _pulls():
    P = {k: pal(k) for k in ('royal_purple', 'royal_purple_hi', 'madder_dark', 'crimson', 'crimson_hi', 'crimson_deep', 'gold', 'gold_hi',
                             'gold_lo', 'mustard', 'gold_deep', 'flesh_fill', 'linen_hi', 'flesh_line', 'terracotta', 'steel', 'steel_lo',
                             'buff', 'woad', 'woad_dark', 'ink_blueblack', 'heraldic_green', 'royal_blue', 'metal_gold_f0', 'navy',
                             'navy_hi', 'olive', 'forest', 'sage', 'fire', 'fire_core', 'fire_outer', 'smoke', 'smoke_hi', 'smoke_deep',
                             'night', 'dusk_sky', 'wax')}
    return {
        FAM['purple']: [P['royal_purple'], P['royal_purple_hi'], P['madder_dark'], hex_lin('#2E1A36')],
        FAM['red']: [P['crimson'], P['crimson_hi'], P['terracotta']],
        FAM['darkred']: [P['crimson_deep'], P['madder_dark']],
        FAM['gold']: [P['gold'], P['gold_hi'], P['gold_lo'], P['mustard']],
        FAM['orange']: [P['terracotta'], P['fire'], P['fire_outer'], P['mustard']],
        FAM['flame']: [P['fire'], P['fire_core'], P['fire_outer'], P['mustard']],
        FAM['brown']: [P['madder_dark'], P['gold_lo'], P['gold_deep'], hex_lin('#5A3A22'), hex_lin('#8A6238')],
        FAM['skin']: [P['flesh_fill'], P['linen_hi'], P['flesh_line'], P['terracotta']],
        FAM['light']: [P['linen_hi'], P['steel'], P['steel_lo'], hex_lin('#EFE8DA'), P['wax']],
        FAM['white']: [P['linen_hi'], hex_lin('#EFE8DA'), P['wax']],
        FAM['ermine']: [P['linen_hi'], hex_lin('#EFE8DA'), P['buff']],
        FAM['buff']: [P['buff'], P['linen_hi'], P['wax']],
        FAM['blue']: [P['woad'], P['woad_dark'], P['royal_blue']],
        FAM['navy']: [P['navy'], P['woad_dark'], P['night']],
        FAM['green']: [P['heraldic_green'], P['olive'], P['forest'], P['sage']],
        FAM['grey']: [P['steel'], P['steel_lo'], P['smoke_hi']],
        FAM['darkgrey']: [P['smoke'], P['smoke_deep'], P['steel_lo']],
        FAM['ink']: [P['ink_blueblack'], hex_lin('#1A1418')],
        FAM['jewel']: [P['crimson'], P['heraldic_green'], P['royal_blue'], P['crimson_hi']],
        FAM['metal']: [P['metal_gold_f0']],
    }


def _ghost(m, rec, gsel, gmask_canvas, ud_paths, PX, seed=0, ud_col='#6E3326', ud_alpha=0.72, hole_spacing_mm=1.05):
    """write the ghost of the selected record entries into the LINEN maps m (before any replay):
    flattened protected linen, needle holes at the real strand ends (Poisson-thinned, 0.5-0.7 mm pits with raised lips),
    faint red-brown underdrawing (no relief).  Returns layers dict (holes, ud) for the manifest."""
    H, W = m['h'].shape
    r = np.random.default_rng(seed)
    s = cv2.GaussianBlur(gmask_canvas.astype(np.float32), (0, 0), 0.4 * PX)
    m['h'][:] = np.where(m['h'] > 0, m['h'] * (1 - 0.30 * s), m['h'])
    # underdrawing
    ud = np.zeros((H, W), np.float32)
    for p in ud_paths:
        q = S.smooth_poly(S.resample(p.astype(np.float32), 0.3 * PX), 2) + r.normal(0, 0.10 * PX, 2).astype(np.float32)
        cv2.polylines(ud, [np.round(q).astype(np.int32)], False, float(r.uniform(0.6, 1.0)), max(1, int(round(0.42 * PX))), cv2.LINE_AA)
    ud = cv2.GaussianBlur(ud, (0, 0), sigmaX=0.10 * PX, sigmaY=0.07 * PX)
    ud *= (0.8 + 0.4 * r.random(ud.shape).astype(np.float32))
    ud = np.clip(ud, 0, 1)
    ink = hex_lin(ud_col)
    a = np.clip(ud * ud_alpha, 0, 0.6)[..., None]
    m['alb'][:] = m['alb'] * (1 - a) + (m['alb'] * ink / (m['alb'].mean() + 1e-3) * 0.9) * a
    # needle holes at strand ends (stitches of fill/outline/couching), Poisson-thinned at 0.55 mm
    pts = []
    for k in gsel:
        if rec['typ'][k] != 0: continue
        kd = rec['kind'][k]
        if kd in (S.K_TIE, S.K_MTIE, S.K_CTIE): continue
        if kd == S.K_SPLIT and (k % 3) != 0: continue
        p = rec['P'][rec['off'][k]:rec['off'][k + 1]]
        pts.append(p[0]); pts.append(p[-1])
    hole = np.zeros((H, W), np.float32)
    if pts:
        pts = np.array(pts, np.float32)
        pts = pts[r.permutation(len(pts))]
        cell = hole_spacing_mm * PX
        grid = {}
        keep = []
        for p in pts:
            if not (0 <= p[0] < W and 0 <= p[1] < H): continue
            if not gmask_canvas[int(p[1]), int(p[0])]: continue
            gx, gy = int(p[0] / cell), int(p[1] / cell)
            ok = True
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    q = grid.get((gx + dx, gy + dy))
                    if q is not None and (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 < cell * cell:
                        ok = False; break
                if not ok: break
            if ok:
                grid[(gx, gy)] = p; keep.append(p)
        for p in keep:
            rad = r.uniform(0.17, 0.26) * PX
            cv2.circle(hole, (int(round(p[0] * 4)), int(round(p[1] * 4))), max(1, int(round(rad * 4))), 1.0, -1, cv2.LINE_AA, shift=2)
    hole = cv2.GaussianBlur(hole, (0, 0), 0.06 * PX)
    rim = np.clip(cv2.GaussianBlur(hole, (0, 0), 0.22 * PX) * 1.7 - hole, 0, 1)
    m['h'][:] = m['h'] - 0.28 * hole + 0.07 * rim
    m['alb'][:] = m['alb'] * (1 - 0.5 * hole[..., None]) * (1 + 0.06 * rim[..., None])
    return dict(holes=hole, ud=ud)


def build_panel(hints_path, out_root=None, PX=10.0, margin_mm=20.0, verbose=True, max_regions=None, focus=None):
    t0 = time.time()
    H = json.load(open(hints_path))
    name = H['panel']
    out_root = out_root or sheet_dir('')
    seed = H.get('seed', 1)
    from ..config import PANELS
    src0 = cv2.cvtColor(cv2.imread(PANELS[name], cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    src = inpaint_glows(src0, H.get('glows', [])) if H.get('glows') else src0
    Hs, Ws = src.shape[:2]
    ms, fam_s, Z = segment_panel(src, H)
    if verbose: print(f'[{name}] segmented {time.time() - t0:.1f}s', flush=True)
    sc = PX / SRC_PX
    mpx = int(round(margin_mm * PX))
    Wc, Hc = int(round(Ws * sc)) + 2 * mpx, int(round(Hs * sc)) + 2 * mpx
    off = (mpx, mpx)
    # group label map at source res (0 = ground) -> regions are cut by group polygons
    gnames = ['ground'] + [g['name'] for g in H.get('groups', [])]
    gmap_s = np.zeros((Hs, Ws), np.int32)
    gout_s = np.zeros((Hs, Ws), np.int32)        # outline assignment: group regions dilated 1.2 mm, inside the polygon
    for gi, g in enumerate(H.get('groups', []), start=1):
        sel = Z['gpolys'][g['name']] & (gmap_s == 0)
        if g.get('families'):
            sel &= np.isin(fam_s, [FAM[f] for f in g['families']])
        if g.get('exclude_families'):
            sel &= ~np.isin(fam_s, [FAM[f] for f in g['exclude_families']])
        gmap_s[sel] = gi
        dil = cv2.dilate(sel.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))) > 0
        gout_s[dil & Z['gpolys'][g['name']] & (gout_s == 0)] = gi
    # regions at source res: family x group
    combo = fam_s * 64 + gmap_s
    lab_s, info = components(combo, int(1.0 * SRC_PX * SRC_PX * 1.2))
    for rid, inf in info.items():
        inf['group'] = inf['fam'] % 64; inf['fam'] = inf['fam'] // 64
    lab_s, info = merge_similar(lab_s, info, lin2oklab(srgb2lin(ms.astype(np.float32) / 255)), H.get('merge_dE', 0.10))
    if verbose: print(f'[{name}] {len(info)} regions {time.time() - t0:.1f}s', flush=True)
    # canvas-res label map (nearest x2 + 5x5 median to round the steps)
    lab_c = np.zeros((Hc, Wc), np.int32)
    up = cv2.resize(lab_s.astype(np.float32), (Ws * int(sc), Hs * int(sc)), interpolation=cv2.INTER_NEAREST)
    if int(sc) == sc and lab_s.max() < 65535:
        up = cv2.medianBlur(up.astype(np.uint16), 5).astype(np.int32)
    lab_c[mpx:mpx + up.shape[0], mpx:mpx + up.shape[1]] = up
    del up
    gmap_c = np.zeros((Hc, Wc), np.uint8)
    gmap_c[mpx:mpx + int(Hs * sc), mpx:mpx + int(Ws * sc)] = cv2.resize(gmap_s.astype(np.uint8), (int(Ws * sc), int(Hs * sc)),
                                                                           interpolation=cv2.INTER_NEAREST)
    gpoly_c = gmap_c.copy()
    gout_c = np.zeros((Hc, Wc), np.uint8)
    gout_c[mpx:mpx + int(Hs * sc), mpx:mpx + int(Ws * sc)] = cv2.resize(gout_s.astype(np.uint8), (int(Ws * sc), int(Hs * sc)),
                                                                           interpolation=cv2.INTER_NEAREST)
    # ---------------- generation pass (live raster into scratch linen), recording everything
    m = make_linen(Hc, Wc, PX, 0.0, 0.0, seed=H.get('linen_seed', 0))
    S.ensure(m)
    S.REC = rec = Record(); S.reset_sid(1)
    CTX['gmap'] = None
    pulls = _pulls()
    lin_src = srgb2lin(src.astype(np.float32) / 255)

    def src_crop(x0, y0, x1, y1):
        """source colour (linear) and luminance resampled to canvas px window"""
        sx0, sy0 = (x0 - mpx) / sc, (y0 - mpx) / sc
        Mx = np.array([[1 / sc, 0, sx0], [0, 1 / sc, sy0]], np.float32)
        lc = cv2.warpAffine(lin_src, Mx, (x1 - x0, y1 - y0), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
        lc = np.clip(lc, 0, 1)
        lum = (np.clip(lc, 0, 1) ** (1 / 2.2) * LUMA).sum(-1).astype(np.float32)
        return lc, lum

    faces_c = lambda x, y: Z['faces'][int(np.clip((y - mpx) / sc, 0, Hs - 1)), int(np.clip((x - mpx) / sc, 0, Ws - 1))]
    beard_c = lambda x, y: Z['beard'][int(np.clip((y - mpx) / sc, 0, Hs - 1)), int(np.clip((x - mpx) / sc, 0, Ws - 1))]
    zones = []
    for z in H.get('zones', []):
        zones.append((poly_mask((Hs, Ws), [z['poly']]), z))
    order = [FAM[f] for f in ('navy', 'blue', 'grey', 'darkgrey', 'brown', 'purple', 'red', 'darkred', 'green', 'orange', 'buff', 'ermine',
                              'gold', 'skin', 'light', 'white', 'ink', 'metal', 'jewel', 'flame')]
    rids = sorted(info.keys(), key=lambda r: (info[r]['group'], order.index(info[r]['fam']) if info[r]['fam'] in order else 99,
                                              -info[r]['area']))
    stats = {}
    nreg = 0
    for rid in rids:
        f = info[rid]['fam']; g = info[rid]['group']
        if f == FAM['bg']: continue
        x0s, y0s, x1s, y1s = info[rid]['bbox']
        if focus is not None and (x1s < focus[0] or x0s > focus[2] or y1s < focus[1] or y0s > focus[3]): continue
        x0, y0 = int(x0s * sc) + mpx - 30, int(y0s * sc) + mpx - 30
        x1, y1 = int(x1s * sc) + mpx + 31, int(y1s * sc) + mpx + 31
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, Wc), min(y1, Hc)
        labw = lab_c[y0:y1, x0:x1]
        mk = labw == rid
        npx = int(mk.sum())
        if npx < 0.6 * PX * PX: continue
        area_mm2 = npx / PX / PX
        sub = S.view(m, x0, y0, x1, y1)
        sb_lin, lum = src_crop(x0, y0, x1, y1)
        sb = cv2.GaussianBlur(sb_lin, (0, 0), 0.45 * PX)
        pix = sb_lin[mk]
        ys, xs = np.nonzero(mk)
        cy, cx = ys.mean() + y0, xs.mean() + x0
        in_face = faces_c(cx, cy); in_beard = beard_c(cx, cy)
        zr = None
        for zm, z in zones:
            if zm[int(np.clip((cy - mpx) / sc, 0, Hs - 1)), int(np.clip((cx - mpx) / sc, 0, Ws - 1))] and (
                    'families' not in z or FAM_NAMES[f] in z['families']):
                zr = z; break
        sd = seed * 1000 + rid
        CTX['region'] = int(rid); CTX['group'] = int(g)
        origin = (x0 / PX, y0 / PX)
        nsh = int(np.clip(area_mm2 / 40, 2, 6))
        pull = pulls.get(f, pulls[FAM['brown']])
        lab_r = np.where(mk, rid, -1).astype(np.int32)
        mode = (zr or {}).get('field', 'auto')
        ang = (zr or {}).get('angle', None)
        laid_big = area_mm2 > H.get('laid_min_mm2', 40) and f not in (FAM['skin'], FAM['ink'], FAM['jewel'], FAM['metal']) and not in_face and not in_beard
        if f == FAM['metal']:
            fld, md = select_field(lum, mk, PX, mode='contour')
            S.metal_couch(sub, lab_r, rid, fld, PX, pitch=1.0, seed=sd, tarnish=0.06)
        elif f == FAM['jewel']:
            pad = S.pad_dome(mk, PX, 1.2, 1.2)
            sub['base'][:] = np.maximum(sub['base'], pad)
            shd = ShadeSet.from_pixels(pix, 2, pull, 0.5, sd)
            fld, md = select_field(lum, mk, PX, mode='blend', w_shape=1.0)
            S.fill_region(sub, lab_r, rid, fld, sb, shd, PX, style='laid', pitch=0.45, seed=sd, matid=SILK, h0=0.05, hamp=0.3,
                          r_fac=0.6, maxlen=12, bmul=1.0, cov=0.0)
        elif f == FAM['ink']:
            thick = cv2.morphologyEx(mk.astype(np.uint8), cv2.MORPH_OPEN,
                                     cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(1.6 * PX), int(1.6 * PX))))
            if thick.sum() < 2 * PX * PX: continue
            lab_t = np.where(thick > 0, rid, -1).astype(np.int32)
            in_erm = Z['ermine'][int(np.clip((cy - mpx) / sc, 0, Hs - 1)), int(np.clip((cx - mpx) / sc, 0, Ws - 1))]
            shd = ShadeSet.from_pixels(pix, 2, pull, 0.6, sd)
            if in_erm and area_mm2 < 40:       # ermine tails: padded black satin
                pad = S.pad_dome(thick > 0, PX, 0.9, 0.8)
                sub['base'][:] = np.maximum(sub['base'], pad)
                fld, md = select_field(lum, thick > 0, PX, mode='blend', w_shape=1.2)
                S.fill_region(sub, lab_t, rid, fld, sb, shd, PX, style='laid', pitch=0.5, seed=sd, matid=SILK, h0=0.08, hamp=0.3,
                              r_fac=0.62, maxlen=14, bmul=1.0, cov=0.0, hbias=0.2)
            elif area_mm2 > 150:
                fld, md = select_field(lum, thick > 0, PX, mode=mode if zr else 'auto', laid=True, angle_deg=ang, seed=sd, origin_mm=origin)
                S.fill_region(sub, lab_t, rid, fld, sb, shd, PX, style='laid', pitch=0.85, seed=sd, h0=0.06, hamp=0.42,
                              couch=dict(spacing=4.5, tie=4.0), cov=1.0)
            else:
                fld, md = select_field(lum, thick > 0, PX, mode='blend', w_shape=1.2)
                S.fill_region(sub, lab_t, rid, fld, sb, shd, PX, style='split', L=3.2, pitch=0.85, seed=sd, h0=0.18, hamp=0.42,
                              r_fac=0.62, tw_deg=15, maxlen=60, minlen=0.6, hbias=0.15)
        elif f == FAM['skin'] or in_face:
            shd = ShadeSet.from_pixels(pix, max(nsh, 4), pulls[FAM['skin']] if f == FAM['skin'] else pull, 0.3, sd)
            fld, md = select_field(lum, mk, PX, mode='blend', w_shape=0.15, sig_t_mm=1.0)
            S.fill_region(sub, lab_r, rid, fld, sb, shd, PX, style='split', L=2.2, pitch=0.45, seed=sd, h0=0.05, hamp=0.28,
                          r_fac=0.62, ply_mm=0.45, taper=0.3)
        elif in_beard and f in (FAM['light'], FAM['white'], FAM['grey'], FAM['buff']):
            shd = ShadeSet.from_pixels(pix, 5, pulls[FAM['light']], 0.3, sd)
            fld, md = select_field(lum, mk, PX, mode='blend', w_shape=0.1, sig_t_mm=1.2)
            S.fill_region(sub, lab_r, rid, fld, sb, shd, PX, style='split', L=6.5, pitch=0.6, seed=sd, h0=0.08, hamp=0.36, r_fac=0.6)
        elif f == FAM['ermine']:
            # laid cream wool on a constant axis + diagonal jittered couching (no brick lattice)
            shd = ShadeSet.from_pixels(pix, 3, pulls[FAM['ermine']], 0.35, sd)
            fld = region_axis_field(mk, PX, 90.0, 6.0, 30.0, sd, origin)
            bars = const_field(mk.shape, 35.0 + 10 * ((rid % 2) * 2 - 1))
            S.fill_region(sub, lab_r, rid, fld, sb, shd, PX, style='laid', pitch=0.85, seed=sd, h0=0.05, hamp=0.42,
                          couch=dict(spacing=5.0, tie=4.5, bar_field=bars, jitter_deg=6.0))
            md = 'axis'
        elif laid_big:
            shd = ShadeSet.from_pixels(pix, nsh, pull, 0.35, sd, chroma_max=0.17)
            fld, md = select_field(lum, mk, PX, mode=mode, laid=True, angle_deg=ang if ang is not None else H.get('laid_axis_default'),
                                   seed=sd, origin_mm=origin, sig_t_mm=5.0, w_shape=0.3)
            sp = 3.5 if f in (FAM['gold'],) else 4.5
            S.fill_region(sub, lab_r, rid, fld, sb, shd, PX, style='laid', pitch=0.85 if f != FAM['gold'] else 0.75, seed=sd,
                          couch=dict(spacing=sp, tie=sp - 0.5), h0=0.05, hamp=0.42, maxturn_deg=35 if md == 'axis' else 50)
        else:
            shd = ShadeSet.from_pixels(pix, nsh, pull, 0.3, sd, chroma_max=0.17)
            fld, md = select_field(lum, mk, PX, mode=mode if zr else 'blend', laid=False, angle_deg=ang, seed=sd, origin_mm=origin,
                                   sig_t_mm=1.6, w_shape=0.4)
            S.fill_region(sub, lab_r, rid, fld, sb, shd, PX, style='split', L=4.0, pitch=0.7, seed=sd, h0=0.06, hamp=0.4)
        stats[md] = stats.get(md, 0) + 1
        sub['base'][:] = np.where(mk, 0, sub['base'])
        nreg += 1
        if max_regions and nreg >= max_regions: break
        if verbose and nreg % 100 == 0:
            print(f'[{name}] {nreg} regions, {len(rec)} stitches, {time.time() - t0:.1f}s', flush=True)
    if verbose: print(f'[{name}] fills done: {nreg} regions {stats}, {len(rec)} stitches, {time.time() - t0:.1f}s', flush=True)
    # ---------------- stem outlines from dark lines (source res skeletons), suppressed in busy zones
    g = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    gs = cv2.GaussianBlur(g, (0, 0), 0.7)
    bh = cv2.morphologyEx(gs, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
    thr = np.where(Z['beard'] & ~Z['faces'], 0.17, 0.11)
    ln = ((bh > thr) & (gs < 0.45)) | (fam_s == FAM['ink'])
    ln &= (fam_s != FAM['bg']) | (bh > 0.16)
    ln = cv2.morphologyEx(ln.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    dens = cv2.GaussianBlur(ln.astype(np.float32), (0, 0), 5 * SRC_PX)
    busy = box_mask((Hs, Ws), H.get('busy_zones', [])) & (dens > 0.25)
    ln[busy] = 0
    # painted strand texture inside dark / busy fills is not an outline (no chenille web over dark grounds)
    loc = cv2.GaussianBlur(gs, (0, 0), 3 * SRC_PX)
    ln[loc < H.get('outline_min_local_lum', 0.0)] = 0
    ln[dens > H.get('outline_max_density', 1.0)] = 0
    up = cv2.GaussianBlur(cv2.resize(ln.astype(np.float32), (int(Ws * sc), int(Hs * sc)), interpolation=cv2.INTER_LINEAR), (0, 0),
                          0.1 * PX) > 0.45
    del ln
    dt = cv2.distanceTransform(up.astype(np.uint8), cv2.DIST_L2, 5) / PX
    if verbose: print(f'[{name}] line mask {time.time() - t0:.1f}s', flush=True)
    paths, _ = skeleton_paths(up, 4)
    if verbose: print(f'[{name}] skeleton {len(paths)} paths {time.time() - t0:.1f}s', flush=True)
    paths = merge_paths(paths, 0.3 * PX)
    if verbose: print(f'[{name}] merged -> {len(paths)} paths {time.time() - t0:.1f}s', flush=True)
    del up
    src_dark = cv2.erode(lin_src, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    P = {k: pal(k) for k in ('ink_blueblack',)}

    def ink_for(c, inf):
        lb = lin2oklab(np.asarray(c, np.float32)[None])[0]
        C = math.hypot(lb[1], lb[2]); hh = math.degrees(math.atan2(lb[2], lb[1])) % 360
        if inf: base = hex_lin('#55291D')
        elif C > 0.03 and (hh > 290 or hh < 20): base = hex_lin('#2A1730')
        elif C > 0.035 and 20 <= hh < 100: base = hex_lin('#3A1D12') if lb[0] < 0.4 else hex_lin('#5C2C1C')
        elif C > 0.03 and 180 <= hh < 290: base = hex_lin('#1C2438')
        else: base = P['ink_blueblack']
        return base * 0.8 + np.clip(c, 0, 1) * 0.2
    r = np.random.default_rng(seed + 11)
    okeep = poly_mask((Hs, Ws), H['outline_keepout']) if H.get('outline_keepout') else None
    CTX['region'] = OUTLINE_REGION
    CTX['gmap'] = gout_c
    nst = 0
    m_off = S.view(m, mpx, mpx, Wc - mpx, Hc - mpx)
    for pth in paths:
        if focus is not None:
            c_ = pth.mean(0) / sc
            if not (focus[0] <= c_[0] <= focus[2] and focus[1] <= c_[1] <= focus[3]): continue
        pth = S.smooth_poly(S.resample(pth.astype(np.float32), 0.3 * PX), 3)
        ln_mm = np.hypot(*np.diff(pth, axis=0).T).sum() / PX
        xi = np.clip(pth[:, 0].astype(int), 0, dt.shape[1] - 1); yi = np.clip(pth[:, 1].astype(int), 0, dt.shape[0] - 1)
        sxi = np.clip((pth[:, 0] / sc).astype(int), 0, Ws - 1); syi = np.clip((pth[:, 1] / sc).astype(int), 0, Hs - 1)
        inf = Z['faces'][syi, sxi].mean() > 0.5
        if ln_mm < (0.8 if inf else 1.5): continue
        if okeep is not None and okeep[int(np.median(syi)), int(np.median(sxi))] and ln_mm < 12.0: continue
        w = float(np.clip(2.0 * np.median(dt[yi, xi]) + 0.25, 0.55 if inf else 0.8, 1.7))
        col = ink_for(src_dark[syi, sxi].mean(0), inf) * (1 + r.uniform(-0.08, 0.08))
        S.stem_path(m_off, pth, col, PX, L=(2.2 if inf else 3.3), width=w, h0=(0.3 if inf else 0.5), hamp=(0.3 if inf else 0.42),
                    seed=int(r.integers(1 << 30)), cov=0.5)
        nst += 1
    CTX['gmap'] = None
    if verbose: print(f'[{name}] {nst} outlines, {len(rec)} stitches, {time.time() - t0:.1f}s', flush=True)
    S.REC = None
    pad_map = m['base'].copy()     # padded domes (jewels, ermine tails) persist for replay
    del m
    R = rec.arrays(); R['PX'] = np.float32(PX)
    del rec
    # ---------------- needle-path order
    gorder = list(range(len(gnames)))
    pol = {gi: g.get('policy', 'region') for gi, g in enumerate(H.get('groups', []), start=1)}
    swp = {gi: g.get('sweep_mm', 8.0) for gi, g in enumerate(H.get('groups', []), start=1)}
    ordr, flips = needle_order(R, gorder, pol, swp)
    apply_flips(R, ordr, flips)
    rank = np.full(len(R['typ']), -1, np.int64); rank[ordr] = np.arange(len(ordr))
    R['order'] = ordr; R['rank'] = rank
    if verbose: print(f'[{name}] ordered {time.time() - t0:.1f}s', flush=True)
    # ---------------- ghost under groups (+ underdrawing of the group's outlines & region boundaries)
    lin = make_linen(Hc, Wc, PX, 0.0, 0.0, seed=H.get('linen_seed', 0))
    gsel = np.nonzero(R['group'] > 0)[0]
    gm = gpoly_c > 0
    ud_paths = []
    for gi in range(1, len(gnames)):
        sel = np.nonzero((R['group'] == gi) & (R['kind'] == S.K_STEM))[0]
        # underdrawing follows the outline paths (unit = one stem path)
        for u in np.unique(R['unit'][sel]):
            ks = sel[R['unit'][sel] == u]
            pts = np.array([R['P'][R['off'][k]:R['off'][k + 1]].mean(0) for k in ks], np.float32)
            if len(pts) >= 2: ud_paths.append(pts)
        grids = [rid for rid, inf in info.items() if inf['group'] == gi and inf['fam'] != FAM['bg']]
        gmk = (np.isin(lab_c, grids) & (gpoly_c == gi)).astype(np.uint8)
        gmk = cv2.morphologyEx(gmk, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(1.5 * PX), int(1.5 * PX))))
        for c in S.mask_contours(gmk, PX, 4.0):
            ud_paths.append(c)
    del lab_c, Z, ms, lin_src, src_dark, dt
    layers = _ghost(lin, R, gsel, gm, ud_paths, PX, seed=seed + 5)
    for k in ('h', 'alb', 'T', 'cov'):
        lin[k] = lin[k].astype(np.float16)
    age = bake_age_layers((Hc, Wc), PX, seed=seed + 7, density=0.3, margin_px=mpx, tide=H.get('tide'))
    # ---------------- exact replays
    def final_maps(sel_order):
        mm = blank_like(lin)
        mm['base'] = pad_map
        replay(mm, R, sel_order, 0, 0)
        del mm['stamp'], mm['base']
        return mm
    meta_common = dict(panel=name, hints=os.path.basename(hints_path), margin_mm=margin_mm, panel_origin_mm=[margin_mm, margin_mm],
                       src_px_per_mm=SRC_PX, linen_seed=H.get('linen_seed', 0), groups=gnames, seed=seed)
    n = len(ordr)
    sid2idx = np.zeros(int(R['ipar'][:, 2].max()) + 2, np.int32) - 1
    sid2idx[R['ipar'][:, 2]] = np.arange(len(R['typ']))
    extra = {k: v.astype(np.float16) for k, v in dict(age_fox=age['fox'], age_tide=age['tide'], age_fade=age['fade'],
                                                      ghost=gm.astype(np.float32), ud=layers['ud'], holes=layers['holes'],
                                                      gpoly=gpoly_c.astype(np.float32), pad=pad_map).items()}
    del age, layers

    def write(maps, sheet, stitched_sel):
        sidm = maps['sid']
        idx = sid2idx[np.clip(sidm, 0, len(sid2idx) - 1)]
        has = (sidm > 0) & (idx >= 0)
        ih = idx[has]
        del idx
        reg = np.zeros(sidm.shape, np.uint16); grp = np.zeros(sidm.shape, np.uint8); birth = np.zeros(sidm.shape, np.float16)
        reg[has] = np.clip(R['region'][ih], 0, 65535); grp[has] = R['group'][ih]
        birth[has] = ((rank[ih] + maps['sfr'][has]) / max(n, 1)).astype(np.float16)
        del ih, has, maps['sfr']
        maps['reg'] = reg; maps['grp'] = grp; maps['birth'] = birth
        path = os.path.join(out_root, sheet)
        MapSet.write(path, maps, meta=dict(meta_common, sheet=sheet, stitched=int(len(stitched_sel))), extra_layers=extra)
        return path
    sel_all = ordr
    full = final_maps(sel_all)
    p_full = write(full, name, sel_all)
    del full
    sel_ground = ordr[R['group'][ordr] == 0]
    gr = final_maps(sel_ground)
    p_ground = write(gr, name + '_ground', sel_ground)
    del gr
    # record + group info
    for p in (p_full, p_ground):
        np.savez_compressed(os.path.join(p, 'stitches.npz'), **{k: v for k, v in R.items()})
        json.dump(dict(groups=gnames, group_polys_src=[g['poly'] for g in H.get('groups', [])],
                       group_counts={gn: int((R['group'] == gi).sum()) for gi, gn in enumerate(gnames)}, n=int(n),
                       sheet_canvas_px=[Wc, Hc], panel_origin_px=[mpx, mpx], src_scale=sc, regions=len(info),
                       field_modes=stats, built_s=round(time.time() - t0, 1)),
                  open(os.path.join(p, 'groups.json'), 'w'), indent=1)
    if verbose: print(f'[{name}] written {p_full}, {p_ground}  total {time.time() - t0:.1f}s', flush=True)
    return p_full, p_ground
