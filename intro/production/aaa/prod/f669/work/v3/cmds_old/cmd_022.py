import __main__ as _m; R = _m.R
import cv2, numpy as np
import touchup as TU
tiles = []
cfgs = [('c 1.5/1.5/1.0 q60 s2', dict(k_dark=1.5, k_hot=1.5, k_detail=1.0, q_ref=60, sigma=2.0)),
        ('d 1.8/2.0/1.2 q55 s1.4', dict(k_dark=1.8, k_hot=2.0, k_detail=1.2, q_ref=55, sigma=1.4)),
        ('e 2.2/2.5/1.4 q50 s1.2', dict(k_dark=2.2, k_hot=2.5, k_detail=1.4, q_ref=50, sigma=1.2)),
        ('f 1.4/2.4/1.6 q60 s1.0', dict(k_dark=1.4, k_hot=2.4, k_detail=1.6, q_ref=60, sigma=1.0))]
for name, cfg in cfgs:
    TU.MP.update(cfg)
    r = R(cx=296, cy=135, cache='cache_crown.pkl')
    im = r['img'][..., ::-1]
    c = im[200:430, 510:750]
    c = cv2.resize(c, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    cv2.putText(c, name, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    tiles.append(c)
cv2.imwrite(os.path.join(W, 'c2_crown_grid.png'), np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])]))
