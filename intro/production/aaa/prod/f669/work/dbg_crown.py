import os, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src')
import numpy as np, cv2
import shot
from chron.maps import MapSet
from chron.config import MAPS
from chron.anim.groupanim import GroupAnim
from crown import CrownSlip
G = MapSet(MAPS + '/p1_oath_ground')
cr = CrownSlip(GroupAnim(G, ['crown']))
print('centre', cr.c, 'bb', cr.bb_mm, 'alpha', cr.alpha.shape, cr.alpha.max())
f = 669
view = shot.view_of(f); light = shot.light_of(f)
L_ = cr.layers(view, light, 15.0, shot.crown_turn(f), shot.pool_at(f))
print('shadow max', L_['shadow'].max(), 'alpha max', L_['alpha'].max(), 'top_mm', L_['top_mm'])
im = np.zeros((1440, 2560, 3), np.uint8)
im[..., 2] = (L_['shadow'] * 255).astype(np.uint8)
im[..., 1] = (L_['alpha'] * 255).astype(np.uint8)
for P in cr.tether_curves(L_, 15.0):
    q = np.stack([(P[:, 0] - L_['x0']) * L_['s'], (P[:, 1] - L_['y0']) * L_['s']], 1).astype(np.int32)
    cv2.polylines(im, [q], False, (255, 255, 255), 1)
cv2.imwrite('dbg_crown.png', im[200:1100, 900:1700])
print('turn', shot.crown_turn(f))
