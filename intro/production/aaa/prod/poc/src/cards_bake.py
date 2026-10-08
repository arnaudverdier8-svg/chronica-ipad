"""v3: the standing figure cards, re-embroidered ON THEIR OWN canvas at 2.4x the board's stitch density (the v2 cards were cut out of the board bake, so a card
carried the strands of its neighbours and only 85 x 132 px of colour: blotchy faces, double arms).
Each card = the game sprite quantised to its own palette (13 OKLab clusters), every region filled with contour-following laid wool (R25 emb.stitch),
a couched outline in the figure's OWN darkest dye (not near-black brown), no die-cut cream ring (the sprite's anti-aliased edge is eroded away).
Outputs data/eevee/cards/<id>_alb.png (sRGB + coverage alpha), <id>_nrm.png (strand relief normal) -- overwrites the finalize.py crops.
python3 cards_bake.py"""
import sys, os, json, math, time, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
sys.path.insert(0, RND)
import numpy as np, cv2
cv2.setNumThreads(2)
from emb.core import hex_lin, smooth_noise, hash1, WOOL, SILK, lin2oklab, oklab2lin, srgb2lin, lin2srgb
from linen2 import make_linen
from emb import stitch as S
import pal2
from bakelib import Baker, tag, shades_around
from figures import load_card

SC = 2.4                 # stitch density multiplier of the card (card drawn SC times larger on its own canvas, shown at its true size)
T0 = time.time()
PIECES = json.load(open(f'{POC}/data/pieces.json'))
E = f'{POC}/data/eevee/cards'; os.makedirs(E, exist_ok=True)
CACHE = {}


