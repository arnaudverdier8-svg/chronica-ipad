import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r25render import grade
from exr import read_exr
import numpy as np, cv2
for p in sys.argv[1:]:
    a = read_exr(p)[..., :3]
    cv2.imwrite(p.replace('.exr', '.png'), cv2.cvtColor(grade(a, seed=1), cv2.COLOR_RGB2BGR))
