import os, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src')
import numpy as np, cv2
import shot
from chron.color import lin2oklab, lin2srgb
A = shot.assets(); G = A['G']
x0,y0=472.0,198.0
m = G.read(x0, y0, x0+26, y0+30, 0, keys=shot.READ_KEYS)
alb = m['alb']; mat = m['mat']
lab = lin2oklab(alb); L=lab[...,0]; C=np.hypot(lab[...,1],lab[...,2]); hue=np.degrees(np.arctan2(lab[...,2],lab[...,1]))%360
np.set_printoptions(linewidth=250)
# coarse printout every 10 px
for name,arr in [('L',L),('C',C),('hue',hue)]:
    print(name)
    print(np.round(arr[::10,::10],2))
mk = (L>0.72)&(C<0.12)
print('mask px', mk.sum())
out=(np.clip(lin2srgb(alb),0,1)*255).astype(np.uint8).copy()
out[mk]=(255,0,255)
cv2.imwrite('/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/work/v3/horse_mask.png', cv2.resize(out[...,::-1],None,fx=3,fy=3,interpolation=cv2.INTER_NEAREST))
