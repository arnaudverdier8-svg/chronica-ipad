"""Polish layer on top of handoff.py (critique items of the f1983 review). Per bucket it adds to mattes_<bucket>/:

  menu_card_frame.png           the card with the parchment field cut out (alpha 0 inside the field, up to the
                                inner dark line; walnut, dark line and brass corners opaque). The S24 leaf lands
                                UNDER this layer: 'the frame now holds the page'.
  menu_card_parchment_field.png the field alone (the pixels the frame cuts out). over(frame, field) == menu_card.
  card_contents.png             the live card contents (title, ornaments, subtitle, rule, 5 buttons, footer) as a
                                straight-alpha layer: over(card_contents, blank card) == the live capture.
  units_water_g12_mask.png      255 where the live board is not static (units idling, water, dust, nameplate pop-in),
                                measured across the stored captures: exclude these from G12.
and writes into rects.json: content geometry (reading-order bands, title baseline, rule centre line, button rects),
the parchment frequency target for S24/S25, colour metadata. It also writes handoff_spec.json (overlay timing,
encode guard, storyboard corrections) and tags every PNG as sRGB.

usage: python3 polish.py HANDOFF_DIR
"""
import sys, os, json, glob
import numpy as np
from PIL import Image
from scipy import ndimage
from godot2d import load_rgba, save_rgba, draw_ninepatch, bilinear
from menu_layout import MARGINS
from chrome import tex
from handoff import parchment_field_tex
import png_srgb

BUCKETS = {
    '16x9_2560x1440': dict(cap_dir='c169_a', base='menu_2560x1440_mf030_r0.png',
                           others=['c169_a/menu_2560x1440_mf003_r0.png', 'c169_a/menu_2560x1440_mf120_r0.png', 'c169_b/menu_2560x1440_mf030_r0.png']),
    '4x3_2048x1536': dict(cap_dir='c133_a', base='menu_2048x1536_mf030_r0.png',
                          others=['c133_a/menu_2048x1536_mf060_r0.png']),
}


def rgb8(p):
    return np.asarray(Image.open(p).convert('RGB'))


def runs(mask1d, min_gap):
    """contiguous index runs of a boolean vector, merging gaps shorter than min_gap."""
    idx = np.nonzero(mask1d)[0]
    if not len(idx):
        return []
    out, s, p = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - p > min_gap:
            out.append((int(s), int(p))); s = i
        p = i
    out.append((int(s), int(p)))
    return out


def card_frame_and_field(hd, tag, R, mdir):
    """menu_card_frame.png / menu_card_parchment_field.png: a hard, complementary split of the blank card."""
    W, H = R['size']
    s = R['canvas_scale']
    ctex = tex('menu_card')
    card = load_rgba(os.path.join(mdir, 'menu_card.png'))
    card_r = R['card_draw_rect_base']
    _, (x0, y0, x1, y1, tx, ty) = draw_ninepatch(W, H, ctex, card_r, s, MARGINS['menu_card'])
    ft = parchment_field_tex(ctex).astype(np.float32)
    TX, TY = np.meshgrid(tx / ctex.shape[1], ty / ctex.shape[0])
    Mf = np.zeros((H, W), np.float32)
    Mf[y0:y1, x0:x1] = bilinear(ft[..., None], TX, TY)[..., 0]
    Mb = Mf > 0.5
    frame, field = card.copy(), card.copy()
    frame[Mb, 3] = 0.0
    field[~Mb, 3] = 0.0
    save_rgba(os.path.join(mdir, 'menu_card_frame.png'), frame)
    save_rgba(os.path.join(mdir, 'menu_card_parchment_field.png'), field)
    ys, xs = np.nonzero(Mb)
    # exactness: the two layers are disjoint, so over(frame, field) == card
    return Mb, dict(field_px_bbox=[int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1], field_px=int(Mb.sum()))


def card_contents(hd, tag, R, mdir, Mb):
    """Difference matte of the live capture over the rebuilt blank card (minimal alpha keeping the straight
    colour in [0,1]); alpha 0 outside the replaced region."""
    cap = rgb8(R['capture']).astype(np.float64) / 255.0
    f = rgb8(os.path.join(hd, f'f1983_{tag}.png')).astype(np.float64) / 255.0   # blank where replaced, else the capture
    M = np.asarray(Image.open(os.path.join(mdir, 'card_parchment_replaced_alpha.png'))).astype(np.float64) / 255.0
    region = M > 0
    B = f                                           # backdrop = f1983 itself (the blank card in the field)
    up = np.maximum((cap - B) / np.maximum(1 - B, 1e-6), 0)
    dn = np.maximum((B - cap) / np.maximum(B, 1e-6), 0)
    a = np.clip(np.maximum(up, dn).max(2), 0, 1)
    a[~region] = 0
    a8 = np.rint(a * 255).astype(np.uint8)
    a8[a8 <= 2] = 0                                 # <= 2/255 is parchment noise, not content
    a = a8 / 255.0
    with np.errstate(invalid='ignore', divide='ignore'):
        rgb = np.where(a[..., None] > 0, (cap - B * (1 - a[..., None])) / a[..., None], 0)
    rgb8_ = np.clip(np.rint(rgb * 255), 0, 255).astype(np.uint8)
    rgb8_[a8 == 0] = 0
    layer = np.dstack([rgb8_, a8])
    Image.fromarray(layer, 'RGBA').save(os.path.join(mdir, 'card_contents.png'))
    # check: over(contents, f1983) vs capture inside the region
    rec = rgb8_.astype(np.float64) / 255.0 * a[..., None] + B * (1 - a[..., None])
    err = np.abs(rec - cap).max(2) * 255
    cmask = a8 > 0
    stats = dict(content_px=int(cmask.sum()), recompose_max_abs_255=round(float(err[region].max()), 2),
                 recompose_mean_abs_255=round(float(err[region].mean()), 4),
                 recompose_px_over_2_255=int((err[region] > 2.0 + 1e-6).sum()))
    return a8, stats


