"""Review sheets of the v3 touch-up round: v2 vs v3 at 100 % (shield, strands, crown, void core, lords) + the full frame, and the
iteration strips (what was tried).  python3 review_v3.py"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np, cv2
OUT = os.path.join(HERE, '..', 'out'); V2 = os.path.join(HERE, '..', 'out_v2'); WK = os.path.join(HERE, '..', 'work', 'v3')
a = cv2.imread(os.path.join(V2, 'f669_2560x1440.png')); b = cv2.imread(os.path.join(OUT, 'f669_2560x1440.png'))
rep = json.load(open(os.path.join(OUT, 'f669_report.json')))['crops']


def lab(im, t, w=250):
    im = im.copy()
    cv2.rectangle(im, (0, 0), (w, 30), (0, 0, 0), -1)
    cv2.putText(im, t, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (240, 235, 220), 2, cv2.LINE_AA)
    return im


def pair(name, x, y, w, h, scale=1.0, tags=('v2 (before)', 'v3 (after)')):
    ca = lab(a[y:y + h, x:x + w], tags[0]); cb = lab(b[y:y + h, x:x + w], tags[1])
    o = np.hstack([ca, np.full((h, 6, 3), 255, np.uint8), cb])
    if scale != 1.0:
        o = cv2.resize(o, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)
    cv2.imwrite(os.path.join(OUT, f'f669_v2_vs_v3_{name}.png'), o)


x, y, w, h = rep['green_lord_shield']; pair('shield_green_lord', x + 110, y + 100, 420, 380, 1.5)
x, y, w, h = rep['loose_purple_strands']; pair('strands', x + 230, y + 10, 460, 360, 1.4)
x, y, w, h = rep['crown_gold_metal']; pair('crown_gold', x + 20, y + 20, 480, 300, 1.4)
x, y, w, h = rep['void_pool_core']; pair('void_needle_holes_underdrawing', x + 60, y + 90, 640, 400, 1.2)
x, y, w, h = rep['red_lord_face_rim']; pair('red_lord_rim_unchanged', x, y, 460, 420, 1.0)
x, y, w, h = rep['blue_lord_face_rim']; pair('blue_lord_rim_unchanged', x, y, 460, 420, 1.0)
full = np.hstack([lab(cv2.resize(a, (1280, 720), interpolation=cv2.INTER_AREA), 'v2'), np.full((720, 6, 3), 255, np.uint8),
                  lab(cv2.resize(b, (1280, 720), interpolation=cv2.INTER_AREA), 'v3')])
cv2.imwrite(os.path.join(OUT, 'f669_v2_vs_v3_full.jpg'), full, [cv2.IMWRITE_JPEG_QUALITY, 90])

# ---- iteration strips ----------------------------------------------------------------------------------------------------
def rd(n): return cv2.imread(os.path.join(WK, n))
# strands window (centre 300, 232 mm, 1280x720 at 5.8125 px/mm): its top-left in the full frame
tlx = int(round(1280 - 640 + (300 - 307.7129) * 5.8125)); tly = int(round(720 - 360 + (232 - 173) * 5.8125))
sw = (slice(150, 440), slice(480, 820))
fin = b[tly:tly + 720, tlx:tlx + 1280]; old = a[tly:tly + 720, tlx:tlx + 1280]
tiles = [(old, 'v2: tubes 1.0-1.4 mm'), (rd('s1_strands.png'), 'try 1: thin, no fuzz / twist'), (rd('s3_strands.png'), 'try 2: fuzz everywhere'),
         (rd('s6_strands.png'), 'try 3: ply + side fuzz, robe dye'), (rd('s10_strands.png'), 'try 4: designed shapes'), (fin, 'v3 final (full frame)')]
row1 = np.hstack([lab(cv2.resize(t[sw], None, fx=1.0, fy=1.0), n, 330) for t, n in tiles])
shield = [(a, 'v2'), (rd('h1_shield.png'), 'try 1 (dun, cool)'), (b, 'v3 final')]
c = []
sx, sy, sw_, sh_ = rep['green_lord_shield']
c.append(lab(a[sy + 100:sy + 480, sx + 110:sx + 530], 'v2 white blob', 220))
h1 = rd('h1_shield.png'); c.append(lab(cv2.resize(h1[220:600, 560:980], (420, 380)), 'try 1: x0.36/0.30/0.235', 330))
c.append(lab(b[sy + 100:sy + 480, sx + 110:sx + 530], 'v3: x0.46/0.35/0.22 dun', 300))
row2 = np.hstack(c)
crown = [(a, 'v2: flat cream'), (rd('c1_crown_grid.png'), None)]
cg = [rd('c5_crown_grid.png'), rd('crown_tune.png')]
ccx, ccy, ccw, cch = rep['crown_gold_metal']
c3 = [lab(cv2.resize(a[ccy + 40:ccy + 300, ccx + 90:ccx + 430], (420, 320)), 'v2: flat cream gold', 260),
      lab(cv2.resize(rd('c1_crown_grid.png')[0:690, 0:720], (420, 402))[0:320], 'try 1: mild curve', 260),
      lab(cv2.resize(rd('c3_crown_grid.png')[690:1380, 0:720], (420, 402))[0:320], 'try 2: pale ramp (silver)', 300),
      lab(cv2.resize(rd('c5_crown_grid.png')[690:1380, 0:720], (420, 402))[0:320], 'try 3: saturated ramp', 300),
      lab(cv2.resize(b[ccy + 40:ccy + 300, ccx + 90:ccx + 430], (420, 320)), 'v3 final: grooves floor, glints', 330)]
row3 = np.hstack(c3)
W_ = max(row1.shape[1], row2.shape[1], row3.shape[1])
def padw(r): return np.hstack([r, np.zeros((r.shape[0], W_ - r.shape[1], 3), np.uint8)]) if r.shape[1] < W_ else r
sheet = np.vstack([padw(row1), padw(row2), padw(row3)])
sheet = cv2.resize(sheet, None, fx=0.75, fy=0.75, interpolation=cv2.INTER_AREA)
cv2.imwrite(os.path.join(OUT, 'f669_v3_iterations.jpg'), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
print('ok', sheet.shape)
