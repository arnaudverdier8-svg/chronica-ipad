import sys; sys.path.insert(0,'.')
import numpy as np, cv2
from emb.core import *
from emb.segment import *
src = load_rgba('work/m1_src.png')[..., :3]
ms = cv2.pyrMeanShiftFiltering(cv2.cvtColor(src,cv2.COLOR_RGB2BGR), 5, 16, maxLevel=1)
ms = cv2.cvtColor(ms, cv2.COLOR_BGR2RGB)
ms = cv2.bilateralFilter(ms, 7, 30, 5)
lab,L,C,h = oklab_lch(ms)
H,W=L.shape
yy,xx=np.mgrid[0:H,0:W]
fam=np.full((H,W),FAM['brown'],np.int32)
hue=lambda a,b: ((h-a)%360)<=((b-a)%360)
fam[(C<0.045)&(L>0.52)]=FAM['light']
fam[(C<0.04)&(L>=0.27)&(L<=0.52)]=FAM['midgrey']
fam[hue(180,275)&(C>=0.012)&(L<0.62)&(L>0.25)]=FAM['blue']
fam[hue(295,25)&(C>=0.035)&(L<0.66)]=FAM['purple']
fam[hue(48,105)&(C>=0.075)&(L>=0.53)]=FAM['gold']
fam[(L<0.27)]=FAM['ink']
fam[(C>0.12)&~hue(40,105)&(L>0.3)]=FAM['jewel']
# skin only inside face ellipse
face=((xx-285)/68.)**2+((yy-262)/55.)**2<1
skin=face&hue(25,80)&(C>0.035)&(L>0.5)
fam[skin]=FAM['skin']
# bg linen: flood from border over linen-like low-texture pixels
lum=L.astype(np.float32); tex=cv2.GaussianBlur(np.abs(lum-cv2.GaussianBlur(lum,(0,0),2)),(0,0),3)
lin_like=(L>0.74)&(C<0.07)&hue(50,100)&(tex<0.03)
nc,cc=cv2.connectedComponents(lin_like.astype(np.uint8))
border=set(np.unique(np.concatenate([cc[0],cc[-1],cc[:,0],cc[:,-1]])))-{0}
bg=np.isin(cc,list(border))
fam[bg]=FAM['bg']
fam=majority(fam,5,2,n=21)
cols={0:(220,205,170),1:(20,20,30),2:(110,50,110),3:(230,170,40),4:(120,80,40),5:(230,160,130),6:(240,240,240),7:(60,90,140),8:(200,0,60),9:(130,130,130)}
viz=np.zeros((H,W,3),np.uint8)
for k,c in cols.items(): viz[fam==k]=c
save_rgb('work/fam_viz.png',np.hstack([ms,viz]))
np.save('work/fam.npy',fam)
print({k:(fam==v).mean().round(3) for k,v in FAM.items() if (fam==v).any()})
print('tex percentiles', np.percentile(tex,[10,50,90]))
