"""f899 COMP: R25 ground plate (per light) x Eevee shadow ratios + Eevee slips (per light, pooled like the plate) + tethers,
contact darkening, depth of field (analytic ground depth + slip Z), lens vignette, one shared grade.

    python3 comp.py EEVEE_DIR OUT.png [--tag v1] [--exposure 1.0]
"""
import os, sys, json, math, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bkit
import numpy as np, cv2
import camera as CAM, exr
from chron import grade
from chron.color import hex_lin
from slip_fibres import silhouette_halo

ROOT = os.path.dirname(HERE)
shot = json.load(open(os.path.join(ROOT, 'shot_f899.json')))
cam = CAM.build(shot['camera'])
W, H = CAM.W, CAM.H


def rd(path):
    a = exr.read(path)
    if a.shape[0] != H or a.shape[1] != W:
        a = cv2.resize(a, (W, H), interpolation=cv2.INTER_LINEAR)
    return a


def pool(x, y, k):
    d = np.hypot((x - k['cx_mm']) / k.get('aspect', 1.0), y - k['cy_mm']) / k['r_mm']
    return (k.get('floor', 0.5) + (1 - k.get('floor', 0.5)) * np.exp(-d * d)).astype(np.float32)


def pixel_grid(w, h):
    uu, vv = np.meshgrid(np.arange(w, dtype=np.float64) + 0.5, np.arange(h, dtype=np.float64) + 0.5)
    return uu, vv


def ground_maps(step=8):
    """sheet mm (x, y) and depth z of the cloth plane at every pixel (computed on a coarse grid, bilinear)."""
    us = np.arange(0, W + step, step, dtype=np.float64); vs = np.arange(0, H + step, step, dtype=np.float64)
    U, V = np.meshgrid(us, vs)
    xy, z = CAM.ground_from_pixel(cam, np.stack([U.ravel(), V.ravel()], 1))
    X = xy[:, 0].reshape(U.shape).astype(np.float32); Y = xy[:, 1].reshape(U.shape).astype(np.float32); Z = z.reshape(U.shape).astype(np.float32)
    out = []
    for A in (X, Y, Z):
        out.append(cv2.resize(A, None, fx=step, fy=step, interpolation=cv2.INTER_LINEAR)[:H, :W])
    return out


def world_from_depth(zmap):
    """world position of every pixel from the Z pass (distance along the optical axis)."""
    uu, vv = pixel_grid(W, H)
    dc = np.stack([(uu - cam['cx']) / cam['f_px'], -(vv - cam['cy']) / cam['f_px'], -np.ones_like(uu)], -1)
    Pc = dc * zmap[..., None]
    Pw = Pc @ cam['Rcw'].T + cam['C']
    return Pw.astype(np.float32)


def dof(img, zmap, zf, f_mm, fstop, px_per_mm_sensor, sig_scale=0.5, levels=(0.0, 0.8, 1.6, 2.6)):
    A = f_mm / fstop
    coc_mm = A * f_mm * np.abs(zmap - zf) / (zmap * (zf - f_mm))
    coc_px = coc_mm * px_per_mm_sensor                      # blur-circle diameter in px
    sig = np.clip(coc_px * sig_scale, 0, levels[-1])
    out = np.zeros_like(img)
    stack = [img] + [cv2.GaussianBlur(img, (0, 0), s) for s in levels[1:]]
    lv = np.array(levels, np.float32)
    idx = np.clip(np.searchsorted(lv, sig, side='right') - 1, 0, len(lv) - 2)
    t = np.clip((sig - lv[idx]) / (lv[idx + 1] - lv[idx]), 0, 1)[..., None]
    for i in range(len(lv) - 1):
        sel = (idx == i)[..., None]
        out += np.where(sel, stack[i] * (1 - t) + stack[i + 1] * t, 0)
    return out


