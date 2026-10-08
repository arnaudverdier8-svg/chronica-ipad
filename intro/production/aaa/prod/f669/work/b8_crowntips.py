import os, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/lib')
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np, cv2
from chron.config import MAPS
from chron.maps import MapSet
from chron.color import lin2srgb
W = os.path.dirname(os.path.abspath(__file__))
P = MapSet(MAPS + '/p1_oath'); G = MapSet(MAPS + '/p1_oath_ground')
x0, y0, x1, y1 = 2550, 880, 3350, 1480
a = P.read_px(x0, y0, x1, y1, 0, keys=['alb'])['alb']
g = G.read_px(x0, y0, x1, y1, 0, keys=['alb','sid'])
f = lambda x: (np.clip(lin2srgb(np.clip(x, 0, 1)), 0, 1) * 255).astype(np.uint8)
out = np.hstack([f(a), f(g['alb'])])
cv2.imwrite(W + '/b8_crowntips.png', out[..., ::-1])
