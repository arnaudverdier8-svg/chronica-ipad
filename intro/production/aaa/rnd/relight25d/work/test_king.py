import sys, time; sys.path.insert(0,'.')
import numpy as np, cv2
from emb.core import *
from emb.linen import make_linen
from emb import stitch as S
from emb.motif_king import build_king
from emb.render import prepare, frontal, spot
from emb.fibres import make_fibres
PX=10.0
t=time.time()
H,W=1260,1220
m=make_linen(H,W,PX,seed=5); S.ensure(m)
info=build_king(m,10,10)
print('build',time.time()-t)
prepare(m)
t=time.time(); fib=make_fibres(m,density=0.7,seed=3); print('fibres',time.time()-t, fib['P'].shape)
km=spot((H,W),PX,50,40,110,floor=0.6)
light=dict(az=140,el=20,key_i=2.6,fill_i=0.22,rim_i=0.25,rim_az=20,rim_el=10)
tm={}
img=frontal(m,(0,0,W,H),(W,H),light,fib=fib,kmap=km,timing=tm)
print(tm)
save_rgb('work/king_test.png',img)
cv2.imwrite('work/king_zoom1.png', cv2.cvtColor(img[180:700,330:900],cv2.COLOR_RGB2BGR))
cv2.imwrite('work/king_zoom2.png', cv2.cvtColor(img[760:1210,20:620],cv2.COLOR_RGB2BGR))
np.savez('cache/king_test_maps.npz',**{k:v for k,v in m.items() if isinstance(v,np.ndarray)})
