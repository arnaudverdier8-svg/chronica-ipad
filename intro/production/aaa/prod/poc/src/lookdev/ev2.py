import sys, os
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/poc/src')
import numpy as np, cv2
from exr import read_exr
from r25render import grade
# usage: ev2.py in.exr out.png [raw]   (graded like the film unless raw)
a = read_exr(sys.argv[1])[..., :3]
if len(sys.argv) > 3 and sys.argv[3] == 'raw':
    u = (np.clip(a, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)
else:
    u = grade(a, grain=0.0)
cv2.imwrite(sys.argv[2], cv2.cvtColor(u, cv2.COLOR_RGB2BGR))
