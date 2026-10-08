"""Build and cache the test scene: linen canvas with the re-embroidered king (M1), Bayeux register lines, ageing,
and the knight (M2) as a separate liftable 'slip' layer; under the slip the canvas keeps a ghost
(underdrawing + needle holes + less-faded linen) that is revealed when the figure rises."""
import os, time, math
import numpy as np, cv2
from .core import *
from .linen import make_linen, add_ageing
from . import stitch as S
from .motif_king import build_king
from .motif_knight import build_knight
from .render import prepare
from .fibres import make_fibres

PX = 10.0
CANVAS_MM = (380.0, 210.0)
KING_ORIGIN_MM = (42.0, 36.0)
KNIGHT_WIN_MM = (163.0, 26.0, 150.0, 150.0)   # x, y, w, h
CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache', 'scene.npz')
KEYS = ('h', 'alb', 'T', 'mat', 'cov', 'sid', 'N', 'ao')


def register_lines(m, y_mm, x0_mm, x1_mm, seed):
    P = PAL['cinematic']
    r = np.random.default_rng(seed)
    for k, (dy, colname, w) in enumerate([(0.0, 'ink_blueblack', 1.4), (2.6, 'ink_redbrown', 1.3)]):
        xs = np.linspace(x0_mm, x1_mm, 400)
        ys = y_mm + dy + 0.35 * np.sin(xs / 37.0 + seed) + 0.2 * np.sin(xs / 11.0 + 2 * seed)
        S.stem_path(m, np.stack([xs, ys], 1).astype(np.float32) * PX, hex_lin(P[colname]['hex']), PX, width=w,
                    seed=seed * 10 + k)


