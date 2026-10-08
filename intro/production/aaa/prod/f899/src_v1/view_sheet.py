import os, sys, time
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import bkit
import numpy as np, cv2
from chron.maps import MapSet
from chron import frontal, shade, grade
path, x0, y0, w, h, ppm, out = sys.argv[1], *map(float, sys.argv[2:7]), sys.argv[7]
az = float(sys.argv[8]) if len(sys.argv)>8 else 135; el = float(sys.argv[9]) if len(sys.argv)>9 else 24
ms=MapSet(path)
light=shade.rig(az=az,el=el,K=3000,key_i=2.6,fill_ratio=3.0,tint=0.3,rim_i=0.2)
W,H=int(w*ppm),int(h*ppm)
t0=time.time()
fr=frontal.render(ms,dict(x0_mm=x0,y0_mm=y0,px_per_mm=ppm),light,out_wh=(W,H),fib_seed=3)
img=grade.grade(fr['lin'],exposure=0.95,act='I',seed=1)
cv2.imwrite(out,cv2.cvtColor(img,cv2.COLOR_RGB2BGR))
print('rendered',time.time()-t0)
