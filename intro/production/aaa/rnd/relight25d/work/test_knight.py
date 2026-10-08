import sys, time; sys.path.insert(0,'.')
import numpy as np, cv2
from emb.core import *
from emb.linen import make_linen
from emb import stitch as S
from emb.motif_knight import build_knight
from emb.render import prepare, frontal, spot
from emb.fibres import make_fibres
PX=10.0
H,W=1450,1400
base=make_linen(H,W,PX,seed=5)
t=time.time()
K=build_knight(base,PX,135.0,'blue',seed=2)
print('build',time.time()-t)
m=K['maps']
a=K['alpha'][...,None]
for k in ('h','alb','T','mat','cov'):
    pass
prepare(m)
fib=make_fibres(m,density=0.9,seed=3)
km=spot((H,W),PX,60,50,110,floor=0.6)
light=dict(az=125,el=20,key_i=2.6,fill_i=0.22,rim_i=0.25,rim_az=20,rim_el=10)
tm={}
img=frontal(m,(0,0,W,H),(W,H),light,fib=fib,kmap=km,timing=tm)
print(tm)
save_rgb('work/knight_test.png',img)
cv2.imwrite('work/knight_zoom.png', cv2.cvtColor(img[300:800,350:900],cv2.COLOR_RGB2BGR))
np.savez('cache/knight_test.npz',alpha=K['alpha'],sil=K['sil'],relief=K['relief'],**{k:v for k,v in m.items() if isinstance(v,np.ndarray)})
