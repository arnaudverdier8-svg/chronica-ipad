"""R25 production shading: LOD-banded normals (G7), two-scale AO, height-field shadows toward directional and point
lights, wrap-Lambert + Kajiya-Kay lobes per material (Toksvig-widened), grazing sheen, and the gate-G2 metal
environment term (warm prefiltered studio gradient, so couched gold returns a crest band at ANY key azimuth).
Units: mm; maps in px at PX px/mm; x right, y down, z toward the viewer.  (<- R25 shade.py)"""
import math
import numpy as np, cv2
from numba import njit, prange
from .color import light_colour

GOLD_F0 = np.array([0.815, 0.515, 0.141], np.float32)  # linear of #E9BE6A

# band split of the height field (periods in mm used for the LOD fade)
BAND_SIG_MM = (0.25, 0.8)          # gaussian sigmas separating fine | strand | structure
BAND_PERIOD_MM = (0.6, 0.85)       # nominal periods of the fine (weave/ply) and strand bands


LOD_P0, LOD_RAMP = 1.2, 1.5     # band fully faded at <= 1.2 screen px period, full strength at >= 2.7 px


def lod_weight(period_mm, screen_px_per_mm):
    """band normal weight: clamp((p_px - LOD_P0) / LOD_RAMP, 0, 1) with p_px = band period in screen px.
    (pipeline 5.2 proposed P0 = 2 px; measured on the F0 truck, P0 = 1.2 keeps the strand relief with the HF
    residual still ~0.4 % - far inside the +3 point budget - so the production default is 1.2)."""
    return float(np.clip((period_mm * screen_px_per_mm - LOD_P0) / LOD_RAMP, 0.0, 1.0))


def lod_height(h, PX, screen_px_per_mm):
    """height with the fine and strand bands faded for the current screen density. Returns (h_lod, weights)."""
    s0, s1 = BAND_SIG_MM
    if s0 * PX < 0.35:      # the fine band is not even representable at this map density
        g0 = h
    else:
        g0 = cv2.GaussianBlur(h, (0, 0), s0 * PX)
    g1 = cv2.GaussianBlur(h, (0, 0), s1 * PX)
    wA = lod_weight(BAND_PERIOD_MM[0], screen_px_per_mm)
    wB = lod_weight(BAND_PERIOD_MM[1], screen_px_per_mm)
    return (g1 + wB * (g0 - g1) + wA * (h - g0)).astype(np.float32), (wA, wB)


def normals(h, PX, blur=0.6, lod=1.0):
    hs = cv2.GaussianBlur(h, (0, 0), blur) if blur > 0 else h
    gx = cv2.Sobel(hs, cv2.CV_32F, 1, 0, ksize=3) / 8 * PX * lod
    gy = cv2.Sobel(hs, cv2.CV_32F, 0, 1, ksize=3) / 8 * PX * lod
    N = np.dstack([-gx, -gy, np.ones_like(h)])
    N /= np.linalg.norm(N, axis=2, keepdims=True)
    return N.astype(np.float32)


def toksvig(h, PX, footprint_px):
    """per-pixel lobe widening factor tok = (1 - |<N>|) / |<N>| from the full-detail normals averaged over the
    screen-pixel footprint; exponent_eff = s / (1 + s * tok)."""
    N = normals(h, PX, blur=0.0)
    sig = max(0.5, 0.5 * footprint_px)
    Nb = cv2.GaussianBlur(N, (0, 0), sig)
    L = np.clip(np.linalg.norm(Nb, axis=2), 1e-3, 1.0)
    return ((1 - L) / L).astype(np.float32)


def ambient_occlusion(h, PX):
    a1 = cv2.GaussianBlur(h, (0, 0), 0.8 * PX) - h
    a2 = cv2.GaussianBlur(h, (0, 0), 3.0 * PX) - h
    return np.clip(1 - 1.4 * np.clip(a1, 0, None) - 0.35 * np.clip(a2, 0, None), 0.35, 1).astype(np.float32)


