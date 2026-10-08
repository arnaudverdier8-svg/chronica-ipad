import os, sys, time
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import figure as F
import numpy as np, cv2
from bkit.canvas import Canvas
PX=10.0
out=sys.argv[1]
c=Canvas(330,125,PX=PX,seed=5,linen_seed=0,name='tfigs3',verbose=False)
RED,REDD,BLUE,BLUED='#A3181A','#6E2428','#2F5F9E','#2D4460'
spec=[('legionary','strike',RED,REDD,0,45,112),('mercenary','strike',RED,REDD,0,105,112),('spearman','strike',BLUE,BLUED,1,170,112),
      ('man_at_arms','strike',BLUE,BLUED,1,235,112),('knight','strike',RED,REDD,0,305,112)]
t0=time.time()
for k,(u,p,t,d,fl,x,y) in enumerate(spec):
    card=F.load_card(u,p,t,flip=bool(fl),shield=t,deep_hex=d)
    cross=dict(kind='cross') if t==RED else dict(kind='chevron')
    info=F.embroider(c,card,x,y,ppm=5.0*(1.0 if u!='knight' else 1.0),group=None,seed=11+k,shield_cross=cross,name=u,outline_mode='tonal',fill_pitch=0.74,gap_prob=0.0,skin_mode='bare',cord_outline=True)
    print(u,info['regions'],info['outlines'],info['features'])
print('embroidered',time.time()-t0)
c.finish(out,sheet='tfigs3',age_density=0.2)
