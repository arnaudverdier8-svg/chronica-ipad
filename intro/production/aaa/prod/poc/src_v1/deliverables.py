"""Client-review extras: keyframe f1760, contact sheet, A/B swap still with difference, final frame vs the live menu.
python3 deliverables.py"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from r25render import grade
from exr import read_exr
import numpy as np, cv2, shutil

FR = f'{POC}/frames'
shutil.copy(f'{FR}/f1760.png', f'{POC}/keyframe_f1760_2560x1440.png')
os.system(f'python3 {POC}/src/contact.py {FR} {POC}/contact_sheet.jpg 1664 1676 1688 1700 1710 1719 1722 1726 1734 1740 1746 1752 1760 1766 1782')
# A/B at the swap: R25 last state (f1719) vs Eevee zero-tilt still (f1725), both graded without grain, + |diff| x4
r = np.load(f'{POC}/r25/last_linear.npy').astype(np.float32)
e = read_exr(f'{POC}/ev/f1725.exr')[..., :3]
a = grade(r, grain=0); b = grade(e, grain=0)
d = np.clip(np.abs(a.astype(int) - b.astype(int)) * 4, 0, 255).astype(np.uint8)
y0, x0 = 380, 1150
crop = lambda im: im[y0:y0 + 560, x0:x0 + 840]
ab = np.hstack([crop(a), crop(b), crop(d)])
for i, t in enumerate(['R25 f1719 (2D)', 'Eevee zero-tilt f1725', '|diff| x4']):
    cv2.putText(ab, t, (12 + 840 * i, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
cv2.imwrite(f'{POC}/ab_swap_f1719_vs_f1725.jpg', cv2.cvtColor(ab, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
# final pose vs the live menu's first frame (same camera; the menu chrome is out of scope for this proof)
g = cv2.imread(f'{A}/game/02_menu_first_frame_1920x1080.png')
o = cv2.resize(cv2.imread(f'{FR}/f1782.png'), (1920, 1080), interpolation=cv2.INTER_AREA)
mix = o.copy(); mix[:, 960:] = g[:, 960:]
cv2.line(mix, (960, 0), (960, 1080), (255, 255, 255), 2)
cmp_ = np.vstack([np.hstack([cv2.resize(o, (960, 540)), cv2.resize(g, (960, 540))]), np.hstack([cv2.resize(mix, (960, 540)), np.zeros((540, 960, 3), np.uint8)])])
cv2.putText(cmp_, 'PoC f1782 (menu camera)', (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
cv2.putText(cmp_, 'live menu first frame', (972, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
cv2.putText(cmp_, 'split: PoC left | game right', (12, 570), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
cv2.imwrite(f'{POC}/compare_f1782_vs_menu.jpg', cmp_, [cv2.IMWRITE_JPEG_QUALITY, 90])
print('ok')