@njit(parallel=True, cache=True)
def shadow_march(h, lx, ly, tan_el, PX, maxd, stepd, soft):
    """visibility (0..1) by marching toward a directional light. lx,ly: unit screen dir to light."""
    H, W = h.shape
    vis = np.ones((H, W), np.float32)
    nst = int(maxd / stepd)
    for y in prange(H):
        for x in range(W):
            h0 = h[y, x]
            ex = 0.0
            for k in range(1, nst + 1):
                d = k * stepd
                xs = int(x + lx * d + 0.5); ys = int(y + ly * d + 0.5)
                if xs < 0 or ys < 0 or xs >= W or ys >= H: break
                e = h[ys, xs] - (h0 + d / PX * tan_el)
                if e > ex: ex = e
            v = 1.0 - ex / soft
            if v < 0: v = 0.0
            vis[y, x] = v
    return vis


@njit(parallel=True, cache=True)
def shadow_march_point(h, px, py, pz, PX, maxd, stepd, soft):
    """visibility toward a point light at (px, py) map px and height pz mm (per-pixel direction)."""
    H, W = h.shape
    vis = np.ones((H, W), np.float32)
    for y in prange(H):
        for x in range(W):
            dx = px - x; dy = py - y
            dist = math.sqrt(dx * dx + dy * dy) + 1e-6
            lx = dx / dist; ly = dy / dist
            h0 = h[y, x]
            tan_el = (pz - h0) / (dist / PX)
            if tan_el < 0.02: tan_el = 0.02
            lim = min(maxd, dist)
            nst = int(lim / stepd)
            ex = 0.0
            for k in range(1, nst + 1):
                d = k * stepd
                xs = int(x + lx * d + 0.5); ys = int(y + ly * d + 0.5)
                if xs < 0 or ys < 0 or xs >= W or ys >= H: break
                e = h[ys, xs] - (h0 + d / PX * tan_el)
                if e > ex: ex = e
            v = 1.0 - ex / soft
            if v < 0: v = 0.0
            vis[y, x] = v
    return vis


@njit(cache=True, inline='always')
def _env(rx, ry, rz, bx, by, bz, inv_w2, dome):
    """warm studio gradient: softbox lobe (direction b, width ~35 deg) + broad dome; dark floor."""
    if rz <= 0.0:
        return 0.0
    c = rx * bx + ry * by + rz * bz
    if c > 1.0: c = 1.0
    a = math.acos(c)
    return math.exp(-a * a * inv_w2) + dome * (0.4 + 0.6 * rz)


