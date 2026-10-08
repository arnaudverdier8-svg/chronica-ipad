import os, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/lib')
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np, cv2
from chron.config import MAPS
from chron.maps import MapSet
from chron.color import lin2srgb
W = os.path.dirname(os.path.abspath(__file__))
P = MapSet(MAPS + '/p1_oath'); G = MapSet(MAPS + '/p1_oath_ground')
def crop(x0mm, y0mm, x1mm, y1mm, name, fx=0.5):
    x0, y0, x1, y1 = int(x0mm*10), int(y0mm*10), int(x1mm*10), int(y1mm*10)
    a = P.read_px(x0, y0, x1, y1, 0, keys=['alb'])['alb']
    g = G.read_px(x0, y0, x1, y1, 0, keys=['alb'])['alb']
    f = lambda x: (np.clip(lin2srgb(np.clip(x, 0, 1)), 0, 1) * 255).astype(np.uint8)
    out = np.hstack([f(a), f(g)])
    cv2.imwrite(f'{W}/{name}', cv2.resize(out[..., ::-1], None, fx=fx, fy=fx, interpolation=cv2.INTER_AREA))
crop(440, 200, 575, 295, 'b4_right.png', 0.45)
crop(360, 225, 480, 285, 'b4_gob23.png', 0.5)
crop(20, 205, 160, 310, 'b4_left.png', 0.4)
