import os, sys, time
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src')
import numpy as np, cv2
import shot
W = os.path.dirname(os.path.abspath(__file__))
ims = []
for f in [int(a) for a in sys.argv[1:]]:
    t = time.time()
    r = shot.render_frame(f, out_wh=(1280, 720), level=1)
    print(f, round(time.time() - t, 1), r['timing']['loose'], round(r['timing']['u']), flush=True)
    ims.append(r['img'])
    cv2.imwrite(os.path.join(W, f't720_{f}.png'), r['img'][..., ::-1])
