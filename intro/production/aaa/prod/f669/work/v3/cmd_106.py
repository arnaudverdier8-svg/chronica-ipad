import __main__ as _m; R = _m.R
import cv2, numpy as np
import loose, threads3d as T
shot.TS = T
A = shot._ASSETS
A['loose'] = loose.LooseEnds(A['kv'])
r = R(cache='cache_strands.pkl')
im = r['img'][..., ::-1]
cv2.imwrite(os.path.join(W, 's10_strands.png'), im)
cv2.imwrite(os.path.join(W, 's10_x2.png'), cv2.resize(im[100:500, 400:900], None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC))
