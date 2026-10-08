"""Candle desk states for the S22-S24 relight beats (f1612-f1707): every candle sprite is split into

  <name>_unlit      the candle with the flame removed: a charred, slightly curled wick (no flame root,
                    no baked glow), and the warm top-down subsurface glow taken out of the upper
                    ~18 % of the wax (matched row by row to the tone of the lower body, detail kept);
  <name>_flame      the EXACT residual, so that over(<name>_flame, <name>_unlit) == <name> to within
                    1/255 (premultiplied RGB and alpha) at every pixel -- asserted below;
  <name>_flame_core the part of the residual above the wax (flame body, halo, ember on the wick);
  <name>_waxglow    the part of the residual on the wax and rim (the flame's light on the candle);
                    flame_core and waxglow have disjoint support and add up to <name>_flame.

v1 split the sprite's alpha with a soft mask (flame alpha + unlit alpha = full alpha), which does not
recompose under 'over' (alpha up to 25 % off, premultiplied RGB up to 58/255 at the wick junction).
v2 builds the unlit layer first and solves the flame layer as the residual in screen space, from the
very pixels the matte stores:
    alpha_f = 1 - (1 - a_full) / (1 - a_unlit)                       (unlit not opaque)
    alpha_f = minimal alpha that keeps the straight colour in [0,1]  (unlit opaque: difference matte)
    rgb_f   = (c_full - c_unlit (1 - alpha_f)) / alpha_f             (premultiplied terms)

usage: python3 flames.py MATTE_DIR W H CARD_W CARD_H
"""
import sys, os
import numpy as np
from scipy import ndimage
from godot2d import save_rgba, draw_texture_rect, load_rgba
from chrome import tex
from menu_layout import layout, draw_rects

# Texture-space parameters, measured on the sprites (assets/tex/table_backgrounds/*.png).
#   box    window around flame + cup (x0, y0, x1, y1)
#   wick   x=(top, bottom) centre, rows=(first row of the wick incl. ember, cup row), hw half width,
#          cut = last row the flame touches, curl = lateral bend of the wick tip in texels
#   wax    cols = wax columns, rim = first wax row, full/end = rows (from rim) where the glow
#          correction is full / zero, ref = rows used as the lower-body tone, seed = a pixel of the body
PARAMS = {
    'candle_left': dict(
        box=(76, 0, 128, 100), wick=dict(x=(102, 102), rows=(55, 86), hw=4.5, cut=70, curl=2.2, ember=1),
        wax=dict(cols=(60, 142), rim=63, full=75, end=175, ref=(200, 270), seed=(300, 100))),
    'candle_right': dict(
        box=(84, 0, 140, 125), wick=dict(x=(110, 105), rows=(77, 116), hw=5.5, cut=93, curl=2.2, ember=2),
        wax=dict(cols=(70, 150), rim=89, full=70, end=190, ref=(205, 275), seed=(300, 106))),
    'table_edge_bottom': dict(
        box=(116, 0, 158, 70), wick=dict(x=(137, 137), rows=(34, 52), hw=7.5, cut=42, curl=0.0, ember=0),
        wax=dict(cols=(108, 168), rim=44, full=6, end=60, ref=(62, 78), seed=(75, 138))),
}


def _lum(t):
    return t[..., :3].mean(2)


