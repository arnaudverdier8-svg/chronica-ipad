"""Colour-family segmentation of a painted/AI embroidery image into stitchable regions."""
import numpy as np, cv2
from .core import srgb2lin, lin2oklab

FAM = dict(bg=0, ink=1, purple=2, gold=3, brown=4, skin=5, light=6, blue=7, jewel=8, midgrey=9, metal=10, ermine=11,
           red=12, steel=13, team=14, cord=15, white=16, horse=17, horse_dark=18, wood=19, black=20)


def oklab_lch(rgb_u8):
    lab = lin2oklab(srgb2lin(rgb_u8.astype(np.float32) / 255))
    L = lab[..., 0]; C = np.hypot(lab[..., 1], lab[..., 2]); h = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    return lab, L, C, h


def majority(lbl, k, iters=2, n=None):
    n = n or int(lbl.max()) + 1
    for _ in range(iters):
        votes = np.stack([cv2.blur((lbl == i).astype(np.float32), (k, k)) for i in range(n)], 0)
        lbl = votes.argmax(0).astype(np.int32)
    return lbl


def components(fam, min_px, n_fam=None):
    """split family map into connected regions; merge regions < min_px into the most common neighbour family."""
    H, W = fam.shape
    lab = np.zeros((H, W), np.int32); nxt = 1; info = {}
    for f in np.unique(fam):
        nc, cc = cv2.connectedComponents((fam == f).astype(np.uint8), connectivity=8)
        for c in range(1, nc):
            mk = cc == c
            lab[mk] = nxt; info[nxt] = dict(fam=int(f), area=int(mk.sum())); nxt += 1
    # merge small
    for rid, inf in sorted(info.items(), key=lambda kv: kv[1]['area']):
        if inf['area'] >= min_px: continue
        mk = (lab == rid).astype(np.uint8)
        ring = cv2.dilate(mk, np.ones((3, 3), np.uint8)) & (1 - mk)
        nb = lab[ring > 0]; nb = nb[nb != rid]
        if len(nb) == 0: continue
        tgt = np.bincount(nb).argmax()
        lab[mk > 0] = tgt
        info[tgt]['area'] += inf['area']; inf['area'] = 0
    info = {k: v for k, v in info.items() if v['area'] > 0}
    return lab, info