def content_geometry(R, a8, cap):
    """Reading-order bands from the live capture's content mask (card_contents alpha > 24)."""
    s = R['canvas_scale']
    px, py, pw, ph = R['parchment_field_px']
    mask = a8 > 24
    X0, X1 = int(px), int(px + pw)
    rows = mask[:, X0:X1].any(1)
    bands = runs(rows, 6)
    names = ['title', 'subtitle_1', 'subtitle_2', 'rule'] + [f'button_{i}' for i in range(1, 6)] + ['footer']
    assert len(bands) == len(names), ('unexpected band count', bands)
    geo = {}
    for n, (r0, r1) in zip(names, bands):
        cols = np.nonzero(mask[r0:r1 + 1, X0:X1].any(0))[0] + X0
        c0, c1 = int(cols.min()), int(cols.max())
        geo[n] = dict(x=[c0, c1 + 1], y=[r0, r1 + 1], rect_px=[c0, r0, c1 + 1 - c0, r1 + 1 - r0],
                      rect_base=[round(c0 / s, 3), round(r0 / s, 3), round((c1 + 1 - c0) / s, 3), round((r1 + 1 - r0) / s, 3)])
    # title: the word 'Chronica' = the widest run of very dark pixels (g < 55) in the title band; ornament groups are
    # what lies left and right of it; the glyph baseline = first row below the bodies of the tall letters
    t = geo['title']
    r0, r1 = t['y']
    xa, xb = t['x']
    g = cap.astype(np.float64).mean(2)
    txt = (g[r0:r1, xa:xb] < 55)
    cl = runs(txt.any(0), 14)
    wx0, wx1 = max(cl, key=lambda c: c[1] - c[0])
    lab, n = ndimage.label(txt[:, wx0:wx1 + 1])
    bots = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if ys.max() - ys.min() >= 0.25 * (r1 - r0):
            bots.append(int(ys.max()) + r0)
    base_y = int(np.median(bots)) + 1
    geo['title'].update(word_x_px=[xa + wx0, xa + wx1 + 1], ornament_left_x_px=[xa, xa + wx0], ornament_right_x_px=[xa + wx1 + 1, xb],
                        baseline_y_px=base_y, baseline_y_base=round(base_y / s, 3),
                        baseline_note='first pixel row below the bodies of the tall letters of the word (median of the letter components), serif feet included')
    # rule: centre line = row of the greatest horizontal run; boss = column of the greatest height
    r0, r1 = geo['rule']['y']
    sub = mask[r0:r1, X0:X1]
    rc = sub.sum(1)
    yc = np.average(np.arange(r0, r1), weights=np.where(rc > 0.5 * rc.max(), rc, 0))
    colh = sub.sum(0)
    geo['rule']['centre_y_px'] = round(float(yc) + 0.5, 2)
    geo['rule']['centre_y_base'] = round((float(yc) + 0.5) / s, 3)
    geo['rule']['boss_x_px'] = int(np.argmax(colh) + X0)
    return geo


def parchment_target(f1983, Mb):
    """Frequency/tone target of the blank field, for S24/S25 grading of the landing leaf."""
    inner = ndimage.binary_erosion(Mb, iterations=40)
    g = f1983.astype(np.float64)
    lum = g.mean(2)
    hp = lum - ndimage.gaussian_filter(lum, 2.0)
    lap = ndimage.laplace(ndimage.gaussian_filter(lum, 0.7))
    loc = lum - ndimage.gaussian_filter(lum, 8.0)
    spk = (loc < -5.0) & inner
    lab, n = ndimage.label(spk)
    sizes = ndimage.sum(spk, lab, range(1, n + 1)) if n else np.array([])
    area_mp = inner.sum() / 1e6
    return dict(mean_rgb=[round(float(g[..., c][inner].mean()), 2) for c in range(3)],
                mean_luminance_255=round(float(lum[inner].mean()), 2),
                highpass_std_sigma2_255=round(float(hp[inner].std()), 3),
                laplacian_variance=round(float(lap[inner].var()), 3),
                luminance_levels_spanned=int(np.ptp(np.round(ndimage.gaussian_filter(lum, 4.0)[inner]))) + 1,
                foxing_specks_per_megapixel=round(float((sizes >= 3).sum() / area_mp), 1),
                foxing_speck_rule='connected areas of >= 3 px darker than the 8 px local mean by > 5/255, field eroded by 40 px (scale dependent: the specks are stretched with the card)',
                note=('Measured on f1983 inside the field eroded by 40 px. The game card is a 260x340 texture stretched about 3.9x: '
                      'very soft and low-frequency by design. The S24 leaf must be low-passed and graded to these numbers before the dissolve, '
                      'or the hand-off reads as a pop from sharp textile to soft bitmap.'))