def run(ev_dir, out_png, tag='', exposure=None, params=None):
    t0 = time.time()
    P = dict(slip_gain=dict(h=1.08, c=1.0, f=1.0), contact=0.55, ratio_blur=1.6, vignette=0.22, dof=True, halo=0.25, fibres=True, sharpen=0.8, fill_pool=0.35, haze=0.18, haze_col='#2B2D3C', bloom=0.22)
    P.update(params or {})
    plate = {k: np.load(os.path.join(ROOT, 'work', 'plate', f'plate_{k}_screen.npy')).astype(np.float32) for k in 'hcf'}
    ratio = {}
    a_sl = rd(os.path.join(ev_dir, 'slips_hearth_img_0001.exr'))[..., 3]
    # ratio is only meaningful where the plane itself is visible: mask the slips (dilated), fill by normalised convolution, then smooth
    valid = (cv2.dilate((a_sl > 0.003).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))) == 0).astype(np.float32)
    for k, name in (('h', 'hearth'), ('c', 'cool'), ('f', 'fill')):
        p = rd(os.path.join(ev_dir, f'plane_{name}_img_0001.exr'))[..., :3]
        q = rd(os.path.join(ev_dir, f'planeclean_{name}_img_0001.exr'))[..., :3]
        r = p.mean(-1) / np.maximum(q.mean(-1), 1e-5)
        r = np.clip(np.where(q.mean(-1) < 1e-5, 1.0, r), 0, 1.15)
        sig = max(P['ratio_blur'], 0.5)
        num = cv2.GaussianBlur(r * valid, (0, 0), sig); den = cv2.GaussianBlur(valid, (0, 0), sig)
        r_s = num / np.maximum(den, 1e-4)
        far = cv2.GaussianBlur(r * valid, (0, 0), 12) / np.maximum(cv2.GaussianBlur(valid, (0, 0), 12), 1e-4)
        r_s = np.where(den > 0.05, r_s, far)
        ratio[k] = np.where(valid > 0, r_s, np.where(den > 0.02, r_s, far))[..., None]
    sl = {k: rd(os.path.join(ev_dir, f'slips_{name}_img_0001.exr')) for k, name in (('h', 'hearth'), ('c', 'cool'), ('f', 'fill'))}
    zs = rd(os.path.join(ev_dir, 'slips_hearth_z_0001.exr'))[..., 0]
    zs = np.where(zs > 1e4, 1e5, zs).astype(np.float32)
    alpha = sl['h'][..., 3]
    X, Y, Zg = ground_maps()
    # ---- ground (plates carry no pool: the key pools are applied here, in screen space, identically for plate and slips)
    ph = pool(X, Y, shot['hearth']['kmap'])[..., None]; pc = pool(X, Y, shot['cool']['kmap'])[..., None]
    # the Act III grade carries a warm gain (#FFE2C4): the pale daylight arc is pre-compensated so that it still lands pale / cool
    gg = np.asarray(grade.act_params(shot['grade']['act'])['gain'], np.float32); gg = gg / gg.max()
    cool_pre = ((1.0 / gg) ** P.get('cool_comp', 0.85)).astype(np.float32)[None, None]
    fp = (P['fill_pool'] + (1 - P['fill_pool']) * ph)
    ground = plate['h'] * ph * ratio['h'] + plate['c'] * pc * ratio['c'] * cool_pre + plate['f'] * fp * ratio['f']
    if P.get('haze', 0) > 0:      # dusk aerial perspective: the far cloth (up-frame) sinks toward a cool grey
        t_ = np.clip((Zg - 830.0) / 140.0, 0, 1)[..., None] ** 1.3
        hz = hex_lin(P['haze_col']).astype(np.float32)
        ground = ground * (1 - P['haze'] * t_) + hz[None, None] * (0.4 + 0.6 * ph) * P['haze'] * t_
    # ---- beyond the cloth's top edge (sheet y < 0) is the walnut table: a dark, lit-from-below wedge with a soft edge shadow
    tab = np.clip((0.0 - Y) / 0.5, 0, 1)[..., None]
    if tab.max() > 0:
        from chron.util import vnoise
        # walnut: dark brown, long horizontal grain streaks (frieze-mm noise stretched along x), softly lit by the hearth pool
        gx = (X / 260.0).astype(np.float32); gy = (Y / 2.2).astype(np.float32)
        grain = 0.5 + 0.5 * np.sin(gy * 6.0 + 2.2 * np.sin(gx * 5.0 + gy * 0.7) + 1.5 * np.sin(gy * 17.0 + gx * 3.0))
        walnut = hex_lin('#2B180C').astype(np.float32)[None, None] * (0.70 + 0.55 * grain[..., None])
        lit = (0.30 + 0.70 * ph) * 1.4
        # the cloth edge throws a soft shadow onto the table (light from the bottom, so away from the viewer)
        edge_sh = 1.0 - 0.55 * np.exp(-np.clip(-Y, 0, None) / 7.0)
        ground = ground * (1 - tab) + walnut * lit * edge_sh[..., None] * tab
    ground = ground * (1 - (0.30 * np.exp(-np.clip(Y, 0, None) / 1.6) * (Y > -0.3))[..., None])   # contact shadow just inside the hem
    # ---- slips: pool factors at the pixel's world position
    Pw = world_from_depth(np.minimum(zs, 5000.0))
    xs_, ys_ = Pw[..., 0], -Pw[..., 1]
    kh = pool(xs_, ys_, shot['hearth']['kmap'])[..., None]; kc = pool(xs_, ys_, shot['cool']['kmap'])[..., None]
    G = P['slip_gain']
    # the Eevee passes were rendered with the sun colours / strengths in render_meta.json: re-balance to the current shot lights
    gm = {}
    mp = os.path.join(ev_dir, 'render_meta.json')
    if os.path.exists(mp):
        from chron.color import light_colour
        rm = json.load(open(mp))
        for k, nm, K, tint in (('h', 'hearth', shot['hearth']['K'], shot['hearth']['tint']), ('c', 'cool', shot['cool']['K'], shot['cool']['tint'])):
            c0 = np.array(rm[nm]['col'], np.float32) * rm[nm]['strength']
            cc = np.asarray(light_colour(K, tint), np.float32) if not shot[nm].get('rgb') else np.asarray(shot[nm]['rgb'], np.float32)
            cc = cc / cc.max() * shot[nm]['key_i']
            gm[k] = (cc / np.maximum(c0, 1e-6)).astype(np.float32)
        fc0 = np.array(rm['fill']['col'], np.float32) * rm['fill']['strength']
        fcc = np.asarray(light_colour(shot['fill']['K'], 0.1), np.float32); fcc = fcc / fcc.max() * shot['fill']['i']
        gm['f'] = (fcc / np.maximum(fc0, 1e-6)).astype(np.float32)
    else:
        gm = {k: np.ones(3, np.float32) for k in 'hcf'}
    srgb_ = sl['h'][..., :3] * kh * G['h'] * gm['h'] + sl['c'][..., :3] * kc * G['c'] * gm['c'] * cool_pre + sl['f'][..., :3] * G['f'] * gm['f']
    if P.get('sharpen', 0) > 0:
        bl = cv2.GaussianBlur(srgb_, (0, 0), 0.9)
        srgb_ = np.maximum(srgb_ + P['sharpen'] * (srgb_ - bl), 0) * (alpha[..., None] > 0.02)
    out = ground * (1 - alpha[..., None]) + srgb_
    if P.get('halo', 0) > 0:
        cb, ha = silhouette_halo(srgb_, alpha, 4.65, 0.3, P['halo'])
        out = out * (1 - ha[..., None]) + cb * ha[..., None]
    nfib = 0
    if P.get('fibres', True):
        import slip_fibres as SF
        ex = json.load(open(os.path.join(ROOT, 'blend', 'slips', 'slips_export.json')))
        nfib = SF.add_fibres(out, zs, cam, ex, shot, lambda x, y, k: float(pool(np.array([x]), np.array([y]), k)[0]), density=P.get('fib_density', 0.9),
                             width=P.get('fib_width', 0.9))
        print('fibres', nfib, flush=True)
    zmap = np.where(alpha > 0.5, zs, Zg)
    # contact darkening handled by the AO ratio ('fill') + sun contact shadows; extra soft occlusion band near the hinge is in the ratio
    if P['dof']:
        out = dof(out, zmap, cam['cfg']['focus_mm'], cam['focal_mm'], cam['cfg']['fstop'], W / CAM.SENSOR_W)
    if P.get('bloom', 0) > 0:
        br = np.maximum(out - 0.55, 0)
        out = out + P['bloom'] * (cv2.GaussianBlur(br, (0, 0), 22) * 0.6 + cv2.GaussianBlur(br, (0, 0), 7) * 0.4)
    if P['vignette'] > 0:
        uu, vv = pixel_grid(W, H)
        r2 = ((uu - W / 2) / (W / 2)) ** 2 + ((vv - H / 2) / (H / 2)) ** 2
        out = out * (1 - P['vignette'] * np.clip(r2 / 2.0, 0, 1))[..., None]
    np.save(os.path.join(ROOT, 'work', f'comp_lin{tag}.npy'), out.astype(np.float16))
    Gd = shot['grade']
    ap = dict(grade.act_params(Gd['act']))
    ap['gamma'] = ap['gamma'] * Gd.get('gamma_mul', 1.0); ap['sat'] = ap['sat'] * Gd.get('sat_mul', 1.0)
    img = grade.grade(out, exposure=exposure if exposure is not None else Gd['exposure'], act=ap, seed=899, grain=Gd['grain'])
    cv2.imwrite(out_png, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    # diagnostics
    cv2.imwrite(out_png.replace('.png', '_ground.jpg'), cv2.cvtColor(grade.grade(ground, exposure=exposure if exposure is not None else Gd['exposure'], act=ap, seed=1, grain=0), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print('comp done', round(time.time() - t0, 1), 's ->', out_png, flush=True)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('ev'); ap.add_argument('out'); ap.add_argument('--tag', default=''); ap.add_argument('--exposure', type=float, default=None)
    ap.add_argument('--params', default=None)
    a = ap.parse_args()
    run(a.ev, a.out, a.tag, a.exposure, json.loads(a.params) if a.params else None)