def embroider(B, alb, sil, seed):
    """port of board_bake.embroider_card_icon on a private canvas (origin 0, 0)"""
    hh_, ww_ = sil.shape
    lab = lin2oklab(srgb2lin(alb)).astype(np.float32)
    ys, xs = np.nonzero(sil)
    X = lab[ys, xs] * np.array([1.0, 1.7, 1.7], np.float32)
    k = 13
    _, lb, cen = cv2.kmeans(X.astype(np.float32), k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 1e-4), 3, cv2.KMEANS_PP_CENTERS)
    cen = cen / np.array([1.0, 1.7, 1.7], np.float32)
    rank = np.argsort(np.argsort(cen[:, 0]))
    L_ = -np.ones((hh_, ww_), np.int32); L_[ys, xs] = rank[lb.ravel()]
    cen = cen[np.argsort(cen[:, 0])]
    for _ in range(2):
        tmp = (L_ + 1).astype(np.uint8)
        tmp = cv2.medianBlur(tmp, 5)
        L_ = np.where(sil > 0, tmp.astype(np.int32) - 1, -1)
        L_ = np.where((L_ < 0) & (sil > 0), 0, L_)
    order = np.argsort(-np.array([(L_ == c_).sum() for c_ in range(k)]))
    kk = 0
    for c_ in order:
        mk_all = L_ == c_
        if mk_all.sum() < 12: continue
        nc, cc = cv2.connectedComponents(mk_all.astype(np.uint8), connectivity=4)
        for ci in range(1, nc):
            mk = cc == ci
            n_px = int(mk.sum())
            if n_px < 14: continue
            colr = oklab2lin(cen[c_][None])[0]
            sh = S.ShadeSet(np.array([lin2oklab(colr[None])[0] * np.array([1.0 + 0.03 * t, 1, 1]) for t in (-1, 0, 1)], np.float32), 9500 + kk + seed)
            dt = cv2.distanceTransform(mk.astype(np.uint8), cv2.DIST_L2, 3)
            tag('icon', 'card', 0.1 * kk)
            if n_px < 70:
                ys_, xs_ = np.nonzero(mk)
                cxp, cyp = xs_.mean(), ys_.mean()
                ln = max(1.0, (ys_.max() - ys_.min() + 1))
                B.put_poly(np.array([[cxp, cyp - ln / 2 + 0.5], [cxp, cyp + ln / 2 - 0.5]], np.float32), sh.lin[1], max(0.2, min(0.36, (xs_.max() - xs_.min() + 1) / PX / 2)),
                           0.35, 0.35, WOOL, ply_mm=0.4, taper_mm=0.1, tw_deg=10, seed=9100, hbias=0.35)
            else:
                c2, s2, coh = S.orient_tensor(cv2.GaussianBlur(dt, (0, 0), 0.8), 1.2, 3.0, mask=mk)
                nrm_ = np.hypot(c2, s2); weak = nrm_ < 1e-6
                c2 = np.where(weak, -1.0, c2 / (nrm_ + 1e-12)).astype(np.float32); s2 = np.where(weak, 0.0, s2 / (nrm_ + 1e-12)).astype(np.float32)
                B.fill_mask(mk, 0, 0, 90.0, sh, style='laid', pitch=0.42, seed=9200 + kk + seed, matid=WOOL, h0=0.15, hamp=0.40, r_fac=0.62, bend=0, hbias=0.3, maxlen=10,
                            field=(c2, s2), minlen=0.5)
            kk += 1
    cs_, _ = cv2.findContours(sil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    tag('icon_out', 'card', 0.8)
    dk = cen[0].copy(); dk[0] *= 0.82
    out_col = oklab2lin(dk[None])[0]
    for c in cs_:
        if len(c) < 8: continue
        pts = S.smooth_poly(S.resample(c[:, 0, :].astype(np.float32), 0.5 * PX), 2)
        B.stem(np.vstack([pts, pts[:1]]), out_col, width=0.40, seed=9300 + kk, h0=0.60, hamp=0.32, L=2.0)


def bake_card(unit, realm, variant, w_u, h_u):
    key = (unit, realm, variant)
    if key in CACHE: return CACHE[key]
    c = load_card(unit, realm)
    wpx, hpx = int(round(w_u * PPU * SC)), int(round(h_u * PPU * SC))
    alb = cv2.resize(cv2.cvtColor((c['alb'] * 255).astype(np.uint8), cv2.COLOR_RGB2BGR), (wpx, hpx), interpolation=cv2.INTER_AREA)
    alb = cv2.cvtColor(alb, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    al = cv2.resize(c['alpha'], (wpx, hpx), interpolation=cv2.INTER_AREA)
    sil = (al > 0.55).astype(np.uint8)
    sil = cv2.erode(sil, np.ones((3, 3), np.uint8), iterations=2)            # strips the anti-aliased die-cut ring of the sprite
    mg = 6
    Hc, Wc = hpx + 2 * mg, wpx + 2 * mg
    m = make_linen(Hc, Wc, PX, seed=77 + variant)
    S.ensure(m)
    m['base'][:] = 0.0
    B = Baker(m, Wc, Hc)
    sil_p = np.zeros((Hc, Wc), np.uint8); sil_p[mg:mg + hpx, mg:mg + wpx] = sil
    alb_p = np.zeros((Hc, Wc, 3), np.float32); alb_p[mg:mg + hpx, mg:mg + wpx] = alb
    # embroider on the padded canvas (origin 0, 0)
    embroider(B, alb_p, sil_p, variant * 17)
    cov = (m['mat'] != 0).astype(np.uint8)
    cov = cv2.morphologyEx(cov, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    sl = (slice(0, Hc), slice(0, Wc))        # no crop: the mesh maps the padded canvas 1:1 (SC * PPU px per game unit), feet at v = mg / Hc
    cov = cov[sl]; alb_o = lin2srgb(np.clip(m['alb'][sl], 0, 1)); h = m['h'][sl] * cov
    al2 = cv2.GaussianBlur(cov.astype(np.float32), (0, 0), 0.5)
    hb = cv2.GaussianBlur(h, (0, 0), 0.5)
    gx = cv2.Sobel(hb, cv2.CV_32F, 1, 0, ksize=3) / 8 * PX
    gy = cv2.Sobel(hb, cv2.CV_32F, 0, 1, ksize=3) / 8 * PX
    nz = 1.0 / np.sqrt(gx * gx + gy * gy + 1)
    nrm = np.dstack([0.5 - 0.5 * gx * nz * 1.2, 0.5 + 0.5 * gy * nz * 1.2, 0.5 + 0.5 * nz])
    CACHE[key] = (np.dstack([alb_o, al2]), np.clip(nrm, 0, 1), dict(W=int(Wc), H=int(Hc), mg=int(mg), sc=SC, ppu=PPU))
    return CACHE[key]


n = 0
META = {}
for p in PIECES:
    if p['kind'] != 'card' or p.get('skip'): continue
    var = zlib.crc32(p['id'].encode()) % 3
    rgba, nrm, box = bake_card(p['unit'], p['realm'], var, p['w'], p['height'])
    nm = p['id']
    cv2.imwrite(f'{E}/{nm}_alb.png', cv2.cvtColor((rgba * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGBA2BGRA))
    cv2.imwrite(f'{E}/{nm}_nrm.png', cv2.cvtColor((nrm * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR))
    META[nm] = box
    n += 1
    print(f'[{time.time() - T0:6.1f}s]', nm, rgba.shape, flush=True)
json.dump(META, open(f'{E}/cards_meta.json', 'w'))
print('cards', n)