def ghost(m, K, seed=0):
    """modify canvas maps under the knight slip: faint underdrawing on the cord skeleton, needle holes along region
    boundaries, linen under former wool slightly flattened and less faded."""
    ox, oy = K['offset_canvas']
    Wm, Hm = K['size']; kox, koy = K['offset']
    win = (slice(oy + koy, oy + koy + Hm), slice(ox + kox, ox + kox + Wm))
    sil = K['sil'][koy:koy + Hm, kox:kox + Wm]
    lab = K['lab']; cord = K['cord']
    h = m['h'][win]; alb = m['alb'][win]
    # flattened + fresher linen where the wool protected it
    s = cv2.GaussianBlur(sil.astype(np.float32), (0, 0), 0.4 * PX)
    h[:] = np.where(h > 0, h * (1 - 0.35 * s), h)
    alb[:] = alb * (1 - 0.06 * s[..., None]) * (1 + np.array([0.04, 0.01, -0.03], np.float32) * s[..., None])
    # underdrawing (iron-gall / charcoal line, bleeding along the weave)
    from .skel import skeleton_paths
    ud = np.zeros(sil.shape, np.float32)
    paths, _ = skeleton_paths(cord.astype(np.uint8), 4)
    r = np.random.default_rng(seed)
    for p in paths:
        q = S.smooth_poly(S.resample(p.astype(np.float32), 0.3 * PX), 2) + r.normal(0, 0.12 * PX, 2).astype(np.float32)
        cv2.polylines(ud, [np.round(q).astype(np.int32)], False, float(r.uniform(0.5, 0.9)), max(1, int(0.35 * PX)), cv2.LINE_AA)
    ud = cv2.GaussianBlur(ud, (0, 0), sigmaX=0.12 * PX, sigmaY=0.08 * PX) * (0.85 + 0.3 * (np.random.default_rng(seed + 1).random(ud.shape) - 0.5))
    ink = hex_lin('#5A6070')
    a = np.clip(ud * 0.55, 0, 0.6)[..., None]
    alb[:] = alb * (1 - a) + alb * ink / 0.75 * a
    # needle holes along region boundaries and both sides of the cord
    edges = np.zeros(lab.shape, np.uint8)
    edges[:, 1:] |= (lab[:, 1:] != lab[:, :-1]); edges[1:, :] |= (lab[1:, :] != lab[:-1, :])
    edges &= (cv2.dilate(sil.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0)
    ys, xs = np.nonzero(edges)
    pick = r.permutation(len(xs))[: int(len(xs) / (0.75 * PX))]
    hole = np.zeros(sil.shape, np.float32)
    for i in pick:
        cv2.circle(hole, (int(xs[i] + r.normal(0, 0.6)), int(ys[i] + r.normal(0, 0.6))), int(max(1, r.uniform(0.12, 0.22) * PX)),
                   1.0, -1, cv2.LINE_AA)
    hole = cv2.GaussianBlur(hole, (0, 0), 0.6)
    rim = np.clip(cv2.GaussianBlur(hole, (0, 0), 0.25 * PX) * 1.6 - hole, 0, 1)
    h[:] = h - 0.22 * hole + 0.05 * rim
    alb[:] = alb * (1 - 0.6 * hole[..., None])


def build(force=False, verbose=True):
    if os.path.exists(CACHE) and not force:
        return load()
    t0 = time.time()
    W, H = int(CANVAS_MM[0] * PX), int(CANVAS_MM[1] * PX)
    m = make_linen(H, W, PX, seed=11)
    S.ensure(m)
    add_ageing(m, seed=3, density=0.3)
    if verbose: print(f'linen {time.time() - t0:.1f}s')
    # knight layer: built on a copy of the canvas linen window (seamless when flat)
    kx, ky, kw, kh = [int(v * PX) for v in KNIGHT_WIN_MM]
    base = {k: (v[ky:ky + kh, kx:kx + kw].copy() if isinstance(v, np.ndarray) else v) for k, v in m.items()}
    K = build_knight(base, PX, 135.0, 'blue', seed=2, margin_mm=0.2)
    K['offset_canvas'] = (kx, ky)
    if verbose: print(f'knight {time.time() - t0:.1f}s')
    info = build_king(m, int(KING_ORIGIN_MM[0] * PX), int(KING_ORIGIN_MM[1] * PX), seed=1)
    if verbose: print(f'king {time.time() - t0:.1f}s')
    register_lines(m, 22.0, 3.0, 377.0, 1)
    register_lines(m, 172.0, 3.0, 377.0, 2)
    from .titulus import titulus
    titulus(m, 'HIC SEDET REX', 40.0, 33.2, 6.0, seed=21)
    titulus(m, 'ET HIC MILES', 231.0, 33.2, 6.0, seed=22)
    ghost(m, K, seed=4)
    prepare(m); prepare(K['maps'])
    km = K['maps']
    fib0 = make_fibres(m, density=1.0, seed=5)
    fib1 = make_fibres(km, density=1.0, seed=6, region=(K['alpha'] > 0.5))
    if verbose: print(f'prepared {time.time() - t0:.1f}s')
    np.savez(CACHE, **{f'c_{k}': m[k] for k in KEYS}, **{f'k_{k}': km[k] for k in KEYS},
             k_alpha=K['alpha'], k_sil=K['sil'], k_relief=K['relief'], k_off=np.array([kx, ky]),
             **{f'f0_{k}': v for k, v in fib0.items()}, **{f'f1_{k}': v for k, v in fib1.items()},
             king_alpha=info['alpha'], king_origin=np.array(info['origin']))
    if verbose: print(f'cached {time.time() - t0:.1f}s')
    return load()


def load():
    z = dict(np.load(CACHE))
    z['k_alpha'] = np.maximum(z['k_alpha'], z['k_sil'].astype(np.float32))
    c = {k: z[f'c_{k}'] for k in KEYS}; c['PX'] = PX
    k = {kk: z[f'k_{kk}'] for kk in KEYS}; k['PX'] = PX
    zf = z
    fib0 = make_fibres(c, density=1.0, seed=5)
    fib1 = make_fibres(k, density=1.0, seed=6, region=(z['k_alpha'] > 0.5), clip_region=(z['k_alpha'] > 0.5))
    rel = z['k_relief'].astype(np.float32)
    sil = z['k_sil'].astype(np.float32)
    # padding profile for stumpwork rise: rounded dome from the silhouette distance x part relief
    dt = cv2.distanceTransform((sil > 0.5).astype(np.uint8), cv2.DIST_L2, 5) / PX
    dome = np.sqrt(1 - (1 - np.clip(dt / 4.0, 0, 1)) ** 2)
    pad = cv2.GaussianBlur((0.55 * dome + 0.45 * rel * dome).astype(np.float32), (0, 0), 0.6 * PX)
    return dict(canvas=c, knight=k, k_alpha=z['k_alpha'], k_sil=z['k_sil'], k_relief=rel, k_off=tuple(z['k_off']),
                fib0=fib0, fib1=fib1, k_relief_pad=pad)


def composite_flat(sc):
    """knight slip flattened into the canvas (frontal still in the 'stitched' state)."""
    c = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in sc['canvas'].items()}
    kx, ky = sc['k_off']; km = sc['knight']; a = sc['k_alpha']
    Hk, Wk = a.shape
    win = (slice(ky, ky + Hk), slice(kx, kx + Wk))
    sel = a > 0.5
    for k in ('h', 'T', 'mat', 'cov', 'sid', 'alb', 'N', 'ao'):
        v = c[k][win]
        v[sel] = km[k][sel]
    # fibres: canvas fibres outside the slip + knight fibres shifted
    f0 = sc['fib0']; f1 = sc['fib1']
    rx, ry = f0['root'][:, 0] - kx, f0['root'][:, 1] - ky
    inwin = (rx >= 0) & (ry >= 0) & (rx < Wk) & (ry < Hk)
    inside = np.zeros(len(rx), bool)
    inside[inwin] = sel[ry[inwin], rx[inwin]]
    keep = ~inside
    P1 = f1['P'].copy(); P1[..., 0] += kx / PX; P1[..., 1] += ky / PX
    fib = dict(P=np.concatenate([f0['P'][keep], P1]), A=np.concatenate([f0['A'][keep], f1['A']]),
               alpha=np.concatenate([f0['alpha'][keep], f1['alpha']]),
               root=np.concatenate([f0['root'][keep], f1['root'] + np.array([kx, ky])]))
    return c, fib