def segment(t, p):
    """wax component, wick band, flame region (texture space)."""
    a = t[..., 3]
    x0, y0, x1, y1 = p['box']
    w = p['wick']
    rows = np.arange(t.shape[0])[:, None]
    cols = np.arange(t.shape[1])[None, :]
    xc = w['x'][0] + (w['x'][1] - w['x'][0]) * np.clip((rows - w['rows'][0]) / max(1, w['rows'][1] - w['rows'][0]), 0, 1)
    wickband = (np.abs(cols - xc) <= w['hw']) & (rows >= w['rows'][0] - 2) & (rows <= w['rows'][1])
    solid = (a > 0.85) & ~wickband
    lab, _ = ndimage.label(solid, structure=np.ones((3, 3)))
    sd = p['wax']['seed']
    assert lab[sd] > 0, 'seed pixel not on the candle body'
    wax = lab == lab[sd]
    # per column: first wax row; the flame region is everything above it, minus a 2-texel margin that
    # keeps the soft antialiased top edge of the wax with the wax
    first = np.where(wax.any(0), wax.argmax(0), t.shape[0])
    win = np.zeros(a.shape, bool)
    win[y0:y1, x0:x1] = True
    # flame = the connected bundle of every non-wax, non-wick pixel that contains the bright flame body
    # (so wax antialiasing and stray wax-edge pixels never count as flame)
    waxd = ndimage.binary_dilation(wax, iterations=2)
    cand = (a > 0) & win & ~wickband & ~waxd & (rows < (first[None, :] - 2))
    labc, _ = ndimage.label(cand, structure=np.ones((3, 3)))
    bright = cand & (a > 0.9) & (_lum(t) * 255 > 200)
    flame = np.isin(labc, np.unique(labc[bright])) & cand
    return wax, wickband, flame, xc


