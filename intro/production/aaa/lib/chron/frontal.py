"""R25-F frontal (rostrum) renderer: mip select (1.0-1.4x rule) -> optional per-frame edits (ageing, unpick, stitch-on)
-> LOD-banded normals + Toksvig -> relight (key, rim, point practicals, metal env) -> halo -> Lanczos warp to screen
-> calibrated fibres (>= 4 px/mm) -> linear frame + coverage alpha (G4).

    from chron.maps import MapSet
    from chron import frontal, shade
    ms = MapSet(f'{MAPS}/p1_oath')
    fr = frontal.render(ms, view=dict(cx_mm=295, cy_mm=170, px_per_mm=4.65), light=shade.rig(az=135, el=22, K=3000))
    img8 = grade.grade(fr['lin'], act='I', seed=frame)
"""
import time, math
import numpy as np, cv2
from . import shade
from .shade import relight, normals, ambient_occlusion, lod_height, toksvig, light_vec, spot
from .fibres import halo, make_fibres, render_fibres
from .ageing import apply_age
from .qa.void import check_void

OUT_WH = (2560, 1440)


def view_rect(view, out_wh=OUT_WH):
    """view: dict(cx_mm, cy_mm, px_per_mm) | dict(x0_mm, y0_mm, px_per_mm) -> (x0, y0, w, h, s) in sheet mm."""
    s = float(view['px_per_mm'])
    w, h = out_wh[0] / s, out_wh[1] / s
    if 'cx_mm' in view:
        x0, y0 = view['cx_mm'] - w / 2, view['cy_mm'] - h / 2
    else:
        x0, y0 = view['x0_mm'], view['y0_mm']
    return x0, y0, w, h, s


def read_window(src, rect_mm, level, margin_mm=8.0):
    x0, y0, w, h = rect_mm
    if isinstance(src, dict):     # already a working-maps dict covering the area (origin_mm, PX)
        return src
    return src.read(x0 - margin_mm, y0 - margin_mm, x0 + w + margin_mm, y0 + h + margin_mm, level)


def h_for_shadow(m):
    return m['h'].astype(np.float32)


def prepare(m, screen_px_per_mm, lod=True):
    """LOD normals, AO, Toksvig for the current screen density (in place).  Returns m."""
    PX = m['PX']
    h = m['h'].astype(np.float32)
    if lod:
        hl, w = lod_height(h, PX, screen_px_per_mm)
    else:
        hl, w = h, (1, 1)
    m['h_lod'] = hl
    m['N'] = normals(hl, PX, blur=0.6)
    m['ao'] = ambient_occlusion(h, PX)
    m['tok'] = toksvig(h, PX, max(1.0, PX / screen_px_per_mm)) if lod else np.zeros(h.shape, np.float32)
    m['lod_w'] = w
    return m


