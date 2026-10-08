import sys, os
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/src')
import numpy as np, cv2, math
from common import *
import lightmodel as lm
from r25render import grade
hu = 2 * DIST * math.tan(math.radians(FOV_V / 2)); wu = hu * 16 / 9
Wo, Ho = 640, 360
xs = TARGET[0] + (np.arange(Wo) + .5) / Wo * wu - wu / 2
zs = TARGET[2] + (np.arange(Ho) + .5) / Ho * hu - hu / 2
GX, GZ = np.meshgrid(xs, zs)
DLv = (math.sin(math.radians(lm.EL)) + .25) / 1.25
def lit(f, alb):
    sc = lm.pool_scale(f); fa = lm.pool_floor(f)
    kl, kr = lm.pool('L', GX, GZ, sc, floor_add=fa), lm.pool('R', GX, GZ, sc, floor_add=fa)
    gL, gR = lm.gain('L', f), lm.gain('R', f)
    kf = lm.fill_map(kl, kr, gL, gR, f)
    key = lm.key_colour()
    tot = (kl * gL * lm.CANDLE['L']['key_i'] * DLv)[..., None] * key + (kr * gR * lm.CANDLE['R']['key_i'] * DLv)[..., None] * key \
        + (kf * lm.FILL_I * lm.fill_gain(f))[..., None] * lm.fill_colour(f)
    return tot * alb
alb_lin = np.array([0.55, 0.45, 0.30], np.float32)   # linen
alb_grn = np.array([0.10, 0.17, 0.06], np.float32)   # satin green
frames = [int(a) for a in sys.argv[2:]] if len(sys.argv) > 2 else [1668, 1700, 1720, 1760, 1782]
rows = []
for f in frames:
    for nm, al in (('linen', alb_lin), ('green', alb_grn)):
        im = grade(lit(f, al), grain=0.0)
        L = im.astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        gb = (int((0 - (TARGET[0] - wu / 2)) / wu * Wo), int((0 - (TARGET[2] - hu / 2)) / hu * Ho))
        pts = {'GB': (gb[0], gb[1]), 'W(-9,0)': (int((-9 - (TARGET[0] - wu / 2)) / wu * Wo), gb[1]), 'E(5,1)': (int((5 - (TARGET[0] - wu / 2)) / wu * Wo), int(gb[1] + .67/hu*Ho))}
        info = ' '.join(f'{k}:{L[p[1], p[0]]:.0f}' for k, p in pts.items())
        print(f, nm, 'p1 %.1f p50 %.1f p99 %.1f max %.0f corners %.0f %.0f %.0f %.0f' % (np.percentile(L, 1), np.median(L), np.percentile(L, 99), L.max(), L[0, 0], L[0, -1], L[-1, 0], L[-1, -1]), info)
        cv2.putText(im, f'f{f} {nm}', (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.circle(im, gb, 5, (0, 255, 0), 1)
        if nm == 'linen': rows.append(im)
cv2.imwrite(sys.argv[1], cv2.cvtColor(np.vstack([np.hstack(rows[i:i+3]) for i in range(0, len(rows), 3)]), cv2.COLOR_RGB2BGR))
