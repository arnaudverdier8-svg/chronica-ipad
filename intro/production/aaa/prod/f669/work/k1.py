import os, sys, time
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src')
import numpy as np, cv2
import shot
from chron.util import save_rgb
W = os.path.dirname(os.path.abspath(__file__))
tag = sys.argv[1] if len(sys.argv) > 1 else 'k1'
f = int(sys.argv[2]) if len(sys.argv) > 2 else 669
ex = float(sys.argv[3]) if len(sys.argv) > 3 else 1.55
r = shot.render_frame(f, exposure=ex)
print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r['timing'].items()})
save_rgb(os.path.join(W, f'{tag}.png'), r['img'])
np.save(os.path.join(W, f'{tag}_lin.npy'), r['lin'].astype(np.float16))
cv2.imwrite(os.path.join(W, f'{tag}_prev.jpg'), cv2.resize(r['img'][..., ::-1], (1280, 720), interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 92])
