import os, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src')
import numpy as np, cv2
import shot
from chron.color import lin2oklab, lin2srgb
A = shot.assets(); G = A['G']
m = G.read(470, 195, 500, 228, 0, keys=shot.READ_KEYS)
alb = m['alb']; mat = m['mat']; print(alb.shape, m['PX'], m['origin_mm'])
Y = alb @ np.array([0.2126,0.7152,0.0722], np.float32)
lab = lin2oklab(alb)
print('Y quantiles', np.quantile(Y,[.1,.5,.9,.99]))
mask = Y > 0.25
print('bright px', mask.sum(), 'mean alb', alb[mask].mean(0), 'oklab mean', lab[mask].mean(0))
print('mat in mask', np.unique(mat[mask], return_counts=True))
im = (np.clip(lin2srgb(alb),0,1)*255).astype(np.uint8)
cv2.imwrite('/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/work/v3/horse_alb.png', im[...,::-1])
