"""Client review sheet for the hand-off keyframe (v2).

  row 1  context strip: what the client is approving is a TRANSITION, not a poster:
         PoC f1760 (reference snapshot) -> f1983 -> the card writing itself (illustrative: f1983 + card_contents under a
         reading-order wipe, 35 % and 70 %) -> the live menu
  row 2  16:9: live capture | f1983 | |diff| x8 (outside the card: 0)
  row 3  4:3:  the same
  row 4  100 % crops of the card's top-left and bottom-right corners, live vs f1983, for BOTH buckets

usage: python3 review_sheet.py OUTDIR  (expects f1983_<tag>.png, report_<tag>.json, mattes_<tag>/card_contents.png in OUTDIR)
"""
import sys, os, json, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/game/fonts/AlegreyaSans-Medium.ttf'
POC = 'work/ref/poc_keyframe_f1760_v2_snapshot.png'


def label(img, text, size=26, pos=(14, 10)):
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, size)
    x, y = pos
    bb = d.textbbox((x, y), text, font=f)
    d.rectangle([bb[0] - 8, bb[1] - 5, bb[2] + 8, bb[3] + 6], fill=(12, 12, 16))
    d.text((x, y), text, font=f, fill=(236, 222, 190))
    return img


def writes_itself(hd, tag, R, p):
    """f1983 with the live card contents revealed down to progress p of the card height (soft 40 px edge)."""
    f = Image.open(os.path.join(hd, f'f1983_{tag}.png')).convert('RGBA')
    c = np.asarray(Image.open(os.path.join(hd, f'mattes_{tag}', 'card_contents.png')).convert('RGBA')).astype(np.float32)
    cx, cy, cw, ch = R['card_draw_rect_px']
    ys = np.arange(c.shape[0], dtype=np.float32)[:, None]
    wipe = np.clip((cy + 0.12 * ch + p * 0.80 * ch - ys) / 40.0, 0, 1)
    c[..., 3] *= wipe
    f.alpha_composite(Image.fromarray(np.clip(c, 0, 255).astype(np.uint8), 'RGBA'))
    return f.convert('RGB')


def main(outdir):
    reps = [r for r in sorted(glob.glob(os.path.join(outdir, 'report_*.json'))) if not os.path.basename(r)[7:-5].endswith('_v1')]
    data = []
    for rep in reps:
        tag = os.path.basename(rep)[7:-5]
        R = json.load(open(rep))
        data.append((tag, R, Image.open(R['capture']).convert('RGB'), Image.open(os.path.join(outdir, f'f1983_{tag}.png')).convert('RGB')))
    tag169, R169, live169, f169 = data[0]
    gap = 12
    tw = 840
    Wt = 3 * tw + 4 * gap

    # --- row 1: context strip (5 panels)
    pw = (Wt - 6 * gap) // 5
    ph = int(round(pw * 9 / 16))
    strip = []
    poc = Image.open(os.path.join(outdir, POC)).convert('RGB') if os.path.exists(os.path.join(outdir, POC)) else None
    strip.append(label((poc or f169).resize((pw, ph), Image.LANCZOS), 'S24 PoC f1760 (snapshot): the board', 20, (10, 8)))
    strip.append(label(f169.resize((pw, ph), Image.LANCZOS), 'S26 f1983: the page waits', 20, (10, 8)))
    for p, nm in ((0.35, '35 %'), (0.70, '70 %')):
        strip.append(label(writes_itself(outdir, tag169, R169, p).resize((pw, ph), Image.LANCZOS), f'card writes itself {nm} (illustrative)', 20, (10, 8)))
    strip.append(label(live169.resize((pw, ph), Image.LANCZOS), 'live menu (what the player gets)', 20, (10, 8)))

    # --- rows 2-3: live | f1983 | diff, per bucket
    rows = []
    for tag, R, live, f in data:
        a = np.asarray(live).astype(np.int16); b = np.asarray(f).astype(np.int16)
        d = np.clip(np.abs(a - b).max(2) * 8, 0, 255).astype(np.uint8)
        dimg = Image.fromarray(np.stack([d] * 3, 2))
        W, H = live.size
        th = int(round(H * tw / W))
        oc = R['outside_card_rect']
        rows.append([label(live.resize((tw, th), Image.LANCZOS), f'live menu, no save, {W}x{H}'),
                     label(f.resize((tw, th), Image.LANCZOS), 'f1983 hand-off: card left blank'),
                     label(dimg.resize((tw, th), Image.BOX), f'|diff| x8: outside card max {oc["max_abs_diff"]}/255, {oc["changed_px"]} px')])

    # --- row 4: 100 % corner crops, both buckets (8 crops)
    cw_, ch_ = 300, 210
    crops = []
    for tag, R, live, f in data:
        cx, cy, cw, ch = R['card_draw_rect_px']
        short = tag.split('_')[0]
        for nm, bx in (('top-left', (int(cx) - 10, int(cy) - 10)), ('bottom-right', (int(cx + cw) - cw_ + 10, int(cy + ch) - ch_ + 10))):
            for what, im in (('live', live), ('f1983', f)):
                crops.append(label(im.crop((bx[0], bx[1], bx[0] + cw_, bx[1] + ch_)), f'{short} {nm}, {what}, 100 %', 17, (8, 6)))

    Ht = gap + ph + gap + sum(r[0].size[1] + gap for r in rows) + ch_ + gap + 70
    sheet = Image.new('RGB', (Wt, Ht), (20, 20, 24))
    y = gap
    for i, t in enumerate(strip):
        sheet.paste(t, (gap + i * (pw + gap), y))
    y += ph + gap
    for r in rows:
        x = gap
        for p in r:
            sheet.paste(p, (x, y)); x += p.size[0] + gap
        y += r[0].size[1] + gap
    x = gap
    sx = (Wt - gap) // 8
    for c in crops:
        sheet.paste(c, (x, y)); x += sx
    label(sheet, 'CHRONICA intro - KEYFRAME f1983 (S26): the hand-off frame. Every pixel outside the card parchment is the live game, bit for bit. '
                 'Illustrative frames are composites of f1983 and the live card contents, not the final CSS wipe.', 22, (gap + 4, y + ch_ + 18))
    sheet.save(os.path.join(outdir, 'review_sheet_f1983.png'))
    sheet.convert('RGB').save(os.path.join(outdir, 'review_sheet_f1983.jpg'), quality=90)
    return sheet.size


if __name__ == '__main__':
    print(main(sys.argv[1]))
