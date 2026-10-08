import sys,time; sys.path.insert(0,'.')
import numpy as np, cv2
from emb.core import *
from emb.motif_king import segment_king, arch_mask
from emb.segment import FAM
from emb.skel import skeleton_paths, merge_paths
src,ms,fam,h=segment_king()
g=cv2.cvtColor(src,cv2.COLOR_RGB2GRAY).astype(np.float32)/255
gs=cv2.GaussianBlur(g,(0,0),0.7)
k=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(11,11))
bh=cv2.morphologyEx(gs,cv2.MORPH_BLACKHAT,k)
ln=(bh>0.11)&(gs<0.45)
ln|=(fam==FAM['ink'])
ln&=arch_mask(g.shape)&(fam!=FAM['bg'])
ln=cv2.morphologyEx(ln.astype(np.uint8),cv2.MORPH_OPEN,np.ones((2,2),np.uint8))
sc=2
up=cv2.resize(ln.astype(np.float32),None,fx=sc,fy=sc,interpolation=cv2.INTER_LINEAR)
up=cv2.GaussianBlur(up,(0,0),1.0)>0.45
t=time.time()
paths,sk=skeleton_paths(up,4)
print('skel',time.time()-t,len(paths))
paths=merge_paths(paths,3.0)
print('merged',len(paths), sum(len(p) for p in paths))
viz=cv2.resize(src,None,fx=sc,fy=sc)//2+64
r=np.random.default_rng(0)
for p in paths:
    cv2.polylines(viz,[p.astype(np.int32)],False,tuple(int(c) for c in r.integers(0,255,3)),1)
save_rgb('work/lines_viz.png',viz[0:700,150:1000])
save_rgb('work/lines_mask.png',np.dstack([up*255]*3).astype(np.uint8)[0:700,150:1000])
