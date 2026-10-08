"""QA evidence images for the v2 polish (written to qa/):
  card_layers_16x9.png / _4x3.png      frame | parchment field | card contents (on a checker) | contents over f1983 | live capture, and the G12 mask overlay
  candle_flames_v2_<bucket>.png        per candle: full | unlit | flame_core | waxglow | recomposed over dark and light grounds, x5
usage: python3 qa_images.py HANDOFF_DIR"""
import sys, os, json
import numpy as np
from PIL import Image
import flame_sheet


def checker(size, s=16):
    w, h = size
    a = np.indices((h, w)).sum(0) // s % 2
    return Image.fromarray(np.where(a[..., None] == 0, (70, 70, 80), (110, 110, 120)).astype(np.uint8), 'RGB').convert('RGBA')


def card_layers(hd, tag):
    M = os.path.join(hd, f'mattes_{tag}')
    R = json.load(open(os.path.join(hd, f'report_{tag}.json')))
    cx, cy, cw, ch = [int(v) for v in R['card_draw_rect_px']]
    box = (cx - 20, cy - 20, cx + cw + 20, cy + ch + 20)

    def on(p):
        im = Image.open(p).convert('RGBA').crop(box); c = checker(im.size); c.alpha_composite(im); return c.convert('RGB')
    base = Image.open(os.path.join(hd, f'f1983_{tag}.png')).convert('RGBA')
    base.alpha_composite(Image.open(os.path.join(M, 'card_contents.png')).convert('RGBA'))
    tiles = [on(os.path.join(M, 'menu_card_frame.png')), on(os.path.join(M, 'menu_card_parchment_field.png')), on(os.path.join(M, 'card_contents.png')),
             base.convert('RGB').crop(box), Image.open(R['capture']).convert('RGB').crop(box)]
    full = np.asarray(Image.open(os.path.join(hd, f'f1983_{tag}.png')).convert('RGB')).astype(float)
    mk = np.asarray(Image.open(os.path.join(M, 'units_water_g12_mask.png'))) > 0
    full[mk] = full[mk] * 0.4 + np.array([255, 0, 80]) * 0.6
    ov = Image.fromarray(full.astype(np.uint8))
    tw, th = int(tiles[0].width * 0.42), int(tiles[0].height * 0.42)
    tiles = [t.resize((tw, th), Image.LANCZOS) for t in tiles]
    o = ov.resize((int(ov.width * 0.45), int(ov.height * 0.45)), Image.LANCZOS)
    S = Image.new('RGB', (max(5 * tw + 60, o.width + 20), th + 30 + o.height), (40, 40, 44))
    for i, t in enumerate(tiles):
        S.paste(t, (10 + i * (tw + 10), 10))
    S.paste(o, (10, th + 20))
    out = os.path.join(hd, 'qa', f'card_layers_{tag.split("_")[0]}.png')
    S.save(out)
    return out


if __name__ == '__main__':
    hd = sys.argv[1]
    for tag in ('16x9_2560x1440', '4x3_2048x1536'):
        print(card_layers(hd, tag))
        print(flame_sheet.sheet(os.path.join(hd, f'mattes_{tag}'), os.path.join(hd, 'qa', f'candle_flames_v2_{tag.split("_")[0]}.png'), 5))