def render(src, view, light, out_wh=OUT_WH, level=None, fib='auto', fib_seed=0, fib_density=0.7, kmap=None, cam=None,
           age=None, edit=None, lod=True, timing=None, overlay=None, return_maps=False, margin_mm=8.0, halo_fn=None):
    """src: MapSet or working maps dict (with PX, origin_mm).  view: see view_rect (sheet mm).  light: shade.rig().
    kmap: None | dict(cx_mm, cy_mm, r_mm, floor, aspect) | callable(maps)->HxW.  cam: (x, y, z) sheet mm (default:
    above the view centre at 1200 mm).  age: None | amount | callable(maps)->amount (apply_age with the sheet's age_*
    layers).  edit: callable(maps) modifying the window maps in place (unpick / stitch-on / slips).
    fib: 'auto' (built from the window, seeded) | fibre dict in sheet mm | None.  Returns dict(lin, alpha, level, ...)."""
    t0 = time.time()
    x0, y0, w, h, s = view_rect(view, out_wh)
    if level is None:
        level = src.level_for(s) if not isinstance(src, dict) else 0
    if not isinstance(src, dict) and s > 1.4 * src.PX:
        print(f'[frontal] warning: {s:.1f} screen px/mm magnifies the {src.PX:.0f} px/mm bake > 1.4x (re-bake denser or cut to Eevee)')
    m = read_window(src, (x0, y0, w, h), level, margin_mm)
    PX = m['PX']; ox, oy = m['origin_mm']
    if edit is not None:          # edits (stitch-on / unpick / slips) first, so ageing applies to the re-rasterised patch too
        edit(m)
    if age is not None:
        amt = age(m) if callable(age) else age
        layers = {k: m[k] for k in ('age_fox', 'age_tide', 'age_fade') if k in m}
        m['alb'] = apply_age(m['alb'], m['mat'], amt, layers, ghost=m.get('ghost'))
    t1 = time.time()
    prepare(m, s, lod)
    if kmap is None:
        km = None
    elif callable(kmap):
        km = kmap(m)
    else:
        km = spot(m['h'].shape, PX, kmap['cx_mm'], kmap['cy_mm'], kmap['r_mm'], kmap.get('floor', 0.5), kmap.get('aspect', 1.0), (ox, oy))
    if cam is None:
        cam = (x0 + w / 2, y0 + h / 2, 1200.0)
    col, vis = relight(m, light, cam=cam, kmap=km, h_shadow=h_for_shadow(m), return_vis=True)
    col = (halo_fn or halo)(col, m)
    t2 = time.time()
    # warp map px -> screen px
    r = PX / s
    if r > 1.2:
        col = cv2.GaussianBlur(col, (0, 0), 0.5 * math.sqrt(r * r - 1))
    M = np.array([[s / PX, 0, (ox - x0) * s + 0.5 * (s / PX - 1)], [0, s / PX, (oy - y0) * s + 0.5 * (s / PX - 1)]], np.float32)
    img = cv2.warpAffine(col, M, out_wh, flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
    ones = m['valid'].astype(np.float32) if 'valid' in m else np.ones(m['h'].shape, np.float32)
    alpha = cv2.warpAffine(ones, M, out_wh, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    img = np.maximum(img, 0)
    t3 = time.time()
    if overlay is not None:
        overlay(img, dict(x0=x0, y0=y0, s=s, m=m, vis=vis, light=light))
    if fib == 'auto' and s >= 4.0:
        fb = make_fibres(m, density=fib_density, seed=fib_seed, origin_px=(int(round(ox * PX)), int(round(oy * PX))))
        if fb is not None:
            fb['frame'] = 'window'
    elif isinstance(fib, dict):
        fb = fib
    elif callable(fib):
        fb = fib(m)
    else:
        fb = None
    if fb is not None and s >= 4.0:
        L = light_vec(light['az'], light['el'])
        key = np.asarray(light['key'], np.float32) * light['key_i']
        if km is not None:
            key = key * float(np.median(km))
        fill = np.asarray(light['fill'], np.float32) * light['fill_i']

        def project(P):
            Q = np.empty(P.shape[:2] + (2,), np.float32)
            Q[..., 0] = (P[..., 0] - x0) * s; Q[..., 1] = (P[..., 1] - y0) * s
            return Q, -P[..., 2]
        render_fibres(img, fb, L, key, fill, vis, project, width=min(1.0, s * 0.11),
                      root_offset=(int(round(ox * PX)), int(round(oy * PX))) if fb.get('frame') != 'window' else (0, 0))
    t4 = time.time()
    if timing is not None:
        timing.update(read=t1 - t0, relight=t2 - t1, warp=t3 - t2, fibres=t4 - t3, level=level)
    out = dict(lin=img, alpha=alpha, level=level, px_per_mm=s, rect_mm=(x0, y0, w, h), map_px=PX)
    if return_maps:
        out['maps'] = m; out['vis'] = vis
    return out


def render_checked(*a, **k):
    """render() + gate G4 (raises VoidError on any void pixel)."""
    fr = render(*a, **k)
    check_void(fr['lin'], fr['alpha'], name=str(k.get('view')))
    return fr


def shot_fibres(src, rect_mm, level, seed=0, density=0.7):
    """ONE fibre set for a whole shot (camera moves must not re-seed fibres): rect_mm = (x0, y0, x1, y1) sheet mm
    covering every frame of the shot, level = the shading level the shot uses.  Pass as render(fib=...)."""
    x0, y0, x1, y1 = rect_mm
    m = src.read(x0, y0, x1, y1, level)
    PX = m['PX']; ox, oy = int(round(m['origin_mm'][0] * PX)), int(round(m['origin_mm'][1] * PX))
    fb = make_fibres(m, density=density, seed=seed, origin_px=(ox, oy))
    if fb is not None:
        fb['root'] = fb['root'] + np.array([ox, oy], np.int32)
    return fb