def g12_mask(hd, name, R, mdir, f1983):
    """Pixels that vary between stored live captures of the same menu (units idling, water, dust, nameplate pop-in)."""
    b = BUCKETS[name]
    base = rgb8(os.path.join(hd, 'capture', b['cap_dir'], b['base'])).astype(np.int16)
    varying = np.zeros(base.shape[:2], bool)
    used = []
    for o in b['others']:
        p = os.path.join(hd, 'capture', o)
        if not os.path.exists(p):
            continue
        d = np.abs(rgb8(p).astype(np.int16) - base).max(2)
        varying |= d > 6
        used.append(o)
    mask = ndimage.binary_dilation(varying, iterations=6)
    Image.fromarray((mask * 255).astype(np.uint8), 'L').save(os.path.join(mdir, 'units_water_g12_mask.png'))
    # outlook: f1983 vs every stored capture, outside the card rect, with and without the mask
    cx, cy, cw, ch = R['card_draw_rect_px']
    H, W = base.shape[:2]
    out = np.ones((H, W), bool)
    out[int(np.floor(cy)):int(np.ceil(cy + ch)), int(np.floor(cx)):int(np.ceil(cx + cw))] = False
    res = {}
    for o in used:
        d = np.abs(rgb8(os.path.join(hd, 'capture', o)).astype(np.float64) - f1983.astype(np.float64)).mean(2)
        res[o] = dict(mean_abs_255_no_mask=round(float(d[out].mean()), 3), mean_abs_255_with_mask=round(float(d[out & ~mask].mean()), 3),
                      px_over_16_pct_no_mask=round(float((d[out] > 16).mean() * 100), 2), px_over_16_pct_with_mask=round(float((d[out & ~mask] > 16).mean() * 100), 2))
    return dict(mask_fraction_of_frame=round(float(mask.mean()), 4), captures_used=['capture/' + o for o in used], g12_outlook_outside_card=res,
                rule='mask = dilate(max over stored captures of |capture - menu frame 30| > 6/255, 6 px); empirical, from the captures listed. '
                     'A frame in which no unit moved differently is not covered: re-derive it from a wider capture set if G12 starts flagging units.')


def process(hd, name):
    mdir = os.path.join(hd, f'mattes_{name}')
    R = json.load(open(os.path.join(hd, f'report_{name}.json')))
    f1983 = rgb8(os.path.join(hd, f'f1983_{name}.png'))
    cap = rgb8(R['capture'])
    Mb, fstats = card_frame_and_field(hd, name, R, mdir)
    a8, cstats = card_contents(hd, name, R, mdir, Mb)
    geo = content_geometry(R, a8, cap)
    pt = parchment_target(f1983, Mb)
    g12 = g12_mask(hd, name, R, mdir, f1983)
    rj = os.path.join(mdir, 'rects.json')
    J = json.load(open(rj))
    J['draw_order_note'] = 'menu_card = menu_card_frame over menu_card_parchment_field (disjoint). Contents: over(card_contents, menu_card) == the live capture.'
    J['card_layers'] = dict(menu_card_frame='alpha 0 inside the parchment field; the leaf lands under it', menu_card_parchment_field=fstats,
                            card_contents=cstats)
    J['content_geometry'] = dict(coordinate_note='px of the native capture; rect_base = px / canvas_scale; bands = bounding boxes of card_contents alpha > 24 in the card field',
                                 **geo)
    J['parchment_target'] = pt
    J['g12'] = g12
    J['colour'] = dict(encoding='sRGB (PNGs carry an sRGB chunk since v2; v1 files were untagged)', alpha='straight (non-premultiplied)',
                       blend='2D in sRGB space (Godot Compatibility); composite with plain over',
                       encode_hint='Flag the shipped encode BT.709 (primaries/transfer/matrix) with tv range, as the storyboard states; the game presents full-range sRGB, so verify the range mapping on device in G12.')
    json.dump(J, open(rj, 'w'), indent=1)
    return dict(frame_field=fstats, contents=cstats, geometry=geo, parchment=pt, g12=g12)


def main(hd):
    allres = {}
    for name in BUCKETS:
        if os.path.exists(os.path.join(hd, f'report_{name}.json')):
            allres[name] = process(hd, name)
            print(name, 'ok')
    json.dump(allres, open(os.path.join(hd, 'polish_report.json'), 'w'), indent=1)
    return allres


if __name__ == '__main__':
    main(sys.argv[1])
