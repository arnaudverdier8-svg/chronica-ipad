"""R25 ground plate passes (hearth / cool / fill) for f899: rectified relight of the war_ground sheet, warped to the camera.
Writes work/plate/plate_{h,c,f}_screen.npy (float16, 1440x2560x3, linear, per-light radiance incl. its pool) and the rectified hearth plate."""
import os, sys, json, time, copy
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bkit
import numpy as np, cv2
import camera as CAM, plate as PL
from chron.maps import MapSet
from chron import shade, frontal
from chron.ageing import apply_age
ROOT = os.path.dirname(HERE)
shot = json.load(open(os.path.join(ROOT, 'shot_f899.json')))
out = os.path.join(ROOT, 'work', 'plate'); os.makedirs(out, exist_ok=True)
sheet = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'maps', 'war_ground')
sfac = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
cam = CAM.build(shot['camera'])
P = shot['plate']; s = P['s'] * sfac
x0, y0, w, h = P['x0'], P['y0'], P['w'], P['h']
ms = MapSet(sheet)
level = ms.level_for(s)
t0 = time.time()
m0 = ms.read(x0 - 8, y0 - 8, x0 + w + 8, y0 + h + 8, level)
print('read', level, m0['h'].shape, time.time() - t0, flush=True)
H, Cc, Fi = shot['hearth'], shot['cool'], shot['fill']
age_fn = PL.age_amount_fn(shot['age'])
cp = cam['C']
cam_pos = (float(cp[0]), float(-cp[1]), float(cp[2]))        # sheet coords: x, y (down), z
rigs = dict(
    h=(shade.rig(az=H['az'], el=H['el'], K=H['K'], key_i=H['key_i'], tint=H['tint'], fill_ratio=1e9, fill_i=0.0, rim_i=0.0), None, 'auto'),
    c=(shade.rig(az=Cc['az'], el=Cc['el'], K=Cc['K'], key_i=Cc['key_i'], tint=Cc['tint'], fill_ratio=1e9, fill_i=0.0, rim_i=0.0, key=(Cc.get('rgb') and np.array(Cc['rgb'], np.float32))), None, None),
    f=(shade.rig(az=90, el=60, K=Fi['K'], key_i=0.0, tint=0.1, fill_i=Fi['i'], fill_K=Fi['K'], rim_i=0.0), None, None))
view = dict(x0_mm=x0, y0_mm=y0, px_per_mm=s)
out_wh = (int(round(w * s)), int(round(h * s)))
for k, (rig, km, fib) in rigs.items():
    m = {kk: (v.copy() if isinstance(v, np.ndarray) else v) for kk, v in m0.items()}
    def edit(mm):
        # order matters: folds -> library dye ageing (fade / linen yellowing, ghost protected; its own fox / tide discs are replaced by the irregular ones)
        # -> art-directed foxing / tideline / bleach front / protected-linen match -> gold tarnish front
        PL.fold_field(mm, shot['folds'])
        mm['alb'] = apply_age(mm['alb'], mm['mat'], age_fn(mm), {k: mm[k] for k in ('age_fade',) if k in mm}, ghost=mm.get('ghost'))
        PL.extra_age(mm, shot['age'], shot.get('arc'))
        PL.tarnish_metal(mm, shot['tarnish'], front=shot.get('tarnish_front'))
    t1 = time.time()
    fr = frontal.render(m, view, rig, out_wh=out_wh, fib=fib, fib_seed=899, kmap=km, edit=edit, age=None, cam=cam_pos, return_maps=(k == 'h'))
    img = PL.warp_plate(fr['lin'], cam, x0, y0, s)
    np.save(os.path.join(out, f'plate_{k}_screen.npy'), img.astype(np.float16))
    if k == 'h':
        np.save(os.path.join(out, 'plate_h_rect.npy'), fr['lin'].astype(np.float16))
        mm_ = fr['maps']; PXm = mm_['PX']; ox_, oy_ = mm_['origin_mm']; x0_, y0_, w_, h_ = fr['rect_mm']; s_ = fr['px_per_mm']
        mt = cv2.GaussianBlur((mm_['mat'] == 3).astype(np.float32), (0, 0), 0.25 * PXm)
        Ma = np.array([[s_ / PXm, 0, (ox_ - x0_) * s_ + 0.5 * (s_ / PXm - 1)], [0, s_ / PXm, (oy_ - y0_) * s_ + 0.5 * (s_ / PXm - 1)]], np.float32)
        mt_r = cv2.warpAffine(mt, Ma, out_wh, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        np.save(os.path.join(out, 'plate_metal_screen.npy'), PL.warp_plate(mt_r, cam, x0, y0, s, interp=cv2.INTER_LINEAR).astype(np.float16))
        del mm_
    print(k, 'rendered', time.time() - t1, flush=True)
print('done', time.time() - t0)
