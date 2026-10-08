import os, sys, time
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import figure as F
import numpy as np, cv2
from bkit.canvas import Canvas
from chron.maps import MapSet
from chron import frontal, shade, grade
unit, pose, team, flip = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
out = sys.argv[5]
PX=10.0
c=Canvas(110,110,PX=PX,seed=5,linen_seed=0,name='tfig',verbose=True)
t0=time.time()
card=F.load_card(unit,pose,team,flip=bool(flip),shield=team,deep_hex=sys.argv[6] if len(sys.argv)>6 else None)
info=F.embroider(c,card,55,100,ppm=8.0,group='slip0',seed=11,shield_cross=dict(kind='cross') if 'legion' in unit else dict(kind='chevron'),verbose=True)
print('embroidered',time.time()-t0, info['bbox_mm'])
paths=c.finish(out,sheet='tfig',ground_without=['slip0'],age_density=0.2)
print(paths)
