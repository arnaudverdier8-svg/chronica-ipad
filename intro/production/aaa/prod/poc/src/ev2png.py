import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from exr import read_exr
from r25render import grade
import cv2, numpy as np
# usage: ev2png.py in.exr out.png [exposure] [--neutral]
a = read_exr(sys.argv[1])[..., :3]
exp = float(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else None
img = grade(a, exposure=exp, grain=0.0, neutral='--neutral' in sys.argv)
cv2.imwrite(sys.argv[2], cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
