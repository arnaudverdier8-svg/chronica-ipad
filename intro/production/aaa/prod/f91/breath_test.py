"""S02 'breath' proof: relight the same sheet at three keys (az 120 / el 22, az 150 / el 22, az 150 / el 16) at F0 density (3.3 px/mm) over the
f91 window region and report how far the cast shadows of hills / towns / the capital move.  Writes look2/breath_*.png and breath_stats.json."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('F91_SHOT', 'shot_f91.json')
sys.path.insert(0, HERE)
import render_f91 as R
import numpy as np, cv2
from chron.maps import MapSet
from chron import grade, frontal
sheet = sys.argv[1] if len(sys.argv) > 1 else 'k1_realm'
s = 3.3
ms = MapSet(os.path.join(R.MAPS, sheet))
x0, y0 = 168.0 + 20, 70.0          # capital / towns region, 3.3 px/mm
W, H = 1800, 800
view = dict(x0_mm=x0, y0_mm=y0, px_per_mm=s)
out = {}
imgs = {}
for name, (az, el) in dict(a=(120, 22), b=(150, 22), c=(150, 16)).items():
    L = dict(R.SHOT['light'], az=az, el=el)
    fr = R.render_frame(ms, view, (W, H), light=R.rig(L), return_maps=True) if False else frontal.render(
        ms, view, R.rig(L), out_wh=(W, H), kmap=R.SHOT['kmap'], fib_seed=7, edit=R.fold_field, age=R.age_map, return_maps=True)
    lin = fr['lin']
    P = dict(R.SHOT['pool_all']); P['accents'] = []
    R.SHOT['pool_all'] = P
    pa = R.pool_all(lin.shape[:2], s, x0, y0)
    lin = R.split_tone(lin * pa[..., None], R.SHOT.get('split_tone'))
    img = grade.grade(lin, exposure=R.SHOT['grade']['exposure'], act='I', seed=1, grain=0.0)
    imgs[name] = img
    vis = fr['vis']                                    # key visibility in map px
    m = fr['maps']
    out[name] = dict(az=az, el=el, shadow_frac=float((vis < 0.5).mean()), max_h_mm=float(m['h'].max()), p99_h_mm=float(np.percentile(m['h'], 99)))
    cv2.imwrite(os.path.join(HERE, 'look2', f'breath_{name}.png'), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    np.save(os.path.join(HERE, 'work', f'vis_{name}.npy'), vis.astype(np.float16))
    out[name]['PX'] = float(m['PX'])
def diff(a, b):
    d = np.abs(imgs[a].astype(np.float32) - imgs[b].astype(np.float32)).mean(2)
    return d
for pair in ('ab', 'bc', 'ac'):
    d = diff(pair[0], pair[1])
    out['diff_' + pair] = dict(mean=float(d.mean()), frac_gt_8=float((d > 8).mean()), p99=float(np.percentile(d, 99)))
    cv2.imwrite(os.path.join(HERE, 'look2', f'breath_diff_{pair}_x4.png'), np.clip(d * 4, 0, 255).astype(np.uint8))
# analytic shadow length of the tallest feature: length = h / tan(el)
for k in ('a', 'b', 'c'):
    el = np.radians(out[k]['el'])
    out[k]['shadow_len_px_at_p99_h'] = float(out[k]['p99_h_mm'] / np.tan(el) * s)
    out[k]['shadow_len_px_at_max_h'] = float(out[k]['max_h_mm'] / np.tan(el) * s)
# displacement of the shadow tip of the tallest feature between lights (vector difference)
def tip(k):
    az = np.radians(out[k]['az']); L = out[k]['shadow_len_px_at_p99_h']
    return np.array([-np.cos(az), np.sin(az)]) * (-L)
for pair in ('ab', 'bc', 'ac'):
    out['tip_shift_px_' + pair] = float(np.linalg.norm(tip(pair[0]) - tip(pair[1])))
json.dump(out, open(os.path.join(HERE, 'look2', 'breath_stats.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
