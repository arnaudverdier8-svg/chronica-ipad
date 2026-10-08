# shared bench helper (exec'd by cmds): yarn variants on the cached linen window
import numpy as np, cv2, pickle, math
import threads3d
from chron import grade
f = 669
zc = pickle.load(open(os.path.join(W, 'cache_strands.pkl'), 'rb'))
base0 = zc['lin']
s = 5.8125; x0 = 300 - 640 / s; y0 = 232 - 360 / s
ctx = dict(x0=x0, y0=y0, s=s)
light = shot.light_of(f); cpos = light['candle']['pos_mm']
lfn = shot.thread_light_fn(f)
fill = shot.NIGHT * shot.FILL_I * shot.I0
ALB = np.array([0.0775, 0.0506, 0.0656], np.float32) * np.array([1.06, 1.0, 0.9], np.float32)


def bench(variants, name, angs=(20, 100), rad=0.36, pit=1.6, scale=3, crop=None):
    """variants: list of dict(fuzz=bool, halo=float, ao=float, ...) -> rows of the same yarn rendered with each variant."""
    out_rows = []
    for vi, v in enumerate(variants):
        ts = threads3d.ThreadSet()
        for ai, ang in enumerate(angs):
            cx = 250 + ai * 22.0; cy = 205 + vi * 0.0
            th = math.radians(ang)
            sig = np.linspace(0, 14, 90)
            P = np.stack([cx + (sig - 7) * math.cos(th), cy + (sig - 7) * math.sin(th), np.full(90, rad)], 1)
            ts.add(P, v.get('rad', rad), ALB, kind=4, seed=0.1 + 0.13 * ai, pitch_mm=v.get('pit', pit), slub=0.08, dip=False, fray=3,
                   halo=v.get('halo', 1.0), fuzz_k=v.get('fuzz_k', 1.0), shadow=0.85)
        img = base0.copy()
        ts.render(img, ctx, cpos, lfn, fill, shadow_strength=0.84, fuzz=v.get('fuzz', True), fuzz_seed=3, flame_r_mm=6.0, contact_ao=v.get('ao', 0.45))
        Yl = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        img = img + shot.COOL_LIFT * shot.NIGHT[None, None, :] * np.exp(-Yl / 0.045)[..., None]
        o = grade.grade(img, exposure=shot.EXPOSURE, act='II', seed=f)
        X0 = int((250 - 12 - x0) * s); Y0 = int((205 - 10 - y0) * s)
        c = o[Y0:Y0 + int(20 * s), X0:X0 + int(48 * s)][..., ::-1]
        out_rows.append(cv2.resize(c, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC))
    cv2.imwrite(os.path.join(W, name), np.vstack(out_rows))
