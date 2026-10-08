"""offline tuning of touchup.metal_pop on the cached crown window (no assets needed).  python3 crown_tune.py"""
import os, sys, pickle
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
import shot, touchup as TU
from chron import grade
W = os.path.join(HERE, '..', 'work', 'v3')
zc = pickle.load(open(os.path.join(W, 'cache_crown.pkl'), 'rb'))
base, L_ = zc['lin'], zc['L_']
view = dict(cx_mm=296, cy_mm=135, px_per_mm=5.8125); wh = (1280, 720)
def render(cfg):
    lin = base.copy()
    slip = L_['rgb']
    if cfg is not None:
        TU.MP.update(cfg); slip = TU.metal_pop(slip, L_['metal'], L_['alpha'])
    a = L_['alpha'][..., None]
    lin = lin * (1 - a) + slip * a
    Yl = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    lin = lin + shot.COOL_LIFT * shot.NIGHT[None, None, :] * np.exp(-Yl / 0.045)[..., None]
    lin, _ = TU.pool_contrast(lin, view, wh)
    img = grade.grade(lin, exposure=shot.EXPOSURE, act='II', seed=669)
    return img
m = (L_['metal'] > 0.5) & (L_['alpha'] > 0.5)
cfgs = [('v2', None), ('v3 final', dict(k_dark=1.0, k_hot=1.4, k_detail=1.1, q_ref=55, sigma=1.4, ramp=0.8, floor=0.20))]
tiles = []
for name, cfg in cfgs:
    img = render(cfg)
    Y = (img.astype(np.float32) / 255 * [0.2126, 0.7152, 0.0722]).sum(-1)
    y = Y[m]
    print('%-22s gold luma mean %.3f p10 %.3f p50 %.3f p90 %.3f  std %.3f  frac>0.7 %.3f' % (name, y.mean(), *np.percentile(y, [10, 50, 90]), y.std(), (y > 0.7).mean()))
    c = cv2.resize(img[220:430, 530:740][..., ::-1], None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    cv2.putText(c, name, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2); tiles.append(c)
cv2.imwrite(os.path.join(W, 'crown_tune.png'), np.hstack(tiles))
