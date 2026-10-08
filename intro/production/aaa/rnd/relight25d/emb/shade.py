"""Relighting of 2.5D stitch maps: wrap-Lambert + height-field soft shadows + AO + Kajiya-Kay anisotropic
lobes per material (linen / wool / silk / metal) + grazing sheen. Numba parallel over rows."""
import math
import numpy as np, cv2
from numba import njit, prange

GOLD_F0 = np.array([0.815, 0.515, 0.141], np.float32)  # linear of #E9BE6A


def normals(h, PX, blur=0.6, lod=1.0):
    hs = cv2.GaussianBlur(h, (0, 0), blur) if blur > 0 else h
    gx = cv2.Sobel(hs, cv2.CV_32F, 1, 0, ksize=3) / 8 * PX * lod
    gy = cv2.Sobel(hs, cv2.CV_32F, 0, 1, ksize=3) / 8 * PX * lod
    N = np.dstack([-gx, -gy, np.ones_like(h)])
    N /= np.linalg.norm(N, axis=2, keepdims=True)
    return N.astype(np.float32)


def ambient_occlusion(h, PX):
    a1 = cv2.GaussianBlur(h, (0, 0), 0.8 * PX) - h
    a2 = cv2.GaussianBlur(h, (0, 0), 3.0 * PX) - h
    return np.clip(1 - 1.4 * np.clip(a1, 0, None) - 0.35 * np.clip(a2, 0, None), 0.35, 1).astype(np.float32)


@njit(parallel=True, cache=True)
def shadow_march(h, lx, ly, tan_el, PX, maxd, stepd, soft):
    """visibility (0..1) by marching toward the light in the height field. lx,ly: unit screen dir to light."""
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
def brdf(alb, N, T, mat, ao, vis, kmap, L, kc, fc, rimL, rimc, camx, camy, camz, h, PX, out, spec_scale):
    H, W, _ = alb.shape
    Lx, Ly, Lz = L[0], L[1], L[2]
    for y in prange(H):
        for x in range(W):
            nx = N[y, x, 0]; ny = N[y, x, 1]; nz = N[y, x, 2]
            # view vector
            if camz > 0:
                vx = camx - x / PX; vy = camy - y / PX; vz = camz - h[y, x]
                vl = math.sqrt(vx * vx + vy * vy + vz * vz); vx /= vl; vy /= vl; vz /= vl
            else:
                vx = 0.0; vy = 0.0; vz = 1.0
            m = mat[y, x]
            ar = alb[y, x, 0]; ag = alb[y, x, 1]; ab = alb[y, x, 2]
            amax = max(ar, max(ag, ab)) + 1e-6
            # tangent orthogonalised to N
            tx = T[y, x, 0]; ty = T[y, x, 1]; tz = 0.0
            tn = tx * nx + ty * ny
            tx -= tn * nx; ty -= tn * ny; tz -= tn * nz
            tl = math.sqrt(tx * tx + ty * ty + tz * tz) + 1e-6
            tx /= tl; ty /= tl; tz /= tl
            ndv = nx * vx + ny * vy + nz * vz
            km = kmap[y, x]
            rr = 0.0; gg = 0.0; bb = 0.0
            # ---- two directional lights: key (with shadows) + rim (unshadowed, grazing)
            for li in range(2):
                if li == 0:
                    lx = Lx; ly = Ly; lz = Lz; cr = kc[0] * km; cg = kc[1] * km; cb = kc[2] * km; vv = vis[y, x]
                else:
                    lx = rimL[0]; ly = rimL[1]; lz = rimL[2]; cr = rimc[0]; cg = rimc[1]; cb = rimc[2]; vv = 1.0
                    if cr + cg + cb <= 0: continue
                ndl = nx * lx + ny * ly + nz * lz
                diff = (ndl + 0.25) / 1.25
                if diff < 0: diff = 0.0
                hx = lx + vx; hy = ly + vy; hz = lz + vz
                hl = math.sqrt(hx * hx + hy * hy + hz * hz) + 1e-6
                hx /= hl; hy /= hl; hz /= hl
                tdh = tx * hx + ty * hy + tz * hz
                sth = math.sqrt(max(0.0, 1 - tdh * tdh))
                fade = (ndl + 0.1) / 0.35
                if fade < 0: fade = 0.0
                if fade > 1: fade = 1.0
                fade = fade * fade * (3 - 2 * fade)
                sr = 0.0; sg = 0.0; sb = 0.0
                dmul = 1.0
                if m == 0:      # linen
                    k = 0.05 * sth ** 24
                    sr = k; sg = k; sb = k
                    gz = 0.04 * (1 - ndv) ** 2
                    sr += gz * (ar * 0.8 + 0.08); sg += gz * (ag * 0.8 + 0.08); sb += gz * (ab * 0.8 + 0.08)
                elif m == 1 or m == 4:  # wool
                    k = 0.045 * sth ** 8
                    tint = 0.6
                    sr = k * (tint + 0.4 * ar / amax); sg = k * (tint + 0.4 * ag / amax); sb = k * (tint + 0.4 * ab / amax)
                    k2 = 0.09 * sth ** 3
                    sr += k2 * ar; sg += k2 * ag; sb += k2 * ab
                    gz = 0.12 * (1 - ndv) ** 2
                    sr += gz * (ar * 0.8 + 0.08); sg += gz * (ag * 0.8 + 0.08); sb += gz * (ab * 0.8 + 0.08)
                elif m == 2:    # silk / floss satin
                    ndh = nx * hx + ny * hy + nz * hz
                    if ndh < 0: ndh = 0.0
                    k = 0.18 * sth ** 40 * (0.35 + 0.65 * ndh ** 6)
                    sr = k * (0.5 + 0.5 * ar / amax); sg = k * (0.5 + 0.5 * ag / amax); sb = k * (0.5 + 0.5 * ab / amax)
                    k2 = 0.06 * sth ** 4
                    sr += k2 * ar; sg += k2 * ag; sb += k2 * ab
                else:           # couched metal (silver-gilt): narrow glint across the thread + weak broad lobe
                    ndh = nx * hx + ny * hy + nz * hz
                    if ndh < 0: ndh = 0.0
                    k = 2.6 * sth ** 90 * ndh ** 20 + 0.30 * sth ** 40 * ndh ** 10 + 0.45 * ndh ** 80 + 0.03 * sth ** 4
                    sr = k * ar / amax; sg = k * ag / amax; sb = k * ab / amax
                    dmul = 0.16
                sr *= fade * spec_scale; sg *= fade * spec_scale; sb *= fade * spec_scale
                rr += (ar * dmul * diff + sr) * cr * vv
                gg += (ag * dmul * diff + sg) * cg * vv
                bb += (ab * dmul * diff + sb) * cb * vv
            a = ao[y, x]
            if m == 3:  # metal: dark diffuse + warm environment reflection (room / candles), view dependent
                env = 0.06 * (0.4 + 0.6 * nz) * km
                out[y, x, 0] = rr + ar * 0.25 * fc[0] * a + ar * env * kc[0] * 0.35
                out[y, x, 1] = gg + ag * 0.25 * fc[1] * a + ag * env * kc[1] * 0.35
                out[y, x, 2] = bb + ab * 0.25 * fc[2] * a + ab * env * kc[2] * 0.35
            else:
                out[y, x, 0] = rr + ar * fc[0] * a * (0.6 + 0.4 * nz)
                out[y, x, 1] = gg + ag * fc[1] * a * (0.6 + 0.4 * nz)
                out[y, x, 2] = bb + ab * fc[2] * a * (0.6 + 0.4 * nz)
    return out


