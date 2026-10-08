import os, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src')
import numpy as np, cv2
import shot
from threads3d import ThreadSet
from chron.maps import MapSet
from chron.config import MAPS
from chron.anim.groupanim import GroupAnim
from crown import CrownSlip
G = MapSet(MAPS + '/p1_oath_ground')
cr = CrownSlip(GroupAnim(G, ['crown']))
f = 669
view = shot.view_of(f); light = shot.light_of(f)
L_ = cr.layers(view, light, 15.0, shot.crown_turn(f), shot.pool_at(f))
img = np.ones((1440, 2560, 3), np.float32) * 0.5
ts = ThreadSet()
for i, P in enumerate(cr.tether_curves(L_, 15.0, seed=3)):
    print(i, P[0], P[-1])
    ts.add(P, 0.30, shot.GOLD, kind=1, pitch_mm=0.42, seed=i / 4.0, shadow=1.0)
ctx = dict(x0=L_['x0'], y0=L_['y0'], s=L_['s'])
ts.render(img, ctx, light['candle']['pos_mm'], shot.thread_light_fn(f), shot.NIGHT * 0.1, shadow_strength=0.84, fuzz=False)
cv2.imwrite('dbg_teth.png', (np.clip(img[300:1000, 950:1550], 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)[..., ::-1])