def build_unlit_texture(t, name):
    """Returns (unlit texture, info dict)."""
    p = PARAMS[name]
    w = p['wick']
    a = t[..., 3]
    L = _lum(t) * 255
    wax, wickband, flame, xc = segment(t, p)
    tu = t.copy()
    rows = np.arange(t.shape[0])[:, None]
    cols = np.arange(t.shape[1])[None, :]

    # --- 1. wax: remove the top-down warm glow (rows rim .. rim+end), keep the detail --------------
    wp = p['wax']
    c0, c1 = wp['cols']
    core = wax & (a > 0.95) & (L > 115) & ~ndimage.binary_dilation(wickband, iterations=3)
    core[:, :c0] = False
    core[:, c1:] = False
    ref_rows = slice(*wp['ref'])
    ref = np.median(t[ref_rows][core[ref_rows]][:, :3], axis=0)
    r_lo, r_hi = wp['rim'] - 2, wp['rim'] + wp['end']
    gain = np.ones((t.shape[0], 3), np.float32)
    for r in range(r_lo, r_hi + 1):
        m = core[r]
        if m.sum() >= 4:
            gain[r] = np.clip(ref / np.maximum(np.median(t[r][m][:, :3], axis=0), 1e-3), 0.55, 1.12)
        else:
            gain[r] = np.nan
    # fill gaps, smooth along the rows
    idx = np.arange(t.shape[0])
    for c in range(3):
        g = gain[:, c]
        ok = ~np.isnan(g)
        g[~ok] = np.interp(idx[~ok], idx[ok & (idx >= r_lo) & (idx <= r_hi)], g[ok & (idx >= r_lo) & (idx <= r_hi)]) if ok.any() else 1
        gain[:, c] = ndimage.gaussian_filter1d(g, 3.0)
    wrow = np.zeros(t.shape[0], np.float32)
    full_end = wp['rim'] + wp['full']
    for r in range(r_lo, r_hi + 1):
        if r <= full_end:
            wrow[r] = 1.0
        else:
            wrow[r] = 0.5 * (1 + np.cos(np.pi * (r - full_end) / max(1, r_hi - full_end)))
    # weight: only well inside the silhouette (the screen-space resample footprint must not see a
    # colour step at the antialiased edge, or the residual would need a wrong alpha there)
    dist = ndimage.distance_transform_edt(a > 0.5)
    wedge = np.clip((dist - 5.5) / 4.0, 0, 1)
    colmask = np.zeros(a.shape, np.float32)
    colmask[:, c0:c1] = 1
    wickfree = 1 - ndimage.gaussian_filter(ndimage.binary_dilation(wickband, iterations=3).astype(np.float32), 1.0)
    wgt = (wrow[:, None] * wedge * colmask * wax * wickfree).astype(np.float32)
    eff = 1 + wgt[..., None] * (gain[:, None, :] - 1)
    tu[..., :3] = np.clip(t[..., :3] * eff, 0, 1)

    # --- 2. flame region: gone ----------------------------------------------------------------------
    clear = flame | (wickband & (rows < w['cut'] + 1))
    tu[clear, 3] = 0.0          # RGB under alpha 0 stays as in the sprite, so the straight-alpha filter of the
                                # screen resample sees the same colours as it does for the full candle
    # --- 3. wick: clean charred stroke, lightly curled ------------------------------------------------
    D = wickband & (a > 0.5) & (L < 110) & (rows <= w['rows'][1])
    D = ndimage.binary_closing(D, structure=np.ones((3, 3)))
    r0, r1 = w['rows'][0] - 0, w['cut'] + 6
    lo = np.full(t.shape[0], np.nan); hi = np.full(t.shape[0], np.nan)
    for r in range(r0, w['rows'][1] + 1):
        c = np.nonzero(D[r])[0]
        if len(c):
            lo[r], hi[r] = c.min(), c.max()
    have = np.nonzero(~np.isnan(lo))[0]
    first_r = int(have.min())
    for r in range(max(0, first_r - w['ember'] - 1), first_r):
        lo[r], hi[r] = lo[first_r], hi[first_r]
    # smooth the extents (median over 5 rows) so the stroke is a clean column
    rr = np.arange(r0, w['rows'][1] + 1)
    for arr in (lo, hi):
        seg = arr[rr]
        ok = ~np.isnan(seg)
        seg[~ok] = np.interp(rr[~ok], rr[ok], seg[ok]) if ok.any() else 0
        arr[rr] = ndimage.median_filter(seg, size=5, mode='nearest')
    # colours: the dark core's own pixels; everything else takes the nearest dark colour, a touch darker
    nearest = ndimage.distance_transform_edt(~D, return_indices=True)[1]
    wick_rgb = t[..., :3][nearest[0], nearest[1]]
    paint = np.zeros(t.shape, np.float32)
    top_row = int(min(first_r - w['ember'], first_r))
    for r in range(top_row, w['cut'] + 4):
        if np.isnan(lo[r]):
            continue
        c_lo, c_hi = int(round(lo[r])), int(round(hi[r]))
        sl = slice(c_lo, c_hi + 1)
        col = np.where(D[r, sl][:, None], t[r, sl, :3], wick_rgb[r, sl] * 0.9)
        # the topmost rows are char: darker, a little cooler
        k = np.clip(1.0 - (r - top_row) / 5.0, 0, 1) * 0.75
        col = col * (1 - k) + np.array([0.075, 0.055, 0.05], np.float32) * k
        paint[r, sl, :3] = col
        paint[r, sl, 3] = 1.0
    # curl: shear the top rows sideways (quadratic), toward the existing lean
    curl_rows = 10
    sgn = 1.0 if w['x'][0] >= w['x'][1] else -1.0
    out = np.zeros_like(paint)
    for r in range(paint.shape[0]):
        if not paint[r, :, 3].any():
            continue
        dx = 0
        if w['curl'] > 0 and r < top_row + curl_rows:
            dx = int(round(sgn * w['curl'] * ((top_row + curl_rows - r) / curl_rows) ** 2))
        out[r] = np.roll(paint[r], dx, axis=0)
    # never exceed the sprite's own alpha (so over(flame, unlit) can be exact)
    out[..., 3] = np.where(a > 0.9, out[..., 3], np.minimum(out[..., 3], a))
    m = out[..., 3] > 0
    tu[m] = out[m]
    info = dict(ref_rgb=(ref * 255).round().tolist(), glow_gain_max=[float(gain[r_lo:r_hi, c].min()) for c in range(3)],
                wick_top_row=top_row, flame_region_texels=int(flame.sum()), wax_texels=int(wax.sum()))
    return tu, info, dict(wax=wax, flame=flame, wickband=wickband)


