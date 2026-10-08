import os, sys, time
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import figure as F
import numpy as np, cv2
from bkit.canvas import Canvas
PX=10.0
out=sys.argv[1]
c=Canvas(420,190,PX=PX,seed=5,linen_seed=0,name='tfigs',verbose=False)
RED,REDD,BLUE,BLUED='#A3181A','#6E2428','#2F5F9E','#2D4460'
spec=[('legionary','strike',RED,REDD,0,50,95),('knight','strike',RED,REDD,0,140,95),('mercenary','strike',RED,REDD,0,215,95),
      ('spearman','strike',BLUE,BLUED,1,280,95),('horse_archer','strike',BLUE,BLUED,1,350,95),
      ('man_at_arms','strike',BLUE,BLUED,1,60,180),('archer','strike',BLUE,BLUED,1,120,180),('scout','strike',BLUE,BLUED,1,180,180),
      ('legionary','idle',RED,REDD,0,240,180),('engineer','strike',RED,REDD,0,300,180)]
t0=time.time()
for k,(u,p,t,d,fl,x,y) in enumerate(spec):
    card=F.load_card(u,p,t,flip=bool(fl),shield=t,deep_hex=d)
    cross=dict(kind='cross') if t==RED else dict(kind='chevron')
    F.embroider(c,card,x,y,ppm=8.0,group=None,seed=11+k,shield_cross=cross,name=u)
print('embroidered',time.time()-t0)
c.finish(out,sheet='tfigs',age_density=0.2)
