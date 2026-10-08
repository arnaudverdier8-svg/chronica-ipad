import sys; sys.path.insert(0,'.')
import numpy as np, cv2
from emb.core import *
from emb.scene import load, PX
from emb.oblique import Camera
from emb.obl_render import render_oblique
from emb.render import undulation
sc=load(); Hc,Wc=sc['canvas']['h'].shape
W,H=960,540
cam=Camera((238,101,0),300,12,72,28,W,H)
U=undulation((Hc,Wc),PX,0,amp=1.0)
img,zf,lay=render_oblique(sc,cam,dict(az=142,el=21,key_i=2.8,fill_i=0.18),lift1=np.zeros_like(sc['k_alpha']),undul=U,fibres=False)
g=cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)
ys,xs=np.nonzero(g[:, 600:]<40); print('dark px', len(ys), (ys.mean(), xs.mean()+600) if len(ys) else None)
print('lay values near', np.unique(lay[200:250,680:720],return_counts=True))
pos,f,r,u,tx,ty=cam.args()
# find canvas position of that pixel
from emb.oblique import raymarch
y0,x0=int(ys.mean()),int(xs.mean()+600)
print('pixel',x0,y0,'lay',lay[y0,x0],'z',zf[y0,x0])
h=sc['canvas']['h']; print('canvas h range',h.min(),h.max(), 'argmin', np.unravel_index(h.argmin(),h.shape))
sub=g[310:370,660:740]; yy,xx=np.unravel_index(sub.argmin(),sub.shape); py,px=310+yy,660+xx
print('disc pixel',px,py,'gray',g[py,px],'lay',lay[py,px],'zf',zf[py,px])
# canvas coords of that ray at plane z=0
sx=(2*(px+0.5)/W-1)*tx; sy=(1-2*(py+0.5)/H)*ty
d=f+sx*r+sy*u; d/=np.linalg.norm(d); t=-pos[2]/d[2]; P=pos+t*d; print('canvas mm',P)
c=sc['canvas']; xi,yi=int(P[0]*PX),int(P[1]*PX)
print('h',c['h'][yi-3:yi+4,xi-3:xi+4].round(2)); print('mat',c['mat'][yi,xi],'alb',c['alb'][yi,xi],'ao',c['ao'][yi,xi])
ka=sc['k_alpha']; kx,ky=sc['k_off']; print('k_alpha there', ka[yi-ky,xi-kx] if 0<=yi-ky<ka.shape[0] and 0<=xi-kx<ka.shape[1] else 'out')