@njit(parallel=True, cache=True)
def brdf(alb, N, T, mat, ao, tok, vis, kmap, Ls, fc, cam, h, PX, out, spec_scale, envp):
    """Ls: (nl, 9) rows [type(0 dir / 1 point), x, y, z (dir or pos in mm), r, g, b, vis_index(-1 none), ref_mm].
    Row 0 is the key (multiplied by kmap). envp: [k_env, bx, by, bz, inv_w2, dome, er, eg, eb]."""
    H, W, _ = alb.shape
    nl = Ls.shape[0]
    camx = cam[0]; camy = cam[1]; camz = cam[2]
    for y in prange(H):
        for x in range(W):
            nx = N[y, x, 0]; ny = N[y, x, 1]; nz = N[y, x, 2]
            if camz > 0:
                vx = camx - x / PX; vy = camy - y / PX; vz = camz - h[y, x]
                vl = math.sqrt(vx * vx + vy * vy + vz * vz); vx /= vl; vy /= vl; vz /= vl
            else:
                vx = 0.0; vy = 0.0; vz = 1.0
            m = mat[y, x]
            ar = alb[y, x, 0]; ag = alb[y, x, 1]; ab = alb[y, x, 2]
            amax = max(ar, max(ag, ab)) + 1e-6
            tx = T[y, x, 0]; ty = T[y, x, 1]; tz = 0.0
            tn = tx * nx + ty * ny
            tx -= tn * nx; ty -= tn * ny; tz -= tn * nz
            tl = math.sqrt(tx * tx + ty * ty + tz * tz) + 1e-6
            tx /= tl; ty /= tl; tz /= tl
            ndv = nx * vx + ny * vy + nz * vz
            tk = tok[y, x]
            km = kmap[y, x]
            rr = 0.0; gg = 0.0; bb = 0.0
            for li in range(nl):
                typ = Ls[li, 0]
                if typ == 0:
                    lx = Ls[li, 1]; ly = Ls[li, 2]; lz = Ls[li, 3]; att = 1.0
                else:
                    lx = Ls[li, 1] - x / PX; ly = Ls[li, 2] - y / PX; lz = Ls[li, 3] - h[y, x]
                    dd = math.sqrt(lx * lx + ly * ly + lz * lz) + 1e-6
                    lx /= dd; ly /= dd; lz /= dd
                    att = (Ls[li, 8] / dd) ** 2
                cr = Ls[li, 4] * att; cg = Ls[li, 5] * att; cb = Ls[li, 6] * att
                if li == 0:
                    cr *= km; cg *= km; cb *= km
                vi = int(Ls[li, 7])
                vv = vis[vi, y, x] if vi >= 0 else 1.0
                if cr + cg + cb <= 0 or vv <= 0: continue
                ndl = nx * lx + ny * ly + nz * lz
                diff = (ndl + 0.25) / 1.25
                if diff < 0: diff = 0.0
                hx = lx + vx; hy = ly + vy; hz = lz + vz
                hl = math.sqrt(hx * hx + hy * hy + hz * hz) + 1e-6
                hx /= hl; hy /= hl; hz /= hl
                tdh = tx * hx + ty * hy + tz * hz
                sth = math.sqrt(max(0.0, 1 - tdh * tdh))
                ndh = nx * hx + ny * hy + nz * hz
                if ndh < 0: ndh = 0.0
                fade = (ndl + 0.1) / 0.35
                if fade < 0: fade = 0.0
                if fade > 1: fade = 1.0
                fade = fade * fade * (3 - 2 * fade)
                sr = 0.0; sg = 0.0; sb = 0.0
                dmul = 1.0
                if m == 0 or m == 7:      # linen / parchment
                    e = 24.0 / (1.0 + 24.0 * tk)
                    k = 0.05 * sth ** e
                    sr = k; sg = k; sb = k
                    gz = 0.04 * (1 - ndv) ** 2
                    sr += gz * (ar * 0.8 + 0.08); sg += gz * (ag * 0.8 + 0.08); sb += gz * (ab * 0.8 + 0.08)
                elif m == 1 or m == 4 or m == 5 or m == 8:   # wool, ink, cord, felt
                    e1 = 8.0 / (1.0 + 8.0 * tk); e2 = 3.0 / (1.0 + 3.0 * tk)
                    k = 0.045 * sth ** e1
                    sr = k * (0.6 + 0.4 * ar / amax); sg = k * (0.6 + 0.4 * ag / amax); sb = k * (0.6 + 0.4 * ab / amax)
                    k2 = 0.06 * sth ** e2
                    sr += k2 * ar; sg += k2 * ag; sb += k2 * ab
                    gz = 0.12 * (1 - nz) ** 2
                    sr += gz * (ar * 0.8 + 0.08); sg += gz * (ag * 0.8 + 0.08); sb += gz * (ab * 0.8 + 0.08)
                elif m == 2:    # silk / floss satin
                    e1 = 40.0 / (1.0 + 40.0 * tk)
                    k = 0.15 * sth ** e1 * (0.35 + 0.65 * ndh ** 6)
                    sr = k * (0.5 + 0.5 * ar / amax); sg = k * (0.5 + 0.5 * ag / amax); sb = k * (0.5 + 0.5 * ab / amax)
                    k2 = 0.06 * sth ** 4
                    sr += k2 * ar; sg += k2 * ag; sb += k2 * ab
                elif m == 3:    # couched metal: wider anisotropic glint across the thread + broad lobe
                    e1 = 60.0 / (1.0 + 60.0 * tk); e2 = 18.0 / (1.0 + 18.0 * tk)
                    k = 1.5 * sth ** e1 * ndh ** 6 + 0.35 * sth ** e2 * ndh ** 3 + 0.25 * ndh ** 40 + 0.03 * sth ** 4
                    sr = k * ar / amax; sg = k * ag / amax; sb = k * ab / amax
                    dmul = 0.22
                else:           # walnut etc.
                    k = 0.08 * ndh ** 30
                    sr = k; sg = k; sb = k
                sr *= fade * spec_scale; sg *= fade * spec_scale; sb *= fade * spec_scale
                rr += (ar * dmul * diff + sr) * cr * vv
                gg += (ag * dmul * diff + sg) * cg * vv
                bb += (ab * dmul * diff + sb) * cb * vv
            a = ao[y, x]
            if m == 3:
                # metal environment term: R = reflect(-V, N_strand); warm studio gradient; F = gold tint
                ndv2 = 2.0 * ndv
                rx = ndv2 * nx - vx; ry = ndv2 * ny - vy; rz = ndv2 * nz - vz
                E = _env(rx, ry, rz, envp[1], envp[2], envp[3], envp[4], envp[5])
                kk = envp[0] * E * a * (0.5 + 0.5 * km) * spec_scale
                out[y, x, 0] = rr + ar * 0.25 * fc[0] * a + kk * envp[6] * ar / amax
                out[y, x, 1] = gg + ag * 0.25 * fc[1] * a + kk * envp[7] * ag / amax
                out[y, x, 2] = bb + ab * 0.25 * fc[2] * a + kk * envp[8] * ab / amax
            else:
                out[y, x, 0] = rr + ar * fc[0] * a * (0.6 + 0.4 * nz)
                out[y, x, 1] = gg + ag * fc[1] * a * (0.6 + 0.4 * nz)
                out[y, x, 2] = bb + ab * fc[2] * a * (0.6 + 0.4 * nz)
    return out


