"""Deliverables sheets (v2): keyframe f1760, contact sheet, before/after vs v1, A/B swap check, f1782 vs the live menu.  python3 deliverables.py"""
import sys, os, json, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import numpy as np, cv2
FR = f'{POC}/frames'
def rd(p): return cv2.imread(p)
def lab(im, t, s=0.8):
    cv2.putText(im, t, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, s, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(im, t, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, s, (255, 255, 255), 2, cv2.LINE_AA)
    return im
# keyframe
shutil.copy(f'{FR}/f1760.png', f'{POC}/keyframe_f1760_2560x1440.png')
# contact sheet f1664 .. f1782
fs = [1664, 1676, 1688, 1700, 1710, 1719, 1722, 1726, 1734, 1740, 1746, 1752, 1760, 1766, 1774, 1782]
tiles = [lab(cv2.resize(rd(f'{FR}/f{f}.png'), (640, 360), interpolation=cv2.INTER_AREA), f'f{f}') for f in fs]
cv2.imwrite(f'{POC}/contact_sheet.jpg', np.concatenate([np.concatenate(tiles[i:i + 4], 1) for i in range(0, 16, 4)], 0), [cv2.IMWRITE_JPEG_QUALITY, 90])
# before / after (v1 left, v2 right)
pairs = [1664, 1676, 1700, 1719, 1740, 1752, 1760, 1782]
rows = []
for i in range(0, len(pairs), 2):
    row = []
    for f in pairs[i:i + 2]:
        a = lab(cv2.resize(rd(f'{POC}/v1_frames/f{f}_v1.jpg'), (640, 360), interpolation=cv2.INTER_AREA), f'f{f}  v1')
        b = lab(cv2.resize(rd(f'{FR}/f{f}.png'), (640, 360), interpolation=cv2.INTER_AREA), f'f{f}  v2')
        row += [a, b]
    rows.append(np.concatenate(row, 1))
cv2.imwrite(f'{POC}/before_after_v1_vs_v2.jpg', np.concatenate(rows, 0), [cv2.IMWRITE_JPEG_QUALITY, 90])
# A/B swap
from exr import read_exr
from r25render import grade
r = np.load(f'{POC}/r25/last_linear.npy').astype(np.float32)
e = read_exr(f'{POC}/ev/f1725.exr')[..., :3]
if e.shape[1] != r.shape[1]: e = cv2.resize(e, (r.shape[1], r.shape[0]), interpolation=cv2.INTER_AREA)
ga = cv2.cvtColor(grade(r, grain=0), cv2.COLOR_RGB2BGR); gb = cv2.cvtColor(grade(e, grain=0), cv2.COLOR_RGB2BGR)
diff = np.clip(np.abs(ga.astype(np.float32) - gb.astype(np.float32)) * 8, 0, 255).astype(np.uint8)
sz = (853, 480)
cv2.imwrite(f'{POC}/ab_swap_f1719_vs_f1725.jpg', np.concatenate([lab(cv2.resize(ga, sz), 'R25 2D (f1719 state)'), lab(cv2.resize(gb, sz), 'Eevee zero-tilt f1725'), lab(cv2.resize(diff, sz), 'abs diff x8')], 1), [cv2.IMWRITE_JPEG_QUALITY, 90])
# f1782 vs the live menu (same camera), shown + neutral
menu = rd(f'{A}/prod/handoff/capture/c169_a/menu_2560x1440_mf030_r0.png')
v2 = rd(f'{FR}/f1782.png')
v1 = rd(f'{POC}/v1_frames/f1782_v1.jpg')
sz = (853, 480)
neutral = f'{POC}/preview/ev_neutral/f1782.png'
tiles = [lab(cv2.resize(v1, sz), 'v1 f1782'), lab(cv2.resize(v2, sz), 'v2 f1782 (candlelit, act V grade)'), lab(cv2.resize(menu, sz), 'live menu')]
if os.path.exists(neutral): tiles.append(lab(cv2.resize(rd(neutral), sz), 'v2 f1782 neutral light (palette check)'))
while len(tiles) % 2: tiles.append(np.zeros_like(tiles[0]))
cv2.imwrite(f'{POC}/compare_f1782_vs_menu.jpg', np.concatenate([np.concatenate(tiles[i:i + 2], 1) for i in range(0, len(tiles), 2)], 0), [cv2.IMWRITE_JPEG_QUALITY, 90])
print('deliverable sheets written')
