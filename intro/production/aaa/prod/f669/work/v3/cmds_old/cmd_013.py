import __main__ as _m; R = _m.R
import numpy as np, cv2, pickle, math
import threads3d
from chron import grade
f = 669
zc = pickle.load(open(os.path.join(W, 'cache_strands.pkl'), 'rb'))
base = zc['lin'].copy()                      # raw frontal frame at the strands window (1280x720)
s = 5.8125; x0 = 300 - 640 / s; y0 = 232 - 360 / s
ctx = dict(x0=x0, y0=y0, s=s)
light = shot.light_of(f); cpos = light['candle']['pos_mm']
lfn = shot.thread_light_fn(f)
fill = shot.NIGHT * shot.FILL_I * shot.I0
alb = np.array([0.0775, 0.0506, 0.0656], np.float32) * np.array([1.06, 1.0, 0.9], np.float32)
ts = threads3d.ThreadSet()
rows = [(0.30, 1.4), (0.36, 1.6), (0.42, 1.9)]
angs = [0, 45, 90, 135, 200]
for ri, (rad, pit) in enumerate(rows):
    for ai, ang in enumerate(angs):
        cx = 245 + ai * 17.0; cy = 205 + ri * 12.0
        th = math.radians(ang)
        sig = np.linspace(0, 12, 80)
        P = np.stack([cx + sig * math.cos(th) - 6 * math.cos(th), cy + sig * math.sin(th) - 6 * math.sin(th), np.full(80, rad)], 1)
        ts.add(P, rad, alb, kind=4, seed=0.1 + 0.13 * ai, pitch_mm=pit, slub=0.08, dip=False, fray=3, halo=1.0, fuzz_k=1.0, shadow=0.85)
img = base.copy()
ts.render(img, ctx, cpos, lfn, fill, shadow_strength=0.84, fuzz=True, fuzz_seed=3, flame_r_mm=6.0, contact_ao=0.45)
Yl = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
img = img + shot.COOL_LIFT * shot.NIGHT[None, None, :] * np.exp(-Yl / 0.045)[..., None]
out = grade.grade(img, exposure=shot.EXPOSURE, act='II', seed=f)
c = out[190:440, 290:720][..., ::-1]
cv2.imwrite(os.path.join(W, 'bench1.png'), cv2.resize(c, None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST))
cv2.imwrite(os.path.join(W, 'bench1_x3.png'), cv2.resize(c, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC))
