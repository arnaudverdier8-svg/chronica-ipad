"""v3 QA numbers (v2 vs v3 keyframe, graded sRGB, Rec.709 luma 0-1).  python3 measure_v3.py [v3.png] [v2.png]
Writes ../out/f669_v3_measurements.json and prints a table."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np, cv2
import shot, silhouette as SIL
OUT = os.path.join(HERE, '..', 'out')
p3 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(OUT, 'f669_2560x1440.png')
p2 = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, '..', 'out_v2', 'f669_2560x1440.png')
W709 = np.array([0.2126, 0.7152, 0.0722], np.float32)
ims = {k: cv2.imread(p)[..., ::-1].astype(np.float32) / 255 for k, p in (('v2', p2), ('v3', p3))}
Y = {k: v @ W709 for k, v in ims.items()}
v = shot.view_of(669); s = v['px_per_mm']
x0 = v['cx_mm'] - 1280 / s; y0 = v['cy_mm'] - 720 / s
def px(xm, ym): return int(round((xm - x0) * s)), int(round((ym - y0) * s))
res = {}
# ---- void mask (as measure.py): inside the silhouette, eroded 6 mm, 150 < y < 255 mm
poly = (SIL.sil_mm() - [x0, y0]) * s
m = np.zeros((1440, 2560), np.uint8); cv2.fillPoly(m, [np.round(poly).astype(np.int32)], 1)
m = cv2.erode(m, np.ones((int(6 * s / 2) * 2 + 1,) * 2, np.uint8)).astype(bool)
yy = (np.arange(1440) / s + y0)[:, None] * np.ones((1, 2560)); mm = m & (yy > 150) & (yy < 255)
for k in ims:
    y = Y[k][mm]
    q = np.quantile(y, [.01, .05, .25, .5, .75, .95]).round(3).tolist()
    res.setdefault('void_luma', {})[k] = dict(mean=round(float(y.mean()), 3), p1_p5_p25_p50_p75_p95=q, std=round(float(y.std()), 3),
                                              frac_below_0p15=round(float((y < 0.15).mean()), 4), frac_below_0p10=round(float((y < 0.10).mean()), 4))
# ---- needle-hole / underdrawing depth: darkest 2 % of the void relative to its median
for k in ims:
    y = Y[k][mm]; res['void_luma'][k]['p2_over_median'] = round(float(np.quantile(y, 0.02) / np.median(y)), 3)
# ---- lords (faces) and wall, unchanged?
reg = dict(red_face=(198, 148), blue_face=(396, 148), gold_face=(126, 158), green_face=(472, 156), wallL=(120, 60), wallR=(470, 60), table=(300, 285))
res['regions_mean_luma'] = {}
for nm, (xm, ym) in reg.items():
    X, Yp = px(xm, ym); R = int(5 * s)
    res['regions_mean_luma'][nm] = {k: round(float(Y[k][Yp - R:Yp + R, X - R:X + R].mean()), 3) for k in ims}
# ---- (a) the shield of the green lord: the charge (horse head) vs the field and the border
X0, Y0 = px(478, 205); X1, Y1 = px(492, 222)
box = (slice(Y0, Y1), slice(X0, X1))
res['green_shield_box'] = {k: dict(max=round(float(Y[k][box].max()), 3), p99=round(float(np.quantile(Y[k][box], .99)), 3), mean=round(float(Y[k][box].mean()), 3)) for k in ims}
Xr, Yr = px(485, 224); R = int(4 * s)
res['green_robe_luma_next_to_shield'] = {k: round(float(Y[k][Yr - R:Yr + R, Xr - R:Xr + R].mean()), 3) for k in ims}
# ---- the whole right third (x 0.78-1.0): brightest 0.05 % of pixels (the blob was the brightest thing there)
for k in ims:
    sub = Y[k][400:1100, int(0.78 * 2560):]
    res.setdefault('right_third_p9995', {})[k] = round(float(np.quantile(sub, 0.9995)), 3)
# ---- ratio of the blob region to everything else in the green lord's tunic
res['green_shield_box_max_over_robe'] = {k: round(res['green_shield_box'][k]['max'] / res['green_robe_luma_next_to_shield'][k], 2) for k in ims}
json.dump(res, open(os.path.join(OUT, 'f669_v3_measurements.json'), 'w'), indent=1)
print(json.dumps(res, indent=1))
