import __main__ as _m; R = _m.R
import cv2, numpy as np
import touchup as TU
tiles = []
cfgs = [('d ramp0 (orig chroma)', dict(k_dark=1.8, k_hot=2.0, k_detail=1.2, q_ref=55, sigma=1.4, ramp=0.0)),
        ('d ramp .75', dict(k_dark=1.8, k_hot=2.0, k_detail=1.2, q_ref=55, sigma=1.4, ramp=0.75)),
        ('g 2.0/2.2/1.3 q52 s1.3 ramp1', dict(k_dark=2.0, k_hot=2.2, k_detail=1.3, q_ref=52, sigma=1.3, ramp=1.0)),
        ('h 1.6/1.8/1.2 q58 s1.4 ramp.75', dict(k_dark=1.6, k_hot=1.8, k_detail=1.2, q_ref=58, sigma=1.4, ramp=0.75))]
for name, cfg in cfgs:
    TU.MP.update(cfg)
    r = R(cx=296, cy=135, cache='cache_crown.pkl')
    im = r['img'][..., ::-1]
    c = im[200:430, 510:750]
    c = cv2.resize(c, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    cv2.putText(c, name, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    tiles.append(c)
cv2.imwrite(os.path.join(W, 'c3_crown_grid.png'), np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])]))
