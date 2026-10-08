"""High-level oblique render of the scene (canvas + liftable knight slip)."""
import math, time
import numpy as np, cv2
from .core import *
from .shade import relight, light_vec, normals
from .fibres import halo, render_fibres
from .oblique import Camera, raymarch, gather, slab_shadow, pyramid, dof
from .render import spot


def lift_map(alpha, PX, lift, curl=0.0, tilt=(0.0, 0.0), seed=0, peel=None):
    """spatially varying lift (mm) over the slip: base lift + gentle curl (edges lift more) + tilt."""
    H, W = alpha.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ys, xs = np.nonzero(alpha > 0.5)
    cx, cy = xs.mean(), ys.mean()
    d = np.hypot((xx - cx) / PX, (yy - cy) / PX)
    L = lift + curl * (d / 70.0) ** 2 + tilt[0] * (xx - cx) / PX / 100 + tilt[1] * (yy - cy) / PX / 100
    if peel is not None:   # peel: (progress 0..1, direction angle deg) -> lift front sweeps across
        prog, ang = peel
        a = math.radians(ang)
        u = ((xx - cx) * math.cos(a) + (yy - cy) * math.sin(a)) / PX
        umin, umax = u[alpha > 0.5].min(), u[alpha > 0.5].max()
        un = (u - umin) / (umax - umin + 1e-6)
        front = np.clip((prog * 1.6 - un) / 0.6, 0, 1)
        L = L * (front * front * (3 - 2 * front))
    return np.maximum(L, 0).astype(np.float32)