def light_vec(az_deg, el_deg):
    """unit vector toward a light at azimuth az (deg, 0 = +x right, 90 = up the image) and elevation el."""
    az, el = math.radians(az_deg), math.radians(el_deg)
    L = np.array([math.cos(az) * math.cos(el), -math.sin(az) * math.cos(el), math.sin(el)], np.float32)
    return L / np.linalg.norm(L)


def rig(az=135, el=22, K=3000, key_i=2.6, tint=0.35, fill_ratio=3.0, fill_K=8000, rim_az=30, rim_el=8, rim_i=0.0,
        points=(), k_env=0.35, env_el=62.0, env_w_deg=35.0, env_dome=0.08, key=None, fill=None, fill_i=None, spec_scale=1.0):
    """light rig dict for relight().  points: dicts {pos_mm: (x, y, z) in SHEET mm, K, i, ref_mm, shadow}.
    key/fill override the Kelvin colours (R25-compatible); fill_i overrides key_i / fill_ratio."""
    kc = np.asarray(key, np.float32) if key is not None else light_colour(K, tint)
    fcol = np.asarray(fill, np.float32) if fill is not None else light_colour(fill_K, 0.25)
    fi = fill_i if fill_i is not None else key_i / fill_ratio * 0.35
    return dict(az=az, el=el, key=kc, key_i=key_i, fill=fcol, fill_i=fi, rim_az=rim_az, rim_el=rim_el, rim_i=rim_i,
                points=list(points), k_env=k_env, env_el=env_el, env_w_deg=env_w_deg, env_dome=env_dome, spec_scale=spec_scale)


