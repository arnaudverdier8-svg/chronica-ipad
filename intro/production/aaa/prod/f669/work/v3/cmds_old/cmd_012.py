import __main__ as _m; R = _m.R
import cv2, time
import loose
t = time.time()
A = shot._ASSETS
A['loose'] = loose.LooseEnds(A['kv'])
print('  loose rebuilt %.1fs' % (time.time() - t), flush=True)
r = R(cache='cache_strands.pkl')
im = r['img'][..., ::-1]
cv2.imwrite(os.path.join(W, 's5_strands.png'), im)
cv2.imwrite(os.path.join(W, 's5_x3.png'), cv2.resize(im[150:440, 480:820], None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC))
cv2.imwrite(os.path.join(W, 's5_x7.png'), cv2.resize(im[240:340, 560:700], None, fx=7, fy=7, interpolation=cv2.INTER_NEAREST))
