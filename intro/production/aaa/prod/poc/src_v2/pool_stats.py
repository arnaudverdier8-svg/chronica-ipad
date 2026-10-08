import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, math
from common import *
import lightmodel as lm
def stats(show=True):
    hu = 2 * DIST * math.tan(math.radians(FOV_V / 2)); wu = hu * 16 / 9
    ny, nx = 9, 16
    xs = TARGET[0] + (np.arange(nx) + .5) / nx * wu - wu / 2
    zs = TARGET[2] + (np.arange(ny) + .5) / ny * hu - hu / 2
    GX, GZ = np.meshgrid(xs, zs)
    kl, kr = lm.pool('L', GX, GZ), lm.pool('R', GX, GZ); kf = lm.fill_map(kl, kr)
    c = lm.key_colour()
    DLv = (math.sin(math.radians(lm.EL)) + .25) / 1.25
    lum = (kl * lm.CANDLE['L']['key_i'] + kr * lm.CANDLE['R']['key_i']) * DLv * float(c.mean()) + kf * lm.FILL_I
    pk = lum.max()
    rel = lum / pk
    if show:
        np.set_printoptions(linewidth=200, precision=2, suppress=True)
        print('relative luminance grid (rows north->south, cols west->east); peak at', np.unravel_index(lum.argmax(), lum.shape))
        print(rel)
        print('corners', rel[0, 0], rel[0, -1], rel[-1, 0], rel[-1, -1], 'edge mids', rel[0, nx // 2], rel[-1, nx // 2], rel[ny // 2, 0], rel[ny // 2, -1])
    return rel
if __name__ == '__main__': stats()
