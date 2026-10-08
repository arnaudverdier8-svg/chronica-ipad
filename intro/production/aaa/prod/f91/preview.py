"""Fast layout preview: build the scene at low density (default 4 px/mm) without writing a MapSet, add the padding base to the
height and relight the live maps at s=2.5 px/mm (1280x720) over the f91 window with the v2 rig.  Writes look2/pv_<tag>.jpg."""
import os, sys, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault('F91_SHOT', 'shot_f91.json')
import scene_f91 as SC                         # noqa: E402
import render_f91 as R                         # noqa: E402
import numpy as np, cv2                         # noqa: E402
from chron import frontal, shade, grade         # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--px', type=float, default=4.0)
ap.add_argument('--tag', default='a')
ap.add_argument('--ext', action='store_true')
ap.add_argument('--x0', type=float, default=None)
ap.add_argument('--y0', type=float, default=5.0)
ap.add_argument('--w', type=float, default=512.0)
ap.add_argument('--s', type=float, default=2.5)
a = ap.parse_args()
t0 = time.time()
c = SC.build(a.px, preview=True, ext=a.ext)
print('built', round(time.time() - t0, 1))
m = c.m
m['h'] = m['h'] + 0.0
m['origin_mm'] = (0.0, 0.0)
m['valid'] = np.ones(m['h'].shape, bool)
for k in ('base', 'sfr', 'stamp', 'sid'):
    m.pop(k, None) if k != 'sid' else None
x0 = SC.OX + SC.FRAME_X0 if a.x0 is None else a.x0
view = dict(x0_mm=x0, y0_mm=a.y0, px_per_mm=a.s)
out_wh = (int(a.w * a.s), int(a.w * a.s * 9 / 16))
fr = frontal.render(m, view, R.rig(), out_wh=out_wh, fib=None, kmap=R.SHOT['kmap'], edit=R.fold_field, age=R.age_map)
lin = fr['lin']
pa = R.pool_all(lin.shape[:2], a.s, x0, a.y0)
lin = lin * pa[..., None]
lin = R.split_tone(lin, R.SHOT.get('split_tone'))
G = R.SHOT['grade']
img = grade.grade(lin, exposure=G['exposure'], act=G['act'], seed=91, grain=G.get('grain', 0.012))
os.makedirs(os.path.join(HERE, 'look2'), exist_ok=True)
cv2.imwrite(os.path.join(HERE, 'look2', f'pv_{a.tag}.jpg'), cv2.cvtColor(img, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
print(f'preview {time.time() - t0:.1f}s level {fr["level"]}')
