"""quick composition preview: ground plate only (no slips), hearth + cool + fill, warped by the f899 camera."""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bkit
import numpy as np, cv2
import camera as CAM, plate as PL
from chron.maps import MapSet
from chron import shade, grade
ROOT = os.path.dirname(HERE)
shot = json.load(open(os.path.join(ROOT, 'shot_f899_v2.json')))
sheet = sys.argv[1]; out = sys.argv[2]; sc = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
cam = CAM.build(shot['camera'])
P = shot['plate']; s = P['s'] * (1 if len(sys.argv) <= 4 else float(sys.argv[4]))
ms = MapSet(sheet)
rect = (P['x0'], P['y0'], P['w'], P['h'])
age_fn = PL.age_amount_fn(shot['age'])
H = shot['hearth']; Cc = shot['cool']; Fi = shot['fill']
cam_pos = (300.0, 198.0 + 900 * np.sin(np.radians(22)), 900 * np.cos(np.radians(22)))
t0 = time.time()
rig_h = shade.rig(az=H['az'], el=H['el'], K=H['K'], key_i=H['key_i'], tint=H['tint'], fill_ratio=1e9, fill_i=0.0, rim_i=0.0)
rig_c = shade.rig(az=Cc['az'], el=Cc['el'], K=Cc['K'], key_i=Cc['key_i'], tint=Cc['tint'], fill_ratio=1e9, fill_i=0.0, rim_i=0.0)
rig_f = shade.rig(az=90, el=60, K=Fi['K'], key_i=0.0, tint=0.1, fill_i=Fi['i'], fill_K=Fi['K'], rim_i=0.0)
tm = {}
fh = PL.render_pass(ms, cam, rect, s, rig_h, H['kmap'], shot['folds'], age_fn, shot['tarnish'], fib='auto', cam_pos=cam_pos, timing=tm)
print('hearth', tm, time.time() - t0, flush=True)
fc = PL.render_pass(ms, cam, rect, s, rig_c, Cc['kmap'], shot['folds'], age_fn, shot['tarnish'], fib=None, cam_pos=cam_pos)
ff = PL.render_pass(ms, cam, rect, s, rig_f, None, shot['folds'], age_fn, shot['tarnish'], fib=None, cam_pos=cam_pos)
print('passes', time.time() - t0, flush=True)
lin_p = fh['lin'] + fc['lin'] + ff['lin']
np.save(os.path.join(os.path.dirname(out), 'plate_h.npy'), fh['lin'].astype(np.float16))
img = PL.warp_plate(lin_p, cam, rect[0], rect[1], s)
if sc != 1.0:
    img = cv2.resize(img, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
G = shot['grade']
o = grade.grade(img, exposure=G['exposure'], act=G['act'], seed=899, grain=G['grain'])
cv2.imwrite(out, cv2.cvtColor(o, cv2.COLOR_RGB2BGR))
print('done', time.time() - t0)
