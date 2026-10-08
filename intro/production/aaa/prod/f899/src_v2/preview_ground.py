"""ground-only composite preview from work/plate (no Eevee): plates x pools (+ haze, table) -> graded sRGB.   python3 preview_ground.py OUT.png [scale]"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bkit
import numpy as np, cv2
import comp as C
import camera as CAM, arc as ARC
from chron import grade
from chron.color import hex_lin
ROOT = C.ROOT; shot = C.shot
out = sys.argv[1]; sc = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
plate = {k: np.load(os.path.join(ROOT, 'work', 'plate_v2', f'plate_{k}_screen.npy')).astype(np.float32) for k in 'hcf'}
X, Y, Zg = C.ground_maps()
HR = shot['hearth']
ph = C.pool(X, Y, HR['kmap'], lobes=HR.get('lobes'))[..., None]
lw, bw = ARC.weights(X, Y, shot['arc'])
pc = (lw * (0.62 + 0.38 * np.exp(-((Y - 200.0) / 170.0) ** 2)) * shot.get('cool_gain', 1.0))[..., None]
gg = np.asarray(grade.act_params(shot['grade']['act'])['gain'], np.float32); gg = gg / gg.max()
cool_pre = ((1.0 / gg) ** 0.85).astype(np.float32)[None, None]
fp = 0.5 + 0.5 * ph
g = plate['h'] * ph + plate['c'] * pc * cool_pre + plate['f'] * fp
t_ = np.clip((Zg - 830.0) / 140.0, 0, 1)[..., None] ** 1.3
hz = hex_lin('#2B2D3C').astype(np.float32)
g = g * (1 - 0.18 * t_) + hz[None, None] * (0.4 + 0.6 * ph) * 0.18 * t_
tab = np.clip((0.0 - Y) / 0.5, 0, 1)[..., None]
g = g * (1 - tab) + hex_lin('#2E1A0E')[None, None] * 0.7 * tab
Gd = shot['grade']; ap = dict(grade.act_params(Gd['act'])); ap['gamma'] *= Gd.get('gamma_mul', 1.0); ap['sat'] *= Gd.get('sat_mul', 1.0)
img = grade.grade(g, exposure=Gd['exposure'], act=ap, seed=1, grain=0.006)
if sc != 1.0:
    img = cv2.resize(img, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
cv2.imwrite(out, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
print('->', out)
