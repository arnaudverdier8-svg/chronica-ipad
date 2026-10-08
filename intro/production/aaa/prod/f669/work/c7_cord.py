import os, sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/lib')
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src')
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np, cv2
import shot
from chron.record import replay
from chron.color import lin2srgb
P = shot.MapSet(shot.MAPS + '/p1_oath')
G = shot.MapSet(shot.MAPS + '/p1_oath_ground'); R = G.stitches()
gf = shot.GroundFix(G)
names = json.load(open(G.path + '/groups.json'))['groups']
g0 = np.nonzero(R['group'] == names.index('goblet_0'))[0]
x0m, y0m, x1m, y1m = 56, 262, 105, 312
x0, y0, x1, y1 = [int(v * 10) for v in (x0m, y0m, x1m, y1m)]
a = P.read_px(x0, y0, x1, y1, 0, keys=['alb'])['alb']
im = (np.clip(lin2srgb(np.clip(a, 0, 1)), 0, 1) * 255).astype(np.uint8)[..., ::-1].copy()
mm = gf.mm
rest = np.zeros(len(R['typ']), bool); rest[gf.restore] = True
for k in g0:
    p = R['P'][R['off'][k]:R['off'][k+1]] - np.array([x0, y0])
    col = (0, 200, 0) if rest[k] else (0, 0, 255)
    cv2.polylines(im, [np.round(p).astype(np.int32)], False, col, 1)
for xm in range(x0m, x1m, 5):
    X = int((xm - x0m) * 10); cv2.putText(im, str(xm), (X + 2, 12), 0, 0.4, (255, 255, 0), 1); cv2.line(im, (X, 0), (X, 8), (255, 255, 0), 1)
for ym in range(y0m, y1m, 5):
    Y = int((ym - y0m) * 10); cv2.putText(im, str(ym), (2, Y - 2), 0, 0.4, (255, 255, 0), 1); cv2.line(im, (0, Y), (8, Y), (255, 255, 0), 1)
cv2.imwrite('c7_cord.png', cv2.resize(im, None, fx=1.6, fy=1.6))
