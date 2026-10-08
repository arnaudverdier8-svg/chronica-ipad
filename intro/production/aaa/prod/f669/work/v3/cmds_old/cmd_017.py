import __main__ as _m; R = _m.R
import cv2
import loose, threads3d as T
T.FUZZ.update(pile=16.0, fly=2.6, a_pile=0.62, a_fly=0.45, side=0.82)
A = shot._ASSETS
A['loose'] = loose.LooseEnds(A['kv'])
r = R(cache='cache_strands.pkl')
im = r['img'][..., ::-1]
cv2.imwrite(os.path.join(W, 's6_strands.png'), im)
cv2.imwrite(os.path.join(W, 's6_x3.png'), cv2.resize(im[150:440, 480:820], None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC))
