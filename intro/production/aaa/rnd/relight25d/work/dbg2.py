import sys; sys.path.insert(0,'.')
import numpy as np, cv2
from emb.core import *
from emb.scene import load, PX
from emb.render import frontal
sc=load(); k=sc['knight']
light=dict(az=122,el=20,key_i=3.0,fill_i=0.17)
crop=(slice(300,800),slice(500,1100))
a=frontal(k,(0,0,1500,1500),(1500,1500),light,fib=None)
b=frontal(k,(0,0,1500,1500),(1500,1500),light,fib=sc['fib1'])
cv2.imwrite('work/dbg_k.png', cv2.cvtColor(np.hstack([a[crop],b[crop]]),cv2.COLOR_RGB2BGR))
f=sc['fib1']; print('fib1', f['P'].shape, 'P x range', f['P'][...,0].min(), f['P'][...,0].max(), 'alpha', f['alpha'][:5], 'A', f['A'][:3])
