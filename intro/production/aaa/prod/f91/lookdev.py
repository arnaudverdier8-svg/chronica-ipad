"""light/grade look-dev on a cached raw linear frame (no pool, no blur): lookdev.py <variant json> """
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('F91_SHOT', 'shot_f91_t1.json')
sys.path.insert(0, HERE)
import render_f91 as R
import numpy as np, cv2
from chron.maps import MapSet
sheet = sys.argv[1]; x0 = float(sys.argv[2]); y0 = float(sys.argv[3]); tag = sys.argv[4]
rawp = os.path.join(HERE, 'work', f'raw_{tag}.npy')
s = 5.0
if not os.path.exists(rawp) or os.environ.get('RERAW'):
    ms = MapSet(os.path.join(R.MAPS, sheet))
    fr = R.render_frame(ms, dict(x0_mm=x0, y0_mm=y0, px_per_mm=s), (2560, 1440))
    np.save(rawp, fr['lin'].astype(np.float32))
lin0 = np.load(rawp)
variants = json.load(open(sys.argv[5]))
for name, v in variants.items():
    R.SHOT['pool_all'] = v.get('pool_all', R.SHOT['pool_all'])
    R.SHOT['split_tone'] = v.get('split_tone', R.SHOT.get('split_tone'))
    R.SHOT['grade'] = dict(R.SHOT['grade'], **v.get('grade', {}))
    lin = lin0
    pa = R.pool_all(lin.shape[:2], s, x0, y0)
    lin = lin * pa[..., None]
    lin = R.split_tone(lin, R.SHOT.get('split_tone'))
    G = R.SHOT['grade']
    from chron import grade
    img = grade.grade(lin, exposure=G['exposure'], act=G['act'], seed=91, grain=G.get('grain', 0.012))
    out = os.path.join(HERE, 'look2', f'ld_{tag}_{name}.jpg')
    cv2.imwrite(out, cv2.cvtColor(cv2.resize(img, (1600, 900), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(out)
