"""QA contact sheet of the flame / unlit / full candle layers at xN over dark and light grounds.
usage: python3 flame_sheet.py MATTE_DIR OUT.png [scale]"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw

def on(bg, im):
    b = Image.new('RGBA', im.size, bg); b.alpha_composite(im); return b.convert('RGB')

def sheet(mdir, out, scale=6):
    bases = [b for b in ('candle_left', 'candle_right', 'table_edge_bottom') if os.path.exists(os.path.join(mdir, b + '_flame.png'))]
    rows = []
    for base in bases:
        full = Image.open(os.path.join(mdir, base + '.png')).convert('RGBA')
        a = np.asarray(full)[..., 3]
        ys, xs = np.nonzero(a > 4)
        # crop window around the top of the candle (flame + wax rim + some body)
        x0, y0 = xs[(ys < ys.min() + 40)].min() - 14, ys.min() - 8
        if base == 'table_edge_bottom':
            ys2 = ys[(xs > xs.min())]
            x0, y0 = 280, 1330 if full.size[1] > 1400 else 1330
            box = (x0, ys.min() - 8, x0 + 56, ys.min() + 104)
        else:
            box = (x0, y0, x0 + 64, y0 + 112)
        tiles = []
        for suf in ('', '_unlit', '_flame_core', '_waxglow'):
            im = Image.open(os.path.join(mdir, base + suf + '.png')).convert('RGBA').crop(box)
            for bg in ((22, 24, 32, 255), (200, 200, 200, 255)):
                tiles.append(on(bg, im).resize((im.width * scale, im.height * scale), Image.NEAREST))
        # recomposite flame over unlit
        f = Image.open(os.path.join(mdir, base + '_flame.png')).convert('RGBA').crop(box)
        u = Image.open(os.path.join(mdir, base + '_unlit.png')).convert('RGBA').crop(box)
        u2 = u.copy(); u2.alpha_composite(f)
        for bg in ((22, 24, 32, 255), (200, 200, 200, 255)):
            tiles.append(on(bg, u2).resize((u2.width * scale, u2.height * scale), Image.NEAREST))
        rows.append(tiles)
    gap = 6
    tw, th = rows[0][0].size
    n = len(rows[0])
    S = Image.new('RGB', (n * (tw + gap) + gap, len(rows) * (th + gap) + gap), (50, 50, 56))
    for r, tiles in enumerate(rows):
        for c, t in enumerate(tiles):
            S.paste(t, (gap + c * (tw + gap), gap + r * (th + gap)))
    S.save(out)
    return out

if __name__ == '__main__':
    sheet(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 6)