def light_vec(az_deg, el_deg):
    az, el = math.radians(az_deg), math.radians(el_deg)
    L = np.array([math.cos(az) * math.cos(el), -math.sin(az) * math.cos(el), math.sin(el)], np.float32)
    return L / np.linalg.norm(L)


def relight(m, az=135, el=22, key=(1.0, 0.92, 0.80), key_i=2.3, fill=(0.80, 0.86, 1.0), fill_i=0.30,
            rim_az=30, rim_el=8, rim_i=0.0, cam=None, kmap=None, extra_vis=None, maxd_mm=6.0, soft=0.12,
            spec_scale=1.0, N=None, ao=None, region=None):
    """m: maps dict (h, alb, T, mat, PX). Returns linear RGB float32. region=(x0,y0,x1,y1) shades a window only."""
    if region is not None:
        x0, y0, x1, y1 = region
        sl = (slice(y0, y1), slice(x0, x1))
        PX = m['PX']
        ms = {k: (v[sl] if isinstance(v, np.ndarray) and v.ndim >= 2 else v) for k, v in m.items()}
        Ns = (N if N is not None else m.get('N'))
        aos = (ao if ao is not None else m.get('ao'))
        cs = None if cam is None else (cam[0] - x0 / PX, cam[1] - y0 / PX, cam[2])
        o, v = relight(ms, az, el, key, key_i, fill, fill_i, rim_az, rim_el, rim_i, cs,
                       None if kmap is None else kmap[sl], None if extra_vis is None else extra_vis[sl], maxd_mm, soft,
                       spec_scale, None if Ns is None else Ns[sl], None if aos is None else aos[sl])
        full = np.zeros(m['alb'].shape, np.float32); full[sl] = o
        fv = np.ones(m['h'].shape, np.float32); fv[sl] = v
        return full, fv
    h = m['h']; PX = m['PX']
    if N is None: N = m.get('N')
    if N is None: N = normals(h, PX)
    if ao is None: ao = m.get('ao')
    if ao is None: ao = ambient_occlusion(h, PX)
    L = light_vec(az, el)
    l2 = L[:2] / (np.linalg.norm(L[:2]) + 1e-6)
    tan_el = L[2] / (np.linalg.norm(L[:2]) + 1e-6)
    maxd = min(maxd_mm * PX, 2.2 / max(tan_el, 0.05) * PX)
    vis = shadow_march(h, float(l2[0]), float(l2[1]), float(tan_el), float(PX), float(maxd), 1.25, float(soft))
    vis = cv2.GaussianBlur(vis, (0, 0), 0.12 * PX)
    if extra_vis is not None:
        vis = vis * extra_vis
    if kmap is None:
        kmap = np.ones(h.shape, np.float32)
    kc = np.array(key, np.float32) * key_i
    fc = np.array(fill, np.float32) * fill_i
    rimL = light_vec(rim_az, rim_el)
    rimc = np.array(key, np.float32) * rim_i
    if cam is None:
        camx = camy = 0.0; camz = -1.0
    else:
        camx, camy, camz = map(float, cam)
    out = np.empty(m['alb'].shape, np.float32)
    brdf(m['alb'], N, m['T'], m['mat'], ao, vis.astype(np.float32), kmap.astype(np.float32), L, kc, fc, rimL, rimc,
         camx, camy, camz, h, float(PX), out, float(spec_scale))
    return out, vis
