"""Review sheets for the v2 fix round: before/after crops (v1 vs v2) at 100 %, and the crown-shadow diagnostic
(crown alpha | projected shadow | tether shadows | composite crop).  python3 review_sheets.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np, cv2
OUT = os.path.join(HERE, '..', 'out'); V1 = os.path.join(HERE, '..', 'out_v1')
a = cv2.imread(os.path.join(V1, 'f669_2560x1440.png')); b = cv2.imread(os.path.join(OUT, 'f669_2560x1440.png'))
def lab(im, t):
    im = im.copy(); cv2.putText(im, t, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4, cv2.LINE_AA); cv2.putText(im, t, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (240, 230, 210), 1, cv2.LINE_AA); return im
crops = {'void_and_strands': (1000, 560, 760, 700), 'crown_and_tethers': (1090, 280, 560, 460), 'shadow_in_void': (1380, 700, 600, 420),
         'table_ghosts_left': (60, 1020, 700, 420), 'table_ghosts_right': (1860, 1000, 700, 440)}
rows = []
for k, (x, y, w, h) in crops.items():
    rows.append(np.hstack([lab(a[y:y + h, x:x + w], 'v1 ' + k), np.zeros((h, 8, 3), np.uint8), lab(b[y:y + h, x:x + w], 'v2 ' + k)]))
for k, r in zip(crops, rows):
    cv2.imwrite(os.path.join(OUT, f'f669_v1_vs_v2_{k}.png'), r)
full = np.hstack([cv2.resize(a, (1280, 720), interpolation=cv2.INTER_AREA), cv2.resize(b, (1280, 720), interpolation=cv2.INTER_AREA)])
cv2.imwrite(os.path.join(OUT, 'f669_v1_vs_v2_full.jpg'), full, [cv2.IMWRITE_JPEG_QUALITY, 90])
