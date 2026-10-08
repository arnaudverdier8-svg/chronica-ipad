"""Calibrate the L1 (5 px/mm) path of the 720p proof against L0 (10 px/mm, the 1440p keyframe path): same frame, same
output size; mean scene-linear luminance ratio L0/L1 over the frame and per region."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import shot
F = int(sys.argv[1]) if len(sys.argv) > 1 else 669
Yw = np.array([0.2126, 0.7152, 0.0722], np.float32)
r1 = shot.render_frame(F, out_wh=(1280, 720), level=1); Y1 = r1['lin'] @ Yw
r0 = shot.render_frame(F, out_wh=(1280, 720), level=0, free_tiles=True); Y0 = r0['lin'] @ Yw
print('frame', F, 'global mean L0/L1 = %.4f' % (Y0.mean() / Y1.mean()))
H, W = Y0.shape
for nm, (a, b, c, d) in dict(left=(0, 720, 0, 400), mid=(0, 720, 400, 880), right=(0, 720, 880, 1280), top=(0, 200, 0, 1280), bottom=(520, 720, 0, 1280)).items():
    print(nm, 'ratio %.4f' % (Y0[a:b, c:d].mean() / Y1[a:b, c:d].mean()))
# by brightness decile of L1
q = np.quantile(Y1, [0, .25, .5, .75, .9, 1.0])
for lo, hi in zip(q[:-1], q[1:]):
    m = (Y1 >= lo) & (Y1 < hi)
    print('L1 luma [%.3f,%.3f): ratio %.4f' % (lo, hi, Y0[m].mean() / Y1[m].mean()))
