import sys, time, math; sys.path.insert(0,'.')
import os; os.environ.setdefault('NUMBA_NUM_THREADS','2')
import numpy as np, cv2
from emb.core import *
from emb.linen import make_linen
from emb import stitch as S
from emb.shade import relight, normals, ambient_occlusion
PX=16.0; H,W=int(36*PX),int(48*PX)
t=time.time()
m=make_linen(H,W,PX,seed=3); S.ensure(m)
print('linen',time.time()-t)
# region: blob split into two
yy,xx=np.mgrid[0:H,0:W]
cx,cy=24*PX,18*PX
ang=np.arctan2(yy-cy,xx-cx); rad=np.hypot((xx-cx)/1.0,(yy-cy)/0.8)
R=15*PX*(1+0.1*np.cos(3*ang+1)+0.06*np.cos(5*ang))
inside=rad<R
lab=np.zeros((H,W),np.int32)
div=cy+3.5*PX*np.sin(xx/PX/6.0)
lab[inside&(yy<div)]=1; lab[inside&(yy>=div)]=2
# shrink fills (stop short of outline)
for k in (1,2):
    mk=(lab==k).astype(np.uint8); mk=cv2.erode(mk,np.ones((7,7),np.uint8)); lab[(lab==k)&(mk==0)]=0
src=np.zeros((H,W,3),np.float32)
src[lab==1]=hex_lin('#B65E43'); src[lab==2]=hex_lin('#4F6F8A')
f1=S.const_field((H,W),78); f2=S.const_field((H,W),14)
t=time.time()
sh1=S.ShadeSet(lin2oklab(np.array([hex_lin('#B65E43')*0.92,hex_lin('#B65E43'),hex_lin('#B65E43')*1.08])))
sh2=S.ShadeSet(lin2oklab(np.array([hex_lin('#4F6F8A')*0.92,hex_lin('#4F6F8A'),hex_lin('#4F6F8A')*1.08])))
S.fill_region(m,lab,1,f1,src,sh1,PX,style='laid',pitch=0.9,seed=1,couch=dict(spacing=4.5,tie=4.0))
S.fill_region(m,lab,2,f2,src,sh2,PX,style='laid',pitch=0.9,seed=2,couch=dict(spacing=4.5,tie=4.0))
print('fills',time.time()-t)
t=time.time()
for c in S.mask_contours(inside,PX): S.stem_path(m,c,hex_lin('#22232F'),PX,seed=5)
dv=np.stack([np.arange(5*PX,43*PX,PX/2), cy+3.5*PX*np.sin(np.arange(5*PX,43*PX,PX/2)/PX/6.0)],1).astype(np.float32)
dv=dv[inside[np.clip(dv[:,1].astype(int),0,H-1),np.clip(dv[:,0].astype(int),0,W-1)]]
S.stem_path(m,dv,hex_lin('#22232F'),PX,seed=6)
print('stems',time.time()-t)
t=time.time()
N=normals(m['h'],PX); ao=ambient_occlusion(m['h'],PX)
out,vis=relight(m,135,22,N=N,ao=ao)
print('shade',time.time()-t)
t=time.time()
out,vis=relight(m,135,22,N=N,ao=ao)
print('shade2',time.time()-t)
save_rgb('work/test_engine.png',grade(out))
