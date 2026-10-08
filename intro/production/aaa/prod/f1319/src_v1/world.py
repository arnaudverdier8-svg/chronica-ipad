"""World assembly + relight for the S18 keyframe: strip on a walnut table, physical light pool, render to 2560x1440."""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f1319/src')
from s18common import *
from geometry import *
import shade_s18
from chron import frontal, grade
from chron.fibres import halo
from chron.color import light_colour
from chron.ageing import apply_age
from walnut import make_walnut_world

MARGIN = 16.0     # mm around the window
TABLE_GAIN = 3.3
TABLE_EDGE = dict(y0=655.0, R=7.0) if os.environ.get('F_TABLE_EDGE', '1') == '1' else None
BOUNCE_K = 0.6
BOUNCE_SIGMA_MM = 38.0


def world_grid(PX):
    x0, y0 = -WIN_W / 2 - MARGIN, -WIN_H / 2 - MARGIN
    Wpx, Hpx = int(round((WIN_W + 2 * MARGIN) * PX)), int(round((WIN_H + 2 * MARGIN) * PX))
    return x0, y0, Wpx, Hpx


def remap_strip(S, PX, x0, y0, Wpx, Hpx, g=GEO, keys=('h', 'alb', 'T', 'mat', 'cov', 'cloth'), bands=6):
    """strip maps (strip-local, density PX) -> world maps on the world grid, in row bands (bounded memory)."""
    out = {}
    for k in keys:
        a = S[k]
        shp = (Hpx, Wpx) + a.shape[2:]
        out[k] = np.zeros(shp, a.dtype if k == 'mat' else np.float32)
    xs = (x0 + (np.arange(Wpx) + 0.5) / PX).astype(np.float32)
    edges = np.linspace(0, Hpx, bands + 1).astype(int)
    for b in range(bands):
        r0, r1 = edges[b], edges[b + 1]
        ys = (y0 + (np.arange(r0, r1) + 0.5) / PX).astype(np.float32)
        X, Y = np.meshgrid(xs, ys)
        u, v, ang = world_to_strip(X, Y, g)
        mx, my = (u * PX - 0.5).astype(np.float32), (v * PX - 0.5).astype(np.float32)
        del X, Y, u, v
        for k in keys:
            a = S[k]
            interp = cv2.INTER_NEAREST if k == 'mat' else cv2.INTER_LINEAR
            if a.ndim == 3:
                for i in range(a.shape[2]):
                    out[k][r0:r1, :, i] = cv2.remap(np.ascontiguousarray(a[..., i]), mx, my, interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            else:
                out[k][r0:r1] = cv2.remap(np.ascontiguousarray(a), mx, my, interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        c = np.cos(ang); sn = np.sin(ang)
        tx, ty = out['T'][r0:r1, :, 0].copy(), out['T'][r0:r1, :, 1].copy()
        out['T'][r0:r1, :, 0] = tx * c - ty * sn
        out['T'][r0:r1, :, 1] = tx * sn + ty * c
    return out


POOL = dict(cx=-50.0, cy=30.0, a=2.175, rx=WIN_W / 2, ry=WIN_H / 2)


def pool_xy(x, y, p=POOL):
    d2 = ((x - p['cx']) / p['rx']) ** 2 + ((y - p['cy']) / p['ry']) ** 2
    return (1 + p['a'] * d2) ** -1.5


def pool(PX, x0, y0, Wpx, Hpx, cx=-50.0, cy=30.0, a=2.175, rx=WIN_W / 2, ry=WIN_H / 2):
    """physical light pool: irradiance of a point source above the table behind an anamorphic aperture,
    E = (1 + a d^2)^-1.5 with d = 1 at the frame-edge mid-points  ->  a = 2.175 gives exactly -2.5 EV there.
    (cos x inverse-square falloff of a lamp at height z over the table; scales key, rim and fill alike)."""
    xs = (x0 + (np.arange(Wpx) + 0.5) / PX).astype(np.float32)
    ys = (y0 + (np.arange(Hpx) + 0.5) / PX).astype(np.float32)
    d2 = ((xs[None, :] - cx) / rx) ** 2 + ((ys[:, None] - cy) / ry) ** 2
    return ((1 + a * d2) ** -1.5).astype(np.float32)


def compose(PX, S, seed=7, table_angle=-2.0, cloth_lift=1.3):
    import gc
    x0, y0, Wpx, Hpx = world_grid(PX)
    t0 = time.time()
    tab = make_walnut_world(Hpx, Wpx, PX, x0, y0, table_angle, seed)
    print(f'walnut {time.time()-t0:.1f}s', flush=True)
    wm = remap_strip(S, PX, x0, y0, Wpx, Hpx)
    a = np.clip(wm['cloth'], 0, 1)
    out = dict(PX=PX, origin_mm=(x0, y0), valid=np.ones((Hpx, Wpx), bool))
    tab['alb'] *= TABLE_GAIN
    if TABLE_EDGE is not None:       # the long front edge of the table: rounded bevel catching the last light, then the dark floor
        y_edge, R = TABLE_EDGE['y0'], TABLE_EDGE['R']
        xs_ = (x0 + (np.arange(Wpx) + 0.5) / PX).astype(np.float32)
        ys_ = (y0 + (np.arange(Hpx) + 0.5) / PX).astype(np.float32)
        e = ys_[:, None] - (y_edge + math.tan(math.radians(table_angle)) * xs_[None, :])
        bev = (e > -R) & (e <= 0)
        tab['h'] = np.where(bev, -R + np.sqrt(np.maximum(R * R - (e + R) ** 2, 0)), tab['h']).astype(np.float32)
        beyond = e > 0
        tab['h'][beyond] = -R - 60.0
        tab['alb'][beyond] = 0.0012
        tab['spec'][beyond] = 0.0
        tab['spec'][bev] *= 2.2
        # a few knocks / lighter wear on the arris
        tab['alb'][bev] *= (1.15 + 0.2 * np.sin(xs_[None, :].repeat(Hpx, 0)[bev] / 37.0))[:, None]
        del e, bev, beyond
    out['alb'] = tab['alb'] * (1 - a[..., None]) + wm['alb'] * a[..., None]
    out['h'] = np.where(a > 0.5, wm['h'] + cloth_lift, tab['h'] + (cloth_lift) * a).astype(np.float32)
    out['T'] = np.where((a > 0.5)[..., None], wm['T'], tab['T']).astype(np.float32)
    out['mat'] = np.where(a > 0.5, wm['mat'], 6).astype(np.uint8)
    out['cov'] = np.where(a > 0.5, wm['cov'], 0).astype(np.float32)
    out['spec'] = tab['spec']
    out['cloth'] = a.astype(np.float32)
    del tab, wm; gc.collect()
    return out


def render(m, light, PX, kmap, out_wh=(OUT_W, OUT_H), s=S_SCREEN, cam_z=1500.0, timing=None, soft=0.9):
    t0 = time.time()
    x0, y0, w, h, _ = frontal.view_rect(dict(cx_mm=0.0, cy_mm=0.0, px_per_mm=s), out_wh)
    frontal.prepare(m, s, True)
    t1 = time.time()
    col, vis = shade_s18.relight(m, light, cam=(0.0, 0.0, cam_z), kmap=kmap, h_shadow=m['h'], return_vis=True, spec=m['spec'], soft=soft)
    col = halo(col, m)
    # light bounced from the bright strip onto the walnut next to it (cheap one-bounce GI: blurred cloth radiance x table albedo)
    if 'cloth' in m and BOUNCE_K > 0:
        # computed at 1/4 resolution (it is a very smooth term)
        q = 4
        sm = lambda a_: cv2.resize(a_, (a_.shape[1] // q, a_.shape[0] // q), interpolation=cv2.INTER_AREA)
        up = lambda a_: cv2.resize(a_, (col.shape[1], col.shape[0]), interpolation=cv2.INTER_LINEAR)
        src = sm(col * m['cloth'][..., None])
        B = up(cv2.GaussianBlur(src, (0, 0), BOUNCE_SIGMA_MM * PX / q)); B2 = up(cv2.GaussianBlur(src, (0, 0), BOUNCE_SIGMA_MM * 0.35 * PX / q))
        dst = 1 - np.maximum(m['cloth'], m.get('solid', 0))[..., None]
        col += dst * (m['alb'] * (1 / 0.03)) * (0.7 * B + 0.5 * B2) * (BOUNCE_K * 0.25)
        del B, B2, src, dst
    t2 = time.time()
    ox, oy = m['origin_mm']
    r = PX / s
    if r > 1.2:
        col = cv2.GaussianBlur(col, (0, 0), 0.5 * math.sqrt(r * r - 1))
    M = np.array([[s / PX, 0, (ox - x0) * s + 0.5 * (s / PX - 1)], [0, s / PX, (oy - y0) * s + 0.5 * (s / PX - 1)]], np.float32)
    img = cv2.warpAffine(col, M, out_wh, flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    img = np.maximum(img, 0)
    print(f'prepare {t1-t0:.1f}s relight {t2-t1:.1f}s warp {time.time()-t2:.1f}s', flush=True)
    return img, vis


def to_screen(arr, m, PX, out_wh=(OUT_W, OUT_H), s=S_SCREEN, interp=cv2.INTER_LINEAR):
    x0, y0, _, _, _ = frontal.view_rect(dict(cx_mm=0.0, cy_mm=0.0, px_per_mm=s), out_wh)
    ox, oy = m['origin_mm']
    M = np.array([[s / PX, 0, (ox - x0) * s + 0.5 * (s / PX - 1)], [0, s / PX, (oy - y0) * s + 0.5 * (s / PX - 1)]], np.float32)
    return cv2.warpAffine(np.ascontiguousarray(arr, np.float32), M, out_wh, flags=interp, borderMode=cv2.BORDER_REPLICATE)


def rig_last_light(key_i=1.45, fill_ratio=6.0, rim_i=0.30):
    # embers dead: a last warm glow low from the bottom (az 250), a thin cool fill, a faint rim from the upper right
    return shade_s18.rig(az=250, el=17, K=2500, key_i=key_i, tint=0.32, fill_ratio=fill_ratio, fill_K=8500, rim_az=35, rim_el=9, rim_i=rim_i, k_env=0.75)
