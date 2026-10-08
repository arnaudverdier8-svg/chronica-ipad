"""Shimmer check for the motion test: register consecutive frames (affine ECC), then compare their high-pass detail.
Reports the high-frequency residual as % of the high-frequency signal (low % = stable texture, high % = shimmer/boil).
"""
import sys, glob, os, numpy as np, cv2
fr = sorted(glob.glob(sys.argv[1]))
def load(p):
    a = cv2.imread(p, cv2.IMREAD_UNCHANGED).astype(np.float32)
    a /= 65535.0 if a.max() > 255 else 255.0
    return cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
res = []
for i in range(0, len(fr) - 1, max(1, (len(fr) - 1) // 12)):
    a, b = load(fr[i]), load(fr[i + 1])
    warp = np.eye(2, 3, dtype=np.float32)
    try:
        _, warp = cv2.findTransformECC(cv2.GaussianBlur(a, (0, 0), 2), cv2.GaussianBlur(b, (0, 0), 2), warp, cv2.MOTION_AFFINE,
                                       (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 60, 1e-6), None, 5)
    except cv2.error:
        pass
    bw = cv2.warpAffine(b, warp, (a.shape[1], a.shape[0]), flags=cv2.INTER_CUBIC + cv2.WARP_INVERSE_MAP)
    hp = lambda x: x - cv2.GaussianBlur(x, (0, 0), 2.0)
    m = np.zeros_like(a, bool); m[40:-40, 40:-40] = True
    ha, hb = hp(a), hp(bw)
    sig = np.sqrt((ha[m] ** 2).mean()); r = np.sqrt(((ha - hb)[m] ** 2).mean())
    res.append(r / sig * 100)
    print(f'frames {i}->{i + 1}: HF residual {r / sig * 100:.1f}% of HF signal')
print('MEAN HF residual %.1f%%' % np.mean(res))
