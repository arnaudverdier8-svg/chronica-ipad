"""100 % crops of a keyframe PNG (16-bit or 8-bit): crops.py <png> <outdir> [suffix]"""
import sys, os, cv2, numpy as np
src, out = sys.argv[1], sys.argv[2]
sfx = sys.argv[3] if len(sys.argv) > 3 else ''
os.makedirs(out, exist_ok=True)
im = cv2.imread(src, -1)
if im.dtype == np.uint16:
    im = (im / 257.0 + 0.5).astype(np.uint8)
C = dict(c01_thread_tiedown_topleft=(250, 0, 900, 330, 1), c02_border_lions=(480, 60, 1200, 420, 1), c03_capital_crown=(1230, 360, 1990, 960, 1),
         c04_large_town_pennant=(1850, 600, 2560, 1060, 1), c05_river_bridge_hamlet=(180, 940, 920, 1440, 1), c06_road_four_colours=(900, 980, 1700, 1300, 1),
         c07_ploughed_meadow=(1150, 1150, 1950, 1440, 1), c08_hill_town_tree=(900, 700, 1650, 1120, 1), c09_thread_tiedown_3x=(330, 25, 580, 125, 3),
         c10_top_left_corner_blur=(0, 0, 420, 300, 1))
for k, (x0, y0, x1, y1, z) in C.items():
    c = im[y0:y1, x0:x1]
    if z != 1:
        c = cv2.resize(c, None, fx=z, fy=z, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(os.path.join(out, k + sfx + '.png'), c)
print('ok')
