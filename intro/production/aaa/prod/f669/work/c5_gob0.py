import os, sys, json
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/lib')
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np, cv2
from chron.config import MAPS
from chron.maps import MapSet
from chron.color import lin2srgb
P = MapSet(MAPS + '/p1_oath')
x0m, y0m, x1m, y1m = 50, 232, 110, 275
a = P.read_px(int(x0m*10), int(y0m*10), int(x1m*10), int(y1m*10), 0, keys=['alb'])['alb']
im = (np.clip(lin2srgb(np.clip(a, 0, 1)), 0, 1) * 255).astype(np.uint8)[..., ::-1].copy()
for xm in range(x0m, x1m, 5):
    X = int((xm - x0m) * 10); cv2.line(im, (X, 0), (X, im.shape[0]), (255, 255, 0), 1); cv2.putText(im, str(xm), (X + 2, 12), 0, 0.4, (255, 255, 0), 1)
for ym in range(y0m, y1m, 5):
    Y = int((ym - y0m) * 10); cv2.line(im, (0, Y), (im.shape[1], Y), (255, 255, 0), 1); cv2.putText(im, str(ym), (2, Y - 2), 0, 0.4, (255, 255, 0), 1)
cv2.imwrite('c5_gob0.png', cv2.resize(im, None, fx=1.3, fy=1.3))
