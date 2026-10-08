import os, sys, time
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/lib')
sys.path.insert(0, '/tmp/claude-0/-home-user-chronica-ipad/ae358f8e-1e70-5169-a8ed-87e6e6e15cfd/scratchpad/aaa/prod/f669/src')
os.environ.setdefault('NUMBA_NUM_THREADS', '2')
import numpy as np, cv2
cv2.setNumThreads(2)
from chron.config import MAPS
from chron.maps import MapSet
from chron.color import lin2srgb
from chron.shade import normals
from kingvoid import KingVoid
W = os.path.dirname(os.path.abspath(__file__))
G = MapSet(MAPS + '/p1_oath_ground')
t = time.time(); kv = KingVoid(G); print('init', time.time() - t)
th = kv.threads(); L = np.array([b - a for a, b in th]); print('threads', len(th), 'entries/thread q', np.quantile(L, [0.5, 0.9, 0.99]), L.max())
def look(st):
    N = normals(st['h'].astype(np.float32), 10.0)
    sh = np.clip(N[..., 0] * -0.5 + N[..., 1] * -0.5 + N[..., 2] * 0.7, 0, 1)
    img = np.clip(lin2srgb(np.clip(st['alb'] * sh[..., None] * 1.6, 0, 1)), 0, 1)
    return (img * 255).astype(np.uint8)[..., ::-1]
for u, nm in ((0, 'full'), (kv.n, 'void')):
    t = time.time(); st = kv.state(kv.n - u); print(nm, time.time() - t)
    cv2.imwrite(os.path.join(W, f'a6_{nm}.jpg'), cv2.resize(look(st), None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
# compare 'full' with stored full bake (p1_oath) for sanity
F = MapSet(MAPS + '/p1_oath')
x0, y0, x1, y1 = kv.bbox
st = kv.state(kv.n)
ref = F.read_px(x0, y0, x1, y1, 0, keys=['h', 'alb'])
d = np.abs(st['alb'] - ref['alb'].astype(np.float32)).max(-1)
print('full vs bake: frac alb diff>0.02', (d > 0.02).mean())
cv2.imwrite(os.path.join(W, 'a6_fulldiff.jpg'), np.clip(d * 600, 0, 255).astype(np.uint8)[::2, ::2])
