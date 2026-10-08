"""Border beasts extracted from the game's vignette art (assets/tex/ui_embroidery_v2/vignette_red.png / _blue.png):
silhouette, interior detail lines (dark strand separations: mane, legs, tail tuft) and the eye, rescaled to a target
box.  The kit re-stitches them (laid + couched body, stem outlines and detail lines), so the border beasts are the
game's own lions in Bayeux idiom."""
import os, math
import numpy as np, cv2
from . import AAA
from chron.color import srgb2lin, lin2oklab
from chron.skel import skeleton_paths, merge_paths
from chron import stitch as S

VIG = os.path.join(AAA, 'assets', 'tex', 'ui_embroidery_v2')
CROP = dict(red=(232, 18, 492, 182), blue=(238, 22, 472, 186))


def _load(which):
    im = cv2.imread(os.path.join(VIG, f'vignette_{which}.png'), cv2.IMREAD_UNCHANGED)
    rgb = cv2.cvtColor(im[..., :3], cv2.COLOR_BGR2RGB)
    x0, y0, x1, y1 = CROP[which]
    return rgb[y0:y1, x0:x1]


def lion_from_vignette(which, Wpx, Hpx, flip=False, up=4):
    src = _load(which)
    lin = srgb2lin(src.astype(np.float32) / 255)
    lab = lin2oklab(lin)
    L = lab[..., 0]; C = np.hypot(lab[..., 1], lab[..., 2]); h = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    if which == 'red':
        body = (C > 0.06) & ((h < 60) | (h > 340)) & (L < 0.72)
    else:
        body = (C > 0.025) & (h > 200) & (h < 290) & (L < 0.62)
    dark = L < 0.36
    sil = (body | (dark & (cv2.dilate(body.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0))).astype(np.uint8)
    sil = cv2.morphologyEx(sil, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    n, cc, stt, _ = cv2.connectedComponentsWithStats(sil)
    k = 1 + int(np.argmax(stt[1:, 4]))
    sil = (cc == k).astype(np.uint8)
    # fill holes
    ff = sil.copy(); hh, ww = ff.shape
    m2 = np.zeros((hh + 2, ww + 2), np.uint8)
    cv2.floodFill(ff, m2, (0, 0), 1)
    sil = sil | (1 - ff)
    ys, xs = np.nonzero(sil)
    sil = sil[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    Lc = L[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    Cc = C[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    hc = h[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    if flip:
        sil, Lc, Cc, hc = sil[:, ::-1].copy(), Lc[:, ::-1].copy(), Cc[:, ::-1].copy(), hc[:, ::-1].copy()
    sh, sw = sil.shape
    s = min(Wpx / sw, Hpx / sh)
    W2, H2 = int(round(sw * s)), int(round(sh * s))
    mf = cv2.GaussianBlur(sil.astype(np.float32), (0, 0), 0.9)
    mask = (cv2.resize(mf, (W2, H2), interpolation=cv2.INTER_CUBIC) > 0.5).astype(np.uint8)
    lum = cv2.resize(cv2.GaussianBlur(Lc.astype(np.float32), (0, 0), 0.6), (W2, H2), interpolation=cv2.INTER_CUBIC)
    # interior detail lines: dark strand separations inside the eroded silhouette (source res, upsampled first)
    Lu = cv2.resize(Lc.astype(np.float32), (sw * up, sh * up), interpolation=cv2.INTER_CUBIC)
    Lu = cv2.GaussianBlur(Lu, (0, 0), 1.2)
    bh = cv2.morphologyEx(Lu, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)))
    silu = cv2.resize(sil, (sw * up, sh * up), interpolation=cv2.INTER_NEAREST)
    inner = cv2.erode(silu, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * up * 2 + 1, 2 * up * 2 + 1)))
    ln = ((bh > 0.05) & (inner > 0)).astype(np.uint8)
    ln = cv2.morphologyEx(ln, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    paths, _ = skeleton_paths(ln, 6)
    paths = merge_paths(paths, 3.0)
    details = []
    for p in paths:
        q = p.astype(np.float32) / up * s
        if len(q) < 3: continue
        q = S.smooth_poly(S.resample(q, max(2.0, 0.03 * W2)), 3)
        ln_ = np.hypot(*np.diff(q, axis=0).T).sum()
        if ln_ > 0.11 * max(W2, H2):
            details.append(q.astype(np.float32))
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contours = []
    for cc_ in cs:
        q = cc_[:, 0, :].astype(np.float32)
        if len(q) < 10: continue
        q = np.vstack([q, q[:1]])
        contours.append(S.smooth_poly(S.resample(q, 3.0), 3))
    eye = None
    if which == 'red':
        em = (Cc > 0.07) & (hc > 70) & (hc < 110) & (Lc > 0.55)
    else:
        em = (Lc > 0.62) & (cv2.erode(sil, np.ones((3, 3), np.uint8)) > 0)
    if em.sum() >= 2:
        yy, xx = np.nonzero(em)
        eye = np.array([xx.mean() * s, yy.mean() * s], np.float32)
    return dict(mask=mask, lum=lum, details=details, contours=contours, eye=eye, scale=s)
