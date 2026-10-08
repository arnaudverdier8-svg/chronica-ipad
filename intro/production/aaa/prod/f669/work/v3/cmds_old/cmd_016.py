import __main__ as _m; R = _m.R
exec(open(os.path.join(W, 'bench.py')).read())
import threads3d as T
rows = []
for pile, fly, ap, side in [(0, 0, 0, 0), (10, 1.5, 0.55, 0.85), (16, 2.6, 0.62, 0.82), (26, 3.5, 0.7, 0.8)]:
    T.FUZZ.update(pile=pile, fly=fly, a_pile=ap, a_fly=0.45, side=side)
    bench([dict(fuzz=pile > 0, halo=1.0)], 'bench3_%d.png' % pile)
import cv2
cv2.imwrite(os.path.join(W, 'bench3.png'), np.vstack([cv2.imread(os.path.join(W, 'bench3_%d.png' % p)) for p in (0, 10, 16, 26)]))
