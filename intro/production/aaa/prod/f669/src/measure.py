"""luma statistics (graded sRGB, Rec.709 luma) of regions of an f669 frame.  python3 measure.py image.png [W]"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np, cv2
import shot, silhouette as SIL
path = sys.argv[1]
im = cv2.imread(path)[..., ::-1].astype(np.float32) / 255
Hh, Ww = im.shape[:2]
v = shot.view_of(669, (Ww, Hh)); s = v['px_per_mm']
x0 = v['cx_mm'] - Ww / 2 / s; y0 = v['cy_mm'] - Hh / 2 / s
Y = (im * [0.2126, 0.7152, 0.0722]).sum(-1)
def px(xm, ym): return int(round((xm - x0) * s)), int(round((ym - y0) * s))
poly = (SIL.sil_mm() - [x0, y0]) * s
m = np.zeros((Hh, Ww), np.uint8); cv2.fillPoly(m, [np.round(poly).astype(np.int32)], 1)
m = cv2.erode(m, np.ones((int(6 * s / 2) * 2 + 1,) * 2, np.uint8)).astype(bool)
# exclude where the void is occupied by non-void (crown etc): rows y> 150mm only
yy = (np.arange(Hh) / s + y0)[:, None] * np.ones((1, Ww))
mm = m & (yy > 150) & (yy < 255)
q = lambda a: np.quantile(a, [.05, .5, .95]).round(3).tolist()
print('void   mean %.3f  p5/p50/p95 %s' % (Y[mm].mean(), q(Y[mm])))
reg = dict(red_face=(198, 148), blue_face=(396, 148), gold_face=(126, 158), green_face=(472, 156), wallL=(120, 60), wallR=(470, 60), table=(300, 285), banner=(300, 40))
for k, (xm, ym) in reg.items():
    X, Yp = px(xm, ym); R = int(5 * s)
    a = Y[max(Yp - R, 0):Yp + R, max(X - R, 0):X + R]
    print('%-9s mean %.3f' % (k, a.mean() if a.size else -1))
