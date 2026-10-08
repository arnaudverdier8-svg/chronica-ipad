"""Crown-shadow diagnostic at the keyframe: crown alpha | projected shadow (extended candle) | tether shadows | the result.
Writes out/f669_shadow_diagnostic.png.  Uses a 1280x720 L1 render of the SAME geometry (the shadow maths is resolution
independent) for the masks and the 2560 keyframe for the composite crop."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np, cv2
import shot
OUT = os.path.join(HERE, '..', 'out')
F = 669
r = shot.render_frame(F, out_wh=(2560, 1440), level=1, threads=False, debug=True, free_tiles=True)
L = r['L']
x, y, w, h = 1000, 330, 1000, 760
def g(m): return cv2.cvtColor((np.clip(m, 0, 1) * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)[y:y + h, x:x + w]
def lab(im, t):
    im = im.copy(); cv2.putText(im, t, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 4, cv2.LINE_AA); cv2.putText(im, t, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (230, 220, 200), 1, cv2.LINE_AA); return im
final = cv2.imread(os.path.join(OUT, 'f669_2560x1440.png'))[y:y + h, x:x + w]
tiles = [lab(g(L['alpha']), 'crown alpha (slip silhouette, incl. prongs)'), lab(g(L['shadow']), 'projected shadow, extended candle (penumbra grows with throw)'),
         lab(g(np.clip(L['tether_shadow'] * 3, 0, 1)), 'four tether shadows (x3 gain)'), lab(final, 'keyframe')]
sheet = np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])])
cv2.imwrite(os.path.join(OUT, 'f669_shadow_diagnostic.png'), cv2.resize(sheet, None, fx=0.7, fy=0.7, interpolation=cv2.INTER_AREA))
print('ok')