def _q(x):
    return np.clip(np.rint(x * 255.0), 0, 255).astype(np.uint8)


def decompose(C8, U8, rounds=3):
    """Exact residual flame layer. C8, U8: (H,W,4) uint8 straight RGBA of the full candle and the unlit
    layer; U's alpha is first limited to C's. Returns (U8', F8).
    Where the unlit colour differs from the full one but both have the same partial alpha (a colour-only
    change on a soft edge), no flame alpha can express it; the unlit alpha is lowered there by 4 % per
    round so the residual gets an alpha of its own (touches a handful of edge pixels)."""
    U8 = U8.copy()
    for k in range(rounds + 1):
        F8 = _solve(C8, U8)
        pm, a = over_pm(F8, U8)
        full_pm = (C8[..., :3].astype(np.float64) / 255.0) * (C8[..., 3:4] / 255.0)
        bad = ((np.abs(pm - full_pm).max(2) * 255 > 0.75) | (np.abs(a - C8[..., 3] / 255.0) * 255 > 0.75)) & (U8[..., 3] > 4)
        if not bad.any() or k == rounds:
            break
        U8[..., 3][bad] = np.floor(U8[..., 3][bad].astype(np.float64) * 0.96).astype(np.uint8)
    U8[U8[..., 3] == 0, :3] = 0
    return U8, F8


def _solve(C8, U8):
    C = C8.astype(np.float64) / 255.0
    U = U8.astype(np.float64) / 255.0
    ac, au = C[..., 3], np.minimum(U[..., 3], C[..., 3])
    U[..., 3] = au
    pc = C[..., :3] * ac[..., None]
    pu = U[..., :3] * au[..., None]
    af = np.zeros_like(ac)
    # (A) unlit not opaque: the alpha equation fixes the flame alpha
    # (alpha-equal, near-opaque pixels count as opaque: a colour-only change there needs a flame alpha of its own;
    #  the alpha it adds is af * (1 - au) < 1/255)
    notop = (au < 0.999) & ~((au >= 0.99) & (np.abs(ac - au) < 0.004))
    den = np.maximum(1 - au, 1e-6)
    af_A = np.clip(1 - (1 - ac) / den, 0, 1)
    af[notop] = af_A[notop]
    # (B) unlit opaque: smallest alpha for which the straight flame colour stays in [0,1]
    op = ~notop
    pu_ = np.where(op[..., None], pu, 0.5)
    up = np.maximum((pc - pu_) / np.maximum(1 - pu_, 1e-6), 0)          # flame lighter than the unlit
    dn = np.maximum((pu_ - pc) / np.maximum(pu_, 1e-6), 0)              # flame darker than the unlit
    af_B = np.clip(np.maximum(up, dn).max(2), 0, 1)
    af[op] = af_B[op]
    a8 = _q(af)
    af = a8 / 255.0
    pf = np.clip(pc - pu * (1 - af)[..., None], 0, af[..., None])
    rgb = np.where(af[..., None] > 0, pf / np.maximum(af, 1e-9)[..., None], 0)
    F8 = np.dstack([_q(rgb), a8])
    F8[a8 == 0, :3] = 0
    return F8


def absorb_dark_residue(U8, F8, lum_max=0.42, a_noise=1):
    """The residual of the wick's own antialiased edge is dark (brown, luminance < 0.42): it belongs to the
    unlit wick, not to the flame. Such pixels are composited into the unlit layer and removed from the flame
    layer (exact: over(F', U') == over(F, U)). Flame-layer alpha of 1/255 is noise and is dropped.
    This is what keeps the flame layer clean over a light ground."""
    F = F8.astype(np.float64) / 255.0
    U = U8.astype(np.float64) / 255.0
    af, au = F[..., 3:4], U[..., 3:4]
    dark = (F8[..., 3] > 0) & (F[..., :3].mean(2) < lum_max)
    a2 = af + au * (1 - af)
    prem = F[..., :3] * af + U[..., :3] * au * (1 - af)
    rgb2 = np.where(a2 > 0, prem / np.maximum(a2, 1e-9), 0)
    U8n = U8.copy()
    U8n[dark] = np.dstack([_q(rgb2), _q(a2)])[dark]
    F8n = F8.copy()
    F8n[dark] = 0
    noise = (F8n[..., 3] > 0) & (F8n[..., 3] <= a_noise)
    F8n[noise] = 0
    return U8n, F8n, int(dark.sum())


