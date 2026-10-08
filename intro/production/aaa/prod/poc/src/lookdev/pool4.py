import sys, os, json
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/src')
import numpy as np, cv2, math
from common import *
import lightmodel as lm
from r25render import grade
over = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
for k, v in over.items():
    if k in ('L', 'R'): lm.CANDLE[k].update(v)
    else: setattr(lm, k, v)
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
alb_lin = np.array([0.55, 0.45, 0.30], np.float32)
def px(x, z): return (int((x - (TARGET[0] - wu / 2)) / wu * Wo), int((z - (TARGET[2] - hu / 2)) / hu * Ho))
pts = {'GB': (0, 0), 'W5': (-5, 0), 'W9': (-9, 0), 'N': (-2.2, -4.7), 'S': (-2.2, 5.6), 'E5': (5, 0), 'E7.5': (7.5, 0.5), 'NW': (-11.5, -4.5), 'SE': (7.2, 5.3)}
frames = [int(a) for a in sys.argv[3:]] if len(sys.argv) > 3 else [1690, 1720, 1760, 1782]
rows = []
for f in frames:
    im = grade(lit(f, alb_lin), grain=0.0)
    L = im.astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    print(f, 'p1 %.0f p50 %.0f max %.0f |' % (np.percentile(L, 1), np.median(L), L.max()), ' '.join(f'{k}:{L[min(max(px(*p)[1],0),Ho-1), min(max(px(*p)[0],0),Wo-1)]:.0f}' for k, p in pts.items()))
    cv2.putText(im, f'f{f}', (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    rows.append(im)
while len(rows) % 2: rows.append(rows[-1] * 0)
cv2.imwrite(sys.argv[1], cv2.cvtColor(np.vstack([np.hstack(rows[i:i+2]) for i in range(0, len(rows), 2)]), cv2.COLOR_RGB2BGR))
