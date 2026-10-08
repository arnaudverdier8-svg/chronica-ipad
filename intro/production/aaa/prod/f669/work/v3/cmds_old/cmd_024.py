import __main__ as _m; R = _m.R
import cv2, numpy as np
import touchup as TU
tiles = []
cfgs = [('i q80 1.2/1.2/1.0 s1.4 r.75', dict(k_dark=1.2, k_hot=1.2, k_detail=1.0, q_ref=80, sigma=1.4, ramp=0.75)),
        ('j q85 1.4/1.5/1.2 s1.4 r.75', dict(k_dark=1.4, k_hot=1.5, k_detail=1.2, q_ref=85, sigma=1.4, ramp=0.75)),
        ('k q75 1.0/1.0/1.0 s1.4 r.5', dict(k_dark=1.0, k_hot=1.0, k_detail=1.0, q_ref=75, sigma=1.4, ramp=0.5)),
        ('l q90 1.6/1.8/1.2 s1.2 r.75', dict(k_dark=1.6, k_hot=1.8, k_detail=1.2, q_ref=90, sigma=1.2, ramp=0.75))]
for name, cfg in cfgs:
    TU.MP.update(cfg)
    r = R(cx=296, cy=135, cache='cache_crown.pkl')
    im = r['img'][..., ::-1]
    c = im[200:430, 510:750]
    c = cv2.resize(c, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    cv2.putText(c, name, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    tiles.append(c)
cv2.imwrite(os.path.join(W, 'c4_crown_grid.png'), np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])]))
