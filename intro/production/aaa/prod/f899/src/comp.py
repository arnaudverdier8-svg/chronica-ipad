"""f899 COMP (v2): R25 ground plate (per light) x Eevee shadow ratios (distance-dependent penumbra, warm bounce) + Eevee slips (per light, pooled like the
plate, with the hearth's height falloff up the body) + R25 fibres on the slips, the pale daylight arc (cool pool with a defined leading edge, bleach on
the slips), depth of field (analytic ground depth + slip Z), halation, lens vignette, one shared grade with a split tone (warm highlights, woad shadows).

    python3 comp.py EEVEE_DIR OUT.png [--tag v1] [--exposure 1.0] [--params JSON]
"""
import os, sys, json, math, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bkit
import numpy as np, cv2
import camera as CAM, exr
import arc as ARC
from chron import grade
from chron.color import hex_lin
from slip_fibres import silhouette_halo

ROOT = os.path.dirname(HERE)
shot = json.load(open(os.path.join(ROOT, 'shot_f899.json')))
cam = CAM.build(shot['camera'])
W, H = CAM.W, CAM.H
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


def rd(path):
    a = exr.read(path)
    if a.shape[0] != H or a.shape[1] != W:
        a = cv2.resize(a, (W, H), interpolation=cv2.INTER_LINEAR)
    return a


def pool(x, y, k, z=None, kz=0.0, lobes=None):
    """key-light pool (physical vignette).  z: height above the cloth (mm): a point that is higher is effectively farther from the low hearth, so the
    pool falls off up the body of a standing slip (y shifted by kz * z).  lobes: [[cx, cy, r, amp]] irregular flicker lobes (static, +/- a fraction).
    k['mode'] == 'exp' (v3): the hearth sits just below the frame's bottom edge; the key falls off exponentially up the cloth (length lam mm, from y_h) to a
    floor near black at the top edge, with a gentle lateral fall-off."""
    yy = y if z is None else y - kz * z
    if k.get('mode') == 'exp':
        f = np.exp(-np.clip(k['y_h'] - yy, 0.0, None) / k['lam'])
        lat = k['lat_floor'] + (1 - k['lat_floor']) * np.exp(-((x - k['cx_mm']) / k['rx_mm']) ** 2)
        p = (k['floor'] + (1 - k['floor']) * f) * lat
        if k.get('edge'):      # the cloth's top edge sinks toward black (the hearth is far below, the table beyond is unlit)
            E = k['edge']; p = p * (E['floor'] + (1 - E['floor']) * smoothstep(E['y0'], E['y1'], y))
    else:
        d = np.hypot((x - k['cx_mm']) / k.get('aspect', 1.0), yy - k['cy_mm']) / k['r_mm']
        p = k.get('floor', 0.5) + (1 - k.get('floor', 0.5)) * np.exp(-d * d)
    if lobes:
        m = np.ones_like(p, dtype=np.float32)
        for cx, cy, r, a in lobes:
            m = m + a * np.exp(-((x - cx) ** 2 + (yy - cy) ** 2) / (r * r))
        p = p * m
    return p.astype(np.float32)


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


