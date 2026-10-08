"""Colour-family segmentation of a painted / AI embroidery image into stitchable regions (OKLCh families), fast
bbox-local small-region merging, polygon/ellipse zone rasterising.  (<- R25 segment.py, generalised to whole panels)"""
import numpy as np, cv2
from .color import srgb2lin, lin2oklab

FAM = dict(bg=0, ink=1, purple=2, gold=3, brown=4, skin=5, light=6, blue=7, jewel=8, grey=9, metal=10, ermine=11,
           red=12, green=13, orange=14, darkred=15, navy=16, darkgrey=17, buff=18, flame=19, white=20)
FAM_NAMES = {v: k for k, v in FAM.items()}
NFAM = max(FAM.values()) + 1


def oklab_lch(rgb_u8):
    lab = lin2oklab(srgb2lin(rgb_u8.astype(np.float32) / 255))
    L = lab[..., 0]; C = np.hypot(lab[..., 1], lab[..., 2]); h = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    return lab, L, C, h


def hue_in(h, a, b):
    return ((h - a) % 360) <= ((b - a) % 360)


def majority(lbl, k, iters=1, n=None):
    n = n or int(lbl.max()) + 1
    for _ in range(iters):
        best = np.zeros(lbl.shape, np.float32) - 1; out = lbl.copy()
        for i in np.unique(lbl):
            v = cv2.blur((lbl == i).astype(np.float32), (k, k))
            sel = v > best
            out[sel] = i; best[sel] = v[sel]
        lbl = out
    return lbl.astype(np.int32)


def classify(L, C, h):
    """default family per pixel from OKLCh (zone rules are applied by the panel builder afterwards)."""
    fam = np.full(L.shape, FAM['brown'], np.int32)
    chrom = C >= 0.035
    fam[chrom & hue_in(h, 345, 40) & (L >= 0.42)] = FAM['red']
    fam[chrom & hue_in(h, 345, 40) & (L < 0.42)] = FAM['darkred']
    fam[chrom & hue_in(h, 40, 68) & (L >= 0.55) & (C >= 0.09)] = FAM['orange']
    fam[chrom & hue_in(h, 40, 68) & ((L < 0.55) | (C < 0.09))] = FAM['brown']
    fam[chrom & hue_in(h, 68, 112) & (C >= 0.075) & (L >= 0.52)] = FAM['gold']
    fam[chrom & hue_in(h, 68, 112) & (L < 0.52)] = FAM['brown']
    fam[chrom & hue_in(h, 68, 112) & (C < 0.075) & (L >= 0.52)] = FAM['buff']
    fam[chrom & hue_in(h, 112, 185)] = FAM['green']
    fam[(C >= 0.02) & hue_in(h, 185, 280) & (L >= 0.36)] = FAM['blue']
    fam[(C >= 0.02) & hue_in(h, 185, 285) & (L < 0.36)] = FAM['navy']
    fam[(C >= 0.03) & hue_in(h, 280, 345)] = FAM['purple']
    grey = C < 0.035
    fam[grey & (L >= 0.74)] = FAM['light']
    fam[grey & (L >= 0.45) & (L < 0.74)] = FAM['grey']
    fam[grey & (L >= 0.24) & (L < 0.45)] = FAM['darkgrey']
    fam[(L < 0.24) | ((L < 0.29) & (C < 0.03))] = FAM['ink']
    fam[(L > 0.86) & (C < 0.06)] = FAM['white']
    return fam


def components(fam, min_px, protect=None):
    """split family map into connected regions; merge regions < min_px into the most common neighbouring region
    (bbox-local, fast).  Returns (lab int32, info {rid: dict(fam, area, bbox)})."""
    H, W = fam.shape
    lab = np.zeros((H, W), np.int32); nxt = 1; info = {}
    for f in np.unique(fam):
        nc, cc, st, _ = cv2.connectedComponentsWithStats((fam == f).astype(np.uint8), connectivity=8)
        if nc <= 1: continue
        sel = cc > 0
        lab[sel] = cc[sel] + nxt - 1
        for c in range(1, nc):
            x, y, w, h, a = st[c]
            info[nxt + c - 1] = dict(fam=int(f), area=int(a), bbox=(int(x), int(y), int(x + w), int(y + h)))
        nxt += nc - 1
    order = sorted(info.items(), key=lambda kv: kv[1]['area'])
    for rid, inf in order:
        if inf['area'] >= min_px or inf['area'] == 0: continue
        if protect is not None and inf['fam'] in protect: continue
        x0, y0, x1, y1 = inf['bbox']
        x0, y0, x1, y1 = max(x0 - 1, 0), max(y0 - 1, 0), min(x1 + 1, W), min(y1 + 1, H)
        sub = lab[y0:y1, x0:x1]
        mk = (sub == rid).astype(np.uint8)
        ring = (cv2.dilate(mk, np.ones((3, 3), np.uint8)) > 0) & (mk == 0)
        nb = sub[ring]; nb = nb[(nb != rid) & (nb > 0)]
        if len(nb) == 0: continue
        tgt = int(np.bincount(nb).argmax())
        sub[mk > 0] = tgt
        t = info[tgt]
        t['area'] += inf['area']
        bx0, by0, bx1, by1 = t['bbox']; ax0, ay0, ax1, ay1 = inf['bbox']
        t['bbox'] = (min(bx0, ax0), min(by0, ay0), max(bx1, ax1), max(by1, ay1))
        inf['area'] = 0
    info = {k: v for k, v in info.items() if v['area'] > 0}
    return lab, info


def poly_mask(shape, polys, scale=1.0, offset=(0.0, 0.0)):
    m = np.zeros(shape, np.uint8)
    for p in polys:
        q = (np.asarray(p, np.float32) * scale + np.asarray(offset, np.float32)).round().astype(np.int32)
        cv2.fillPoly(m, [q], 1)
    return m > 0


def ellipse_mask(shape, ells, scale=1.0, offset=(0.0, 0.0)):
    m = np.zeros(shape, np.uint8)
    for e in ells:
        cx, cy, ax, ay = e[:4]
        ang = e[4] if len(e) > 4 else 0
        cv2.ellipse(m, (int(round(cx * scale + offset[0])), int(round(cy * scale + offset[1]))),
                    (int(round(ax * scale)), int(round(ay * scale))), ang, 0, 360, 1, -1)
    return m > 0


def box_mask(shape, boxes, scale=1.0, offset=(0.0, 0.0)):
    m = np.zeros(shape, bool)
    for x0, y0, x1, y1 in boxes:
        m[int(y0 * scale + offset[1]):int(y1 * scale + offset[1]), int(x0 * scale + offset[0]):int(x1 * scale + offset[0])] = True
    return m
