import __main__ as _m; R = _m.R
import cv2, numpy as np
r = R(cx=296, cy=135, cache='cache_crown.pkl')
im = r['img'][..., ::-1]
cv2.imwrite(os.path.join(W, 'c6_crown.png'), im)
c = im[130:560, 440:820]
cv2.imwrite(os.path.join(W, 'c6_crown_x2.png'), cv2.resize(c, None, fx=2.4, fy=2.4, interpolation=cv2.INTER_CUBIC))