def dof(img, zmap, zf, f_mm, fstop, px_per_mm_sensor, sig_scale=0.5, levels=(0.0, 0.7, 1.4, 2.4)):
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


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def run(ev_dir, out_png, tag='', exposure=None, params=None):
    t0 = time.time()
    P = dict(slip_gain=dict(h=1.55, c=1.0, f=1.0), contact=0.55, ratio_blur=1.4, ratio_blur_far=7.0, pen_dist_px=260.0, vignette=0.25, dof=True, halo=0.0, fibres=True,
             sharpen=0.8, fill_pool=0.10, haze=0.08, haze_col='#2B2D3C', bloom=0.20, halation=0.10, bounce=shot.get('bounce', 0.22), shadow_fade=0.30, shadow_warm=1.0,
             split_cool=0.40, gleam=1.1, hearth_gain=shot.get('hearth_gain', 1.0), split_warm=0.04, slip_bleach=0.45, fib_edge=1.0,
             fill_gain=shot.get('fill_gain', 1.0), hearth_haze=shot.get('hearth_haze', 0.0), sharpen_all=shot.get('sharpen_all', 0.0), hi_desat=shot.get('hi_desat', 0.0))
    P.update(params or {})
    HR = shot['hearth']; kz = HR.get('kz', 0.0); lobes = HR.get('lobes')
    A = shot['arc']
    plate = {k: np.load(os.path.join(ROOT, 'work', 'plate', f'plate_{k}_screen.npy')).astype(np.float32) for k in 'hcf'}
    ratio = {}
    a_sl = rd(os.path.join(ev_dir, 'slips_hearth_img_0001.exr'))[..., 3]
    # ratio is only meaningful where the plane itself is visible: mask the slips (dilated), fill by normalised convolution, then smooth
    valid = (cv2.dilate((a_sl > 0.003).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))) == 0).astype(np.float32)
    dist_px = cv2.distanceTransform((cv2.dilate((a_sl > 0.003).astype(np.uint8), np.ones((3, 3), np.uint8)) == 0).astype(np.uint8), cv2.DIST_L2, 5)
    wpen = np.clip(dist_px / P['pen_dist_px'], 0, 1)                    # penumbra grows with the distance from the caster
    for k, name in (('h', 'hearth'), ('c', 'cool'), ('f', 'fill')):
        p = rd(os.path.join(ev_dir, f'plane_{name}_img_0001.exr'))[..., :3]
        q = rd(os.path.join(ev_dir, f'planeclean_{name}_img_0001.exr'))[..., :3]
        r = p.mean(-1) / np.maximum(q.mean(-1), 1e-5)
        r = np.clip(np.where(q.mean(-1) < 1e-5, 1.0, r), 0, 1.15)

        def nconv(sig):
            num = cv2.GaussianBlur(r * valid, (0, 0), sig); den = cv2.GaussianBlur(valid, (0, 0), sig)
            return num / np.maximum(den, 1e-4), den
        r_near, den = nconv(max(P['ratio_blur'], 0.5))
        r_far_s, _ = nconv(P['ratio_blur_far'])
        r_s = r_near * (1 - wpen) + r_far_s * wpen
        r_s = 1.0 - (1.0 - r_s) * (1.0 - P['shadow_fade'] * np.clip(dist_px / 330.0, 0, 1))      # the far end of a shadow thins out (partial occlusion of the extended hearth)
        far = cv2.GaussianBlur(r * valid, (0, 0), 12) / np.maximum(cv2.GaussianBlur(valid, (0, 0), 12), 1e-4)
        r_s = np.where(den > 0.05, r_s, far)
        ratio[k] = np.where(valid > 0, r_s, np.where(den > 0.02, r_s, far))[..., None]
    sl = {k: rd(os.path.join(ev_dir, f'slips_{name}_img_0001.exr')) for k, name in (('h', 'hearth'), ('c', 'cool'), ('f', 'fill'))}
    zs = rd(os.path.join(ev_dir, 'slips_hearth_z_0001.exr'))[..., 0]
    zs = np.where(zs > 1e4, 1e5, zs).astype(np.float32)
    alpha = sl['h'][..., 3]
    X, Y, Zg = ground_maps()
    # ---- ground (plates carry no pool: the key pools are applied here, in screen space, identically for plate and slips)
    ph = pool(X, Y, HR['kmap'], lobes=lobes)[..., None] * P['hearth_gain']
    lw_g, bw_g = ARC.weights(X, Y, A)
    env = (0.62 + 0.38 * np.exp(-((Y - 200.0) / 170.0) ** 2)).astype(np.float32)
    E_ = HR['kmap'].get('edge') or dict(y0=0.0, y1=1.0, floor=1.0)
    ed_g = (E_['floor'] + (1 - E_['floor']) * smoothstep(E_['y0'], E_['y1'], Y)).astype(np.float32)
    pc = (lw_g * env * ed_g * shot.get('cool_gain', 1.0))[..., None]
    gg = np.asarray(grade.act_params(shot['grade']['act'])['gain'], np.float32); gg = gg / gg.max()
    cool_pre = ((1.0 / gg) ** P.get('cool_comp', 0.85)).astype(np.float32)[None, None]
    fp = (P['fill_pool'] + (1 - P['fill_pool']) * ph / max(P['hearth_gain'], 1e-6)) * P['fill_gain']
    bounce = P['bounce']
    rh_b = ratio['h'] + bounce * (1 - ratio['h'])                            # warm radiosity: the shadow keeps a fraction of the hearth, in the hearth's colour
    ground = plate['h'] * ph * rh_b + plate['c'] * pc * ratio['c'] * cool_pre + plate['f'] * fp * ratio['f']
    if P.get('haze', 0) > 0:      # dusk aerial perspective: the far cloth (up-frame) sinks toward a cool grey
        t_ = np.clip((Zg - 830.0) / 140.0, 0, 1)[..., None] ** 1.3
        hz = hex_lin(P['haze_col']).astype(np.float32)
        ground = ground * (1 - P['haze'] * t_) + hz[None, None] * (0.4 + 0.6 * ph) * P['haze'] * t_
    # ---- beyond the cloth's top edge (sheet y < 0) is the walnut table: dark, grained, lit from below, with the cloth's edge shadow and a soft sheen
    tab = np.clip((0.0 - Y) / 0.5, 0, 1)[..., None]
    if tab.max() > 0:
        gx = (X / 260.0).astype(np.float32); gy = (Y / 2.2).astype(np.float32)
        grain = 0.5 + 0.5 * np.sin(gy * 6.0 + 2.2 * np.sin(gx * 5.0 + gy * 0.7) + 1.5 * np.sin(gy * 17.0 + gx * 3.0))
        grain2 = 0.5 + 0.5 * np.sin(gy * 31.0 + 4.0 * np.sin(gx * 9.0) + gx * 2.0)
        walnut = hex_lin('#2E1A0E').astype(np.float32)[None, None] * (0.62 + 0.55 * grain[..., None] + 0.18 * grain2[..., None])
        lit = (0.34 + 0.66 * ph) * 2.0
        edge_sh = 1.0 - 0.60 * np.exp(-np.clip(-Y, 0, None) / 6.5)
        sheen = (0.22 * np.exp(-((Y + 26.0) / 13.0) ** 2) * (0.5 + 0.5 * grain))[..., None] * hex_lin('#C98A4C').astype(np.float32)[None, None] * ph
        ground = ground * (1 - tab) + (walnut * lit * edge_sh[..., None] + sheen) * tab
    ground = ground * (1 - (0.30 * np.exp(-np.clip(Y, 0, None) / 1.6) * (Y > -0.3))[..., None])   # contact shadow just inside the hem
    mpath = os.path.join(ROOT, 'work', 'plate', 'plate_metal_screen.npy')
    if os.path.exists(mpath) and P.get('gleam', 0) > 0:     # the chronicle thread: fresh gold gleams under the hearth, the tarnished left end stays dull bronze
        mt = np.clip(np.load(mpath).astype(np.float32), 0, 1)[..., None]
        TF = shot['tarnish_front']
        tt = np.clip((X - TF['x0']) / (TF['x1'] - TF['x0']), 0, 1); tt = tt * tt * (3 - 2 * tt)
        fresh = (1.0 - (TF['hi'] + (TF['lo'] - TF['hi']) * tt))[..., None]
        gold = hex_lin('#E9BE6A').astype(np.float32)[None, None]
        ground = ground + P['gleam'] * mt * fresh * gold * (0.55 + 0.45 * np.sqrt(ph))
    ground = ground * (1 + (0.35 * np.exp(-(Y / 0.45) ** 2) * (Y > -0.2))[..., None] * ph)            # the hem's rolled edge catches the hearth
    # ---- slips: pool factors at the pixel's world position (height-dependent: the light falls off up the body)
    Pw = world_from_depth(np.minimum(zs, 5000.0))
    xs_, ys_, zz_ = Pw[..., 0], -Pw[..., 1], Pw[..., 2]
    kh = pool(xs_, ys_, HR['kmap'], z=zz_, kz=kz, lobes=lobes)[..., None] * P['hearth_gain']
    lw_s, bw_s = ARC.weights(xs_, ys_, A)
    kc = (lw_s * (0.62 + 0.38 * np.exp(-((ys_ - 200.0) / 170.0) ** 2)) * (E_['floor'] + (1 - E_['floor']) * smoothstep(E_['y0'], E_['y1'], ys_)) * shot.get('cool_gain', 1.0))[..., None]
    G = P['slip_gain']
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
    fillk = (P['fill_pool'] + (1 - P['fill_pool']) * kh / max(P['hearth_gain'], 1e-6)) * P['fill_gain']
    srgb_ = sl['h'][..., :3] * kh * G['h'] * gm['h'] + sl['c'][..., :3] * kc * G['c'] * gm['c'] * cool_pre + sl['f'][..., :3] * G['f'] * gm['f'] * fillk
    # the century's bleach on the slips (screen-space twin of the plate's albedo bleach)
    if P['slip_bleach'] > 0:
        l_ = (srgb_ * LUMA).sum(-1, keepdims=True)
        kb = (bw_s * P['slip_bleach'])[..., None]
        srgb_ = l_ + (srgb_ - l_) * (1 - 0.62 * kb)
        srgb_ = srgb_ + 0.34 * kb * (np.maximum(l_, 1e-4) ** 0.8) * (1.0 - np.clip(l_ / 0.6, 0, 1)) * 0.9
    if P.get('sharpen', 0) > 0:
        bl = cv2.GaussianBlur(srgb_, (0, 0), 0.9)
        srgb_ = np.maximum(srgb_ + P['sharpen'] * (srgb_ - bl), 0) * (alpha[..., None] > 0.02)
    out = ground * (1 - alpha[..., None]) + srgb_
    if P.get('halo', 0) > 0:
        cb, ha = silhouette_halo(srgb_, alpha, 4.5, 0.3, P['halo'])
        out = out * (1 - ha[..., None]) + cb * ha[..., None]
    nfib = 0
    if P.get('fibres', True):
        import slip_fibres as SF
        ex = json.load(open(os.path.join(ROOT, 'blend', 'slips', 'slips_export.json')))
        nfib = SF.add_fibres(out, zs, cam, ex, shot, lambda x, y, k: float(pool(np.array([x]), np.array([y]), k, lobes=lobes)[0]) * P['hearth_gain'], density=P.get('fib_density', 0.9),
                             width=P.get('fib_width', 0.9), edge_boost=P['fib_edge'] * 4.0)
        print('fibres', nfib, flush=True)
    zmap = np.where(alpha > 0.5, zs, Zg)
    if P['dof']:
        out = dof(out, zmap, cam['cfg']['focus_mm'], cam['focal_mm'], cam['cfg']['fstop'], W / CAM.SENSOR_W)
    if P.get('bloom', 0) > 0:
        br = np.maximum(out - 0.55, 0)
        out = out + P['bloom'] * (cv2.GaussianBlur(br, (0, 0), 22) * 0.6 + cv2.GaussianBlur(br, (0, 0), 7) * 0.4)
    if P.get('hearth_haze', 0) > 0:      # the hearth itself is just below the frame: a faint warm veil of scattered light lifts the bottom edge
        from chron.color import light_colour
        uu, vv = pixel_grid(W, H)
        g = np.exp(-(H - vv) / (0.17 * H)) * (0.55 + 0.45 * np.exp(-((uu - 0.55 * W) / (0.55 * W)) ** 2))
        hc = np.asarray(light_colour(HR['K'], HR['tint']), np.float32); hc = hc / hc.max()
        out = out + (P['hearth_haze'] * g[..., None] * hc[None, None]).astype(np.float32)
    if P.get('halation', 0) > 0:      # a trace of red-orange halation around the hottest warm highlights
        hot = np.maximum((out * LUMA).sum(-1, keepdims=True) - 0.85, 0) * np.array([1.0, 0.38, 0.14], np.float32)
        out = out + P['halation'] * (cv2.GaussianBlur(hot, (0, 0), 9) * 0.65 + cv2.GaussianBlur(hot, (0, 0), 3.2) * 0.35)
    if P.get('sharpen_all', 0) > 0:      # final micro-contrast on the whole frame (weave, strands, cords), applied on the linear image before the vignette / grade
        bl_ = cv2.GaussianBlur(out, (0, 0), 1.15)
        out = np.maximum(out + P['sharpen_all'] * (out - bl_), 0).astype(np.float32)
    if P['vignette'] > 0:
        uu, vv = pixel_grid(W, H)
        r2 = ((uu - W / 2) / (W / 2)) ** 2 + ((vv - H / 2) / (H / 2)) ** 2
        out = out * (1 - P['vignette'] * np.clip(r2 / 2.0, 0, 1))[..., None]
    np.save(os.path.join(ROOT, 'work', f'comp_lin{tag}.npy'), out.astype(np.float16))
    Gd = shot['grade']
    ap = dict(grade.act_params(Gd['act']))
    ap['gamma'] = ap['gamma'] * Gd.get('gamma_mul', 1.0); ap['sat'] = ap['sat'] * Gd.get('sat_mul', 1.0)
    img_f = split_grade(out, ap, Gd, exposure if exposure is not None else Gd['exposure'], P)
    cv2.imwrite(out_png, cv2.cvtColor(img_f[0], cv2.COLOR_RGB2BGR))
    cv2.imwrite(out_png.replace('.png', '_16bit.png'), cv2.cvtColor(img_f[1], cv2.COLOR_RGB2BGR))
    cv2.imwrite(out_png.replace('.png', '_ground.jpg'), cv2.cvtColor(grade.grade(ground, exposure=exposure if exposure is not None else Gd['exposure'], act=ap, seed=1, grain=0), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print('comp done', round(time.time() - t0, 1), 's ->', out_png, flush=True)
    return out


def split_grade(lin, ap, Gd, exposure, P):
    """the shared Act III grade, then a split tone applied in the graded sRGB: woad-cool shadows (the dusk's blue survives under the 2200 K hearth), a
    slightly warmer highlight.  Returns (uint8, uint16)."""
    from chron.color import srgb2lin, lin2srgb
    s16 = grade.grade(lin, exposure=exposure, act=ap, seed=899, grain=Gd['grain'], out_u16=True)
    x = s16.astype(np.float32) / 65535.0
    y = (x * LUMA).sum(-1, keepdims=True)
    ws = (1 - smoothstep(0.10, 0.62, y)) ** 1.3                 # deep shadows
    wh = smoothstep(0.55, 0.9, y)
    cool = np.array([0.80, 0.97, 1.22], np.float32)
    x = x * (1 - P['split_cool'] * ws) + (y * cool) * P['split_cool'] * ws
    x = x * (1 + P['split_warm'] * wh * np.array([0.9, 0.2, -0.8], np.float32))
    if P.get('hi_desat', 0) > 0:        # the brightest firelit linen drifts toward cream-gold instead of orange paper: desaturate the upper mids / highlights a little
        wd = smoothstep(0.30, 0.72, y)
        x = x * (1 - P['hi_desat'] * wd) + y * (P['hi_desat'] * wd)
    r = np.random.default_rng(7)
    d = (r.random(x.shape[:2], dtype=np.float32) + r.random(x.shape[:2], dtype=np.float32) - 1.0)[..., None] / 255.0   # TPDF dither before the 8-bit quantise
    u8 = np.clip((x + d) * 255 + 0.5, 0, 255).astype(np.uint8)
    u16 = np.clip(x * 65535 + 0.5, 0, 65535).astype(np.uint16)
    return u8, u16


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('ev'); ap.add_argument('out'); ap.add_argument('--tag', default=''); ap.add_argument('--exposure', type=float, default=None)
    ap.add_argument('--params', default=None)
    a = ap.parse_args()
    run(a.ev, a.out, a.tag, a.exposure, json.loads(a.params) if a.params else None)
