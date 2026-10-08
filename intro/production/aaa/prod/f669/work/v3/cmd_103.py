import __main__ as _m; R = _m.R
import cv2, numpy as np
import loose, threads3d as T
import sys
shot.TS = T
T.FUZZ.update(pile=16.0, fly=2.6, a_pile=0.62, a_fly=0.45, side=0.82)
A = shot._ASSETS
A['loose'] = loose.LooseEnds(A['kv'])
tiles = []
for dec in (3.4, 6.0, 9.0):
    T.SHADOW_DECAY_YARN = dec
    r = R(cache='cache_strands.pkl')
    im = r['img'][..., ::-1]
    c = cv2.resize(im[150:450, 480:860], None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    cv2.putText(c, 'decay %.1f' % dec, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    tiles.append(c)
cv2.imwrite(os.path.join(W, 's9_decay.png'), np.hstack(tiles))
