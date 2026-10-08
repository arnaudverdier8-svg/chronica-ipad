import sys; sys.path.insert(0,'.')
import numpy as np, cv2, time
from emb.core import *
src = load_rgba('work/m1_src.png')[..., :3]
t=time.time()
ms = cv2.pyrMeanShiftFiltering(cv2.cvtColor(src,cv2.COLOR_RGB2BGR), 6, 18, maxLevel=1)
ms = cv2.cvtColor(ms, cv2.COLOR_BGR2RGB)
print('meanshift', time.time()-t)
lab = lin2oklab(srgb2lin(ms.astype(np.float32)/255))
Z = (lab*np.array([1,2,2],np.float32)).reshape(-1,3).astype(np.float32)
K=14
crit=(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-4)
_,lab_,cent = cv2.kmeans(Z,K,None,crit,3,cv2.KMEANS_PP_CENTERS)
lbl = lab_.reshape(src.shape[:2])
cent = cent/np.array([1,2,2],np.float32)
cols = (lin2srgb(oklab2lin(cent))*255).astype(np.uint8)
for i,c in enumerate(cent):
    C=np.hypot(c[1],c[2]); h=np.degrees(np.arctan2(c[2],c[1]))%360
    print(i, 'L%.2f C%.3f h%3.0f'%(c[0],C,h), (lbl==i).mean().round(3), cols[i])
viz = cols[lbl]
# label index map in false colour
fc = (np.random.default_rng(1).integers(40,255,(K,3))).astype(np.uint8)[lbl]
for i in range(K):
    ys,xs=np.nonzero(lbl==i); 
    if len(ys)==0: continue
    j=len(ys)//2
    cv2.putText(fc,str(i),(int(np.median(xs)),int(np.median(ys))),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,0,0),2)
save_rgb('work/seg_viz.png', np.hstack([ms, viz, fc]))
np.save('work/seg_lbl.npy', lbl)
