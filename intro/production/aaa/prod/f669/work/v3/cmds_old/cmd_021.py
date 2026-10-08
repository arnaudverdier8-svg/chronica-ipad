import __main__ as _m; R = _m.R
import cv2, numpy as np
import touchup as TU
tiles = []
cfgs = [('v2 (off)', None), ('v3a 0.62/0.85/0.55', dict(k_dark=0.62, k_hot=0.85, k_detail=0.55, q_ref=70)),
        ('b 1.1/1.2/0.8', dict(k_dark=1.1, k_hot=1.2, k_detail=0.8, q_ref=70)),
        ('c 1.5/1.5/1.0 q60', dict(k_dark=1.5, k_hot=1.5, k_detail=1.0, q_ref=60))]
for name, cfg in cfgs:
    if cfg is None:
        os.environ['F669_NOMETAL'] = '1'
    else:
        os.environ.pop('F669_NOMETAL', None); TU.MP.update(cfg)
    r = R(cx=296, cy=135, cache='cache_crown.pkl')
    im = r['img'][..., ::-1]
    c = im[200:430, 510:750]
    c = cv2.resize(c, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    cv2.putText(c, name, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    tiles.append(c)
os.environ.pop('F669_NOMETAL', None)
cv2.imwrite(os.path.join(W, 'c1_crown_grid.png'), np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])]))