def render_oblique(sc, cam, light, lift1=None, th=0.7, fibres=True, dof_px=0.0, exposure=0.9, grain=0.012, seed=0,
                   kmap_params=None, timing=None, lod_bias=0.0, ss=1, undul=None, pad=0.0):
    tm = {}; t0 = time.time()
    c = sc['canvas']; k = sc['knight']; a1 = sc['k_alpha'].astype(np.float32)
    PX = c['PX']; kx, ky = sc['k_off']
    if pad > 0:   # stumpwork padding grows: extra smooth relief under the figure
        k = dict(k)
        k['h'] = (k['h'] + pad * sc['k_relief_pad']).astype(np.float32)
        k['N'] = normals(k['h'], PX)
        from .shade import ambient_occlusion
        k['ao'] = ambient_occlusion(k['h'], PX)
    H0, W0 = c['h'].shape; H1, W1 = k['h'].shape
    use1 = lift1 is not None
    if lift1 is None:
        lift1 = np.zeros((H1, W1), np.float32)
    lift_eff = (lift1 + 0.06).astype(np.float32)
    if undul is not None:   # the slip rides on the cloth
        lift_eff = (lift_eff + undul[ky:ky + H1, kx:kx + W1]).astype(np.float32)
    L = light_vec(light.get('az', 135), light.get('el', 22))
    l2 = L[:2] / (np.linalg.norm(L[:2]) + 1e-6); tan_el = L[2] / (np.linalg.norm(L[:2]) + 1e-6)
    kp = kmap_params or dict(cx=150, cy=85, r=190, floor=0.5, aspect=1.4)
    km0 = spot((H0, W0), PX, kp['cx'], kp['cy'], kp['r'], kp['floor'], kp['aspect'])
    km1 = km0[ky:ky + H1, kx:kx + W1]
    # ---------- slab shadow + AO on the canvas
    extra = np.ones((H0, W0), np.float32)
    if use1:
        zmax1 = float((lift_eff + k['h']).max())
        zmin1s = float(lift_eff[a1 > 0.5].min() - th)
        if undul is not None: zmin1s -= float(undul.max()) + 0.5
        smax = (zmax1 + 0.5) / tan_el * PX
        bx0 = int(min(kx, kx - l2[0] * smax)) - 4; bx1 = int(max(kx + W1, kx + W1 - l2[0] * smax)) + 4
        by0 = int(min(ky, ky - l2[1] * smax)) - 4; by1 = int(max(ky + H1, ky + H1 - l2[1] * smax)) + 4
        bx0, by0 = max(bx0, 0), max(by0, 0); bx1, by1 = min(bx1, W0), min(by1, H0)
        # half resolution (the shadow is soft): canvas heights downsampled, slab sampled at full res
        hcan = c['h'] if undul is None else (c['h'] + undul)
        hs = cv2.resize(hcan, (W0 // 2, H0 // 2), interpolation=cv2.INTER_AREA)
        vis_h = np.ones(hs.shape, np.float32)
        slab_shadow(hs, float(PX / 2), bx0 // 2, by0 // 2, bx1 // 2, by1 // 2, float(l2[0]), float(l2[1]), float(tan_el),
                    k['h'], a1, lift_eff, float(kx), float(ky), float(th), zmax1, 14.0, vis_h, zmin1s, 2.0)
        vis = cv2.resize(vis_h, (W0, H0), interpolation=cv2.INTER_LINEAR)
        Lm = float(np.median(lift1[a1 > 0.5]))
        vis = cv2.GaussianBlur(vis, (0, 0), 0.5 + 0.045 * Lm / max(tan_el, 0.1) * PX)
        a_full = np.zeros((H0, W0), np.float32); a_full[ky:ky + H1, kx:kx + W1] = (a1 > 0.5)
        occ = cv2.GaussianBlur(a_full, (0, 0), (0.6 * Lm + 1.0) * PX)
        occ_amt = 0.55 * (1 - math.exp(-Lm / 1.5))
        extra = vis
        ao_extra = (1 - occ_amt * occ).astype(np.float32)
    tm['shadow'] = time.time() - t0
    # ---------- shading in texture space (per-texel view vectors)
    ao0 = c['ao'] if not use1 else c['ao'] * ao_extra
    N0 = c['N'] if undul is None else normals(c['h'] + undul, PX)
    # visible canvas footprint from a coarse pre-march
    Wq, Hq = max(cam.W // 8, 8), max(cam.H // 8, 8)
    pos_, fw_, rt_, up_, tx_, ty_ = cam.args()
    lq = np.empty((Hq, Wq), np.int8); Uq = np.empty((Hq, Wq), np.float32); Vq = np.empty((Hq, Wq), np.float32); Tq = np.empty((Hq, Wq), np.float32)
    raymarch(pos_, fw_, rt_, up_, tx_, ty_, Wq, Hq, 0.5, 0.5, c['h'], float(PX), float(c['h'].min()) - 0.5, float(c['h'].max()) + 0.5,
             False, k['h'], a1, lift_eff, float(kx), float(ky), float(th), 0.0, 0.0, lq, Uq, Vq, Tq)
    if (lq == 0).any():
        uu, vv = Uq[lq == 0], Vq[lq == 0]
        reg = (max(int(uu.min()) - 120, 0), max(int(vv.min()) - 120, 0), min(int(uu.max()) + 120, W0), min(int(vv.max()) + 120, H0))
    else:
        reg = None
    cU = c if undul is None else dict(c, h=(c['h'] + undul).astype(np.float32))
    col0, vis0 = relight(cU, cam=tuple(cam.pos), kmap=km0, extra_vis=extra, N=N0, ao=ao0, region=reg, **light)
    col0 = halo(col0, c)
    Lmean = float(np.median(lift1[a1 > 0.5])) if use1 else 0.0
    cam1 = (cam.pos[0] - kx / PX, cam.pos[1] - ky / PX, cam.pos[2] - Lmean)
    col1, vis1 = relight(k, cam=cam1, kmap=km1, **light)
    col1 = halo(col1, k)
    tm['shade'] = time.time() - t0 - tm['shadow']
    # ---------- ray march
    Wo, Ho = cam.W, cam.H
    pos, fw, rt, up, tanx, tany = cam.args()
    hmin0, hmax0 = float(c['h'].min()) - 0.01, float(c['h'].max()) + 0.01
    if undul is not None:
        h0 = (c['h'] + undul).astype(np.float32); hmin0 += float(undul.min()); hmax0 += float(undul.max())
    else:
        h0 = c['h']
    zmin1 = float(lift_eff.min() - th) - 0.01; zmax1 = float((lift_eff + k['h']).max()) + 0.01
    pyr0 = pyramid(col0); pyr1 = pyramid(col1)
    edge = hex_lin('#B49C74') * 0.45
    bg = hex_lin('#120E0B')
    kc = np.array(light.get('key', (1.0, 0.92, 0.80)), np.float32) * light.get('key_i', 2.3)
    fc = np.array(light.get('fill', (0.80, 0.86, 1.0)), np.float32) * light.get('fill_i', 0.3)
    pix_ang = 2 * tany / Ho
    acc = np.zeros((Ho, Wo, 3), np.float32); depth = None
    subs = [(0.5, 0.5)] if ss == 1 else [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)][:ss * ss]
    for (sx_, sy_) in subs:
        lay = np.empty((Ho, Wo), np.int8); U = np.empty((Ho, Wo), np.float32); V = np.empty((Ho, Wo), np.float32)
        T = np.empty((Ho, Wo), np.float32)
        raymarch(pos, fw, rt, up, tanx, tany, Wo, Ho, sx_, sy_, h0, float(PX), hmin0, hmax0,
                 use1, k['h'], a1, lift_eff, float(kx), float(ky), float(th), zmin1, zmax1, lay, U, V, T)
        img = np.empty((Ho, Wo, 3), np.float32)
        gather(lay, U, V, T, pix_ang, float(PX), *pyr0, *pyr1, edge, a1, L, kc, fc, bg, img, float(lod_bias))
        acc += img
        if depth is None: depth = T.copy(); layer = lay.copy()
    img = acc / len(subs)
    tm['march'] = time.time() - t0 - tm['shadow'] - tm['shade']
    # forward depth for fibre depth test / DOF
    yy, xx = np.mgrid[0:Ho, 0:Wo].astype(np.float32)
    sx = (2 * (xx + 0.5) / Wo - 1) * tanx; sy = (1 - 2 * (yy + 0.5) / Ho) * tany
    zf = depth / np.sqrt(1 + sx * sx + sy * sy)
    zf = np.where(layer < 0, 1e6, zf).astype(np.float32)
    if fibres:
        key = kc * float(np.median(km0)); fill = fc
        f0 = sc['fib0']
        render_fibres(img, f0, L, key, fill, vis0, cam.project, V=tuple(-cam.f), depth=zf)
        if use1:
            f1 = dict(sc['fib1']); P = f1['P'].copy()
            rx, ry = f1['root'][:, 0], f1['root'][:, 1]
            P[..., 0] += kx / PX; P[..., 1] += ky / PX; P[..., 2] += lift_eff[ry, rx][:, None]
            if pad > 0: P[..., 2] += pad * sc['k_relief_pad'][ry, rx][:, None]
            f1['P'] = P
            render_fibres(img, f1, L, key, fill, vis1, cam.project, V=tuple(-cam.f), depth=zf)
    tm['fibres'] = time.time() - t0 - tm['shadow'] - tm['shade'] - tm['march']
    if dof_px > 0:
        img, coc = dof(img, zf, cam.focus, dof_px)
    tm['total'] = time.time() - t0
    if timing is not None: timing.update(tm)
    return grade(img, exposure=exposure, grain=grain, seed=seed), zf, layer
