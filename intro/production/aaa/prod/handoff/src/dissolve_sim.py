"""Simulation of the hand-off dissolve (16:9): the overlay holding f1983 fades out over the live game.
    shown(t) = alpha(t) * f1983 + (1 - alpha(t)) * live(frame)        (outside the card)
alpha follows the CSS 'ease' curve cubic-bezier(.25,.1,.25,1) over 0.9 s (storyboard section 13).

  A  the dissolve starts as soon as the engine-ready signal fires (about menu frame 1): the live game under the
     overlay is the settling state (stored capture: menu frame 3; the nameplates are still popping in larger);
  B  the overlay waits for 30 presented rAF frames first (the recommendation in handoff_spec.json): the live game is
     the state f1983 was built on (menu frame 30) or later (menu frame 120 as a later-state proxy).

This is arithmetic on the stored captures, not a capture of the real overlay on a device. It shows what the
recommendation buys; the on-device G12 run stays mandatory.

usage: python3 dissolve_sim.py HANDOFF_DIR
"""
import sys, os, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

FONT = '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/game/fonts/AlegreyaSans-Medium.ttf'


def bezier_ease(x, p1=(0.25, 0.1), p2=(0.25, 1.0), n=2000):
    """CSS cubic-bezier timing function y(x)."""
    t = np.linspace(0, 1, n)
    bx = 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3
    by = 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3
    return np.interp(x, bx, by)


def overlay_alpha(t, dur=0.9):
    return 1.0 - float(bezier_ease(np.clip(t / dur, 0, 1)))


def lab(img, text, size=24, pos=(8, 6)):
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, size)
    bb = d.textbbox(pos, text, font=f)
    d.rectangle([bb[0] - 6, bb[1] - 4, bb[2] + 6, bb[3] + 5], fill=(12, 12, 16))
    d.text(pos, text, font=f, fill=(236, 222, 190))
    return img


def main(hd):
    R = json.load(open(os.path.join(hd, 'report_16x9_2560x1440.json')))
    ld = lambda p: np.asarray(Image.open(p).convert('RGB')).astype(np.float64)
    f = ld(os.path.join(hd, 'f1983_16x9_2560x1440.png'))
    c3 = ld(os.path.join(hd, 'capture/c169_a/menu_2560x1440_mf003_r0.png'))
    c30 = ld(os.path.join(hd, 'capture/c169_a/menu_2560x1440_mf030_r0.png'))
    c120 = ld(os.path.join(hd, 'capture/c169_a/menu_2560x1440_mf120_r0.png'))
    cx, cy, cw, ch = [int(v) for v in R['card_draw_rect_px']]
    out = np.ones(f.shape[:2], bool)
    out[cy:cy + ch + 1, cx:cx + cw + 1] = False
    rows = []
    for tm in (0.1, 0.2, 0.3, 0.45, 0.6):
        a = overlay_alpha(tm)
        A = a * f + (1 - a) * c3
        B = a * f + (1 - a) * c30
        B2 = a * f + (1 - a) * c120
        # the dissolve should be a pure fade of f1983 into a still of the same picture: reference = f1983 itself
        gA = np.abs(A - f).mean(2); gB = np.abs(B - f).mean(2); gB2 = np.abs(B2 - f).mean(2)
        rows.append(dict(t_s=tm, overlay_opacity=round(a, 3),
                         A_start_at_frame1_mean_abs=round(float(gA[out].mean()), 3), A_px_over_16=round(float((gA[out] > 16).mean() * 100), 2),
                         B_after_30_frames_mean_abs=round(float(gB[out].mean()), 3), B_px_over_16=round(float((gB[out] > 16).mean() * 100), 2),
                         B_later_state_mf120_mean_abs=round(float(gB2[out].mean()), 3)))
    # crops of the three biggest pop-in regions at the 0.2 s mark
    d = np.abs(c3 - c30).max(2); d[~out] = 0
    m = ndimage.binary_dilation(d > 40, iterations=12)
    labm, n = ndimage.label(m)
    sl = ndimage.find_objects(labm)
    items = sorted([(int((labm[s] == i + 1).sum()), s) for i, s in enumerate(sl)], key=lambda t: -t[0])[:3]
    a = overlay_alpha(0.2)
    tiles = []
    for ar, s in items:
        x0, y0, x1, y1 = s[1].start, s[0].start, s[1].stop, s[0].stop
        x0 = max(0, x0 - 20); y0 = max(0, y0 - 20); x1 = min(f.shape[1], x1 + 20); y1 = min(f.shape[0], y1 + 20)
        row = []
        for nm, live in (('A: starts at frame 1', c3), ('B: waits 30 frames', c30)):
            sh = (a * f + (1 - a) * live)[y0:y1, x0:x1]
            row.append(lab(Image.fromarray(np.clip(sh, 0, 255).astype(np.uint8)), nm, 18))
        tiles.append(row)
    wmax = max(t[0].width for t in tiles); hsum = sum(t[0].height for t in tiles) + 10 * (len(tiles) + 1)
    S = Image.new('RGB', (2 * wmax + 30, hsum + 40), (30, 30, 34))
    lab(S, f'dissolve at t = 0.2 s (overlay opacity {a:.2f}), 16:9, outside the card: A starts at frame 1, B waits 30 frames', 20, (10, 8))
    y = 50
    for r in tiles:
        S.paste(r[0], (10, y)); S.paste(r[1], (wmax + 20, y)); y += r[0].height + 10
    S.save(os.path.join(hd, 'qa', 'dissolve_ghost_sim_16x9.png'))
    rep = dict(model='alpha(t) = 1 - cubic-bezier(.25,.1,.25,1)(t / 0.9 s); shown = alpha f1983 + (1 - alpha) live; outside the card rect',
               frames_used='A: live = menu frame 3 capture; B: live = menu frame 30 capture (f1983 base) and menu frame 120 as a later-state proxy',
               table=rows, crops='qa/dissolve_ghost_sim_16x9.png (opacity at 0.2 s = %.2f)' % a,
               caveat='arithmetic on stored captures; not the real overlay on a device')
    json.dump(rep, open(os.path.join(hd, 'qa', 'dissolve_ghost_sim.json'), 'w'), indent=1)
    print(json.dumps(rows, indent=1))


if __name__ == '__main__':
    main(sys.argv[1])
