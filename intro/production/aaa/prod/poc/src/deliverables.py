"""Deliverable sheets (v3): keyframe f1760, contact sheet, before/after (v1 | v2 | v3), A/B swap check, f1782 vs the live menu, 1:1 detail sheets
(stitch-on frontier, pieces, gold glint).  python3 deliverables.py"""
import sys, os, json, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import numpy as np, cv2
FR = f'{POC}/frames'
def rd(p):
    im = cv2.imread(p)
    if im is None: raise FileNotFoundError(p)
    return im
def lab(im, t, s=0.8):
    cv2.putText(im, t, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, s, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(im, t, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, s, (255, 255, 255), 2, cv2.LINE_AA)
    return im
def small(im, w=640, h=360): return cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA)
JPG = [cv2.IMWRITE_JPEG_QUALITY, 90]

# keyframe
shutil.copy(f'{FR}/f1760.png', f'{POC}/keyframe_f1760_2560x1440.png')
# contact sheet
fs = [1664, 1668, 1680, 1696, 1708, 1719, 1726, 1730, 1736, 1744, 1752, 1760, 1766, 1770, 1776, 1782]
tiles = [lab(small(rd(f'{FR}/f{f}.png')), f'f{f}') for f in fs]
cv2.imwrite(f'{POC}/contact_sheet.jpg', np.concatenate([np.concatenate(tiles[i:i + 4], 1) for i in range(0, 16, 4)], 0), JPG)
# before / after: v1 | v2 | v3 at the key moments
pairs = [1664, 1688, 1710, 1719, 1740, 1752, 1760, 1782]
rows = []
for f in pairs:
    row = []
    a = lab(small(rd(f'{POC}/v1_frames/f{f}_v1.jpg'), 512, 288), f'f{f}  v1', 0.65)
    b = lab(small(rd(f'{POC}/v2_frames/f{f}.png'), 512, 288), f'f{f}  v2', 0.65)
    c = lab(small(rd(f'{FR}/f{f}.png'), 512, 288), f'f{f}  v3', 0.65)
    rows.append(np.concatenate([a, b, c], 1))
cv2.imwrite(f'{POC}/before_after_v1_v2_v3.jpg', np.concatenate(rows, 0), JPG)
# A/B swap
from exr import read_exr
from r25render import grade
r = np.load(f'{POC}/r25/last_linear.npy').astype(np.float32)
e = read_exr(f'{POC}/ev/f1725.exr')[..., :3]
if e.shape[1] != r.shape[1]: e = cv2.resize(e, (r.shape[1], r.shape[0]), interpolation=cv2.INTER_AREA)
ga = cv2.cvtColor(grade(r, grain=0), cv2.COLOR_RGB2BGR); gb = cv2.cvtColor(grade(e, grain=0), cv2.COLOR_RGB2BGR)
diff = np.clip(np.abs(ga.astype(np.float32) - gb.astype(np.float32)) * 8, 0, 255).astype(np.uint8)
sz = (853, 480)
cv2.imwrite(f'{POC}/ab_swap_f1719_vs_f1725.jpg', np.concatenate([lab(cv2.resize(ga, sz), 'R25 2D (f1719 state)'), lab(cv2.resize(gb, sz), 'Eevee zero-tilt f1725'), lab(cv2.resize(diff, sz), 'abs diff x8')], 1), JPG)
# f1782 vs the live menu (same camera): v2, v3, menu, v3 neutral
menu = rd(f'{A}/prod/handoff/capture/c169_a/menu_2560x1440_mf030_r0.png')
sz = (853, 480)
tiles = [lab(cv2.resize(rd(f'{POC}/v2_frames/f1782.png'), sz), 'v2 f1782'), lab(cv2.resize(rd(f'{FR}/f1782.png'), sz), 'v3 f1782 (candlelit, Act V grade, light state 45 % toward D)'),
         lab(cv2.resize(menu, sz), 'live menu'), ]
neutral = f'{POC}/preview/ev_neutral/f1782.png'
if os.path.exists(neutral): tiles.append(lab(cv2.resize(rd(neutral), sz), 'v3 f1782 neutral light (palette check)'))
while len(tiles) % 2: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(f'{POC}/compare_f1782_vs_menu.jpg', np.concatenate([np.concatenate(tiles[i:i + 2], 1) for i in range(0, len(tiles), 2)], 0), JPG)


def crop(f, x, y, w, h, s=1.0, d=FR):
    im = rd(f'{d}/f{f}.png')[y:y + h, x:x + w]
    return cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC) if s != 1 else im
# 1:1 stitch-on frontier detail (R25 phase): first strands, land frontier, sea frontier, underdrawing ahead
tiles = [lab(crop(1666, 1200, 440, 480, 270), 'f1666 first strands'), lab(crop(1680, 1050, 330, 480, 270), 'f1680 land frontier'),
         lab(crop(1690, 400, 960, 480, 270), 'f1690 sea frontier'), lab(crop(1676, 520, 420, 480, 270), 'f1676 underdrawing ahead')]
cv2.imwrite(f'{POC}/stitch_on_detail_1to1.jpg', np.concatenate([np.concatenate(tiles[:2], 1), np.concatenate(tiles[2:], 1)], 0), JPG)
# pieces at 1:1: town, figure cards, forest, footprints
tiles = [lab(crop(1760, 1380, 500, 480, 270), 'f1760 Grandbois 1:1'), lab(crop(1760, 1130, 780, 480, 270), 'f1760 figure cards 1:1'),
         lab(crop(1745, 700, 560, 480, 270), 'f1745 footprints + pieces 1:1'), lab(crop(1760, 620, 380, 480, 270), 'f1760 forest 1:1')]
cv2.imwrite(f'{POC}/pieces_detail_1to1.jpg', np.concatenate([np.concatenate(tiles[:2], 1), np.concatenate(tiles[2:], 1)], 0), JPG)
print('deliverable sheets written')
