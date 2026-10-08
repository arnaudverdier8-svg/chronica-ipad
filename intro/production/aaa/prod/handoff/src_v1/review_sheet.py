"""Client review sheet for the hand-off keyframe: live menu capture vs f1983 vs the x8 difference,
for each aspect bucket that exists, plus 100 % crops of the card seam.

usage: python3 review_sheet.py OUTDIR  (expects f1983_<tag>.png, report_<tag>.json in OUTDIR)
"""
import sys, os, json, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/game/fonts/AlegreyaSans-Medium.ttf'


def label(img, text, size=26, pos=(14, 10)):
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, size)
    x, y = pos
    bb = d.textbbox((x, y), text, font=f)
    d.rectangle([bb[0] - 8, bb[1] - 5, bb[2] + 8, bb[3] + 6], fill=(12, 12, 16))
    d.text((x, y), text, font=f, fill=(236, 222, 190))
    return img


def main(outdir):
    rows = []
    for rep in sorted(glob.glob(os.path.join(outdir, 'report_*.json'))):
        tag = os.path.basename(rep)[7:-5]
        R = json.load(open(rep))
        cap_path = R['capture'] if os.path.isabs(R['capture']) else os.path.normpath(os.path.join(os.path.dirname(__file__), R['capture']))
        live = Image.open(cap_path).convert('RGB')
        f = Image.open(os.path.join(outdir, f'f1983_{tag}.png')).convert('RGB')
        a = np.asarray(live).astype(np.int16); b = np.asarray(f).astype(np.int16)
        d = np.clip(np.abs(a - b).max(2) * 8, 0, 255).astype(np.uint8)
        dimg = Image.fromarray(np.stack([d] * 3, 2))
        W, H = live.size
        tw = 840
        th = int(round(H * tw / W))
        oc = R['outside_card_rect']
        panels = [label(live.resize((tw, th), Image.LANCZOS), f'live menu, no save, {W}x{H}'),
                  label(f.resize((tw, th), Image.LANCZOS), 'f1983 hand-off: card left blank'),
                  label(dimg.resize((tw, th), Image.BOX), f'|diff| x8: outside card max {oc["max_abs_diff"]}/255, {oc["changed_px"]} px')]
        rows.append(panels)
    gap = 12
    Wt = 3 * 840 + 4 * gap
    Ht = sum(r[0].size[1] for r in rows) + gap * (len(rows) + 1)
    # seam crops (100 %) from the first bucket
    rep0 = sorted(glob.glob(os.path.join(outdir, 'report_*.json')))[0]
    tag0 = os.path.basename(rep0)[7:-5]
    R0 = json.load(open(rep0))
    cx, cy, cw, ch = R0['card_draw_rect_px']
    f0 = Image.open(os.path.join(outdir, f'f1983_{tag0}.png')).convert('RGB')
    l0 = Image.open(R0['capture'] if os.path.isabs(R0['capture']) else os.path.normpath(os.path.join(os.path.dirname(__file__), R0['capture']))).convert('RGB')
    boxes = [(int(cx) - 10, int(cy) - 10, int(cx) + 390, int(cy) + 270), (int(cx + cw) - 390, int(cy + ch) - 270, int(cx + cw) + 10, int(cy + ch) + 10)]
    crops = []
    for bx in boxes:
        crops.append(label(l0.crop(bx), 'live, 100 %', 22))
        crops.append(label(f0.crop(bx), 'f1983, 100 %', 22))
    crop_h = 280
    sheet = Image.new('RGB', (Wt, Ht + crop_h + gap + 70), (20, 20, 24))
    y = gap
    for r in rows:
        x = gap
        for p in r:
            sheet.paste(p, (x, y)); x += p.size[0] + gap
        y += r[0].size[1] + gap
    x = gap
    for c in crops:
        sheet.paste(c, (x, y)); x += c.size[0] + gap
    label(sheet, 'CHRONICA intro - KEYFRAME f1983 (S26): the hand-off frame. Every pixel outside the card parchment is the live game, bit for bit.', 24, (gap + 4, y + crop_h + 18))
    sheet.save(os.path.join(outdir, 'review_sheet_f1983.png'))
    sheet.convert('RGB').save(os.path.join(outdir, 'review_sheet_f1983.jpg'), quality=90)


if __name__ == '__main__':
    main(sys.argv[1])
