import os, sys, time
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/lib')
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np, cv2
cv2.setNumThreads(2)
from chron.config import MAPS
from chron.maps import MapSet
from chron import frontal, shade, grade
from chron.anim.groupanim import GroupAnim
from chron.lift import Slip, tethers
from chron.color import pal
from chron.util import save_rgb

W = os.path.dirname(os.path.abspath(__file__))
G = MapSet(MAPS + '/p1_oath_ground')
king, crown = GroupAnim(G, ['king']), GroupAnim(G, ['crown'])
print('king n', king.n, 'crown n', crown.n)
f = 669
s = 4.65 * 1.25
VX, VY = 294.5, 200.0
cx = VX + (0.5 - 0.47) * 2560 / s
cy = float(sys.argv[1]) if len(sys.argv) > 1 else 172.0
view = dict(cx_mm=cx, cy_mm=cy, px_per_mm=s)
az = 128.0
el = 12.0
import math
d = 78.0 / math.tan(math.radians(el))
cpos = (VX + d * math.cos(math.radians(az)), 190 - d * math.sin(math.radians(az)), 78.0)
print('candle', cpos)
candle = dict(pos_mm=cpos, K=1900, i=2.6, ref_mm=360, tint=0.55, shadow=True)
light = shade.rig(az=az, el=el, K=1900, key_i=1.2, fill_ratio=6, tint=0.5, points=[candle])
kmap = dict(cx_mm=VX - 15, cy_mm=190, r_mm=150, floor=0.25, aspect=1.25)
t = time.time()
tm = {}
u = king.n
fr = frontal.render(G, view, light, age=1.0, kmap=kmap, edit=king.edit(u, mode='unpick'), timing=tm)
print('render', time.time() - t, tm)
slip = Slip(crown)
L_ = slip.layers(view, light, 15.0)
lin = slip.composite(fr['lin'], L_)
print('total', time.time() - t)
for ex in (1.0, 1.6):
    img = grade.grade(lin, exposure=ex, act='II', seed=f)
    save_rgb(os.path.join(W, f't0_ex{ex}.png'), img)
    cv2.imwrite(os.path.join(W, f't0_ex{ex}_prev.jpg'), cv2.resize(img[..., ::-1], (1280, 720), interpolation=cv2.INTER_AREA))
np.save(os.path.join(W, 't0_lin.npy'), lin.astype(np.float16))