def relight(m, light, cam=None, kmap=None, extra_vis=None, maxd_mm=6.0, soft=0.12, N=None, ao=None, tok=None,
            h_shadow=None, return_vis=False):
    """m: maps dict (h, alb, T, mat, PX, origin_mm optional).  light: dict from rig() (or the R25 light dict).
    cam: (x, y, z) mm in SHEET coordinates (None = orthographic frontal).  Returns linear RGB (and key visibility)."""
    if 'points' not in light:
        light = rig(**{k: v for k, v in light.items() if k in ('az', 'el', 'key', 'key_i', 'fill', 'fill_i', 'rim_az', 'rim_el',
                                                                    'rim_i', 'spec_scale')})
    h = m['h']; PX = m['PX']
    ox, oy = m.get('origin_mm', (0.0, 0.0))
    hs = h if h_shadow is None else h_shadow
    if N is None: N = m.get('N')
    if N is None: N = normals(hs, PX)
    if ao is None: ao = m.get('ao')
    if ao is None: ao = ambient_occlusion(hs, PX)
    if tok is None: tok = m.get('tok')
    if tok is None: tok = np.zeros(h.shape, np.float32)
    L = light_vec(light['az'], light['el'])
    l2 = L[:2] / (np.linalg.norm(L[:2]) + 1e-6)
    tan_el = L[2] / (np.linalg.norm(L[:2]) + 1e-6)
    maxd = min(maxd_mm * PX, 2.2 / max(tan_el, 0.05) * PX)
    vis_list = []
    v = shadow_march(hs, float(l2[0]), float(l2[1]), float(tan_el), float(PX), float(maxd), 1.25, float(soft))
    v = cv2.GaussianBlur(v, (0, 0), max(0.5, 0.12 * PX))
    if extra_vis is not None:
        v = v * extra_vis
    vis_list.append(v)
    rows = [[0, L[0], L[1], L[2], *(np.asarray(light['key'], np.float32) * light['key_i']), 0, 1.0]]
    if light.get('rim_i', 0) > 0:
        R = light_vec(light['rim_az'], light['rim_el'])
        rows.append([0, R[0], R[1], R[2], *(np.asarray(light['key'], np.float32) * light['rim_i']), -1, 1.0])
    for p in light.get('points', []):
        x, y, z = p['pos_mm']
        col = np.asarray(p.get('col', light_colour(p.get('K', 1900), p.get('tint', 0.5))), np.float32) * p['i']
        vi = -1
        if p.get('shadow', True):
            pv = shadow_march_point(hs, float((x - ox) * PX), float((y - oy) * PX), float(z), float(PX), float(maxd_mm * 2 * PX), 1.25,
                                    float(soft))
            vis_list.append(cv2.GaussianBlur(pv, (0, 0), max(0.5, 0.12 * PX)))
            vi = len(vis_list) - 1
        rows.append([1, x - ox, y - oy, z, *col, vi, float(p.get('ref_mm', 200.0))])
    Ls = np.array(rows, np.float32)
    vis = np.stack(vis_list, 0).astype(np.float32)
    if kmap is None:
        kmap = np.ones(h.shape, np.float32)
    fc = np.asarray(light['fill'], np.float32) * light['fill_i']
    camv = np.array([-1, -1, -1], np.float32) if cam is None else np.array([cam[0] - ox, cam[1] - oy, cam[2]], np.float32)
    # environment: softbox toward the key azimuth at env_el, width env_w
    B = light_vec(light['az'], light.get('env_el', 62.0))
    w = math.radians(light.get('env_w_deg', 35.0))
    kc = np.asarray(light['key'], np.float32) * light['key_i']
    envp = np.array([light.get('k_env', 0.35), B[0], B[1], B[2], 1.0 / (w * w), light.get('env_dome', 0.08), *kc], np.float32)
    out = np.empty(m['alb'].shape, np.float32)
    brdf(np.ascontiguousarray(m['alb'], np.float32), np.ascontiguousarray(N, np.float32), np.ascontiguousarray(m['T'], np.float32),
         np.ascontiguousarray(m['mat']), ao.astype(np.float32), tok.astype(np.float32), vis, kmap.astype(np.float32), Ls, fc, camv,
         np.ascontiguousarray(h, np.float32), float(PX), out, float(light.get('spec_scale', 1.0)), envp)
    if return_vis:
        return out, vis[0]
    return out


def spot(shape, PX, cx_mm, cy_mm, r_mm, floor=0.55, aspect=1.0, origin_mm=(0.0, 0.0)):
    """key-light pool (kmap): 1 at the centre falling to `floor`; coordinates in sheet mm."""
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot((xx / PX + origin_mm[0] - cx_mm) / aspect, yy / PX + origin_mm[1] - cy_mm) / r_mm
    return (floor + (1 - floor) * np.exp(-d * d)).astype(np.float32)
