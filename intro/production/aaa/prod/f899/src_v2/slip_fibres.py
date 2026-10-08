"""Wool fuzz on the Eevee slips (pipeline 7.8): R25 calibrated fibre sets of each slip's own maps, carried by the slip's standing
matrix, projected with the f899 camera, depth-tested against the slips' Z pass, lit by the hearth (Kajiya-Kay, pooled) + fill, splatted
into the composite AFTER the render (so the fuzz is the same R25 fuzz as the ground plate's).  Also a 0.3 mm wool halo around the slip
silhouette (texture-space halo of R25, here in screen space)."""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bkit
import numpy as np, cv2
import camera as CAM
from chron.fibres import make_fibres, render_fibres
from chron.shade import light_vec

ROOT = os.path.dirname(HERE)
PX = 10.0


def slip_fibre_set(g, density=0.9, seed=0, edge_boost=3.0):
    z = np.load(os.path.join(ROOT, 'blend', 'slips_v2', f'{g}_maps.npz'))
    alpha = z['alpha'].astype(np.float32)
    H, W = alpha.shape
    m = dict(PX=PX, h=z['h'].astype(np.float32), mat=z['mat'], cov=z['cov'].astype(np.float32), T=z['T'].astype(np.float32), alb=z['alb'].astype(np.float32))
    ox, oy = z['origin_mm']
    fb = make_fibres(m, density=density, seed=seed, origin_px=(int(round(ox * PX)), int(round(oy * PX))), edge_boost=edge_boost)
    return fb, (float(ox), float(oy))


def project_fibres(fb, M, hinge, cam):
    """fibre points (sheet mm: x, y down, z) -> slip-local -> world (Blender) -> screen px + depth.  Also returns P in sheet-world
    (x, y_down, z up) for the lighting."""
    P = fb['P'].astype(np.float64)
    n, K, _ = P.shape
    loc = np.stack([P[..., 0] - hinge[0], hinge[1] - P[..., 1], P[..., 2]], -1).reshape(-1, 3)
    wb = (np.concatenate([loc, np.ones((len(loc), 1))], 1) @ M.T)[:, :3]
    uv, z = CAM.project(cam, wb)
    Q = (uv - 0.0).reshape(n, K, 2).astype(np.float32)
    Zc = z.reshape(n, K).astype(np.float32)
    Psheet = np.stack([wb[:, 0], -wb[:, 1], wb[:, 2]], -1).reshape(n, K, 3).astype(np.float32)
    return Q, Zc, Psheet


def add_fibres(img, depth, cam, slips_export, shot, pool_fn, density=0.9, width=0.9, kfill=1.0, edge_boost=3.0):
    """img: linear composite (modified in place).  depth: slips Z pass (1e5 where empty)."""
    from chron.color import light_colour
    H_ = shot['hearth']
    L = light_vec(H_['az'], H_['el'])
    kcol = np.asarray(light_colour(H_['K'], H_['tint']), np.float32) * H_['key_i']
    fcol = np.asarray(light_colour(shot['fill']['K'], 0.1), np.float32) * shot['fill']['i']
    n_tot = 0
    for k, s in enumerate(slips_export['slips']):
        g = s['group']
        fb, org = slip_fibre_set(g, density=density, seed=700 + k, edge_boost=edge_boost)
        if fb is None:
            continue
        M = np.array(s['matrix'])
        Q, Zc, Psheet = project_fibres(fb, M, s['hinge_mm'], cam)
        # pooled key at the slip's feet
        kp = float(pool_fn(s['hinge_mm'][0], s['hinge_mm'][1], H_['kmap']))
        fb2 = dict(fb); fb2['P'] = Psheet
        vis = np.ones((2, 2), np.float32)
        fb2['root'] = np.zeros_like(fb['root'])
        from chron.fibres import _light_fibres, _splat
        C = np.zeros(Psheet.shape, np.float32)
        # fibres standing out of a tilted card are lit along the card's own normal field: the key vector is the same L (world)
        vr = np.ones(len(Psheet), np.float32)
        _light_fibres(Psheet, fb['A'], vr, fb.get('occ', np.ones(len(Psheet), np.float32)), np.asarray(L, np.float32), (kcol * kp).astype(np.float32),
                      fcol.astype(np.float32), np.asarray([0.0, 0.0, 1.0], np.float32), C)
        _splat(img, depth.astype(np.float32), Q, Zc, C, fb['alpha'], float(width))
        n_tot += len(Psheet)
    return n_tot


def silhouette_halo(rgb_pm, alpha, px_per_mm=4.65, sigma_mm=0.3, strength=0.35):
    """screen-space wool halo: premultiplied slip colour bled 0.3 mm outside the silhouette (x strength)."""
    sig = max(0.6, sigma_mm * px_per_mm)
    ab = cv2.GaussianBlur(alpha, (0, 0), sig)
    cb = cv2.GaussianBlur(rgb_pm, (0, 0), sig) / (ab[..., None] + 1e-4)
    a = np.clip(ab - alpha, 0, 1) * strength
    return cb, a
