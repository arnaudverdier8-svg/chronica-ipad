import sys; sys.path.insert(0,'.')
import numpy as np
from emb.core import *
from emb.linen import make_linen
from emb import stitch as S
from emb.titulus import titulus
from emb.render import prepare, frontal
from emb.fibres import make_fibres
PX=10.0
m=make_linen(160,900,PX,seed=2); S.ensure(m)
end=titulus(m,"HIC SEDET REX",3,12,6.0,seed=21); print('end mm',end)
prepare(m); fib=make_fibres(m,1.0,seed=1)
img=frontal(m,(0,0,900,160),(900,160),dict(az=122,el=20,key_i=3.0,fill_i=0.17),fib=fib)
save_rgb('work/tit_test.png',img)
