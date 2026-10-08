"""KEYFRAME f1983 (S26): the hand-off frame.

From a native capture of the live main menu's first frames (no-save state, see capture_menu.mjs):
  1. fit the card's minimum size to the capture (position is layout-exact, size depends on fonts),
  2. rebuild the blank card exactly as Godot draws its StyleBoxTexture nine-patch
     (assets/tex/table_parchment/menu_card.png, margins 46/47/48/56, stretch, bilinear),
  3. replace ONLY the parchment interior of the card (title, subtitle, rule, 5 buttons, footer)
     by the rebuilt blank parchment, with a 3-texel inset and a soft 2-texel feather inside the
     parchment where rebuild and capture agree to < 1/255; every other pixel is the capture, bit
     for bit,
  4. write the chrome mattes (one aligned full-frame straight-alpha RGBA per element, plus the
     combined desk and a board-visibility matte), the verification diff and a JSON report.

usage: python3 handoff.py CAPTURE.png OUTDIR TAG
"""
import sys, os, json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from godot2d import load_rgba, save_rgba, draw_ninepatch, bilinear
from menu_layout import layout, draw_rects, MARGINS
from chrome import build_layers, check_against_capture, ORDER, tex
from fit_card import fit

S = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa'


def parchment_mask_tex(card_tex, inset=3.0, feather=2.0):
    """Float mask in texture space: 1 on the parchment field of menu_card.png, 0 on the walnut
    frame, its dark inner line and the brass corners; inset and feathered (in texels)."""
    lum = card_tex[..., :3].mean(2) * 255
    th, tw = lum.shape
    inner = np.zeros_like(lum, bool)
    inner[20:320, 22:238] = True               # inside the inner dark line (measured on the texture)
    cand = inner & (lum > 140) & (card_tex[..., 3] > 0.99)
    lab, _ = ndimage.label(cand)
    field = lab == lab[th // 2, tw // 2]
    field = ndimage.binary_fill_holes(field)
    # brass corners: remove anything near them (they are not parchment even where bright)
    d = ndimage.distance_transform_edt(field)  # distance (texels) to the nearest non-field texel
    return np.clip((d - inset) / feather, 0.0, 1.0).astype(np.float32)


def run(cap_path, outdir, tag):
    os.makedirs(outdir, exist_ok=True)
    mdir = os.path.join(outdir, f'mattes_{tag}')
    os.makedirs(mdir, exist_ok=True)
    cap8 = np.asarray(Image.open(cap_path).convert('RGB'))
    H, W = cap8.shape[:2]
    cap = cap8.astype(np.float32) / 255.0

    # 1. card size from the capture
    best, err_sum, s = fit(cap_path, W, H)
    card_min = (float(best[2]), float(best[3]))
    L, rects, layers = build_layers(W, H, card_min=card_min)
    card_r = rects['menu_card']

    # 2. blank card (nine-patch) + texel coordinates of every pixel
    ctex = tex('menu_card')
    card_layer, (x0, y0, x1, y1, tx, ty) = draw_ninepatch(W, H, ctex, card_r, s, MARGINS['menu_card'])
    mtex = parchment_mask_tex(ctex)
    TX, TY = np.meshgrid(tx / ctex.shape[1], ty / ctex.shape[0])
    m = bilinear(mtex[..., None], TX, TY)[..., 0]
    M = np.zeros((H, W), np.float32)
    M[y0:y1, x0:x1] = m

    # 3. composite: only pixels with M > 0 change
    rebuild = card_layer[..., :3] * card_layer[..., 3:4] + cap * (1 - card_layer[..., 3:4])
    out = cap * (1 - M[..., None]) + rebuild * M[..., None]
    out8 = np.clip(np.rint(out * 255), 0, 255).astype(np.uint8)
    out8[M <= 0] = cap8[M <= 0]
    Image.fromarray(out8).save(os.path.join(outdir, f'f1983_{tag}.png'))

    # residual where the replacement is partial or the parchment is content-free
    diff = np.abs(out8.astype(np.int16) - cap8.astype(np.int16)).max(2)
    card_box = np.zeros((H, W), bool)
    card_box[y0:y1, x0:x1] = True
    content = ndimage.binary_dilation(np.abs(rebuild - cap).max(2) * 255 > 6, iterations=6)
    ring = (M > 0) & ~content                         # replaced but content-free parchment
    feather = (M > 0) & (M < 1)
    stats = {
        'capture': os.path.abspath(cap_path), 'size': [W, H], 'canvas_scale': s,
        'card_min_size_base_fitted': [round(v, 3) for v in card_min],
        'card_draw_rect_base': [round(v, 3) for v in card_r],
        'card_draw_rect_px': [round(v * s, 2) for v in card_r],
        'card_frame_fit_err_sum_255': round(err_sum, 3),
        'outside_card_rect': {'max_abs_diff': int(diff[~card_box].max()), 'changed_px': int((diff[~card_box] > 0).sum())},
        'outside_replaced_region': {'max_abs_diff': int(diff[M <= 0].max())},
        'replaced_px': int((M > 0).sum()),
        'content_free_parchment_ring': {'px': int(ring.sum()), 'mean_abs_255': round(float(diff[ring].mean()), 3),
                                        'p99_abs_255': round(float(np.percentile(diff[ring], 99)), 2)},
        'feather_band': {'px': int(feather.sum()), 'mean_abs_255': round(float(diff[feather & ~content].mean()), 3)},
    }

    # 4a. verification diff image (x8 amplified, card rect outlined)
    vis = np.clip(diff.astype(np.float32) * 8, 0, 255).astype(np.uint8)
    vimg = Image.fromarray(np.stack([vis] * 3, 2))
    dr = ImageDraw.Draw(vimg)
    cx, cy, cw, chh = [v * s for v in card_r]
    dr.rectangle([cx, cy, cx + cw, cy + chh], outline=(255, 64, 32), width=3)
    from PIL import ImageFont
    fnt = ImageFont.truetype(S + '/game/fonts/AlegreyaSans-Medium.ttf', int(30 * s / 1.6))
    dr.text((24, H - int(60 * s / 1.6)), f'|f1983 - live menu| x8.  Outside the card: max {stats["outside_card_rect"]["max_abs_diff"]}/255, '
            f'{stats["outside_card_rect"]["changed_px"]} px changed.  Content-free parchment: mean '
            f'{stats["content_free_parchment_ring"]["mean_abs_255"]}/255.', font=fnt, fill=(255, 200, 80))
    vimg.save(os.path.join(outdir, f'verify_diff_{tag}.png'))

    # 4b. mattes: one aligned straight-alpha RGBA per element (texture colours, Godot placement)
    layers['menu_card'] = card_layer  # blank card
    chk = check_against_capture(cap, layers)
    stats['matte_check_vs_capture'] = {k: (None if v is None else {'opaque_px': v[0], 'mean_abs_255': round(v[1], 3), 'p99_abs_255': round(v[2], 2)}) for k, v in chk.items()}
    desk = np.zeros((H, W, 4), np.float32)
    for n in ORDER:
        if n not in layers:
            continue
        save_rgba(os.path.join(mdir, f'{n}.png'), layers[n])
        if n != 'menu_card':
            a = layers[n][..., 3:4]
            rgb = layers[n][..., :3] * a + desk[..., :3] * desk[..., 3:4] * (1 - a)
            al = a + desk[..., 3:4] * (1 - a)
            desk = np.concatenate([np.where(al > 0, rgb / np.maximum(al, 1e-6), 0), al], 2)
    save_rgba(os.path.join(mdir, 'desk_all_but_card.png'), desk)
    a = card_layer[..., 3:4]
    rgb = card_layer[..., :3] * a + desk[..., :3] * desk[..., 3:4] * (1 - a)
    al = a + desk[..., 3:4] * (1 - a)
    chrome_all = np.concatenate([np.where(al > 0, rgb / np.maximum(al, 1e-6), 0), al], 2)
    save_rgba(os.path.join(mdir, 'chrome_all.png'), chrome_all)
    Image.fromarray(np.clip(np.rint((1 - al[..., 0]) * 255), 0, 255).astype(np.uint8), 'L').save(os.path.join(mdir, 'board_visible_alpha.png'))
    Image.fromarray(np.clip(np.rint(M * 255), 0, 255).astype(np.uint8), 'L').save(os.path.join(mdir, 'card_parchment_replaced_alpha.png'))
    # how well does chrome_all over the capture reproduce the capture (alpha-weighted)?
    re = chrome_all[..., :3] * chrome_all[..., 3:4] + cap * (1 - chrome_all[..., 3:4])
    sel = (chrome_all[..., 3] > 0.999) & (M <= 0) & ~card_box
    stats['chrome_all_opaque_vs_capture_mean_abs_255'] = round(float((np.abs(re - cap)[sel] * 255).mean()), 3)
    from flames import run as flames_run   # candle_*_flame / candle_*_unlit layers
    flames_run(mdir, W, H, card_min)
    # the parchment field (light area inside the card's inner dark line) in screen px: the rect
    # the S24 leaf must land on. Texel -> local units through the nine-patch margins (1:1 there).
    fy, fx = np.nonzero(mtex > 0)  # inset field; the raw field is 3 texels larger on each side
    th_, tw_ = ctex.shape[:2]
    ml, mt, mr, mb = MARGINS['menu_card']
    def tex2loc(t, size, tsize, m0, m1):
        if t <= m0: return t
        if t >= tsize - m1: return size - (tsize - t)
        return m0 + (t - m0) * (size - m0 - m1) / (tsize - m0 - m1)
    raw = [fx.min() - 3.0, fy.min() - 3.0, fx.max() + 1 + 3.0, fy.max() + 1 + 3.0]
    lx0 = tex2loc(raw[0], card_r[2], tw_, ml, mr); lx1 = tex2loc(raw[2], card_r[2], tw_, ml, mr)
    ly0 = tex2loc(raw[1], card_r[3], th_, mt, mb); ly1 = tex2loc(raw[3], card_r[3], th_, mt, mb)
    pf = [(card_r[0] + lx0) * s, (card_r[1] + ly0) * s, (lx1 - lx0) * s, (ly1 - ly0) * s]
    stats['parchment_field_px'] = [round(v, 2) for v in pf]
    stats['parchment_field_texels'] = [int(v) for v in raw]
    stats['rects_base'] = {k: [round(v, 4) for v in r] for k, r in rects.items()}
    stats['rects_px'] = {k: [round(v * s, 3) for v in r] for k, r in rects.items()}
    stats['draw_order'] = [n for n in ORDER if n in layers]
    with open(os.path.join(outdir, f'report_{tag}.json'), 'w') as f:
        json.dump(stats, f, indent=1)
    with open(os.path.join(mdir, 'rects.json'), 'w') as f:
        json.dump({'size': [W, H], 'canvas_scale': s, 'draw_order': stats['draw_order'],
                   'card_min_size_base': stats['card_min_size_base_fitted'], 'parchment_field_px': stats['parchment_field_px'],
                   'rects_base': stats['rects_base'], 'rects_px': stats['rects_px'],
                   'note': 'straight (non-premultiplied) RGBA, sRGB-encoded, full frame, aligned to the live menu; '
                           'composite in draw_order with plain over (Godot Compatibility 2D blends in sRGB space)'}, f, indent=1)
    return stats


if __name__ == '__main__':
    st = run(sys.argv[1], sys.argv[2], sys.argv[3])
    print(json.dumps({k: v for k, v in st.items() if k not in ('rects_base', 'rects_px')}, indent=1))
