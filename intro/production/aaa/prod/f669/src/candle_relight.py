"""Shot-local patch of chron.shade.relight (the library is read-only): the CANDLE is a point practical in row 0 of
the light table, so the key-light pool (kmap) shapes the candle itself (a guttered candle behind the goblet rim /
a flagged practical) instead of a directional key.  Everything else is the library code path: the same numba
brdf kernel, height-field shadows (shadow_march_point toward the candle), AO, Toksvig, metal environment term.

Installed at runtime with install(); frontal.render() then uses it.  If light has no 'candle' entry the call is
passed through to the library relight unchanged."""
import math
import numpy as np, cv2
from chron import shade, frontal
from chron.shade import (normals, ambient_occlusion, shadow_march_point, brdf, light_vec)
from chron.color import light_colour

_lib_relight = shade.relight


def relight(m, light, cam=None, kmap=None, extra_vis=None, maxd_mm=6.0, soft=0.12, N=None, ao=None, tok=None,
            h_shadow=None, return_vis=False):
    if 'candle' not in light:
        return _lib_relight(m, light, cam=cam, kmap=kmap, extra_vis=extra_vis, maxd_mm=maxd_mm, soft=soft, N=N, ao=ao,
                            tok=tok, h_shadow=h_shadow, return_vis=return_vis)
    h = m['h']; PX = m['PX']
    ox, oy = m.get('origin_mm', (0.0, 0.0))
    hs = h if h_shadow is None else h_shadow
    if N is None: N = m.get('N')
    if N is None: N = normals(hs, PX)
    if ao is None: ao = m.get('ao')
    if ao is None: ao = ambient_occlusion(hs, PX)
    if tok is None: tok = m.get('tok')
    if tok is None: tok = np.zeros(h.shape, np.float32)
    c = light['candle']
    x, y, z = c['pos_mm']
    vis_list = []
    pv = shadow_march_point(hs, float((x - ox) * PX), float((y - oy) * PX), float(z), float(PX),
                            float(maxd_mm * 2 * PX), 1.25, float(soft))
    pv = cv2.GaussianBlur(pv, (0, 0), max(0.5, 0.12 * PX))
    if extra_vis is not None:
        pv = pv * extra_vis
    vis_list.append(pv)
    col = np.asarray(c.get('col', light_colour(c.get('K', 1900), c.get('tint', 0.5))), np.float32) * c['i']
    rows = [[1, x - ox, y - oy, z, *col, 0, float(c.get('ref_mm', 300.0))]]
    for p in light.get('points', []):
        px_, py_, pz_ = p['pos_mm']
        pc = np.asarray(p.get('col', light_colour(p.get('K', 1900), p.get('tint', 0.5))), np.float32) * p['i']
        vi = -1
        if p.get('shadow', False):
            v2 = shadow_march_point(hs, float((px_ - ox) * PX), float((py_ - oy) * PX), float(pz_), float(PX),
                                    float(maxd_mm * 2 * PX), 1.25, float(soft))
            vis_list.append(cv2.GaussianBlur(v2, (0, 0), max(0.5, 0.12 * PX)))
            vi = len(vis_list) - 1
        rows.append([1, px_ - ox, py_ - oy, pz_, *pc, vi, float(p.get('ref_mm', 200.0))])
    Ls = np.array(rows, np.float32)
    vis = np.stack(vis_list, 0).astype(np.float32)
    if kmap is None:
        kmap = np.ones(h.shape, np.float32)
    fc = np.asarray(light['fill'], np.float32) * light['fill_i']
    camv = np.array([-1, -1, -1], np.float32) if cam is None else np.array([cam[0] - ox, cam[1] - oy, cam[2]], np.float32)
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


def install():
    frontal.relight = relight
