"""close-up relight of a region of the kit sheet: closeup.py name x0 y0 w_mm h_mm px_per_mm [sheet]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_f91 as R
import numpy as np, cv2
from chron.maps import MapSet
from chron import grade
name, x0, y0, w, h, s = sys.argv[1], *map(float, sys.argv[2:7])
sheet = sys.argv[7] if len(sys.argv) > 7 else 'k1_realm'
ms = MapSet(os.path.join(R.MAPS, sheet))
wh = (int(w * s), int(h * s))
fr = R.render_frame(ms, dict(x0_mm=x0, y0_mm=y0, px_per_mm=s), wh)
lin = fr['lin']
pa = R.pool_all(lin.shape[:2], s, x0, y0)
if pa is not None: lin = lin * pa[..., None]
img = grade.grade(lin, exposure=1.0, act='I', seed=91)
cv2.imwrite(os.path.join(HERE, '_c', name + '.png'), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
