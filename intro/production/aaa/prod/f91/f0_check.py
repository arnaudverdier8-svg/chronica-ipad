"""render the F0 landing frame (f114-125: 3.3 px/mm, sheet x 12-788, y 2-438) from the kit sheet, to prove the sheet covers it."""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('F91_SHOT', 'shot_f91.json')
sys.path.insert(0, HERE)
import render_f91 as R
import numpy as np, cv2
from chron.maps import MapSet
from chron import grade
from chron.qa.void import check_void
sheet = sys.argv[1] if len(sys.argv) > 1 else 'k1_realm'
tag = sys.argv[2] if len(sys.argv) > 2 else 'f0'
s = 3.3
ms = MapSet(os.path.join(R.MAPS, sheet))
view = dict(x0_mm=12.0, y0_mm=2.0, px_per_mm=s)
t0 = time.time()
fr = R.render_frame(ms, view, (2560, 1440), fib_seed=114)
check_void(fr['lin'], fr['alpha'], name='f0')
lin = fr['lin']
P = dict(R.SHOT['pool_all']); P['accents'] = []
R.SHOT['pool_all'] = P
pa = R.pool_all(lin.shape[:2], s, 12.0, 2.0)
lin = R.split_tone(lin * pa[..., None], R.SHOT.get('split_tone'))
G = R.SHOT['grade']
img = grade.grade(lin, exposure=G['exposure'], act='I', seed=114, out_u16=False)
out = os.path.join(HERE, 'look2', f'f0_{tag}.jpg')
cv2.imwrite(out, cv2.cvtColor(cv2.resize(img, (1600, 900), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
print(out, 'level', fr['level'], 'void-free', round(time.time() - t0, 1), 's')