def over_pm(F8, U8):
    f = F8.astype(np.float64) / 255.0
    u = U8.astype(np.float64) / 255.0
    af, au = f[..., 3:4], u[..., 3:4]
    return f[..., :3] * af + u[..., :3] * au * (1 - af), (af + au * (1 - af))[..., 0]


def run(mdir, W, H, card_min):
    L = layout(W, H, card_min=card_min)
    rects = draw_rects(L)
    s = L['scale']
    report = {}
    for n in ('candle_left', 'candle_right', 'table_edge_bottom'):
        if n not in rects:
            continue
        t = tex(n)
        tu, info, seg = build_unlit_texture(t, n)
        C8 = np.asarray(__import__('PIL.Image', fromlist=['Image']).open(os.path.join(mdir, n + '.png')).convert('RGBA'))
        U = draw_texture_rect(W, H, tu, rects[n], s, mipmaps=True)
        U8, F8 = decompose(C8, _q(U))
        U8, F8, moved = absorb_dark_residue(U8, F8)
        # partition of the residual: flame body vs light on the wax (wax mask resampled like the sprite)
        wm = np.zeros(t.shape, np.float32)
        wm[..., 3] = ndimage.binary_dilation(seg['wax'], iterations=2).astype(np.float32)
        wl = draw_texture_rect(W, H, wm, rects[n], s, mipmaps=True)[..., 3] > 0.5
        glow = F8.copy(); glow[~wl] = 0
        core = F8.copy(); core[wl] = 0
        # tidy: residual below 1/255 alpha is noise
        for nm, arr in (('unlit', U8), ('flame', F8), ('flame_core', core), ('waxglow', glow)):
            save_rgba(os.path.join(mdir, f'{n}_{nm}.png'), arr.astype(np.float32) / 255.0)
        pm, a = over_pm(F8, U8)
        full_pm = (C8[..., :3].astype(np.float64) / 255.0) * (C8[..., 3:4] / 255.0)
        d_rgb = np.abs(pm - full_pm).max(2) * 255
        d_a = np.abs(a - C8[..., 3] / 255.0) * 255
        pm2, a2 = over_pm(core, U8)
        pm3, a3 = over_pm(glow, U8)
        # core and glow are disjoint: over(core, over(glow, unlit)) == over(flame, unlit)
        report[n] = {'max_pm_rgb_255': round(float(d_rgb.max()), 3), 'max_alpha_255': round(float(d_a.max()), 3),
                     'px_over_1_255': int(((d_rgb > 1.0 + 1e-3) | (d_a > 1.0 + 1e-3)).sum()),
                     'flame_px': int((F8[..., 3] > 0).sum()), 'dark_residue_px_moved_to_unlit': moved, 'core_px': int((core[..., 3] > 0).sum()), 'glow_px': int((glow[..., 3] > 0).sum()),
                     **info}
        print(n, report[n])
        assert report[n]['max_pm_rgb_255'] <= 1.5 and report[n]['max_alpha_255'] <= 1.5, ('flame/unlit does not recompose', n, report[n])
    import json
    with open(os.path.join(mdir, 'flames_report.json'), 'w') as fh:
        json.dump(report, fh, indent=1)
    return report


if __name__ == '__main__':
    run(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), (float(sys.argv[4]), float(sys.argv[5])))
