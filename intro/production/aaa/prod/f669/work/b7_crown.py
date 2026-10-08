import os, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src')
import shot
import numpy as np, cv2
from chron.color import lin2srgb
W = os.path.dirname(os.path.abspath(__file__))
G = shot.MapSet(shot.MAPS + '/p1_oath_ground')
cr = shot.CrownSlip(shot.GroupAnim(G, ['crown']))
a = cr.alpha; print(a.shape, cr.PX, cr.origin, cr.c, cr.bb_mm, cr.anc.tolist())
alb = cr.m['alb']; h = cr.m['h']
img = (np.clip(lin2srgb(np.clip(alb,0,1)),0,1)*255).astype(np.uint8)
raw = (cr.slip.alpha*255).astype(np.uint8)
fin = (np.clip(a,0,1)*255).astype(np.uint8)
holes = np.clip(a - cr.slip.alpha, 0, 1)
vis = np.hstack([img[..., ::-1], cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR), cv2.cvtColor(fin, cv2.COLOR_GRAY2BGR), cv2.cvtColor((holes*255).astype(np.uint8), cv2.COLOR_GRAY2BGR)])
cv2.imwrite(W + '/b7_crown.png', cv2.resize(vis, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA))
