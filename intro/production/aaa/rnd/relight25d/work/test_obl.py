import sys, time; sys.path.insert(0,'.')
import numpy as np, cv2
from emb.core import *
from emb.scene import load, PX
from emb.oblique import Camera
from emb.obl_render import render_oblique, lift_map
from emb.render import undulation
sc=load()
W,H=int(sys.argv[1]),int(sys.argv[2])
tilt=float(sys.argv[3]); yaw=float(sys.argv[4]); dist=float(sys.argv[5]); lift=float(sys.argv[6]); out=sys.argv[7]
tx=float(sys.argv[8]); ty=float(sys.argv[9]); pad=float(sys.argv[10]); fov=float(sys.argv[11]) if len(sys.argv)>11 else 28
cam=Camera((tx,ty,0),dist,tilt,yaw,fov,W,H)
l1=lift_map(sc['k_alpha'],PX,lift,curl=lift*0.10)
U=undulation(sc['canvas']['h'].shape,PX,0.0,amp=0.9)
light=dict(az=128,el=22,key_i=2.7,fill_i=0.2,rim_i=0.25,rim_az=25,rim_el=9)
tm={}
img,zf,lay=render_oblique(sc,cam,light,lift1=l1,dof_px=W/2560*14,timing=tm,pad=pad,undul=U)
print({k:round(v,2) for k,v in tm.items()}, 'miss frac', (lay<0).mean())
save_rgb(out,img)
