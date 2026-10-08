import __main__ as _m; R = _m.R
import numpy as np, cv2
import threads3d
A = shot._ASSETS; lo = A['loose']
ts = threads3d.ThreadSet(); lo.add_to(ts, 669)
f = 669
light = shot.light_of(f); cpos = light['candle']['pos_mm']
s = 5.8125; x0 = 300 - 640 / s; y0 = 232 - 360 / s
ctx = dict(x0=x0, y0=y0, s=s)
img = np.ones((720, 1280, 3), np.float32)
lfn = shot.thread_light_fn(f)
fill = shot.NIGHT * shot.FILL_I * shot.I0
ts.render(img, ctx, cpos, lfn, fill, shadow_strength=1.0, flame_r_mm=6.0, fuzz=False, shadow_only=True, contact_ao=0.0)
sh = 1 - img[..., 0]
print('shadow max', sh.max(), 'mean', sh.mean(), 'n>0.1', (sh > 0.1).sum())
cv2.imwrite(os.path.join(W, 'shadow_only.png'), (np.clip(sh, 0, 1) * 255).astype(np.uint8))
