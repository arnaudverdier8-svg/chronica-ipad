import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2, math
from common import *
import lightmodel as lm
hu = 2 * DIST * math.tan(math.radians(FOV_V / 2)); wu = hu * 16 / 9
Wo, Ho = 640, 360
xs = TARGET[0] + (np.arange(Wo) + .5) / Wo * wu - wu / 2
zs = TARGET[2] + (np.arange(Ho) + .5) / Ho * hu - hu / 2
GX, GZ = np.meshgrid(xs, zs)
kl, kr = lm.pool('L', GX, GZ), lm.pool('R', GX, GZ); kf = lm.fill_map(kl, kr)
cL = np.array(lm.key_colour()) * lm.CANDLE['L']['key_i'] * 0.49; cR = np.array(lm.key_colour()) * lm.CANDLE['R']['key_i'] * 0.49
fill = kf[..., None] * np.array(lm.FILL_COL) * lm.FILL_I
tot = kl[..., None] * cL + kr[..., None] * cR + fill
def tm(x, e=0.42):
    x = x * e
    return np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)
def enc(x): return np.clip(np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.maximum(x, 0), 1 / 2.4) - 0.055), 0, 1)
imgs = []
for name, v in [('L only', kl[..., None] * cL + fill * 0.5), ('R only', kr[..., None] * cR + fill * 0.5), ('both', tot)]:
    im = (enc(tm(v)) * 255).astype(np.uint8)
    cv2.putText(im, name, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    gx, gz = (0 - (TARGET[0] - wu / 2)) / wu * Wo, (0 - (TARGET[2] - hu / 2)) / hu * Ho
    cv2.circle(im, (int(gx), int(gz)), 5, (0, 255, 0), 1)
    imgs.append(im)
out = np.concatenate(imgs, 1)
cv2.imwrite(sys.argv[1] if len(sys.argv) > 1 else '/tmp/pool.png', cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
print('lum range both', tot.mean(-1).min(), tot.mean(-1).max())
